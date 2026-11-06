"""Bloque 2: estructura de error común y rechazo de campos desconocidos (BE-01)."""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from app.errores import CATALOGO, AppError
from app.main import crear_app


class _Cuerpo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titulo: str | None = None


@pytest.fixture()
def cliente() -> TestClient:
    app = crear_app()

    @app.get("/prueba/error/{codigo}")
    def _lanzar(codigo: str):
        raise AppError(codigo)

    @app.get("/prueba/fallo")
    def _fallo():
        raise RuntimeError("detalle interno secreto")

    @app.post("/prueba/cuerpo")
    def _cuerpo(cuerpo: _Cuerpo):
        return {"ok": True}

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("codigo", sorted(CATALOGO))
def test_cada_codigo_del_catalogo_se_devuelve_con_su_estado_http(cliente, codigo):
    if codigo == "ERROR_INTERNO":
        pytest.skip("Se prueba en el caso de fallo interno")
    r = cliente.get(f"/prueba/error/{codigo}")
    assert r.status_code == CATALOGO[codigo][0]
    cuerpo = r.json()
    assert set(cuerpo) == {"codigo", "mensaje", "detalles"}
    assert cuerpo["codigo"] == codigo
    assert isinstance(cuerpo["detalles"], list)


def test_un_codigo_fuera_del_catalogo_no_se_puede_lanzar():
    with pytest.raises(ValueError):
        AppError("INVENTADO")


def test_un_campo_desconocido_se_rechaza_como_solicitud_invalida(cliente):
    r = cliente.post("/prueba/cuerpo", json={"titulo": "x", "estado": "Completada"})
    assert r.status_code == 400
    assert r.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_el_fallo_interno_no_revela_detalles_y_lleva_correlacion(cliente):
    r = cliente.get("/prueba/fallo")
    assert r.status_code == 500
    assert "secreto" not in r.text and "RuntimeError" not in r.text
    assert r.json()["codigo"] == "ERROR_INTERNO"
    assert r.json()["detalles"][0]["correlacion"]


def test_una_ruta_inexistente_responde_con_el_error_uniforme(cliente):
    r = cliente.get("/api/v1/no-existe")
    assert r.status_code == 404
    assert r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"


def test_la_documentacion_interactiva_no_existe_fuera_de_desarrollo():
    # APP_ENV=test en las pruebas: no se publica /docs ni /openapi.json
    c = TestClient(crear_app(), raise_server_exceptions=False)
    assert c.get("/docs").status_code == 404
    assert c.get("/openapi.json").status_code == 404
