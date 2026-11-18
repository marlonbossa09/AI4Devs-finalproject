"""Lecturas de M4. Toda selección de registros ajenos aplica el predicado de autorización de M1 (``visibilidad.condicion_lectura``) **en la propia
consulta**, antes de ordenar, de paginar y de calcular cualquier cosa derivada (convenciones 3.3). Aquí no se escribe ninguna condición de equipo."""

from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido.visibilidad import Consultante, condicion_equipo, condicion_lectura, pertenencia_del_equipo


def listar_historico(db: Session, consultante: Consultante, desde: date, hasta: date, persona: UUID | None,
                     cursor: tuple[date, UUID, UUID] | None, cantidad: int):
    """Bitácoras autorizadas del rango, por (fecha laboral, persona, id), tras ``cursor`` (la clave del último elemento entregado). Si ``persona`` se indica,
    solo las de esa persona que además estén autorizadas (una persona sin registros visibles da una lista vacía)."""
    condicion, parametros = condicion_lectura(consultante, "b.persona_id", "b.fecha_laboral")
    sql = ("select b.id, b.persona_id, b.fecha_laboral, b.estado, b.resumen from bitacora b "
           "where b.fecha_laboral between :desde and :hasta and " + condicion)
    parametros.update({"desde": desde, "hasta": hasta, "n": cantidad})
    if persona is not None:
        sql += " and b.persona_id = :persona"
        parametros["persona"] = persona
    if cursor is not None:
        sql += " and (b.fecha_laboral, b.persona_id, b.id) > (:c_fecha, :c_persona, :c_id)"
        parametros.update({"c_fecha": cursor[0], "c_persona": cursor[1], "c_id": cursor[2]})
    sql += " order by b.fecha_laboral, b.persona_id, b.id limit :n"
    return db.execute(text(sql), parametros).all()


def actividades_referenciadas(db: Session, bitacoras: list[UUID]):
    """Actividades referenciadas por las planificaciones o los avances de cada bitácora de la lista, con la fecha de su jornada de origen. Una sola consulta."""
    if not bitacoras:
        return []
    return db.execute(
        text("select r.bitacora_id, a.*, ob.fecha_laboral as fecha_laboral_origen from actividad a "
             "join bitacora ob on ob.id = a.bitacora_origen_id "
             "join (select actividad_id, bitacora_id from planificacion where bitacora_id = any(:b) "
             "      union select actividad_id, bitacora_id from avance where bitacora_id = any(:b)) r on r.actividad_id = a.id "
             "order by r.bitacora_id, a.creada_en, a.id"),
        {"b": bitacoras},
    ).all()


# =============================== M4-03: vista de supervisión ==========================================

def actividades_candidatas(db: Session, consultante: Consultante, desde: date, hasta: date):
    """Actividades que pueden entrar en la vista del período del supervisor, con los HECHOS de autorización que decide la política (``visibilidad``): ``origen_autorizado`` (el
    equipo de la propietaria en la fecha de su jornada de origen es el del supervisor, ``condicion_equipo``), ``por_planificacion`` y ``por_avances`` (con planificación o avances
    autorizados en el período) y ``en_el_equipo_al_corte`` (la propietaria es del equipo en la fecha de corte). No salen las marcadas por error (RA-08, CA-147). Una actividad
    cuyo origen no está autorizado (heredada) sale SIN título, origen ni fecha de origen: esos datos no abandonan la base si no están autorizados. La decisión final (forma,
    estado al corte, motivos) la toma el servicio con la política.

    La consulta PARTE de los integrantes del equipo (``pertenencia_del_equipo``, la misma expresión de pertenencia de la política) y de las bitácoras de esos integrantes en las
    fechas en que lo eran, así que su coste crece con el tamaño del equipo y del período, no con el de la organización."""
    c_bitacoras, p_bitacoras = pertenencia_del_equipo(consultante, "pv", "b.fecha_laboral", prefijo="eb")
    c_corte, p_corte = pertenencia_del_equipo(consultante, "pc", ":hasta", prefijo="ec")
    c_origen, p_origen = condicion_equipo(consultante, "a.propietaria_id", "ob.fecha_laboral", prefijo="eo")
    sql = (
        # bitácoras del período de quienes eran del equipo EN ESA fecha (autorizadas)
        "with eb as ("
        " select b.id, b.persona_id from pertenencia pv join bitacora b on b.persona_id = pv.persona_id"
        f" where b.fecha_laboral between :desde and :hasta and {c_bitacoras}),"
        # actividades con planificación o con avances autorizados en el período (siempre en una bitácora de su propietaria)
        " planificadas as (select distinct pl.actividad_id from eb join planificacion pl on pl.bitacora_id = eb.id"
        "  join actividad ap on ap.id = pl.actividad_id and ap.propietaria_id = eb.persona_id),"
        " con_avances as (select distinct av.actividad_id from eb join avance av on av.bitacora_id = eb.id"
        "  join actividad aa on aa.id = av.actividad_id and aa.propietaria_id = eb.persona_id),"
        # actividades de quienes son del equipo en la fecha de corte (posiblemente pendientes al corte)
        " del_equipo_al_corte as (select distinct a.id from pertenencia pc join actividad a on a.propietaria_id = pc.persona_id"
        f"  where {c_corte}),"
        " candidatas as (select actividad_id as id from planificadas union select actividad_id from con_avances union select id from del_equipo_al_corte),"
        " hechos as ("
        "  select a.id, a.propietaria_id, a.titulo, a.origen, a.estado_actual, a.registrada_por_error, a.motivo_error, a.marcada_en, a.creada_en,"
        "   ob.fecha_laboral as fecha_laboral_origen,"
        f"   ({c_origen}) as origen_autorizado,"
        "   (a.id in (select actividad_id from planificadas)) as por_planificacion,"
        "   (a.id in (select actividad_id from con_avances)) as por_avances,"
        "   (a.id in (select id from del_equipo_al_corte)) as en_el_equipo_al_corte"
        "  from candidatas k join actividad a on a.id = k.id join bitacora ob on ob.id = a.bitacora_origen_id"
        "  where not a.registrada_por_error and ob.fecha_laboral <= :hasta"
        # lo completado antes del corte y sin avances posteriores no puede estar pendiente al corte: solo cuenta si tiene otro motivo
        "   and (a.id in (select actividad_id from planificadas) or a.id in (select actividad_id from con_avances)"
        "        or a.estado_actual <> 'Completada' or exists (select 1 from avance ax join bitacora bx on bx.id = ax.bitacora_id where ax.actividad_id = a.id and bx.fecha_laboral > :hasta)))"
        " select id, propietaria_id, case when origen_autorizado then titulo end as titulo, case when origen_autorizado then origen end as origen, estado_actual,"
        "  registrada_por_error, motivo_error, marcada_en, case when origen_autorizado then creada_en end as creada_en,"
        "  case when origen_autorizado then fecha_laboral_origen end as fecha_laboral_origen,"
        "  origen_autorizado, por_planificacion, por_avances, en_el_equipo_al_corte from hechos")
    parametros = {"desde": desde, "hasta": hasta, **p_bitacoras, **p_corte, **p_origen}
    return db.execute(text(sql), parametros).all()


def avances_de_las_actividades(db: Session, consultante: Consultante, actividades: list[UUID]):
    """Los avances de esas actividades de TODAS las fechas (el servicio separa los de hasta el corte), cada uno con si está autorizado (su fecha laboral es de un período en que la
    propietaria era del equipo del supervisor, ``condicion_equipo``). El estado al corte lo determina el último hasta el corte; si no está autorizado, no se muestra (RA-07)."""
    if not actividades:
        return []
    autorizado, parametros = condicion_equipo(consultante, "a.propietaria_id", "bx.fecha_laboral", prefijo="ea")
    sql = ("select av.actividad_id, av.id, bx.fecha_laboral, av.registrado_en, av.estado, av.es_reactivacion, " + autorizado + " as autorizado "
           "from avance av join bitacora bx on bx.id = av.bitacora_id join actividad a on a.id = av.actividad_id "
           "where av.actividad_id = any(:ids)")
    return db.execute(text(sql), {"ids": actividades, **parametros}).all()


def actividades_con_planificacion_autorizada(db: Session, consultante: Consultante, actividades: list[UUID], hasta: date) -> set[UUID]:
    """Identificadores de las actividades que tienen alguna planificación (original o continuación) autorizada con fecha laboral hasta el corte: son «registros del equipo» sobre
    ellas (RN-47). Solo el identificador sale de la consulta."""
    if not actividades:
        return set()
    autorizado, parametros = condicion_equipo(consultante, "a.propietaria_id", "bp.fecha_laboral", prefijo="ep")
    sql = ("select distinct pl.actividad_id from planificacion pl join bitacora bp on bp.id = pl.bitacora_id join actividad a on a.id = pl.actividad_id "
           f"where pl.actividad_id = any(:ids) and bp.fecha_laboral <= :hasta and {autorizado}")
    return {fila[0] for fila in db.execute(text(sql), {"ids": actividades, "hasta": hasta, **parametros}).all()}


# =============================== M4-04: historial de una actividad ====================================

def actividad_con_hechos_de_autorizacion(db: Session, consultante: Consultante, actividad: UUID):
    """La actividad (o ``None`` si no existe) con el hecho ``origen_autorizado`` que decide la política (``condicion_equipo`` sobre la fecha de su jornada de origen). Si el origen NO
    está autorizado, el título, el origen, el motivo y la fecha de la marca, la fecha de creación y la fecha de origen salen de la base como nulos: lo protegido no abandona la consulta.
    ``registrada_por_error`` sí sale (el servicio lo necesita para ocultar la actividad, RA-08)."""
    c_origen, p_origen = condicion_equipo(consultante, "a.propietaria_id", "ob.fecha_laboral", prefijo="eo")
    sql = (
        "with h as (select a.id, a.propietaria_id, a.titulo, a.origen, a.estado_actual, a.registrada_por_error, a.motivo_error, a.marcada_en, a.creada_en,"
        f"  ob.fecha_laboral as fecha_laboral_origen, ({c_origen}) as origen_autorizado"
        " from actividad a join bitacora ob on ob.id = a.bitacora_origen_id where a.id = :actividad)"
        " select id, propietaria_id, case when origen_autorizado then titulo end as titulo, case when origen_autorizado then origen end as origen, estado_actual,"
        "  registrada_por_error, case when origen_autorizado then motivo_error end as motivo_error, case when origen_autorizado then marcada_en end as marcada_en,"
        "  case when origen_autorizado then creada_en end as creada_en, case when origen_autorizado then fecha_laboral_origen end as fecha_laboral_origen,"
        "  origen_autorizado from h")
    return db.execute(text(sql), {"actividad": actividad, **p_origen}).one_or_none()


def avances_autorizados_de_la_actividad(db: Session, consultante: Consultante, actividad: UUID):
    """Los avances de la actividad cuya fecha laboral es de un período en que su propietaria era del equipo del supervisor (``condicion_equipo``), con su detalle propio. Los demás NO
    salen de la consulta."""
    autorizado, parametros = condicion_equipo(consultante, "a.propietaria_id", "bx.fecha_laboral", prefijo="ea")
    sql = ("select av.id, av.actividad_id, av.estado, av.descripcion, av.motivo_bloqueo, av.es_reactivacion, av.registrado_en, av.modificado_en, bx.fecha_laboral "
           "from avance av join bitacora bx on bx.id = av.bitacora_id join actividad a on a.id = av.actividad_id "
           f"where av.actividad_id = :actividad and {autorizado}")
    return db.execute(text(sql), {"actividad": actividad, **parametros}).all()


def planificaciones_autorizadas_de_la_actividad(db: Session, consultante: Consultante, actividad: UUID):
    """Las planificaciones (original y continuaciones) autorizadas de la actividad, con su fecha laboral. Una planificación conservada (fecha no cubierta por la propietaria) no es de
    ningún equipo y no sale. Las demás no salen de la consulta."""
    autorizado, parametros = condicion_equipo(consultante, "a.propietaria_id", "bp.fecha_laboral", prefijo="ep")
    sql = ("select pl.id, pl.actividad_id, pl.tipo, pl.descripcion, pl.registrada_en, bp.fecha_laboral "
           "from planificacion pl join bitacora bp on bp.id = pl.bitacora_id join actividad a on a.id = pl.actividad_id "
           f"where pl.actividad_id = :actividad and {autorizado}")
    return db.execute(text(sql), {"actividad": actividad, **parametros}).all()
