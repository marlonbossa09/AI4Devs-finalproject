"""M4-04 (M4-T5) — historial de una actividad del equipo (``GET /api/v1/equipo/actividades/{actividad_id}``).

SOLO el supervisor vigente con acceso efectivo (RA-12, RN-13); un colaborador recibe 403 ``OPERACION_NO_PERMITIDA``, exista o no la actividad (el permiso se comprueba ANTES de buscarla,
así la respuesta no es un oráculo de existencia). Solo lectura. Orden de evaluación (convenciones 3.2): sesión y puede operar (dependencia ``operador``), FORMATO del identificador,
permiso de supervisión y, solo entonces, los datos.

**Una sola política.** Como en M4-03, este módulo no tiene reglas de autorización propias: la política de M1 (``app.compartido.visibilidad``) decide la pertenencia al equipo
(``condicion_equipo`` en SQL), la forma de la actividad (``forma_en_supervision``) y el estado actual (``puede_ver_estado_actual``). Aquí solo se reúnen esos hechos y se construye la
respuesta con los proyectores de M4 (``proyecciones``), que tienen listas CERRADAS de campos propias del contrato (no se reutilizan los esquemas de M2 con todos sus campos). Los avances y las planificaciones se seleccionan ya
autorizados (convenciones 3.3): lo que no lo está no sale de la consulta, así que no puede asomar en un campo, en el orden ni en el estado histórico de otro registro.

**Respuestas** (lista cerrada de campos por forma):
- ``tipo`` ``actividad``: ``actividad`` (``ActividadVisible`` ``completa`` si el origen es del equipo, ``neutral`` si es heredada con registros del equipo), ``avances`` (solo los autorizados,
  en el orden de la secuencia —fecha laboral, momento de registro e identificador, que se usan para ordenar pero NO se envían—; cada uno con SOLO fecha laboral, estado histórico, descripción y motivo de bloqueo PROPIOS), ``planificaciones`` (solo las
  autorizadas) y ``estado_actual`` solo si la propietaria pertenece hoy al equipo (D-M4-05). El estado histórico de cada avance es el de ese avance autorizado: nunca se deduce de uno protegido.
- ``tipo`` ``referencia_minima`` (D-09, RN-84, RN-89; CA-233, CA-292): actividad heredada SIN registros del equipo, no completada y de una propietaria que pertenece hoy al equipo.
  Es la misma ``ReferenciaMínima`` de M4-03: propietaria, «iniciada en otro equipo», estado actual y referencia neutral; nada del equipo anterior ni historial.
- ``404`` ``RECURSO_NO_DISPONIBLE`` indistinguible (T-01) para todo lo demás: inexistente, de otro equipo u organización, heredada completada o de una persona que ya no es del equipo
  sin registros del equipo, y marcada por error con el origen no autorizado (RA-08, CA-268).

**Marcas por error.** Una actividad marcada por error con el origen AUTORIZADO se muestra con su marca y su motivo (RA-04: los ve quien está autorizado sobre su jornada de origen); con el origen
no autorizado no existe para el supervisor, ni siquiera como referencia mínima. Sin clasificaciones, rankings ni puntuaciones de personas (CA-151).
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido import visibilidad
from app.compartido.dependencias import Operador
from app.compartido.visibilidad import consultante_de, puede_ver_estado_actual
from app.errores import AppError
from app.modulos.bitacoras import secuencia
from app.modulos.bitacoras.secuencia import AvanceEnSecuencia
from app.modulos.consulta import proyecciones, repositorio


def consultar_historial_de_actividad(db: Session, op: Operador, actividad_id: str) -> dict:
    try:
        actividad = UUID(actividad_id)
    except ValueError:
        raise AppError("SOLICITUD_INVALIDA", [{"campo": "actividad_id", "motivo": "identificador_no_valido"}]) from None

    consultante = consultante_de(db, op.persona_id, hoy=op.contexto.fecha_actual)
    if not consultante.es_supervisor_vigente:                                            # RN-13, RA-12: nadie más consulta el historial del equipo
        raise AppError("OPERACION_NO_PERMITIDA")

    a = repositorio.actividad_con_hechos_de_autorizacion(db, consultante, actividad)
    if a is None or (a.registrada_por_error and not a.origen_autorizado):                  # inexistente, u oculta por RA-08 (T-01: la misma respuesta)
        raise AppError("RECURSO_NO_DISPONIBLE")
    avances = repositorio.avances_autorizados_de_la_actividad(db, consultante, actividad)
    planificaciones = repositorio.planificaciones_autorizadas_de_la_actividad(db, consultante, actividad)
    ve_estado_actual = puede_ver_estado_actual(db, consultante, a.propietaria_id)

    forma = visibilidad.forma_en_supervision(a.origen_autorizado, bool(avances or planificaciones))
    if forma == visibilidad.EN_SUPERVISION_REFERENCIA_MINIMA:
        # D-09: solo si se puede informar el estado actual (la propietaria es del equipo) y la actividad no está completada; si no, no es siquiera una referencia (CA-221)
        if not ve_estado_actual or a.estado_actual == secuencia.COMPLETADA:
            raise AppError("RECURSO_NO_DISPONIBLE")
        return proyecciones.referencia_minima(a, estado_actual=a.estado_actual, fecha_ultimo_avance=None)   # sin avances autorizados no hay fecha que mostrar (RA-06)

    ordenados = secuencia.ordenar([AvanceEnSecuencia(v.id, v.fecha_laboral, v.registrado_en, v.estado, v.es_reactivacion) for v in avances])
    por_id = {v.id: v for v in avances}
    respuesta = {
        "tipo": "actividad",
        "actividad": (proyecciones.actividad_completa(a, a.fecha_laboral_origen, con_estado_actual=False) if forma == visibilidad.EN_SUPERVISION_COMPLETA
                      else proyecciones.actividad_neutral(a)),
        "avances": [proyecciones.avance_de_historial(por_id[v.id]) for v in ordenados],
        "planificaciones": [proyecciones.planificacion_de_historial(p) for p in sorted(planificaciones, key=lambda p: (p.fecha_laboral, p.registrada_en, p.id))],
    }
    if ve_estado_actual:
        respuesta["estado_actual"] = a.estado_actual                                       # solo con la propietaria en el equipo hoy (D-M4-05)
    return respuesta
