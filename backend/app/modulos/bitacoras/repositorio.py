"""Acceso a datos de bitácoras, actividades y planificaciones (SQL explícito)."""

from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def obtener_bitacora(db: Session, persona_id: UUID, fecha: date):
    return db.execute(
        text("select * from bitacora where persona_id = :p and fecha_laboral = :f"),
        {"p": persona_id, "f": fecha},
    ).one_or_none()


def obtener_o_crear_bitacora(db: Session, persona_id: UUID, fecha: date):
    """Crea la bitácora si no existe. La unicidad por persona y fecha (IR-01) es absoluta: ante
    aperturas simultáneas, solo una inserta y las demás reciben la existente."""
    creada = db.execute(
        text("insert into bitacora (persona_id, fecha_laboral) values (:p, :f) "
             "on conflict (persona_id, fecha_laboral) do nothing returning *"),
        {"p": persona_id, "f": fecha},
    ).one_or_none()
    if creada is not None:
        return creada, True
    return obtener_bitacora(db, persona_id, fecha), False


def listar_planificaciones(db: Session, bitacora_id: UUID):
    return db.execute(
        text("select * from planificacion where bitacora_id = :b order by registrada_en, id"), {"b": bitacora_id}
    ).all()


def listar_avances(db: Session, bitacora_id: UUID):
    return db.execute(
        text("select * from avance where bitacora_id = :b order by registrado_en, id"), {"b": bitacora_id}
    ).all()


def listar_actividades_referenciadas(db: Session, persona_id: UUID, bitacora_id: UUID):
    """Actividades propias referenciadas por las planificaciones o los avances de la bitácora."""
    return db.execute(
        text("select a.*, b.fecha_laboral as fecha_laboral_origen from actividad a "
             "join bitacora b on b.id = a.bitacora_origen_id "
             "where a.propietaria_id = :p and a.id in ("
             "  select actividad_id from planificacion where bitacora_id = :b "
             "  union select actividad_id from avance where bitacora_id = :b) "
             "order by a.creada_en, a.id"),
        {"p": persona_id, "b": bitacora_id},
    ).all()


def insertar_actividad(db: Session, persona_id: UUID, bitacora_id: UUID, titulo: str):
    return db.execute(
        text("insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen) "
             "values (:p, :b, :t, 'planificada') returning *"),
        {"p": persona_id, "b": bitacora_id, "t": titulo},
    ).one()


def insertar_planificacion_original(db: Session, actividad_id: UUID, bitacora_id: UUID, descripcion: str):
    return db.execute(
        text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) "
             "values (:a, :b, 'original', :d) returning *"),
        {"a": actividad_id, "b": bitacora_id, "d": descripcion},
    ).one()
