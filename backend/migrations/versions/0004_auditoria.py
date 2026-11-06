"""Auditoría de solo anexado (DB-04).

Una entrada por operación (docs/modelo-datos/modelo-datos.md, sección 3.9; IR-23 a IR-26 e
IR-34 a IR-36).

- IR-23: no se actualiza ni se borra ninguna entrada. Se garantiza de dos formas: la aplicación
  solo tiene INSERT y SELECT, y un disparador rechaza UPDATE y DELETE para cualquier rol.
- IR-34: si el autor es una persona, ``autor_persona_id`` está presente y no hay referencia de
  provisión; si es provisión, ocurre lo contrario.
"""

import re

from alembic import op

from app.config import get_settings

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

OPERACIONES = (
    "reapertura", "cierre", "correccion", "modificacion_jornada_pasada", "reactivacion",
    "marca_error", "reversion_marca", "alta", "cambio_pertenencia", "finalizacion_pertenencia",
    "cancelacion_operacion", "sustitucion_operacion", "desactivacion_acceso",
    "entrega_acceso", "recuperacion_acceso",
)


def _rol_app() -> str:
    rol = get_settings().app_db_role
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", rol):
        raise ValueError("APP_DB_ROLE no es un identificador válido")
    return f'"{rol}"'


def upgrade() -> None:
    lista = ", ".join(f"'{o}'" for o in OPERACIONES)
    op.execute(f"""
        CREATE TABLE auditoria (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            momento timestamptz NOT NULL DEFAULT now(),
            tipo_autor text NOT NULL CHECK (tipo_autor IN ('persona', 'provision')),
            autor_persona_id uuid REFERENCES persona (id),
            referencia_provision text,
            operacion text NOT NULL CHECK (operacion IN ({lista})),
            tipo_objeto text NOT NULL,
            objeto_id uuid NOT NULL,
            propietaria_registro_id uuid NOT NULL REFERENCES persona (id),
            fecha_laboral_registro date,
            motivo text,
            valor_anterior jsonb,
            valor_nuevo jsonb,
            CONSTRAINT auditoria_autor_exclusivo CHECK (
                (tipo_autor = 'persona' AND autor_persona_id IS NOT NULL AND referencia_provision IS NULL)
                OR (tipo_autor = 'provision' AND autor_persona_id IS NULL AND referencia_provision IS NOT NULL)
            )
        )
    """)
    op.execute("CREATE INDEX auditoria_objeto_idx ON auditoria (tipo_objeto, objeto_id, momento)")
    op.execute("""
        CREATE FUNCTION auditoria_solo_anexado() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'La auditoría es de solo anexado: no se actualiza ni se borra'
                USING ERRCODE = 'integrity_constraint_violation';
        END $$
    """)
    op.execute("""
        CREATE TRIGGER auditoria_inmutable BEFORE UPDATE OR DELETE ON auditoria
        FOR EACH ROW EXECUTE FUNCTION auditoria_solo_anexado()
    """)
    op.execute(f"GRANT SELECT, INSERT ON auditoria TO {_rol_app()}")


def downgrade() -> None:
    op.execute("DROP TABLE auditoria")
    op.execute("DROP FUNCTION auditoria_solo_anexado()")
