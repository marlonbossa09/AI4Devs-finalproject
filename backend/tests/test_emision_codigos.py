"""M1-T8.2 — emisión administrativa de códigos de primer acceso y de recuperación (órdenes CLI ``emitir-codigo-primer-acceso`` y
``emitir-codigo-recuperacion``; contratos M1-03a y M1-09a). SOLO la emisión: no hay canje, así que nada de esto hace funcional el primer acceso.

Pruebas esenciales (metodología ligera): el flujo principal de cada orden con PostgreSQL real; elegibilidad y rechazos sin efectos parciales; el
código solo en una terminal interactiva y nunca en el JSON, la auditoría ni la base; la verificación de identidad estructurada y DECLARADA; la
invalidación del código anterior; un fallo al presentar no deja nada guardado; y la carrera con la desactivación del acceso en los dos órdenes.
"""

import io
import json
import os
import subprocess
import sys
import threading
import uuid

import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine, get_owner_engine, get_provision_engine
from app.provision import cli, emision
from app.provision.acceso import desactivar_acceso
from app.provision.errores import ErrorDeProvision
from app.provision.operadores import identificar
from app.seguridad import codigos
from tests.fabricas import hoy
from tests.test_provision_cli import CREDENCIAL, RAIZ, instalada  # noqa: F401  (fixture ``instalada``)
from tests.test_traslados import _esperar_bloqueo_consultivo
from tests.utiles_m2 import contar, filas

HOY = hoy()
REF = "ACTA-2026/0117"


class Terminal(io.StringIO):
    def isatty(self):
        return True


def correr(argv, *, tty=True, confirmar="CONFIRMO", interactivo=True, credencial=CREDENCIAL, **extra):
    salida = Terminal() if tty else io.StringIO()
    error = io.StringIO()
    visto = []
    codigo = cli.main(argv, entorno={cli.VARIABLE_CREDENCIAL: credencial}, interactivo=interactivo, salida=salida, error=error,
                      motor_provision=get_provision_engine(), motor_propietario=get_owner_engine(),
                      confirmar=lambda prompt: visto.append(prompt) or confirmar, **extra)
    return codigo, salida.getvalue(), error.getvalue(), visto


def ejecutar_simple(argv):
    """Para preparar el mundo con órdenes que no muestran nada (la CLI exige terminal solo a las de emisión)."""
    codigo, salida, error, _ = correr(argv, tty=False, interactivo=False)
    assert codigo == 0, error
    return json.loads(salida)


@pytest.fixture()
def mundo(instalada):
    op = ["--operador", instalada["operador"]]
    equipo = ejecutar_simple(["crear-equipo", *op, "--organizacion", str(instalada["org"]), "--nombre", "T"])["equipo_id"]
    p = {}
    for clave, rol in (("ST", "supervisor"), ("ANA", "colaborador"), ("BETO", "colaborador")):
        p[clave] = ejecutar_simple(["crear-persona", *op, "--nombre", clave, "--identificador-acceso", clave.lower(), "--equipo", equipo, "--rol", rol,
                                   "--desde", HOY.isoformat()])["persona_id"]
    with get_owner_engine().begin() as c:                                    # BETO ya tiene contraseña (recuperación); ANA no (primer acceso)
        c.execute(text("update identidad set hash_contrasena = 'x' where identificador_acceso = 'beto'"))
    return {"op": op, "p": p, "operador": instalada["operador"]}


def primer(mundo, clave="ANA", **kw):
    return correr(["emitir-codigo-primer-acceso", *mundo["op"], "--persona", mundo["p"][clave]], **kw)


def recuperacion(mundo, clave="BETO", procedimiento="PRESENCIAL", referencia=REF, **kw):
    return correr(["emitir-codigo-recuperacion", *mundo["op"], "--persona", mundo["p"][clave], "--procedimiento", procedimiento,
                   "--referencia", referencia], **kw)


def el_codigo_mostrado(salida):
    import re
    hallados = re.findall(r"\b[0-9A-Z]{5}(?:-[0-9A-Z]{5}){3}-[0-9A-Z]{6}\b", salida)
    assert len(hallados) == 1, salida
    return hallados[0]


def sin_efectos():
    return contar("codigo_unico") == 0 and filas("select count(*) from auditoria where operacion in ('entrega_acceso', 'recuperacion_acceso')") == [(0,)]


# ===================================================== flujo principal =======================================================

def test_el_primer_acceso_se_emite_se_muestra_una_vez_en_la_terminal_y_solo_se_guarda_su_hmac(mundo):
    codigo, salida, error, confirmaciones = primer(mundo)
    assert codigo == 0 and error == "" and confirmaciones == []                              # el primer acceso no pide declaración
    mostrado = el_codigo_mostrado(salida)
    resultado = json.loads(salida.strip().splitlines()[-1])
    assert resultado["finalidad"] == "primer_acceso" and resultado["codigo_anterior_invalidado"] is False and "orden" in resultado
    fila = filas("select hash_codigo, finalidad, caduca_en - emitido_en, usado_en, invalidado_en, emitido_por from codigo_unico")[0]
    assert fila[0] == codigos.hash_de_codigo(mostrado) and fila[1] == "primer_acceso" and fila[3] is None and fila[4] is None
    assert 599 <= fila[2].total_seconds() <= 601 and fila[5].startswith(f"operador:{mundo['operador']}|invocacion:")
    # El código no está en el resultado JSON, ni en la base (más que su HMAC), ni en la auditoría.
    assert mostrado not in json.dumps(resultado) and codigos.normalizar(mostrado).hex() not in json.dumps(resultado)
    for tabla in ("codigo_unico", "auditoria", "evento_autenticacion"):
        for f in filas(f"select t::text from {tabla} t"):
            assert mostrado not in f[0] and mostrado.replace("-", "") not in f[0], tabla


def test_la_auditoria_de_la_emision_reutiliza_entrega_acceso_con_la_fase_y_sin_secretos(mundo):
    primer(mundo)
    (a,) = filas("select tipo_autor, referencia_provision, operacion, objeto_id, propietaria_registro_id, motivo, valor_anterior, valor_nuevo "
                 "from auditoria where operacion = 'entrega_acceso'")
    assert a[0] == "provision" and a[1].startswith(f"operador:{mundo['operador']}|") and a[3] == a[4] == uuid.UUID(mundo["p"]["ANA"])
    assert set(a[7]) == {"fase", "finalidad", "codigo_id", "caduca_en"} and a[7]["fase"] == "emision" and a[7]["finalidad"] == "primer_acceso"
    assert a[6] == {"codigo_pendiente_invalidado": False}
    hash_ = filas("select hash_codigo from codigo_unico")[0][0]
    assert hash_ not in json.dumps(a[7]) and "hash" not in json.dumps(a[7])


def test_la_recuperacion_exige_declarar_la_verificacion_y_la_deja_estructurada_en_la_auditoria(mundo):
    codigo, salida, error, confirmaciones = recuperacion(mundo, procedimiento="VIDEOLLAMADA")
    assert codigo == 0 and len(confirmaciones) == 1 and "VIDEOLLAMADA" in confirmaciones[0] and REF in confirmaciones[0]
    resultado = json.loads(salida.strip().splitlines()[-1])
    assert resultado["verificacion"] == {"procedimiento": "VIDEOLLAMADA", "referencia": REF, "declarada_por_la_persona_operadora": True}
    (a,) = filas("select operacion, valor_nuevo from auditoria where operacion = 'recuperacion_acceso'")
    v = a[1]["verificacion"]
    assert a[1]["fase"] == "emision" and a[1]["finalidad"] == "recuperacion"
    assert set(v) == {"procedimiento", "referencia", "declarada_en", "declarada_por_la_persona_operadora", "verificada_por_el_sistema"}
    assert v["procedimiento"] == "VIDEOLLAMADA" and v["referencia"] == REF and v["declarada_por_la_persona_operadora"] is True
    assert v["verificada_por_el_sistema"] is False                      # elegir una opción no equivale a que el sistema haya verificado nada
    assert el_codigo_mostrado(salida) not in json.dumps(a[1])


@pytest.mark.parametrize("declaracion", ["", "no", "confirmo", "SI"])
def test_sin_la_declaracion_expresa_no_se_emite_nada(mundo, declaracion):
    codigo, salida, error, _ = recuperacion(mundo, confirmar=declaracion)
    assert codigo == 2 and json.loads(error)["error"] == "VERIFICACION_NO_DECLARADA" and salida == "" and sin_efectos()


@pytest.mark.parametrize("referencia", ["ab", "DNI 12345678", "x" * 65, "foto del documento", "../../etc", "con\nsalto"])
def test_la_referencia_debe_ser_una_referencia_administrativa_no_una_descripcion(mundo, referencia):
    codigo, salida, error, confirmaciones = recuperacion(mundo, referencia=referencia)
    assert codigo == 2 and json.loads(error)["error"] in ("SOLICITUD_INVALIDA", "CAMPO_OBLIGATORIO") and confirmaciones == [] and sin_efectos()


def test_solo_los_tres_procedimientos_aprobados_son_validos(mundo):
    assert recuperacion(mundo, procedimiento="TELEFONO")[0] == 2 and sin_efectos()            # argparse lo rechaza
    for ok in emision.PROCEDIMIENTOS:
        assert recuperacion(mundo, procedimiento=ok)[0] == 0


# ===================================================== elegibilidad y rechazos sin efectos parciales =========================

def test_la_finalidad_debe_corresponder_al_estado_de_la_contrasena(mundo):
    codigo, _, error, _ = primer(mundo, "BETO")                                            # ya tiene contraseña
    assert codigo == 2 and json.loads(error)["detalles"] == [{"campo": "persona", "motivo": "primer_acceso_ya_completado"}]
    codigo, _, error, _ = recuperacion(mundo, "ANA")                                       # aún no tiene contraseña
    assert codigo == 2 and json.loads(error)["detalles"] == [{"campo": "persona", "motivo": "sin_contrasena_establecida"}]
    assert sin_efectos()


def test_a_un_acceso_desactivado_no_se_le_emite_ningun_codigo(mundo):
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now()"))
    for resultado in (primer(mundo), recuperacion(mundo)):
        assert resultado[0] == 2 and json.loads(resultado[2])["error"] == "ACCESO_DESACTIVADO_ADMINISTRATIVAMENTE" and resultado[1] == ""
    assert sin_efectos()


def test_una_persona_inexistente_o_una_operadora_no_autorizada_no_dejan_nada(mundo):
    r = correr(["emitir-codigo-primer-acceso", *mundo["op"], "--persona", str(uuid.uuid4())])
    assert r[0] == 2 and json.loads(r[2])["error"] == "RECURSO_NO_DISPONIBLE"
    r = primer(mundo, credencial="credencial-equivocada-123")
    assert r[0] == 2 and json.loads(r[2])["error"] == "OPERADOR_NO_AUTORIZADO" and r[1] == ""
    r = correr(["emitir-codigo-primer-acceso", "--operador", "no.existe", "--persona", mundo["p"]["ANA"]])
    assert r[0] == 2 and json.loads(r[2])["error"] == "OPERADOR_NO_AUTORIZADO" and sin_efectos()


def test_volver_a_emitir_invalida_el_codigo_anterior_de_la_misma_finalidad_y_lo_deja_en_la_auditoria(mundo):
    primero = el_codigo_mostrado(primer(mundo)[1])
    segundo = el_codigo_mostrado(primer(mundo)[1])
    assert primero != segundo
    assert filas("select usado_en is not null, invalidado_en is not null from codigo_unico order by emitido_en") == [(False, True), (False, False)]
    assert filas("select hash_codigo from codigo_unico where invalidado_en is null") == [(codigos.hash_de_codigo(segundo),)]
    anteriores = [a[0] for a in filas("select valor_anterior from auditoria where operacion = 'entrega_acceso' order by momento, id")]
    assert sorted(x["codigo_pendiente_invalidado"] for x in anteriores) == [False, True]
    assert recuperacion(mundo)[0] == 0 and contar("codigo_unico") == 3                       # otra finalidad: no invalida a la anterior
    assert filas("select count(*) from codigo_unico where invalidado_en is null and finalidad = 'primer_acceso'") == [(1,)]


# ===================================================== el código solo en una terminal interactiva ============================

@pytest.mark.parametrize("tty, interactivo", [(False, True), (True, False), (False, False)])
def test_sin_terminal_interactiva_la_orden_se_rechaza_antes_de_tocar_nada(mundo, tty, interactivo):
    intentos_antes = contar("control_de_intentos_operador")
    codigo, salida, error, confirmaciones = recuperacion(mundo, tty=tty, interactivo=interactivo)
    assert codigo == 2 and json.loads(error)["error"] == "TERMINAL_INTERACTIVA_REQUERIDA" and salida == "" and confirmaciones == []
    assert sin_efectos() and contar("control_de_intentos_operador") == intentos_antes       # ni siquiera se identifica a la persona operadora


def test_como_proceso_real_con_la_salida_en_una_tuberia_se_rechaza_y_no_imprime_ningun_codigo(mundo):
    r = subprocess.run([sys.executable, "-m", "scripts.provision", "emitir-codigo-primer-acceso", *mundo["op"], "--persona", mundo["p"]["ANA"]], cwd=RAIZ,
                       env={**os.environ, cli.VARIABLE_CREDENCIAL: CREDENCIAL}, capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL, timeout=120)
    assert r.returncode == 2 and json.loads(r.stderr)["error"] == "TERMINAL_INTERACTIVA_REQUERIDA" and r.stdout == "" and sin_efectos()


def test_ninguna_orden_acepta_un_codigo_ni_una_credencial_como_argumento():
    ayuda = {n: cli._parser()._subparsers._group_actions[0].choices[n].format_help() for n in cli.EMISION}
    for texto in ayuda.values():
        for palabra in ("--codigo", "--credencial", "--password", "--contrasena", "--hash"):
            assert palabra not in texto


def test_la_api_no_emite_codigos_ni_tiene_rutas_de_codigos():
    from app.main import crear_app
    for ruta in crear_app().openapi()["paths"]:
        assert "codigo" not in ruta and "emitir" not in ruta, ruta
    for sentencia in ("insert into codigo_unico (identidad_id, finalidad, hash_codigo, caduca_en, emitido_por) values (gen_random_uuid(), 'primer_acceso', '"
                      + "a" * 64 + "', now(), 'x')", "select 1 from codigo_unico"):
        with get_engine().connect() as c:
            with pytest.raises(Exception) as e:
                c.execute(text(sentencia))
            assert "42501" in str(e.value) or "permiso denegado" in str(e.value)


# ===================================================== sin código sin ver: fallos al presentar o al confirmar =================

def test_si_no_se_puede_presentar_el_codigo_la_transaccion_se_deshace_y_no_queda_nada_guardado(mundo):
    def falla(codigo, caduca_en):
        raise OSError(f"no se pudo escribir {codigo}")
    with get_provision_engine().connect() as c:
        operador = identificar(c, mundo["operador"], CREDENCIAL)
        c.commit()
    with pytest.raises(ErrorDeProvision) as e, get_provision_engine().begin() as c:
        emision.emitir_codigo(c, operador, persona_id=uuid.UUID(mundo["p"]["ANA"]), finalidad="primer_acceso", verificacion=None, presentar=falla)
    assert e.value.codigo == "CODIGO_NO_PRESENTADO" and "no se pudo escribir" not in str(e.value) and sin_efectos()


def test_si_falla_la_confirmacion_despues_de_mostrarlo_se_avisa_de_que_el_codigo_mostrado_no_vale(mundo, monkeypatch):
    original = emision.emitir_codigo

    def muestra_y_falla(*a, **k):
        original(*a, **k)
        raise RuntimeError("falló el commit")
    monkeypatch.setattr(emision, "emitir_codigo", muestra_y_falla)
    codigo, salida, error, _ = primer(mundo)
    assert codigo == 2 and json.loads(error)["error"] == "CODIGO_NO_CONFIRMADO" and sin_efectos()
    assert json.loads(error)["mensaje"].startswith("El código mostrado NO es válido")


def test_sin_el_secreto_de_codigos_se_rechaza_antes_de_identificar_a_la_operadora(mundo, monkeypatch):
    monkeypatch.setattr(get_settings(), "code_pepper", None)
    r = primer(mundo)
    assert r[0] == 2 and json.loads(r[2])["error"] == "SECRETO_DE_CODIGOS_NO_CONFIGURADO" and sin_efectos()


# ===================================================== carrera con la desactivación del acceso ===============================

def _operador():
    with get_provision_engine().connect() as c:
        o = identificar(c, "operadora.cli", CREDENCIAL)
        c.commit()
    return o


def test_si_la_desactivacion_toma_el_bloqueo_primero_la_emision_la_ve_y_se_rechaza(mundo):
    operador, resultado, ana = _operador(), {}, uuid.UUID(mundo["p"]["ANA"])

    def emitir():
        try:
            with get_provision_engine().begin() as c:
                emision.emitir_codigo(c, operador, persona_id=ana, finalidad="primer_acceso", verificacion=None, presentar=lambda *a: None)
            resultado["r"] = "emitido"
        except ErrorDeProvision as e:
            resultado["r"] = e.codigo
    with get_provision_engine().connect() as c:
        desactivar_acceso(c, operador, persona_id=ana, motivo="Baja")                         # sin confirmar todavía
        hilo = threading.Thread(target=emitir)
        hilo.start()
        assert _esperar_bloqueo_consultivo(), "la emisión debía esperar el bloqueo de la persona"
        c.commit()
    hilo.join(30)
    assert resultado["r"] == "ACCESO_DESACTIVADO_ADMINISTRATIVAMENTE" and contar("codigo_unico") == 0


def test_si_la_emision_toma_el_bloqueo_primero_la_desactivacion_invalida_el_codigo_en_su_transaccion(mundo):
    operador, ana = _operador(), uuid.UUID(mundo["p"]["ANA"])
    resultado = {}

    def desactivar():
        with get_provision_engine().begin() as c:
            resultado["d"] = desactivar_acceso(c, operador, persona_id=ana, motivo="Baja")
    with get_provision_engine().connect() as c:
        emision.emitir_codigo(c, operador, persona_id=ana, finalidad="primer_acceso", verificacion=None, presentar=lambda *a: None)   # sin confirmar
        hilo = threading.Thread(target=desactivar)
        hilo.start()
        assert _esperar_bloqueo_consultivo(), "la desactivación debía esperar a la emisión"
        c.commit()
    hilo.join(30)
    assert filas("select usado_en is not null, invalidado_en is not null from codigo_unico") == [(False, True)]       # nunca queda un código vivo
    assert filas("select acceso_desactivado_en is not null from persona where id = :p", p=ana) == [(True,)]
    assert filas("select valor_nuevo ->> 'codigos_invalidados' from auditoria where operacion = 'desactivacion_acceso'") == [("1",)]
