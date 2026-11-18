"""Proyecciones de M4 (DM-03, RA-04 a RA-06): cómo se presenta una actividad a quien no es su propietaria.

``ActividadVisible`` (convenciones 7) tiene dos formas:

- ``completa``: lo mismo que ve la propietaria (título, origen, marca de error con su motivo, fecha de su jornada de origen),
  para quien está autorizado sobre su JORNADA DE ORIGEN. El estado actual solo se informa si la propietaria pertenece hoy al
  equipo de quien consulta (RN-48, RN-85, ``visibilidad.puede_ver_estado_actual``).
- ``neutral``: ``id`` (opaco: los identificadores son aleatorios y no llevan información del equipo anterior),
  ``propietaria_id`` y ``referencia_neutral`` con el texto fijo «Actividad en continuidad» (D-07, RN-101). **Nada más**: ni título,
  ni origen, ni marca de error, ni estado, ni fecha de origen. La lista de campos es cerrada a propósito.

``forma`` (``completa`` o ``neutral``) discrimina las dos formas en el JSON `[PROPUESTO]`.

Quién decide la forma es la política de visibilidad (``forma_de_actividad``): aquí solo se construye el JSON. Una actividad
``oculta`` no aparece (RA-08) y no se proyecta.
"""

from datetime import date

from app.modulos.bitacoras.esquemas import actividad_a_dict

REFERENCIA_NEUTRAL = "Actividad en continuidad"
COMPLETA = "completa"
NEUTRAL = "neutral"


def actividad_completa(fila, fecha_laboral_origen, *, con_estado_actual: bool) -> dict:
    visible = actividad_a_dict(fila, fecha_laboral_origen)
    if not con_estado_actual:
        del visible["estado_actual"]          # omitido, no nulo: ni siquiera se sabe que existe
    return {"forma": COMPLETA, **visible}


def actividad_neutral(fila) -> dict:
    return {"forma": NEUTRAL, "id": str(fila.id), "propietaria_id": str(fila.propietaria_id), "referencia_neutral": REFERENCIA_NEUTRAL}


REFERENCIA_MINIMA = "referencia_minima"


def avance_de_historial(fila) -> dict:
    """Avance de M4-04: SOLO los campos que el contrato permite (fecha laboral, estado histórico, descripción y motivo de bloqueo del propio avance). No reutiliza ``avance_a_dict`` de M2:
    ni el identificador, ni ``registrado_en``, ni ``modificado_en`` (momentos reales y señal de una corrección, que pertenecen a la auditoría de M3-07), ni ``es_reactivacion`` se exponen
    a otra persona. Un campo nuevo de M2 no llega aquí por sí solo: hay que añadirlo a esta lista a propósito."""
    return {"fecha_laboral": fila.fecha_laboral.isoformat(), "estado": fila.estado, "descripcion": fila.descripcion, "motivo_bloqueo": fila.motivo_bloqueo}


def planificacion_de_historial(fila) -> dict:
    """Planificación autorizada de M4-04 (todas vigentes por selección): solo fecha laboral, tipo (original o continuación) y descripción. Sin identificadores ni momentos de registro."""
    return {"fecha_laboral": fila.fecha_laboral.isoformat(), "tipo": fila.tipo, "descripcion": fila.descripcion}


def referencia_minima(fila, *, estado_actual: str, fecha_ultimo_avance: date | None) -> dict:
    """``ReferenciaMínima`` (convenciones 7, RA-06, RN-84, RN-89, D-09, D-M4-06): elemento de la vista de supervisión para una actividad iniciada en otro equipo sin registros del
    equipo. Lista CERRADA de campos: ``tipo`` (la distingue del acceso completo), ``actividad`` (forma neutral), ``propietaria_id``, ``iniciada_en_otro_equipo`` (siempre verdadero, sin
    nombrar el equipo), ``estado_actual`` y ``fecha_ultimo_avance`` solo si ese avance está autorizado (se OMITE, no se envía nulo). Nunca título, descripciones, motivos de bloqueo,
    contenido de bitácoras, nombre del equipo anterior, número de avances, fecha de creación, planificación original, marca de error ni estado al corte."""
    referencia = {"tipo": REFERENCIA_MINIMA, "actividad": actividad_neutral(fila), "propietaria_id": str(fila.propietaria_id), "iniciada_en_otro_equipo": True,
                  "estado_actual": estado_actual}
    if fecha_ultimo_avance is not None:
        referencia["fecha_ultimo_avance"] = fecha_ultimo_avance.isoformat()
    return referencia
