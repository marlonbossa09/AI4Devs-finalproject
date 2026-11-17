"""Casos de uso de provisión sobre operaciones de pertenencia PROGRAMADAS: finalizar una pertenencia (M1-06) y cancelar o
sustituir operaciones que todavía no han surtido efecto (M1-07).

Independientes de la CLI y de cualquier transporte. Cada función recibe una conexión ya dentro de UNA transacción (quien llama
la abre y la confirma o la deshace): una orden rechazada no deja cambios ni auditoría. Las dos comparten un único motor
(``_programar``) porque tienen la misma forma: retirar operaciones programadas (cancelar) y registrar otras nuevas (traslado,
cambio de rol o finalización), todo en la misma operación atómica. Así un relevo de supervisor que se finaliza (CA-240) y la
sustitución de una operación (CA-247) son una sola transacción.

Reglas (modelo de datos IR-02, IR-03, IR-26, IR-28 a IR-32 e IR-39; la parte pura está en ``operaciones_programadas``):

- Solo se modifica lo PROGRAMADO: se cierra o se restituye el fin de un intervalo cuyo fin es posterior a la fecha actual, y se
  borran intervalos cuyo inicio es posterior a ella. El historial efectivo no se toca (IR-30), y la base lo garantiza además
  para el rol de provisión (migración 0011).
- Se valida la línea temporal RESULTANTE completa de cada persona (sin solapes ni huecos) y de cada equipo afectado (como
  máximo un supervisor y exactamente uno mientras haya colaboradores) en toda fecha desde la primera afectada.
- Serialización: se bloquean las personas y después los equipos afectados, siempre ordenados; el bloqueo de equipo es el mismo
  de ``crear_persona`` y ``registrar_traslado``.
- Una única entrada de auditoría por orden (IR-35): ``finalizacion_pertenencia``, ``cancelacion_operacion`` o
  ``sustitucion_operacion``, con los valores anterior y nuevo de todos los intervalos afectados. La entrada de la operación
  original NO se toca (la auditoría es de solo anexado): se identifica por los identificadores de las pertenencias retiradas.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from app.provision.errores import ErrorDeProvision
from app.provision.linea_temporal import Tramo, primera_irregularidad_de_persona, primera_violacion_de_supervision
from app.provision.operaciones_programadas import (
    Incumplimiento, Intervalo, OperacionCancelada, aplicar_cambio, aplicar_finalizacion, cancelar, tipo_de_transicion,
)
from app.provision.operadores import Operador
from app.provision.servicio import (
    ROLES, CambioSolicitado, PertenenciaDelHistorial, Reloj, _auditar, _bloquear_en_orden, _fecha_actual, _restriccion, ahora_utc,
)

RESTRICCIONES_DE_PERTENENCIA = ("pertenencia_un_supervisor_por_equipo_y_fecha", "pertenencia_sin_solape_por_persona",
                                "pertenencia_solo_cambia_lo_programado", "pertenencia_intervalo_valido")


@dataclass(frozen=True)
class FinalizacionSolicitada:
    persona_id: uuid.UUID
    fecha_efectiva: date


@dataclass(frozen=True)
class CancelacionSolicitada:
    """La operación que se cancela se identifica por su persona, su tipo y su fecha efectiva (M1-07)."""

    persona_id: uuid.UUID
    tipo: str
    fecha_efectiva: date


@dataclass(frozen=True)
class OperacionRegistrada:
    persona_id: uuid.UUID
    tipo: str                     # traslado, cambio_de_rol, traslado_y_cambio_de_rol o finalizacion
    fecha_efectiva: date
    equipo_id: uuid.UUID | None   # solo en los cambios
    rol: str | None


@dataclass(frozen=True)
class ProgramacionAplicada:
    invocacion: uuid.UUID
    operacion: str                                                   # finalizacion_pertenencia, cancelacion_operacion o sustitucion_operacion
    canceladas: tuple[CancelacionSolicitada, ...]
    nuevas: tuple[OperacionRegistrada, ...]
    historiales: dict[uuid.UUID, tuple[PertenenciaDelHistorial, ...]]   # el historial COMPLETO de cada persona afectada


def _error(incumplimiento: Incumplimiento, persona: uuid.UUID) -> ErrorDeProvision:
    detalle: dict = {"persona": str(persona), "motivo": incumplimiento.motivo}
    for clave, valor in incumplimiento.extra.items():
        detalle[clave] = valor.isoformat() if isinstance(valor, date) else valor
    if incumplimiento.codigo == "FECHA_EFECTIVA_INVALIDA":
        detalle["campo"] = "fecha_efectiva"
    return ErrorDeProvision(incumplimiento.codigo, [detalle])


def _repetidas(personas: Sequence[uuid.UUID], campo: str) -> None:
    if len(set(personas)) != len(personas):
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": campo, "motivo": "persona_repetida"}])


def finalizar_pertenencia(conexion: Connection, operador: Operador, *, finalizaciones: Sequence[FinalizacionSolicitada],
                          cambios: Sequence[CambioSolicitado] = (), reloj: Reloj = ahora_utc,
                          invocacion: uuid.UUID | None = None) -> ProgramacionAplicada:
    """M1-06. Finaliza la pertenencia de una o más personas con efecto en una fecha futura (CA-258): cierra su último
    intervalo sin fin y no crea otro. ``cambios`` permite, en la MISMA operación atómica, registrar a quien releva a un
    supervisor que se finaliza (CA-240); sin él, finalizar al único supervisor de un equipo con colaboradores se rechaza."""
    if not finalizaciones:
        raise ErrorDeProvision("CAMPO_OBLIGATORIO", [{"campo": "finalizaciones", "motivo": "vacio"}])
    return _programar(conexion, operador, operacion="finalizacion_pertenencia", cancelaciones=(), cambios=cambios,
                      finalizaciones=finalizaciones, reloj=reloj, invocacion=invocacion)


def cancelar_operacion_programada(conexion: Connection, operador: Operador, *, cancelaciones: Sequence[CancelacionSolicitada],
                                  cambios: Sequence[CambioSolicitado] = (), finalizaciones: Sequence[FinalizacionSolicitada] = (),
                                  reloj: Reloj = ahora_utc, invocacion: uuid.UUID | None = None) -> ProgramacionAplicada:
    """M1-07. Cancela operaciones que todavía no han surtido efecto y, opcionalmente, las SUSTITUYE por otras en la misma
    transacción (``cambios`` y ``finalizaciones``). Una operación ya efectiva no se modifica (CA-245). Las operaciones
    relacionadas, como un relevo, se cancelan o sustituyen juntas (IR-39)."""
    if not cancelaciones:
        raise ErrorDeProvision("CAMPO_OBLIGATORIO", [{"campo": "cancelaciones", "motivo": "vacio"}])
    sustituye = bool(cambios or finalizaciones)
    return _programar(conexion, operador, operacion="sustitucion_operacion" if sustituye else "cancelacion_operacion",
                      cancelaciones=cancelaciones, cambios=cambios, finalizaciones=finalizaciones, reloj=reloj, invocacion=invocacion)


def _programar(conexion: Connection, operador: Operador, *, operacion: str, cancelaciones: Sequence[CancelacionSolicitada],
               cambios: Sequence[CambioSolicitado], finalizaciones: Sequence[FinalizacionSolicitada], reloj: Reloj,
               invocacion: uuid.UUID | None) -> ProgramacionAplicada:
    invocacion = invocacion or uuid.uuid4()
    cancelaciones, cambios, finalizaciones = list(cancelaciones), list(cambios), list(finalizaciones)
    _repetidas([c.persona_id for c in cambios], "cambios")
    _repetidas([f.persona_id for f in finalizaciones], "finalizaciones")
    for i, c in enumerate(cambios):
        if c.rol not in ROLES:
            raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"campo": "cambios", "indice": i, "motivo": "rol_no_valido"}])
    personas = list(dict.fromkeys([*(c.persona_id for c in cancelaciones), *(c.persona_id for c in cambios),
                                   *(f.persona_id for f in finalizaciones)]))

    # 1. Las personas, en orden. Con su bloqueo nadie más cambia sus pertenencias hasta el final de la transacción.
    _bloquear_en_orden(conexion, [f"smartwork:pertenencias:persona:{p}" for p in personas])
    existentes = {f.id for f in conexion.execute(text("select id from persona where id = any(cast(:ids as uuid[]))"), {"ids": personas})}
    for persona in personas:
        if persona not in existentes:
            raise ErrorDeProvision("RECURSO_NO_DISPONIBLE", [{"campo": "persona", "persona": str(persona)}])
    lineas: dict[uuid.UUID, list[Intervalo]] = {p: [] for p in personas}
    for f in conexion.execute(
        text("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia "
             "where persona_id = any(cast(:ids as uuid[])) order by persona_id, desde"), {"ids": personas}):
        lineas[f.persona_id].append(Intervalo(f.id, f.equipo_id, f.rol, f.desde, f.hasta_exclusivo))

    equipos = {i.equipo for linea in lineas.values() for i in linea} | {c.equipo_id for c in cambios}
    datos_equipo = {f.id: f for f in conexion.execute(
        text("select e.id, e.nombre, e.organizacion_id, o.zona_horaria from equipo e "
             "join organizacion o on o.id = e.organizacion_id where e.id = any(cast(:ids as uuid[]))"), {"ids": list(equipos)})}
    for i, c in enumerate(cambios):
        if c.equipo_id not in datos_equipo:
            raise ErrorDeProvision("RECURSO_NO_DISPONIBLE", [{"campo": "equipo", "indice": i}])

    # 2. La línea resultante de cada persona, en memoria y antes de escribir nada.
    por_cambio = {c.persona_id: c for c in cambios}
    por_final = {f.persona_id: f for f in finalizaciones}
    canceladas_de: dict[uuid.UUID, list[CancelacionSolicitada]] = {}
    for c in cancelaciones:
        canceladas_de.setdefault(c.persona_id, []).append(c)

    resultados: dict[uuid.UUID, list[Intervalo]] = {}
    detalle_cancelado: dict[uuid.UUID, list[OperacionCancelada]] = {}
    tipo_del_cambio: dict[uuid.UUID, str] = {}
    for persona in personas:
        linea = lineas[persona]
        if not linea:
            if persona in canceladas_de:
                raise ErrorDeProvision("RECURSO_NO_DISPONIBLE", [{"campo": "operacion", "persona": str(persona), "motivo": "operacion_no_encontrada"}])
            raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"persona": str(persona), "motivo": "sin_pertenencia"}])
        organizacion = datos_equipo[linea[-1].equipo].organizacion_id
        hoy = _fecha_actual(datos_equipo[linea[-1].equipo].zona_horaria, reloj)
        try:
            actual = linea
            if persona in canceladas_de:
                actual, detalle_cancelado[persona] = cancelar(actual, hoy, [(c.tipo, c.fecha_efectiva) for c in canceladas_de[persona]])
            if persona in por_cambio:
                c = por_cambio[persona]
                if datos_equipo[c.equipo_id].organizacion_id != organizacion:
                    raise Incumplimiento("PERTENENCIA_INVALIDA", "otra_organizacion")
                actual = aplicar_cambio(actual, hoy, c.equipo_id, c.rol, c.fecha_efectiva)
                nuevo = next(i for i in actual if i.id is None)
                tipo_del_cambio[persona] = tipo_de_transicion(actual[actual.index(nuevo) - 1], nuevo)
            if persona in por_final:
                actual = aplicar_finalizacion(actual, hoy, por_final[persona].fecha_efectiva)
        except Incumplimiento as incumplimiento:
            raise _error(incumplimiento, persona) from incumplimiento
        irregularidad = primera_irregularidad_de_persona([Tramo(persona, i.rol, i.desde, i.hasta) for i in actual])
        if irregularidad is not None:       # defensa: cierre, restitución y apertura producen siempre una línea contigua
            raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"persona": str(persona), "motivo": irregularidad}])
        resultados[persona] = actual

    # 3. Qué cambia exactamente en la base de datos.
    borrar: list[tuple[uuid.UUID, Intervalo]] = []
    actualizar: list[tuple[uuid.UUID, Intervalo, Intervalo]] = []
    insertar: list[tuple[uuid.UUID, Intervalo]] = []
    desde_control: dict[uuid.UUID, date] = {}

    def afectar(equipo: uuid.UUID, fecha: date) -> None:
        desde_control[equipo] = min(desde_control.get(equipo, fecha), fecha)

    for persona in personas:
        originales = {i.id: i for i in lineas[persona]}
        finales = {i.id for i in resultados[persona] if i.id is not None}
        for i in lineas[persona]:
            if i.id not in finales:
                borrar.append((persona, i))
                afectar(i.equipo, i.desde)
        for nuevo in resultados[persona]:
            if nuevo.id is None:
                insertar.append((persona, nuevo))
                afectar(nuevo.equipo, nuevo.desde)
            elif originales[nuevo.id].hasta != nuevo.hasta:
                actualizar.append((persona, originales[nuevo.id], nuevo))
                afectar(nuevo.equipo, min(f for f in (originales[nuevo.id].hasta, nuevo.hasta) if f is not None))
    if not (borrar or actualizar or insertar):
        raise ErrorDeProvision("SOLICITUD_INVALIDA", [{"campo": "operaciones", "motivo": "sin_efecto"}])

    # 4. Los equipos afectados, también en orden, y su línea temporal completa leída DESPUÉS de bloquearlos (IR-03, IR-32).
    _bloquear_en_orden(conexion, [f"smartwork:pertenencias:equipo:{e}" for e in desde_control])
    filas_equipo: dict[uuid.UUID, dict] = {e: {} for e in desde_control}
    for f in conexion.execute(
        text("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia "
             "where equipo_id = any(cast(:ids as uuid[]))"), {"ids": list(desde_control)}):
        filas_equipo[f.equipo_id][f.id] = {"persona": f.persona_id, "rol": f.rol, "desde": f.desde, "hasta": f.hasta_exclusivo}
    for _, i in borrar:
        filas_equipo[i.equipo].pop(i.id, None)
    for _, antes, despues in actualizar:
        filas_equipo[despues.equipo][despues.id]["hasta"] = despues.hasta
    for persona, i in insertar:
        filas_equipo[i.equipo][uuid.uuid4()] = {"persona": persona, "rol": i.rol, "desde": i.desde, "hasta": i.hasta}
    for equipo in sorted(desde_control, key=str):
        violacion = primera_violacion_de_supervision(
            [Tramo(f["persona"], f["rol"], f["desde"], f["hasta"]) for f in filas_equipo[equipo].values()], desde_control[equipo])
        if violacion is not None:
            motivo = "el_equipo_quedaria_sin_supervisor" if violacion.motivo == "sin_supervisor" else "el_equipo_tendria_mas_de_un_supervisor"
            raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"campo": "equipo", "equipo": str(equipo), "motivo": motivo,
                                                              "fecha": violacion.fecha.isoformat()}])

    # 5. Se aplica: borrados, después fines, después aperturas (las exclusiones se comprueban sentencia a sentencia).
    nuevos_ids: dict[tuple, uuid.UUID] = {}
    try:
        for _, i in borrar:
            if len(conexion.execute(text("delete from pertenencia where id = :i returning id"), {"i": i.id}).all()) != 1:
                raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"motivo": "la_pertenencia_ya_no_existe"}])
        for _, antes, despues in actualizar:
            cambiadas = conexion.execute(
                text("update pertenencia set hasta_exclusivo = cast(:nuevo as date) where id = :i "
                     "and hasta_exclusivo is not distinct from cast(:antes as date) returning id"),
                {"nuevo": despues.hasta, "antes": antes.hasta, "i": despues.id}).all()
            if len(cambiadas) != 1:
                raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"motivo": "la_pertenencia_cambio"}])
        for persona, i in insertar:
            nuevos_ids[(persona, i.desde)] = conexion.execute(
                text("insert into pertenencia (persona_id, equipo_id, rol, desde, hasta_exclusivo) "
                     "values (:p, :e, :r, :d, cast(:h as date)) returning id"),
                {"p": persona, "e": i.equipo, "r": i.rol, "d": i.desde, "h": i.hasta}).scalar_one()
        conexion.execute(text("set constraints pertenencia_supervision_del_equipo immediate"))
    except IntegrityError as error:
        restriccion = _restriccion(error)
        if restriccion == "pertenencia_supervision_del_equipo":
            raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"campo": "equipo", "motivo": "la_supervision_del_equipo_no_se_cumple"}]) from error
        if restriccion in RESTRICCIONES_DE_PERTENENCIA:
            raise ErrorDeProvision("PERTENENCIA_INVALIDA", [{"motivo": "restriccion_de_la_base_de_datos"}]) from error
        raise

    # 6. IR-35: UNA entrada con los valores anterior y nuevo de todo lo afectado. La operación original no se toca: se
    # identifica por los ids de las pertenencias retiradas, presentes en el ``valor_nuevo`` de su propia entrada.
    def intervalo(i: Intervalo, persona: uuid.UUID, id_=None) -> dict:
        return {"id": str(id_ or i.id), "persona": str(persona), "equipo": str(i.equipo), "rol": i.rol, "desde": i.desde.isoformat(),
                "hasta_exclusivo": i.hasta.isoformat() if i.hasta else None}

    canceladas_audit = [{"persona": str(p), "tipo": d.tipo, "fecha_efectiva": d.fecha.isoformat(),
                         "pertenencias_retiradas": [str(r.id) for r in d.retirados]}
                        for p in personas for d in detalle_cancelado.get(p, [])]
    nuevas: list[OperacionRegistrada] = []
    nuevas_audit = []
    for persona in personas:
        if persona in por_cambio:
            c = por_cambio[persona]
            nuevas.append(OperacionRegistrada(persona, tipo_del_cambio[persona], c.fecha_efectiva, c.equipo_id, c.rol))
        if persona in por_final:
            nuevas.append(OperacionRegistrada(persona, "finalizacion", por_final[persona].fecha_efectiva, None, None))
    for o in nuevas:
        nuevas_audit.append({"persona": str(o.persona_id), "tipo": o.tipo, "fecha_efectiva": o.fecha_efectiva.isoformat(),
                             **({"equipo": str(o.equipo_id), "rol": o.rol} if o.equipo_id else {})})
    _auditar(
        conexion, operador, invocacion, tipo_objeto="operacion_de_pertenencia", objeto_id=invocacion, propietaria=None,
        operacion=operacion,
        valor_anterior={"operaciones_canceladas": canceladas_audit,
                        "pertenencias_retiradas": [intervalo(i, p) for p, i in borrar],
                        "fines_anteriores": [{"id": str(a.id), "persona": str(p), "hasta_exclusivo": a.hasta.isoformat() if a.hasta else None}
                                             for p, a, _ in actualizar]},
        valor_nuevo={"operaciones_canceladas": canceladas_audit, "operaciones_nuevas": nuevas_audit,
                     "fines_nuevos": [{"id": str(d.id), "persona": str(p), "hasta_exclusivo": d.hasta.isoformat() if d.hasta else None}
                                      for p, _, d in actualizar],
                     "pertenencias_nuevas": [intervalo(i, p, nuevos_ids[(p, i.desde)]) for p, i in insertar]},
    )

    # 7. El historial completo de cada persona afectada: los intervalos anteriores, intactos, y lo que cambió.
    historiales: dict[uuid.UUID, list[PertenenciaDelHistorial]] = {p: [] for p in personas}
    for f in conexion.execute(
        text("select p.persona_id, p.id, p.equipo_id, e.nombre, p.rol, p.desde, p.hasta_exclusivo from pertenencia p "
             "join equipo e on e.id = p.equipo_id where p.persona_id = any(cast(:ids as uuid[])) order by p.persona_id, p.desde"),
        {"ids": personas}):
        historiales[f.persona_id].append(PertenenciaDelHistorial(f.id, f.equipo_id, f.nombre, f.rol, f.desde, f.hasta_exclusivo))
    return ProgramacionAplicada(invocacion, operacion, tuple(cancelaciones), tuple(nuevas), {p: tuple(h) for p, h in historiales.items()})
