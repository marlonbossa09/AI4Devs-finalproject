"""Agregaciones deterministas de los informes (RF-46, RF-51, RN-26, RN-29). Definiciones **decididas por la persona responsable para M5-T1 (2026-11-18)**: el catálogo completo (D-M5-04)
y sus valores siguen pendientes de aprobación formal, así que el contrato las mantiene `[PROPUESTO]` hasta entonces.

Son recuentos sobre los hechos YA autorizados (nunca sobre filas sin filtrar), sin IA, sin porcentajes (RN-57) y sin ordenar ni puntuar personas (RF-47). Con los mismos hechos dan siempre el
mismo resultado (CA-164). Un «registro» del informe es un AVANCE autorizado del período (contrato M5, ``hechos``; ADR-003, sección 7): una planificación sin avances no cuenta.

Definiciones (sobre ``hechos``, una tupla de avances autorizados, y ``actividades``, las que esos avances referencian):

| Campo | Definición |
|---|---|
| ``avances`` | cantidad de avances autorizados en el período |
| ``jornadas_con_registros`` | fechas laborales distintas con avances autorizados |
| ``actividades_con_registros`` | actividades distintas con avances autorizados |
| ``actividades_por_origen`` | ``planificadas``, ``no_planificadas`` y ``origen_no_disponible``. Un origen protegido (forma neutral) NUNCA se infiere: va a ``origen_no_disponible`` |
| ``actividades_con_bloqueo`` | actividades con algún avance autorizado en estado Bloqueada durante el período |
| ``actividades_por_estado_al_corte`` | SOLO las actividades con avances autorizados en el período. El corte es ``hasta`` (RF-70). El estado de cada una es el del último avance hasta el corte según la secuencia válida completa, y solo se informa si ese avance está autorizado (RA-07, RN-88); si lo determina un avance protegido (o no puede demostrarse), la actividad va a ``estado_no_disponible`` y NO se sustituye por el estado de un avance anterior. No incluye las actividades pendientes de M4-03 |

Invariante: los cinco grupos de ``actividades_por_estado_al_corte`` suman ``actividades_con_registros``.

Agregaciones de EQUIPO (consolidado, M5-T2): son estas mismas definiciones aplicadas al conjunto de todos los hechos autorizados del equipo; por tanto ``avances``, las actividades y los grupos
son la suma de los de las personas y ``jornadas_con_registros`` son las fechas laborales distintas del conjunto (no la suma de las de cada persona).
"""

from dataclasses import dataclass

BLOQUEADA = "Bloqueada"
ESTADOS = ("Pendiente", "En progreso", "Bloqueada", "Completada")


@dataclass(frozen=True)
class ActividadesPorOrigen:
    planificadas: int
    no_planificadas: int
    origen_no_disponible: int


@dataclass(frozen=True)
class ActividadesPorEstadoAlCorte:
    pendiente: int
    en_progreso: int
    bloqueada: int
    completada: int
    estado_no_disponible: int


@dataclass(frozen=True)
class Agregaciones:
    avances: int
    jornadas_con_registros: int
    actividades_con_registros: int
    actividades_por_origen: ActividadesPorOrigen
    actividades_con_bloqueo: int
    actividades_por_estado_al_corte: ActividadesPorEstadoAlCorte


def calcular(hechos, actividades, estado_al_corte: dict[str, str | None]) -> Agregaciones:
    """``hechos`` y ``actividades`` son los ya autorizados del informe (``Hecho`` y ``ActividadDelInforme``). ``estado_al_corte`` asocia la referencia de cada actividad con su estado al corte,
    o ``None`` si no puede informarse. Una actividad sin entrada se trata como no disponible: falla cerrado."""
    con_hechos = {h.actividad_ref for h in hechos}
    de_origen = [a for a in actividades if a.ref in con_hechos]
    estados = [estado_al_corte.get(ref) for ref in con_hechos]
    return Agregaciones(
        avances=len(hechos),
        jornadas_con_registros=len({h.fecha_laboral for h in hechos}),
        actividades_con_registros=len(con_hechos),
        actividades_por_origen=ActividadesPorOrigen(
            planificadas=sum(1 for a in de_origen if a.planificada is True),
            no_planificadas=sum(1 for a in de_origen if a.planificada is False),
            origen_no_disponible=sum(1 for a in de_origen if a.planificada is None),
        ),
        actividades_con_bloqueo=len({h.actividad_ref for h in hechos if h.estado == BLOQUEADA}),
        actividades_por_estado_al_corte=ActividadesPorEstadoAlCorte(
            pendiente=estados.count("Pendiente"), en_progreso=estados.count("En progreso"), bloqueada=estados.count("Bloqueada"),
            completada=estados.count("Completada"), estado_no_disponible=sum(1 for e in estados if e not in ESTADOS)),
    )
