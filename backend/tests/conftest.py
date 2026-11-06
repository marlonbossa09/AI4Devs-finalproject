"""Configuración de las pruebas.

Las pruebas son destructivas y el servicio PostgreSQL local es compartido, así que SOLO pueden
tocar la base ``smartwork_test`` (ver tests/aislamiento.py). La validación se hace antes de
importar la aplicación, al abrir la sesión y antes de cada limpieza; si algo no cuadra, se aborta
toda la ejecución sin tocar nada.
"""

import os

import pytest

from app.config import get_settings
from tests.aislamiento import (
    ErrorDeAislamiento,
    exigir_base_de_pruebas,
    validar_conexion,
    validar_distinta_de_desarrollo,
    validar_url_de_pruebas,
)

# Puerto esperado de las URLs de pruebas, para contrastarlo con el que declare el servidor
_PUERTO_ESPERADO: dict[str, int | None] = {}


def _preparar_entorno() -> None:
    settings = get_settings()  # en este punto todavía son los valores de desarrollo del .env
    app_url = settings.test_database_url
    owner_url = settings.test_migrations_database_url
    if not app_url or not owner_url:
        pytest.exit("Faltan TEST_DATABASE_URL o TEST_MIGRATIONS_DATABASE_URL en backend/.env", 2)
    try:
        for url in (app_url, owner_url):
            _PUERTO_ESPERADO[url] = validar_url_de_pruebas(url).port
            validar_distinta_de_desarrollo(url, [settings.database_url, settings.migrations_database_url])
    except ErrorDeAislamiento as error:
        pytest.exit(f"Aislamiento de pruebas no garantizado: {error}", 2)
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = app_url
    os.environ["MIGRATIONS_DATABASE_URL"] = owner_url
    os.environ["WEB_CLIENT_DIR"] = ""  # las pruebas no dependen de que el cliente esté compilado
    get_settings.cache_clear()


_preparar_entorno()


# ---------------------------------------------------------------------------------------------
# Esquema y datos: migraciones reales sobre la base de pruebas, y base limpia en cada prueba
# ---------------------------------------------------------------------------------------------

from pathlib import Path  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import get_engine, get_owner_engine  # noqa: E402

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
TABLAS = (
    "auditoria, clave_idempotencia, sesion, identidad, avance, planificacion, actividad, "
    "bitacora, pertenencia, persona, equipo, organizacion"
)


@pytest.fixture(scope="session", autouse=True)
def esquema():
    """Confirma con el servidor a qué se conecta cada rol y solo entonces parte de cero y aplica
    todas las migraciones (también comprueba que se pueden revertir)."""
    settings = get_settings()
    try:
        for motor, url in ((get_engine(), settings.database_url), (get_owner_engine(), settings.migrations_database_url)):
            with motor.connect() as conexion:
                validar_conexion(conexion, puerto_esperado=_PUERTO_ESPERADO.get(url))
    except ErrorDeAislamiento as error:
        pytest.exit(f"Aislamiento de pruebas no garantizado: {error}", 2)
    configuracion = Config(str(RAIZ_BACKEND / "alembic.ini"))
    command.downgrade(configuracion, "base")
    command.upgrade(configuracion, "head")
    yield


@pytest.fixture(autouse=True)
def base_limpia(esquema):
    with get_owner_engine().begin() as c:
        exigir_base_de_pruebas(c)  # justo antes de vaciar: la misma conexión debe estar en smartwork_test
        c.execute(text(f"TRUNCATE {TABLAS} CASCADE"))
    yield
