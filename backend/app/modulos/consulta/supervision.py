"""M4-03 (núcleo, M4-T3) — vista de supervisión del equipo en un período (``GET /api/v1/equipo/supervision``).

SOLO el supervisor vigente con acceso efectivo (RA-12, RN-13); un colaborador recibe 403 ``OPERACION_NO_PERMITIDA`` (convenciones 3.1). Solo lectura. Orden de evaluación
(convenciones 3.2): sesión y puede operar (dependencia ``operador``), FORMATO de los parámetros, permiso de supervisión y, solo entonces, los datos.

**Autorización.** Todo lo que se lee se selecciona con ``visibilidad.condicion_equipo`` (la misma definición de pertenencia que el resto de la política, sin la rama «es la propia
consultante»): el equipo de la propietaria EN LA FECHA del registro es el del supervisor (RA-01). Por eso el filtro se aplica al seleccionar y antes de calcular nada: totales,
estado al corte, orden y cursor se calculan solo sobre registros autorizados (convenciones 3.3). El servicio no contiene ninguna regla de pertenencia propia.

**Reglas implementadas (D-06, D-M4-03 a D-M4-06, RN-47 y RN-48).** El corte es ``hasta``. Una actividad del equipo (no marcada por error, CA-147) se incluye si:
- tiene una planificación (original o continuación) con fecha laboral en el período y autorizada (``planificada_en_el_periodo``, CA-138);
- tiene avances con fecha laboral en el período y autorizados (``con_avances_en_el_periodo``, CA-139); o
- no estaba completada al corte y su propietaria pertenece al equipo en la fecha de corte (``pendiente_al_corte``, CA-140). Una completada antes del período sin avances en él no
  entra (CA-141). Incluye las propias del supervisor (CA-142).
Puede tener más de un motivo. El **estado al corte** es el del último avance con fecha laboral ≤ corte, con la secuencia válida completa (orden de ``secuencia.ordenar``), o
Pendiente si no hay ninguno; una continuación planificada posterior no interviene (CA-198). El **estado actual** solo se informa, aparte, si difiere y la propietaria pertenece HOY al
equipo del supervisor (``puede_ver_estado_actual``, D-M4-05, CA-143 y CA-144). ``totales_por_estado`` cuenta todas las actividades incluidas del período, no solo la página. Sin
clasificaciones, rankings ni puntuaciones de personas (CA-145). Una planificación CONSERVADA (fecha no cubierta por una pertenencia de su propietaria: DM-08, D-M4-07) no es del
equipo de nadie: nunca cuenta ni se muestra (CA-274).

**Falla cerrado (lo que necesita M4-T4).** Una actividad solo se muestra si su jornada de origen y TODOS los avances que determinan su estado al corte están autorizados. Si el
origen es de otro equipo (actividad heredada: forma neutral o referencia mínima) o el último avance hasta el corte es de otro equipo (CA-230), la actividad NO aparece, ni en la lista
ni en los totales: nada de otro equipo se expone y no se inventa un estado al corte. La referencia mínima y el recuento aparte de referencias mínimas (D-M4-06) llegan con M4-T4.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido import paginacion
from app.compartido.dependencias import Operador
from app.compartido.visibilidad import Consultante, consultante_de, puede_ver_estado_actual
from app.errores import AppError
from app.modulos.bitacoras import secuencia
from app.modulos.bitacoras.secuencia import AvanceEnSecuencia
from app.modulos.consulta import proyecciones, repositorio

PARAMETROS_DE_LA_SUPERVISION = frozenset({"desde", "hasta", "limite", "continuar_desde"})
PLANIFICADA, CON_AVANCES, PENDIENTE = "planificada_en_el_periodo", "con_avances_en_el_periodo", "pendiente_al_corte"


def estado_al_corte(avances: list[AvanceEnSecuencia], autorizados: dict[UUID, bool]) -> tuple[str, bool]:
    """``(estado, autorizado)``: el estado de la actividad al corte según los avances con fecha laboral ≤ corte (ya filtrados por quien llama) y si el avance que lo determina
    está autorizado. Sin avances, Pendiente y autorizado (no deriva de ningún registro de otro equipo). Una continuación planificada posterior no interviene (IR-14)."""
    if not avances:
        return secuencia.ESTADO_INICIAL, True
    ultimo = secuencia.ordenar(avances)[-1]
    return ultimo.estado, autorizados[ultimo.id]


def _estado_valido(valor: str) -> str:
    if valor not in secuencia.ESTADOS:
        raise ValueError("estado")
    return valor


@dataclass(frozen=True)
class _Incluida:
    fila: object
    motivos: list[str]
    estado_al_corte: str

    @property
    def clave(self) -> tuple[int, UUID, UUID]:
        return (secuencia.ESTADOS.index(self.estado_al_corte), self.fila.propietaria_id, self.fila.id)


def consultar_supervision(db: Session, op: Operador, consulta: list[tuple[str, str]]) -> dict:
    parametros = paginacion.leer_parametros(consulta, PARAMETROS_DE_LA_SUPERVISION)      # ``corte`` u otro: SOLICITUD_INVALIDA (D-06)
    desde, hasta = paginacion.rango_de_fechas(parametros)
    cantidad = paginacion.limite_de(parametros.get("limite"))
    cursor = paginacion.leer_cursor(parametros.get("continuar_desde"), _estado_valido, UUID, UUID)

    consultante: Consultante = consultante_de(db, op.persona_id, hoy=op.contexto.fecha_actual)
    if not consultante.es_supervisor_vigente:                                            # RN-13, RA-12: nadie más supervisa
        raise AppError("OPERACION_NO_PERMITIDA")

    candidatas = repositorio.actividades_candidatas(db, consultante, desde, hasta)
    avances: dict[UUID, list] = {}
    for a in repositorio.avances_hasta_el_corte(db, consultante, [c.id for c in candidatas], hasta):
        avances.setdefault(a.actividad_id, []).append(a)

    incluidas: list[_Incluida] = []
    for c in candidatas:
        propios = avances.get(c.id, [])
        estado, autorizado = estado_al_corte(
            [AvanceEnSecuencia(v.id, v.fecha_laboral, v.registrado_en, v.estado, v.es_reactivacion) for v in propios], {v.id: v.autorizado for v in propios})
        if not autorizado:
            continue                                                                      # CA-230: lo determina un avance de otro equipo; llega con M4-T4
        motivos = [m for m, cumple in ((PLANIFICADA, c.por_planificacion), (CON_AVANCES, c.por_avances),
                                       (PENDIENTE, c.en_el_equipo_al_corte and estado != secuencia.COMPLETADA)) if cumple]
        if motivos:
            incluidas.append(_Incluida(c, motivos, estado))

    totales = {e: 0 for e in secuencia.ESTADOS}
    for i in incluidas:
        totales[i.estado_al_corte] += 1
    incluidas.sort(key=lambda i: i.clave)                                                 # estado al corte, propietaria e identificador (convenciones 6.1)
    if cursor is not None:
        posicion = (secuencia.ESTADOS.index(cursor[0]), cursor[1], cursor[2])
        incluidas = [i for i in incluidas if i.clave > posicion]
    pagina = incluidas[:cantidad]

    ve_estado_actual: dict[UUID, bool] = {}
    elementos = []
    for i in pagina:
        a = i.fila
        elemento = {
            "tipo": "actividad",
            "actividad": proyecciones.actividad_completa(a, a.fecha_laboral_origen, con_estado_actual=False),
            "propietaria_id": str(a.propietaria_id),
            "motivo_inclusion": i.motivos,
            "estado_al_corte": i.estado_al_corte,
        }
        if a.propietaria_id not in ve_estado_actual:
            ve_estado_actual[a.propietaria_id] = puede_ver_estado_actual(db, consultante, a.propietaria_id)
        if a.estado_actual != i.estado_al_corte and ve_estado_actual[a.propietaria_id]:
            elemento["estado_actual_si_difiere"] = a.estado_actual                      # solo si difiere y la propietaria pertenece hoy al equipo (CA-143, CA-144)
        elementos.append(elemento)
    ultimo = pagina[-1] if pagina else None
    return {
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        "corte": hasta.isoformat(),
        "totales_por_estado": totales,
        "elementos": elementos,
        "siguiente": paginacion.emitir_cursor(ultimo.estado_al_corte, str(ultimo.fila.propietaria_id), str(ultimo.fila.id)) if ultimo and len(incluidas) > cantidad else None,
    }
