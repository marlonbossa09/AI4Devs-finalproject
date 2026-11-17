"""M1-T0 — PA-30: un método HTTP no admitido en una ruta que existe responde 405 con la cabecera ``Allow``.

Decisión aprobada el 2026-11-11: el 400 se mantiene para las solicitudes inválidas, el rechazo de CSRF y de ``Origin``
queda provisionalmente como está (400) y una ruta inexistente sigue siendo el 404 uniforme. El 405 no depende de la
sesión ni del identificador del recurso, así que no revela nada privado. Las pruebas destructivas corren solo sobre
``smartwork_test``.
"""

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_owner_engine
from app.main import crear_app
from tests.fabricas import escenario_basico, hoy
from tests.utiles_http import API, ORIGEN, nuevo_cliente, sesion_iniciada
from tests.utiles_m2 import avanzar, con_clave, contar, iso, planificar_actividad

METODOS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def _rutas() -> dict[str, set[str]]:
    """Métodos declarados por ruta, tomados del esquema OpenAPI (no de la estructura interna del router)."""
    return {ruta: {m.upper() for m in metodos} for ruta, metodos in crear_app().openapi()["paths"].items()}


RUTAS = _rutas()


def _concreta(ruta: str) -> str:
    """Sustituye cada parámetro de la ruta por un valor cualquiera: el 405 solo depende de la forma de la ruta."""
    partes = []
    for trozo in ruta.split("/"):
        partes.append("valor" if trozo.startswith("{") else trozo)
    return "/".join(partes)


def _casos():
    return [(ruta, metodo) for ruta, declarados in sorted(RUTAS.items()) for metodo in METODOS if metodo not in declarados]


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c, desde=hoy() - timedelta(days=400))


@pytest.fixture()
def sesion(esc):
    return sesion_iniciada(esc)


@pytest.fixture()
def cliente_con_web(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<html><body>SMARTWORK cliente</body></html>", encoding="utf-8")
    monkeypatch.setattr(get_settings(), "web_client_dir", str(tmp_path))
    return TestClient(crear_app(), base_url=ORIGEN, raise_server_exceptions=False)


def _allow(ruta: str) -> str:
    return ", ".join(sorted(RUTAS[ruta]))


def _comprobar_405(r, esperado_allow: str):
    assert r.status_code == 405, (r.status_code, r.text)
    assert r.headers["Allow"] == esperado_allow
    if r.request.method != "HEAD":  # una respuesta a HEAD no lleva cuerpo
        cuerpo = r.json()
        assert cuerpo["codigo"] == "METODO_NO_PERMITIDO"
        assert cuerpo["detalles"] == [{"campo": "metodo", "motivo": "metodo_no_permitido"}]


# ============================ todas las rutas existentes ==================================================

def test_el_catalogo_de_rutas_cubre_las_rutas_de_la_api():
    """Salvaguarda de las pruebas siguientes: si se añade una ruta, entra sola en la comprobación."""
    assert f"{API}/sesion" in RUTAS and f"{API}/auditoria" in RUTAS and "/health" in RUTAS
    assert len(RUTAS) >= 17 and len(_casos()) > 100


@pytest.mark.parametrize("ruta,metodo", _casos())
def test_un_metodo_no_admitido_en_una_ruta_existente_responde_405_con_allow(ruta, metodo):
    r = nuevo_cliente().request(metodo, _concreta(ruta), headers={"Origin": ORIGEN})
    _comprobar_405(r, _allow(ruta))


@pytest.mark.parametrize("ruta,metodo", _casos())
def test_el_405_es_el_mismo_con_sesion_iniciada_y_sin_ella(sesion, ruta, metodo):
    cliente, csrf = sesion
    sin_sesion = nuevo_cliente().request(metodo, _concreta(ruta))
    con_sesion = cliente.request(metodo, _concreta(ruta), headers=con_clave(csrf))
    _comprobar_405(sin_sesion, _allow(ruta))
    _comprobar_405(con_sesion, _allow(ruta))
    if metodo != "HEAD":
        assert sin_sesion.json() == con_sesion.json()


def test_allow_reune_los_metodos_de_todas_las_rutas_que_comparten_la_misma_ruta():
    """``/sesion`` está registrada con POST (iniciar), GET (consultar): Allow las lista todas, ordenadas."""
    assert RUTAS[f"{API}/sesion"] == {"GET", "POST"}
    r = nuevo_cliente().delete(f"{API}/sesion")
    _comprobar_405(r, "GET, POST")
    assert RUTAS[f"{API}/mi/bitacoras/{{fecha_laboral}}"] == {"GET"}
    _comprobar_405(nuevo_cliente().post(f"{API}/mi/bitacoras/2026-01-01"), "GET")


def test_head_sobre_una_ruta_solo_de_lectura_tambien_responde_405_con_allow():
    r = nuevo_cliente().head(f"{API}/auditoria")
    _comprobar_405(r, "GET")
    assert r.content == b""


def test_options_sin_cors_responde_405_con_allow():
    """Sin CORS (producción y pruebas) no hay una respuesta de preselección: OPTIONS es un método más."""
    _comprobar_405(nuevo_cliente().options(f"{API}/sesion"), "GET, POST")


# ============================ lo que no cambia ============================================================

@pytest.mark.parametrize("metodo", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_una_ruta_inexistente_sigue_siendo_el_404_uniforme_sin_allow(sesion, metodo):
    cliente, csrf = sesion
    for c in (nuevo_cliente(), cliente):
        r = c.request(metodo, f"{API}/no-existe", headers=con_clave(csrf))
        assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE" and "Allow" not in r.headers


def test_las_solicitudes_invalidas_siguen_siendo_400(sesion):
    cliente, csrf = sesion
    r = nuevo_cliente().post(f"{API}/sesion", json={"identificador_acceso": "x", "contrasena": "y", "otro": 1},
                             headers={"Origin": ORIGEN})
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA" and "Allow" not in r.headers
    r = cliente.get(f"{API}/auditoria")  # sin los parámetros obligatorios
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_csrf_y_origen_siguen_rechazandose_con_400(sesion):
    """Provisionalmente como estaba (PA-30): una escritura con un método admitido sin token o de otro origen es 400."""
    cliente, csrf = sesion
    ruta = f"{API}/mi/actividades/{uuid.uuid4()}/marca-error"
    sin_csrf = cliente.post(ruta, json={"motivo": "x"}, headers={"Origin": ORIGEN, "Idempotency-Key": uuid.uuid4().hex})
    otro_origen = cliente.post(ruta, json={"motivo": "x"},
                               headers={"Origin": "http://otro.invalid", "X-CSRF-Token": csrf, "Idempotency-Key": uuid.uuid4().hex})
    for r in (sin_csrf, otro_origen):
        assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA" and "Allow" not in r.headers


def test_un_metodo_no_admitido_se_rechaza_antes_que_el_csrf_y_el_origen(sesion):
    """El 405 depende de la ruta, no de la petición: con token inválido y otro origen sigue siendo 405."""
    cliente, csrf = sesion
    r = cliente.delete(f"{API}/mi/avances/{uuid.uuid4()}", headers={"Origin": "http://otro.invalid", "X-CSRF-Token": "mal"})
    _comprobar_405(r, "PATCH")


def test_los_metodos_admitidos_siguen_funcionando_como_antes(sesion):
    cliente, csrf = sesion
    assert cliente.get(f"{API}/sesion").status_code == 200
    assert cliente.get(f"{API}/mi/actividades").status_code == 200
    a = planificar_actividad(cliente, csrf, iso(0))
    assert avanzar(cliente, csrf, a, iso(0)).status_code == 201
    assert nuevo_cliente().get("/health").status_code == 200


# ============================ no revela información privada ===============================================

def test_el_405_no_depende_de_que_el_recurso_exista(sesion):
    """Un avance que existe y un identificador cualquiera dan exactamente la misma respuesta."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    avance = avanzar(cliente, csrf, a, iso(0)).json()["avance"]["id"]
    existente = cliente.delete(f"{API}/mi/avances/{avance}", headers=con_clave(csrf))
    inexistente = cliente.delete(f"{API}/mi/avances/{uuid.uuid4()}", headers=con_clave(csrf))
    ajeno = nuevo_cliente().delete(f"{API}/mi/avances/{avance}")
    for r in (existente, inexistente, ajeno):
        _comprobar_405(r, "PATCH")
    assert existente.json() == inexistente.json() == ajeno.json()


def test_un_metodo_no_admitido_no_modifica_nada(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    avance = avanzar(cliente, csrf, a, iso(0)).json()["avance"]["id"]
    antes = (contar("avance"), contar("actividad"), contar("auditoria"), contar("bitacora"))
    for metodo, ruta in (("DELETE", f"/mi/avances/{avance}"), ("PUT", f"/mi/actividades/{a}"), ("PATCH", f"/mi/actividades/{a}"),
                         ("DELETE", f"/mi/actividades/{a}"), ("POST", "/auditoria"), ("PUT", "/mi/bitacoras/2026-01-01/cierre")):
        r = cliente.request(metodo, f"{API}{ruta}", headers=con_clave(csrf))
        assert r.status_code == 405, (metodo, ruta, r.status_code)
    assert (contar("avance"), contar("actividad"), contar("auditoria"), contar("bitacora")) == antes


# ============================ con el cliente web montado ==================================================

def test_con_el_cliente_web_montado_todas_las_rutas_de_la_api_dan_el_mismo_allow(cliente_con_web):
    """El servidor de ficheros estáticos responde ``Allow: GET, HEAD`` y, con GET, buscaría un fichero: la API no debe
    heredar ninguna de las dos cosas."""
    casos = _casos()
    assert len(casos) > 100
    for ruta, metodo in casos:
        _comprobar_405(cliente_con_web.request(metodo, _concreta(ruta)), _allow(ruta))


def test_con_el_cliente_web_montado_un_metodo_no_admitido_sobre_un_fichero_es_405_con_get_y_head(cliente_con_web):
    for metodo in ("POST", "PUT", "DELETE"):
        _comprobar_405(cliente_con_web.request(metodo, "/index.html"), "GET, HEAD")
    _comprobar_405(cliente_con_web.post("/"), "GET, HEAD")
    assert cliente_con_web.get("/").status_code == 200


def test_con_el_cliente_web_montado_una_ruta_de_la_api_inexistente_sigue_siendo_404(cliente_con_web):
    r = cliente_con_web.delete(f"{API}/no-existe")
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"
