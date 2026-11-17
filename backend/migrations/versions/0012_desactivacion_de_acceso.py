"""Desactivación del acceso de una persona (M1-T6, contrato M1-08).

Qué concede al rol de provisión (decisiones aprobadas el 2026-11-11; modelo de datos: IR-37, DD-04, DD-05):

- ``UPDATE (acceso_desactivado_en)`` sobre ``persona``: ÚNICA columna. No hay permiso general de actualización sobre personas ni sobre
  identidades; el rol sigue sin poder cambiar el nombre, borrar personas ni tocar contraseñas.
- ``SELECT (identidad_id, revocada_en)`` y ``UPDATE (revocada_en)`` sobre ``sesion``: ÚNICAS columnas, las necesarias para revocar todas
  las sesiones de una persona (``update sesion set revocada_en = now() where revocada_en is null and identidad_id in (...)``). No lee el
  hash del secreto de ninguna sesión, no inserta y no borra.

Endurecimiento de un privilegio heredado de 0009: el rol de provisión leía TODA la tabla ``identidad`` (incluido el hash de contraseña) solo
para comprobar la unicidad del identificador de acceso y localizar las sesiones de una persona. Pasa a leer únicamente ``id``,
``persona_id`` e ``identificador_acceso`` (conserva INSERT para crear la identidad sin contraseña de ``crear-persona``).

Dos protecciones en la base de datos, SOLO para el rol de provisión (defensa en profundidad de lo que valida el servicio):

- ``persona_solo_se_desactiva``: el rol de provisión solo puede pasar ``acceso_desactivado_en`` de nulo a la hora actual de la
  transacción: no reactiva un acceso (M1-10 no existe, DD-05), no lo reescribe y no lo fecha en el pasado ni en el futuro.
- ``sesion_solo_se_revoca``: solo puede pasar ``revocada_en`` de nulo a la hora actual: no «resucita» una sesión revocada.

No cambia datos, no añade tablas ni columnas (la condición «equipo pendiente de supervisión efectiva», DM-09, es derivada y no se
almacena) y no cambia la auditoría: el tipo de operación ``desactivacion_acceso`` ya existía (0004). La aplicación no recibe ningún
permiso nuevo.
"""

import re

from alembic import op
from sqlalchemy import text

from app.config import get_settings

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def _rol(nombre: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", nombre):
        raise ValueError("El nombre del rol no es un identificador válido")
    return nombre


def _exigir_rol_de_provision(rol: str) -> None:
    existe = op.get_bind().execute(text("select 1 from pg_roles where rolname = :r"), {"r": rol}).first()
    if existe is None:
        raise RuntimeError(
            f"No existe el rol de PostgreSQL de provisión {rol!r}: ver backend/scripts/provision_rol_de_provision.sql "
            "(debe existir antes de migrar; la migración no puede crear roles)."
        )


def upgrade() -> None:
    rol = _rol(get_settings().provision_db_role)
    _exigir_rol_de_provision(rol)

    op.execute(f'GRANT UPDATE (acceso_desactivado_en) ON persona TO "{rol}"')
    op.execute(f'GRANT SELECT (identidad_id, revocada_en), UPDATE (revocada_en) ON sesion TO "{rol}"')
    op.execute(f'REVOKE SELECT ON identidad FROM "{rol}"')
    op.execute(f'GRANT SELECT (id, persona_id, identificador_acceso) ON identidad TO "{rol}"')

    op.execute(f"""
        CREATE FUNCTION persona_solo_se_desactiva() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF current_user <> '{rol}' THEN
                RETURN NEW;
            END IF;
            IF OLD.acceso_desactivado_en IS NOT NULL OR NEW.acceso_desactivado_en IS DISTINCT FROM now() THEN
                RAISE EXCEPTION 'La provisión solo desactiva un acceso que está activo, con la hora actual'
                    USING ERRCODE = '23514', CONSTRAINT = 'persona_solo_se_desactiva';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER persona_solo_se_desactiva BEFORE UPDATE ON persona
        FOR EACH ROW EXECUTE FUNCTION persona_solo_se_desactiva()
    """)

    op.execute(f"""
        CREATE FUNCTION sesion_solo_se_revoca() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF current_user <> '{rol}' THEN
                RETURN NEW;
            END IF;
            IF OLD.revocada_en IS NOT NULL OR NEW.revocada_en IS DISTINCT FROM now() THEN
                RAISE EXCEPTION 'La provisión solo revoca una sesión que no está revocada, con la hora actual'
                    USING ERRCODE = '23514', CONSTRAINT = 'sesion_solo_se_revoca';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER sesion_solo_se_revoca BEFORE UPDATE ON sesion
        FOR EACH ROW EXECUTE FUNCTION sesion_solo_se_revoca()
    """)


def downgrade() -> None:
    rol = _rol(get_settings().provision_db_role)
    op.execute("DROP TRIGGER sesion_solo_se_revoca ON sesion")
    op.execute("DROP FUNCTION sesion_solo_se_revoca()")
    op.execute("DROP TRIGGER persona_solo_se_desactiva ON persona")
    op.execute("DROP FUNCTION persona_solo_se_desactiva()")
    existe = op.get_bind().execute(text("select 1 from pg_roles where rolname = :r"), {"r": rol}).first()
    if existe is not None:
        op.execute(f'REVOKE UPDATE (acceso_desactivado_en) ON persona FROM "{rol}"')
        op.execute(f'REVOKE SELECT (identidad_id, revocada_en), UPDATE (revocada_en) ON sesion FROM "{rol}"')
        op.execute(f'REVOKE SELECT (id, persona_id, identificador_acceso) ON identidad FROM "{rol}"')
        op.execute(f'GRANT SELECT ON identidad TO "{rol}"')
