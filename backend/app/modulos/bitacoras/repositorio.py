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


def bloquear_bitacora(db: Session, bitacora_id: UUID):
    """Relee la bitácora bloqueando su fila: las escrituras simultáneas sobre la misma jornada se
    serializan, así que el valor anterior que se audita es siempre el realmente reemplazado."""
    return db.execute(text("select * from bitacora where id = :b for update"), {"b": bitacora_id}).one()


def bitacora_fue_reabierta(db: Session, bitacora_id: UUID) -> bool:
    """Una bitácora reabierta (M3-02) deja siempre su entrada de reapertura en la auditoría (RN-103,
    CA-266)."""
    return db.execute(
        text("select exists (select 1 from auditoria where tipo_objeto = 'bitacora' and objeto_id = :b "
             "and operacion = 'reapertura')"),
        {"b": bitacora_id},
    ).scalar_one()


def contar_actividades_efectivas(db: Session, persona_id: UUID, bitacora_id: UUID,
                                 *, excluir: UUID | None = None) -> int:
    """Actividades válidas que cuentan para cerrar la jornada (RN-21, RN-109): creadas en ella, o
    continuadas en ella con al menos un AVANCE de esa fecha laboral. Una continuación planificada no
    cuenta (CA-184) y las marcadas como registradas por error tampoco (CA-283). ``excluir`` deja fuera una
    actividad concreta: la comprobación de M3-05 («sin contar esta actividad»)."""
    return db.execute(
        text("select count(*) from actividad a where a.propietaria_id = :p and not a.registrada_por_error "
             "and (cast(:x as uuid) is null or a.id <> cast(:x as uuid)) "
             "and (a.bitacora_origen_id = :b or exists "
             "(select 1 from avance v where v.actividad_id = a.id and v.bitacora_id = :b))"),
        {"p": persona_id, "b": bitacora_id, "x": excluir},
    ).scalar_one()


def bloquear_jornadas_de_actividad(db: Session, actividad_id: UUID, bitacora_origen_id: UUID):
    """Bloquea, en orden de fecha laboral, todas las bitácoras en las que la actividad cuenta: la de origen
    y las de cada fecha con un avance suyo (PA-28 admite avances anteriores al origen). Quien cierra una
    jornada bloquea su fila antes de contar, así que marcar y cerrar se serializan (M3-01, M3-05). El orden
    fijo evita bloqueos cruzados entre dos marcas."""
    return db.execute(
        text("select * from bitacora where id = :o or id in "
             "(select bitacora_id from avance where actividad_id = :a) "
             "order by fecha_laboral, id for update"),
        {"o": bitacora_origen_id, "a": actividad_id},
    ).all()


def existe_avance_posterior_al_origen(db: Session, actividad_id: UUID, fecha_origen: date) -> bool:
    """RN-59: algún avance en una jornada posterior a la de origen de la actividad (PA-28: el origen es la
    fecha laboral de su bitácora de origen, no ``creada_en``). Los de la propia fecha de origen no cuentan."""
    return db.execute(
        text("select exists (select 1 from avance av join bitacora b on b.id = av.bitacora_id "
             "where av.actividad_id = :a and b.fecha_laboral > :f)"),
        {"a": actividad_id, "f": fecha_origen},
    ).scalar_one()


def aplicar_marca_de_error(db: Session, actividad_id: UUID, persona_id: UUID, motivo: str) -> None:
    """La marca es lógica: no cambia el estado, el título ni ningún avance. El momento usa el reloj real."""
    db.execute(
        text("update actividad set registrada_por_error = true, motivo_error = :m, marcada_por = :p, "
             "marcada_en = clock_timestamp() where id = :a"),
        {"m": motivo, "p": persona_id, "a": actividad_id},
    )


def retirar_marca_de_error(db: Session, actividad_id: UUID) -> None:
    db.execute(
        text("update actividad set registrada_por_error = false, motivo_error = null, marcada_por = null, "
             "marcada_en = null where id = :a"),
        {"a": actividad_id},
    )


def cerrar_bitacora(db: Session, bitacora_id: UUID):
    """Estado y momento de cierre juntos (la restricción ``bitacora_cierre_coherente`` lo exige). Reloj
    real, no el inicio de la transacción. No toca ``modificada_en``: cerrar no modifica el contenido."""
    return db.execute(
        text("update bitacora set estado = 'cerrada', cerrada_en = clock_timestamp() where id = :b returning *"),
        {"b": bitacora_id},
    ).one()


def reabrir_bitacora(db: Session, bitacora_id: UUID):
    return db.execute(
        text("update bitacora set estado = 'abierta', cerrada_en = null where id = :b returning *"),
        {"b": bitacora_id},
    ).one()


def guardar_resumen(db: Session, bitacora_id: UUID, resumen: str):
    """Reemplaza el resumen y renueva ``modificada_en`` (RN-18). Usa el reloj real, no el inicio de la
    transacción: una escritura que esperó el bloqueo queda con un momento posterior a la anterior."""
    return db.execute(
        text("update bitacora set resumen = :r, modificada_en = clock_timestamp() where id = :b returning *"),
        {"r": resumen, "b": bitacora_id},
    ).one()


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


def propietaria_y_fecha_de_actividad(db: Session, actividad_id: UUID):
    """``(propietaria_id, fecha laboral de su bitácora de origen)`` de CUALQUIER actividad, o ``None`` si no existe: lo único que la política de visibilidad necesita para decidir si
    la actividad ajena le es visible a quien opera (convenciones 3.1, M4-T6). No devuelve nada más de la actividad."""
    return db.execute(
        text("select a.propietaria_id, b.fecha_laboral from actividad a join bitacora b on b.id = a.bitacora_origen_id where a.id = :a"),
        {"a": actividad_id},
    ).one_or_none()


def propietaria_y_fecha_de_avance(db: Session, avance_id: UUID):
    """``(propietaria_id de la actividad, fecha laboral de la bitácora del avance)`` de CUALQUIER avance, o ``None``: la fecha de un avance es la de su bitácora (RA-01, sección 12.2)."""
    return db.execute(
        text("select a.propietaria_id, b.fecha_laboral from avance av join bitacora b on b.id = av.bitacora_id join actividad a on a.id = av.actividad_id where av.id = :v"),
        {"v": avance_id},
    ).one_or_none()


def listar_avances_de_actividad(db: Session, actividad_id: UUID):
    """La secuencia de la actividad con la fecha laboral de la bitácora de cada avance (IR-09)."""
    return db.execute(
        text("select av.id, b.fecha_laboral, av.registrado_en, av.estado, av.es_reactivacion "
             "from avance av join bitacora b on b.id = av.bitacora_id where av.actividad_id = :a"),
        {"a": actividad_id},
    ).all()


def insertar_avance(db: Session, actividad_id: UUID, bitacora_id: UUID, estado: str, descripcion: str,
                    motivo_bloqueo: str | None, es_reactivacion: bool = False):
    """``registrado_en`` usa el reloj real (``clock_timestamp``), no el inicio de la transacción: así
    un registro que espera el bloqueo de la actividad queda después del que lo precedió."""
    return db.execute(
        text("insert into avance (actividad_id, bitacora_id, registrado_en, estado, descripcion, motivo_bloqueo, "
             "es_reactivacion) values (:a, :b, clock_timestamp(), :e, :d, :m, :r) returning *"),
        {"a": actividad_id, "b": bitacora_id, "e": estado, "d": descripcion, "m": motivo_bloqueo, "r": es_reactivacion},
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


def insertar_continuacion_planificada(db: Session, actividad_id: UUID, bitacora_id: UUID, descripcion: str):
    """Una fila de ``planificacion`` de tipo continuación: no es un avance, no entra en la secuencia y no
    toca el estado de la actividad (IR-14)."""
    return db.execute(
        text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) "
             "values (:a, :b, 'continuacion', :d) returning *"),
        {"a": actividad_id, "b": bitacora_id, "d": descripcion},
    ).one()


def insertar_planificacion_original(db: Session, actividad_id: UUID, bitacora_id: UUID, descripcion: str):
    return db.execute(
        text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) "
             "values (:a, :b, 'original', :d) returning *"),
        {"a": actividad_id, "b": bitacora_id, "d": descripcion},
    ).one()


def obtener_avance_propio(db: Session, persona_id: UUID, avance_id: UUID, *, bloquear: bool = False):
    """El avance solo si su actividad es de la persona, con la fecha laboral y el estado de su bitácora. Un avance
    ajeno es indistinguible de uno inexistente (T-01). ``bloquear`` toma la fila del avance (FOR UPDATE OF av)."""
    return db.execute(
        text("select av.*, b.fecha_laboral, b.estado as estado_bitacora from avance av "
             "join bitacora b on b.id = av.bitacora_id join actividad a on a.id = av.actividad_id "
             "where av.id = :v and a.propietaria_id = :p" + (" for update of av" if bloquear else "")),
        {"v": avance_id, "p": persona_id},
    ).one_or_none()


def corregir_avance(db: Session, avance_id: UUID, estado: str, descripcion: str, motivo_bloqueo: str | None):
    """Solo cambia lo corregible. ``modificado_en`` usa el reloj real (como ``registrado_en``): una corrección que
    esperó el bloqueo queda posterior a la anterior. Ni la fecha laboral, ni el momento de registro, ni la condición
    de reactivación se tocan (la base lo garantiza)."""
    return db.execute(
        text("update avance set estado = :e, descripcion = :d, motivo_bloqueo = :m, modificado_en = clock_timestamp() "
             "where id = :v returning *"),
        {"e": estado, "d": descripcion, "m": motivo_bloqueo, "v": avance_id},
    ).one()
