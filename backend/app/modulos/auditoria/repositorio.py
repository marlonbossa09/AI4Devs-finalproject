"""Acceso de solo lectura a la auditoría y a la propiedad de los registros auditados (SQL explícito)."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

# Cómo se comprueba que el registro auditado es de la persona, según su tipo. Es la propiedad del PROPIO registro
# (su bitácora, su actividad, o la actividad a la que pertenece el avance o la planificación), no la de las entradas.
_PROPIEDAD = {
    "bitacora": "select 1 from bitacora where id = :o and persona_id = :p",
    "actividad": "select 1 from actividad where id = :o and propietaria_id = :p",
    "avance": "select 1 from avance av join actividad a on a.id = av.actividad_id where av.id = :o and a.propietaria_id = :p",
    "planificacion": "select 1 from planificacion pl join actividad a on a.id = pl.actividad_id "
                     "where pl.id = :o and a.propietaria_id = :p",
}


def registro_es_de(db: Session, tipo_objeto: str, objeto_id: UUID, persona_id: UUID) -> bool:
    """¿Existe el registro Y es de la persona? Quien no es la propietaria y un registro inexistente son lo mismo
    para quien consulta (CA-286, T-01): la respuesta no distingue entre ambos."""
    return db.execute(text(_PROPIEDAD[tipo_objeto]), {"o": objeto_id, "p": persona_id}).first() is not None


def listar_entradas(db: Session, persona_id: UUID, tipo_objeto: str, objeto_id: UUID, operacion: str | None,
                    cursor: tuple[str, str] | None, cantidad: int):
    """Entradas de UN registro en orden cronológico (momento e identificador, para que la paginación sea estable).
    Solo operaciones de dominio hechas por personas: las de provisión administrativa no se devuelven nunca (D-11,
    CA-285). Se piden ``cantidad`` filas (el límite más una) para saber si hay más. Solo lectura."""
    condiciones = ["tipo_autor = 'persona'", "tipo_objeto = :t", "objeto_id = :o", "propietaria_registro_id = :p"]
    parametros: dict = {"t": tipo_objeto, "o": objeto_id, "p": persona_id, "n": cantidad}
    if operacion is not None:
        condiciones.append("operacion = :op")
        parametros["op"] = operacion
    if cursor is not None:
        condiciones.append("(momento, id) > (cast(:c_momento as timestamptz), cast(:c_id as uuid))")
        parametros["c_momento"], parametros["c_id"] = cursor
    return db.execute(
        text("select id, momento, tipo_autor, autor_persona_id, operacion, tipo_objeto, objeto_id, "
             "propietaria_registro_id, fecha_laboral_registro, motivo, valor_anterior, valor_nuevo "
             "from auditoria where " + " and ".join(condiciones) + " order by momento, id limit :n"),
        parametros,
    ).all()
