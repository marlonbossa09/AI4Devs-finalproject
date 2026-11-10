"""Marca de actividad registrada por error y su reversión (M3-05, M3-06).

Hasta la 0006 la aplicación no podía tocar la marca. Esta migración concede el permiso mínimo y añade
las restricciones de coherencia de la marca; no crea tablas ni columnas (la marca ya existe desde la 0003).

Permiso (solo COLUMNAS, nunca la tabla completa): ``actividad.registrada_por_error``,
``motivo_error``, ``marcada_por`` y ``marcada_en``. La propietaria, la bitácora de origen y el título
siguen siendo inmutables (disparador de 0003). Siguen sin permiso de actualización ``avance`` y
``planificacion``, y no existe ningún permiso de borrado: la marca es lógica (RN-59, RN-60).

Restricciones:

- ``actividad_marca_coherente``: con marca vigente constan el motivo (no vacío), quién la aplicó y
  cuándo; sin marca vigente ninguno de los tres. Así la reversión deja la actividad limpia y la
  auditoría conserva la marca anterior (CA-122).
- ``actividad_marca_inmutable`` (disparador): una marca vigente no se reescribe (cambiar motivo, autora o
  momento sin revertirla antes) y no se aplica a una actividad con avances en jornadas posteriores a su
  jornada de origen (RN-59, IR-25). El servicio ya lo valida; esto lo garantiza aunque algo lo eluda.
- ``avance_sobre_actividad_marcada`` y ``continuacion_sobre_actividad_marcada`` (disparadores): una
  actividad con marca vigente no recibe avances, reactivaciones ni continuaciones planificadas (IR-18). El
  disparador toma ``FOR SHARE`` sobre la fila de la actividad, así que se serializa con una marca
  simultánea y ve su resultado una vez confirmada.
"""

import re

from alembic import op

from app.config import get_settings

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

COLUMNAS_DE_LA_MARCA = "registrada_por_error, motivo_error, marcada_por, marcada_en"


def _rol_app() -> str:
    rol = get_settings().app_db_role
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", rol):
        raise ValueError("APP_DB_ROLE no es un identificador válido")
    return f'"{rol}"'


def upgrade() -> None:
    op.execute(f"GRANT UPDATE ({COLUMNAS_DE_LA_MARCA}) ON actividad TO {_rol_app()}")
    op.execute("""
        ALTER TABLE actividad ADD CONSTRAINT actividad_marca_coherente CHECK (
            (registrada_por_error
                AND btrim(coalesce(motivo_error, '')) <> ''
                AND marcada_por IS NOT NULL
                AND marcada_en IS NOT NULL)
            OR (NOT registrada_por_error
                AND motivo_error IS NULL
                AND marcada_por IS NULL
                AND marcada_en IS NULL)
        )
    """)

    op.execute("""
        CREATE FUNCTION actividad_marca_valida() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.registrada_por_error AND NEW.registrada_por_error
               AND (NEW.motivo_error IS DISTINCT FROM OLD.motivo_error
                    OR NEW.marcada_por IS DISTINCT FROM OLD.marcada_por
                    OR NEW.marcada_en IS DISTINCT FROM OLD.marcada_en) THEN
                RAISE EXCEPTION 'Una marca de error vigente no se reescribe: se revierte antes'
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            IF NEW.registrada_por_error AND NOT OLD.registrada_por_error AND EXISTS (
                SELECT 1
                FROM avance av
                JOIN bitacora b ON b.id = av.bitacora_id
                JOIN bitacora o ON o.id = NEW.bitacora_origen_id
                WHERE av.actividad_id = NEW.id AND b.fecha_laboral > o.fecha_laboral
            ) THEN
                RAISE EXCEPTION 'No se marca por error una actividad con avances en jornadas posteriores a su origen'
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER actividad_marca_inmutable
        BEFORE UPDATE OF registrada_por_error, motivo_error, marcada_por, marcada_en ON actividad
        FOR EACH ROW EXECUTE FUNCTION actividad_marca_valida()
    """)

    op.execute("""
        CREATE FUNCTION actividad_marcada_no_admite_registros() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            marcada boolean;
        BEGIN
            SELECT registrada_por_error INTO marcada FROM actividad WHERE id = NEW.actividad_id FOR SHARE;
            IF marcada THEN
                RAISE EXCEPTION 'Una actividad marcada como registrada por error no admite avances ni continuaciones'
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER avance_sobre_actividad_marcada BEFORE INSERT ON avance
        FOR EACH ROW EXECUTE FUNCTION actividad_marcada_no_admite_registros()
    """)
    op.execute("""
        CREATE TRIGGER continuacion_sobre_actividad_marcada BEFORE INSERT ON planificacion
        FOR EACH ROW WHEN (NEW.tipo = 'continuacion') EXECUTE FUNCTION actividad_marcada_no_admite_registros()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER continuacion_sobre_actividad_marcada ON planificacion")
    op.execute("DROP TRIGGER avance_sobre_actividad_marcada ON avance")
    op.execute("DROP FUNCTION actividad_marcada_no_admite_registros()")
    op.execute("DROP TRIGGER actividad_marca_inmutable ON actividad")
    op.execute("DROP FUNCTION actividad_marca_valida()")
    op.execute("ALTER TABLE actividad DROP CONSTRAINT actividad_marca_coherente")
    op.execute(f"REVOKE UPDATE ({COLUMNAS_DE_LA_MARCA}) ON actividad FROM {_rol_app()}")
