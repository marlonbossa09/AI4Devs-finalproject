"""CLI de provisión del servidor (A2: órdenes de línea de comandos, sin endpoints HTTP administrativos).

Uso (desde ``backend/``)::

    uv run python -m scripts.provision crear-primer-operador --identificador <identificador>
    uv run python -m scripts.provision crear-equipo   --operador <id> --organizacion <uuid> --nombre "<nombre>"
    uv run python -m scripts.provision crear-persona  --operador <id> --nombre "<nombre>" --identificador-acceso <id> \
        --equipo <uuid> --rol colaborador|supervisor --desde AAAA-MM-DD
    uv run python -m scripts.provision registrar-traslado --operador <id> \
        --cambio <persona>:<equipo>:colaborador|supervisor:AAAA-MM-DD [--cambio ...]
    uv run python -m scripts.provision finalizar-pertenencia --operador <id> \\
        --finalizar <persona>:AAAA-MM-DD [--finalizar ...] [--cambio ...]
    uv run python -m scripts.provision cancelar-operacion-programada --operador <id> \\
        --cancelar <persona>:<tipo>:AAAA-MM-DD [--cancelar ...] [--cambio ...] [--finalizar ...]
    uv run python -m scripts.provision desactivar-acceso --operador <id> --persona <uuid> --motivo "<motivo>"
    uv run python -m scripts.provision purgar-eventos-autenticacion --operador <id>
    uv run python -m scripts.provision purgar-codigos --operador <id>
    uv run python -m scripts.provision emitir-codigo-primer-acceso --operador <id> --persona <uuid>
    uv run python -m scripts.provision emitir-codigo-recuperacion --operador <id> --persona <uuid> \
        --procedimiento PRESENCIAL|VIDEOLLAMADA|PROCEDIMIENTO_INTERNO --referencia <referencia-administrativa>

Seguridad:
- La credencial de la persona operadora NUNCA va como argumento (se vería en la lista de procesos y en el historial):
  se lee de la variable ``SMARTWORK_OPERADOR_CREDENCIAL`` o, en una terminal, se pide sin eco.
- Las órdenes se ejecutan con ``PROVISION_DATABASE_URL`` (rol de provisión de privilegios mínimos). La CLI se niega a
  trabajar si el servidor confirma que la conexión es de otro rol, o de un rol con privilegios de administración.
  ``crear-primer-operador`` es el único procedimiento que usa el rol propietario (instalación) y se niega si ya existe
  una persona operadora.
- Una orden rechazada no modifica nada. Los errores se imprimen con su código y un mensaje fijo, nunca con el texto de una
  excepción (que podría incluir valores); no se escribe ninguna credencial ni código en la salida.
- La salida y los errores son JSON con solo caracteres ASCII (los acentos van escapados), para que no dependa de la
  codificación de la terminal ni de la tubería.
- Intentos fallidos (M1-T7): una credencial incorrecta, o un identificador desconocido, avanza un contador PROPIO de la persona
  operadora con la misma curva de espera que las personas (5 intentos libres; luego 30 s, 1, 2, 4, 8, 16, 32 min y 1 hora). Durante
  una espera la orden termina con el código de salida 4 y ``DEMASIADOS_INTENTOS``, sin verificar la credencial. Nunca se deshabilita
  a la persona operadora: las esperas caducan solas.
- Emisión de códigos (M1-T8.2): el código se muestra UNA sola vez y SOLO si la entrada y la salida son una terminal interactiva; con una tubería,
  un archivo o sin terminal la orden se rechaza ANTES de tocar nada. El código nunca va en el JSON de resultado, ni en la auditoría, ni en un
  argumento, y no se puede volver a ver: si falla, se emite otro. Ninguna orden recibe un código ni una credencial como argumento. La recuperación
  pide además que la persona operadora DECLARE (escribiendo CONFIRMO) que verificó la identidad por el procedimiento y la referencia indicados.
- Purga de códigos (M1-T8.6): ``purgar-codigos`` borra los códigos usados, invalidados o caducados que terminaron hace 30 días o más, con el reloj de
  PostgreSQL. No borra un código pendiente y vigente ni uno más reciente (la base lo impide además a cualquier rol), no toca la auditoría funcional,
  es repetible y solo informa de cuántos borró: ni códigos, ni hashes, ni personas. Nada la lanza sola (no hay planificador): quien administra el
  servidor debe ejecutarla periódicamente, igual que ``purgar-eventos-autenticacion``.
- No existe ninguna opción para fijar la «fecha actual»: el reloj inyectable (D7) es solo para los casos de uso y las pruebas.
"""

import argparse
import getpass
import json
import os
import sys
import uuid
from datetime import date

from sqlalchemy import Connection, Engine, text

from app.config import get_settings
from app.provision import acceso, emision, eventos, operadores, programacion, servicio
from app.provision import codigos as registro_de_codigos
from app.provision.errores import ErrorDeProvision

VARIABLE_CREDENCIAL = "SMARTWORK_OPERADOR_CREDENCIAL"
CODIGO_RECHAZO, CODIGO_CONEXION, CODIGO_INTERNO, CODIGO_ESPERA = 2, 3, 1, 4
EMISION = {"emitir-codigo-primer-acceso": emision.PRIMER_ACCESO, "emitir-codigo-recuperacion": emision.RECUPERACION}
CONFIRMACION = "CONFIRMO"


def _hay_terminal() -> bool:
    """Solo se pide la credencial si hay una persona delante: entrada y salida de errores en una terminal. En Windows el
    dispositivo nulo se declara «terminal», por eso no basta con mirar la entrada."""
    return sys.stdin.isatty() and sys.stderr.isatty()


def leer_credencial(entorno=os.environ, pedir=getpass.getpass, interactivo: bool | None = None, confirmar: bool = False) -> str:
    """Credencial por un canal local que no es un argumento: variable de entorno o petición sin eco."""
    if entorno.get(VARIABLE_CREDENCIAL):
        return entorno[VARIABLE_CREDENCIAL]
    if interactivo if interactivo is not None else _hay_terminal():
        valor = pedir("Credencial de la persona operadora (no se muestra): ")
        if confirmar and pedir("Repita la credencial: ") != valor:
            raise ErrorDeProvision("CREDENCIAL_NO_VALIDA", [{"campo": "credencial", "motivo": "no_coincide"}])
        return valor
    raise ErrorDeProvision("CREDENCIAL_NO_VALIDA", [{"campo": "credencial", "motivo": f"falta_{VARIABLE_CREDENCIAL}_o_terminal"}])


def _rol_actual(conexion: Connection):
    return conexion.execute(text(
        "select current_user as usuario, current_database() as base, r.rolsuper, r.rolcreaterole, r.rolcreatedb "
        "from pg_roles r where r.rolname = current_user")).one()


def verificar_conexion_de_provision(conexion: Connection) -> dict:
    """Pregunta al servidor quién es la conexión: debe ser exactamente el rol de provisión y sin privilegios de administración."""
    rol = _rol_actual(conexion)
    if rol.usuario != get_settings().provision_db_role or rol.rolsuper or rol.rolcreaterole or rol.rolcreatedb:
        raise ErrorDeProvision("CONEXION_NO_PERMITIDA")
    return {"base": rol.base}


def verificar_conexion_de_instalacion(conexion: Connection) -> dict:
    """La instalación usa el rol propietario: nunca el de la aplicación ni el de provisión."""
    rol = _rol_actual(conexion)
    s = get_settings()
    if rol.usuario in (s.provision_db_role, s.app_db_role) or rol.rolsuper:
        raise ErrorDeProvision("CONEXION_NO_PERMITIDA")
    return {"base": rol.base}


def _uuid(valor: str, campo: str) -> uuid.UUID:
    try:
        return uuid.UUID(valor)
    except ValueError as error:
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": campo, "motivo": "formato"}]) from error


def _fecha(valor: str, campo: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError as error:
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": campo, "motivo": "formato"}]) from error


def _cambio(valor: str, indice: int) -> servicio.CambioSolicitado:
    """``persona:equipo:rol:fecha``. Los identificadores son UUID y no contienen ``:``; la fecha, tampoco."""
    partes = valor.split(":")
    if len(partes) != 4:
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": "cambio", "indice": indice, "motivo": "formato"}])
    persona, equipo, rol, fecha = partes
    try:
        return servicio.CambioSolicitado(uuid.UUID(persona), uuid.UUID(equipo), rol, date.fromisoformat(fecha))
    except ValueError as error:
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": "cambio", "indice": indice, "motivo": "formato"}]) from error


def _finalizacion(valor: str, indice: int) -> programacion.FinalizacionSolicitada:
    """``persona:fecha``."""
    partes = valor.split(":")
    try:
        if len(partes) != 2:
            raise ValueError
        return programacion.FinalizacionSolicitada(uuid.UUID(partes[0]), date.fromisoformat(partes[1]))
    except ValueError as error:
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": "finalizar", "indice": indice, "motivo": "formato"}]) from error


def _cancelacion(valor: str, indice: int) -> programacion.CancelacionSolicitada:
    """``persona:tipo:fecha``: la operación programada que se cancela, por su persona, su tipo y su fecha efectiva."""
    partes = valor.split(":")
    try:
        if len(partes) != 3:
            raise ValueError
        return programacion.CancelacionSolicitada(uuid.UUID(partes[0]), partes[1], date.fromisoformat(partes[2]))
    except ValueError as error:
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": "cancelar", "indice": indice, "motivo": "formato"}]) from error


def _historiales(historiales) -> list[dict]:
    return [{"persona_id": str(persona), "pertenencias": [
        {"id": str(h.id), "equipo_id": str(h.equipo_id), "equipo": h.equipo, "rol": h.rol, "desde": h.desde.isoformat(),
         "hasta_exclusivo": h.hasta_exclusivo.isoformat() if h.hasta_exclusivo else None} for h in historial]}
        for persona, historial in historiales.items()]


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="provision", description="Órdenes de provisión administrativa de SMARTWORK (CLI del servidor).")
    sub = p.add_subparsers(dest="orden", required=True)
    a = sub.add_parser("crear-primer-operador", help="Instalación: crea la primera persona operadora (rol propietario)")
    a.add_argument("--identificador", required=True)
    for nombre in ("crear-equipo", "crear-persona", "registrar-traslado", "finalizar-pertenencia", "cancelar-operacion-programada", "desactivar-acceso",
                   "purgar-eventos-autenticacion", "purgar-codigos", *EMISION):
        s = sub.add_parser(nombre)
        s.add_argument("--operador", required=True, help="identificador de la persona operadora")
        if nombre in ("purgar-eventos-autenticacion", "purgar-codigos"):
            continue
        if nombre in EMISION:
            s.add_argument("--persona", required=True, help="identificador (UUID) de la persona que recibirá el código")
            if nombre == "emitir-codigo-recuperacion":
                s.add_argument("--procedimiento", required=True, choices=emision.PROCEDIMIENTOS,
                               help="procedimiento con el que la persona operadora verificó la identidad (PROCEDIMIENTO_INTERNO debe corresponder a un protocolo documentado)")
                s.add_argument("--referencia", required=True, metavar="REFERENCIA",
                               help="referencia administrativa de la evidencia (de 3 a 64 caracteres, sin espacios): no un documento ni una descripción")
            continue
        if nombre == "desactivar-acceso":
            s.add_argument("--persona", required=True, help="identificador (UUID) de la persona cuyo acceso se desactiva")
            s.add_argument("--motivo", required=True,
                           help="motivo obligatorio (P6). Texto breve y no secreto: queda en la auditoría y en el historial del intérprete de órdenes")
        elif nombre in ("finalizar-pertenencia", "cancelar-operacion-programada"):
            if nombre == "finalizar-pertenencia":
                s.add_argument("--finalizar", action="append", required=True, metavar="PERSONA:FECHA",
                               help="la pertenencia de la persona termina en FECHA (primer día que ya no pertenece); repetible")
            else:
                s.add_argument("--cancelar", action="append", required=True, metavar="PERSONA:TIPO:FECHA",
                               help="cancela la operación programada de ese TIPO (alta, traslado, cambio_de_rol, "
                                    "traslado_y_cambio_de_rol o finalizacion) con efecto en FECHA; repetible")
                s.add_argument("--finalizar", action="append", default=[], metavar="PERSONA:FECHA",
                               help="en la misma operación, registra una finalización nueva (sustitución)")
            s.add_argument("--cambio", action="append", default=[], metavar="PERSONA:EQUIPO:ROL:FECHA",
                           help="en la misma operación, registra un traslado o cambio de rol (por ejemplo, el relevo de un supervisor)")
        elif nombre == "registrar-traslado":
            s.add_argument("--cambio", action="append", required=True, metavar="PERSONA:EQUIPO:ROL:FECHA",
                           help="desde FECHA la persona pertenece al equipo con ese rol; repetible (un relevo son dos cambios)")
        elif nombre == "crear-equipo":
            s.add_argument("--organizacion", required=True)
            s.add_argument("--nombre", required=True)
        else:
            s.add_argument("--nombre", required=True)
            s.add_argument("--identificador-acceso", required=True)
            s.add_argument("--equipo", required=True)
            s.add_argument("--rol", required=True)
            s.add_argument("--desde", required=True)
    return p


def _presentador(salida):
    """Muestra el código en la terminal, una sola vez. Es lo ÚNICO que lo escribe: no pasa por el JSON de resultado ni por el de errores."""
    def presentar(codigo: str, caduca_en) -> None:
        print(f"\nCódigo de un solo uso (se muestra UNA vez y no puede volver a verse; comuníquelo en directo):\n\n    {codigo}\n\n"
              f"Caduca el {caduca_en.isoformat()}. Si se pierde, emita uno nuevo.\n", file=salida, flush=True)
    return presentar


def _ejecutar(args, *, entorno, pedir, interactivo, motor_provision: Engine | None, motor_propietario: Engine | None, reloj,
              salida=None, terminal: bool = False, confirmar=input) -> dict:
    invocacion = uuid.uuid4()
    if args.orden in EMISION:
        # ANTES de leer ninguna credencial o de tocar la base: el código solo se muestra en una terminal interactiva (entrada y salida).
        if not ((interactivo if interactivo is not None else _hay_terminal()) and terminal):
            raise ErrorDeProvision("TERMINAL_INTERACTIVA_REQUERIDA")
    if args.orden == "crear-primer-operador":
        from app.db import get_owner_engine
        credencial = leer_credencial(entorno, pedir, interactivo, confirmar=True)
        with (motor_propietario or get_owner_engine()).begin() as c:
            evidencia = verificar_conexion_de_instalacion(c)
            operador = operadores.crear_primer_operador(c, args.identificador, credencial, invocacion)
        return {"orden": args.orden, "operador_id": str(operador.id), "identificador": operador.identificador,
                "invocacion": str(invocacion), **evidencia}

    from app.db import get_provision_engine
    verificacion = None
    if args.orden == "emitir-codigo-recuperacion":
        verificacion = emision.validar_verificacion(args.procedimiento, args.referencia)
        # Elegir una opción no equivale a haber verificado la identidad: la persona operadora lo DECLARA expresamente.
        declaracion = confirmar(f"Declaro que he verificado la identidad de la persona por {verificacion.procedimiento} "
                                f"(referencia {verificacion.referencia}). Escriba {CONFIRMACION} para continuar: ")
        if declaracion.strip() != CONFIRMACION:
            raise ErrorDeProvision("VERIFICACION_NO_DECLARADA")
    credencial = leer_credencial(entorno, pedir, interactivo)
    parametros = {}
    if args.orden in EMISION:
        parametros = {"persona_id": _uuid(args.persona, "persona")}
    elif args.orden == "crear-equipo":
        parametros = {"organizacion_id": _uuid(args.organizacion, "organizacion"), "nombre": args.nombre}
    elif args.orden == "registrar-traslado":
        parametros = {"cambios": [_cambio(valor, i) for i, valor in enumerate(args.cambio)]}
    elif args.orden == "desactivar-acceso":
        parametros = {"persona_id": _uuid(args.persona, "persona"), "motivo": args.motivo}
    elif args.orden == "finalizar-pertenencia":
        parametros = {"finalizaciones": [_finalizacion(v, i) for i, v in enumerate(args.finalizar)],
                      "cambios": [_cambio(v, i) for i, v in enumerate(args.cambio)]}
    elif args.orden == "cancelar-operacion-programada":
        parametros = {"cancelaciones": [_cancelacion(v, i) for i, v in enumerate(args.cancelar)],
                      "finalizaciones": [_finalizacion(v, i) for i, v in enumerate(args.finalizar)],
                      "cambios": [_cambio(v, i) for i, v in enumerate(args.cambio)]}
    elif args.orden in ("purgar-eventos-autenticacion", "purgar-codigos"):
        parametros = {}
    else:
        parametros = {"nombre": args.nombre, "identificador_acceso": args.identificador_acceso,
                      "equipo_id": _uuid(args.equipo, "equipo"), "rol": args.rol, "desde": _fecha(args.desde, "desde")}
    motor = motor_provision or get_provision_engine()
    # La identificación (con su control de intentos) se confirma por separado: un fallo deja su rastro aunque la orden se rechace, y
    # no hay transacción abierta mientras se calcula Argon2. La orden en sí sigue siendo una sola transacción: todo o nada.
    operador = operadores.autenticar(motor, args.operador, credencial, verificar_conexion_de_provision)
    presentado = []
    try:
        return _orden_en_transaccion(args, motor, operador, parametros, invocacion, reloj, salida, verificacion, presentado)
    except ErrorDeProvision:
        raise
    except Exception:
        if presentado:          # el código llegó a mostrarse y después falló la confirmación: no es válido, hay que emitir otro
            raise ErrorDeProvision("CODIGO_NO_CONFIRMADO") from None
        raise


def _orden_en_transaccion(args, motor, operador, parametros, invocacion, reloj, salida, verificacion, presentado) -> dict:
    with motor.begin() as c:
        evidencia = verificar_conexion_de_provision(c)
        operadores.sigue_activo(c, operador)
        if args.orden in EMISION:
            mostrar = _presentador(salida)

            def presentar(codigo, caduca_en):
                mostrar(codigo, caduca_en)
                presentado.append(True)
            r = emision.emitir_codigo(c, operador, finalidad=EMISION[args.orden], verificacion=verificacion, presentar=presentar,
                                      invocacion=invocacion, **parametros)
            resultado = {"persona_id": str(r.persona_id), "finalidad": r.finalidad, "codigo_id": str(r.codigo_id),
                         "caduca_en": r.caduca_en.isoformat(), "codigo_anterior_invalidado": r.codigo_anterior_invalidado,
                         **({"verificacion": {"procedimiento": r.verificacion.procedimiento, "referencia": r.verificacion.referencia,
                                              "declarada_por_la_persona_operadora": True}} if r.verificacion else {})}
        elif args.orden == "purgar-eventos-autenticacion":
            r = eventos.purgar_eventos_de_autenticacion(c, operador, invocacion=invocacion, reloj=reloj)
            resultado = {"eventos_purgados": r.purgados, "anteriores_a": r.anteriores_a.isoformat(), "retencion_dias": r.retencion_dias}
        elif args.orden == "purgar-codigos":
            r = registro_de_codigos.purgar_codigos_terminados(c, invocacion=invocacion)
            resultado = {"codigos_purgados": r.purgados, "anteriores_a": r.anteriores_a.isoformat(), "retencion_dias": r.retencion_dias}
        elif args.orden == "crear-equipo":
            r = servicio.crear_equipo(c, operador, invocacion=invocacion, **parametros)
            resultado = {"equipo_id": str(r.equipo_id), "organizacion_id": str(r.organizacion_id), "nombre": r.nombre}
        elif args.orden == "registrar-traslado":
            r = servicio.registrar_traslado(c, operador, invocacion=invocacion, reloj=reloj, **parametros)
            resultado = {
                "cambios": [{"persona_id": str(a.persona_id), "tipo": a.tipo, "equipo_anterior_id": str(a.equipo_anterior_id),
                             "rol_anterior": a.rol_anterior, "equipo_id": str(a.equipo_id), "rol": a.rol,
                             "fecha_efectiva": a.fecha_efectiva.isoformat()} for a in r.cambios],
                "historiales": _historiales(r.historiales),
            }
        elif args.orden == "desactivar-acceso":
            r = acceso.desactivar_acceso(c, operador, invocacion=invocacion, reloj=reloj, **parametros)
            resultado = {"persona_id": str(r.persona_id), "acceso_desactivado_en": r.desactivado_en.isoformat(),
                         "sesiones_revocadas": r.sesiones_revocadas, "advertencias": [a.como_dict() for a in r.advertencias]}
        elif args.orden in ("finalizar-pertenencia", "cancelar-operacion-programada"):
            funcion = programacion.finalizar_pertenencia if args.orden == "finalizar-pertenencia" else programacion.cancelar_operacion_programada
            r = funcion(c, operador, invocacion=invocacion, reloj=reloj, **parametros)
            resultado = {
                "operacion": r.operacion,
                "canceladas": [{"persona_id": str(x.persona_id), "tipo": x.tipo, "fecha_efectiva": x.fecha_efectiva.isoformat()} for x in r.canceladas],
                "nuevas": [{"persona_id": str(x.persona_id), "tipo": x.tipo, "fecha_efectiva": x.fecha_efectiva.isoformat(),
                            **({"equipo_id": str(x.equipo_id), "rol": x.rol} if x.equipo_id else {})} for x in r.nuevas],
                "historiales": _historiales(r.historiales),
            }
        else:
            r = servicio.crear_persona(c, operador, invocacion=invocacion, reloj=reloj, **parametros)
            resultado = {"persona_id": str(r.persona_id), "equipo_id": str(r.equipo_id), "rol": r.rol,
                         "desde": r.desde.isoformat(), "sin_contrasena": r.sin_contrasena}
    return {"orden": args.orden, "operador_id": str(operador.id), "invocacion": str(invocacion), **evidencia, **resultado}


def main(argv: list[str] | None = None, *, entorno=os.environ, pedir=getpass.getpass, interactivo: bool | None = None,
         salida=None, error=None, motor_provision: Engine | None = None, motor_propietario: Engine | None = None,
         reloj=servicio.ahora_utc, confirmar=input, salida_terminal: bool | None = None) -> int:
    salida, error = salida or sys.stdout, error or sys.stderr
    terminal = salida_terminal if salida_terminal is not None else bool(getattr(salida, "isatty", lambda: False)())
    try:
        args = _parser().parse_args(argv)
    except SystemExit as fin:  # argparse ya escribió el uso; no se propaga
        return CODIGO_RECHAZO if fin.code else 0
    try:
        resultado = _ejecutar(args, entorno=entorno, pedir=pedir, interactivo=interactivo, motor_provision=motor_provision,
                              motor_propietario=motor_propietario, reloj=reloj, salida=salida, terminal=terminal, confirmar=confirmar)
    except ErrorDeProvision as e:
        print(json.dumps(e.como_dict()), file=error)
        return {"CONEXION_NO_PERMITIDA": CODIGO_CONEXION, "DEMASIADOS_INTENTOS": CODIGO_ESPERA}.get(e.codigo, CODIGO_RECHAZO)
    except Exception as e:  # noqa: BLE001 - nunca se imprime el texto de la excepción: podría contener valores
        print(json.dumps({"error": "ERROR_INTERNO", "tipo": type(e).__name__}), file=error)
        return CODIGO_INTERNO
    print(json.dumps(resultado), file=salida)
    return 0
