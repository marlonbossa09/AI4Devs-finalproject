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

IR-11 y CA-78 (interpretación confirmada, PA-27): al registrar un avance nuevo solo se mira el
avance que quedaría justo antes; si es una finalización, hace falta una reactivación. Los avances
posteriores ya existentes no se revalidan ni se modifican, así que un retroactivo Completada anterior
a otro posterior En progreso se acepta y el estado actual sigue siendo el del posterior (el del último
avance del orden laboral completo). Una corrección (M3-03) no debe introducir violaciones nuevas y no se rechaza por esos pares (PA-29).
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


def finalizacion_vigente(avances: list[AvanceEnSecuencia]) -> AvanceEnSecuencia | None:
    """La finalización que determina el estado actual: el último avance del orden laboral completo, si es
    Completada (M3-04, decisión de T10). Una finalización anterior ya superada por otro avance no cuenta."""
    if not avances:
        return None
    ultimo = ordenar(avances)[-1]
    return ultimo if ultimo.estado == COMPLETADA else None


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


# ================================== M3-03: corregir un avance (PA-29, opción A) ==================================

@dataclass(frozen=True, order=True)
class Violacion:
    """Un incumplimiento de IR-11 en la secuencia, identificado por el avance que lo sufre y por su motivo.
    Dos violaciones iguales antes y después de una corrección son LA MISMA situación preexistente."""

    avance_id: UUID
    motivo: str


AVANCE_TRAS_FINALIZACION = "avance_tras_finalizacion_sin_reactivacion"
REACTIVACION_SIN_FINALIZACION = "reactivacion_sin_finalizacion"
REACTIVACION_COMPLETADA = "reactivacion_con_estado_completada"


def violaciones(avances: list[AvanceEnSecuencia]) -> frozenset[Violacion]:
    """Recorre la secuencia completa en orden (IR-11): tras un avance Completada el único válido es una
    reactivación con estado distinto de Completada, y una reactivación solo puede seguir a un Completada.
    No altera nada: una secuencia con pares admitidos por una inserción retroactiva (PA-27) devuelve esas
    violaciones tal cual, y es quien compara antes y después la que decide (``violaciones_nuevas``)."""
    resultado: set[Violacion] = set()
    previo: AvanceEnSecuencia | None = None
    for avance in ordenar(avances):
        tras_finalizacion = previo is not None and previo.estado == COMPLETADA
        if avance.es_reactivacion:
            if not tras_finalizacion:
                resultado.add(Violacion(avance.id, REACTIVACION_SIN_FINALIZACION))
            if avance.estado == COMPLETADA:
                resultado.add(Violacion(avance.id, REACTIVACION_COMPLETADA))
        elif tras_finalizacion:
            resultado.add(Violacion(avance.id, AVANCE_TRAS_FINALIZACION))
        previo = avance
    return frozenset(resultado)


def con_estado_corregido(avances: list[AvanceEnSecuencia], avance_id: UUID, estado: str) -> list[AvanceEnSecuencia]:
    """Copia de la secuencia con el estado de un avance cambiado. No modifica el original, no reordena (el orden
    no depende del estado) ni crea avances: una corrección nunca genera una reactivación (RN-93, CA-239)."""
    return [
        AvanceEnSecuencia(a.id, a.fecha_laboral, a.registrado_en, estado, a.es_reactivacion) if a.id == avance_id else a
        for a in avances
    ]


def violaciones_nuevas(antes: list[AvanceEnSecuencia], despues: list[AvanceEnSecuencia]) -> list[Violacion]:
    """Violaciones que la secuencia de ``despues`` tiene y la de ``antes`` no tenía (PA-29, opción A). Las que ya
    existían y la corrección no modifica ni agrava no la rechazan por sí solas."""
    return sorted(violaciones(despues) - violaciones(antes))
