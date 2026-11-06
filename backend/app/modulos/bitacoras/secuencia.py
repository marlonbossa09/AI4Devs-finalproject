"""Dominio de la secuencia de avances y del estado actual de una actividad (M2-05, HU-2.8, HU-2.9).

Reglas puras, sin acceso a la base de datos, para poder probarlas de forma aislada:

- **Orden total (IR-09, CA-74 a CA-76):** fecha laboral de la bitácora, momento real de registro e
  identificador estable. La fecha laboral manda: un avance de un martes es posterior a uno del
  lunes aunque se haya registrado antes.
- **Estado actual (IR-12, RN-66):** el del último avance de la secuencia, y Pendiente si la
  actividad no tiene avances. La planificación, incluida la continuación futura, nunca interviene
  (IR-14, CA-185, CA-186).
- **Avance tras una finalización (RN-73, RN-79, CA-190, CA-206, CA-207):** si, según la secuencia,
  el avance nuevo quedaría justo después de un avance Completada, se rechaza hasta que la
  actividad se reactive (M3-04, fuera de esta entrega). Rige tanto para el último avance como para
  un hueco entre una finalización y una reactivación posterior.
- **Avance retroactivo anterior a una finalización (RN-77, CA-203 a CA-205):** se acepta sin
  reactivar, se inserta en su posición histórica y no sustituye el estado de un avance posterior
  (CA-78).

Diferencia documentada con IR-11: leída al pie de la letra, IR-11 exigiría que a un avance
Completada siempre le siga una reactivación. CA-78 y el contrato M2-05 aceptan un avance
retroactivo Completada anterior a otro posterior En progreso y fijan que el estado actual sigue
siendo el del posterior. Aquí se aplica el criterio de aceptación y el contrato.
"""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

ESTADO_INICIAL = "Pendiente"
COMPLETADA = "Completada"
BLOQUEADA = "Bloqueada"
ESTADOS = (ESTADO_INICIAL, "En progreso", BLOQUEADA, COMPLETADA)


@dataclass(frozen=True)
class AvanceEnSecuencia:
    """Lo mínimo de un avance que interviene en el orden y en el estado actual."""

    id: UUID
    fecha_laboral: date
    registrado_en: datetime
    estado: str
    es_reactivacion: bool = False


def clave_de_orden(avance: AvanceEnSecuencia) -> tuple[date, datetime, UUID]:
    return (avance.fecha_laboral, avance.registrado_en, avance.id)


def ordenar(avances: list[AvanceEnSecuencia]) -> list[AvanceEnSecuencia]:
    return sorted(avances, key=clave_de_orden)


def estado_actual(avances: list[AvanceEnSecuencia]) -> str:
    """Estado del último avance de la secuencia; Pendiente si no hay ninguno."""
    return ordenar(avances)[-1].estado if avances else ESTADO_INICIAL


def _precedente_de_un_avance_nuevo(avances: list[AvanceEnSecuencia], fecha_laboral: date) -> AvanceEnSecuencia | None:
    """Avance que quedaría justo antes del nuevo. El servidor asigna al nuevo el momento de registro
    más reciente, así que, a igual fecha laboral, queda después de todos los existentes."""
    anteriores = [a for a in ordenar(avances) if a.fecha_laboral <= fecha_laboral]
    return anteriores[-1] if anteriores else None


def quedaria_tras_una_finalizacion(avances: list[AvanceEnSecuencia], fecha_laboral: date) -> bool:
    """¿El avance nuevo (no reactivación) quedaría justo después de un avance Completada?"""
    precedente = _precedente_de_un_avance_nuevo(avances, fecha_laboral)
    return precedente is not None and precedente.estado == COMPLETADA


def estado_actual_tras_insertar(avances: list[AvanceEnSecuencia], fecha_laboral: date, estado: str) -> str:
    """Estado actual de la actividad una vez insertado un avance nuevo de [fecha_laboral].

    Si el avance queda al final de la secuencia, su estado pasa a ser el actual; si es retroactivo
    (existe uno con fecha laboral posterior), el estado actual no cambia (CA-78)."""
    hay_posterior = any(a.fecha_laboral > fecha_laboral for a in avances)
    return estado_actual(avances) if hay_posterior else estado
