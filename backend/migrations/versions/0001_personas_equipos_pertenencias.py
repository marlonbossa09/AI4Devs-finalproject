"""Personas, equipos y pertenencias (DB-01).

ORGANIZACION, EQUIPO, PERSONA y PERTENENCIA, con las restricciones que la base de datos puede
expresar (docs/modelo-datos/modelo-datos.md, secciones 3.1 a 3.4 y 6.1):
- IR-02/IR-28: una persona no tiene intervalos solapados; solo el último puede carecer de fin.
- IR-03: un equipo tiene como máximo un supervisor por fecha.
- IR-27: intervalos semiabiertos [desde, hasta_exclusivo).
Lo no expresable (contigüidad, equipo con colaboradores siempre con supervisor, fecha efectiva
posterior a la actual) se valida en la capa de servicio (DM-05).

Permisos: la aplicación solo lee estas tablas. No hay borrado físico (IR-26).
"""

import re

from alembic import op

from app.config import get_settings

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _rol_app() -> str:
    rol = get_settings().app_db_role
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", rol):
        raise ValueError("APP_DB_ROLE no es un identificador válido")
    return f'"{rol}"'


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.execute("""
        CREATE TABLE organizacion (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nombre text NOT NULL CHECK (btrim(nombre) <> ''),
            zona_horaria text NOT NULL CHECK (btrim(zona_horaria) <> '')
        )
    """)
    op.execute("""
        CREATE TABLE equipo (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            organizacion_id uuid NOT NULL REFERENCES organizacion (id),
            nombre text NOT NULL CHECK (btrim(nombre) <> '')
        )
    """)
    op.execute("""
        CREATE TABLE persona (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nombre text NOT NULL CHECK (btrim(nombre) <> ''),
            acceso_desactivado_en timestamptz
        )
    """)
    op.execute("""
        CREATE TABLE pertenencia (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            persona_id uuid NOT NULL REFERENCES persona (id),
            equipo_id uuid NOT NULL REFERENCES equipo (id),
            rol text NOT NULL CHECK (rol IN ('colaborador', 'supervisor')),
            desde date NOT NULL,
            hasta_exclusivo date,
            CONSTRAINT pertenencia_intervalo_valido
                CHECK (hasta_exclusivo IS NULL OR hasta_exclusivo > desde),
            -- IR-02, IR-28: sin solapes por persona; un intervalo sin fin solapa con cualquier
            -- posterior, de modo que solo el último puede carecer de fin.
            CONSTRAINT pertenencia_sin_solape_por_persona
                EXCLUDE USING gist (
                    persona_id WITH =,
                    daterange(desde, hasta_exclusivo, '[)') WITH &&
                ),
            -- IR-03: como máximo un supervisor por equipo y fecha.
            CONSTRAINT pertenencia_un_supervisor_por_equipo_y_fecha
                EXCLUDE USING gist (
                    equipo_id WITH =,
                    daterange(desde, hasta_exclusivo, '[)') WITH &&
                ) WHERE (rol = 'supervisor')
        )
    """)
    op.execute("CREATE INDEX pertenencia_persona_idx ON pertenencia (persona_id, desde)")

    rol = _rol_app()
    for tabla in ("organizacion", "equipo", "persona", "pertenencia"):
        op.execute(f"GRANT SELECT ON {tabla} TO {rol}")


def downgrade() -> None:
    for tabla in ("pertenencia", "persona", "equipo", "organizacion"):
        op.execute(f"DROP TABLE {tabla}")
