"""Permisos mínimos de actualización para completar M2 (y el cierre y reapertura de M3-01/M3-02).

Hasta la 0005 la aplicación solo podía insertar y leer en bitácoras, actividades, planificaciones y
avances (0003). Las operaciones aprobadas necesitan actualizar solo estas COLUMNAS, nunca la tabla
completa:

- ``actividad.estado_actual``: copia derivada de la secuencia de avances (IR-12). Lo escribe
  únicamente el procedimiento que registra avances, en la misma transacción (M2-05, M2-06).
  La propietaria, la bitácora de origen y el título siguen siendo inmutables (disparador de 0003).
- ``bitacora.resumen`` y ``bitacora.modificada_en``: guardar el resumen libre (M2-02) y renovar la
  fecha de modificación (RN-18).
- ``bitacora.estado`` y ``bitacora.cerrada_en``: cierre y reapertura manual (M3-01, M3-02). La
  restricción ``bitacora_cierre_coherente`` de 0003 impide un estado sin su momento de cierre.

Siguen SIN permiso de actualización: ``avance`` y ``planificacion`` (no se editan ni se borran;
las correcciones de M3-03 no forman parte de esta entrega), la identidad de las bitácoras
(persona y fecha laboral) y todo lo relativo a la marca de error (M3-05).
"""

import re

from alembic import op

from app.config import get_settings

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def _rol_app() -> str:
    rol = get_settings().app_db_role
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", rol):
        raise ValueError("APP_DB_ROLE no es un identificador válido")
    return f'"{rol}"'


def upgrade() -> None:
    rol = _rol_app()
    op.execute(f"GRANT UPDATE (estado_actual) ON actividad TO {rol}")
    op.execute(f"GRANT UPDATE (resumen, modificada_en, estado, cerrada_en) ON bitacora TO {rol}")


def downgrade() -> None:
    rol = _rol_app()
    op.execute(f"REVOKE UPDATE (estado_actual) ON actividad FROM {rol}")
    op.execute(f"REVOKE UPDATE (resumen, modificada_en, estado, cerrada_en) ON bitacora FROM {rol}")
