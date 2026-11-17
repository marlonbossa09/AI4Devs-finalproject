"""M1-T6 — la orden de la CLI ``desactivar-acceso`` (contrato M1-08) con PostgreSQL real.

Mismas garantías que las demás órdenes de provisión: la credencial de la persona operadora nunca es un argumento ni aparece en la
salida, la CLI se niega a trabajar con un rol distinto del de provisión, una orden rechazada no deja nada y los errores inesperados no
imprimen el texto de la excepción. No existe ninguna ruta HTTP de desactivación (A2). Las pruebas destructivas corren solo sobre
``smartwork_test``.
"""

import json
import os
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import text

from app.db import get_engine, get_owner_engine
from app.provision import acceso, cli
from app.provision.cli import VARIABLE_CREDENCIAL
from tests.fabricas import hoy
from tests.test_provision_cli import CREDENCIAL, RAIZ, ejecutar, instalada, sin_secretos  # noqa: F401  (fixture ``instalada``)
from tests.utiles_m2 import contar, filas

HOY = hoy()
MOTIVO = "Fin de la relación laboral"


@pytest.fixture()
def mundo(instalada):
    """Con las órdenes reales de la CLI: equipo T (supervisor ST, colaborador C1), equipo U (supervisor SU) y una sesión de C1."""
    op = ["--operador", instalada["operador"]]
    ids = {}
    for nombre in ("T", "U"):
        codigo, salida, error = ejecutar(["crear-equipo", *op, "--organizacion", str(instalada["org"]), "--nombre", nombre])
        assert codigo == 0, error
        ids[nombre] = json.loads(salida)["equipo_id"]
    for clave, equipo, rol in (("ST", "T", "supervisor"), ("C1", "T", "colaborador"), ("SU", "U", "supervisor")):
        codigo, salida, error = ejecutar(["crear-persona", *op, "--nombre", clave, "--identificador-acceso", f"{clave.lower()}.cli", "--equipo", ids[equipo],
                                          "--rol", rol, "--desde", HOY.isoformat()])
        assert codigo == 0, error
        ids[clave] = json.loads(salida)["persona_id"]
    with get_owner_engine().begin() as c:
        identidad = c.execute(text("select id from identidad where persona_id = :p"), {"p": ids["C1"]}).scalar_one()
        c.execute(text("insert into sesion (identidad_id, secreto_hash, caduca_absoluta_en) values (:i, 'secreto-de-c1', now() + interval '1 hour')"), {"i": identidad})
    return {"op": op, "ids": ids, "operador": instalada["operador"]}


def desactivar(mundo, clave, motivo=MOTIVO, **kw):
    return ejecutar(["desactivar-acceso", *mundo["op"], "--persona", mundo["ids"][clave], "--motivo", motivo], **kw)


def foto():
    return (filas("select id, acceso_desactivado_en from persona order by id"), filas("select id, revocada_en from sesion order by id"),
            filas("select * from pertenencia order by id"), contar("auditoria"))


# ==================================================== resultado ===========================================================

def test_desactivar_por_la_cli_devuelve_el_resultado_y_ningun_secreto(mundo):
    codigo, salida, error = desactivar(mundo, "C1")
    assert codigo == 0 and error == ""
    r = json.loads(salida)
    assert r["orden"] == "desactivar-acceso" and r["persona_id"] == mundo["ids"]["C1"] and r["sesiones_revocadas"] == 1 and r["advertencias"] == []
    assert r["base"] == "smartwork_test" and "invocacion" in r and "operador_id" in r and r["acceso_desactivado_en"]
    sin_secretos(salida, error)
    # La salida es JSON ASCII (los acentos van escapados): se comprueba también la forma escapada del motivo, y que no exista el campo.
    assert salida.isascii() and MOTIVO not in salida and json.dumps(MOTIVO)[1:-1] not in salida and "motivo" not in r
    assert "secreto-de-c1" not in salida                                                        # no se muestra nada de la sesión
    assert filas("select acceso_desactivado_en is not null from persona where id = :p", p=uuid.UUID(mundo["ids"]["C1"])) == [(True,)]
    assert filas("select count(*) from sesion where revocada_en is null") == [(0,)]


def test_dm09_la_advertencia_de_supervision_se_muestra_en_la_salida_de_la_cli(mundo):
    codigo, salida, error = desactivar(mundo, "ST")
    assert codigo == 0 and error == ""                                                         # la orden se aplica: no se bloquea (DD-04)
    r = json.loads(salida)
    assert r["advertencias"] == [{"codigo": "EQUIPO_PENDIENTE_DE_SUPERVISION_EFECTIVA", "equipo_id": mundo["ids"]["T"], "equipo": "T", "colaboradores": 1,
                                  "supervisor_id": mundo["ids"]["ST"], "supervisor_hasta_exclusivo": None}]
    auditada = filas("select valor_nuevo from auditoria where operacion = 'desactivacion_acceso'")[0][0]
    assert auditada["advertencias"] == r["advertencias"]                                       # el mismo resultado queda en la auditoría
    assert filas("select rol, hasta_exclusivo from pertenencia where persona_id = :p", p=uuid.UUID(mundo["ids"]["ST"])) == [("supervisor", None)]   # y no se tocó nada


@pytest.mark.parametrize("persona", ["C1", "SU"])
def test_sin_equipo_pendiente_la_lista_de_advertencias_va_vacia(mundo, persona):
    """C1 es colaborador; SU supervisa U, que no tiene colaboradores (equipo en provisión, IR-32): ninguno deja a un equipo pendiente."""
    assert json.loads(desactivar(mundo, persona)[1])["advertencias"] == []


# ==================================================== evento técnico de revocación (M1-T7, A11) ============================

def test_la_revocacion_de_sesiones_deja_un_evento_tecnico_sin_el_motivo(mundo):
    """Misma transacción que la desactivación; separado de la auditoría funcional; sin motivo ni secretos."""
    r = json.loads(desactivar(mundo, "C1")[1])
    (evento,) = filas("select tipo, ambito, persona_id, sesion_id, clave_cuenta, clave_origen, detalle from evento_autenticacion where ambito = 'persona'")
    assert evento == ("revocacion_por_desactivacion", "persona", uuid.UUID(mundo["ids"]["C1"]), None, None, None,
                      {"sesiones_revocadas": 1, "invocacion": r["invocacion"]})
    assert MOTIVO not in json.dumps(evento[6]) and "secreto-de-c1" not in json.dumps(evento[6])


def test_sin_sesiones_que_revocar_no_se_registra_ningun_evento_de_revocacion(mundo):
    assert json.loads(desactivar(mundo, "ST")[1])["sesiones_revocadas"] == 0
    assert filas("select count(*) from evento_autenticacion where ambito = 'persona'") == [(0,)]      # (la identificación de la persona operadora deja el suyo)


def test_la_auditoria_registra_siempre_la_operacion_efectiva_y_el_evento_solo_si_habia_sesiones_que_revocar(mundo):
    """Interpretación 6 (2026-11-17): la auditoría funcional siempre deja la entrada; el evento técnico solo cuenta sesiones realmente revocadas."""
    with get_owner_engine().begin() as c:                         # la única sesión de C1 ya estaba revocada: no hay nada que revocar
        c.execute(text("update sesion set revocada_en = now() - interval '1 hour'"))
    r = json.loads(desactivar(mundo, "C1")[1])
    assert r["sesiones_revocadas"] == 0
    (auditada,) = filas("select valor_nuevo, motivo from auditoria where operacion = 'desactivacion_acceso'")
    assert auditada[0]["sesiones_revocadas"] == 0 and auditada[1] == MOTIVO                         # la operación efectiva queda auditada
    assert filas("select count(*) from evento_autenticacion where tipo = 'revocacion_por_desactivacion'") == [(0,)]   # y no se inventa una revocación


def test_el_evento_de_revocacion_cuenta_las_sesiones_reales_y_no_guarda_identificadores_ni_secretos(mundo):
    with get_owner_engine().begin() as c:                         # dos sesiones vigentes y una ya revocada de C1
        identidad = c.execute(text("select id from identidad where persona_id = :p"), {"p": mundo["ids"]["C1"]}).scalar_one()
        for secreto in ("segundo-secreto-de-c1", "tercer-secreto-de-c1"):
            c.execute(text("insert into sesion (identidad_id, secreto_hash, caduca_absoluta_en) values (:i, :h, now() + interval '1 hour')"), {"i": identidad, "h": secreto})
        c.execute(text("update sesion set revocada_en = now() - interval '1 hour' where secreto_hash = 'tercer-secreto-de-c1'"))
    r = json.loads(desactivar(mundo, "C1")[1])
    assert r["sesiones_revocadas"] == 2                           # solo las que seguían vigentes
    (evento,) = filas("select detalle, sesion_id, clave_cuenta, clave_origen from evento_autenticacion where tipo = 'revocacion_por_desactivacion'")
    assert evento[0] == {"sesiones_revocadas": 2, "invocacion": r["invocacion"]} and evento[1:] == (None, None, None)
    ids = [str(f[0]) for f in filas("select id from sesion")]
    for secreto in ("secreto-de-c1", "segundo-secreto-de-c1", "tercer-secreto-de-c1", *ids):
        assert secreto not in json.dumps(evento[0])
    assert filas("select valor_nuevo ->> 'sesiones_revocadas' from auditoria where operacion = 'desactivacion_acceso'") == [("2",)]


def test_una_desactivacion_rechazada_no_deja_evento(mundo):
    assert desactivar(mundo, "C1")[0] == 0
    assert desactivar(mundo, "C1", "Otro motivo")[0] == 2                                        # ACCESO_YA_DESACTIVADO
    assert filas("select count(*) from evento_autenticacion where tipo = 'revocacion_por_desactivacion'") == [(1,)]


def test_si_falla_el_evento_la_desactivacion_se_deshace_por_completo(mundo, monkeypatch):
    def falla(*a, **k):
        raise RuntimeError("no se pudo registrar")
    monkeypatch.setattr(acceso, "registrar_evento", falla)
    antes = foto()
    codigo, salida, error = desactivar(mundo, "C1")
    assert codigo == 1 and json.loads(error) == {"error": "ERROR_INTERNO", "tipo": "RuntimeError"} and foto() == antes


# ==================================================== validaciones y rechazos ============================================

@pytest.mark.parametrize("motivo", ["", "   ", "\t"])
def test_un_motivo_vacio_se_rechaza_sin_cambios(mundo, motivo):
    antes = foto()
    codigo, salida, error = desactivar(mundo, "C1", motivo)
    assert codigo == 2 and salida == "" and json.loads(error)["error"] == "CAMPO_OBLIGATORIO" and foto() == antes


def test_sin_motivo_la_cli_se_niega_antes_de_tocar_la_base(mundo):
    antes = foto()
    codigo, salida, error = ejecutar(["desactivar-acceso", *mundo["op"], "--persona", mundo["ids"]["C1"]])
    assert codigo == 2 and salida == "" and foto() == antes


def test_los_errores_de_la_orden_tienen_codigos_estables_y_no_dejan_nada(mundo):
    antes = foto()
    for argv, esperado in ((["--persona", "no-es-un-uuid", "--motivo", MOTIVO], "SOLICITUD_INVALIDA"),
                           (["--persona", str(uuid.uuid4()), "--motivo", MOTIVO], "RECURSO_NO_DISPONIBLE")):
        codigo, salida, error = ejecutar(["desactivar-acceso", *mundo["op"], *argv])
        assert codigo == 2 and salida == "" and json.loads(error)["error"] == esperado
    assert foto() == antes


def test_una_solicitud_repetida_se_rechaza_de_forma_explicita(mundo):
    assert desactivar(mundo, "C1")[0] == 0
    antes = foto()
    codigo, salida, error = desactivar(mundo, "C1", "Otro motivo")
    assert codigo == 2 and salida == "" and json.loads(error)["error"] == "ACCESO_YA_DESACTIVADO" and foto() == antes


# ==================================================== autorización y conexión =============================================

def test_una_persona_operadora_desconocida_o_con_otra_credencial_no_desactiva_nada(mundo):
    for operador, credencial in (("desconocida", CREDENCIAL), (mundo["operador"], "credencial-equivocada-123")):
        antes = foto()
        codigo, salida, error = ejecutar(["desactivar-acceso", "--operador", operador, "--persona", mundo["ids"]["C1"], "--motivo", MOTIVO], credencial=credencial)
        assert codigo == 2 and json.loads(error)["error"] == "OPERADOR_NO_AUTORIZADO" and salida == "" and credencial not in error
        assert foto() == antes


@pytest.mark.parametrize("motor_nombre", ["aplicacion", "propietario"])
def test_la_cli_se_niega_a_trabajar_con_un_rol_que_no_es_el_de_provision(mundo, motor_nombre):
    antes = foto()
    motor = get_engine() if motor_nombre == "aplicacion" else get_owner_engine()
    codigo, salida, error = desactivar(mundo, "C1", motor_provision=motor)
    assert codigo == 3 and json.loads(error)["error"] == "CONEXION_NO_PERMITIDA" and salida == "" and foto() == antes


def test_un_error_inesperado_no_imprime_el_texto_de_la_excepcion(mundo, monkeypatch):
    def falla(*a, **k):
        raise RuntimeError(f"falló con la credencial {CREDENCIAL} y el hash $argon2id$secreto")
    monkeypatch.setattr(acceso, "desactivar_acceso", falla)
    antes = foto()
    codigo, salida, error = desactivar(mundo, "C1")
    assert codigo == 1 and json.loads(error) == {"error": "ERROR_INTERNO", "tipo": "RuntimeError"} and salida == ""
    sin_secretos(salida, error)
    assert foto() == antes


def test_no_hay_opciones_para_fijar_la_fecha_ni_para_pasar_la_credencial_y_el_motivo_se_advierte_como_no_secreto():
    ayuda = cli._parser()._subparsers._group_actions[0].choices["desactivar-acceso"].format_help()
    for palabra in ("--hoy", "--fecha-actual", "--reloj", "--ahora", "--credencial", "--password", "--contrasena"):
        assert palabra not in ayuda
    assert "no secreto" in ayuda


def test_no_existe_ninguna_ruta_http_de_desactivacion_del_acceso():
    """A2 y CA-26: es solo una orden de la CLI del servidor; nadie con una sesión (supervisor incluido) la tiene."""
    from app.main import crear_app
    # Las dos únicas rutas públicas con «acceso» son los canjes del código (M1-T8.3 y M1-T8.4), que no desactivan ni provisionan nada.
    canjes = {"/api/v1/acceso/primer-acceso", "/api/v1/acceso/recuperacion"}
    rutas = [r for r in crear_app().openapi()["paths"] if r not in canjes]
    assert len(rutas) < len(crear_app().openapi()["paths"])
    for ruta in rutas:
        for palabra in ("desactiv", "acceso", "provision", "operador"):
            assert palabra not in ruta, ruta


# ==================================================== el proceso real =====================================================

def _proceso(argv, entorno=None):
    return subprocess.run([sys.executable, "-m", "scripts.provision", *argv], cwd=RAIZ, env=entorno or {**os.environ, VARIABLE_CREDENCIAL: CREDENCIAL},
                          capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL, timeout=120)


def test_la_cli_desactiva_como_proceso_y_la_credencial_no_aparece_en_los_argumentos(mundo):
    argv = ["desactivar-acceso", "--operador", mundo["operador"], "--persona", mundo["ids"]["ST"], "--motivo", MOTIVO]
    assert CREDENCIAL not in " ".join(argv)
    r = _proceso(argv)
    assert r.returncode == 0, r.stderr
    salida = json.loads(r.stdout)
    assert salida["advertencias"][0]["equipo"] == "T" and r.stderr == ""
    sin_secretos(r.stdout, r.stderr)


def test_el_proceso_sin_credencial_ni_terminal_termina_con_error_y_sin_cambios(mundo):
    antes = foto()
    entorno = {k: v for k, v in os.environ.items() if k != VARIABLE_CREDENCIAL}
    r = _proceso(["desactivar-acceso", "--operador", mundo["operador"], "--persona", mundo["ids"]["C1"], "--motivo", MOTIVO], entorno)
    assert r.returncode == 2 and json.loads(r.stderr)["error"] == "CREDENCIAL_NO_VALIDA" and foto() == antes
