"""Códigos de un solo uso y contraseña establecida (M1-T8.1; ADR-002, secciones 4, 6 y 8; decisiones A3, A4, D1, D6 y D8 del 2026-11-17).

Qué crea:

- ``identidad.contrasena_establecida_en`` (D8). Un disparador la mantiene: nadie la fija a mano. Se rellena sola cuando se fija el hash de la
  contraseña y se vacía cuando el hash se vacía; una restricción obliga a que haya hash exactamente cuando hay fecha. Las identidades que ya tienen
  contraseña reciben la fecha de esta migración. Distingue «primer acceso pendiente» de «recuperación» sin leer el hash.
- ``codigo_unico``: solo el HMAC del código (nunca el código), la finalidad (primer acceso o recuperación), la vigencia, el uso, la invalidación,
  los intentos de canje fallidos y la referencia no secreta de quien lo emite.

Invariantes que impone la base de datos (sin depender de quien la llame ni del reloj de Python; todo con ``clock_timestamp()`` de PostgreSQL):

1. Como mucho UN código pendiente por identidad y finalidad (índice único parcial). Dos emisiones simultáneas no pueden dejar dos vigentes.
2. La finalidad corresponde al estado: primer acceso solo si la contraseña NO está establecida; recuperación solo si lo está. Y NUNCA para un
   acceso desactivado (DD-05): no hay forma indirecta de dar un código a una persona desactivada, ni de reactivarla con uno.
3. ``emitido_en`` lo fija la base; un código nuevo nace sin usar, sin invalidar y sin intentos. La vigencia es posterior a la emisión y de 24 horas
   como máximo (la referencia de ADR-002 para un canal asíncrono; la decisión de 10 minutos la aplica el servicio).
4. Un código se usa UNA vez: ``usado_en`` solo pasa de vacío a la hora de la base, solo antes de caducar y solo si no está invalidado; un código usado o
   invalidado no vuelve a cambiar. Un código nunca está usado e invalidado a la vez.
5. Los intentos de canje fallidos solo crecen, de uno en uno, y al llegar a 10 el código se invalida solo (A4).
6. El hash, la identidad, la finalidad, la emisión y la vigencia no se modifican jamás.
7. Un código solo se borra pasados 30 días desde que terminó (usado, invalidado o caducado), para cualquier rol, también el propietario (D6). La
   purga programada es de T8.6; no se concede todavía permiso de borrado a ningún rol.

Privilegios mínimos:

- **Aplicación:** NINGUNO sobre ``codigo_unico`` (no puede emitir códigos ni leer sus hashes). El canje (T8.3) se hará con una función de la base
  con ``SECURITY DEFINER``, que NO se crea todavía (D2: aprobada condicionalmente; hay que demostrar que no permite escalada de privilegios).
- **Provisión:** ``INSERT`` de las columnas de emisión (no de ``emitido_en``, el uso ni los intentos), ``SELECT`` de todo menos ``hash_codigo``
  y ``UPDATE (invalidado_en)`` (invalidar el pendiente al emitir otro). Nunca lee ni cambia un hash.
- ``identidad``: el rol de provisión pasa a poder insertar solo ``persona_id``, ``identificador_acceso`` y ``hash_contrasena`` (este último solo
  vacío, por un disparador: la provisión no da contraseñas) y a leer ``contrasena_establecida_en``. Sin cambios para la aplicación.

No crea ninguna ruta, orden ni función de canje: el primer acceso y la recuperación NO son funcionales con esta migración.
"""

import re

from alembic import op
from sqlalchemy import text

from app.config import get_settings

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

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
    prov = _rol(get_settings().provision_db_role)
    _exigir_rol_de_provision(prov)

    # ---- identidad.contrasena_establecida_en (D8)
    op.execute("ALTER TABLE identidad ADD COLUMN contrasena_establecida_en timestamptz")
    op.execute("UPDATE identidad SET contrasena_establecida_en = now() WHERE hash_contrasena IS NOT NULL")
    op.execute("""
        CREATE FUNCTION identidad_contrasena_establecida() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.hash_contrasena IS NULL THEN
                NEW.contrasena_establecida_en := NULL;
            ELSIF TG_OP = 'INSERT' OR OLD.hash_contrasena IS DISTINCT FROM NEW.hash_contrasena THEN
                NEW.contrasena_establecida_en := clock_timestamp();
            ELSE
                NEW.contrasena_establecida_en := OLD.contrasena_establecida_en;
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER identidad_contrasena_establecida BEFORE INSERT OR UPDATE ON identidad
        FOR EACH ROW EXECUTE FUNCTION identidad_contrasena_establecida()
    """)
    op.execute("""
        ALTER TABLE identidad ADD CONSTRAINT identidad_contrasena_coherente
        CHECK ((hash_contrasena IS NULL) = (contrasena_establecida_en IS NULL))
    """)

    # La provisión crea identidades SIN contraseña: nunca puede insertar un hash.
    op.execute(f'REVOKE INSERT ON identidad FROM "{prov}"')
    op.execute(f'GRANT INSERT (persona_id, identificador_acceso, hash_contrasena) ON identidad TO "{prov}"')
    op.execute(f'GRANT SELECT (contrasena_establecida_en) ON identidad TO "{prov}"')
    op.execute(f"""
        CREATE FUNCTION identidad_provision_sin_contrasena() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF current_user = '{prov}' AND NEW.hash_contrasena IS NOT NULL THEN
                RAISE EXCEPTION 'La provisión crea identidades sin contraseña'
                    USING ERRCODE = '23514', CONSTRAINT = 'identidad_provision_sin_contrasena';
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER identidad_provision_sin_contrasena BEFORE INSERT ON identidad
        FOR EACH ROW EXECUTE FUNCTION identidad_provision_sin_contrasena()
    """)

    # ---- codigo_unico
    op.execute(f"""
        CREATE TABLE codigo_unico (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            identidad_id uuid NOT NULL REFERENCES identidad (id),
            finalidad text NOT NULL CHECK (finalidad IN ('primer_acceso', 'recuperacion')),
            -- HMAC-SHA256 del código (hexadecimal). Nunca el código.
            hash_codigo text NOT NULL UNIQUE CHECK (hash_codigo ~ {HEX64}),
            emitido_en timestamptz NOT NULL,
            caduca_en timestamptz NOT NULL,
            usado_en timestamptz,
            invalidado_en timestamptz,
            intentos_fallidos integer NOT NULL DEFAULT 0 CHECK (intentos_fallidos BETWEEN 0 AND 10),
            -- Referencia NO secreta de quien emite: la misma que ``auditoria.referencia_provision``.
            emitido_por text NOT NULL CHECK (btrim(emitido_por) <> ''),
            CONSTRAINT codigo_vigencia CHECK (caduca_en > emitido_en AND caduca_en <= emitido_en + interval '24 hours'),
            CONSTRAINT codigo_un_solo_final CHECK (usado_en IS NULL OR invalidado_en IS NULL),
            CONSTRAINT codigo_final_posterior CHECK (
                (usado_en IS NULL OR usado_en >= emitido_en) AND (invalidado_en IS NULL OR invalidado_en >= emitido_en)
            )
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX codigo_un_pendiente ON codigo_unico (identidad_id, finalidad)
        WHERE usado_en IS NULL AND invalidado_en IS NULL
    """)

    op.execute("""
        CREATE FUNCTION codigo_unico_al_emitir() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            v_establecida timestamptz;
            v_desactivado timestamptz;
        BEGIN
            SELECT i.contrasena_establecida_en, p.acceso_desactivado_en INTO v_establecida, v_desactivado
            FROM identidad i JOIN persona p ON p.id = i.persona_id WHERE i.id = NEW.identidad_id;
            IF FOUND THEN
                IF v_desactivado IS NOT NULL THEN
                    RAISE EXCEPTION 'No se emite un código para un acceso desactivado'
                        USING ERRCODE = '23514', CONSTRAINT = 'codigo_acceso_desactivado';
                END IF;
                IF NEW.finalidad = 'primer_acceso' AND v_establecida IS NOT NULL THEN
                    RAISE EXCEPTION 'El primer acceso solo se emite si la contraseña no está establecida'
                        USING ERRCODE = '23514', CONSTRAINT = 'codigo_finalidad_primer_acceso';
                END IF;
                IF NEW.finalidad = 'recuperacion' AND v_establecida IS NULL THEN
                    RAISE EXCEPTION 'La recuperación solo se emite si la contraseña está establecida'
                        USING ERRCODE = '23514', CONSTRAINT = 'codigo_finalidad_recuperacion';
                END IF;
            END IF;
            NEW.emitido_en := clock_timestamp();
            NEW.usado_en := NULL;
            NEW.invalidado_en := NULL;
            NEW.intentos_fallidos := 0;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER codigo_unico_al_emitir BEFORE INSERT ON codigo_unico
        FOR EACH ROW EXECUTE FUNCTION codigo_unico_al_emitir()
    """)

    op.execute("""
        CREATE FUNCTION codigo_unico_transiciones() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.id <> OLD.id OR NEW.identidad_id <> OLD.identidad_id OR NEW.finalidad <> OLD.finalidad
               OR NEW.hash_codigo <> OLD.hash_codigo OR NEW.emitido_en <> OLD.emitido_en OR NEW.caduca_en <> OLD.caduca_en
               OR NEW.emitido_por <> OLD.emitido_por THEN
                RAISE EXCEPTION 'Un código no cambia su hash, su identidad, su finalidad, su emisión ni su vigencia'
                    USING ERRCODE = '23514', CONSTRAINT = 'codigo_inmutable';
            END IF;
            IF (OLD.usado_en IS NOT NULL OR OLD.invalidado_en IS NOT NULL) AND NEW IS DISTINCT FROM OLD THEN
                RAISE EXCEPTION 'Un código usado o invalidado no vuelve a cambiar'
                    USING ERRCODE = '23514', CONSTRAINT = 'codigo_finalizado';
            END IF;
            IF NEW.intentos_fallidos < OLD.intentos_fallidos OR NEW.intentos_fallidos > OLD.intentos_fallidos + 1 THEN
                RAISE EXCEPTION 'Los intentos fallidos solo crecen de uno en uno'
                    USING ERRCODE = '23514', CONSTRAINT = 'codigo_intentos';
            END IF;
            IF NEW.usado_en IS NOT NULL THEN
                IF NEW.invalidado_en IS NOT NULL OR NEW.intentos_fallidos <> OLD.intentos_fallidos THEN
                    RAISE EXCEPTION 'Un código se usa sin invalidarse ni sumar intentos'
                        USING ERRCODE = '23514', CONSTRAINT = 'codigo_uso';
                END IF;
                IF clock_timestamp() >= OLD.caduca_en THEN
                    RAISE EXCEPTION 'Un código caducado no se usa'
                        USING ERRCODE = '23514', CONSTRAINT = 'codigo_caducado';
                END IF;
                NEW.usado_en := clock_timestamp();
            ELSIF NEW.invalidado_en IS NOT NULL THEN
                NEW.invalidado_en := clock_timestamp();
            ELSIF NEW.intentos_fallidos >= 10 THEN
                NEW.invalidado_en := clock_timestamp();
            END IF;
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER codigo_unico_transiciones BEFORE UPDATE ON codigo_unico
        FOR EACH ROW EXECUTE FUNCTION codigo_unico_transiciones()
    """)

    op.execute("""
        CREATE FUNCTION codigo_unico_retencion() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF coalesce(OLD.usado_en, OLD.invalidado_en, OLD.caduca_en) > clock_timestamp() - interval '30 days' THEN
                RAISE EXCEPTION 'Un código solo se borra pasados 30 días desde que terminó'
                    USING ERRCODE = '23514', CONSTRAINT = 'codigo_retencion';
            END IF;
            RETURN OLD;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER codigo_unico_retencion BEFORE DELETE ON codigo_unico
        FOR EACH ROW EXECUTE FUNCTION codigo_unico_retencion()
    """)

    op.execute(f'GRANT INSERT (identidad_id, finalidad, hash_codigo, caduca_en, emitido_por) ON codigo_unico TO "{prov}"')
    op.execute(f'GRANT SELECT (id, identidad_id, finalidad, emitido_en, caduca_en, usado_en, invalidado_en, intentos_fallidos, emitido_por) '
               f'ON codigo_unico TO "{prov}"')
    op.execute(f'GRANT UPDATE (invalidado_en) ON codigo_unico TO "{prov}"')


def downgrade() -> None:
    prov = _rol(get_settings().provision_db_role)
    # Revertir elimina los códigos (son temporales y sin valor sin su secreto) y la fecha de contraseña, que se recalcula con el hash.
    op.execute("DROP TABLE codigo_unico")
    for funcion in ("codigo_unico_al_emitir", "codigo_unico_transiciones", "codigo_unico_retencion"):
        op.execute(f"DROP FUNCTION {funcion}()")
    op.execute("DROP TRIGGER identidad_provision_sin_contrasena ON identidad")
    op.execute("DROP FUNCTION identidad_provision_sin_contrasena()")
    op.execute("ALTER TABLE identidad DROP CONSTRAINT identidad_contrasena_coherente")
    op.execute("DROP TRIGGER identidad_contrasena_establecida ON identidad")
    op.execute("DROP FUNCTION identidad_contrasena_establecida()")
    existe = op.get_bind().execute(text("select 1 from pg_roles where rolname = :r"), {"r": prov}).first()
    op.execute("ALTER TABLE identidad DROP COLUMN contrasena_establecida_en")
    if existe is not None:
        op.execute(f'REVOKE INSERT (persona_id, identificador_acceso, hash_contrasena) ON identidad FROM "{prov}"')
        op.execute(f'GRANT INSERT ON identidad TO "{prov}"')
