"""Control de intentos fallidos y eventos técnicos de autenticación (M1-T7; ADR-002, A9 y A11; decisiones del 2026-11-17).

Qué crea, con TABLAS SEPARADAS (no se reutilizan columnas de ``identidad``: no tiene contadores, no podría contar los
identificadores inexistentes y obligaría a conceder a la aplicación un UPDATE sobre la tabla de contraseñas):

- ``control_de_intentos``: contador por (cuenta, origen) de las personas que inician sesión por HTTP. La clave es un HMAC
  (64 hex): nunca el identificador ni el origen en claro. Estado: intentos, espera (``permitido_desde``) y último intento.
- ``intento_de_origen``: reservas por origen (también por HMAC) para los límites de 30 intentos en 5 minutos y 200 en 1 hora.
  Cada fila sale sola de la ventana; no hay nada permanente.
- ``control_de_intentos_operador``: el mismo contador para las personas operadoras de la CLI, SEPARADO del de las personas.
- ``evento_autenticacion``: registro técnico de eventos de autenticación (A11), separado de la auditoría funcional. Solo
  anexado: no se actualiza nunca y solo se borra pasados 30 días (retención técnica inicial aprobada). No guarda contraseñas,
  cookies, tokens ni identificadores en claro; solo HMAC, identificadores internos y datos que fija el código.

Privilegios mínimos (tabla a tabla, y columna a columna donde importa):

- Aplicación: ``control_de_intentos`` (SELECT, INSERT, DELETE y UPDATE solo de intentos, espera y último intento),
  ``intento_de_origen`` (SELECT, INSERT, DELETE) y INSERT en ``evento_autenticacion`` sin poder fijar ``id`` ni ``ocurrido_en``
  (no se puede fechar un evento). No lee eventos y no toca los contadores de las personas operadoras.
- Provisión: ``control_de_intentos_operador`` (igual que la aplicación en el suyo), INSERT en ``evento_autenticacion`` (solo
  eventos de la persona operadora y la revocación por desactivación), y SELECT (id, ocurrido_en) y DELETE para el
  procedimiento de purga. No toca los contadores de las personas.
- Sin cambios sobre ``identidad``, ``persona`` ni ``sesion``.

Tres disparadores: ``evento_autenticacion_inmutable`` (ningún UPDATE; DELETE solo de eventos de más de 30 días, para cualquier
rol, también el propietario) y ``evento_autenticacion_segun_rol`` (cada rol solo escribe los eventos que le corresponden).
"""

import re

from alembic import op
from sqlalchemy import text

from app.config import get_settings

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

TIPOS = ("inicio_correcto", "inicio_fallido", "espera_aplicada", "cierre_sesion",
         "acceso_desactivado_en_inicio", "revocacion_por_desactivacion")
HEX64 = "'^[0-9a-f]{64}$'"


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
    s = get_settings()
    app, prov = _rol(s.app_db_role), _rol(s.provision_db_role)
    _exigir_rol_de_provision(prov)
    tipos = ", ".join(f"'{t}'" for t in TIPOS)

    for tabla in ("control_de_intentos", "control_de_intentos_operador"):
        op.execute(f"""
            CREATE TABLE {tabla} (
                clave text PRIMARY KEY CHECK (clave ~ {HEX64}),
                intentos integer NOT NULL CHECK (intentos > 0),
                permitido_desde timestamptz,
                ultimo_intento_en timestamptz NOT NULL
            )
        """)
        op.execute(f"CREATE INDEX {tabla}_ultimo_intento_idx ON {tabla} (ultimo_intento_en)")

    op.execute(f"""
        CREATE TABLE intento_de_origen (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            clave_origen text NOT NULL CHECK (clave_origen ~ {HEX64}),
            en timestamptz NOT NULL
        )
    """)
    op.execute("CREATE INDEX intento_de_origen_ventana_idx ON intento_de_origen (clave_origen, en DESC)")
    op.execute("CREATE INDEX intento_de_origen_en_idx ON intento_de_origen (en)")

    op.execute(f"""
        CREATE TABLE evento_autenticacion (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            ocurrido_en timestamptz NOT NULL DEFAULT now(),
            tipo text NOT NULL CHECK (tipo IN ({tipos})),
            ambito text NOT NULL CHECK (ambito IN ('persona', 'operador')),
            -- Solo en eventos de una persona ya autenticada (o de su revocación): nunca en un intento fallido.
            persona_id uuid REFERENCES persona (id),
            sesion_id uuid,
            -- HMAC del identificador (y del origen): permiten correlacionar intentos sin guardar ninguno en claro.
            clave_cuenta text CHECK (clave_cuenta ~ {HEX64}),
            clave_origen text CHECK (clave_origen ~ {HEX64}),
            detalle jsonb CHECK (jsonb_typeof(detalle) = 'object'),
            CONSTRAINT evento_operador_sin_persona CHECK (ambito <> 'operador' OR persona_id IS NULL),
            CONSTRAINT evento_revocacion_con_persona CHECK (tipo <> 'revocacion_por_desactivacion' OR persona_id IS NOT NULL)
        )
    """)
    op.execute("CREATE INDEX evento_autenticacion_ocurrido_idx ON evento_autenticacion (ocurrido_en)")

    op.execute("""
        CREATE FUNCTION evento_autenticacion_solo_anexado() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                RAISE EXCEPTION 'Los eventos de autenticación son de solo anexado: no se actualizan'
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            IF OLD.ocurrido_en > now() - interval '30 days' THEN
                RAISE EXCEPTION 'Un evento de autenticación solo se borra pasados 30 días (retención técnica)'
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            RETURN OLD;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER evento_autenticacion_inmutable BEFORE UPDATE OR DELETE ON evento_autenticacion
        FOR EACH ROW EXECUTE FUNCTION evento_autenticacion_solo_anexado()
    """)

    op.execute(f"""
        CREATE FUNCTION evento_autenticacion_segun_rol() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF current_user = '{prov}' THEN
                IF NOT (NEW.ambito = 'operador' AND NEW.tipo IN ('inicio_correcto', 'inicio_fallido', 'espera_aplicada'))
                   AND NOT (NEW.ambito = 'persona' AND NEW.tipo = 'revocacion_por_desactivacion') THEN
                    RAISE EXCEPTION 'La provisión solo registra eventos de la persona operadora y la revocación por desactivación'
                        USING ERRCODE = '23514', CONSTRAINT = 'evento_autenticacion_segun_rol';
                END IF;
            ELSIF current_user = '{app}' THEN
                IF NEW.ambito <> 'persona' OR NEW.tipo = 'revocacion_por_desactivacion' THEN
                    RAISE EXCEPTION 'La aplicación no registra eventos de la persona operadora ni la revocación por desactivación'
                        USING ERRCODE = '23514', CONSTRAINT = 'evento_autenticacion_segun_rol';
                END IF;
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER evento_autenticacion_segun_rol BEFORE INSERT ON evento_autenticacion
        FOR EACH ROW EXECUTE FUNCTION evento_autenticacion_segun_rol()
    """)

    columnas_evento = "tipo, ambito, persona_id, sesion_id, clave_cuenta, clave_origen, detalle"
    columnas_contador = "intentos, permitido_desde, ultimo_intento_en"
    op.execute(f'GRANT SELECT, INSERT, DELETE, UPDATE ({columnas_contador}) ON control_de_intentos TO "{app}"')
    op.execute(f'GRANT SELECT, INSERT, DELETE ON intento_de_origen TO "{app}"')
    op.execute(f'GRANT INSERT ({columnas_evento}) ON evento_autenticacion TO "{app}"')
    op.execute(f'GRANT SELECT, INSERT, DELETE, UPDATE ({columnas_contador}) ON control_de_intentos_operador TO "{prov}"')
    op.execute(f'GRANT INSERT ({columnas_evento}) ON evento_autenticacion TO "{prov}"')
    op.execute(f'GRANT SELECT (id, ocurrido_en), DELETE ON evento_autenticacion TO "{prov}"')


def downgrade() -> None:
    # Revertir elimina los contadores y los eventos técnicos de esta migración (no son auditoría funcional).
    op.execute("DROP TABLE evento_autenticacion")
    op.execute("DROP FUNCTION evento_autenticacion_solo_anexado()")
    op.execute("DROP FUNCTION evento_autenticacion_segun_rol()")
    op.execute("DROP TABLE control_de_intentos_operador")
    op.execute("DROP TABLE intento_de_origen")
    op.execute("DROP TABLE control_de_intentos")
