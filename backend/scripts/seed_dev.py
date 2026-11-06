"""Semilla de datos FICTICIOS para el desarrollo y la demostración (DB-07).

Uso (desde backend/):  uv run python -m scripts.seed_dev

Garantías:
- Solo corre en entorno de desarrollo o de pruebas, contra un servidor local (127.0.0.1,
  localhost o ::1) y una base cuyo nombre termine en ``_dev`` o ``_test``. Si no, se niega.
  Una base con otro nombre exige autorización explícita y por nombre exacto en cada ejecución:
  ``SMARTWORK_SEED_DATABASE=<nombre>``.
- Las contraseñas se generan al ejecutarla, se muestran UNA sola vez y no se guardan en ningún
  archivo. No hay contraseñas ni claves en el repositorio.
- Ningún dato corresponde a una persona real.
- Escribe directamente con el rol propietario: no es una orden de provisión (esas quedan fuera
  de la Entrega 2) y por eso no deja entradas de auditoría de provisión. Las pertenencias
  empiezan en el pasado para poder demostrar jornadas pasadas; el modelo permite representar
  períodos históricos (IR-30, última frase).
"""

import os
import secrets
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db import get_owner_engine
from app.seguridad.contrasenas import calcular_hash
from app.seguridad.identificadores import normalizar_identificador

ZONA_HORARIA_DEMO = "America/Bogota"  # dato de la semilla; no es una regla del producto
DIAS_DE_HISTORIAL = 60

PERSONAS_DEMO = (
    # (nombre ficticio, identificador de acceso, rol)
    ("Sofía Supervisora (demo)", "supervisor.demo", "supervisor"),
    ("Carlos Colaborador (demo)", "colaborador1.demo", "colaborador"),
    ("Camila Colaboradora (demo)", "colaborador2.demo", "colaborador"),
)


class EntornoNoPermitido(RuntimeError):
    pass


def comprobar_entorno_local(url: str, app_env: str) -> None:
    if app_env not in ("development", "test"):
        raise EntornoNoPermitido(f"Entorno no permitido: {app_env}")
    u = make_url(url)
    if (u.host or "") not in ("127.0.0.1", "localhost", "::1"):
        raise EntornoNoPermitido("La semilla solo puede ejecutarse contra un servidor local")
    nombre = u.database or ""
    autorizada = os.environ.get("SMARTWORK_SEED_DATABASE")
    if not (nombre.endswith("_dev") or nombre.endswith("_test") or (autorizada and autorizada == nombre)):
        raise EntornoNoPermitido(
            "La base de datos debe terminar en _dev o _test, o autorizarse por su nombre exacto "
            "con SMARTWORK_SEED_DATABASE"
        )


def sembrar(engine: Engine, zona: str = ZONA_HORARIA_DEMO) -> dict[str, dict[str, str]]:
    """Crea la organización, el equipo y las personas ficticias. Devuelve, por identificador de
    acceso, la contraseña generada (para mostrarla una vez)."""
    hoy = datetime.now(ZoneInfo(zona)).date()
    desde: date = hoy - timedelta(days=DIAS_DE_HISTORIAL)
    credenciales: dict[str, dict[str, str]] = {}
    with engine.begin() as c:
        if c.execute(text("select count(*) from organizacion")).scalar():
            raise EntornoNoPermitido("La base ya contiene datos; la semilla no sobrescribe")
        org = c.execute(
            text("insert into organizacion (nombre, zona_horaria) values (:n, :z) returning id"),
            {"n": "Organización Demo", "z": zona},
        ).scalar_one()
        equipo = c.execute(
            text("insert into equipo (organizacion_id, nombre) values (:o, :n) returning id"),
            {"o": org, "n": "Equipo Demo"},
        ).scalar_one()
        for nombre, identificador, rol in PERSONAS_DEMO:
            contrasena = secrets.token_urlsafe(18)
            persona = c.execute(
                text("insert into persona (nombre) values (:n) returning id"), {"n": nombre}
            ).scalar_one()
            c.execute(
                text("insert into identidad (persona_id, identificador_acceso, hash_contrasena) "
                     "values (:p, :i, :h)"),
                {"p": persona, "i": normalizar_identificador(identificador),
                 "h": calcular_hash(contrasena)},
            )
            c.execute(
                text("insert into pertenencia (persona_id, equipo_id, rol, desde) "
                     "values (:p, :e, :r, :d)"),
                {"p": persona, "e": equipo, "r": rol, "d": desde},
            )
            credenciales[identificador] = {"rol": rol, "contrasena": contrasena}
    return credenciales


def main() -> int:
    settings = get_settings()
    try:
        comprobar_entorno_local(settings.migrations_database_url, settings.app_env)
        credenciales = sembrar(get_owner_engine())
    except EntornoNoPermitido as error:
        print(f"Semilla rechazada: {error}", file=sys.stderr)
        return 1
    print("Datos ficticios creados. Estas contraseñas se muestran UNA sola vez y no se guardan:")
    for identificador, datos in credenciales.items():
        print(f"  {identificador:<20} ({datos['rol']:<11}) contraseña: {datos['contrasena']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
