"""Finalizar pertenencias y cancelar o sustituir operaciones programadas (M1-T4, contratos M1-06 y M1-07).

Qué cambia respecto de 0010 (decisiones aprobadas el 2026-11-11; modelo de datos: IR-26, IR-30, IR-31, IR-32 e IR-39):

- Un permiso nuevo para el rol de provisión: ``DELETE`` sobre ``pertenencia``. IR-26 admite UNA excepción al «no se borra»:
  retirar una pertenencia programada que no ha surtido efecto, con sus valores completos en la auditoría. El permiso es de
  tabla (PostgreSQL no concede borrado por filas) y por eso lo acota el disparador de abajo: el rol de provisión solo puede
  borrar un intervalo que todavía no ha empezado.
- ``pertenencia_solo_se_cierra_el_ultimo`` (0010) se SUSTITUYE por ``pertenencia_solo_cambia_lo_programado``. La regla de 0010
  («solo se cierra un intervalo sin fin») no admite restituir el fin de un intervalo al cancelar un traslado o una finalización.
  La regla nueva, sobre la fecha actual de la organización del equipo (zona horaria de la organización), para el rol de provisión:
  * Se puede cambiar el fin de un intervalo solo si su fin actual es nulo o posterior a hoy, y el nuevo fin es nulo o
    posterior a hoy: cerrar el último intervalo (traslado, finalización) y restituir o mover un fin programado (cancelar,
    sustituir). Un intervalo cuyo fin ya llegó (historial) no se modifica nunca.
  * Se puede borrar un intervalo solo si su inicio es posterior a hoy (una operación programada).
  El inicio, el equipo, el rol y la persona de un intervalo siguen sin poder cambiarse (permiso por columna de 0010).
  Usa el reloj de la base de datos: la fecha actual de las pruebas con reloj inyectable es de la orden, no de este control.
- ``pertenencia_supervision_del_equipo`` (diferido, IR-03 e IR-32) pasa a vigilar también los BORRADOS: retirar un intervalo
  programado puede dejar a un equipo con colaboradores sin supervisor (cancelar una alta o un relevo a medias).

No cambia datos ni la auditoría: los tipos de operación ``finalizacion_pertenencia``, ``cancelacion_operacion`` y
``sustitucion_operacion`` ya existían (0004).
"""

import re

from alembic import op
from sqlalchemy import text

from app.config import get_settings

revision = "0011"
down_revision = "0010"
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


def _funcion_de_supervision(rol: str, con_borrados: bool) -> str:
    """IR-03 e IR-32 sobre el resultado de la transacción, desde la fecha afectada hasta el fin de los tiempos."""
    if con_borrados:
        equipo, desde = "equipo_afectado", """
            IF TG_OP = 'DELETE' THEN
                equipo_afectado := OLD.equipo_id;
                desde_control := OLD.desde;
            ELSIF TG_OP = 'INSERT' THEN
                equipo_afectado := NEW.equipo_id;
                desde_control := NEW.desde;
            ELSE
                equipo_afectado := NEW.equipo_id;
                -- Solo cambia ``hasta_exclusivo``: la línea temporal cambia desde el menor de los dos fines (vacío = sin fin).
                desde_control := LEAST(OLD.hasta_exclusivo, NEW.hasta_exclusivo);
                IF desde_control IS NULL THEN
                    RETURN NULL;
                END IF;
            END IF;"""
        declaracion = "desde_control date;\n            equipo_afectado uuid;"
    else:
        equipo, declaracion = "NEW.equipo_id", "desde_control date;"
        desde = """
            IF TG_OP = 'INSERT' THEN
                desde_control := NEW.desde;
            ELSE
                desde_control := LEAST(OLD.hasta_exclusivo, NEW.hasta_exclusivo);
                IF desde_control IS NULL THEN
                    RETURN NULL;
                END IF;
            END IF;"""
    return f"""
        CREATE OR REPLACE FUNCTION pertenencia_exigir_supervision() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            {declaracion}
        BEGIN
            IF current_user <> '{rol}' THEN
                RETURN NULL;
            END IF;{desde}
            PERFORM 1
            FROM (
                SELECT desde_control AS d
                UNION SELECT t.desde FROM pertenencia t WHERE t.equipo_id = {equipo} AND t.desde > desde_control
                UNION SELECT t.hasta_exclusivo FROM pertenencia t WHERE t.equipo_id = {equipo} AND t.hasta_exclusivo > desde_control
            ) p
            CROSS JOIN LATERAL (
                SELECT count(*) FILTER (WHERE t.rol = 'supervisor') AS supervisores,
                       count(*) FILTER (WHERE t.rol = 'colaborador') AS colaboradores
                FROM pertenencia t
                WHERE t.equipo_id = {equipo} AND t.desde <= p.d AND (t.hasta_exclusivo IS NULL OR p.d < t.hasta_exclusivo)
            ) k
            WHERE k.supervisores > 1 OR (k.colaboradores > 0 AND k.supervisores = 0);
            IF FOUND THEN
                RAISE EXCEPTION 'La supervisión del equipo incumple IR-03 o IR-32'
                    USING ERRCODE = '23514', CONSTRAINT = 'pertenencia_supervision_del_equipo';
            END IF;
            RETURN NULL;
        END $$
    """


def upgrade() -> None:
    rol = _rol(get_settings().provision_db_role)
    _exigir_rol_de_provision(rol)

    op.execute(f'GRANT DELETE ON pertenencia TO "{rol}"')

    op.execute("DROP TRIGGER pertenencia_solo_se_cierra_el_ultimo ON pertenencia")
    op.execute("DROP FUNCTION pertenencia_solo_se_cierra_el_ultimo()")
    op.execute(f"""
        CREATE FUNCTION pertenencia_solo_cambia_lo_programado() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            hoy date;
            equipo_del_intervalo uuid;
        BEGIN
            IF current_user <> '{rol}' THEN
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                END IF;
                RETURN NEW;
            END IF;
            equipo_del_intervalo := OLD.equipo_id;
            SELECT (now() AT TIME ZONE o.zona_horaria)::date INTO hoy
            FROM equipo e JOIN organizacion o ON o.id = e.organizacion_id WHERE e.id = equipo_del_intervalo;
            IF TG_OP = 'DELETE' THEN
                IF OLD.desde <= hoy THEN
                    RAISE EXCEPTION 'La provisión solo borra pertenencias programadas (que todavía no han empezado)'
                        USING ERRCODE = '23514', CONSTRAINT = 'pertenencia_solo_cambia_lo_programado';
                END IF;
                RETURN OLD;
            END IF;
            IF (OLD.hasta_exclusivo IS NOT NULL AND OLD.hasta_exclusivo <= hoy)
               OR (NEW.hasta_exclusivo IS NOT NULL AND NEW.hasta_exclusivo <= hoy) THEN
                RAISE EXCEPTION 'La provisión solo cambia el fin de un intervalo cuando el fin actual y el nuevo son posteriores a hoy'
                    USING ERRCODE = '23514', CONSTRAINT = 'pertenencia_solo_cambia_lo_programado';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER pertenencia_solo_cambia_lo_programado BEFORE UPDATE OR DELETE ON pertenencia
        FOR EACH ROW EXECUTE FUNCTION pertenencia_solo_cambia_lo_programado()
    """)

    op.execute("DROP TRIGGER pertenencia_supervision_del_equipo ON pertenencia")
    op.execute(_funcion_de_supervision(rol, con_borrados=True))
    op.execute("""
        CREATE CONSTRAINT TRIGGER pertenencia_supervision_del_equipo AFTER INSERT OR UPDATE OR DELETE ON pertenencia
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pertenencia_exigir_supervision()
    """)


def downgrade() -> None:
    rol = _rol(get_settings().provision_db_role)
    op.execute("DROP TRIGGER pertenencia_supervision_del_equipo ON pertenencia")
    op.execute(_funcion_de_supervision(rol, con_borrados=False))
    op.execute("""
        CREATE CONSTRAINT TRIGGER pertenencia_supervision_del_equipo AFTER INSERT OR UPDATE ON pertenencia
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pertenencia_exigir_supervision()
    """)
    op.execute("DROP TRIGGER pertenencia_solo_cambia_lo_programado ON pertenencia")
    op.execute("DROP FUNCTION pertenencia_solo_cambia_lo_programado()")
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
    existe = op.get_bind().execute(text("select 1 from pg_roles where rolname = :r"), {"r": rol}).first()
    if existe is not None:
        op.execute(f'REVOKE DELETE ON pertenencia FROM "{rol}"')
