"""M1-T8.4 — canje del código de recuperación (``POST /api/v1/acceso/recuperacion``, contrato M1-09b) con FastAPI y PostgreSQL reales.

Pruebas esenciales (metodología ligera): recuperación correcta con revocación de TODAS las sesiones anteriores y cambio efectivo de contraseña; respuestas uniformes
(también entre finalidades); un acceso desactivado NO se reactiva; la política de contraseña primero y sin consumir nada; límites y 10 intentos; dos canjes simultáneos;
atomicidad (si falla la auditoría no se revoca ni se cambia nada); y el blindaje de la función. El patrón de la base es el de ``test_canje_primer_acceso.py``.
"""

import threading
import uuid
from collections import Counter
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine, get_owner_engine, get_provision_engine
from app.provision import emision
from app.provision.acceso import desactivar_acceso
from app.provision.operadores import Operador
from app.seguridad import codigos, control_de_intentos as control
from app.seguridad.contrasenas import calcular_hash, verificar
from app.seguridad.sesiones import NOMBRE_COOKIE
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, hoy
from tests.test_canje_primer_acceso import cliente, huella
from tests.test_control_de_intentos import Reloj
from tests.test_traslados import _esperar_bloqueo_consultivo
from tests.utiles_http import API, ORIGEN, iniciar_sesion
from tests.utiles_m2 import contar, filas

ANTERIOR, NUEVA = "contraseña-anterior-1", "una-contraseña-nueva-2"
RUTA = f"{API}/acceso/recuperacion"
OPERADOR = Operador(uuid.uuid4(), "operadora.test")
VERIFICACION = emision.VerificacionDeIdentidad("PRESENCIAL", "ACTA-2026/0117")


def canjear(c, identificador, codigo, contrasena=NUEVA, origen=ORIGEN, ruta=RUTA):
    return c.post(ruta, json={"identificador_acceso": identificador, "codigo": codigo, "contrasena_nueva": contrasena}, headers={"Origin": origen} if origen else {})


def emitir(persona, finalidad="recuperacion"):
    visto = []
    with get_provision_engine().begin() as c:
        emision.emitir_codigo(c, OPERADOR, persona_id=persona, finalidad=finalidad, verificacion=VERIFICACION if finalidad == "recuperacion" else None,
                              presentar=lambda cod, caduca: visto.append(cod))
    return visto[0]


@pytest.fixture()
def mundo():
    """Beto y Clara con contraseña; Ana sin ella. Un código de recuperación para Beto y otro de primer acceso para Ana."""
    with get_owner_engine().begin() as c:
        eq = crear_equipo(c, crear_organizacion(c), "T")
        p = {}
        for nombre, clave in (("beto", ANTERIOR), ("clara", ANTERIOR), ("ana", None)):
            p[nombre] = crear_persona(c, nombre)
            crear_pertenencia(c, p[nombre], eq, "colaborador", desde=hoy() - timedelta(days=1))
            crear_identidad(c, p[nombre], nombre, clave)
    return {"p": p, "codigo": emitir(p["beto"]), "primer": emitir(p["ana"], "primer_acceso")}


def sesiones_de(identificador, n=2):
    """Abre ``n`` sesiones reales de la persona con su contraseña anterior; devuelve los clientes (cada uno con su cookie)."""
    clientes = [cliente(f"198.51.100.{10 + i}") for i in range(n)]
    for c in clientes:
        assert iniciar_sesion(c, identificador, ANTERIOR).status_code == 201 and c.get(f"{API}/sesion").status_code == 200
    return clientes


def estado(identificador):
    return filas("select c.usado_en is not null, c.invalidado_en is not null, c.intentos_fallidos from codigo_unico c join identidad i on i.id = c.identidad_id "
                 "where i.identificador_acceso = :i and c.finalidad = 'recuperacion' order by c.emitido_en", i=identificador)


def vigentes(identificador):
    return filas("select count(*) from sesion s join identidad i on i.id = s.identidad_id where i.identificador_acceso = :i and s.revocada_en is null", i=identificador)[0][0]


@pytest.fixture()
def reloj(monkeypatch):
    r = Reloj()
    monkeypatch.setattr(control, "_ahora", r)
    return r


# ===================================================== recuperación correcta =================================================

def test_la_recuperacion_cambia_la_contrasena_revoca_todas_las_sesiones_y_no_abre_ninguna(mundo):
    previas = sesiones_de("beto", 2)
    antes = filas("select hash_contrasena, contrasena_establecida_en, (select acceso_desactivado_en from persona where id = persona_id) from identidad where identificador_acceso = 'beto'")[0]
    r = canjear(cliente(), "beto", mundo["codigo"])
    assert r.status_code == 204 and r.content == b"" and r.headers["cache-control"] == "no-store" and NOMBRE_COOKIE not in r.headers.get("set-cookie", "")
    assert vigentes("beto") == 0 and all(c.get(f"{API}/sesion").status_code == 401 for c in previas)           # TODAS las sesiones anteriores, en el servidor
    despues = filas("select hash_contrasena, contrasena_establecida_en, (select acceso_desactivado_en from persona where id = persona_id) from identidad where identificador_acceso = 'beto'")[0]
    assert despues[0] != antes[0] and despues[0].startswith("$argon2id$") and verificar(despues[0], NUEVA) and not verificar(despues[0], ANTERIOR)
    assert despues[1] > antes[1] and despues[2] is None                                                          # fecha renovada; el acceso no se tocó
    assert iniciar_sesion(cliente("198.51.100.50"), "beto", ANTERIOR).status_code == 401                         # rechazo con la contraseña anterior
    r2 = iniciar_sesion(cliente("198.51.100.51"), "beto", NUEVA)
    assert r2.status_code == 201 and r2.cookies.get(NOMBRE_COOKIE)                                               # inicio de sesión con la nueva
    assert estado("beto") == [(True, False, 0)] and verificar(filas("select hash_contrasena from identidad where identificador_acceso = 'clara'")[0][0], ANTERIOR)


def test_la_auditoria_de_la_recuperacion_es_de_la_persona_en_fase_canje_distinta_de_la_emision_y_sin_secretos(mundo):
    sesiones_de("beto", 2)
    canjear(cliente(), "beto", mundo["codigo"])
    filas_ = filas("select tipo_autor, autor_persona_id, referencia_provision, objeto_id, propietaria_registro_id, valor_anterior, valor_nuevo "
                   "from auditoria where operacion = 'recuperacion_acceso' order by momento, id")
    assert [f[6]["fase"] for f in filas_].count("emision") == 1 and [f[6]["fase"] for f in filas_].count("canje") == 1
    a = next(f for f in filas_ if f[6]["fase"] == "canje")
    assert a[0] == "persona" and a[1] == a[3] == a[4] == mundo["p"]["beto"] and a[2] is None
    assert a[5] == {"contrasena_establecida": True} and a[6]["finalidad"] == "recuperacion" and a[6]["sesiones_revocadas"] == 2 and a[6]["contrasena_cambiada"] is True
    hashes = [filas("select hash_codigo from codigo_unico where finalidad = 'recuperacion'")[0][0], filas("select hash_contrasena from identidad where identificador_acceso = 'beto'")[0][0]]
    for secreto in (mundo["codigo"], mundo["codigo"].replace("-", ""), *hashes, NUEVA, ANTERIOR, "argon2"):
        assert secreto not in str(a)


def test_un_codigo_de_recuperacion_se_usa_una_sola_vez(mundo):
    assert canjear(cliente(), "beto", mundo["codigo"]).status_code == 204
    r = canjear(cliente(), "beto", mundo["codigo"], "otra-contraseña-nueva-3")
    assert r.status_code == 400 and r.json()["codigo"] == "CODIGO_NO_VALIDO"
    assert iniciar_sesion(cliente("198.51.100.60"), "beto", NUEVA).status_code == 201


# ===================================================== uniformidad (también entre finalidades) ===============================

def test_todas_las_causas_de_codigo_no_valido_dan_la_misma_respuesta_tambien_entre_finalidades(mundo, reloj):
    with get_owner_engine().begin() as c:
        for n in ("caducado", "usado", "invalidado", "desactivado"):
            p = crear_persona(c, n)
            crear_pertenencia(c, p, crear_equipo(c, crear_organizacion(c), n), "colaborador", desde=hoy() - timedelta(days=1))
            crear_identidad(c, p, n, ANTERIOR)
            mundo["p"][n] = p
    cods = {n: emitir(mundo["p"][n]) for n in ("caducado", "usado", "invalidado", "desactivado")}
    with get_owner_engine().begin() as c:
        c.execute(text("alter table codigo_unico disable trigger user"))
        c.execute(text("update codigo_unico set emitido_en = now() - interval '2 hours', caduca_en = now() - interval '1 hour' where identidad_id = "
                       "(select id from identidad where identificador_acceso = 'caducado')"))
        c.execute(text("alter table codigo_unico enable trigger user"))
        c.execute(text("update codigo_unico set usado_en = now() where identidad_id = (select id from identidad where identificador_acceso = 'usado')"))
        c.execute(text("update codigo_unico set invalidado_en = now() where identidad_id = (select id from identidad where identificador_acceso = 'invalidado')"))
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": mundo["p"]["desactivado"]})
    casos = {**{n: ("/acceso/recuperacion", n, cod) for n, cod in cods.items()},
             "inexistente": ("/acceso/recuperacion", "nadie", mundo["codigo"]), "equivocado": ("/acceso/recuperacion", "beto", codigos.formatear(codigos.generar_codigo())),
             "mal_formado": ("/acceso/recuperacion", "beto", "no es un código"), "ajeno": ("/acceso/recuperacion", "clara", mundo["codigo"]),
             "de_primer_acceso": ("/acceso/recuperacion", "ana", mundo["primer"]),                       # identidad sin contraseña: eso es otro proceso
             "sin_contrasena": ("/acceso/recuperacion", "ana", mundo["codigo"])}
    huellas = {n: huella(canjear(cliente(f"198.51.100.{100 + i}"), ident, cod, ruta=API + ruta)) for i, (n, (ruta, ident, cod)) in enumerate(casos.items())}
    assert {h[0] for h in huellas.values()} == {400} and len({str(h) for h in huellas.values()}) == 1, huellas
    # Un código de recuperación no sirve en el primer acceso (ni viceversa): misma respuesta, sin efectos.
    cruzado = huella(canjear(cliente("198.51.100.150"), "beto", mundo["codigo"], ruta=f"{API}/acceso/primer-acceso"))
    assert cruzado == next(iter(huellas.values())) and estado("beto")[0][:2] == (False, False)         # el cruzado no gasta intentos del código ni lo consume


def test_un_acceso_desactivado_no_se_reactiva_ni_cambia_su_contrasena(mundo):
    anterior = filas("select hash_contrasena from identidad where identificador_acceso = 'beto'")[0][0]
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": mundo["p"]["beto"]})
    desactivado = filas("select acceso_desactivado_en from persona where id = :p", p=mundo["p"]["beto"])[0][0]
    r = canjear(cliente(), "beto", mundo["codigo"])
    assert r.status_code == 400 and r.json()["codigo"] == "CODIGO_NO_VALIDO"
    assert filas("select acceso_desactivado_en from persona where id = :p", p=mundo["p"]["beto"])[0][0] == desactivado       # sigue desactivado (CA-254)
    assert filas("select hash_contrasena from identidad where identificador_acceso = 'beto'")[0][0] == anterior and estado("beto") == [(False, False, 0)]
    assert iniciar_sesion(cliente("198.51.100.70"), "beto", ANTERIOR).status_code == 403


# ===================================================== política de contraseña primero (T8.3, confirmada) =====================

def test_la_politica_se_evalua_antes_que_el_codigo_no_consume_nada_ni_revoca_sesiones(mundo):
    previas = sesiones_de("beto", 1)
    valido = canjear(cliente(), "beto", mundo["codigo"], "corta")
    falso = canjear(cliente(), "beto", codigos.formatear(codigos.generar_codigo()), "corta")
    assert valido.status_code == 422 and valido.json()["codigo"] == "CONTRASENA_NO_VALIDA" and huella(valido) == huella(falso)
    assert estado("beto") == [(False, False, 0)] and vigentes("beto") == 1 and previas[0].get(f"{API}/sesion").status_code == 200
    assert contar("control_de_intentos") == 0 and contar("intento_de_origen") == 0                                  # esta rama no prueba ningún código: no gasta intentos
    assert canjear(cliente(), "beto", mundo["codigo"]).status_code == 204


# ===================================================== límites de intentos y 10 fallos =======================================

def test_los_canjes_fallidos_se_limitan_con_m1_t7_y_a_los_10_el_codigo_se_invalida(mundo, reloj):
    c = cliente()
    malo = lambda: codigos.formatear(codigos.generar_codigo())   # noqa: E731
    assert [canjear(c, "beto", malo()).status_code for _ in range(5)] == [400] * 5
    r = canjear(c, "beto", mundo["codigo"])
    assert r.status_code == 429 and r.headers["retry-after"] == "30" and estado("beto") == [(False, False, 5)]
    for _ in range(5):
        r = canjear(c, "beto", malo())
        while r.status_code == 429:
            reloj.avanzar(seconds=int(r.headers["retry-after"]))
            r = canjear(c, "beto", malo())
    assert estado("beto") == [(False, True, 10)]
    reloj.avanzar(hours=2)
    assert canjear(c, "beto", mundo["codigo"]).status_code == 400 and verificar(filas("select hash_contrasena from identidad where identificador_acceso = 'beto'")[0][0], ANTERIOR)


# ===================================================== concurrencia y atomicidad =============================================

def test_dos_o_mas_canjes_simultaneos_dejan_exactamente_uno_efectivo_y_ninguna_sesion_viva(mundo):
    sesiones_de("beto", 2)
    clientes = [cliente(f"198.51.100.{200 + i}") for i in range(8)]
    barrera, resultados = threading.Barrier(8), []

    def tarea(i):
        barrera.wait(timeout=30)
        resultados.append(canjear(clientes[i], "beto", mundo["codigo"], f"contraseña-simultanea-{i}-ok").status_code)
    hilos = [threading.Thread(target=tarea, args=(i,)) for i in range(8)]
    [t.start() for t in hilos]
    [t.join(60) for t in hilos]
    assert Counter(resultados) == {204: 1, 400: 7} and estado("beto") == [(True, False, 0)] and vigentes("beto") == 0
    assert filas("select count(*) from auditoria where operacion = 'recuperacion_acceso' and valor_nuevo ->> 'fase' = 'canje'") == [(1,)]


def test_si_falla_la_auditoria_no_se_consume_el_codigo_ni_se_cambia_la_contrasena_ni_se_revocan_las_sesiones(mundo):
    previas = sesiones_de("beto", 2)
    with get_owner_engine().begin() as c:
        c.execute(text("alter table auditoria add constraint zz_falla check (valor_nuevo ->> 'fase' is distinct from 'canje') not valid"))
    try:
        r = canjear(cliente(), "beto", mundo["codigo"])
    finally:
        with get_owner_engine().begin() as c:
            c.execute(text("alter table auditoria drop constraint zz_falla"))
    assert r.status_code == 500 and estado("beto") == [(False, False, 0)] and vigentes("beto") == 2
    assert all(c.get(f"{API}/sesion").status_code == 200 for c in previas)                                       # nada se revocó a medias
    assert verificar(filas("select hash_contrasena from identidad where identificador_acceso = 'beto'")[0][0], ANTERIOR)
    assert canjear(cliente("198.51.100.77"), "beto", mundo["codigo"]).status_code == 204                       # y el código sigue siendo válido


def test_la_desactivacion_que_toma_el_bloqueo_primero_deja_la_recuperacion_sin_efecto(mundo):
    resultado, beto = {}, mundo["p"]["beto"]
    with get_provision_engine().connect() as c:
        desactivar_acceso(c, OPERADOR, persona_id=beto, motivo="Baja")
        hilo = threading.Thread(target=lambda: resultado.update(r=canjear(cliente(), "beto", mundo["codigo"])))
        hilo.start()
        assert _esperar_bloqueo_consultivo(), "el canje debía esperar el bloqueo de la persona"
        c.commit()
    hilo.join(30)
    assert resultado["r"].status_code == 400 and estado("beto") == [(False, True, 0)]
    assert filas("select acceso_desactivado_en is not null from persona where id = :p", p=beto) == [(True,)]
    assert verificar(filas("select hash_contrasena from identidad where identificador_acceso = 'beto'")[0][0], ANTERIOR)


# ===================================================== PostgreSQL: función y permisos ========================================

def test_la_funcion_de_recuperacion_tiene_el_mismo_blindaje_que_la_de_primer_acceso(mundo):
    for nombre in ("canjear_codigo_primer_acceso", "canjear_codigo_recuperacion"):
        (f,) = filas("select p.prosecdef, p.proconfig, r.rolsuper, r.rolcreaterole, r.rolcreatedb, r.rolreplication, r.rolbypassrls, p.prosrc "
                     "from pg_proc p join pg_roles r on r.oid = p.proowner where p.proname = :n", n=nombre)
        assert f[0] is True and f[1] == ["search_path=pg_catalog, pg_temp"] and not any(f[2:7]) and "format(" not in f[7].lower()
        assert "EXECUTE" not in f[7].upper().replace("FOR UPDATE", "")
        firma = f"public.{nombre}(text, text, text)"
        assert filas("select has_function_privilege(:r, :f, 'EXECUTE')", r=get_settings().app_db_role, f=firma) == [(True,)]
        assert filas("select has_function_privilege(:r, :f, 'EXECUTE')", r=get_settings().provision_db_role, f=firma) == [(False,)]
        assert filas("select has_function_privilege('public', :f, 'EXECUTE')", f=firma) == [(False,)]
    for sentencia in ("update identidad set hash_contrasena = 'x'", "update codigo_unico set usado_en = now()"):
        with pytest.raises(Exception) as e, get_engine().begin() as c:
            c.execute(text(sentencia))
        assert "permiso denegado" in str(e.value) or "42501" in str(e.value), sentencia


def test_la_funcion_no_toca_otra_identidad_ni_acepta_parametros_invalidos(mundo):
    llamar = "select public.canjear_codigo_recuperacion(:i, :hc, :hp)"
    argon = calcular_hash("una-contraseña-nueva-2")
    bueno = codigos.hash_de_codigo(mundo["codigo"])
    for i, hc, hp in (("beto", bueno, "no-es-argon2"), ("beto", "no-es-hex", argon), (None, bueno, argon), ("beto", None, argon), ("clara", bueno, argon), ("ana", bueno, argon),
                      ("nadie", bueno, argon)):
        with get_engine().begin() as c:
            assert c.execute(text(llamar), {"i": i, "hc": hc, "hp": hp}).scalar_one() is None
    assert verificar(filas("select hash_contrasena from identidad where identificador_acceso = 'beto'")[0][0], ANTERIOR)
    assert verificar(filas("select hash_contrasena from identidad where identificador_acceso = 'clara'")[0][0], ANTERIOR)
    assert filas("select hash_contrasena from identidad where identificador_acceso = 'ana'") == [(None,)]


def test_origen_y_forma_se_verifican_sin_contar_intentos(mundo):
    assert canjear(cliente(), "beto", mundo["codigo"], origen="https://evil.example").status_code == 400
    assert canjear(cliente(), "beto", mundo["codigo"], origen=None).status_code == 400
    r = cliente().post(RUTA, json={"identificador_acceso": "beto", "codigo": mundo["codigo"], "contrasena_nueva": NUEVA, "extra": 1}, headers={"Origin": ORIGEN})
    assert r.status_code == 400 and contar("control_de_intentos") == 0 and estado("beto") == [(False, False, 0)]
