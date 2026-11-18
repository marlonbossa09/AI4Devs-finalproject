"""Lecturas de M5 (informes). Como en M4, toda selección aplica el predicado de autorización de M1 (``visibilidad.condicion_lectura``) **en la propia consulta** (convenciones 3.3,
RA-09): un registro no autorizado no llega a salir de la base, así que ningún recuento, agregación o texto puede derivar de él. Aquí no se escribe ninguna condición de equipo."""

from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido.visibilidad import Consultante, condicion_equipo, condicion_lectura, pertenencia_del_equipo


def nombre_de_la_persona(db: Session, persona: UUID) -> str | None:
    """Solo el nombre: no se lee ningún otro dato de la persona (ni acceso, ni identidad, ni equipo). Se llama DESPUÉS de autorizar."""
    return db.execute(text("select nombre from persona where id = :p"), {"p": persona}).scalar_one_or_none()


def ultimo_avance_hasta_el_corte(db: Session, actividades: list[UUID], hasta: date, autorizado: tuple[str, dict]):
    """Para cada actividad de la lista, su ÚLTIMO avance con fecha laboral <= ``hasta`` según la secuencia válida completa (fecha laboral, momento de registro, identificador: la de M2 y M4),
    esté o no autorizado, con ``autorizado`` decidido en la propia consulta por el predicado que recibe (``condicion_lectura`` en el informe individual, ``condicion_equipo`` en el
    consolidado: siempre de ``app.compartido.visibilidad``; el predicado debe usar los alias ``a`` (actividad) y ``bx`` (bitácora del avance)). El ``estado`` SOLO sale de la base si el avance
    está autorizado (RA-07, RN-88): el de un avance protegido nunca abandona la consulta y NUNCA se sustituye por el de uno anterior. Devuelve ``actividad_id``, ``autorizado`` y ``estado``."""
    if not actividades:
        return []
    condicion, parametros = autorizado
    sql = ("select distinct on (u.actividad_id) u.actividad_id, u.autorizado, case when u.autorizado then u.estado end as estado from ("
           f" select av.actividad_id, av.id, bx.fecha_laboral, av.registrado_en, av.estado, ({condicion}) as autorizado"
           " from avance av join bitacora bx on bx.id = av.bitacora_id"
           " join actividad a on a.id = av.actividad_id and a.propietaria_id = bx.persona_id"
           " where av.actividad_id = any(:ids) and bx.fecha_laboral <= :hasta) u"
           " order by u.actividad_id, u.fecha_laboral desc, u.registrado_en desc, u.id desc")
    return db.execute(text(sql), {"ids": actividades, "hasta": hasta, **parametros}).all()


def avances_autorizados_del_periodo(db: Session, consultante: Consultante, persona: UUID, desde: date, hasta: date, limite: int | None = None):
    """Los avances de ``persona`` con fecha laboral en [``desde``, ``hasta``] que ``consultante`` puede leer (``condicion_lectura`` sobre la fecha laboral de cada avance: RA-01, RN-36).
    No salen las actividades marcadas por error (RA-08, RN-60, CA-167) ni ningún avance de una fecha cuyo equipo no es el del consultante (salvo que sea la propietaria: RA-03).

    ``titulo`` y ``origen`` salen de la base solo si el consultante está autorizado sobre la JORNADA DE ORIGEN de la actividad (RA-04, RN-101, ``condicion_lectura`` sobre la fecha de
    origen); si no, salen nulos y ``origen_autorizado`` es falso. Orden: la secuencia de avances (fecha laboral, momento de registro, identificador), la misma de M2 y M4.
    Una planificación no es un avance y esta consulta no la lee (la planificación conservada de RA-11 queda fuera por construcción).

    ``limite`` (M5-T4) es un TOPE DE LECTURA, no un recorte del informe: el servicio pide ``máximo + 1`` filas y, si llegan más que el máximo, RECHAZA la solicitud (``INFORME_EXCEDE_LIMITES``); nunca devuelve un
    informe truncado. Sirve para no cargar miles de filas de una solicitud que se va a rechazar."""
    c_avance, p_avance = condicion_lectura(consultante, "bx.persona_id", "bx.fecha_laboral", prefijo="av")
    c_origen, p_origen = condicion_lectura(consultante, "a.propietaria_id", "ob.fecha_laboral", prefijo="ori")
    sql = (
        "with h as ("
        " select av.id as avance_id, bx.fecha_laboral, av.registrado_en, av.estado, av.descripcion, av.motivo_bloqueo,"
        f"  a.id as actividad_id, a.titulo, a.origen, ({c_origen}) as origen_autorizado"
        " from avance av"
        " join bitacora bx on bx.id = av.bitacora_id"
        " join actividad a on a.id = av.actividad_id and a.propietaria_id = bx.persona_id"
        " join bitacora ob on ob.id = a.bitacora_origen_id"
        " where bx.persona_id = :persona and bx.fecha_laboral between :desde and :hasta"
        f"  and not a.registrada_por_error and {c_avance})"
        " select avance_id, fecha_laboral, registrado_en, estado, descripcion, motivo_bloqueo, actividad_id,"
        "  case when origen_autorizado then titulo end as titulo, case when origen_autorizado then origen end as origen, origen_autorizado"
        " from h order by fecha_laboral, registrado_en, avance_id" + (" limit :limite" if limite is not None else ""))
    parametros = {"persona": persona, "desde": desde, "hasta": hasta, **p_avance, **p_origen}
    if limite is not None:
        parametros["limite"] = limite
    return db.execute(text(sql), parametros).all()


def avances_autorizados_del_equipo(db: Session, consultante: Consultante, desde: date, hasta: date, limite: int | None = None):
    """Los avances con fecha laboral en [``desde``, ``hasta``] de las personas que ERAN DEL EQUIPO de quien consulta EN ESA FECHA (``pertenencia_del_equipo``: la misma expresión de pertenencia de la
    política de M1; RA-01, RN-36), de todas las personas a la vez. A diferencia de la lectura de una persona (``condicion_lectura``) NO concede nada por ser la propia consultante: lo que la
    supervisora hizo en un período en que estaba en otro equipo no es del equipo (como en M4-03). No salen las actividades marcadas por error (RA-08, CA-167) ni ninguna planificación.

    ``titulo`` y ``origen`` salen de la base solo si la jornada de origen de la actividad es del equipo (``condicion_equipo``); si no (actividad heredada de otro equipo), salen nulos y
    ``origen_autorizado`` es falso (RN-101). De cada persona sale solo su nombre. La consulta PARTE de los integrantes del equipo y de sus bitácoras en las fechas en que lo eran, así que su
    coste crece con el tamaño del equipo y del período, no con el de la organización. Orden: persona, secuencia de avances (fecha laboral, momento, identificador).
    ``limite``: tope de lectura de TODAS las personas juntas, con el mismo sentido que en ``avances_autorizados_del_periodo`` (nunca trunca el informe)."""
    c_equipo, p_equipo = pertenencia_del_equipo(consultante, "pv", "bx.fecha_laboral", prefijo="eq")
    c_origen, p_origen = condicion_equipo(consultante, "a.propietaria_id", "ob.fecha_laboral", prefijo="eo")
    sql = (
        "with h as ("
        " select av.id as avance_id, bx.persona_id, p.nombre, bx.fecha_laboral, av.registrado_en, av.estado, av.descripcion, av.motivo_bloqueo,"
        f"  a.id as actividad_id, a.titulo, a.origen, ({c_origen}) as origen_autorizado"
        " from pertenencia pv"
        " join bitacora bx on bx.persona_id = pv.persona_id"
        " join avance av on av.bitacora_id = bx.id"
        " join actividad a on a.id = av.actividad_id and a.propietaria_id = bx.persona_id"
        " join bitacora ob on ob.id = a.bitacora_origen_id"
        " join persona p on p.id = bx.persona_id"
        " where bx.fecha_laboral between :desde and :hasta and not a.registrada_por_error"
        f"  and {c_equipo})"
        " select avance_id, persona_id, nombre, fecha_laboral, registrado_en, estado, descripcion, motivo_bloqueo, actividad_id,"
        "  case when origen_autorizado then titulo end as titulo, case when origen_autorizado then origen end as origen, origen_autorizado"
        " from h order by persona_id, fecha_laboral, registrado_en, avance_id" + (" limit :limite" if limite is not None else ""))
    parametros = {"desde": desde, "hasta": hasta, **p_equipo, **p_origen}
    if limite is not None:
        parametros["limite"] = limite
    return db.execute(text(sql), parametros).all()
