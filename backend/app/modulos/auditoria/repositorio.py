"""Acceso de solo lectura a la auditoría y a los datos que decide la política de visibilidad sobre los registros auditados (SQL explícito)."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido.visibilidad import Consultante, condicion_lectura_auditoria

# Propietaria y fecha laboral del PROPIO registro auditado, según su tipo: la fecha que determina su equipo (sección 12.2 del modelo de datos): la de la bitácora, la de la bitácora de
# origen de la actividad y la de la bitácora del avance o de la planificación. Es lo único que se lee del registro: la política decide con eso, antes de leer ninguna entrada.
_REGISTRO = {
    "bitacora": "select b.persona_id as propietaria_id, b.fecha_laboral from bitacora b where b.id = :o",
    "actividad": "select a.propietaria_id, b.fecha_laboral from actividad a join bitacora b on b.id = a.bitacora_origen_id where a.id = :o",
    "avance": "select a.propietaria_id, b.fecha_laboral from avance av join actividad a on a.id = av.actividad_id join bitacora b on b.id = av.bitacora_id where av.id = :o",
    "planificacion": "select a.propietaria_id, b.fecha_laboral from planificacion pl join actividad a on a.id = pl.actividad_id join bitacora b on b.id = pl.bitacora_id where pl.id = :o",
}


def propietaria_y_fecha_del_registro(db: Session, tipo_objeto: str, objeto_id: UUID):
    """``(propietaria_id, fecha_laboral)`` del registro, o ``None`` si no existe. Quien no puede verlo y un registro inexistente son lo mismo para quien consulta (CA-286, T-01): el
    servicio decide con la política de M1 y responde lo mismo en ambos casos."""
    return db.execute(text(_REGISTRO[tipo_objeto]), {"o": objeto_id}).one_or_none()


def listar_entradas(db: Session, consultante: Consultante, tipo_objeto: str, objeto_id: UUID, operacion: str | None,
                    cursor: tuple[str, str] | None, cantidad: int):
    """Entradas de UN registro en orden cronológico (momento e identificador, para que la paginación sea estable). La autorización de CADA entrada se aplica al seleccionar, con
    ``condicion_lectura_auditoria`` (RA-10: la propietaria, o el supervisor vigente del equipo de la fecha laboral del registro; solo entradas hechas por personas, así que las de
    provisión administrativa no se devuelven nunca: D-11, CA-285), antes de ordenar y de paginar. Se piden ``cantidad`` filas (el límite más una) para saber si hay más. Solo lectura."""
    autorizada, parametros = condicion_lectura_auditoria(consultante, "au.propietaria_registro_id", "au.fecha_laboral_registro", "au.tipo_autor")
    condiciones = ["au.tipo_objeto = :t", "au.objeto_id = :o", autorizada]
    parametros.update({"t": tipo_objeto, "o": objeto_id, "n": cantidad})
    if operacion is not None:
        condiciones.append("au.operacion = :op")
        parametros["op"] = operacion
    if cursor is not None:
        condiciones.append("(au.momento, au.id) > (cast(:c_momento as timestamptz), cast(:c_id as uuid))")
        parametros["c_momento"], parametros["c_id"] = cursor
    return db.execute(
        text("select au.id, au.momento, au.tipo_autor, au.autor_persona_id, au.operacion, au.tipo_objeto, au.objeto_id, "
             "au.propietaria_registro_id, au.fecha_laboral_registro, au.motivo, au.valor_anterior, au.valor_nuevo "
             "from auditoria au where " + " and ".join(condiciones) + " order by au.momento, au.id limit :n"),
        parametros,
    ).all()
