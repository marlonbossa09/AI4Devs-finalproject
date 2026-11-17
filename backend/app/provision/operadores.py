"""Personas operadoras de provisión (ADR-002, sección 9, opción C; decisión A7 del 2026-11-11).

Cada orden exige identificarse como persona operadora con su identificador y su credencial, aunque se tenga acceso al
servidor: tener acceso al servidor no equivale a tener autorización administrativa. No hay sesión persistente: la
credencial se verifica en cada invocación. Solo se guarda el hash Argon2id. Una persona operadora no es un rol funcional.

Intentos fallidos (M1-T7, decisiones del 2026-11-17): ``autenticar`` aplica la MISMA curva de espera que a las personas, con un
contador SEPARADO (por identificador, sin origen), y registra eventos técnicos de autenticación. No deshabilita nunca a la persona
operadora: solo hay esperas, que caducan. Un identificador desconocido y una credencial incorrecta dan la misma respuesta.

LO QUE ESTE MÓDULO NO RESUELVE TODAVÍA (decisiones del ADR-002 pendientes de aprobación específica; no se inventan valores):
- Alta de las siguientes personas operadoras y control de dos personas (con dos o más operadoras).
- Alta de la primera persona operadora mediante un código de un solo uso (A4): se usa en su lugar un procedimiento de
  instalación con el rol propietario, que además se niega si ya existe alguna.
"""

import json
import uuid
from dataclasses import dataclass

from collections.abc import Callable

from sqlalchemy import Connection, Engine, text

from app.config import get_settings
from app.provision.errores import ErrorDeProvision
from app.seguridad import control_de_intentos as control
from app.seguridad.contrasenas import calcular_hash, hash_senuelo, verificar
from app.seguridad.identificadores import normalizar_identificador


@dataclass(frozen=True)
class Operador:
    id: uuid.UUID
    identificador: str


def validar_credencial(credencial: str) -> None:
    """Política vigente de contraseñas (ADR-002, sección 7, A8): longitud mínima decidida; sin reglas de composición."""
    s = get_settings()
    if len(credencial) < s.password_min_length or len(credencial) > s.login_password_max_length:
        raise ErrorDeProvision("CREDENCIAL_NO_VALIDA", [{"campo": "credencial", "motivo": "longitud"}])


def _identificador_valido(identificador: str) -> str:
    normalizado = normalizar_identificador(identificador or "")
    if not normalizado:
        raise ErrorDeProvision("CAMPO_OBLIGATORIO", [{"campo": "identificador", "motivo": "vacio"}])
    if len(normalizado) > get_settings().login_identifier_max_length:
        raise ErrorDeProvision("TEXTO_DEMASIADO_LARGO", [{"campo": "identificador", "motivo": "demasiado_largo"}])
    return normalizado


def crear_primer_operador(conexion: Connection, identificador: str, credencial: str, invocacion: uuid.UUID) -> Operador:
    """Procedimiento de INSTALACIÓN: crea la primera persona operadora. Se ejecuta con el rol propietario (el rol de
    provisión solo lee ``operador``) y se niega si ya existe alguna. Deja una entrada de auditoría de provisión sin la
    credencial. Atómico: lo llama quien abre la transacción."""
    normalizado = _identificador_valido(identificador)
    validar_credencial(credencial)
    conexion.execute(text("select pg_advisory_xact_lock(hashtextextended('smartwork:operador:instalacion', 0))"))
    if conexion.execute(text("select 1 from operador limit 1")).first() is not None:
        raise ErrorDeProvision("INSTALACION_YA_REALIZADA")
    operador_id = conexion.execute(
        text("insert into operador (identificador, hash_credencial) values (:i, :h) returning id"),
        {"i": normalizado, "h": calcular_hash(credencial)},
    ).scalar_one()
    conexion.execute(
        text("insert into auditoria (tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id, valor_nuevo) "
             "values ('provision', :ref, 'alta', 'operador', :o, cast(:nuevo as jsonb))"),
        {"ref": f"instalacion|invocacion:{invocacion}", "o": operador_id,
         "nuevo": json.dumps({"operador": str(operador_id), "estado": "activo"})},
    )
    return Operador(operador_id, normalizado)


def identificar(conexion: Connection, identificador: str, credencial: str) -> Operador:
    """Identifica a la persona operadora. Un identificador desconocido, una credencial incorrecta y una persona operadora
    revocada producen el MISMO error, y siempre se calcula un hash (con uno señuelo si hace falta)."""
    normalizado = normalizar_identificador(identificador or "")
    fila = conexion.execute(
        text("select id, hash_credencial, estado from operador where identificador = :i"), {"i": normalizado},
    ).one_or_none()
    guardado = fila.hash_credencial if fila is not None else hash_senuelo()
    correcta = verificar(guardado, credencial or "")
    if fila is None or not correcta or fila.estado != "activo":
        raise ErrorDeProvision("OPERADOR_NO_AUTORIZADO")
    return Operador(fila.id, normalizado)


def autenticar(motor: Engine, identificador: str, credencial: str, comprobar_conexion: Callable[[Connection], object]) -> Operador:
    """Identifica a la persona operadora CON control de intentos (M1-T7). Tres tramos, ninguno con una transacción abierta mientras
    se calcula Argon2: (1) reserva del intento y lectura de la fila, (2) verificación del hash, (3) fallo (evento) o acierto
    (reinicio del contador y evento). Cada tramo se confirma por separado, así que un fallo deja su rastro aunque la orden se
    rechace. ``comprobar_conexion`` confirma que la conexión es la del rol de provisión antes de tocar nada."""
    normalizado = normalizar_identificador(identificador or "")
    with motor.begin() as c:
        comprobar_conexion(c)
        reserva = control.reservar_operador(c, normalizado)
        fila = None
        if isinstance(reserva, control.Denegado):
            espera = reserva.espera_segundos
        else:
            espera = None
            fila = c.execute(text("select id, hash_credencial, estado from operador where identificador = :i"), {"i": normalizado}).one_or_none()
    if espera is not None:
        raise ErrorDeProvision("DEMASIADOS_INTENTOS", [{"espera_segundos": espera}])
    guardado = fila.hash_credencial if fila is not None else hash_senuelo()
    correcta = verificar(guardado, credencial or "")
    acierto = fila is not None and correcta and fila.estado == "activo"
    with motor.begin() as c:
        if acierto:
            control.liberar_operador(c, reserva)
            control.registrar_evento(c, "inicio_correcto", ambito=control.AMBITO_OPERADOR, clave_cuenta=reserva.clave)
        else:
            control.registrar_fallo(c, reserva, ambito=control.AMBITO_OPERADOR)
    if not acierto:
        raise ErrorDeProvision("OPERADOR_NO_AUTORIZADO")
    return Operador(fila.id, normalizado)


def sigue_activo(conexion: Connection, operador: Operador) -> None:
    """Dentro de la transacción de la orden: la persona operadora no se revocó entre su identificación y la orden."""
    if conexion.execute(text("select 1 from operador where id = :i and estado = 'activo'"), {"i": operador.id}).first() is None:
        raise ErrorDeProvision("OPERADOR_NO_AUTORIZADO")
