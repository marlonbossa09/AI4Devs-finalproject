r"""Canje del código de primer acceso (M1-T8.3; contrato M1-03b; ADR-002, secciones 4 y 6; decisiones A3, A4, D2 y D7 del 2026-11-17).

Crea UNA función, ``canjear_codigo_primer_acceso``, con ``SECURITY DEFINER``, que es la única forma en que la aplicación puede establecer la
contraseña de una identidad y consumir un código. La aplicación NO recibe ningún permiso de escritura sobre ``identidad`` ni sobre ``codigo_unico``
(ni de lectura del hash del código): solo ``EXECUTE`` sobre esta función.

Por qué esta estrategia y qué la hace segura contra la escalada de privilegios (D2):

- **Sin SQL dinámico:** solo sentencias fijas. Los tres parámetros son DATOS (identificador normalizado, HMAC del código y hash Argon2id de la
  contraseña); ninguno se interpreta como identificador, nombre de objeto ni código SQL.
- **``search_path`` fijo** a ``pg_catalog, pg_temp`` y todos los objetos van calificados con ``public.``: una persona que cambie su ``search_path`` o
  cree objetos temporales no puede hacer que la función resuelva nada distinto.
- **``EXECUTE`` revocado a PUBLIC** y concedido únicamente al rol de la aplicación (no al de provisión).
- **Alcance mínimo:** solo puede (a) incrementar ``intentos_fallidos`` del código pendiente de ESA identidad, (b) marcar ese código como usado,
  (c) fijar ``hash_contrasena`` de ESA identidad si estaba vacío (un disparador fija ``contrasena_establecida_en``), (d) revocar sus sesiones y (e) insertar
  su entrada de auditoría. La identidad y el código se localizan por el identificador de acceso y por el vínculo del código con esa misma identidad:
  un código de una persona no sirve para otra ni para ningún otro campo.
- **Propietario:** el de la migración (``smartwork_owner``), que no es superusuario ni crea roles ni bases (lo comprueban las pruebas). Un rol propio
  de solo este canje sería preferible, pero crear roles exige un administrador del servidor y una migración no puede hacerlo.
- **Parámetros validados:** el HMAC debe ser hexadecimal de 64 y el hash de contraseña una cadena Argon2id de longitud acotada; si no, no hace nada.

Qué hace, de forma ATÓMICA (si falla cualquier parte, incluida la auditoría, no se consume el código ni se toca la identidad):

1. Localiza la identidad por su identificador y toma el bloqueo por persona (el del inicio de sesión, la desactivación y la emisión).
2. Con el bloqueo: rechaza si el acceso está desactivado (DD-05) o si la contraseña ya está establecida (el primer acceso solo se canjea una vez).
3. Busca el código PENDIENTE (no usado, no invalidado y no caducado, con el reloj de PostgreSQL) de primer acceso de esa identidad, con bloqueo de fila.
4. Si el HMAC no coincide, suma un intento fallido (a los 10 el código se invalida solo) y devuelve nulo. Si coincide: lo usa, fija la contraseña, revoca las
   sesiones y audita (``entrega_acceso``, fase ``canje``, la persona como autora), y devuelve la persona.

Todos los rechazos devuelven NULO sin distinguir la causa. La función no crea ninguna sesión.
"""

import re

from alembic import op

from app.config import get_settings

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def _rol(nombre: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", nombre):
        raise ValueError("El nombre del rol no es un identificador válido")
    return nombre


def upgrade() -> None:
    app = _rol(get_settings().app_db_role)
    op.execute(r"""
        CREATE FUNCTION public.canjear_codigo_primer_acceso(p_identificador text, p_hash_codigo text, p_hash_contrasena text)
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
            IF v_desactivado IS NOT NULL OR v_establecida IS NOT NULL THEN
                RETURN NULL;
            END IF;

            SELECT c.id, c.hash_codigo INTO v_codigo, v_hash FROM public.codigo_unico c
            WHERE c.identidad_id = v_identidad AND c.finalidad = 'primer_acceso' AND c.usado_en IS NULL AND c.invalidado_en IS NULL
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
            UPDATE public.identidad SET hash_contrasena = p_hash_contrasena WHERE id = v_identidad AND hash_contrasena IS NULL;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'No se pudo establecer la contraseña' USING ERRCODE = '23514';
            END IF;
            UPDATE public.sesion SET revocada_en = clock_timestamp() WHERE identidad_id = v_identidad AND revocada_en IS NULL;
            GET DIAGNOSTICS v_sesiones = ROW_COUNT;
            INSERT INTO public.auditoria (tipo_autor, autor_persona_id, operacion, tipo_objeto, objeto_id, propietaria_registro_id,
                                          valor_anterior, valor_nuevo)
            VALUES ('persona', v_persona, 'entrega_acceso', 'persona', v_persona, v_persona,
                    jsonb_build_object('contrasena_establecida', false),
                    jsonb_build_object('fase', 'canje', 'finalidad', 'primer_acceso', 'codigo_id', v_codigo,
                                       'contrasena_establecida', true, 'sesiones_revocadas', v_sesiones));
            RETURN v_persona;
        END $$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.canjear_codigo_primer_acceso(text, text, text) FROM PUBLIC")
    op.execute(f'GRANT EXECUTE ON FUNCTION public.canjear_codigo_primer_acceso(text, text, text) TO "{app}"')


def downgrade() -> None:
    op.execute("DROP FUNCTION public.canjear_codigo_primer_acceso(text, text, text)")
