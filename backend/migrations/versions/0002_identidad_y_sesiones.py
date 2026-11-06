"""Identidad y sesiones (DB-02, subconjunto de la Entrega 2).

Estructuras técnicas de ADR-002, fuera de las nueve entidades de dominio: IDENTIDAD y SESION.
No se crean CODIGO_UNICO ni OPERADOR: pertenecen a las órdenes de provisión y a los códigos de
acceso, que quedan fuera de esta entrega.

- Solo se guardan hashes: de la contraseña (Argon2id, con sus parámetros dentro de la propia
  cadena) y del secreto de la sesión. Nunca la contraseña ni el secreto en claro.
- El token CSRF no se almacena: se deriva con HMAC del secreto de la sesión (ver app/seguridad).
"""

import re

from alembic import op

from app.config import get_settings

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _rol_app() -> str:
    rol = get_settings().app_db_role
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", rol):
        raise ValueError("APP_DB_ROLE no es un identificador válido")
    return f'"{rol}"'


def upgrade() -> None:
    op.execute("""
        CREATE TABLE identidad (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            persona_id uuid NOT NULL UNIQUE REFERENCES persona (id),
            -- Identificador de acceso normalizado (recortado y en minúsculas): la unicidad se
            -- comprueba sobre el valor normalizado, de modo que 'Ana' y 'ana' no coexisten.
            identificador_acceso text NOT NULL UNIQUE,
            -- Vacío hasta completar el primer acceso. Cadena Argon2id (incluye sus parámetros).
            hash_contrasena text,
            CONSTRAINT identidad_identificador_normalizado CHECK (
                identificador_acceso <> ''
                AND identificador_acceso = lower(btrim(identificador_acceso))
            )
        )
    """)
    op.execute("""
        CREATE TABLE sesion (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            identidad_id uuid NOT NULL REFERENCES identidad (id),
            -- Hash SHA-256 (hexadecimal) del secreto aleatorio de la cookie
            secreto_hash text NOT NULL UNIQUE,
            creada_en timestamptz NOT NULL DEFAULT now(),
            ultimo_uso_en timestamptz NOT NULL DEFAULT now(),
            caduca_absoluta_en timestamptz NOT NULL,
            revocada_en timestamptz
        )
    """)
    op.execute("CREATE INDEX sesion_identidad_idx ON sesion (identidad_id)")

    rol = _rol_app()
    op.execute(f"GRANT SELECT ON identidad TO {rol}")
    # La sesión se crea, se actualiza su último uso y se revoca; no se borra.
    op.execute(f"GRANT SELECT, INSERT ON sesion TO {rol}")
    op.execute(f"GRANT UPDATE (ultimo_uso_en, revocada_en) ON sesion TO {rol}")


def downgrade() -> None:
    op.execute("DROP TABLE sesion")
    op.execute("DROP TABLE identidad")
