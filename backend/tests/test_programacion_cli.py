"""M1-T4 — las órdenes de la CLI ``finalizar-pertenencia`` (M1-06) y ``cancelar-operacion-programada`` (M1-07) con PostgreSQL real.

Mismas garantías que las demás órdenes de provisión: la credencial nunca es un argumento ni aparece en la salida, la CLI se
niega a trabajar con un rol distinto del de provisión, una orden rechazada no deja nada y los errores inesperados no imprimen el
texto de la excepción. No hay ninguna ruta HTTP. Las pruebas destructivas corren solo sobre ``smartwork_test``.
"""

import json
import os
import subprocess
import sys
import uuid
from datetime import timedelta

import pytest

from app.db import get_engine, get_owner_engine
from app.provision import cli, programacion
from app.provision.cli import VARIABLE_CREDENCIAL
from tests.fabricas import hoy
from tests.test_provision_cli import CREDENCIAL, RAIZ, ejecutar, instalada, sin_secretos  # noqa: F401  (fixture `instalada`)
from tests.utiles_m2 import contar, filas

HOY = hoy()


def dia(n: int):
    return HOY + timedelta(days=n)


@pytest.fixture()
def mundo(instalada):
    """Con las órdenes reales de la CLI: equipo T (supervisor ST, colaboradores C1 y C2), equipo U (supervisor SU) y equipo X."""
    op = ["--operador", instalada["operador"]]
    ids = {}
    for nombre in ("T", "U", "X"):
        codigo, salida, error = ejecutar(["crear-equipo", *op, "--organizacion", str(instalada["org"]), "--nombre", nombre])
        assert codigo == 0, error
        ids[nombre] = json.loads(salida)["equipo_id"]
    for clave, equipo, rol in (("ST", "T", "supervisor"), ("C1", "T", "colaborador"), ("C2", "T", "colaborador"), ("SU", "U", "supervisor")):
        codigo, salida, error = ejecutar(["crear-persona", *op, "--nombre", clave, "--identificador-acceso", clave.lower(), "--equipo", ids[equipo],
                                          "--rol", rol, "--desde", HOY.isoformat()])
        assert codigo == 0, error
        ids[clave] = json.loads(salida)["persona_id"]
    return {"op": op, "ids": ids, "operador": instalada["operador"]}


def fin(m, persona, fecha):
    return f"{m['ids'][persona]}:{fecha.isoformat()}"


def cambio(m, persona, equipo, rol, fecha):
    return f"{m['ids'][persona]}:{m['ids'][equipo]}:{rol}:{fecha.isoformat()}"


def canc(m, persona, tipo, fecha):
    return f"{m['ids'][persona]}:{tipo}:{fecha.isoformat()}"


def finalizar(m, *finalizaciones, cambios=(), **kw):
    argv = ["finalizar-pertenencia", *m["op"]]
    for f in finalizaciones:
        argv += ["--finalizar", f]
    for c in cambios:
        argv += ["--cambio", c]
    return ejecutar(argv, **kw)


def cancelar(m, *cancelaciones, cambios=(), finalizaciones=(), **kw):
    argv = ["cancelar-operacion-programada", *m["op"]]
    for c in cancelaciones:
        argv += ["--cancelar", c]
    for c in cambios:
        argv += ["--cambio", c]
    for f in finalizaciones:
        argv += ["--finalizar", f]
    return ejecutar(argv, **kw)


def foto():
    return filas("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia order by id"), contar("auditoria")


def historia(m, persona):
    return filas("select e.nombre, p.rol, p.desde, p.hasta_exclusivo from pertenencia p join equipo e on e.id = p.equipo_id "
                 "where p.persona_id = :p order by p.desde", p=uuid.UUID(m["ids"][persona]))


# ==================================================== resultado ===========================================================

def test_finalizar_por_la_cli_devuelve_la_operacion_y_el_historial_completo_sin_secretos(mundo):
    codigo, salida, error = finalizar(mundo, fin(mundo, "C2", dia(3)))
    assert codigo == 0 and error == ""
    r = json.loads(salida)
    assert r["orden"] == "finalizar-pertenencia" and r["operacion"] == "finalizacion_pertenencia" and r["base"] == "smartwork_test"
    assert r["canceladas"] == [] and r["nuevas"] == [{"persona_id": mundo["ids"]["C2"], "tipo": "finalizacion", "fecha_efectiva": dia(3).isoformat()}]
    assert [(h["equipo"], h["rol"], h["desde"], h["hasta_exclusivo"]) for h in r["historiales"][0]["pertenencias"]] == [
        ("T", "colaborador", HOY.isoformat(), dia(3).isoformat())]
    sin_secretos(salida, error)
    assert salida.isascii() and '"c2"' not in salida.lower()


def test_el_relevo_de_un_supervisor_que_se_finaliza_son_una_finalizacion_y_un_cambio_en_una_sola_orden(mundo):
    antes = contar("auditoria")
    codigo, salida, error = finalizar(mundo, fin(mundo, "ST", dia(4)), cambios=[cambio(mundo, "C1", "T", "supervisor", dia(4))])
    assert codigo == 0, error
    r = json.loads(salida)
    assert {n["tipo"] for n in r["nuevas"]} == {"finalizacion", "cambio_de_rol"} and len(r["historiales"]) == 2
    assert contar("auditoria") == antes + 1
    assert historia(mundo, "ST") == [("T", "supervisor", HOY, dia(4))]


def test_cancelar_y_sustituir_por_la_cli(mundo):
    codigo, _, error = ejecutar(["registrar-traslado", *mundo["op"], "--cambio", cambio(mundo, "C1", "U", "colaborador", dia(3))])
    assert codigo == 0, error
    codigo, salida, error = cancelar(mundo, canc(mundo, "C1", "traslado", dia(3)))
    assert codigo == 0, error
    r = json.loads(salida)
    assert r["operacion"] == "cancelacion_operacion" and r["nuevas"] == [] and r["canceladas"] == [
        {"persona_id": mundo["ids"]["C1"], "tipo": "traslado", "fecha_efectiva": dia(3).isoformat()}]
    assert historia(mundo, "C1") == [("T", "colaborador", HOY, None)]

    ejecutar(["registrar-traslado", *mundo["op"], "--cambio", cambio(mundo, "C1", "U", "colaborador", dia(3))])
    codigo, salida, error = cancelar(mundo, canc(mundo, "C1", "traslado", dia(3)), cambios=[cambio(mundo, "C1", "X", "supervisor", dia(6))])
    assert codigo == 0, error
    r = json.loads(salida)
    assert r["operacion"] == "sustitucion_operacion" and r["nuevas"][0]["fecha_efectiva"] == dia(6).isoformat() and r["nuevas"][0]["equipo_id"] == mundo["ids"]["X"]
    assert historia(mundo, "C1") == [("T", "colaborador", HOY, dia(6)), ("X", "supervisor", dia(6), None)]
    sin_secretos(salida, error)


def test_se_sustituye_una_finalizacion_por_la_cli(mundo):
    assert finalizar(mundo, fin(mundo, "C2", dia(4)))[0] == 0
    codigo, salida, error = cancelar(mundo, canc(mundo, "C2", "finalizacion", dia(4)), finalizaciones=[fin(mundo, "C2", dia(8))])
    assert codigo == 0, error
    assert historia(mundo, "C2") == [("T", "colaborador", HOY, dia(8))]


def test_las_ordenes_rechazadas_devuelven_un_codigo_estable_y_no_dejan_nada(mundo):
    antes = foto()
    codigo, salida, error = finalizar(mundo, fin(mundo, "ST", dia(5)))                      # CA-240
    assert codigo == 2 and salida == "" and json.loads(error)["error"] == "PERTENENCIA_INVALIDA"
    assert json.loads(error)["detalles"][0]["motivo"] == "el_equipo_quedaria_sin_supervisor"
    codigo, _, error = finalizar(mundo, fin(mundo, "C2", HOY))                               # CA-258
    assert codigo == 2 and json.loads(error)["error"] == "FECHA_EFECTIVA_INVALIDA"
    codigo, _, error = cancelar(mundo, canc(mundo, "C1", "alta", HOY))                       # CA-245: ya efectiva
    assert codigo == 2 and json.loads(error)["error"] == "FECHA_EFECTIVA_INVALIDA"
    codigo, _, error = cancelar(mundo, canc(mundo, "C1", "traslado", dia(3)))
    assert codigo == 2 and json.loads(error)["error"] == "RECURSO_NO_DISPONIBLE"
    assert foto() == antes


def test_el_tipo_que_no_coincide_se_informa_con_el_tipo_real(mundo):
    ejecutar(["registrar-traslado", *mundo["op"], "--cambio", cambio(mundo, "C1", "U", "colaborador", dia(3))])
    codigo, _, error = cancelar(mundo, canc(mundo, "C1", "finalizacion", dia(3)))
    d = json.loads(error)
    assert codigo == 2 and d["error"] == "SOLICITUD_INVALIDA" and d["detalles"][0]["tipo_real"] == "traslado"


# ==================================================== argumentos ==========================================================

@pytest.mark.parametrize("valor", ["", "solo", "a:b:c", "no-uuid:2030-01-01", "{id}:31/12/2030", "{id}:2030-13-01", "{id}:mañana", "{id}:2030-01-01:de-mas"])
def test_una_finalizacion_mal_formada_se_rechaza_antes_de_tocar_la_base(mundo, valor):
    antes = foto()
    codigo, _, error = finalizar(mundo, valor.replace("{id}", mundo["ids"]["C2"]))
    assert codigo == 2 and json.loads(error)["error"] == "SOLICITUD_INVALIDA" and foto() == antes


@pytest.mark.parametrize("valor", ["", "a:b", "{id}:traslado", "{id}:traslado:31/12/2030", "no-uuid:traslado:2030-01-01", "{id}:traslado:2030-01-01:x"])
def test_una_cancelacion_mal_formada_se_rechaza_antes_de_tocar_la_base(mundo, valor):
    antes = foto()
    codigo, _, error = cancelar(mundo, valor.replace("{id}", mundo["ids"]["C1"]))
    assert codigo == 2 and json.loads(error)["error"] == "SOLICITUD_INVALIDA" and foto() == antes


def test_el_indice_de_la_entrada_mal_formada_se_informa(mundo):
    codigo, _, error = finalizar(mundo, fin(mundo, "C2", dia(3)), "mal")
    assert json.loads(error)["detalles"] == [{"campo": "finalizar", "indice": 1, "motivo": "formato"}]
    codigo, _, error = cancelar(mundo, canc(mundo, "C1", "traslado", dia(3)), "mal")
    assert json.loads(error)["detalles"] == [{"campo": "cancelar", "indice": 1, "motivo": "formato"}]


def test_sin_ninguna_finalizacion_o_cancelacion_la_cli_se_niega(mundo):
    assert ejecutar(["finalizar-pertenencia", *mundo["op"]])[0] == 2
    assert ejecutar(["cancelar-operacion-programada", *mundo["op"], "--cambio", cambio(mundo, "C1", "U", "colaborador", dia(3))])[0] == 2


def test_no_hay_opciones_para_fijar_la_fecha_actual_ni_para_pasar_la_credencial():
    ayuda = ""
    for nombre in ("finalizar-pertenencia", "cancelar-operacion-programada"):
        ayuda += cli._parser()._subparsers._group_actions[0].choices[nombre].format_help()
    for palabra in ("--hoy", "--fecha-actual", "--reloj", "--ahora", "--credencial", "--password", "--contrasena"):
        assert palabra not in ayuda


# ==================================================== autorización y conexión =============================================

def test_una_persona_operadora_desconocida_o_con_otra_credencial_no_ejecuta_nada(mundo):
    for operador, credencial in (("desconocida", CREDENCIAL), (mundo["operador"], "credencial-equivocada-123")):
        antes = foto()
        codigo, salida, error = ejecutar(["finalizar-pertenencia", "--operador", operador, "--finalizar", fin(mundo, "C2", dia(3))], credencial=credencial)
        assert codigo == 2 and json.loads(error)["error"] == "OPERADOR_NO_AUTORIZADO" and salida == "" and credencial not in error
        assert foto() == antes


@pytest.mark.parametrize("motor_nombre", ["aplicacion", "propietario"])
def test_la_cli_se_niega_a_trabajar_con_un_rol_que_no_es_el_de_provision(mundo, motor_nombre):
    antes = foto()
    motor = get_engine() if motor_nombre == "aplicacion" else get_owner_engine()
    codigo, salida, error = finalizar(mundo, fin(mundo, "C2", dia(3)), motor_provision=motor)
    assert codigo == 3 and json.loads(error)["error"] == "CONEXION_NO_PERMITIDA" and salida == ""
    codigo, _, error = cancelar(mundo, canc(mundo, "C1", "traslado", dia(3)), motor_provision=motor)
    assert codigo == 3 and foto() == antes


def test_un_error_inesperado_no_imprime_el_texto_de_la_excepcion(mundo, monkeypatch):
    def falla(*a, **k):
        raise RuntimeError(f"falló con la credencial {CREDENCIAL} y el hash $argon2id$secreto")
    monkeypatch.setattr(programacion, "finalizar_pertenencia", falla)
    monkeypatch.setattr(programacion, "cancelar_operacion_programada", falla)
    antes = foto()
    for resultado in (finalizar(mundo, fin(mundo, "C2", dia(3))), cancelar(mundo, canc(mundo, "C1", "traslado", dia(3)))):
        codigo, salida, error = resultado
        assert codigo == 1 and json.loads(error) == {"error": "ERROR_INTERNO", "tipo": "RuntimeError"} and salida == ""
        sin_secretos(salida, error)
    assert foto() == antes


def test_no_existe_ninguna_ruta_http_de_finalizacion_ni_de_cancelacion_de_pertenencias():
    """A2 y CA-26: son solo órdenes de la CLI del servidor; nadie con una sesión (supervisor incluido) las tiene."""
    from app.main import crear_app
    for ruta in crear_app().openapi()["paths"]:
        for palabra in ("finaliz", "cancel", "programad", "pertenencia", "provision", "operador"):
            assert palabra not in ruta, ruta


# ==================================================== el proceso real =====================================================

def _proceso(argv, entorno=None):
    return subprocess.run([sys.executable, "-m", "scripts.provision", *argv], cwd=RAIZ, env=entorno or {**os.environ, VARIABLE_CREDENCIAL: CREDENCIAL},
                          capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL, timeout=120)


def test_la_cli_finaliza_y_cancela_como_proceso_y_la_credencial_no_aparece_en_los_argumentos(mundo):
    argv = ["finalizar-pertenencia", "--operador", mundo["operador"], "--finalizar", fin(mundo, "C2", dia(4))]
    assert CREDENCIAL not in " ".join(argv)
    r = _proceso(argv)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["nuevas"][0]["tipo"] == "finalizacion" and r.stderr == ""
    sin_secretos(r.stdout, r.stderr)
    r = _proceso(["cancelar-operacion-programada", "--operador", mundo["operador"], "--cancelar", canc(mundo, "C2", "finalizacion", dia(4))])
    assert r.returncode == 0, r.stderr
    assert historia(mundo, "C2") == [("T", "colaborador", HOY, None)]
    sin_secretos(r.stdout, r.stderr)


def test_el_proceso_sin_credencial_ni_terminal_termina_con_error_y_sin_cambios(mundo):
    antes = foto()
    entorno = {k: v for k, v in os.environ.items() if k != VARIABLE_CREDENCIAL}
    r = _proceso(["finalizar-pertenencia", "--operador", mundo["operador"], "--finalizar", fin(mundo, "C2", dia(4))], entorno)
    assert r.returncode == 2 and json.loads(r.stderr)["error"] == "CREDENCIAL_NO_VALIDA" and foto() == antes
