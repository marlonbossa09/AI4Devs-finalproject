"""M4: consultas de solo lectura sobre registros de otras personas (convenciones 3.1 a 3.3).

M4-01 — consultar la bitácora de un compañero (``GET /personas/{persona_id}/bitacoras/{fecha_laboral}``).
M4-02 — consultar el histórico por colaborador y fechas (``GET /historico``).

Orden de evaluación (convenciones 3.2): 1) identificada y 2) puede operar (dependencia ``operador``: ``NO_IDENTIFICADA``,
``ACCESO_DESACTIVADO``, ``SIN_PERTENENCIA_VIGENTE``); 3) formato de la ruta (``SOLICITUD_INVALIDA``), sin consultar nada;
4) visibilidad del registro (``RECURSO_NO_DISPONIBLE``); solo entonces se leen los datos.

La decisión de visibilidad es la de M1 (``app.compartido.visibilidad``): ninguna regla de equipo se escribe aquí. Un registro
inexistente, de una fecha en que la persona pertenecía a otro equipo, de otra organización, de una fecha sin pertenencia o de una
persona inexistente responden lo MISMO (404, T-01): la decisión se toma solo con las pertenencias, antes de mirar si la
bitácora existe, y la respuesta no depende del motivo.
"""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido import paginacion
from app.compartido.dependencias import Operador
from app.compartido.fechas import parsear_fecha_laboral
from app.compartido.visibilidad import (
    Forma, Registro, consultante_de, decidir_lectura, forma_de_actividad, puede_ver_estado_actual,
)
from app.errores import AppError
from app.modulos.bitacoras import repositorio
from app.modulos.bitacoras.esquemas import avance_a_dict, bitacora_a_dict, planificacion_a_dict
from app.modulos.consulta import proyecciones, repositorio as consultas


class _Proyector:
    """Proyecta las actividades de una respuesta según la autorización de quien consulta (RA-04, RA-08), recordando las decisiones repetidas de la misma petición
    (por jornada de origen y por propietaria) para no repetir consultas de pertenencia. La decisión es siempre la de la política de M1."""

    def __init__(self, db: Session, consultante) -> None:
        self.db, self.consultante = db, consultante
        self._formas: dict[tuple, Forma] = {}
        self._estados: dict[UUID, bool] = {}

    def proyectar(self, a) -> dict | None:
        """La actividad en su forma ``completa`` o ``neutral``, o ``None`` si está oculta (no aparece, RA-08)."""
        clave = (a.propietaria_id, a.fecha_laboral_origen, a.registrada_por_error)
        if clave not in self._formas:
            self._formas[clave] = forma_de_actividad(self.db, self.consultante, Registro(a.propietaria_id, a.fecha_laboral_origen), marcada_por_error=a.registrada_por_error)
        forma = self._formas[clave]
        if forma is Forma.OCULTA:
            return None
        if forma is Forma.NEUTRAL:
            return proyecciones.actividad_neutral(a)
        if a.propietaria_id not in self._estados:
            self._estados[a.propietaria_id] = puede_ver_estado_actual(self.db, self.consultante, a.propietaria_id)
        return proyecciones.actividad_completa(a, a.fecha_laboral_origen, con_estado_actual=self._estados[a.propietaria_id])


def consultar_bitacora_de_persona(db: Session, op: Operador, persona_id: str, fecha_laboral: str) -> dict:
    """M4-01. La bitácora de ``persona_id`` de una fecha, en solo lectura. Si ``persona_id`` es quien consulta, equivale a M2-01a
    (mismo contenido, más el campo ``forma`` de cada actividad). No crea nada: sin bitácora, el recurso no está disponible."""
    try:
        persona = UUID(persona_id)
    except ValueError:
        raise AppError("SOLICITUD_INVALIDA", [{"campo": "persona_id", "motivo": "identificador_no_valido"}]) from None
    fecha = parsear_fecha_laboral(fecha_laboral)

    consultante = consultante_de(db, op.persona_id, hoy=op.contexto.fecha_actual)
    if not decidir_lectura(db, consultante, Registro(persona, fecha)).visible:
        raise AppError("RECURSO_NO_DISPONIBLE")
    bitacora = repositorio.obtener_bitacora(db, persona, fecha)
    if bitacora is None:
        raise AppError("RECURSO_NO_DISPONIBLE")

    # Actividades de la bitácora, según la autorización de quien consulta sobre la JORNADA DE ORIGEN de cada una (RA-04, RA-08).
    # Las ocultas no aparecen y tampoco los avances ni las planificaciones que las referencian.
    proyector = _Proyector(db, consultante)
    actividades, visibles = [], set()
    for a in repositorio.listar_actividades_referenciadas(db, persona, bitacora.id):
        proyectada = proyector.proyectar(a)
        if proyectada is None:
            continue
        visibles.add(a.id)
        actividades.append(proyectada)

    # Planificaciones, avances y la bitácora misma: el detalle PROPIO de cada registro (RA-05); no llevan el título de la actividad.
    return {
        "bitacora": bitacora_a_dict(bitacora, op.contexto.fecha_actual),
        "planificaciones": [planificacion_a_dict(p, fecha) for p in repositorio.listar_planificaciones(db, bitacora.id) if p.actividad_id in visibles],
        "avances": [avance_a_dict(a, fecha) for a in repositorio.listar_avances(db, bitacora.id) if a.actividad_id in visibles],
        "actividades": actividades,
    }


# =============================== M4-02: histórico por colaborador y fechas ==========================================

PARAMETROS_DEL_HISTORICO = frozenset({"desde", "hasta", "persona_id", "limite", "continuar_desde"})


def consultar_historico(db: Session, op: Operador, consulta: list[tuple[str, str]]) -> dict:
    """M4-02. Las bitácoras que quien consulta está autorizado a leer en un rango de fechas laborales, de todas las personas que la política permite (siempre
    incluidas las propias) o solo de ``persona_id`` si se indica. Lista paginada con cursor opaco, orden estable (fecha laboral, persona, id) y ``siguiente``.

    Orden de evaluación (convenciones 3.2): 1) y 2) por la dependencia ``operador``; 3) el FORMATO de todos los parámetros, sin consultar nada (parámetro desconocido
    o repetido, rango obligatorio, ``desde`` ≤ ``hasta``, amplitud máxima, ``persona_id``, ``limite``, cursor); después, la selección. La autorización se aplica en la
    propia consulta (``condicion_lectura``) ANTES de ordenar y de paginar: lo no autorizado no cambia ni los elementos, ni su orden, ni el cursor, ni ``siguiente``.
    Un filtro sin registros autorizados (también una persona que no existe) da una lista vacía, no un error (T-01). No hay búsqueda por texto (CA-136)."""
    parametros = paginacion.leer_parametros(consulta, PARAMETROS_DEL_HISTORICO)
    desde, hasta = paginacion.rango_de_fechas(parametros)
    persona = None
    if parametros.get("persona_id") is not None:
        try:
            persona = UUID(parametros["persona_id"])
        except ValueError:
            raise AppError("SOLICITUD_INVALIDA", [{"campo": "persona_id", "motivo": "identificador_no_valido"}]) from None
    cantidad = paginacion.limite_de(parametros.get("limite"))
    cursor = paginacion.leer_cursor(parametros.get("continuar_desde"), date.fromisoformat, UUID, UUID)

    consultante = consultante_de(db, op.persona_id, hoy=op.contexto.fecha_actual)
    filas = consultas.listar_historico(db, consultante, desde, hasta, persona, cursor, cantidad + 1)
    pagina = filas[:cantidad]

    proyector = _Proyector(db, consultante)
    por_bitacora: dict[UUID, list[dict]] = {f.id: [] for f in pagina}
    for a in consultas.actividades_referenciadas(db, [f.id for f in pagina]):
        proyectada = proyector.proyectar(a)
        if proyectada is not None:
            por_bitacora[a.bitacora_id].append(proyectada)
    return {
        "elementos": [{"persona_id": str(f.persona_id), "fecha_laboral": f.fecha_laboral.isoformat(), "estado": f.estado, "resumen": f.resumen,
                       "actividades": por_bitacora[f.id]} for f in pagina],
        "siguiente": paginacion.emitir_cursor(pagina[-1].fecha_laboral.isoformat(), str(pagina[-1].persona_id), str(pagina[-1].id)) if len(filas) > cantidad else None,
    }
