"""Purga de los códigos de un solo uso terminados (M1-T8.6; ADR-002, D6 del 2026-11-17).

Qué cambia: ÚNICAMENTE concede al rol de provisión el permiso ``DELETE`` sobre ``codigo_unico``, que la migración 0014 reservó expresamente
para esta orden («no se concede todavía permiso de borrado a ningún rol»). No crea tablas, columnas ni funciones.

Por qué basta y es seguro:

- La retención ya la impone la base de datos, no el código de la orden: el disparador ``codigo_unico_retencion`` (0014) impide borrar un código
  que terminó (usado, invalidado o caducado) hace menos de 30 días, y uno todavía pendiente, para CUALQUIER rol, también el propietario y también
  este rol de provisión. La orden ``purgar-codigos`` aplica el mismo criterio por su parte, así que un fallo de cualquiera de las dos capas no
  basta para borrar un código antes de tiempo.
- El rol de provisión sigue sin poder leer ``hash_codigo`` (no tiene ``SELECT`` sobre esa columna), sin poder usar un código ni cambiar sus
  intentos, y sin ``TRUNCATE``. Para borrar solo necesita leer las columnas de fecha, que ya tiene.
- La aplicación sigue sin NINGÚN permiso sobre ``codigo_unico``.
- No toca la auditoría funcional: ``auditoria`` guarda el identificador del código en su valor JSON, sin clave ajena, y esta migración no concede nada
  sobre ella.
"""

import re

from alembic import op
from sqlalchemy import text

from app.config import get_settings

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def _rol(nombre: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", nombre):
        raise ValueError("El nombre del rol no es un identificador válido")
    return nombre


def upgrade() -> None:
    prov = _rol(get_settings().provision_db_role)
    existe = op.get_bind().execute(text("select 1 from pg_roles where rolname = :r"), {"r": prov}).first()
    if existe is None:
        raise RuntimeError(
            f"No existe el rol de PostgreSQL de provisión {prov!r}: ver backend/scripts/provision_rol_de_provision.sql "
            "(debe existir antes de migrar; la migración no puede crear roles)."
        )
    op.execute(f'GRANT DELETE ON codigo_unico TO "{prov}"')


def downgrade() -> None:
    prov = _rol(get_settings().provision_db_role)
    existe = op.get_bind().execute(text("select 1 from pg_roles where rolname = :r"), {"r": prov}).first()
    if existe is not None:
        op.execute(f'REVOKE DELETE ON codigo_unico FROM "{prov}"')
