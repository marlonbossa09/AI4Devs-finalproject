"""Traslados y cambios de rol (M1-T3, contrato M1-05).

Qué añade (decisiones aprobadas el 2026-11-11; modelo de datos: IR-02, IR-03, IR-28, IR-30, IR-32):

- Un ÚNICO permiso nuevo para el rol de provisión: ``UPDATE (hasta_exclusivo)`` sobre ``pertenencia``. Un traslado o un
  cambio de rol cierra el último intervalo sin fin de la persona y abre otro; nunca cambia el equipo, el rol, el inicio ni la
  persona de un intervalo existente, y nunca borra. No se concede ningún permiso sobre bitácoras, actividades,
  planificaciones, avances ni sobre la auditoría (que sigue siendo solo INSERT).
- Dos protecciones en la base, SOLO para el rol de provisión (defensa en profundidad de lo que valida el servicio):
  * ``pertenencia_solo_se_cierra_el_ultimo`` (antes de actualizar): el rol de provisión solo puede cerrar un intervalo que no
    tiene fin; un intervalo ya cerrado, y por tanto el historial, no se modifica (IR-30).
  * ``pertenencia_supervision_del_equipo`` (disparador DIFERIDO tras insertar o actualizar): al final de la transacción, el
    equipo tiene como máximo un supervisor y exactamente uno en toda fecha con colaboradores (IR-03, IR-32), desde la fecha
    afectada hasta el fin de los tiempos. Es DIFERIDO a propósito: un relevo de supervisor cierra al saliente y abre al
    entrante en la misma transacción, y entre las dos sentencias el equipo queda un instante sin supervisor. Una comprobación
    inmediata rechazaría ese relevo válido; la diferida solo mira el resultado. Verificado con traslados, cambios de rol y
    relevos en una sola transacción (``tests/test_db_traslados.py``).
  Solo se aplican al rol de provisión porque es el único que escribe pertenencias en ejecución (la aplicación solo lee) y
  porque las herramientas de desarrollo y las pruebas preparan, con el rol propietario, líneas temporales de forma
  deliberadamente arbitraria (por ejemplo, un colaborador sin supervisor).
- Índice por equipo y fecha: la validación de IR-32 y el disparador leen la línea temporal de un EQUIPO, y la tabla solo
  tenía un índice por persona (M1-T1 dejó esa decisión para las consultas reales).

No cambia ningún dato existente y no cambia la auditoría: el tipo de operación ``cambio_pertenencia`` ya existía (0004) y la
propietaria nula de la provisión, desde 0009.
"""

import re

from alembic import op
from sqlalchemy import text

from app.config import get_settings

revision = "0010"
down_revision = "0009"
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

    op.execute("CREATE INDEX pertenencia_equipo_idx ON pertenencia (equipo_id, desde)")
    op.execute(f'GRANT UPDATE (hasta_exclusivo) ON pertenencia TO "{rol}"')

    # Solo se cierran los intervalos sin fin (IR-30). Un intervalo cerrado no se vuelve a tocar.
    op.execute(f"""
        CREATE FUNCTION pertenencia_solo_se_cierra_el_ultimo() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF current_user <> '{rol}' THEN
                RETURN NEW;
            END IF;
            IF OLD.hasta_exclusivo IS NOT NULL OR NEW.hasta_exclusivo IS NULL THEN
                RAISE EXCEPTION 'La provisión solo cierra intervalos de pertenencia que no tienen fin'
                    USING ERRCODE = '23514', CONSTRAINT = 'pertenencia_solo_se_cierra_el_ultimo';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER pertenencia_solo_se_cierra_el_ultimo BEFORE UPDATE ON pertenencia
        FOR EACH ROW EXECUTE FUNCTION pertenencia_solo_se_cierra_el_ultimo()
    """)

    # IR-03 e IR-32 sobre el resultado de la transacción, desde la fecha afectada hasta el fin de los tiempos.
    op.execute(f"""
        CREATE FUNCTION pertenencia_exigir_supervision() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            desde_control date;
        BEGIN
            IF current_user <> '{rol}' THEN
                RETURN NULL;
            END IF;
            IF TG_OP = 'INSERT' THEN
                desde_control := NEW.desde;
            ELSE
                -- Solo cambia ``hasta_exclusivo``: la línea temporal cambia desde el menor de los dos fines (vacío = sin fin).
                desde_control := LEAST(OLD.hasta_exclusivo, NEW.hasta_exclusivo);
                IF desde_control IS NULL THEN
                    RETURN NULL;
                END IF;
            END IF;
            PERFORM 1
            FROM (
                SELECT desde_control AS d
                UNION SELECT t.desde FROM pertenencia t WHERE t.equipo_id = NEW.equipo_id AND t.desde > desde_control
                UNION SELECT t.hasta_exclusivo FROM pertenencia t WHERE t.equipo_id = NEW.equipo_id AND t.hasta_exclusivo > desde_control
            ) p
            CROSS JOIN LATERAL (
                SELECT count(*) FILTER (WHERE t.rol = 'supervisor') AS supervisores,
                       count(*) FILTER (WHERE t.rol = 'colaborador') AS colaboradores
                FROM pertenencia t
                WHERE t.equipo_id = NEW.equipo_id AND t.desde <= p.d AND (t.hasta_exclusivo IS NULL OR p.d < t.hasta_exclusivo)
            ) k
            WHERE k.supervisores > 1 OR (k.colaboradores > 0 AND k.supervisores = 0);
            IF FOUND THEN
                RAISE EXCEPTION 'La supervisión del equipo incumple IR-03 o IR-32'
                    USING ERRCODE = '23514', CONSTRAINT = 'pertenencia_supervision_del_equipo';
            END IF;
            RETURN NULL;
        END $$
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER pertenencia_supervision_del_equipo AFTER INSERT OR UPDATE ON pertenencia
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pertenencia_exigir_supervision()
    """)


def downgrade() -> None:
    rol = _rol(get_settings().provision_db_role)
    op.execute("DROP TRIGGER pertenencia_supervision_del_equipo ON pertenencia")
    op.execute("DROP FUNCTION pertenencia_exigir_supervision()")
    op.execute("DROP TRIGGER pertenencia_solo_se_cierra_el_ultimo ON pertenencia")
    op.execute("DROP FUNCTION pertenencia_solo_se_cierra_el_ultimo()")
    existe = op.get_bind().execute(text("select 1 from pg_roles where rolname = :r"), {"r": rol}).first()
    if existe is not None:
        op.execute(f'REVOKE UPDATE (hasta_exclusivo) ON pertenencia FROM "{rol}"')
    op.execute("DROP INDEX pertenencia_equipo_idx")
