"""Utilidades para probar la API por HTTP.

El cliente usa https://testserver porque la cookie ``__Host-`` es Secure: el cliente HTTP solo la
reenvía por HTTPS, igual que haría un navegador (que además trata localhost como contexto seguro).
"""

from fastapi.testclient import TestClient

from app.main import crear_app

ORIGEN = "https://testserver"
API = "/api/v1"


def nuevo_cliente(cookies: dict[str, str] | None = None) -> TestClient:
    cliente = TestClient(crear_app(), base_url=ORIGEN, raise_server_exceptions=False)
    for nombre, valor in (cookies or {}).items():
        cliente.cookies.set(nombre, valor)
    return cliente


def iniciar_sesion(cliente: TestClient, identificador: str, contrasena: str, origen: str | None = ORIGEN):
    cabeceras = {"Origin": origen} if origen else {}
    return cliente.post(f"{API}/sesion", json={"identificador_acceso": identificador, "contrasena": contrasena},
                        headers=cabeceras)


def cabeceras(csrf: str, **extra: str) -> dict[str, str]:
    return {"Origin": ORIGEN, "X-CSRF-Token": csrf, **extra}


def sesion_iniciada(esc) -> tuple[TestClient, str]:
    """Inicia sesión con el escenario dado y devuelve el cliente (con cookie) y el token CSRF."""
    cliente = nuevo_cliente()
    r = iniciar_sesion(cliente, esc.identificador, esc.contrasena)
    assert r.status_code == 201, r.text
    return cliente, r.json()["csrf_token"]
