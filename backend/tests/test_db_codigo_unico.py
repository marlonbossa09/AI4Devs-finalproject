"""M1-T8.1 — la base de datos de los códigos de un solo uso: migración 0014, invariantes y privilegios (PostgreSQL real, cada rol).

Pruebas esenciales: un solo código pendiente, finalidad según el estado y nunca para un acceso desactivado, uso único y caducidad con el reloj de
PostgreSQL, intentos que invalidan a los 10, inmutabilidad, retención de 30 días, permisos mínimos (nadie lee el hash), ``contrasena_establecida_en``,
migración desde cero / con datos / en reversión y el servicio interno de registro (incluida una carrera de emisiones). Destructivas solo sobre ``smartwork_test``.
"""

import threading
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine, get_owner_engine, get_provision_engine
from app.provision import codigos as servicio
from app.seguridad import codigos
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, hoy
from tests.test_db_traslados import transaccion
from tests.utiles_m2 import contar, filas

RAIZ = Path(__file__).resolve().parent.parent
APP, PROV, OWNER = get_engine, get_provision_engine, get_owner_engine
EMISOR = "operador:operadora.uno|invocacion:" + str(uuid.uuid4())


def h():
    return codigos.hash_de_octetos(codigos.generar_octetos())


@pytest.fixture()
def mundo():
    """Ana sin contraseña (primer acceso pendiente) y Beto con contraseña (recuperación posible)."""
    with get_owner_engine().begin() as c:
        eq = crear_equipo(c, crear_organizacion(c), "T")
        p = {}
        for nombre, clave in (("ana", None), ("beto", "contraseña-de-prueba-123")):
            p[nombre] = crear_persona(c, nombre)
            crear_pertenencia(c, p[nombre], eq, "colaborador", desde=hoy())
            crear_identidad(c, p[nombre], nombre, clave)
        ids = {r.persona_id: r.id for r in c.execute(text("select id, persona_id from identidad"))}
    return {"ana": ids[p["ana"]], "beto": ids[p["beto"]], "pana": p["ana"], "pbeto": p["beto"]}


def nuevo(identidad, finalidad="primer_acceso", motor=OWNER, hash_=None, caduca="clock_timestamp() + interval '10 minutes'"):
    return transaccion(motor(), (f"insert into codigo_unico (identidad_id, finalidad, hash_codigo, caduca_en, emitido_por) "
                                 f"values (:i, :f, :h, {caduca}, :e)", {"i": identidad, "f": finalidad, "h": hash_ or h(), "e": EMISOR}))


def estado(identidad):
    return filas("select usado_en is not null, invalidado_en is not null, intentos_fallidos from codigo_unico where identidad_id = :i order by emitido_en",
                 i=identidad)


def un_codigo(identidad, finalidad="primer_acceso"):
    assert nuevo(identidad, finalidad) == ("ok", None)
    return filas("select id from codigo_unico where identidad_id = :i and usado_en is null and invalidado_en is null", i=identidad)[0][0]


# ===================================================== contrasena_establecida_en (D8) ========================================

def test_la_fecha_de_contrasena_la_mantiene_la_base_y_nadie_la_fija_a_mano(mundo):
    estable = lambda i: filas("select contrasena_establecida_en is not null, hash_contrasena is not null from identidad where id = :i", i=i)[0]   # noqa: E731
    assert estable(mundo["ana"]) == (False, False) and estable(mundo["beto"]) == (True, True)
    with get_owner_engine().begin() as c:
        c.execute(text("update identidad set hash_contrasena = 'x' where id = :i"), {"i": mundo["ana"]})
    assert estable(mundo["ana"]) == (True, True)
    assert transaccion(OWNER(), ("update identidad set hash_contrasena = null where id = :i", {"i": mundo["ana"]})) == ("ok", None)
    assert estable(mundo["ana"]) == (False, False)                                          # vaciar el hash vacía la fecha
    with get_owner_engine().begin() as c:                                                   # intentar fijarla o falsearla no sirve
        c.execute(text("update identidad set contrasena_establecida_en = now() - interval '9 days' where id = :i"), {"i": mundo["beto"]})
    assert filas("select now() - contrasena_establecida_en < interval '1 hour' from identidad where id = :i", i=mundo["beto"]) == [(True,)]
    transaccion(OWNER(), ("update identidad set contrasena_establecida_en = now() where id = :i", {"i": mundo["ana"]}))
    assert estable(mundo["ana"]) == (False, False)                                          # sin hash no hay fecha, se pida lo que se pida


# ===================================================== emisión: estado, DD-05 y un solo pendiente ============================

def test_la_finalidad_debe_corresponder_al_estado_de_la_contrasena(mundo):
    assert nuevo(mundo["beto"], "primer_acceso")[0] == "23514"                              # ya tiene contraseña
    assert nuevo(mundo["ana"], "recuperacion")[0] == "23514"                                # aún no tiene contraseña
    assert nuevo(mundo["ana"], "primer_acceso") == ("ok", None) and nuevo(mundo["beto"], "recuperacion") == ("ok", None)


def test_nunca_se_emite_un_codigo_para_un_acceso_desactivado(mundo):
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now()"))
    assert nuevo(mundo["ana"], "primer_acceso")[0] == "23514" and nuevo(mundo["beto"], "recuperacion")[0] == "23514"
    assert contar("codigo_unico") == 0


def test_como_mucho_un_codigo_pendiente_por_identidad_y_finalidad(mundo):
    assert nuevo(mundo["ana"]) == ("ok", None)
    assert nuevo(mundo["ana"])[0] == "23505"                                                # otro pendiente de lo mismo: no
    assert nuevo(mundo["beto"], "recuperacion") == ("ok", None)                             # otra identidad: sí
    with get_owner_engine().begin() as c:
        c.execute(text("update codigo_unico set invalidado_en = now() where identidad_id = :i"), {"i": mundo["ana"]})
    assert nuevo(mundo["ana"]) == ("ok", None)                                              # invalidado el anterior, ya se puede emitir otro


def test_un_codigo_nace_limpio_y_la_base_fija_su_emision_y_acota_su_vigencia(mundo):
    with get_owner_engine().begin() as c:
        c.execute(text("insert into codigo_unico (identidad_id, finalidad, hash_codigo, emitido_en, caduca_en, usado_en, intentos_fallidos, emitido_por) "
                       "values (:i, 'primer_acceso', :h, now() - interval '5 days', now() + interval '1 hour', now(), 7, :e)"),
                  {"i": mundo["ana"], "h": h(), "e": EMISOR})
    assert estado(mundo["ana"]) == [(False, False, 0)]
    assert filas("select clock_timestamp() - emitido_en < interval '1 minute' from codigo_unico") == [(True,)]
    assert nuevo(mundo["beto"], "recuperacion", caduca="clock_timestamp() + interval '25 hours'")[0] == "23514"     # más de 24 h
    assert nuevo(mundo["beto"], "recuperacion", caduca="clock_timestamp() - interval '1 minute'")[0] == "23514"     # ya caducado al emitirse


@pytest.mark.parametrize("hash_", ["no-es-hex", "A" * 64, "a" * 63])
def test_solo_se_guarda_un_hmac_hexadecimal_nunca_un_codigo(mundo, hash_):
    assert nuevo(mundo["ana"], hash_=hash_)[0] == "23514"


# ===================================================== uso único, caducidad, invalidación, intentos ==========================

def test_un_codigo_se_usa_una_vez_con_la_hora_de_la_base_y_despues_no_cambia(mundo):
    un_codigo(mundo["ana"])
    assert transaccion(OWNER(), ("update codigo_unico set usado_en = now() - interval '3 days'", {})) == ("ok", None)   # la fecha propuesta se ignora
    assert filas("select clock_timestamp() - usado_en < interval '1 minute' from codigo_unico") == [(True,)]
    for sentencia in ("update codigo_unico set usado_en = clock_timestamp()", "update codigo_unico set usado_en = null",
                      "update codigo_unico set invalidado_en = now()", "update codigo_unico set intentos_fallidos = 1"):
        assert transaccion(OWNER(), (sentencia, {}))[0] == "23514", sentencia          # un código consumido no se reutiliza ni se reabre


def test_el_uso_condicional_deja_exactamente_un_canje_efectivo_aunque_sean_simultaneos(mundo):
    un_codigo(mundo["ana"])
    resultados = []
    barrera = threading.Barrier(8)

    def canjear():
        barrera.wait()
        with get_owner_engine().begin() as c:
            resultados.append(c.execute(text("update codigo_unico set usado_en = clock_timestamp() "
                                             "where usado_en is null and invalidado_en is null and caduca_en > clock_timestamp()")).rowcount)
    hilos = [threading.Thread(target=canjear) for _ in range(8)]
    [t.start() for t in hilos]
    [t.join(30) for t in hilos]
    assert sorted(resultados) == [0] * 7 + [1] and estado(mundo["ana"]) == [(True, False, 0)]


def test_un_codigo_invalidado_o_caducado_no_se_puede_usar(mundo):
    un_codigo(mundo["ana"])
    with get_owner_engine().begin() as c:
        c.execute(text("update codigo_unico set invalidado_en = now()"))
    assert transaccion(OWNER(), ("update codigo_unico set usado_en = now()", {}))[0] == "23514"
    assert nuevo(mundo["beto"], "recuperacion", caduca="clock_timestamp() + interval '100 milliseconds'") == ("ok", None)
    with get_owner_engine().begin() as c:
        c.execute(text("select pg_sleep(0.3)"))
    assert transaccion(OWNER(), ("update codigo_unico set usado_en = now() where identidad_id = :i", {"i": mundo["beto"]}))[0] == "23514"   # caducado


def test_a_los_10_intentos_fallidos_el_codigo_se_invalida_solo_y_los_intentos_solo_crecen_de_uno_en_uno(mundo):
    un_codigo(mundo["ana"])
    suma = "update codigo_unico set intentos_fallidos = intentos_fallidos + 1"
    for _ in range(9):
        assert transaccion(OWNER(), (suma, {})) == ("ok", None)
    assert estado(mundo["ana"]) == [(False, False, 9)]
    assert transaccion(OWNER(), ("update codigo_unico set intentos_fallidos = 11", {}))[0] == "23514"       # salto
    assert transaccion(OWNER(), ("update codigo_unico set intentos_fallidos = 3", {}))[0] == "23514"        # retroceso
    assert transaccion(OWNER(), (suma, {})) == ("ok", None)
    assert estado(mundo["ana"]) == [(False, True, 10)]                                                       # décimo fallo: invalidado
    assert transaccion(OWNER(), (suma, {}))[0] == "23514"


def test_el_hash_la_identidad_la_finalidad_y_la_vigencia_no_se_modifican_jamas(mundo):
    un_codigo(mundo["ana"])
    for sentencia in (f"update codigo_unico set hash_codigo = '{'b' * 64}'", f"update codigo_unico set identidad_id = '{mundo['beto']}'",
                      "update codigo_unico set finalidad = 'recuperacion'", "update codigo_unico set caduca_en = caduca_en + interval '1 hour'",
                      "update codigo_unico set emitido_en = emitido_en - interval '1 hour'", "update codigo_unico set emitido_por = 'otro'"):
        assert transaccion(OWNER(), (sentencia, {}))[0] == "23514", sentencia


def test_un_codigo_solo_se_borra_pasados_30_dias_desde_que_termino(mundo):
    un_codigo(mundo["ana"])
    assert transaccion(OWNER(), ("delete from codigo_unico", {}))[0] == "23514"                              # pendiente: no
    with get_owner_engine().begin() as c:
        c.execute(text("update codigo_unico set usado_en = now()"))
    assert transaccion(OWNER(), ("delete from codigo_unico", {}))[0] == "23514"                              # recién usado: no
    with get_owner_engine().begin() as c:                                                                     # envejecer una fila exige saltarse los disparadores
        c.execute(text("alter table codigo_unico disable trigger user"))
        c.execute(text("update codigo_unico set emitido_en = now() - interval '60 days', usado_en = now() - interval '40 days', caduca_en = now() - interval '59 days'"))
        c.execute(text("alter table codigo_unico enable trigger user"))
    assert transaccion(OWNER(), ("delete from codigo_unico", {})) == ("ok", None)


# ===================================================== privilegios mínimos ===================================================

def test_la_aplicacion_no_tiene_ningun_permiso_sobre_los_codigos(mundo):
    un_codigo(mundo["ana"])
    for sentencia in ("select 1 from codigo_unico", "select id from codigo_unico", "select hash_codigo from codigo_unico", "delete from codigo_unico",
                      "update codigo_unico set intentos_fallidos = 1", "update codigo_unico set usado_en = now()", "truncate codigo_unico"):
        assert transaccion(APP(), (sentencia, {}))[0] == "42501", sentencia
    assert nuevo(mundo["ana"], motor=APP)[0] == "42501"                                     # y no puede emitir
    assert transaccion(APP(), ("update identidad set hash_contrasena = 'x'", {}))[0] == "42501"


def test_la_provision_emite_e_invalida_pero_nunca_lee_el_hash_ni_usa_un_codigo(mundo):
    assert nuevo(mundo["ana"], motor=PROV) == ("ok", None)
    assert transaccion(PROV(), ("select id, identidad_id, finalidad, emitido_en, caduca_en, usado_en, invalidado_en, intentos_fallidos, emitido_por from codigo_unico", {})) == ("ok", None)
    for sentencia in ("select hash_codigo from codigo_unico", "select * from codigo_unico", "update codigo_unico set usado_en = now()",
                      "update codigo_unico set intentos_fallidos = 1", "update codigo_unico set hash_codigo = 'x'", "truncate codigo_unico"):
        assert transaccion(PROV(), (sentencia, {}))[0] == "42501", sentencia
    # Desde la migración 0017 puede BORRAR (solo la purga lo usa), pero la base sigue protegiendo los pendientes y los recientes (ver test_purga_de_codigos).
    assert transaccion(PROV(), ("delete from codigo_unico", {}))[0] == "23514"
    assert transaccion(PROV(), ("insert into codigo_unico (identidad_id, finalidad, hash_codigo, caduca_en, emitido_por, emitido_en) "
                                "values (:i, 'recuperacion', :h, now() + interval '1 hour', 'x', now() - interval '1 day')", {"i": mundo["beto"], "h": h()}))[0] == "42501"
    assert transaccion(PROV(), ("update codigo_unico set invalidado_en = now()", {})) == ("ok", None)


def test_la_provision_lee_si_hay_contrasena_pero_no_la_da_ni_la_lee(mundo):
    assert transaccion(PROV(), ("select id, persona_id, identificador_acceso, contrasena_establecida_en from identidad", {})) == ("ok", None)
    assert transaccion(PROV(), ("select hash_contrasena from identidad", {}))[0] == "42501"
    insertar = "insert into identidad (persona_id, identificador_acceso, hash_contrasena) values (:p, :i, :h)"
    nueva = crear_persona_suelta()
    assert transaccion(PROV(), (insertar, {"p": nueva, "i": "con.hash", "h": "x"}))[0] == "23514"            # la provisión no da contraseñas
    assert transaccion(PROV(), (insertar, {"p": nueva, "i": "sin.hash", "h": None})) == ("ok", None)
    assert transaccion(PROV(), ("insert into identidad (persona_id, identificador_acceso, contrasena_establecida_en) values (:p, 'y', now())",
                                {"p": crear_persona_suelta()}))[0] == "42501"


def crear_persona_suelta():
    with get_owner_engine().begin() as c:
        return crear_persona(c, "suelta")


# ===================================================== servicio interno de registro ==========================================

def registrar(identidad, finalidad="primer_acceso", **kw):
    with get_provision_engine().begin() as c:
        return servicio.registrar_codigo(c, identidad_id=identidad, finalidad=finalidad, hash_codigo=h(), emitido_por=EMISOR, **kw)


def test_registrar_un_codigo_invalida_el_pendiente_anterior_y_fija_la_vigencia_con_el_reloj_de_la_base(mundo):
    primero = registrar(mundo["ana"])
    segundo = registrar(mundo["ana"], validez_segundos=60)
    assert primero.id != segundo.id and estado(mundo["ana"]) == [(False, True, 0), (False, False, 0)]
    assert filas("select caduca_en - emitido_en between interval '59 seconds' and interval '61 seconds' from codigo_unico where id = :i", i=segundo.id) == [(True,)]
    por_defecto = registrar(mundo["beto"], "recuperacion")
    assert filas("select caduca_en - emitido_en between interval '9 minutes 59 seconds' and interval '10 minutes 1 second' from codigo_unico where id = :i",
                 i=por_defecto.id) == [(True,)] and get_settings().code_validity_minutes == 10


def test_el_servicio_respeta_el_estado_la_desactivacion_y_el_techo_de_vigencia(mundo):
    from sqlalchemy.exc import DBAPIError
    with pytest.raises(DBAPIError):
        registrar(mundo["ana"], "recuperacion")
    with pytest.raises(DBAPIError):
        registrar(mundo["ana"], validez_segundos=25 * 3600)
    with pytest.raises(ValueError):
        registrar(mundo["ana"], "otra")
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now()"))
    with pytest.raises(DBAPIError):
        registrar(mundo["ana"])
    assert contar("codigo_unico") == 0


def test_emisiones_simultaneas_de_lo_mismo_se_serializan_y_dejan_un_solo_codigo_vigente(mundo):
    errores, barrera = [], threading.Barrier(6)

    def emitir():
        barrera.wait()
        try:
            registrar(mundo["ana"])
        except Exception as e:  # noqa: BLE001
            errores.append(e)
    hilos = [threading.Thread(target=emitir) for _ in range(6)]
    [t.start() for t in hilos]
    [t.join(60) for t in hilos]
    assert errores == [] and sorted(estado(mundo["ana"])) == sorted([(False, True, 0)] * 5 + [(False, False, 0)])


# ===================================================== migración: desde cero, con datos y en reversión =======================

def test_la_migracion_se_aplica_con_datos_existentes_y_se_revierte_sin_alterarlos(mundo):
    cfg = Config(str(RAIZ / "alembic.ini"))
    assert filas("select version_num >= '0014' from alembic_version") == [(True,)]          # (no se fija a la última: cada migración nueva la movería)
    antes = (filas("select persona_id, identificador_acceso, hash_contrasena from identidad order by identificador_acceso"), filas("select * from persona order by id"))
    command.downgrade(cfg, "0013")
    try:
        assert filas("select to_regclass('public.codigo_unico') is null") == [(True,)]
        assert filas("select count(*) from information_schema.columns where table_name = 'identidad' and column_name = 'contrasena_establecida_en'") == [(0,)]
        assert transaccion(PROV(), ("select hash_contrasena from identidad", {}))[0] == "42501"          # el endurecimiento de 0012 sigue
        assert (filas("select persona_id, identificador_acceso, hash_contrasena from identidad order by identificador_acceso"), filas("select * from persona order by id")) == antes
    finally:
        command.upgrade(cfg, "head")
    # Con datos: ana (sin contraseña) sigue sin fecha y beto (con contraseña) la recibe en la migración.
    assert filas("select identificador_acceso, contrasena_establecida_en is not null from identidad order by identificador_acceso") == [("ana", False), ("beto", True)]
    assert filas("select persona_id, identificador_acceso, hash_contrasena from identidad order by identificador_acceso") == antes[0]
    assert contar("codigo_unico") == 0 and nuevo(mundo["ana"]) == ("ok", None)


def test_el_esquema_no_guarda_codigos_en_claro_y_el_hash_no_se_expone_a_ningun_rol_distinto_del_propietario():
    columnas = {f[0] for f in filas("select column_name from information_schema.columns where table_name = 'codigo_unico'")}
    assert "hash_codigo" in columnas and not columnas & {"codigo", "codigo_en_claro", "secreto", "token", "contrasena"}
    for rol in (get_settings().app_db_role, get_settings().provision_db_role):
        assert filas("select has_column_privilege(:r, 'codigo_unico', 'hash_codigo', 'SELECT')", r=rol) == [(False,)]
        assert filas("select has_column_privilege(:r, 'codigo_unico', 'hash_codigo', 'UPDATE')", r=rol) == [(False,)]
