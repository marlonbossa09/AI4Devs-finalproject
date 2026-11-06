"""/health (vivacidad) y /health/ready (disponibilidad de PostgreSQL)."""

import logging
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.config import get_settings
from app.main import crear_app

# Texto que una excepción real de la base de datos podría contener; no debe llegar a la respuesta
SECRETO = "S3cr3t0-d3-prueba"
CADENA = f"postgresql://usuario_x:{SECRETO}@servidor-interno.ejemplo.local:5432/base_secreta"


@pytest.fixture()
def cliente() -> TestClient:
    return TestClient(crear_app(), raise_server_exceptions=False)


def _sin_filtraciones(cuerpo: str) -> None:
    for prohibido in (SECRETO, "servidor-interno", "base_secreta", "postgresql", "usuario_x",
                      "Traceback", "OperationalError", "psycopg", "smartwork_test", "smartwork_app"):
        assert prohibido not in cuerpo, prohibido


# --- /health: vivacidad -----------------------------------------------------------------------

def test_health_responde_200_con_json_minimo(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert r.json() == {"status": "ok"}
    assert r.headers["cache-control"] == "no-store"


def test_health_no_usa_la_base_de_datos(cliente, monkeypatch):
    def prohibido():
        raise AssertionError("/health no debe tocar la base de datos")

    monkeypatch.setattr("app.salud.get_engine", prohibido)
    assert cliente.get("/health").status_code == 200


def test_health_sigue_vivo_aunque_la_base_de_datos_este_caida(cliente, monkeypatch):
    monkeypatch.setattr("app.salud.get_engine", lambda: create_engine("postgresql+psycopg://u:p@127.0.0.1:1/x"))
    assert cliente.get("/health").status_code == 200


# --- /health/ready: disponibilidad ------------------------------------------------------------

def test_ready_responde_200_cuando_postgresql_esta_disponible(cliente):
    r = cliente.get("/health/ready")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert r.json() == {"status": "ok", "checks": {"database": "ok"}}
    assert r.headers["cache-control"] == "no-store"
    _sin_filtraciones(r.text)


def test_ready_responde_503_cuando_la_base_falla_y_no_filtra_nada(cliente, monkeypatch, caplog):
    class MotorQueFalla:
        def connect(self):
            raise OperationalError("select 1", {}, Exception(f"no se pudo conectar a {CADENA}"))

    monkeypatch.setattr("app.salud.get_engine", lambda: MotorQueFalla())
    with caplog.at_level(logging.DEBUG):
        r = cliente.get("/health/ready")
    assert r.status_code == 503
    assert r.headers["content-type"].startswith("application/json")
    assert r.json() == {"status": "unavailable", "checks": {"database": "unavailable"}}
    _sin_filtraciones(r.text)
    # El registro dice qué tipo de fallo fue, pero no el texto de la excepción
    assert "OperationalError" in caplog.text
    assert SECRETO not in caplog.text and "servidor-interno" not in caplog.text


def test_ready_con_un_servidor_real_inalcanzable_da_503_en_pocos_segundos(cliente, monkeypatch):
    """Fallo real, no simulado: nada escucha en el puerto 1 de este equipo."""
    espera = get_settings().db_connect_timeout_seconds
    motor = create_engine(
        "postgresql+psycopg://usuario:clave@127.0.0.1:1/base",
        connect_args={"connect_timeout": espera}, pool_timeout=espera,
    )
    monkeypatch.setattr("app.salud.get_engine", lambda: motor)
    inicio = time.monotonic()
    r = cliente.get("/health/ready")
    assert r.status_code == 503 and r.json()["checks"]["database"] == "unavailable"
    assert time.monotonic() - inicio < espera + 3
    _sin_filtraciones(r.text)
    assert "clave" not in r.text


def test_la_espera_a_la_base_de_datos_esta_acotada_por_configuracion():
    from app.db import get_engine

    espera = get_settings().db_connect_timeout_seconds
    assert espera > 0
    assert get_engine().pool.timeout() == espera


# --- Independencia de la autenticación y del negocio -------------------------------------------

@pytest.mark.parametrize("ruta", ["/health", "/health/ready"])
def test_no_requieren_autenticacion_ni_cabeceras_especiales(cliente, ruta):
    r = cliente.get(ruta)  # sin cookie, sin CSRF, sin Origin
    assert r.status_code == 200


@pytest.mark.parametrize("ruta", ["/health", "/health/ready"])
def test_no_cuelgan_del_prefijo_de_la_api(cliente, ruta):
    assert cliente.get("/api/v1" + ruta).status_code == 404


def test_el_cliente_web_no_tapa_las_rutas_de_salud(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<html>cliente</html>", encoding="utf-8")
    monkeypatch.setattr(get_settings(), "web_client_dir", str(tmp_path))
    c = TestClient(crear_app(), raise_server_exceptions=False)
    assert c.get("/").text.startswith("<html>")
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/health/ready").json()["status"] == "ok"
