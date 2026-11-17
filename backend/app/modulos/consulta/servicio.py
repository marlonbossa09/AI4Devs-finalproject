"""M4: consultas de solo lectura sobre registros de otras personas (convenciones 3.1 a 3.3).

M4-01 — consultar la bitácora de un compañero (``GET /personas/{persona_id}/bitacoras/{fecha_laboral}``).

Orden de evaluación (convenciones 3.2): 1) identificada y 2) puede operar (dependencia ``operador``: ``NO_IDENTIFICADA``,
``ACCESO_DESACTIVADO``, ``SIN_PERTENENCIA_VIGENTE``); 3) formato de la ruta (``SOLICITUD_INVALIDA``), sin consultar nada;
4) visibilidad del registro (``RECURSO_NO_DISPONIBLE``); solo entonces se leen los datos.

La decisión de visibilidad es la de M1 (``app.compartido.visibilidad``): ninguna regla de equipo se escribe aquí. Un registro
inexistente, de una fecha en que la persona pertenecía a otro equipo, de otra organización, de una fecha sin pertenencia o de una
persona inexistente responden lo MISMO (404, T-01): la decisión se toma solo con las pertenencias, antes de mirar si la
bitácora existe, y la respuesta no depende del motivo.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador
from app.compartido.fechas import parsear_fecha_laboral
from app.compartido.visibilidad import (
    Forma, Registro, consultante_de, decidir_lectura, forma_de_actividad, puede_ver_estado_actual,
)
from app.errores import AppError
from app.modulos.bitacoras import repositorio
from app.modulos.bitacoras.esquemas import avance_a_dict, bitacora_a_dict, planificacion_a_dict
from app.modulos.consulta import proyecciones


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
    ve_estado_actual = puede_ver_estado_actual(db, consultante, persona)
    actividades, visibles = [], set()
    for a in repositorio.listar_actividades_referenciadas(db, persona, bitacora.id):
        forma = forma_de_actividad(db, consultante, Registro(a.propietaria_id, a.fecha_laboral_origen), marcada_por_error=a.registrada_por_error)
        if forma is Forma.OCULTA:
            continue
        visibles.add(a.id)
        actividades.append(
            proyecciones.actividad_completa(a, a.fecha_laboral_origen, con_estado_actual=ve_estado_actual)
            if forma is Forma.COMPLETA else proyecciones.actividad_neutral(a))

    # Planificaciones, avances y la bitácora misma: el detalle PROPIO de cada registro (RA-05); no llevan el título de la actividad.
    return {
        "bitacora": bitacora_a_dict(bitacora, op.contexto.fecha_actual),
        "planificaciones": [planificacion_a_dict(p, fecha) for p in repositorio.listar_planificaciones(db, bitacora.id) if p.actividad_id in visibles],
        "avances": [avance_a_dict(a, fecha) for a in repositorio.listar_avances(db, bitacora.id) if a.actividad_id in visibles],
        "actividades": actividades,
    }
