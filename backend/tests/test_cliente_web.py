"""El cliente compilado se sirve en el mismo origen que la API, sin quitarle prioridad a la API."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import crear_app


@pytest.fixture()
def cliente_con_web(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<html><body>SMARTWORK cliente</body></html>", encoding="utf-8")
    monkeypatch.setattr(get_settings(), "web_client_dir", str(tmp_path))
    return TestClient(crear_app(), base_url="https://testserver", raise_server_exceptions=False)


def test_se_sirve_el_cliente_en_la_raiz(cliente_con_web):
    r = cliente_con_web.get("/")
    assert r.status_code == 200 and "SMARTWORK cliente" in r.text


def test_la_api_sigue_teniendo_prioridad_sobre_el_cliente(cliente_con_web):
    r = cliente_con_web.get("/api/v1/sesion")
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"


def test_una_ruta_de_la_api_inexistente_responde_con_el_error_uniforme(cliente_con_web):
    r = cliente_con_web.get("/api/v1/no-existe")
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"


def test_sin_carpeta_configurada_solo_se_publica_la_api(monkeypatch):
    monkeypatch.setattr(get_settings(), "web_client_dir", None)
    r = TestClient(crear_app(), raise_server_exceptions=False).get("/")
    assert r.status_code == 404
