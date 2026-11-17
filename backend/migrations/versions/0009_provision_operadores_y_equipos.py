"""Provisión administrativa inicial (M1-T2): personas operadoras, nombre de equipo único y rol de provisión.

Qué crea (ADR-002, secciones 9 y 10; contratos M1-02a y M1-02b; decisiones aprobadas el 2026-11-11):

- ``operador``: persona operadora de provisión con identificador y credencial PROPIOS (opción C del ADR-002). Solo se guarda
  el hash Argon2id de la credencial. Una operadora no es un rol funcional del producto (RN-33): no es una ``persona``, no
  pertenece a ningún equipo y no tiene permisos sobre los registros de M2 ni de M3.
- Nombre de equipo único por organización (P6), comparando sin distinguir mayúsculas y sin espacios exteriores. No se
  quitan acentos ni espacios interiores. La aplicación normaliza igual antes de insertar; el índice es la garantía final.
- ``auditoria.propietaria_registro_id`` pasa a admitir NULL, SOLO para entradas de provisión: la creación de un equipo o
  de una operadora no tiene propietaria de registro. Las entradas de personas siguen exigiéndola. No cambia ninguna
  entrada existente.
- Privilegios mínimos del rol de provisión (separado del propietario y de la aplicación). El rol lo crea quien administra
  el servidor (``scripts/provision_rol_de_provision.sql``): la migración no puede crear roles.

La aplicación (``APP_DB_ROLE``) NO recibe ningún permiso sobre ``operador``: no puede leer credenciales ni ejecutar órdenes
de provisión. El rol de provisión NO recibe ningún permiso sobre bitácoras, actividades, planificaciones, avances, sesiones
ni claves de idempotencia: una operadora no puede alterar la información funcional de M2 ni de M3.
"""

import re

from alembic import op
from sqlalchemy import text

from app.config import get_settings

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

# Privilegios de la provisión, tabla a tabla (los mínimos de M1-02a y M1-02b).
PRIVILEGIOS = {
    "organizacion": "SELECT",            # comprobar que la organización existe y leer su zona horaria
    "equipo": "SELECT, INSERT",          # crear equipos y comprobar su unicidad
    "persona": "SELECT, INSERT",         # crear personas
    "pertenencia": "SELECT, INSERT",     # leer la línea temporal del equipo (IR-32) y crear la primera pertenencia
    "identidad": "SELECT, INSERT",       # crear la identidad (sin contraseña) y comprobar la unicidad del identificador
    "operador": "SELECT",                # identificar a quien opera (verificar su credencial)
    "auditoria": "INSERT",               # una entrada de provisión por orden
}


def _rol(nombre: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", nombre):
        raise ValueError("El nombre del rol no es un identificador válido")
    return f'"{nombre}"'


def _exigir_rol_de_provision(rol: str) -> None:
    existe = op.get_bind().execute(text("select 1 from pg_roles where rolname = :r"), {"r": rol}).first()
    if existe is None:
        raise RuntimeError(
            f"No existe el rol de PostgreSQL de provisión {rol!r}. Un administrador del servidor debe crearlo antes de "
            "migrar: ver backend/scripts/provision_rol_de_provision.sql (la migración no puede crear roles)."
        )


def upgrade() -> None:
    settings = get_settings()
    rol_provision = settings.provision_db_role
    _exigir_rol_de_provision(rol_provision)

    op.execute("""
        CREATE TABLE operador (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            -- Identificador nominal de la persona operadora, normalizado como el de las personas (ADR-002, sección 4).
            identificador text NOT NULL UNIQUE,
            -- Cadena Argon2id (incluye sus parámetros). Nunca la credencial.
            hash_credencial text NOT NULL,
            estado text NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'revocado')),
            creado_en timestamptz NOT NULL DEFAULT now(),
            revocado_en timestamptz,
            concedido_por uuid REFERENCES operador (id),
            CONSTRAINT operador_identificador_normalizado CHECK (
                identificador <> '' AND identificador = lower(btrim(identificador))
            ),
            CONSTRAINT operador_revocacion_coherente CHECK ((estado = 'revocado') = (revocado_en IS NOT NULL))
        )
    """)

    # P6: nombre único por organización, sin distinguir mayúsculas ni espacios exteriores (espacio, tabulador, retorno,
    # salto de línea, salto de página y tabulación vertical). No se quitan acentos ni espacios interiores.
    op.execute(
        "CREATE UNIQUE INDEX equipo_nombre_unico_por_organizacion "
        "ON equipo (organizacion_id, lower(btrim(nombre, E' \t\r\n\f\v')))"
    )

    # Una entrada de provisión puede no tener propietaria de registro (crear un equipo o una persona operadora).
    op.execute("ALTER TABLE auditoria ALTER COLUMN propietaria_registro_id DROP NOT NULL")
    op.execute("ALTER TABLE auditoria DROP CONSTRAINT IF EXISTS auditoria_propietaria_segun_autor")
    op.execute("""
        ALTER TABLE auditoria ADD CONSTRAINT auditoria_propietaria_segun_autor CHECK (
            tipo_autor = 'provision' OR propietaria_registro_id IS NOT NULL
        )
    """)

    rol = _rol(rol_provision)
    for tabla, permisos in PRIVILEGIOS.items():
        op.execute(f"GRANT {permisos} ON {tabla} TO {rol}")


def downgrade() -> None:
    rol_provision = get_settings().provision_db_role
    existe = op.get_bind().execute(text("select 1 from pg_roles where rolname = :r"), {"r": rol_provision}).first()
    if existe is not None:
        rol = _rol(rol_provision)
        for tabla in PRIVILEGIOS:
            op.execute(f"REVOKE ALL ON {tabla} FROM {rol}")
    op.execute("DROP INDEX equipo_nombre_unico_por_organizacion")
    # La auditoría es de solo anexado: revertir esta migración NO borra entradas ni vuelve a exigir la propietaria, para no
    # destruir las entradas de provisión ya registradas. La restricción auditoria_propietaria_segun_autor se conserva.
    op.execute("DROP TABLE operador")
