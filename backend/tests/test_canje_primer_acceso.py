"""M1-T8.3 — canje del código de primer acceso (``POST /api/v1/acceso/primer-acceso``, contrato M1-03b) con FastAPI y PostgreSQL reales.

Pruebas esenciales (metodología ligera): el flujo válido y el inicio de sesión posterior; respuestas uniformes para todo código no válido; la política de contraseña
sin consumir el código ni dar un oráculo; los límites de intentos de M1-T7 y la invalidación a los 10; dos canjes simultáneos; atomicidad; la carrera con la
desactivación; los permisos y el alcance de la función ``SECURITY DEFINER``; y que no se abre ninguna sesión ni se filtra nada. Destructivas solo sobre ``smartwork_test``.
"""

import logging
import threading
import uuid
from collections import Counter
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine, get_owner_engine, get_provision_engine
from app.main import crear_app
from app.provision import emision
from app.provision.acceso import desactivar_acceso
from app.provision.operadores import Operador
from app.seguridad import codigos, control_de_intentos as control
from app.seguridad.contrasenas import verificar
from app.seguridad.sesiones import NOMBRE_COOKIE
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, hoy
from tests.test_control_de_intentos import Reloj
from tests.test_db_traslados import transaccion
from tests.test_traslados import _esperar_bloqueo_consultivo
from tests.utiles_http import API, ORIGEN, iniciar_sesion
from tests.utiles_m2 import contar, filas
from fastapi.testclient import TestClient

BUENA = "una-contraseña-segura-1"
RUTA = f"{API}/acceso/primer-acceso"
OPERADOR = Operador(uuid.uuid4(), "operadora.test")


def cliente(host="203.0.113.5"):
    return TestClient(crear_app(), base_url=ORIGEN, client=(host, 50000), raise_server_exceptions=False)


def canjear(c, identificador, codigo, contrasena=BUENA, origen=ORIGEN, **extra):
    cabeceras = {"Origin": origen} if origen else {}
    return c.post(RUTA, json={"identificador_acceso": identificador, "codigo": codigo, "contrasena_nueva": contrasena, **extra}, headers=cabeceras)


def huella(r):
    return (r.status_code, r.json() if r.content else None, r.headers.get("cache-control"), "set-cookie" in r.headers)


@pytest.fixture()
def mundo():
    """Ana y Beto sin contraseña (primer acceso pendiente); Clara ya con contraseña. Un código de primer acceso emitido a cada una de las dos primeras."""
    with get_owner_engine().begin() as c:
        eq = crear_equipo(c, crear_organizacion(c), "T")
        p = {}
        for nombre, clave in (("ana", None), ("beto", None), ("clara", "contraseña-de-clara-1")):
            p[nombre] = crear_persona(c, nombre)
            crear_pertenencia(c, p[nombre], eq, "colaborador", desde=hoy() - timedelta(days=1))
            crear_identidad(c, p[nombre], nombre, clave)
    codigo = {n: emitir(p[n]) for n in ("ana", "beto")}
    return {"p": p, "codigo": codigo}


def emitir(persona):
    visto = []
    with get_provision_engine().begin() as c:
        emision.emitir_codigo(c, OPERADOR, persona_id=persona, finalidad="primer_acceso", verificacion=None, presentar=lambda cod, caduca: visto.append(cod))
    return visto[0]


def estado(identificador):
    return filas("select c.usado_en is not null, c.invalidado_en is not null, c.intentos_fallidos from codigo_unico c join identidad i on i.id = c.identidad_id "
                 "where i.identificador_acceso = :i order by c.emitido_en", i=identificador)


def password_establecida(identificador):
    return filas("select hash_contrasena is not null, contrasena_establecida_en is not null from identidad where identificador_acceso = :i", i=identificador)[0]


@pytest.fixture()
def reloj(monkeypatch):
    r = Reloj()
    monkeypatch.setattr(control, "_ahora", r)
    return r


# ===================================================== flujo válido ==========================================================

def test_el_primer_acceso_establece_la_contrasena_consume_el_codigo_y_no_abre_sesion(mundo):
    c = cliente()
    r = canjear(c, "ana", mundo["codigo"]["ana"])
    assert r.status_code == 204 and r.content == b"" and r.headers["cache-control"] == "no-store"
    assert NOMBRE_COOKIE not in r.headers.get("set-cookie", "") and contar("sesion") == 0                     # no crea sesión
    assert password_establecida("ana") == (True, True) and password_establecida("beto") == (False, False)       # solo la de Ana
    assert estado("ana") == [(True, False, 0)] and estado("beto") == [(False, False, 0)]                          # consumo único, y solo el suyo
    hash_ = filas("select hash_contrasena from identidad where identificador_acceso = 'ana'")[0][0]
    assert hash_.startswith("$argon2id$") and verificar(hash_, BUENA) and not verificar(hash_, "otra-contraseña-1")


def test_despues_del_canje_la_persona_inicia_sesion_con_su_contrasena_y_el_codigo_no_se_reutiliza(mundo):
    c = cliente()
    assert canjear(c, "ana", mundo["codigo"]["ana"]).status_code == 204
    r = iniciar_sesion(cliente("203.0.113.9"), "ana", BUENA)
    assert r.status_code == 201 and r.json()["persona"]["nombre"] == "ana" and r.cookies.get(NOMBRE_COOKIE)
    assert iniciar_sesion(cliente("203.0.113.10"), "ana", "otra-contraseña-1").status_code == 401
    # CA-24: un primer acceso ya utilizado no se puede utilizar de nuevo (mismo error uniforme)
    r2 = canjear(c, "ana", mundo["codigo"]["ana"], "segunda-contraseña-2")
    assert r2.status_code == 400 and r2.json()["codigo"] == "CODIGO_NO_VALIDO"
    assert iniciar_sesion(cliente("203.0.113.11"), "ana", BUENA).status_code == 201                             # y la contraseña no cambió


def test_ca25_el_codigo_de_una_persona_no_da_acceso_como_otra(mundo):
    c = cliente()
    assert canjear(c, "beto", mundo["codigo"]["ana"]).status_code == 400                                         # el código de Ana, con el identificador de Beto
    assert canjear(c, "clara", mundo["codigo"]["ana"]).status_code == 400
    assert password_establecida("beto") == (False, False) and password_establecida("ana") == (False, False)
    assert estado("ana") == [(False, False, 0)] and estado("beto") == [(False, False, 1)]                         # solo cuenta el intento fallido contra Beto
    assert canjear(c, "ana", mundo["codigo"]["ana"]).status_code == 204                                          # y el de Ana sigue sirviendo a Ana


def test_el_codigo_se_acepta_con_el_formato_de_presentacion_minusculas_y_sin_guiones(mundo):
    assert canjear(cliente(), "ana", mundo["codigo"]["ana"].lower().replace("-", " ")).status_code == 204


# ===================================================== auditoría =============================================================

def test_la_auditoria_del_canje_es_la_de_la_persona_en_fase_canje_y_no_contiene_secretos(mundo):
    canjear(cliente(), "ana", mundo["codigo"]["ana"])
    filas_ = filas("select tipo_autor, autor_persona_id, referencia_provision, operacion, objeto_id, propietaria_registro_id, valor_anterior, valor_nuevo "
                   "from auditoria where operacion = 'entrega_acceso' order by momento, id")
    assert sum(f[7]["fase"] == "emision" for f in filas_) == 2 and sum(f[7]["fase"] == "canje" for f in filas_) == 1
    (a,) = [f for f in filas_ if f[7]["fase"] == "canje"]
    assert a[0] == "persona" and a[1] == mundo["p"]["ana"] and a[2] is None and a[4] == a[5] == mundo["p"]["ana"]
    assert a[6] == {"contrasena_establecida": False} and a[7]["finalidad"] == "primer_acceso" and a[7]["sesiones_revocadas"] == 0
    texto = str(a)
    hash_codigo = filas("select hash_codigo from codigo_unico c join identidad i on i.id = c.identidad_id where i.identificador_acceso = 'ana'")[0][0]
    hash_contrasena = filas("select hash_contrasena from identidad where identificador_acceso = 'ana'")[0][0]
    for secreto in (mundo["codigo"]["ana"], hash_codigo, hash_contrasena, BUENA, "argon2"):
        assert secreto not in texto


# ===================================================== respuestas uniformes ==================================================

def _causas_de_codigo_no_valido(mundo):
    """Todas las razones por las que un código no vale, cada una con su propio escenario. Devuelve {nombre: (identificador, código)}."""
    with get_owner_engine().begin() as c:
        for n in ("caducado", "usado", "invalidado", "desactivado"):
            p = crear_persona(c, n)
            crear_pertenencia(c, p, crear_equipo(c, crear_organizacion(c), n), "colaborador", desde=hoy() - timedelta(days=1))
            crear_identidad(c, p, n, None)
            mundo["p"][n] = p
    casos = {n: emitir(mundo["p"][n]) for n in ("caducado", "usado", "invalidado", "desactivado")}
    with get_owner_engine().begin() as c:
        c.execute(text("alter table codigo_unico disable trigger user"))          # envejecer un código exige saltarse sus disparadores (solo en la prueba)
        c.execute(text("update codigo_unico set emitido_en = now() - interval '2 hours', caduca_en = now() - interval '1 hour' where identidad_id = "
                       "(select id from identidad where identificador_acceso = 'caducado')"))
        c.execute(text("alter table codigo_unico enable trigger user"))
        c.execute(text("update codigo_unico set usado_en = now() where identidad_id = (select id from identidad where identificador_acceso = 'usado')"))
        c.execute(text("update codigo_unico set invalidado_en = now() where identidad_id = (select id from identidad where identificador_acceso = 'invalidado')"))
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": mundo["p"]["desactivado"]})
    return {**{n: (n, codigo) for n, codigo in casos.items()},
            "inexistente": ("nadie", mundo["codigo"]["ana"]), "equivocado": ("ana", codigos.formatear(codigos.generar_codigo())),
            "mal_formado": ("ana", "esto no es un código"), "ya_con_contrasena": ("clara", mundo["codigo"]["ana"]), "de_otra_persona": ("beto", mundo["codigo"]["ana"])}


def test_todas_las_causas_de_un_codigo_no_valido_dan_exactamente_la_misma_respuesta(mundo, reloj):
    huellas = {}
    for i, (nombre, (ident, cod)) in enumerate(_causas_de_codigo_no_valido(mundo).items()):
        huellas[nombre] = huella(canjear(cliente(f"203.0.113.{20 + i}"), ident, cod))
    assert {h[0] for h in huellas.values()} == {400}
    assert len({str(h) for h in huellas.values()}) == 1, huellas
    cuerpo = next(iter(huellas.values()))[1]
    assert cuerpo == {"codigo": "CODIGO_NO_VALIDO", "mensaje": "El código no es válido.", "detalles": []}
    assert password_establecida("ana") == (False, False) and contar("sesion") == 0


# ===================================================== política de contraseña (D7) ===========================================

def test_una_contrasena_que_incumple_la_politica_no_consume_el_codigo_y_no_es_un_oraculo(mundo, reloj):
    c = cliente()
    con_codigo_valido = canjear(c, "ana", mundo["codigo"]["ana"], "corta")
    con_codigo_falso = canjear(c, "ana", codigos.formatear(codigos.generar_codigo()), "corta")
    con_identificador_falso = canjear(c, "nadie", "xxx", "corta")
    assert con_codigo_valido.status_code == 422 and huella(con_codigo_valido) == huella(con_codigo_falso) == huella(con_identificador_falso)
    assert con_codigo_valido.json() == {"codigo": "CONTRASENA_NO_VALIDA", "mensaje": "La contraseña no cumple la política.",
                                        "detalles": [{"campo": "contrasena_nueva", "motivo": "demasiado_corta"}]}
    assert estado("ana") == [(False, False, 0)] and password_establecida("ana") == (False, False)           # ni consumido ni con intentos
    assert contar("control_de_intentos") == 0 and contar("intento_de_origen") == 0                           # esta rama no prueba ningún código: no gasta intentos
    assert canjear(c, "ana", mundo["codigo"]["ana"]).status_code == 204                                     # y con una contraseña buena, sigue valiendo


def test_la_politica_acepta_exactamente_diez_caracteres_sin_reglas_de_composicion(mundo):
    assert canjear(cliente(), "ana", mundo["codigo"]["ana"], "a" * 9).status_code == 422
    assert canjear(cliente(), "ana", mundo["codigo"]["ana"], "a" * 10).status_code == 204


# ===================================================== límites de intentos (M1-T7) y 10 intentos por código ==================

def test_los_canjes_fallidos_se_limitan_con_la_curva_de_m1_t7_y_un_canje_efectivo_reinicia_el_contador(mundo, reloj):
    c = cliente()
    malo = codigos.formatear(codigos.generar_codigo())
    assert [canjear(c, "ana", malo).status_code for _ in range(5)] == [400] * 5
    r = canjear(c, "ana", mundo["codigo"]["ana"])                                              # aun con el código BUENO: en espera
    assert r.status_code == 429 and r.headers["retry-after"] == "30" and r.json()["detalles"] == [{"espera_segundos": 30}]
    assert estado("ana") == [(False, False, 5)] and password_establecida("ana") == (False, False)
    reloj.avanzar(seconds=30)
    assert canjear(c, "ana", mundo["codigo"]["ana"]).status_code == 204
    assert contar("control_de_intentos") == 0                                                    # reiniciado por el canje efectivo
    assert filas("select count(*) from control_de_intentos where clave = :k", k=control.clave_de_cuenta("ana", "203.0.113.5")) == [(0,)]


def test_el_canje_y_el_inicio_de_sesion_llevan_contadores_separados_aunque_compartan_los_limites_por_origen(mundo, reloj):
    c = cliente()
    for _ in range(5):
        assert iniciar_sesion(c, "ana", "contraseña-equivocada-1").status_code == 401
    assert iniciar_sesion(c, "ana", "contraseña-equivocada-1").status_code == 429                # el inicio de sesión de Ana está en espera...
    assert canjear(c, "ana", mundo["codigo"]["ana"]).status_code == 204                          # ...y el canje no (dominio de clave propio)
    assert control.clave_de_canje("ana", "x") != control.clave_de_cuenta("ana", "x")


def test_a_los_diez_canjes_fallidos_el_codigo_se_invalida_y_ya_no_sirve_ni_el_bueno(mundo, reloj):
    c = cliente()
    for _ in range(10):
        r = canjear(c, "ana", codigos.formatear(codigos.generar_codigo()))
        while r.status_code == 429:
            reloj.avanzar(seconds=int(r.headers["retry-after"]))
            r = canjear(c, "ana", codigos.formatear(codigos.generar_codigo()))
        assert r.status_code == 400
    assert estado("ana") == [(False, True, 10)]
    reloj.avanzar(hours=2)
    assert canjear(c, "ana", mundo["codigo"]["ana"]).status_code == 400 and password_establecida("ana") == (False, False)


# ===================================================== concurrencia y atomicidad =============================================

def test_dos_o_mas_canjes_simultaneos_del_mismo_codigo_dejan_exactamente_uno_efectivo(mundo):
    clientes = [cliente(f"203.0.113.{40 + i}") for i in range(8)]
    barrera, resultados = threading.Barrier(8), []

    def tarea(i):
        barrera.wait(timeout=30)
        resultados.append(canjear(clientes[i], "ana", mundo["codigo"]["ana"], f"contraseña-numero-{i}-ok").status_code)
    hilos = [threading.Thread(target=tarea, args=(i,)) for i in range(8)]
    [t.start() for t in hilos]
    [t.join(60) for t in hilos]
    assert Counter(resultados) == {204: 1, 400: 7}
    assert estado("ana") == [(True, False, 0)] and password_establecida("ana") == (True, True)
    assert filas("select count(*) from auditoria where valor_nuevo ->> 'fase' = 'canje'") == [(1,)]


def test_si_falla_la_auditoria_no_se_consume_el_codigo_ni_se_toca_la_identidad(mundo):
    with get_owner_engine().begin() as c:
        c.execute(text("alter table auditoria add constraint zz_falla check (valor_nuevo ->> 'fase' is distinct from 'canje') not valid"))
    try:
        r = canjear(cliente(), "ana", mundo["codigo"]["ana"])
    finally:
        with get_owner_engine().begin() as c:
            c.execute(text("alter table auditoria drop constraint zz_falla"))
    assert r.status_code == 500
    assert estado("ana") == [(False, False, 0)] and password_establecida("ana") == (False, False)
    assert canjear(cliente("203.0.113.77"), "ana", mundo["codigo"]["ana"]).status_code == 204          # el código sigue siendo válido


def test_la_desactivacion_que_toma_el_bloqueo_primero_deja_el_canje_sin_efecto(mundo):
    resultado, ana = {}, mundo["p"]["ana"]
    with get_provision_engine().connect() as c:
        desactivar_acceso(c, OPERADOR, persona_id=ana, motivo="Baja")                              # sin confirmar: invalida el código en su transacción
        hilo = threading.Thread(target=lambda: resultado.update(r=canjear(cliente(), "ana", mundo["codigo"]["ana"])))
        hilo.start()
        assert _esperar_bloqueo_consultivo(), "el canje debía esperar el bloqueo de la persona"
        c.commit()
    hilo.join(30)
    assert resultado["r"].status_code == 400 and password_establecida("ana") == (False, False) and estado("ana") == [(False, True, 0)]


def test_un_acceso_desactivado_nunca_establece_contrasena(mundo):
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": mundo["p"]["ana"]})
    assert canjear(cliente(), "ana", mundo["codigo"]["ana"]).status_code == 400
    assert password_establecida("ana") == (False, False) and estado("ana") == [(False, False, 0)]


# ===================================================== PostgreSQL: permisos y alcance de la función ==========================

def test_la_aplicacion_solo_puede_ejecutar_la_funcion_y_no_escribe_ni_lee_los_codigos(mundo):
    for sentencia in ("update identidad set hash_contrasena = 'x'", "update codigo_unico set usado_en = now()", "select hash_codigo from codigo_unico",
                      "insert into codigo_unico (identidad_id, finalidad, hash_codigo, caduca_en, emitido_por) values (gen_random_uuid(), 'primer_acceso', '" + "a" * 64 + "', now(), 'x')"):
        assert transaccion(get_engine(), (sentencia, {}))[0] == "42501", sentencia
    privilegio = "select has_function_privilege(:r, 'public.canjear_codigo_primer_acceso(text, text, text)', 'EXECUTE')"
    assert filas(privilegio, r=get_settings().app_db_role) == [(True,)]
    assert filas(privilegio, r=get_settings().provision_db_role) == [(False,)]
    assert filas("select has_function_privilege('public', 'public.canjear_codigo_primer_acceso(text, text, text)', 'EXECUTE')") == [(False,)]


def test_la_funcion_esta_blindada_search_path_fijo_propietario_sin_privilegios_y_sin_sql_dinamico():
    (f,) = filas("select p.prosecdef, p.proconfig, r.rolsuper, r.rolcreaterole, r.rolcreatedb, r.rolreplication, r.rolbypassrls, p.prosrc "
                 "from pg_proc p join pg_roles r on r.oid = p.proowner where p.proname = 'canjear_codigo_primer_acceso'")
    assert f[0] is True and f[1] == ["search_path=pg_catalog, pg_temp"] and not any(f[2:7])
    assert "EXECUTE" not in f[7].upper().replace("FOR UPDATE", "")                          # nada de SQL dinámico (``EXECUTE`` ni ``format``)
    assert "format(" not in f[7].lower()


def test_la_funcion_no_cambia_otra_identidad_ni_acepta_hashes_o_parametros_invalidos(mundo):
    llamar = "select public.canjear_codigo_primer_acceso(:i, :hc, :hp)"
    argon = "$argon2id$v=19$m=19456,t=2,p=1$c2FsdA$aGFzaA"
    buen_hash = codigos.hash_de_codigo(mundo["codigo"]["ana"])
    for i, hc, hp in (("ana", buen_hash, "no-es-argon2"), ("ana", "no-es-hex", argon), ("ana", buen_hash, argon + "x" * 600), (None, buen_hash, argon),
                      ("ana", None, argon), ("beto", buen_hash, argon), ("nadie", buen_hash, argon), ("clara", buen_hash, argon)):
        with get_engine().begin() as c:
            assert c.execute(text(llamar), {"i": i, "hc": hc, "hp": hp}).scalar_one() is None
    assert password_establecida("ana") == (False, False) and password_establecida("beto") == (False, False)
    with get_engine().begin() as c:                                                           # cambiar el search_path de la sesión no altera lo que resuelve
        c.execute(text("set local search_path = pg_temp, public"))
        assert c.execute(text(llamar), {"i": "ana", "hc": buen_hash, "hp": argon}).scalar_one() == mundo["p"]["ana"]
    assert password_establecida("ana") == (True, True)
    assert filas("select hash_contrasena from identidad where identificador_acceso = 'ana'") == [(argon,)]
    assert filas("select hash_contrasena from identidad where identificador_acceso = 'beto'") == [(None,)]


# ===================================================== origen, forma, secretos y configuración ===============================

@pytest.mark.parametrize("origen", ["https://evil.example", "null", None])
def test_el_origen_se_verifica_y_no_cuenta_como_intento(mundo, origen):
    r = canjear(cliente(), "ana", mundo["codigo"]["ana"], origen=origen)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA" and password_establecida("ana") == (False, False)
    assert contar("control_de_intentos") == 0 and estado("ana") == [(False, False, 0)]


def test_los_campos_desconocidos_o_demasiado_largos_se_rechazan_sin_contar_intentos(mundo):
    assert canjear(cliente(), "ana", mundo["codigo"]["ana"], rol="supervisor").status_code == 400
    assert canjear(cliente(), "ana", "x" * 65).status_code == 400
    assert canjear(cliente(), "a" * 500, mundo["codigo"]["ana"]).status_code == 400
    assert contar("control_de_intentos") == 0 and estado("ana") == [(False, False, 0)]


def test_ni_las_respuestas_ni_los_registros_contienen_el_codigo_el_hash_ni_la_contrasena(mundo, caplog):
    with caplog.at_level(logging.DEBUG):
        resultados = [canjear(cliente(), "ana", codigos.formatear(codigos.generar_codigo()), "contraseña-secreta-única-1"),
                      canjear(cliente(), "ana", mundo["codigo"]["ana"], "contraseña-secreta-única-1")]
    secretos = [mundo["codigo"]["ana"], mundo["codigo"]["ana"].replace("-", ""), codigos.hash_de_codigo(mundo["codigo"]["ana"]), "contraseña-secreta-única-1"]
    for r in resultados:
        for s in secretos:
            assert s not in r.text and s not in str(r.headers)
    for s in secretos:
        assert s not in caplog.text
    for tabla in ("evento_autenticacion", "control_de_intentos", "intento_de_origen"):
        for f in filas(f"select t::text from {tabla} t"):
            assert not any(s in f[0] for s in secretos[:1] + secretos[3:])


def test_sin_el_secreto_de_codigos_la_aplicacion_no_arranca(monkeypatch):
    monkeypatch.setattr(get_settings(), "code_pepper", None)
    with pytest.raises(codigos.SecretoDeCodigosNoConfigurado):
        crear_app()
