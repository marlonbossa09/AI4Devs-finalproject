"""M1-T2 — la CLI de provisión del servidor (A2: sin endpoints HTTP) con PostgreSQL real.

Seguridad comprobada: la credencial nunca es un argumento ni aparece en la salida; la CLI se niega a trabajar con un rol que
no sea el de provisión; las órdenes rechazadas no dejan nada; los errores no muestran el texto de una excepción. Las
pruebas destructivas corren solo sobre ``smartwork_test``.
"""

import io
import json
import os
import subprocess
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from app.db import get_engine, get_owner_engine, get_provision_engine
from app.provision import cli, servicio
from app.provision.cli import VARIABLE_CREDENCIAL, main
from tests.fabricas import crear_organizacion, hoy
from tests.utiles_http import API
from tests.utiles_m2 import contar, filas

CREDENCIAL = "credencial-cli-de-prueba-123"
RAIZ = Path(__file__).resolve().parent.parent
HOY = hoy()


def ejecutar(argv, *, credencial=CREDENCIAL, motor_provision=None, motor_propietario=None, **extra):
    salida, error = io.StringIO(), io.StringIO()
    entorno = {VARIABLE_CREDENCIAL: credencial} if credencial is not None else {}
    codigo = main(argv, entorno=entorno, interactivo=False, salida=salida, error=error,
                  motor_provision=motor_provision or get_provision_engine(), motor_propietario=motor_propietario or get_owner_engine(), **extra)
    return codigo, salida.getvalue(), error.getvalue()


@pytest.fixture()
def instalada():
    """Primera persona operadora creada con el procedimiento de instalación (rol propietario) y una organización."""
    codigo, salida, error = ejecutar(["crear-primer-operador", "--identificador", "Operadora.Cli"])
    assert codigo == 0, error
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c)
    return {"org": org, "operador": "operadora.cli", "bootstrap": json.loads(salida)}


def sin_secretos(*textos):
    for t in textos:
        assert CREDENCIAL not in t and "argon2" not in t.lower()


# ==================================================== instalación =========================================================

def test_la_instalacion_crea_la_primera_persona_operadora_y_no_imprime_la_credencial():
    codigo, salida, error = ejecutar(["crear-primer-operador", "--identificador", "Operadora.Cli"])
    assert codigo == 0 and error == ""
    resultado = json.loads(salida)
    assert resultado["identificador"] == "operadora.cli" and resultado["orden"] == "crear-primer-operador"
    assert filas("select identificador, estado from operador") == [("operadora.cli", "activo")]
    sin_secretos(salida, error)


def test_la_instalacion_se_niega_si_ya_existe_una_persona_operadora(instalada):
    codigo, salida, error = ejecutar(["crear-primer-operador", "--identificador", "otra"])
    assert codigo == 2 and json.loads(error)["error"] == "INSTALACION_YA_REALIZADA" and contar("operador") == 1


def test_la_instalacion_exige_una_credencial_valida_y_que_se_repita_en_una_terminal():
    codigo, _, error = ejecutar(["crear-primer-operador", "--identificador", "op"], credencial="corta")
    assert codigo == 2 and json.loads(error)["error"] == "CREDENCIAL_NO_VALIDA" and contar("operador") == 0
    respuestas = iter([CREDENCIAL, "otra-distinta-123"])      # no coinciden
    salida, err = io.StringIO(), io.StringIO()
    codigo = main(["crear-primer-operador", "--identificador", "op"], entorno={}, interactivo=True, pedir=lambda _: next(respuestas),
                  salida=salida, error=err, motor_propietario=get_owner_engine())
    assert codigo == 2 and json.loads(err.getvalue())["error"] == "CREDENCIAL_NO_VALIDA" and contar("operador") == 0


def test_la_credencial_se_puede_pedir_sin_eco_en_una_terminal():
    respuestas = iter([CREDENCIAL, CREDENCIAL])
    salida, err = io.StringIO(), io.StringIO()
    codigo = main(["crear-primer-operador", "--identificador", "op"], entorno={}, interactivo=True, pedir=lambda _: next(respuestas),
                  salida=salida, error=err, motor_propietario=get_owner_engine())
    assert codigo == 0 and contar("operador") == 1
    sin_secretos(salida.getvalue(), err.getvalue())


def test_sin_credencial_ni_terminal_la_cli_se_niega():
    codigo, _, error = ejecutar(["crear-primer-operador", "--identificador", "op"], credencial=None)
    assert codigo == 2 and json.loads(error)["error"] == "CREDENCIAL_NO_VALIDA" and contar("operador") == 0


def test_la_instalacion_solo_acepta_el_rol_propietario(instalada):
    for motor in (get_engine(), get_provision_engine()):
        codigo, _, error = ejecutar(["crear-primer-operador", "--identificador", "otra"], motor_propietario=motor)
        assert codigo == 3 and json.loads(error)["error"] == "CONEXION_NO_PERMITIDA"
    assert contar("operador") == 1


# ==================================================== órdenes =============================================================

def test_crear_equipo_y_persona_por_la_cli_con_resultado_seguro(instalada):
    base = ["--operador", instalada["operador"]]
    codigo, salida, error = ejecutar(["crear-equipo", *base, "--organizacion", str(instalada["org"]), "--nombre", "Contabilidad"])
    assert codigo == 0 and error == ""
    equipo = json.loads(salida)
    assert equipo["nombre"] == "Contabilidad" and equipo["base"] == "smartwork_test" and "invocacion" in equipo
    sin_secretos(salida, error)

    codigo, salida, error = ejecutar(["crear-persona", *base, "--nombre", "Sofía", "--identificador-acceso", "Sofia", "--equipo", equipo["equipo_id"],
                                      "--rol", "supervisor", "--desde", HOY.isoformat()])
    assert codigo == 0 and error == ""
    persona = json.loads(salida)
    assert persona["rol"] == "supervisor" and persona["sin_contrasena"] is True and persona["desde"] == HOY.isoformat()
    sin_secretos(salida, error)
    assert "sofia" not in salida.lower().replace("sofía", "")      # el identificador de acceso no se devuelve
    assert contar("equipo") == 1 and contar("persona") == 1 and contar("pertenencia") == 1
    entradas = filas("select referencia_provision, tipo_objeto from auditoria where tipo_autor = 'provision' and tipo_objeto in ('equipo', 'persona') order by momento")
    assert [e[1] for e in entradas] == ["equipo", "persona"]
    assert all(e[0].startswith("operador:operadora.cli|invocacion:") for e in entradas)    # IR-34


def test_una_persona_operadora_desconocida_o_con_otra_credencial_no_ejecuta_nada(instalada):
    for operador, credencial in (("desconocida", CREDENCIAL), (instalada["operador"], "credencial-equivocada-123")):
        antes = contar("equipo"), contar("auditoria")
        codigo, salida, error = ejecutar(["crear-equipo", "--operador", operador, "--organizacion", str(instalada["org"]), "--nombre", "X"],
                                         credencial=credencial)
        assert codigo == 2 and json.loads(error)["error"] == "OPERADOR_NO_AUTORIZADO" and salida == ""
        assert (contar("equipo"), contar("auditoria")) == antes
        sin_secretos(salida, error)
        assert credencial not in error


def test_una_orden_rechazada_devuelve_un_codigo_estable_y_no_deja_nada(instalada):
    base = ["--operador", instalada["operador"]]
    antes = {t: contar(t) for t in ("equipo", "persona", "pertenencia", "identidad", "auditoria")}
    codigo, _, error = ejecutar(["crear-persona", *base, "--nombre", "C", "--identificador-acceso", "c", "--equipo", str(uuid.uuid4()),
                                 "--rol", "colaborador", "--desde", HOY.isoformat()])
    assert codigo == 2 and json.loads(error)["error"] == "RECURSO_NO_DISPONIBLE"
    codigo, _, error = ejecutar(["crear-equipo", *base, "--organizacion", str(instalada["org"]), "--nombre", "  "])
    assert codigo == 2 and json.loads(error)["error"] == "CAMPO_OBLIGATORIO"
    assert {t: contar(t) for t in antes} == antes


def test_los_argumentos_mal_formados_se_rechazan_antes_de_tocar_la_base(instalada):
    base = ["--operador", instalada["operador"]]
    for argv in (["crear-equipo", *base, "--organizacion", "no-es-un-uuid", "--nombre", "X"],
                 ["crear-persona", *base, "--nombre", "C", "--identificador-acceso", "c", "--equipo", str(uuid.uuid4()), "--rol", "supervisor", "--desde", "31/12/2026"]):
        codigo, _, error = ejecutar(argv)
        assert codigo == 2 and json.loads(error)["error"] == "SOLICITUD_INVALIDA"
    assert contar("equipo") == 0


def test_la_credencial_no_se_acepta_como_argumento(instalada):
    """Un argumento se vería en la lista de procesos y en el historial: la CLI no lo admite."""
    codigo, salida, error = ejecutar(["crear-equipo", "--operador", instalada["operador"], "--organizacion", str(instalada["org"]),
                                      "--nombre", "X", "--credencial", CREDENCIAL])
    assert codigo == 2 and contar("equipo") == 0
    assert "--credencial" not in {a for a in cli._parser().format_help().split() if a.startswith("--credencial")}


def test_no_existe_ninguna_opcion_para_fijar_la_fecha_actual(instalada):
    ayuda = cli._parser().format_help() + "".join(a.format_help() for a in cli._parser()._subparsers._group_actions[0].choices.values())
    for palabra in ("--hoy", "--fecha-actual", "--reloj", "--ahora"):
        assert palabra not in ayuda


# ==================================================== conexión y rol ======================================================

@pytest.mark.parametrize("motor_nombre", ["aplicacion", "propietario"])
def test_la_cli_se_niega_a_provisionar_con_un_rol_que_no_es_el_de_provision(instalada, motor_nombre):
    motor = get_engine() if motor_nombre == "aplicacion" else get_owner_engine()
    antes = contar("equipo"), contar("auditoria")
    codigo, salida, error = ejecutar(["crear-equipo", "--operador", instalada["operador"], "--organizacion", str(instalada["org"]), "--nombre", "X"],
                                     motor_provision=motor)
    assert codigo == 3 and json.loads(error)["error"] == "CONEXION_NO_PERMITIDA" and salida == ""
    assert (contar("equipo"), contar("auditoria")) == antes


# ==================================================== errores inesperados: sin fugas ======================================

def test_un_error_inesperado_no_imprime_el_texto_de_la_excepcion(instalada, monkeypatch):
    def falla(*a, **k):
        raise RuntimeError(f"falló con la credencial {CREDENCIAL} y el hash $argon2id$secreto")
    monkeypatch.setattr(servicio, "crear_equipo", falla)
    codigo, salida, error = ejecutar(["crear-equipo", "--operador", instalada["operador"], "--organizacion", str(instalada["org"]), "--nombre", "X"])
    assert codigo == 1 and json.loads(error) == {"error": "ERROR_INTERNO", "tipo": "RuntimeError"} and salida == ""
    sin_secretos(salida, error)
    assert contar("equipo") == 0


def test_los_errores_de_la_base_no_filtran_valores(instalada, monkeypatch):
    from sqlalchemy.exc import IntegrityError
    def falla(*a, **k):
        raise IntegrityError("insert into operador ... VALUES ('x', '$argon2id$v=19$m=19456')", {"h": "$argon2id$secreto"}, Exception("x"))
    monkeypatch.setattr(servicio, "crear_equipo", falla)
    codigo, salida, error = ejecutar(["crear-equipo", "--operador", instalada["operador"], "--organizacion", str(instalada["org"]), "--nombre", "X"])
    assert codigo == 1 and "argon2" not in error and "VALUES" not in error


# ==================================================== el proceso real =====================================================

def test_la_cli_funciona_como_proceso_y_la_credencial_no_aparece_en_los_argumentos(instalada):
    """Se ejecuta ``python -m scripts.provision`` de verdad, con la credencial solo en el entorno del proceso."""
    entorno = {**os.environ, VARIABLE_CREDENCIAL: CREDENCIAL}
    argv = [sys.executable, "-m", "scripts.provision", "crear-equipo", "--operador", instalada["operador"],
            "--organizacion", str(instalada["org"]), "--nombre", "Desde proceso"]
    assert CREDENCIAL not in " ".join(argv)
    r = subprocess.run(argv, cwd=RAIZ, env=entorno, capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL, timeout=120)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["nombre"] == "Desde proceso" and r.stderr == ""
    sin_secretos(r.stdout, r.stderr)
    assert filas("select nombre from equipo") == [("Desde proceso",)]


def test_el_proceso_sin_credencial_ni_terminal_termina_con_error_y_sin_cambios(instalada):
    entorno = {k: v for k, v in os.environ.items() if k != VARIABLE_CREDENCIAL}
    r = subprocess.run([sys.executable, "-m", "scripts.provision", "crear-equipo", "--operador", instalada["operador"],
                        "--organizacion", str(instalada["org"]), "--nombre", "X"],
                       cwd=RAIZ, env=entorno, capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL, timeout=120)
    assert r.returncode == 2 and json.loads(r.stderr)["error"] == "CREDENCIAL_NO_VALIDA" and contar("equipo") == 0


# ==================================================== herramientas de desarrollo ==========================================

def test_las_herramientas_locales_siguen_existiendo_y_estan_identificadas_como_de_desarrollo():
    for nombre in ("seed_dev.py", "crear_cuentas.py"):
        cabecera = (RAIZ / "scripts" / nombre).read_text(encoding="utf-8")[:1500]
        assert "HERRAMIENTA DE DESARROLLO" in cabecera and "scripts/provision.py" in cabecera


def test_no_existe_ningun_endpoint_http_de_provision():
    """A2: la provisión es solo la CLI del servidor. Ninguna ruta de la API crea equipos, personas, pertenencias ni
    personas operadoras, así que ningún supervisor (ni nadie con una sesión) dispone de esa función (CA-26)."""
    from app.main import crear_app
    # Las únicas excepciones son las rutas de LECTURA de M4 (solo ``GET``; lecturas de registros, no provisión). Se añaden aquí a medida que M4 las implementa.
    lecturas_de_m4 = {"/api/v1/personas/{persona_id}/bitacoras/{fecha_laboral}"}                                                     # M4-01 (M4-T1)
    rutas = crear_app().openapi()["paths"]
    for ruta, metodos in rutas.items():
        if ruta in lecturas_de_m4:
            assert set(metodos) == {"get"}, ruta
            continue
        for palabra in ("provision", "operador", "equipo", "persona", "pertenencia", "organizacion"):
            assert palabra not in ruta, ruta
