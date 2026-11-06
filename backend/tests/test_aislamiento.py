"""El aislamiento de las pruebas: solo se puede tocar ``smartwork_test``, y se comprueba de verdad."""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db import get_engine, get_owner_engine
from tests.aislamiento import (
    BASE_DE_PRUEBAS,
    ErrorDeAislamiento,
    exigir_base_de_pruebas,
    validar_conexion,
    validar_distinta_de_desarrollo,
    validar_url_de_pruebas,
)

BASE = "postgresql+psycopg://u:p@127.0.0.1:5432/"


# --- Validación de las URL -------------------------------------------------------------------

def test_la_url_exacta_de_pruebas_se_acepta():
    assert validar_url_de_pruebas(BASE + "smartwork_test").database == "smartwork_test"
    validar_url_de_pruebas("postgresql+psycopg://u:p@localhost:5432/smartwork_test")


@pytest.mark.parametrize("base", [
    "smartwork_app",        # la base real: jamás
    "smartwork_dev",
    "otra_test",            # termina en _test pero no es la nuestra
    "smartwork_test2",
    "smartwork_test_old",
    "Smartwork_Test",
    "postgres",
    "cleanfastapi", "fastapi", "helpdesk_db", "smartprueba",   # las demás bases del servicio
    "",
])
def test_cualquier_otra_base_se_rechaza(base):
    with pytest.raises(ErrorDeAislamiento):
        validar_url_de_pruebas(BASE + base)


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://u:p@db.ejemplo.com:5432/smartwork_test",   # servidor remoto
    "postgresql+psycopg://u:p@10.0.0.5:5432/smartwork_test",
    "postgresql+psycopg://u:p@127.0.0.1:5433/smartwork_test",        # clúster alternativo descartado
    "mysql://u:p@127.0.0.1:3306/smartwork_test",                      # no es PostgreSQL
    "esto no es una url",
])
def test_servidores_remotos_el_puerto_5433_y_otros_motores_se_rechazan(url):
    with pytest.raises(ErrorDeAislamiento):
        validar_url_de_pruebas(url)


def test_la_base_de_pruebas_no_puede_ser_la_de_desarrollo():
    url = BASE + "smartwork_test"
    validar_distinta_de_desarrollo(url, [BASE + "smartwork_app", None])
    with pytest.raises(ErrorDeAislamiento):
        validar_distinta_de_desarrollo(url, [BASE + "smartwork_test"])


# --- Lo que confirma el propio servidor -------------------------------------------------------

def test_el_servidor_confirma_que_ambas_conexiones_estan_en_smartwork_test():
    settings = get_settings()
    for motor, url in ((get_engine(), settings.database_url), (get_owner_engine(), settings.migrations_database_url)):
        puerto = make_url(url).port
        with motor.connect() as c:
            evidencia = validar_conexion(c, puerto_esperado=puerto)
        assert evidencia["base"] == BASE_DE_PRUEBAS and evidencia["puerto"] == puerto
        assert evidencia["puerto"] != 5433


def test_la_configuracion_efectiva_de_la_aplicacion_apunta_solo_a_smartwork_test():
    settings = get_settings()
    assert settings.app_env == "test"
    assert make_url(settings.database_url).database == BASE_DE_PRUEBAS
    assert make_url(settings.migrations_database_url).database == BASE_DE_PRUEBAS


def test_una_conexion_a_otra_base_seria_rechazada_antes_de_vaciar():
    """exigir_base_de_pruebas protege la limpieza: se simula una conexión a otra base."""

    class Resultado:
        def scalar_one(self):
            return "smartwork_app"

    class ConexionFalsa:
        def execute(self, *_args, **_kwargs):
            return Resultado()

    with pytest.raises(ErrorDeAislamiento):
        exigir_base_de_pruebas(ConexionFalsa())  # type: ignore[arg-type]


def test_los_roles_de_pruebas_no_son_administradores():
    with get_engine().connect() as c:
        super_, crea = c.execute(text(
            "select rolsuper, rolcreatedb from pg_roles where rolname = current_user")).one()
    assert super_ is False and crea is False


def test_la_limpieza_solo_afecta_a_la_base_de_pruebas_en_la_que_esta_conectada():
    """Una conexión de PostgreSQL pertenece a UNA base: TRUNCATE no puede alcanzar otras."""
    with get_owner_engine().connect() as c:
        assert c.execute(text("select current_database()")).scalar_one() == BASE_DE_PRUEBAS
