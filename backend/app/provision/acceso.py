"""Desactivación del acceso de una persona (M1-08; modelo de datos IR-37, DD-04, DD-05, RA-12 y DM-09; decisión P6).

Caso de uso independiente de la CLI y de cualquier transporte. Recibe una conexión ya dentro de UNA transacción (quien llama la abre y
la confirma o la deshace): una orden rechazada no deja cambios ni auditoría.

Qué hace, todo en la misma transacción:

- Fija ``persona.acceso_desactivado_en`` con la hora de la base de datos. Desde ese instante el servidor rechaza TODA petición
  autenticada de la persona, también las de sesiones ya emitidas (IR-37 se comprueba en cada petición, no solo al autenticar).
- Revoca todas sus sesiones (``sesion.revocada_en``), de modo que ninguna sigue siendo válida.
- Deja UNA entrada de auditoría de provisión con el motivo (obligatorio, P6), el valor anterior y el nuevo, las sesiones revocadas
  y las advertencias de supervisión.

Qué NO hace: no toca pertenencias, equipos, personas ni registros laborales; no asigna supervisores sustitutos ni transfiere permisos
(RA-12); no crea ningún estado persistente nuevo y no reactiva ningún acceso (M1-10 no existe).

DM-09: la persona puede ser el único supervisor efectivo de un equipo y la orden NO se bloquea (DD-04). Si deja a un equipo
«pendiente de supervisión efectiva» (con colaboradores en la fecha actual y su supervisor asignado sin acceso efectivo), esa condición,
DERIVADA de las reglas de supervisión (``linea_temporal.supervision_en``), se informa como advertencia estructurada en el resultado y en
la auditoría.

Serialización: se toma el bloqueo consultivo de la persona que también toma el inicio de sesión (``smartwork:acceso:persona:<id>``), de
modo que un inicio de sesión simultáneo ve la desactivación confirmada (y se rechaza) o termina antes de que se revoquen las
sesiones (y su sesión se revoca): no queda ninguna sesión válida por una carrera.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import Connection, text

from app.config import get_settings
from app.provision.errores import ErrorDeProvision
from app.provision.linea_temporal import Tramo, supervision_en
from app.provision.operadores import Operador
from app.provision.servicio import Reloj, _auditar, _bloquear_en_orden, _fecha_actual, ahora_utc
from app.seguridad.control_de_intentos import registrar_evento

ADVERTENCIA_EQUIPO_PENDIENTE = "EQUIPO_PENDIENTE_DE_SUPERVISION_EFECTIVA"


@dataclass(frozen=True)
class EquipoPendiente:
    """DM-09: un equipo con colaboradores en la fecha actual cuyo supervisor asignado ya no tiene acceso efectivo."""

    equipo_id: uuid.UUID
    equipo: str
    colaboradores: int
    supervisor_id: uuid.UUID
    supervisor_hasta_exclusivo: date | None   # fin de la asignación del supervisor (vacío = sin fin); si hay fecha, hay un relevo ya programado

    def como_dict(self) -> dict:
        return {"codigo": ADVERTENCIA_EQUIPO_PENDIENTE, "equipo_id": str(self.equipo_id), "equipo": self.equipo,
                "colaboradores": self.colaboradores, "supervisor_id": str(self.supervisor_id),
                "supervisor_hasta_exclusivo": self.supervisor_hasta_exclusivo.isoformat() if self.supervisor_hasta_exclusivo else None}


@dataclass(frozen=True)
class AccesoDesactivado:
    invocacion: uuid.UUID
    persona_id: uuid.UUID
    desactivado_en: datetime
    sesiones_revocadas: int
    advertencias: tuple[EquipoPendiente, ...]


def _motivo(valor: str | None) -> str:
    """P6: el motivo es obligatorio, recortado (los espacios exteriores no cuentan) y con el máximo configurable (D-03)."""
    limpio = (valor or "").strip()
    if not limpio:
        raise ErrorDeProvision("CAMPO_OBLIGATORIO", [{"campo": "motivo", "motivo": "vacio"}])
    if len(limpio) > get_settings().text_max_description:
        raise ErrorDeProvision("TEXTO_DEMASIADO_LARGO", [{"campo": "motivo", "motivo": "demasiado_largo"}])
    return limpio


def desactivar_acceso(conexion: Connection, operador: Operador, *, persona_id: uuid.UUID, motivo: str | None,
                      reloj: Reloj = ahora_utc, invocacion: uuid.UUID | None = None) -> AccesoDesactivado:
    """M1-08. Desactiva de inmediato el acceso de la persona y revoca todas sus sesiones, sin tocar pertenencias ni registros."""
    invocacion = invocacion or uuid.uuid4()
    motivo = _motivo(motivo)

    # 1. Serializa con el inicio de sesión y con cualquier otra orden sobre la persona (siempre en este orden).
    _bloquear_en_orden(conexion, [f"smartwork:acceso:persona:{persona_id}", f"smartwork:pertenencias:persona:{persona_id}"])
    persona = conexion.execute(text("select id, acceso_desactivado_en from persona where id = :p"), {"p": persona_id}).one_or_none()
    if persona is None:
        raise ErrorDeProvision("RECURSO_NO_DISPONIBLE", [{"campo": "persona"}])
    if persona.acceso_desactivado_en is not None:
        raise ErrorDeProvision("ACCESO_YA_DESACTIVADO")   # solicitud repetida: se rechaza de forma explícita, sin cambios ni entrada

    # 2. DM-09: ¿deja la desactivación a algún equipo pendiente de supervisión efectiva? Se calcula ANTES de cambiar nada, con la
    # supervisión asignada hoy (zona de la organización, reloj inyectable) y las personas sin acceso efectivo después de esta orden.
    advertencias = _equipos_pendientes(conexion, persona_id, reloj)

    # 3. El efecto: acceso desactivado con la hora de la base de datos y todas las sesiones revocadas, en la misma transacción.
    desactivado = conexion.execute(
        text("update persona set acceso_desactivado_en = now() where id = :p and acceso_desactivado_en is null returning acceso_desactivado_en"),
        {"p": persona_id}).all()
    if len(desactivado) != 1:
        raise ErrorDeProvision("ACCESO_YA_DESACTIVADO")
    desactivado_en = desactivado[0][0]
    revocadas = conexion.execute(
        text("update sesion set revocada_en = now() where revocada_en is null "
             "and identidad_id in (select id from identidad where persona_id = :p)"), {"p": persona_id}).rowcount
    # Los códigos de un solo uso pendientes de esta persona dejan de valer en la misma transacción (M1-T8.2): una emisión que ya estuviera
    # en curso se serializó con esta orden por el bloqueo de la persona, y una desactivación nunca deja un código vivo.
    codigos_invalidados = conexion.execute(
        text("update codigo_unico set invalidado_en = clock_timestamp() where usado_en is null and invalidado_en is null "
             "and identidad_id in (select id from identidad where persona_id = :p)"), {"p": persona_id}).rowcount

    if revocadas > 0:
        # Evento técnico de autenticación (A11, M1-T7), en la misma transacción que la revocación. Sin el motivo (va en la auditoría).
        registrar_evento(conexion, "revocacion_por_desactivacion", persona_id=persona_id,
                         detalle={"sesiones_revocadas": revocadas, "invocacion": str(invocacion)})

    # 4. IR-34 e IR-35: una entrada de provisión con el motivo; sin credenciales ni identificadores de acceso.
    _auditar(
        conexion, operador, invocacion, tipo_objeto="persona", objeto_id=persona_id, propietaria=persona_id,
        operacion="desactivacion_acceso", motivo=motivo,
        valor_anterior={"acceso_desactivado_en": None},
        valor_nuevo={"acceso_desactivado_en": desactivado_en.isoformat(), "sesiones_revocadas": revocadas,
                     "advertencias": [a.como_dict() for a in advertencias],
                     **({"codigos_invalidados": codigos_invalidados} if codigos_invalidados else {})},
    )
    return AccesoDesactivado(invocacion, persona_id, desactivado_en, revocadas, advertencias)


def _equipos_pendientes(conexion: Connection, persona_id: uuid.UUID, reloj: Reloj) -> tuple[EquipoPendiente, ...]:
    intervalos = conexion.execute(
        text("select p.equipo_id, p.rol, p.desde, p.hasta_exclusivo, o.zona_horaria from pertenencia p "
             "join equipo e on e.id = p.equipo_id join organizacion o on o.id = e.organizacion_id "
             "where p.persona_id = :p order by p.desde"), {"p": persona_id}).all()
    if not intervalos:
        return ()
    hoy = _fecha_actual(intervalos[-1].zona_horaria, reloj)
    vigente = next((i for i in intervalos if Tramo(persona_id, i.rol, i.desde, i.hasta_exclusivo).cubre(hoy)), None)
    if vigente is None or vigente.rol != "supervisor":
        return ()
    equipo = vigente.equipo_id
    _bloquear_en_orden(conexion, [f"smartwork:pertenencias:equipo:{equipo}"])      # la línea temporal del equipo no cambia mientras se calcula
    tramos = [Tramo(f.persona_id, f.rol, f.desde, f.hasta_exclusivo) for f in conexion.execute(
        text("select persona_id, rol, desde, hasta_exclusivo from pertenencia where equipo_id = :e"), {"e": equipo})]
    sin_acceso = {f.id for f in conexion.execute(
        text("select id from persona where acceso_desactivado_en is not null and id = any(cast(:ids as uuid[]))"),
        {"ids": list({t.persona_id for t in tramos})})} | {persona_id}
    estado = supervision_en(tramos, hoy, sin_acceso)
    if not estado.pendiente or estado.supervisor != persona_id:
        return ()
    nombre = conexion.execute(text("select nombre from equipo where id = :e"), {"e": equipo}).scalar_one()
    return (EquipoPendiente(equipo, nombre, estado.colaboradores, persona_id, vigente.hasta_exclusivo),)
