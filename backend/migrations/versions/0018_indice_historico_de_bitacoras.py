"""Índice del histórico de bitácoras (M4-T2; contrato M4-02; aprobado el 2026-11-18).

Qué añade: UN índice, ``bitacora_historico_idx`` sobre ``bitacora (fecha_laboral, persona_id, id)``. No cambia ningún dato, restricción, permiso ni función.

Por qué: el histórico (``GET /api/v1/historico``) lista las bitácoras que quien consulta puede leer en un rango de fechas, ordenadas por ``(fecha_laboral,
persona_id, id)`` y paginadas por posición. Sin este índice, el único apoyo para el rango es ``bitacora_unica_por_persona_y_fecha (persona_id, fecha_laboral)``, que no sirve
para ordenar por fecha: PostgreSQL recorre TODAS las bitácoras del rango de la organización, comprueba la pertenencia de cada una y ordena. Con el orden de la paginación
puede leer el índice en ese mismo orden, comprobar la autorización fila a fila y detenerse en cuanto reúne la página (``LIMIT``).

Evidencia (PostgreSQL desechable, ~157.000 bitácoras, 1.040 personas, 40 equipos): la consulta sin filtro de persona pasa de 320–380 ms a 3–4 ms; con filtro por persona no
cambia (ya usaba el índice por persona y fecha). Las mediciones de la migración (escritura y peor caso) están en el plan de M4 (``docs/backlog/tickets/m4-plan-implementacion.md``).

Es reversible y no bloquea escrituras más de lo que cualquier ``CREATE INDEX`` normal hace en una tabla de este tamaño; en una instalación con muchos datos puede crearse
con ``CREATE INDEX CONCURRENTLY`` fuera de una transacción si se prefiere (no se usa aquí porque las migraciones de este proyecto se ejecutan dentro de una transacción).
"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX bitacora_historico_idx ON bitacora (fecha_laboral, persona_id, id)")


def downgrade() -> None:
    op.execute("DROP INDEX bitacora_historico_idx")
