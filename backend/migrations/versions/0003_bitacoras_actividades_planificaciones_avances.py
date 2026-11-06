"""Bitácoras, actividades, planificaciones y avances (DB-03).

Núcleo de M2 y M3 (docs/modelo-datos/modelo-datos.md, secciones 3.5 a 3.8 y 6.2). En esta
entrega solo se escriben bitácoras, actividades y planificaciones; AVANCE existe como esquema,
sin operaciones que lo escriban todavía.

Invariantes en la base de datos:
- IR-01: una bitácora por persona y fecha laboral.
- IR-06: la propietaria de una actividad no cambia (disparador). IR-33: tampoco su título.
- IR-08: un avance Bloqueada exige motivo; la descripción no puede estar vacía.
- IR-16: una actividad tiene como máximo una planificación original.
- RN-112: el título de una actividad no puede estar vacío.
Permisos: la aplicación no puede borrar nada (IR-26) ni editar planificaciones (IR-16).
"""

import re

from alembic import op

from app.config import get_settings

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

ESTADOS = "'Pendiente', 'En progreso', 'Bloqueada', 'Completada'"


def _rol_app() -> str:
    rol = get_settings().app_db_role
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", rol):
        raise ValueError("APP_DB_ROLE no es un identificador válido")
    return f'"{rol}"'


def upgrade() -> None:
    op.execute("""
        CREATE TABLE bitacora (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            persona_id uuid NOT NULL REFERENCES persona (id),
            fecha_laboral date NOT NULL,
            resumen text NOT NULL DEFAULT '',
            estado text NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta', 'cerrada')),
            cerrada_en timestamptz,
            creada_en timestamptz NOT NULL DEFAULT now(),
            modificada_en timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT bitacora_unica_por_persona_y_fecha UNIQUE (persona_id, fecha_laboral),
            CONSTRAINT bitacora_cierre_coherente CHECK ((estado = 'cerrada') = (cerrada_en IS NOT NULL))
        )
    """)
    op.execute(f"""
        CREATE TABLE actividad (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            propietaria_id uuid NOT NULL REFERENCES persona (id),
            bitacora_origen_id uuid NOT NULL REFERENCES bitacora (id),
            titulo text NOT NULL CHECK (btrim(titulo) <> ''),
            origen text NOT NULL CHECK (origen IN ('planificada', 'no_planificada')),
            estado_actual text NOT NULL DEFAULT 'Pendiente' CHECK (estado_actual IN ({ESTADOS})),
            registrada_por_error boolean NOT NULL DEFAULT false,
            motivo_error text,
            marcada_por uuid REFERENCES persona (id),
            marcada_en timestamptz,
            creada_en timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX actividad_propietaria_idx ON actividad (propietaria_id)")
    op.execute("CREATE INDEX actividad_bitacora_origen_idx ON actividad (bitacora_origen_id)")

    # IR-06 e IR-33: ni la propietaria, ni la bitácora de origen, ni el título cambian.
    op.execute("""
        CREATE FUNCTION actividad_campos_inmutables() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.propietaria_id IS DISTINCT FROM OLD.propietaria_id
               OR NEW.bitacora_origen_id IS DISTINCT FROM OLD.bitacora_origen_id
               OR NEW.titulo IS DISTINCT FROM OLD.titulo THEN
                RAISE EXCEPTION 'La propietaria, la bitácora de origen y el título de una actividad no se modifican'
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER actividad_inmutable BEFORE UPDATE ON actividad
        FOR EACH ROW EXECUTE FUNCTION actividad_campos_inmutables()
    """)

    op.execute("""
        CREATE TABLE planificacion (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            actividad_id uuid NOT NULL REFERENCES actividad (id),
            bitacora_id uuid NOT NULL REFERENCES bitacora (id),
            tipo text NOT NULL CHECK (tipo IN ('original', 'continuacion')),
            descripcion text NOT NULL DEFAULT '',
            registrada_en timestamptz NOT NULL DEFAULT now()
        )
    """)
    # IR-16: como máximo una planificación original por actividad
    op.execute("""
        CREATE UNIQUE INDEX planificacion_una_original_por_actividad
        ON planificacion (actividad_id) WHERE tipo = 'original'
    """)
    op.execute("CREATE INDEX planificacion_bitacora_idx ON planificacion (bitacora_id)")

    op.execute(f"""
        CREATE TABLE avance (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            actividad_id uuid NOT NULL REFERENCES actividad (id),
            bitacora_id uuid NOT NULL REFERENCES bitacora (id),
            registrado_en timestamptz NOT NULL DEFAULT now(),
            estado text NOT NULL CHECK (estado IN ({ESTADOS})),
            descripcion text NOT NULL CHECK (btrim(descripcion) <> ''),
            motivo_bloqueo text,
            es_reactivacion boolean NOT NULL DEFAULT false,
            CONSTRAINT avance_bloqueada_exige_motivo CHECK (
                estado <> 'Bloqueada' OR (motivo_bloqueo IS NOT NULL AND btrim(motivo_bloqueo) <> '')
            )
        )
    """)
    # Orden total de la secuencia (IR-09) y consulta por actividad
    op.execute("CREATE INDEX avance_actividad_idx ON avance (actividad_id, registrado_en, id)")
    op.execute("CREATE INDEX avance_bitacora_idx ON avance (bitacora_id)")

    rol = _rol_app()
    # Permisos mínimos: INSERT y SELECT. Sin UPDATE ni DELETE (no se borra; la planificación no
    # se edita). Las actualizaciones de estado, marcas y cierres se concederán con sus operaciones.
    for tabla in ("bitacora", "actividad", "planificacion", "avance"):
        op.execute(f"GRANT SELECT, INSERT ON {tabla} TO {rol}")


def downgrade() -> None:
    op.execute("DROP TABLE avance")
    op.execute("DROP TABLE planificacion")
    op.execute("DROP TABLE actividad")
    op.execute("DROP FUNCTION actividad_campos_inmutables()")
    op.execute("DROP TABLE bitacora")
