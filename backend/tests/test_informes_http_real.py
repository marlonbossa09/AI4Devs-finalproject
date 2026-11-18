"""M5-T4 — recorrido HTTP REAL de los informes sobre la aplicación PRINCIPAL: un servidor uvicorn en otro proceso (``app.main:app``), sockets reales, la configuración por variables de entorno y PostgreSQL
desechable. Sin ningún servicio externo.

Tres servidores sobre la misma base: con la configuración POR DEFECTO (generación desactivada), con la generación habilitada y el simulado pedido expresamente, y con un generador simulado que devuelve una salida
malformada (la única sustitución de prueba, ``tests/app_informes_prueba.py``).
"""

import dataclasses
import json
import os
import re
import socket
import subprocess
import sys
import time
from contextlib import contextmanager

import httpx
from sqlalchemy import text

from app.compartido.visibilidad import consultante_de
from app.db import get_owner_engine
from app.modulos.informes.consolidado import preparar_informe_consolidado
from app.modulos.informes.individual import preparar_informe_individual
from app.modulos.informes.presentacion import DECLARACION_DE_BASE
from app.seguridad.sesiones import NOMBRE_COOKIE
from tests.conftest import RAIZ_BACKEND
from tests.test_informe_consolidado import CLAVE, H, d, db, mundo, mundo2  # noqa: F401  (escenario de M5-T1 y M5-T2)
from tests.test_informe_individual import _actividad, _bitacora

UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def servidor(entorno: dict[str, str], aplicacion: str = "app.main:app"):
    puerto = _puerto_libre()
    proceso = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", aplicacion, "--host", "127.0.0.1", "--port", str(puerto), "--log-level", "warning"],
        cwd=RAIZ_BACKEND, env={**os.environ, **entorno}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        limite = time.time() + 40
        while time.time() < limite:
            try:
                httpx.get(f"http://127.0.0.1:{puerto}/api/v1/sesion", timeout=1)
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            raise RuntimeError("El servidor no arrancó a tiempo")
        yield f"http://127.0.0.1:{puerto}/api/v1", f"http://127.0.0.1:{puerto}"
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()


def entrar(base: str, origen: str, nombre: str) -> dict[str, str]:
    r = httpx.post(f"{base}/sesion", headers={"Origin": origen}, json={"identificador_acceso": f"acceso-{nombre}-privado", "contrasena": CLAVE})
    assert r.status_code == 201, r.text
    return {"Cookie": f"{NOMBRE_COOKIE}={r.cookies.get(NOMBRE_COOKIE)}", "Origin": origen, "X-CSRF-Token": r.json()["csrf_token"]}


def periodo(desde: int, hasta: int, **extra) -> dict:
    return {"desde": d(desde).isoformat(), "hasta": d(hasta).isoformat(), **extra}


def test_recorrido_real_con_la_generacion_desactivada_por_defecto(db, mundo2):
    with servidor({"INFORME_HABILITADO": "false", "INFORME_GENERADOR": "ninguno"}) as (base, origen):
        ana, supt = entrar(base, origen, "ana"), entrar(base, origen, "supt")
        assert httpx.post(f"{base}/informes/individuales", json=periodo(-10, 0), headers={"Origin": origen}).status_code == 401              # sin sesión
        for cabeceras, ruta, datos in ((ana, "individuales", periodo(-10, 0)), (supt, "consolidados", periodo(-30, 0))):
            r = httpx.post(f"{base}/informes/{ruta}", json=datos, headers=cabeceras)
            assert (r.status_code, r.json()["codigo"], r.json()["detalles"]) == (503, "INFORME_NO_GENERADO", [{"campo": "reintento", "reintento": False, "motivo": "no_aplicable"}])
        j = httpx.post(f"{base}/informes/individuales", json=periodo(-3, 2), headers=ana).json()                                              # sin datos: no hace falta generador
        assert (j["sin_datos"], j["base"], j["narrativa"], j["hechos"], j["agregaciones"]) == (True, DECLARACION_DE_BASE, None, [], None)


def test_recorrido_real_con_el_simulado_habilitado_expresamente(db, mundo2):
    with servidor({"INFORME_HABILITADO": "true", "INFORME_GENERADOR": "simulado"}) as (base, origen):
        ana, beto, supt = entrar(base, origen, "ana"), entrar(base, origen, "beto"), entrar(base, origen, "supt")
        # individual propio: 200 con el esquema público cerrado y las cifras deterministas
        r = httpx.post(f"{base}/informes/individuales", json=periodo(-10, 0), headers=ana)
        assert r.status_code == 200
        j = r.json()
        assert set(j) == {"tipo", "periodo", "generado_en", "base", "sin_datos", "persona", "agregaciones", "actividades", "hechos", "bloqueos", "narrativa"} and j["base"] == DECLARACION_DE_BASE
        directo = preparar_informe_individual(db, consultante_de(db, mundo2["ana"], hoy=H), None, d(-10), d(0))
        assert j["agregaciones"] == dataclasses.asdict(directo.agregaciones) and len(j["hechos"]) == 4 and [s["texto"][:3] for s in j["narrativa"]] == ["ana", "ana"]
        assert all(set(s) == {"texto"} for s in j["narrativa"])
        # consolidado: 200, una narrativa por persona y la sección de equipo determinista
        r = httpx.post(f"{base}/informes/consolidados", json=periodo(-30, 0), headers=supt)
        c = r.json()
        assert r.status_code == 200 and set(c) == {"tipo", "periodo", "generado_en", "base", "sin_datos", "personas", "agregaciones_del_equipo"}
        assert [p["persona"]["nombre"] for p in c["personas"]] == ["ana", "beto", "gina", "pablo", "supt"] and all(p["narrativa"] for p in c["personas"])
        equipo = preparar_informe_consolidado(db, consultante_de(db, mundo2["supt"], hoy=H), None, d(-30), d(0))
        assert c["agregaciones_del_equipo"] == dataclasses.asdict(equipo.agregaciones_del_equipo)
        # sin datos: 200, la declaración de base y ninguna llamada al generador (aquí, sin narrativa)
        j = httpx.post(f"{base}/informes/individuales", json=periodo(-3, 2), headers=ana).json()
        assert (j["sin_datos"], j["narrativa"], j["base"]) == (True, None, DECLARACION_DE_BASE)
        # sin datos sensibles en el JSON
        for texto in (json.dumps(j), json.dumps(c)):
            for sensible in ("acceso-", "-privado", CLAVE, "argon2", "@", "Equipo T-reservado", "resumen reservado"):
                assert sensible not in texto
        ids_de_actividades = {str(f[0]) for f in db.execute(text("select id from actividad")).all()}
        assert not set(UUID.findall(json.dumps(c))) & ids_de_actividades
        # compañero visible sin permiso: 403; persona invisible o inexistente: el mismo 404; colaborador en el consolidado: 403
        r = httpx.post(f"{base}/informes/individuales", json=periodo(-10, 0, persona_id=str(mundo2["ana"])), headers=beto)
        assert (r.status_code, r.json()["codigo"]) == (403, "OPERACION_NO_PERMITIDA")
        r1 = httpx.post(f"{base}/informes/individuales", json=periodo(-10, 0, persona_id=str(mundo2["celia"])), headers=supt)
        r2 = httpx.post(f"{base}/informes/individuales", json=periodo(-10, 0, persona_id="00000000-0000-4000-8000-000000000000"), headers=ana)
        assert (r1.status_code, r2.status_code, r1.json() == r2.json()) == (404, 404, True)
        assert httpx.post(f"{base}/informes/consolidados", json=periodo(-30, 0), headers=ana).json()["codigo"] == "OPERACION_NO_PERMITIDA"
        # límite de 31 días con ambos extremos
        r = httpx.post(f"{base}/informes/consolidados", json=periodo(-31, 0), headers=supt)
        assert (r.status_code, r.json()["codigo"], r.json()["detalles"][0]) == (422, "INFORME_EXCEDE_LIMITES", {"campo": "hasta", "motivo": "rango_excede_el_maximo", "maximo_dias": 31})
        # CSRF y origen, y campos desconocidos
        sin_csrf = {k: v for k, v in ana.items() if k != "X-CSRF-Token"}
        assert httpx.post(f"{base}/informes/individuales", json=periodo(-10, 0), headers=sin_csrf).json()["detalles"] == [{"campo": "X-CSRF-Token", "motivo": "csrf_invalido"}]
        assert httpx.post(f"{base}/informes/individuales", json=periodo(-10, 0), headers={**ana, "Origin": "https://otro-origen.invalid"}).json()["detalles"] == [{"campo": "Origin", "motivo": "origen_no_permitido"}]
        assert httpx.post(f"{base}/informes/individuales", json={**periodo(-10, 0), "otro": 1}, headers=ana).json()["codigo"] == "SOLICITUD_INVALIDA"
        # más de 400 hechos autorizados: 401 avances de una persona, sin truncar
        with get_owner_engine().begin() as conexion:
            b = _bitacora(conexion, mundo2["ana"], d(-1))
            a = _actividad(conexion, mundo2["ana"], b, "Tarea con muchos avances")
            conexion.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion, registrado_en) select :a, :b, 'En progreso', 'nota', clock_timestamp() from generate_series(1, 401)"),
                             {"a": a, "b": b})
        r = httpx.post(f"{base}/informes/individuales", json=periodo(-5, 0), headers=ana)
        assert (r.status_code, r.json()["codigo"], r.json()["detalles"][0]) == (422, "INFORME_EXCEDE_LIMITES", {"campo": "hechos", "motivo": "hechos_exceden_el_maximo", "maximo_hechos": 400})
        assert "nota" not in r.text and "401" not in r.text


def test_recorrido_real_con_una_salida_malformada_del_generador(db, mundo2):
    with servidor({"INFORME_HABILITADO": "true", "INFORME_GENERADOR": "simulado", "PRUEBA_MODO_GENERADOR": "campo_extra"}, "tests.app_informes_prueba:app") as (base, origen):
        for cabeceras, ruta, datos in ((entrar(base, origen, "ana"), "individuales", periodo(-10, 0)), (entrar(base, origen, "supt"), "consolidados", periodo(-30, 0))):
            r = httpx.post(f"{base}/informes/{ruta}", json=datos, headers=cabeceras)
            assert (r.status_code, r.json()) == (503, {"codigo": "INFORME_NO_GENERADO", "mensaje": "El informe no pudo generarse.", "detalles": [{"campo": "reintento", "reintento": False, "motivo": "no_aplicable"}]})
