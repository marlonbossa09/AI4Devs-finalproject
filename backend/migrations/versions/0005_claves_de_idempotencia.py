"""Registro de claves de idempotencia (DB-05, convenciones de la API 5.3 / T-04).

Estructura técnica fuera de las nueve entidades de dominio. Guarda, por persona, operación y
clave, la huella de la petición y la respuesta de los resultados con éxito (2xx), durante una
ventana configurable. La unicidad garantiza una sola fila ante peticiones simultáneas.
"""

import re

from alembic import op

from app.config import get_settings

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _rol_app() -> str:
    rol = get_settings().app_db_role
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", rol):
        raise ValueError("APP_DB_ROLE no es un identificador válido")
    return f'"{rol}"'


def upgrade() -> None:
    op.execute("""
        CREATE TABLE clave_idempotencia (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            persona_id uuid NOT NULL REFERENCES persona (id),
            operacion text NOT NULL,
            clave text NOT NULL,
            -- Hash SHA-256 (hexadecimal) del contenido de la petición
            huella text NOT NULL,
            estado_http integer NOT NULL,
            respuesta jsonb NOT NULL,
            creada_en timestamptz NOT NULL DEFAULT now(),
            caduca_en timestamptz NOT NULL,
            CONSTRAINT clave_idempotencia_unica UNIQUE (persona_id, operacion, clave)
        )
    """)
    # Las claves caducadas se eliminan para reutilizarse como nuevas (único borrado permitido
    # a la aplicación, y solo en esta estructura técnica).
    op.execute(f"GRANT SELECT, INSERT, DELETE ON clave_idempotencia TO {_rol_app()}")


def downgrade() -> None:
    op.execute("DROP TABLE clave_idempotencia")
