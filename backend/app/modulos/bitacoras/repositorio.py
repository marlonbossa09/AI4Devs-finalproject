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


def obtener_actividad_propia(db: Session, persona_id: UUID, actividad_id: UUID, *, bloquear: bool = False):
    """La actividad solo si es de la persona (fila + fecha laboral de su bitácora de origen). Una
    actividad ajena es indistinguible de una inexistente (T-01). ``bloquear`` serializa los registros
    concurrentes sobre la misma actividad (DM-01): el segundo espera al primero y ve su resultado."""
    return db.execute(
        text("select a.*, b.fecha_laboral as fecha_laboral_origen from actividad a "
             "join bitacora b on b.id = a.bitacora_origen_id "
             "where a.id = :a and a.propietaria_id = :p" + (" for update of a" if bloquear else "")),
        {"a": actividad_id, "p": persona_id},
    ).one_or_none()


def listar_avances_de_actividad(db: Session, actividad_id: UUID):
    """La secuencia de la actividad con la fecha laboral de la bitácora de cada avance (IR-09)."""
    return db.execute(
        text("select av.id, b.fecha_laboral, av.registrado_en, av.estado, av.es_reactivacion "
             "from avance av join bitacora b on b.id = av.bitacora_id where av.actividad_id = :a"),
        {"a": actividad_id},
    ).all()


def insertar_avance(db: Session, actividad_id: UUID, bitacora_id: UUID, estado: str, descripcion: str,
                    motivo_bloqueo: str | None):
    """``registrado_en`` usa el reloj real (``clock_timestamp``), no el inicio de la transacción: así
    un registro que espera el bloqueo de la actividad queda después del que lo precedió."""
    return db.execute(
        text("insert into avance (actividad_id, bitacora_id, registrado_en, estado, descripcion, motivo_bloqueo) "
             "values (:a, :b, clock_timestamp(), :e, :d, :m) returning *"),
        {"a": actividad_id, "b": bitacora_id, "e": estado, "d": descripcion, "m": motivo_bloqueo},
    ).one()


def listar_planificaciones_de_actividad(db: Session, actividad_id: UUID):
    """Todas las planificaciones de la actividad con la fecha laboral de su bitácora, por esa fecha."""
    return db.execute(
        text("select p.*, b.fecha_laboral from planificacion p join bitacora b on b.id = p.bitacora_id "
             "where p.actividad_id = :a order by b.fecha_laboral, p.registrada_en, p.id"),
        {"a": actividad_id},
    ).all()


def listar_avances_con_fecha(db: Session, actividad_id: UUID):
    """La secuencia completa de avances de la actividad, en el orden total de IR-09: fecha laboral de
    la bitácora, momento real de registro e identificador estable (CA-74 a CA-76)."""
    return db.execute(
        text("select av.*, b.fecha_laboral from avance av join bitacora b on b.id = av.bitacora_id "
             "where av.actividad_id = :a order by b.fecha_laboral, av.registrado_en, av.id"),
        {"a": actividad_id},
    ).all()


def listar_actividades_propias(db: Session, persona_id: UUID, estados: list[str] | None, cursor: tuple | None,
                               cantidad: int):
    """Actividades de la persona, sin las marcadas por error (CA-119), de la más reciente a la más
    antigua (``creada_en`` y, de desempate, ``id``). El filtro de autorización (propietaria) se aplica
    en la propia selección, antes de paginar. ``cursor`` es (creada_en, id) del último elemento ya
    entregado; se piden ``cantidad`` filas para saber si hay más."""
    condiciones = ["a.propietaria_id = :p", "not a.registrada_por_error"]
    parametros: dict = {"p": persona_id, "n": cantidad}
    if estados:
        condiciones.append("a.estado_actual = any(cast(:estados as text[]))")
        parametros["estados"] = estados
    if cursor is not None:
        condiciones.append("(a.creada_en, a.id) < (cast(:c_creada as timestamptz), cast(:c_id as uuid))")
        parametros["c_creada"], parametros["c_id"] = cursor
    return db.execute(
        text("select a.id, a.titulo, a.origen, a.estado_actual, a.creada_en from actividad a where "
             + " and ".join(condiciones) + " order by a.creada_en desc, a.id desc limit :n"),
        parametros,
    ).all()


def actualizar_estado_actual(db: Session, actividad_id: UUID, estado: str) -> None:
    db.execute(text("update actividad set estado_actual = :e where id = :a"), {"e": estado, "a": actividad_id})


def insertar_actividad(db: Session, persona_id: UUID, bitacora_id: UUID, titulo: str, *,
                       origen: str = "planificada", estado_actual: str = "Pendiente"):
    """Una planificada empieza en Pendiente (M2-03); una no planificada, en el estado de su primer
    avance (IR-13), que el servicio pasa en el mismo momento de crear ambos."""
    return db.execute(
        text("insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen, estado_actual) "
             "values (:p, :b, :t, :o, :e) returning *"),
        {"p": persona_id, "b": bitacora_id, "t": titulo, "o": origen, "e": estado_actual},
    ).one()


def insertar_planificacion_original(db: Session, actividad_id: UUID, bitacora_id: UUID, descripcion: str):
    return db.execute(
        text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) "
             "values (:a, :b, 'original', :d) returning *"),
        {"a": actividad_id, "b": bitacora_id, "d": descripcion},
    ).one()
