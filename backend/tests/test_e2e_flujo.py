"""Extremo a extremo (bloque 8): el flujo completo contra un servidor REAL en otro proceso.

Un colaborador inicia sesión, consulta su bitácora (que no existe y no se crea), la abre,
planifica una actividad, la consulta de nuevo, y todo sigue ahí cuando el proceso del servidor se
REINICIA: los datos y la sesión están en PostgreSQL, no en memoria.

Se usa HTTP real (uvicorn en un subproceso). La cookie ``__Host-`` es Secure y un cliente solo la
reenvía por HTTPS, así que aquí se reenvía a mano en la cabecera Cookie.
"""

import os
import socket
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import text

from app.db import get_owner_engine
from app.seguridad.sesiones import NOMBRE_COOKIE
from tests.fabricas import escenario_basico, hoy
from tests.conftest import RAIZ_BACKEND


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def servidor_real(puerto: int):
    proceso = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(puerto),
         "--log-level", "warning"],
        cwd=RAIZ_BACKEND, env=os.environ.copy(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        limite = time.time() + 30
        while time.time() < limite:
            try:
                httpx.get(f"http://127.0.0.1:{puerto}/api/v1/sesion", timeout=1)
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            raise RuntimeError("El servidor no arrancó a tiempo")
        yield
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()


def test_flujo_completo_y_persistencia_tras_reiniciar_el_servidor():
    with get_owner_engine().begin() as c:
        esc = escenario_basico(c, desde=hoy() - timedelta(days=30))
    puerto = _puerto_libre()
    base = f"http://127.0.0.1:{puerto}/api/v1"
    origen = f"http://127.0.0.1:{puerto}"
    fecha = hoy().isoformat()

    with servidor_real(puerto):
        # 1. Sin sesión no hay datos
        assert httpx.get(f"{base}/mi/bitacoras/{fecha}").status_code == 401

        # 2. Inicio de sesión real: cookie __Host- Secure/HttpOnly/SameSite=Strict y token CSRF
        r = httpx.post(f"{base}/sesion", headers={"Origin": origen},
                       json={"identificador_acceso": esc.identificador, "contrasena": esc.contrasena})
        assert r.status_code == 201
        set_cookie = r.headers["set-cookie"].lower()
        assert set_cookie.startswith(f"{NOMBRE_COOKIE.lower()}=")
        assert "secure" in set_cookie and "httponly" in set_cookie and "samesite=strict" in set_cookie
        secreto = r.cookies.get(NOMBRE_COOKIE)
        cookie = {"Cookie": f"{NOMBRE_COOKIE}={secreto}"}
        csrf = r.json()["csrf_token"]

        # 3. La sesión se puede consultar y trae la fecha actual del servidor
        sesion = httpx.get(f"{base}/sesion", headers=cookie).json()
        assert sesion["fecha_actual"] == fecha and sesion["rol_vigente"] == "colaborador"

        # 4. Consultar su bitácora: no existe y consultar no la crea
        assert httpx.get(f"{base}/mi/bitacoras/{fecha}", headers=cookie).status_code == 404

        # 5. Abrirla
        escritura = {**cookie, "Origin": origen, "X-CSRF-Token": csrf}
        r = httpx.post(f"{base}/mi/bitacoras", headers=escritura, json={"fecha_laboral": fecha})
        assert r.status_code == 201 and r.json()["creada"] is True

        # 6. Registrar una actividad planificada
        clave = uuid.uuid4().hex
        r = httpx.post(f"{base}/mi/bitacoras/{fecha}/planificaciones", json={
            "titulo": "Preparar informe mensual", "descripcion": "Revisar cifras"},
            headers={**escritura, "Idempotency-Key": clave})
        assert r.status_code == 201
        actividad_id = r.json()["actividad"]["id"]

        # 7. Consultar de nuevo: lo guardado está ahí
        g = httpx.get(f"{base}/mi/bitacoras/{fecha}", headers=cookie).json()
        assert [a["titulo"] for a in g["actividades"]] == ["Preparar informe mensual"]
        assert g["actividades"][0]["estado_actual"] == "Pendiente" and g["avances"] == []

    # 8. El proceso del servidor se reinicia: nada vive en su memoria
    with servidor_real(puerto):
        # La misma sesión sigue siendo válida (vive en PostgreSQL) y los datos persisten
        g = httpx.get(f"{base}/mi/bitacoras/{fecha}", headers=cookie).json()
        assert [a["id"] for a in g["actividades"]] == [actividad_id]
        assert g["planificaciones"][0]["descripcion"] == "Revisar cifras"

        # El reintento de la misma intención devuelve la respuesta original, sin duplicar
        r = httpx.post(f"{base}/mi/bitacoras/{fecha}/planificaciones", json={
            "titulo": "Preparar informe mensual", "descripcion": "Revisar cifras"},
            headers={**escritura, "Idempotency-Key": clave})
        assert r.status_code == 201 and r.headers["idempotency-replayed"] == "true"
        assert r.json()["actividad"]["id"] == actividad_id

        # 9. Cerrar la sesión la revoca en el servidor, aunque se conserve la cookie
        assert httpx.post(f"{base}/sesion/cierre", headers=escritura).status_code == 204
        assert httpx.get(f"{base}/sesion", headers=cookie).status_code == 401

        # 10. Volver a entrar: los datos siguen ahí
        r = httpx.post(f"{base}/sesion", headers={"Origin": origen},
                       json={"identificador_acceso": esc.identificador, "contrasena": esc.contrasena})
        nueva = {"Cookie": f"{NOMBRE_COOKIE}={r.cookies.get(NOMBRE_COOKIE)}"}
        assert nueva != cookie
        g = httpx.get(f"{base}/mi/bitacoras/{fecha}", headers=nueva).json()
        assert [a["titulo"] for a in g["actividades"]] == ["Preparar informe mensual"]

    with get_owner_engine().connect() as c:
        assert c.execute(text("select count(*) from actividad")).scalar_one() == 1   # una sola, pese al reintento
        assert c.execute(text("select count(*) from bitacora")).scalar_one() == 1
