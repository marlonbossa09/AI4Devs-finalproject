"""Lecturas de M4. Toda selección de registros ajenos aplica el predicado de autorización de M1 (``visibilidad.condicion_lectura``) **en la propia
consulta**, antes de ordenar, de paginar y de calcular cualquier cosa derivada (convenciones 3.3). Aquí no se escribe ninguna condición de equipo."""

from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido.visibilidad import Consultante, condicion_lectura


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
