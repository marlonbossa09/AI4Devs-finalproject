"""Corrección auditada de avances (M3-03): ``avance.modificado_en``, permisos mínimos e inmutabilidad.

Hasta la 0007 los avances no se podían modificar: la aplicación solo tenía INSERT y SELECT sobre ``avance``.
Esta migración concede el permiso mínimo para corregir y garantiza en la base que nada más cambia.

- ``avance.modificado_en`` (CA-62): momento real de la última corrección. Para los avances existentes y para
  los nuevos coincide con ``registrado_en`` mientras no se corrijan (un disparador lo rellena al insertar, así
  que ningún INSERT existente cambia). Nunca es anterior al registro.
- Permiso de actualización solo por COLUMNAS: ``estado``, ``descripcion``, ``motivo_bloqueo`` y
  ``modificado_en``. No hay permiso de borrado (RN-52: los avances no se eliminan).
- ``avance_motivo_solo_si_bloqueada``: el motivo de bloqueo solo existe con el estado Bloqueada. Al corregir
  hacia otro estado el motivo se limpia (el valor anterior consta en la auditoría).
- ``avance_correccion_valida`` (disparador de UPDATE): el identificador, la actividad, la bitácora (la fecha
  laboral), el momento de registro y la condición de reactivación son inmutables aunque algo eluda el
  servicio; ``modificado_en`` solo avanza cuando cambia el contenido y nunca retrocede; y no se corrige un
  avance de una actividad con marca de error vigente (RN-113, IR-18). El disparador toma ``FOR SHARE`` sobre la
  actividad, así que se serializa con una marca simultánea.

La validación de la secuencia (IR-11, PA-29) la hace el servicio con la secuencia completa de la actividad,
bloqueada mientras dura la transacción.
"""

import re

from alembic import op

from app.config import get_settings

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

COLUMNAS_CORREGIBLES = "estado, descripcion, motivo_bloqueo, modificado_en"


def _rol_app() -> str:
    rol = get_settings().app_db_role
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", rol):
        raise ValueError("APP_DB_ROLE no es un identificador válido")
    return f'"{rol}"'


def upgrade() -> None:
    op.execute("ALTER TABLE avance ADD COLUMN modificado_en timestamptz")
    op.execute("UPDATE avance SET modificado_en = registrado_en")
    op.execute("ALTER TABLE avance ALTER COLUMN modificado_en SET NOT NULL")
    op.execute("ALTER TABLE avance ADD CONSTRAINT avance_modificado_no_anterior_al_registro "
               "CHECK (modificado_en >= registrado_en)")
    op.execute("ALTER TABLE avance ADD CONSTRAINT avance_motivo_solo_si_bloqueada "
               "CHECK (estado = 'Bloqueada' OR motivo_bloqueo IS NULL)")

    op.execute("""
        CREATE FUNCTION avance_modificado_inicial() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.modificado_en IS NULL THEN
                NEW.modificado_en := NEW.registrado_en;
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER avance_modificado_inicial BEFORE INSERT ON avance
        FOR EACH ROW EXECUTE FUNCTION avance_modificado_inicial()
    """)

    op.execute("""
        CREATE FUNCTION avance_correccion_valida() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            marcada boolean;
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.actividad_id IS DISTINCT FROM OLD.actividad_id
               OR NEW.bitacora_id IS DISTINCT FROM OLD.bitacora_id
               OR NEW.registrado_en IS DISTINCT FROM OLD.registrado_en
               OR NEW.es_reactivacion IS DISTINCT FROM OLD.es_reactivacion THEN
                RAISE EXCEPTION 'De un avance solo se corrigen su estado, su descripción y su motivo de bloqueo'
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            IF NEW.estado IS NOT DISTINCT FROM OLD.estado
               AND NEW.descripcion IS NOT DISTINCT FROM OLD.descripcion
               AND NEW.motivo_bloqueo IS NOT DISTINCT FROM OLD.motivo_bloqueo THEN
                IF NEW.modificado_en IS DISTINCT FROM OLD.modificado_en THEN
                    RAISE EXCEPTION 'Sin cambio de contenido no se renueva la fecha de modificación del avance'
                        USING ERRCODE = 'integrity_constraint_violation';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.modificado_en < OLD.modificado_en THEN
                RAISE EXCEPTION 'La fecha de modificación de un avance no retrocede'
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            SELECT registrada_por_error INTO marcada FROM actividad WHERE id = NEW.actividad_id FOR SHARE;
            IF marcada THEN
                RAISE EXCEPTION 'No se corrigen los avances de una actividad marcada como registrada por error'
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER avance_correccion_valida BEFORE UPDATE ON avance
        FOR EACH ROW EXECUTE FUNCTION avance_correccion_valida()
    """)

    op.execute(f"GRANT UPDATE ({COLUMNAS_CORREGIBLES}) ON avance TO {_rol_app()}")


def downgrade() -> None:
    op.execute(f"REVOKE UPDATE ({COLUMNAS_CORREGIBLES}) ON avance FROM {_rol_app()}")
    op.execute("DROP TRIGGER avance_correccion_valida ON avance")
    op.execute("DROP FUNCTION avance_correccion_valida()")
    op.execute("DROP TRIGGER avance_modificado_inicial ON avance")
    op.execute("DROP FUNCTION avance_modificado_inicial()")
    op.execute("ALTER TABLE avance DROP CONSTRAINT avance_motivo_solo_si_bloqueada")
    op.execute("ALTER TABLE avance DROP CONSTRAINT avance_modificado_no_anterior_al_registro")
    op.execute("ALTER TABLE avance DROP COLUMN modificado_en")
