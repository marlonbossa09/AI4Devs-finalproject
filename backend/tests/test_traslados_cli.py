"""M1-T3 — la orden de la CLI ``registrar-traslado`` (contrato M1-05) con PostgreSQL real.

Mismas garantías que las demás órdenes de provisión (M1-T2): la credencial nunca es un argumento ni aparece en la salida, la CLI
se niega a trabajar con un rol distinto del de provisión, una orden rechazada no deja nada y los errores inesperados no
imprimen el texto de la excepción. No hay ninguna ruta HTTP de traslado (A2). Las pruebas destructivas corren solo sobre
``smartwork_test``.
"""

import json
import os
import subprocess
import sys
import uuid
from datetime import timedelta

import pytest

from app.db import get_engine, get_owner_engine
from app.provision import cli, servicio
from app.provision.cli import VARIABLE_CREDENCIAL
from tests.fabricas import hoy
from tests.test_provision_cli import CREDENCIAL, RAIZ, ejecutar, instalada, sin_secretos  # noqa: F401  (fixture `instalada`)
from tests.utiles_m2 import contar, filas

HOY = hoy()


def dia(n: int):
    return HOY + timedelta(days=n)


@pytest.fixture()
def mundo(instalada):
    """Con las órdenes reales de la CLI: equipo T (supervisor ST, colaborador C1) y equipo U (supervisor SU)."""
    op = ["--operador", instalada["operador"]]
    ids = {}
    for nombre in ("T", "U", "X"):
        codigo, salida, error = ejecutar(["crear-equipo", *op, "--organizacion", str(instalada["org"]), "--nombre", nombre])
        assert codigo == 0, error
        ids[nombre] = json.loads(salida)["equipo_id"]
    for clave, equipo, rol in (("ST", "T", "supervisor"), ("C1", "T", "colaborador"), ("SU", "U", "supervisor")):
        codigo, salida, error = ejecutar(["crear-persona", *op, "--nombre", clave, "--identificador-acceso", clave.lower(), "--equipo", ids[equipo],
                                          "--rol", rol, "--desde", HOY.isoformat()])
        assert codigo == 0, error
        ids[clave] = json.loads(salida)["persona_id"]
    return {"op": op, "ids": ids, "operador": instalada["operador"]}


def pedido(mundo, persona, equipo, rol, fecha):
    return f"{mundo['ids'][persona]}:{mundo['ids'][equipo]}:{rol}:{fecha.isoformat()}"


def trasladar(mundo, *cambios, **kw):
    argv = ["registrar-traslado", *mundo["op"]]
    for c in cambios:
        argv += ["--cambio", c]
    return ejecutar(argv, **kw)


def foto():
    return filas("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia order by id"), contar("auditoria")


# ==================================================== resultado ===========================================================

def test_un_traslado_por_la_cli_devuelve_el_historial_completo_y_ningun_secreto(mundo):
    codigo, salida, error = trasladar(mundo, pedido(mundo, "C1", "U", "colaborador", dia(3)))
    assert codigo == 0 and error == ""
    r = json.loads(salida)
    assert r["orden"] == "registrar-traslado" and r["base"] == "smartwork_test" and "invocacion" in r and "operador_id" in r
    assert r["cambios"] == [{"persona_id": mundo["ids"]["C1"], "tipo": "traslado", "equipo_anterior_id": mundo["ids"]["T"], "rol_anterior": "colaborador",
                             "equipo_id": mundo["ids"]["U"], "rol": "colaborador", "fecha_efectiva": dia(3).isoformat()}]
    historial = r["historiales"][0]
    assert historial["persona_id"] == mundo["ids"]["C1"]
    assert [(h["equipo"], h["rol"], h["desde"], h["hasta_exclusivo"]) for h in historial["pertenencias"]] == [
        ("T", "colaborador", HOY.isoformat(), dia(3).isoformat()), ("U", "colaborador", dia(3).isoformat(), None)]
    sin_secretos(salida, error)
    assert salida.isascii() and '"c1"' not in salida.lower()                # JSON ASCII; sin el identificador de acceso de la persona


def test_un_relevo_son_dos_cambios_en_una_sola_orden_y_una_sola_entrada_de_auditoria(mundo):
    antes = contar("auditoria")
    codigo, salida, error = trasladar(mundo, pedido(mundo, "ST", "X", "supervisor", dia(5)), pedido(mundo, "C1", "T", "supervisor", dia(5)))
    assert codigo == 0, error
    r = json.loads(salida)
    assert {c["tipo"] for c in r["cambios"]} == {"traslado", "cambio_de_rol"} and len(r["historiales"]) == 2
    assert contar("auditoria") == antes + 1
    entradas = filas("select referencia_provision, operacion from auditoria where operacion = 'cambio_pertenencia'")
    assert len(entradas) == 1 and entradas[0][0].startswith(f"operador:{mundo['operador']}|invocacion:{r['invocacion']}")


def test_la_orden_rechazada_devuelve_un_codigo_estable_y_no_deja_nada(mundo):
    antes = foto()
    codigo, salida, error = trasladar(mundo, pedido(mundo, "ST", "X", "supervisor", dia(5)))              # T quedaría sin supervisor
    assert codigo == 2 and salida == "" and json.loads(error)["error"] == "PERTENENCIA_INVALIDA"
    codigo, _, error = trasladar(mundo, pedido(mundo, "C1", "U", "colaborador", HOY))                       # hoy: no es futura
    assert codigo == 2 and json.loads(error)["error"] == "FECHA_EFECTIVA_INVALIDA"
    assert foto() == antes


# ==================================================== argumentos ==========================================================

@pytest.mark.parametrize("cambio", ["", "solo-una-parte", "a:b:c", "a:b:c:d:e", "no-uuid:no-uuid:colaborador:2030-01-01"])
def test_un_cambio_mal_formado_se_rechaza_antes_de_tocar_la_base(mundo, cambio):
    antes = foto()
    codigo, _, error = trasladar(mundo, cambio)
    assert codigo == 2 and json.loads(error)["error"] == "SOLICITUD_INVALIDA"
    assert foto() == antes


def test_una_fecha_con_otro_formato_se_rechaza(mundo):
    for fecha in ("31/12/2030", "2030-13-01", "mañana"):
        codigo, _, error = trasladar(mundo, f"{mundo['ids']['C1']}:{mundo['ids']['U']}:colaborador:{fecha}")
        assert codigo == 2 and json.loads(error)["error"] == "SOLICITUD_INVALIDA"


def test_el_indice_del_cambio_mal_formado_se_informa(mundo):
    codigo, _, error = trasladar(mundo, pedido(mundo, "C1", "U", "colaborador", dia(3)), "mal")
    assert json.loads(error)["detalles"] == [{"campo": "cambio", "indice": 1, "motivo": "formato"}]


def test_sin_ningun_cambio_la_cli_se_niega(mundo):
    codigo, salida, error = ejecutar(["registrar-traslado", *mundo["op"]])
    assert codigo == 2 and salida == ""


def test_no_existe_ninguna_opcion_para_fijar_la_fecha_actual_en_el_traslado():
    ayuda = cli._parser()._subparsers._group_actions[0].choices["registrar-traslado"].format_help()
    for palabra in ("--hoy", "--fecha-actual", "--reloj", "--ahora", "--credencial"):
        assert palabra not in ayuda


# ==================================================== autorización y conexión =============================================

def test_una_persona_operadora_desconocida_o_con_otra_credencial_no_traslada_nada(mundo):
    for operador, credencial in (("desconocida", CREDENCIAL), (mundo["operador"], "credencial-equivocada-123")):
        antes = foto()
        codigo, salida, error = ejecutar(["registrar-traslado", "--operador", operador, "--cambio", pedido(mundo, "C1", "U", "colaborador", dia(3))],
                                         credencial=credencial)
        assert codigo == 2 and json.loads(error)["error"] == "OPERADOR_NO_AUTORIZADO" and salida == "" and credencial not in error
        assert foto() == antes


@pytest.mark.parametrize("motor_nombre", ["aplicacion", "propietario"])
def test_la_cli_se_niega_a_trasladar_con_un_rol_que_no_es_el_de_provision(mundo, motor_nombre):
    antes = foto()
    motor = get_engine() if motor_nombre == "aplicacion" else get_owner_engine()
    codigo, salida, error = trasladar(mundo, pedido(mundo, "C1", "U", "colaborador", dia(3)), motor_provision=motor)
    assert codigo == 3 and json.loads(error)["error"] == "CONEXION_NO_PERMITIDA" and salida == ""
    assert foto() == antes


def test_un_error_inesperado_no_imprime_el_texto_de_la_excepcion(mundo, monkeypatch):
    def falla(*a, **k):
        raise RuntimeError(f"falló con la credencial {CREDENCIAL} y el hash $argon2id$secreto")
    monkeypatch.setattr(servicio, "registrar_traslado", falla)
    antes = foto()
    codigo, salida, error = trasladar(mundo, pedido(mundo, "C1", "U", "colaborador", dia(3)))
    assert codigo == 1 and json.loads(error) == {"error": "ERROR_INTERNO", "tipo": "RuntimeError"} and salida == ""
    sin_secretos(salida, error)
    assert foto() == antes


def test_no_existe_ninguna_ruta_http_de_traslado_ni_de_cambio_de_rol():
    """A2 y CA-26: el traslado es solo la orden de la CLI del servidor; nadie con una sesión (supervisor incluido) la tiene."""
    from app.main import crear_app
    for ruta in crear_app().openapi()["paths"]:
        for palabra in ("traslado", "pertenencia", "cambio", "rol", "provision", "operador"):
            assert palabra not in ruta, ruta


# ==================================================== el proceso real =====================================================

def test_la_cli_traslada_como_proceso_y_la_credencial_no_aparece_en_los_argumentos(mundo):
    entorno = {**os.environ, VARIABLE_CREDENCIAL: CREDENCIAL}
    argv = [sys.executable, "-m", "scripts.provision", "registrar-traslado", "--operador", mundo["operador"],
            "--cambio", pedido(mundo, "C1", "U", "colaborador", dia(4))]
    assert CREDENCIAL not in " ".join(argv)
    r = subprocess.run(argv, cwd=RAIZ, env=entorno, capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL, timeout=120)
    assert r.returncode == 0, r.stderr
    salida = json.loads(r.stdout)
    assert salida["cambios"][0]["tipo"] == "traslado" and r.stderr == ""
    sin_secretos(r.stdout, r.stderr)
    assert filas("select hasta_exclusivo from pertenencia where persona_id = :p order by desde", p=uuid.UUID(mundo["ids"]["C1"])) == [(dia(4),), (None,)]


def test_el_proceso_sin_credencial_ni_terminal_termina_con_error_y_sin_cambios(mundo):
    entorno = {k: v for k, v in os.environ.items() if k != VARIABLE_CREDENCIAL}
    antes = foto()
    r = subprocess.run([sys.executable, "-m", "scripts.provision", "registrar-traslado", "--operador", mundo["operador"],
                        "--cambio", pedido(mundo, "C1", "U", "colaborador", dia(4))],
                       cwd=RAIZ, env=entorno, capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL, timeout=120)
    assert r.returncode == 2 and json.loads(r.stderr)["error"] == "CREDENCIAL_NO_VALIDA" and foto() == antes
