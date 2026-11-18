"""M4-03 — vista de supervisión del equipo en un período (``GET /api/v1/equipo/supervision``). Núcleo (M4-T3) y herencia entre equipos (M4-T4).

SOLO el supervisor vigente con acceso efectivo (RA-12, RN-13); un colaborador recibe 403 ``OPERACION_NO_PERMITIDA`` (convenciones 3.1). Solo lectura. Orden de evaluación
(convenciones 3.2): sesión y puede operar (dependencia ``operador``), FORMATO de los parámetros, permiso de supervisión y, solo entonces, los datos.

**Qué decide cada capa.** La política de visibilidad de M1 (``app.compartido.visibilidad``) decide TODO lo que es autorización: la pertenencia al equipo (``condicion_equipo`` y
``pertenencia_del_equipo`` en SQL, ``pertenece_al_equipo_en`` en Python), la forma de una actividad (``forma_en_supervision``), si el estado al corte se puede mostrar
(``estado_al_corte_es_visible``) y si se puede informar el estado actual (``puede_ver_estado_actual``). Este módulo solo reúne esos HECHOS, aplica la secuencia de avances y las
reglas de inclusión de RN-47, y construye la respuesta. No contiene ninguna regla de pertenencia ni de autorización propia. El filtro se aplica al SELECCIONAR (convenciones 3.3):
totales, estado al corte, orden y cursor se calculan solo sobre lo que se puede mostrar.

**Inclusión (D-06, D-M4-03 a D-M4-06, RN-47).** El corte es ``hasta``. Una actividad (no marcada por error: RA-08, CA-147) se incluye si: tiene una planificación o avances
autorizados en el período (``planificada_en_el_periodo``, ``con_avances_en_el_periodo``), o no estaba completada al corte y su propietaria pertenece al equipo en la fecha de corte
(``pendiente_al_corte``). Puede tener varios motivos. Una completada antes del período sin avances en él no entra (CA-141). Incluye las propias del supervisor (CA-142). Una
planificación CONSERVADA (fecha no cubierta por una pertenencia de su propietaria) no es de ningún equipo: nunca cuenta ni se muestra (CA-274, D-M4-07).

**Formas de un elemento (``tipo``).**
- ``actividad`` con ``ActividadVisible`` ``completa``: el origen de la actividad es del equipo (título y origen autorizados, RA-04).
- ``actividad`` con ``ActividadVisible`` ``neutral``: actividad HEREDADA (origen en otro equipo) sobre la que el equipo tiene registros propios (planificaciones o avances
  autorizados hasta el corte). Se identifica con «Actividad en continuidad» y nunca se revela su título original (RN-101, CA-272, CA-301).
- ``referencia_minima``: actividad heredada SIN registros del equipo, pendiente al corte y de una propietaria del equipo (RN-47, RN-84, D-09): solo propietaria, «iniciada en otro
  equipo», estado actual y, si el último avance es del equipo, su fecha (RA-06, CA-218 a CA-220, CA-232). Se distingue del acceso completo (RN-89). Si el estado actual no se puede
  informar (la propietaria ya no es del equipo) la referencia NO se emite: falla cerrado (CA-221).

**Estado al corte (RA-07, RN-88).** Es el del último avance con fecha laboral ≤ corte según la secuencia válida completa (``secuencia.ordenar``), o Pendiente si no hay ninguno; una
continuación planificada posterior no interviene (CA-198). Solo se muestra si ese avance está autorizado (o, sin avances, si el origen lo está); si lo determina otro equipo se OMITE
(CA-230) y no se sustituye por un avance anterior autorizado. Con un avance autorizado se muestra sin revelar los anteriores protegidos (CA-231). **Estado actual:** solo si la
propietaria pertenece hoy al equipo (D-M4-05): ``estado_actual_si_difiere`` solo cuando el estado al corte se muestra y difiere del actual (CA-143, CA-144, CA-222). Si el estado al
corte no se puede mostrar, el campo se OMITE: sin un estado al corte visible no se puede establecer la diferencia y no hay una representación independiente aprobada del estado actual.

**Totales, orden y cursor sin filtraciones.** ``totales_por_estado`` cuenta solo los elementos CON estado al corte mostrado, antes de paginar. Los que no lo tienen (referencias mínimas y
actividades con el estado al corte no autorizado) se cuentan aparte en ``sin_estado_al_corte`` y nunca entran en ``totales_por_estado``: así ningún agregado revela un estado oculto.
El orden es: los cuatro estados al corte, después las actividades sin estado al corte y por último las referencias mínimas; dentro de cada grupo, propietaria e identificador. La clave
del grupo es exactamente lo que el propio elemento muestra, así que ni el orden ni el cursor revelan nada más.

**Límite conocido.** Para decidir si una actividad heredada sigue «pendiente al corte» (RN-47) hay que saber si estaba completada al corte; ese único dato (completada o no) se usa para
incluirla aunque su estado al corte no se pueda mostrar. Es lo que RN-47 exige y se documenta como riesgo residual en el plan de M4.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido import paginacion, visibilidad
from app.compartido.dependencias import Operador
from app.compartido.visibilidad import Consultante, consultante_de, puede_ver_estado_actual
from app.errores import AppError
from app.modulos.bitacoras import secuencia
from app.modulos.bitacoras.secuencia import AvanceEnSecuencia
from app.modulos.consulta import proyecciones, repositorio

PARAMETROS_DE_LA_SUPERVISION = frozenset({"desde", "hasta", "limite", "continuar_desde"})
PLANIFICADA, CON_AVANCES, PENDIENTE = "planificada_en_el_periodo", "con_avances_en_el_periodo", "pendiente_al_corte"
GRUPO_SIN_ESTADO, GRUPO_REFERENCIA = "sin_estado_al_corte", "referencia_minima"
GRUPOS = (*secuencia.ESTADOS, GRUPO_SIN_ESTADO, GRUPO_REFERENCIA)


def _grupo_valido(valor: str) -> str:
    if valor not in GRUPOS:
        raise ValueError("grupo")
    return valor


@dataclass(frozen=True)
class _Incluida:
    fila: object
    forma: str
    motivos: list[str]
    estado_real: str                      # solo para decidir la inclusión y, si procede, mostrarlo; NUNCA se usa si ``estado_visible`` es falso
    estado_visible: bool
    fecha_ultimo_avance: date | None      # solo si el último avance de la actividad está autorizado

    @property
    def grupo(self) -> str:
        if self.forma == visibilidad.EN_SUPERVISION_REFERENCIA_MINIMA:
            return GRUPO_REFERENCIA
        return self.estado_real if self.estado_visible else GRUPO_SIN_ESTADO

    @property
    def clave(self) -> tuple[int, UUID, UUID]:
        return (GRUPOS.index(self.grupo), self.fila.propietaria_id, self.fila.id)


def consultar_supervision(db: Session, op: Operador, consulta: list[tuple[str, str]]) -> dict:
    parametros = paginacion.leer_parametros(consulta, PARAMETROS_DE_LA_SUPERVISION)      # ``corte`` u otro: SOLICITUD_INVALIDA (D-06)
    desde, hasta = paginacion.rango_de_fechas(parametros)
    cantidad = paginacion.limite_de(parametros.get("limite"))
    cursor = paginacion.leer_cursor(parametros.get("continuar_desde"), _grupo_valido, UUID, UUID)

    consultante: Consultante = consultante_de(db, op.persona_id, hoy=op.contexto.fecha_actual)
    if not consultante.es_supervisor_vigente:                                            # RN-13, RA-12: nadie más supervisa
        raise AppError("OPERACION_NO_PERMITIDA")

    candidatas = repositorio.actividades_candidatas(db, consultante, desde, hasta)
    ids = [c.id for c in candidatas]
    avances: dict[UUID, list] = {}
    for a in repositorio.avances_de_las_actividades(db, consultante, ids):
        avances.setdefault(a.actividad_id, []).append(a)
    con_planificacion = repositorio.actividades_con_planificacion_autorizada(db, consultante, ids, hasta)

    ve_estado_actual: dict[UUID, bool] = {}

    def estado_actual_visible(propietaria_id: UUID) -> bool:
        if propietaria_id not in ve_estado_actual:
            ve_estado_actual[propietaria_id] = puede_ver_estado_actual(db, consultante, propietaria_id)
        return ve_estado_actual[propietaria_id]

    incluidas: list[_Incluida] = []
    for c in candidatas:
        propios = avances.get(c.id, [])
        autorizado_de = {v.id: v.autorizado for v in propios}
        todos = secuencia.ordenar([AvanceEnSecuencia(v.id, v.fecha_laboral, v.registrado_en, v.estado, v.es_reactivacion) for v in propios])
        al_corte = [v for v in todos if v.fecha_laboral <= hasta]
        ultimo = al_corte[-1] if al_corte else None                                       # el que determina el estado al corte (RA-07)
        estado_real = ultimo.estado if ultimo else secuencia.ESTADO_INICIAL
        estado_visible = visibilidad.estado_al_corte_es_visible(ultimo is not None, bool(ultimo and autorizado_de[ultimo.id]), c.origen_autorizado)
        registros_del_equipo = c.id in con_planificacion or any(autorizado_de[v.id] for v in al_corte)
        motivos = [m for m, cumple in ((PLANIFICADA, c.por_planificacion), (CON_AVANCES, c.por_avances),
                                       (PENDIENTE, c.en_el_equipo_al_corte and estado_real != secuencia.COMPLETADA)) if cumple]
        if not motivos:
            continue
        forma = visibilidad.forma_en_supervision(c.origen_autorizado, registros_del_equipo)
        if forma == visibilidad.EN_SUPERVISION_REFERENCIA_MINIMA and not estado_actual_visible(c.propietaria_id):
            continue                                                                      # la referencia exige el estado actual: si no se puede informar, no se emite (CA-221)
        ultimo_de_todos = todos[-1] if todos else None
        fecha_ultimo = ultimo_de_todos.fecha_laboral if ultimo_de_todos and autorizado_de[ultimo_de_todos.id] else None
        incluidas.append(_Incluida(c, forma, motivos, estado_real, estado_visible, fecha_ultimo))

    totales = {e: 0 for e in secuencia.ESTADOS}
    sin_estado = {"referencias_minimas": 0, "actividades": 0}
    for i in incluidas:
        if i.grupo == GRUPO_REFERENCIA:
            sin_estado["referencias_minimas"] += 1
        elif i.grupo == GRUPO_SIN_ESTADO:
            sin_estado["actividades"] += 1
        else:
            totales[i.estado_real] += 1
    incluidas.sort(key=lambda i: i.clave)                                                 # grupo, propietaria e identificador (convenciones 6.1)
    if cursor is not None:
        posicion = (GRUPOS.index(cursor[0]), cursor[1], cursor[2])
        incluidas = [i for i in incluidas if i.clave > posicion]
    pagina = incluidas[:cantidad]

    elementos = [_elemento(i, estado_actual_visible(i.fila.propietaria_id)) for i in pagina]
    ultimo_elemento = pagina[-1] if pagina else None
    return {
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "corte": hasta.isoformat(),
        "totales_por_estado": totales,
        "sin_estado_al_corte": sin_estado,
        "elementos": elementos,
        "siguiente": paginacion.emitir_cursor(ultimo_elemento.grupo, str(ultimo_elemento.fila.propietaria_id), str(ultimo_elemento.fila.id))
        if ultimo_elemento and len(incluidas) > cantidad else None,
    }


def _elemento(i: _Incluida, ve_estado_actual: bool) -> dict:
    a = i.fila
    if i.forma == visibilidad.EN_SUPERVISION_REFERENCIA_MINIMA:
        return proyecciones.referencia_minima(a, estado_actual=a.estado_actual, fecha_ultimo_avance=i.fecha_ultimo_avance)
    elemento = {
        "tipo": "actividad",
        "actividad": (proyecciones.actividad_completa(a, a.fecha_laboral_origen, con_estado_actual=False) if i.forma == visibilidad.EN_SUPERVISION_COMPLETA
                      else proyecciones.actividad_neutral(a)),
        "propietaria_id": str(a.propietaria_id),
        "motivo_inclusion": i.motivos,
    }
    if i.estado_visible:
        elemento["estado_al_corte"] = i.estado_real
    if i.estado_visible and ve_estado_actual and a.estado_actual != i.estado_real:
        elemento["estado_actual_si_difiere"] = a.estado_actual                          # solo si hay estado al corte visible, difiere y la propietaria es del equipo hoy (D-M4-05; CA-143, CA-144, CA-222)
    return elemento
