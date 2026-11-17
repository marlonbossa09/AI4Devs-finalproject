r"""Canje del código de recuperación (M1-T8.4; contrato M1-09b; ADR-002, secciones 6 y 11; decisiones de M1-T8 del 2026-11-17).

Segunda función ``SECURITY DEFINER``, ``canjear_codigo_recuperacion``, con el MISMO patrón y los mismos blindajes que ``canjear_codigo_primer_acceso`` (0015):
sin SQL dinámico, ``search_path`` fijo a ``pg_catalog, pg_temp`` con objetos calificados, ``EXECUTE`` revocado a PUBLIC y concedido solo al rol de la aplicación,
parámetros validados (HMAC hexadecimal de 64 y hash Argon2id acotado), propietario sin privilegios de superusuario y alcance limitado a la identidad y el
código vinculados. La aplicación sigue sin ningún permiso de escritura sobre ``identidad``, ``codigo_unico`` ni ``sesion``.

Es una función aparte (no un parámetro de la anterior) para que cada una haga una sola cosa y la anterior, ya aprobada, no cambie.

Qué hace, de forma ATÓMICA (si falla cualquier parte, incluida la revocación de sesiones o la auditoría, no se consume el código ni se toca nada):

1. Localiza la identidad por su identificador y toma el bloqueo por persona (el del inicio de sesión, la desactivación, la emisión y el primer acceso).
2. Con el bloqueo: rechaza si el acceso está DESACTIVADO (DD-05: recuperar una credencial NO reactiva un acceso; la función nunca toca ``acceso_desactivado_en``)
   o si la identidad NO tenía contraseña (eso es un primer acceso, no una recuperación).
3. Busca el código PENDIENTE de recuperación de esa identidad (no usado, no invalidado, no caducado, con el reloj de PostgreSQL), con bloqueo de fila.
4. Si el HMAC no coincide, suma un intento fallido (a los 10 se invalida solo) y devuelve nulo. Si coincide: lo consume, CAMBIA el hash de la contraseña
   (un disparador renueva ``contrasena_establecida_en``), REVOCA TODAS las sesiones de la persona en la misma transacción y audita (``recuperacion_acceso``,
   fase ``canje``, la persona como autora). Devuelve la persona.

Todos los rechazos devuelven NULO sin distinguir la causa. No crea ninguna sesión.
"""

import re

from alembic import op

from app.config import get_settings

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def _rol(nombre: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", nombre):
        raise ValueError("El nombre del rol no es un identificador válido")
    return nombre


def upgrade() -> None:
    app = _rol(get_settings().app_db_role)
    op.execute(r"""
        CREATE FUNCTION public.canjear_codigo_recuperacion(p_identificador text, p_hash_codigo text, p_hash_contrasena text)
        RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
        DECLARE
            v_identidad uuid;
            v_persona uuid;
            v_desactivado timestamptz;
            v_establecida timestamptz;
            v_codigo uuid;
            v_hash text;
            v_sesiones integer;
        BEGIN
            IF p_identificador IS NULL OR p_hash_codigo IS NULL OR p_hash_contrasena IS NULL
               OR p_hash_codigo !~ '^[0-9a-f]{64}$' OR p_hash_contrasena !~ '^\$argon2id\$' OR length(p_hash_contrasena) > 512 THEN
                RETURN NULL;
            END IF;

            SELECT i.id, i.persona_id INTO v_identidad, v_persona FROM public.identidad i WHERE i.identificador_acceso = p_identificador;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;

            PERFORM pg_advisory_xact_lock(hashtextextended('smartwork\:acceso\:persona\:' || v_persona::text, 0));

            SELECT p.acceso_desactivado_en, i.contrasena_establecida_en INTO v_desactivado, v_establecida
            FROM public.identidad i JOIN public.persona p ON p.id = i.persona_id WHERE i.id = v_identidad;
            IF v_desactivado IS NOT NULL OR v_establecida IS NULL THEN
                RETURN NULL;
            END IF;

            SELECT c.id, c.hash_codigo INTO v_codigo, v_hash FROM public.codigo_unico c
            WHERE c.identidad_id = v_identidad AND c.finalidad = 'recuperacion' AND c.usado_en IS NULL AND c.invalidado_en IS NULL
              AND c.caduca_en > clock_timestamp()
            FOR UPDATE;
            IF NOT FOUND THEN
                RETURN NULL;
            END IF;

            IF v_hash <> p_hash_codigo THEN
                UPDATE public.codigo_unico SET intentos_fallidos = intentos_fallidos + 1 WHERE id = v_codigo;
                RETURN NULL;
            END IF;

            UPDATE public.codigo_unico SET usado_en = clock_timestamp() WHERE id = v_codigo;
            UPDATE public.identidad SET hash_contrasena = p_hash_contrasena WHERE id = v_identidad AND hash_contrasena IS NOT NULL;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'No se pudo cambiar la contraseña' USING ERRCODE = '23514';
            END IF;
            UPDATE public.sesion SET revocada_en = clock_timestamp() WHERE identidad_id = v_identidad AND revocada_en IS NULL;
            GET DIAGNOSTICS v_sesiones = ROW_COUNT;
            INSERT INTO public.auditoria (tipo_autor, autor_persona_id, operacion, tipo_objeto, objeto_id, propietaria_registro_id,
                                          valor_anterior, valor_nuevo)
            VALUES ('persona', v_persona, 'recuperacion_acceso', 'persona', v_persona, v_persona,
                    jsonb_build_object('contrasena_establecida', true),
                    jsonb_build_object('fase', 'canje', 'finalidad', 'recuperacion', 'codigo_id', v_codigo,
                                       'contrasena_cambiada', true, 'sesiones_revocadas', v_sesiones));
            RETURN v_persona;
        END $$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.canjear_codigo_recuperacion(text, text, text) FROM PUBLIC")
    op.execute(f'GRANT EXECUTE ON FUNCTION public.canjear_codigo_recuperacion(text, text, text) TO "{app}"')


def downgrade() -> None:
    op.execute("DROP FUNCTION public.canjear_codigo_recuperacion(text, text, text)")
