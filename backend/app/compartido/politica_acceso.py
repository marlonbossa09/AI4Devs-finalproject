"""Política de acceso centralizada (BE-02, subconjunto de la Entrega 2).

Único punto que decide si una persona puede operar y si una fecha laboral le corresponde. Los
módulos no reimplementan estas comprobaciones. Solo cubre lo que necesitan las operaciones
sobre registros propios (``/mi/...``). La visibilidad histórica entre equipos está en
``app.compartido.visibilidad`` (M1-T1) y todavía no la usa ninguna operación; ambas comparten la
definición de «equipo en una fecha» de ``app.compartido.pertenencias``.

Reglas aplicadas:
- IR-37: con ``acceso_desactivado_en`` informado se rechaza toda operación, con independencia
  de las credenciales o sesiones anteriores (``ACCESO_DESACTIVADO``).
- IR-38: sin pertenencia que cubra la fecha actual no se opera (``SIN_PERTENENCIA_VIGENTE``).
- IR-29: no se crea ni se escribe en una fecha laboral no cubierta por una pertenencia
  (``FECHA_NO_CUBIERTA``).
La «fecha actual» la calcula el servidor en la zona horaria de la organización (DM-06).
"""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido.pertenencias import pertenencia_en_fecha
from app.errores import AppError


@dataclass(frozen=True)
class Contexto:
    """Persona que opera, con su situación vigente."""

    persona_id: UUID
    nombre: str
    rol_vigente: str
    zona_horaria: str
    fecha_actual: date


def fecha_actual_en(zona_horaria: str) -> date:
    return datetime.now(ZoneInfo(zona_horaria)).date()


def contexto_de_operacion(db: Session, persona_id: UUID) -> Contexto:
    """Evalúa los pasos 2 del orden de evaluación: acceso no desactivado y pertenencia vigente."""
    persona = db.execute(
        # clock_timestamp() y no now(): ``now()`` es el inicio de la TRANSACCIÓN, y una transacción iniciada antes de que se confirmara
        # una desactivación (por ejemplo, un inicio de sesión que verifica la contraseña) no la vería. IR-37: desde ese momento.
        text("select nombre, (acceso_desactivado_en is not null and acceso_desactivado_en <= clock_timestamp()) "
             "as desactivado from persona where id = :p"),
        {"p": persona_id},
    ).one_or_none()
    if persona is None or persona.desactivado:
        # Una persona inexistente no puede tener sesión; se trata igual que un acceso no válido.
        raise AppError("ACCESO_DESACTIVADO")

    # Zona horaria de la organización de la última pertenencia de la persona
    zona = db.execute(
        text("select o.zona_horaria from pertenencia p "
             "join equipo e on e.id = p.equipo_id join organizacion o on o.id = e.organizacion_id "
             "where p.persona_id = :p order by p.desde desc limit 1"),
        {"p": persona_id},
    ).scalar_one_or_none()
    if zona is None:
        raise AppError("SIN_PERTENENCIA_VIGENTE")

    hoy = fecha_actual_en(zona)
    vigente = pertenencia_en_fecha(db, persona_id, hoy)  # DM-04: la única definición de «pertenencia en una fecha»
    if vigente is None:
        raise AppError("SIN_PERTENENCIA_VIGENTE")
    return Contexto(persona_id, persona.nombre, vigente.rol, zona, hoy)


def fecha_cubierta(db: Session, persona_id: UUID, fecha: date) -> bool:
    """IR-29: la fecha laboral está cubierta por un intervalo de pertenencia de la persona."""
    return pertenencia_en_fecha(db, persona_id, fecha) is not None
