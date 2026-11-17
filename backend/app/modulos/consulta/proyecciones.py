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
