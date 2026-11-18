"""Estructura de campos CERRADOS y armado de hechos comunes a los informes individual y consolidado (M5-T1 y M5-T2). Una sola definición de hecho, actividad y bloqueo para los dos, de modo que
las agregaciones (``agregaciones.py``) signifiquen lo mismo en ambos y puedan contrastarse cuando sus poblaciones coinciden.

Nada de este módulo decide autorización: recibe filas YA autorizadas por la consulta SQL (``repositorio``, con los predicados de ``app.compartido.visibilidad``) y el predicado ya compuesto para
el estado al corte. Ver ``individual.py`` para el texto no confiable (RN-31) y las medidas de seudonimización posterior (M5-T3), que valen igual para el consolidado.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido.visibilidad import Consultante
from app.errores import AppError
from app.modulos.informes import repositorio

# Texto fijo de la referencia neutral (RN-101). Una sola decisión de producto: una prueba comprueba que coincide con la de M4.
REFERENCIA_NEUTRAL = "Actividad en continuidad"
COMPLETA, NEUTRAL = "completa", "neutral"
BLOQUEADA = "Bloqueada"

CAMPOS_DE_TEXTO_LIBRE = {"Hecho": ("descripcion", "motivo_bloqueo"), "ActividadDelInforme": ("texto (solo si forma es completa: es el título)",)}
CAMPOS_PARA_EL_GENERADOR = {
    "informe": ("tipo", "periodo", "persona (como alias)", "hechos", "bloqueos", "agregaciones"),
    "consolidado": ("tipo", "periodo", "personas (cada una como alias, con sus actividades, hechos, bloqueos y agregaciones)", "agregaciones_del_equipo"),
    "hecho": ("ref", "fecha_laboral", "actividad_ref", "estado", "descripcion", "motivo_bloqueo"),
    "actividad": ("ref", "forma", "texto", "planificada"),
}


@dataclass(frozen=True)
class Persona:
    id: UUID
    nombre: str


@dataclass(frozen=True)
class ActividadDelInforme:
    """Una actividad referenciada por algún hecho. ``texto`` es su título si el consultante está autorizado sobre su jornada de origen (``completa``) o la referencia neutral (``neutral``).
    ``planificada`` es el origen de la actividad (``True`` planificada, ``False`` no planificada) solo si ese origen está autorizado; si no, ``None``: el origen de una actividad iniciada
    en otro equipo no se revela (RN-101). ``id`` es para la respuesta pública y NO debe salir hacia un generador."""

    ref: str
    id: UUID
    forma: str
    texto: str
    planificada: bool | None


@dataclass(frozen=True)
class Hecho:
    """Un avance autorizado del período. ``estado`` es el estado histórico de ese avance. ``motivo_bloqueo`` solo si el estado es Bloqueada."""

    ref: str
    fecha_laboral: date
    actividad_ref: str
    estado: str
    descripcion: str
    motivo_bloqueo: str | None


@dataclass(frozen=True)
class Bloqueo:
    """Un avance en estado Bloqueada con su motivo (RF-74, RN-55, CA-165). Una entrada por avance bloqueado: si una actividad se bloquea en dos jornadas, aparecen dos (P-3, provisional)."""

    hecho_ref: str
    actividad_ref: str
    fecha_laboral: date
    motivo: str


class Numerador:
    """Referencias opacas ``h1``, ``h2``… y ``a1``, ``a2``… ÚNICAS en todo el informe (también entre las personas del consolidado). No son identificadores de la base de datos."""

    def __init__(self) -> None:
        self.hechos = 0
        self.actividades = 0


def exigir_que_puede_operar(consultante: Consultante) -> None:
    """Paso 2 del orden de evaluación (convenciones 3.2)."""
    if not consultante.acceso_activo:
        raise AppError("ACCESO_DESACTIVADO")
    if consultante.pertenencia is None:
        raise AppError("SIN_PERTENENCIA_VIGENTE")


def exigir_periodo_valido(desde: date, hasta: date) -> None:
    """Paso 3: formato, sin consultar nada (no revela existencia). La amplitud máxima es un parámetro pendiente (D-M5-06) y no se aplica aquí."""
    if desde > hasta:
        raise AppError("SOLICITUD_INVALIDA", [{"campo": "desde", "motivo": "posterior_a_hasta"}])


def construir_bloque(filas, numerador: Numerador) -> tuple[dict[UUID, ActividadDelInforme], list[Hecho], tuple[Bloqueo, ...]]:
    """Hechos, actividades y bloqueos de un conjunto de avances ya autorizados y ordenados por la secuencia. Una actividad cuyo origen NO está autorizado sale en forma neutral, sin título ni
    origen (RN-101); su origen nunca se infiere."""
    actividades: dict[UUID, ActividadDelInforme] = {}
    hechos: list[Hecho] = []
    for f in filas:
        if f.actividad_id not in actividades:
            neutral = not f.origen_autorizado
            numerador.actividades += 1
            actividades[f.actividad_id] = ActividadDelInforme(
                ref=f"a{numerador.actividades}", id=f.actividad_id, forma=NEUTRAL if neutral else COMPLETA,
                texto=REFERENCIA_NEUTRAL if neutral else f.titulo, planificada=None if neutral else f.origen == "planificada")
        numerador.hechos += 1
        hechos.append(Hecho(f"h{numerador.hechos}", f.fecha_laboral, actividades[f.actividad_id].ref, f.estado, f.descripcion, f.motivo_bloqueo))
    bloqueos = tuple(Bloqueo(h.ref, h.actividad_ref, h.fecha_laboral, h.motivo_bloqueo) for h in hechos if h.estado == BLOQUEADA)
    return actividades, hechos, bloqueos


def estados_al_corte(db: Session, actividades: list[UUID], hasta: date, autorizado: tuple[str, dict]) -> dict[UUID, str | None]:
    """Estado al corte (``hasta``) de cada actividad: el del último avance hasta el corte, SOLO si está autorizado según el predicado recibido (RA-07, RN-88); si no, ``None`` (no disponible). Un
    avance protegido nunca se sustituye por uno anterior."""
    ultimos = repositorio.ultimo_avance_hasta_el_corte(db, actividades, hasta, autorizado)
    return {u.actividad_id: (u.estado if u.autorizado else None) for u in ultimos}
