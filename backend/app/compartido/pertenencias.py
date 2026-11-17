"""«Equipo en una fecha»: la pertenencia de una persona a un equipo en una fecha laboral (DM-04, IR-27).

Es la ÚNICA definición de qué intervalo de pertenencia cubre una fecha. La política de acceso, la política de
visibilidad histórica y cualquier consulta futura (M4) la usan; ningún módulo vuelve a calcularla.

- Los intervalos son semiabiertos ``[desde, hasta_exclusivo)``: ``desde`` es inclusive y ``hasta_exclusivo`` es el primer
  día que ya no pertenece. Un intervalo sin ``hasta_exclusivo`` no tiene fin (IR-27).
- Una persona tiene como máximo un intervalo por fecha: lo garantiza la base de datos (restricción de exclusión
  ``pertenencia_sin_solape_por_persona``, IR-02). Si aun así hubiera dos, la consulta falla en voz alta en lugar de
  elegir uno.
- La organización se deduce del equipo (cada equipo pertenece a una sola organización).
- Se incluyen los intervalos programados (de fecha posterior a la actual): la planificación futura se evalúa con la
  pertenencia aplicable a su fecha (RA-02).
"""

import re
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

_IDENTIFICADOR_SQL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


def identificador_sql(valor: str) -> str:
    """Valida que ``valor`` sea una columna o alias escrito por el código (``tabla.columna``), nunca texto de una
    petición: los predicados SQL de la política se componen con identificadores, no con valores."""
    if not _IDENTIFICADOR_SQL.match(valor):
        raise ValueError(f"Identificador SQL no admitido: {valor!r}")
    return valor


def cubre(alias: str, fecha: str) -> str:
    """Condición SQL: el intervalo ``alias`` de ``pertenencia`` cubre ``fecha`` (una columna, un alias o un parámetro
    ``:nombre``). Usa la misma expresión de rango que la restricción de exclusión de la tabla, así que PostgreSQL puede
    apoyarse en su índice GiST."""
    return f"daterange({identificador_sql(alias)}.desde, {identificador_sql(alias)}.hasta_exclusivo, '[)') @> {fecha}"


@dataclass(frozen=True)
class Pertenencia:
    persona_id: UUID
    equipo_id: UUID
    organizacion_id: UUID
    rol: str
    desde: date
    hasta_exclusivo: date | None


def pertenencia_en_fecha(db: Session, persona_id: UUID, fecha: date) -> Pertenencia | None:
    """La pertenencia de la persona en la fecha laboral, o ``None`` si ninguna la cubre (antes de la primera, en una
    inactividad o desde la fecha efectiva de una finalización)."""
    fila = db.execute(
        text(
            "select p.persona_id, p.equipo_id, e.organizacion_id, p.rol, p.desde, p.hasta_exclusivo "
            "from pertenencia p join equipo e on e.id = p.equipo_id "
            f"where p.persona_id = :persona and {cubre('p', ':fecha')}"
        ),
        {"persona": persona_id, "fecha": fecha},
    ).one_or_none()
    return None if fila is None else Pertenencia(*fila)


def equipo_en_fecha(db: Session, persona_id: UUID, fecha: date) -> UUID | None:
    """DM-04: el equipo de la persona en la fecha laboral (RN-36), o ``None``."""
    pertenencia = pertenencia_en_fecha(db, persona_id, fecha)
    return None if pertenencia is None else pertenencia.equipo_id
