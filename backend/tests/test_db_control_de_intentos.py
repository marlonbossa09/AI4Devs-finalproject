"""M1-T7 — la base de datos del control de intentos y de los eventos de autenticación: migración 0013 y sus protecciones.

Intentos REALES con cada rol (aplicación, provisión y propietario) sobre PostgreSQL. Lo que se prueba:

- los permisos MÍNIMOS de cada rol, tabla a tabla y columna a columna, y que nada cambia sobre ``identidad``, ``persona`` ni ``sesion``;
- que los contadores de las personas y los de las personas operadoras están separados (cada rol solo ve los suyos);
- que los eventos son de solo anexado (ningún UPDATE; DELETE solo pasados 30 días, para cualquier rol) y que cada rol solo escribe
  los eventos que le corresponden;
- las restricciones de forma (claves HMAC en hexadecimal, tipos, ámbitos);
- instalación desde cero, aplicación sobre datos existentes sin alterarlos, y reversión.

Las pruebas destructivas corren solo sobre ``smartwork_test``.
"""

import re
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.db import get_engine, get_owner_engine, get_provision_engine
from app.seguridad import control_de_intentos as control
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, hoy
from tests.test_db_traslados import transaccion
from tests.utiles_m2 import contar, filas

RAIZ = Path(__file__).resolve().parent.parent
APP, PROV, OWNER = get_engine, get_provision_engine, get_owner_engine
K = "a" * 64
K2 = "b" * 64
COLUMNAS_EVENTO = "tipo, ambito, persona_id, sesion_id, clave_cuenta, clave_origen, detalle"


@pytest.fixture()
def persona():
    with get_owner_engine().begin() as c:
        p = crear_persona(c, "P")
        crear_pertenencia(c, p, crear_equipo(c, crear_organizacion(c), "T"), "colaborador", desde=hoy())
        crear_identidad(c, p, "p", "contraseña-de-prueba-123")
    return p


def evento(tipo="inicio_fallido", ambito="persona", extra="", valores=""):
    return (f"insert into evento_autenticacion (tipo, ambito{extra}) values ('{tipo}', '{ambito}'{valores})", {})


def evento_viejo(dias, tipo="inicio_fallido"):
    with get_owner_engine().begin() as c:
        c.execute(text("insert into evento_autenticacion (tipo, ambito, ocurrido_en) values (:t, 'persona', now() - make_interval(days => :d))"),
                  {"t": tipo, "d": dias})


# ===================================================== contadores de las personas (HTTP): solo la aplicación ================

def test_la_aplicacion_gestiona_los_contadores_de_las_personas():
    assert transaccion(APP(), ("insert into control_de_intentos (clave, intentos, ultimo_intento_en) values (:k, 1, now())", {"k": K})) == ("ok", None)
    assert transaccion(APP(), ("select clave, intentos from control_de_intentos", {})) == ("ok", None)
    assert transaccion(APP(), ("update control_de_intentos set intentos = 2, permitido_desde = now(), ultimo_intento_en = now() where clave = :k", {"k": K})) == ("ok", None)
    assert transaccion(APP(), ("delete from control_de_intentos where clave = :k", {"k": K})) == ("ok", None)


@pytest.mark.parametrize("sentencia", ["update control_de_intentos set clave = 'c' where clave = :k", "truncate control_de_intentos"])
def test_la_aplicacion_no_cambia_la_clave_ni_vacia_la_tabla(sentencia):
    with get_owner_engine().begin() as c:
        c.execute(text("insert into control_de_intentos (clave, intentos, ultimo_intento_en) values (:k, 1, now())"), {"k": K})
    assert transaccion(APP(), (sentencia, {"k": K}))[0] == "42501"


def test_la_provision_no_toca_los_contadores_de_las_personas():
    for sentencia in ("select 1 from control_de_intentos", "insert into control_de_intentos (clave, intentos, ultimo_intento_en) values ('%s', 1, now())" % K,
                      "delete from control_de_intentos", "select 1 from intento_de_origen", "delete from intento_de_origen"):
        assert transaccion(PROV(), (sentencia, {}))[0] == "42501", sentencia


def test_la_aplicacion_gestiona_las_reservas_de_origen_pero_no_las_edita():
    assert transaccion(APP(), ("insert into intento_de_origen (clave_origen, en) values (:k, now())", {"k": K})) == ("ok", None)
    assert transaccion(APP(), ("select clave_origen, en from intento_de_origen", {})) == ("ok", None)
    assert transaccion(APP(), ("delete from intento_de_origen", {})) == ("ok", None)
    with get_owner_engine().begin() as c:
        c.execute(text("insert into intento_de_origen (clave_origen, en) values (:k, now())"), {"k": K})
    assert transaccion(APP(), ("update intento_de_origen set en = now() - interval '1 day'", {}))[0] == "42501"


# ===================================================== contadores de las personas operadoras: solo la provisión =============

def test_la_provision_gestiona_los_contadores_de_la_persona_operadora_y_la_aplicacion_no_los_ve():
    assert transaccion(PROV(), ("insert into control_de_intentos_operador (clave, intentos, ultimo_intento_en) values (:k, 1, now())", {"k": K})) == ("ok", None)
    assert transaccion(PROV(), ("update control_de_intentos_operador set intentos = 2, permitido_desde = now() where clave = :k", {"k": K})) == ("ok", None)
    assert transaccion(PROV(), ("select clave from control_de_intentos_operador", {})) == ("ok", None)
    assert transaccion(PROV(), ("delete from control_de_intentos_operador", {})) == ("ok", None)
    for sentencia in ("select 1 from control_de_intentos_operador", "delete from control_de_intentos_operador",
                      "insert into control_de_intentos_operador (clave, intentos, ultimo_intento_en) values ('%s', 1, now())" % K):
        assert transaccion(APP(), (sentencia, {}))[0] == "42501", sentencia


def test_la_provision_no_cambia_la_clave_de_un_contador_de_operadora():
    with get_owner_engine().begin() as c:
        c.execute(text("insert into control_de_intentos_operador (clave, intentos, ultimo_intento_en) values (:k, 1, now())"), {"k": K})
    assert transaccion(PROV(), ("update control_de_intentos_operador set clave = :n where clave = :k", {"k": K, "n": K2}))[0] == "42501"


# ===================================================== eventos: quién escribe y quién lee ===================================

def test_la_aplicacion_solo_inserta_eventos_de_personas_y_no_los_lee_ni_los_cambia(persona):
    assert transaccion(APP(), evento("inicio_correcto")) == ("ok", None)
    for sentencia in ("select * from evento_autenticacion", "select clave_cuenta from evento_autenticacion", "update evento_autenticacion set tipo = 'inicio_correcto'",
                      "delete from evento_autenticacion", "truncate evento_autenticacion"):
        assert transaccion(APP(), (sentencia, {}))[0] == "42501", sentencia


def test_la_aplicacion_no_puede_fijar_el_identificador_ni_la_fecha_de_un_evento():
    """Sin permiso sobre ``id`` ni ``ocurrido_en``: no se puede fechar un evento en el pasado para esquivar la retención ni falsear su antigüedad."""
    assert transaccion(APP(), ("insert into evento_autenticacion (tipo, ambito, ocurrido_en) values ('inicio_fallido', 'persona', now() - interval '60 days')", {}))[0] == "42501"
    assert transaccion(APP(), (f"insert into evento_autenticacion (id, tipo, ambito) values ('{uuid.uuid4()}', 'inicio_fallido', 'persona')", {}))[0] == "42501"


@pytest.mark.parametrize("tipo, ambito", [("inicio_fallido", "operador"), ("inicio_correcto", "operador"), ("espera_aplicada", "operador")])
def test_la_aplicacion_no_registra_eventos_de_la_persona_operadora(tipo, ambito):
    assert transaccion(APP(), evento(tipo, ambito))[0] == "23514"


def test_la_aplicacion_no_registra_la_revocacion_por_desactivacion(persona):
    assert transaccion(APP(), evento("revocacion_por_desactivacion", "persona", ", persona_id", f", '{persona}'"))[0] == "23514"


@pytest.mark.parametrize("tipo", ["inicio_correcto", "inicio_fallido", "espera_aplicada"])
def test_la_provision_registra_eventos_de_la_persona_operadora(tipo):
    assert transaccion(PROV(), evento(tipo, "operador")) == ("ok", None)


def test_la_provision_registra_la_revocacion_por_desactivacion_y_nada_mas_de_las_personas(persona):
    assert transaccion(PROV(), evento("revocacion_por_desactivacion", "persona", ", persona_id", f", '{persona}'")) == ("ok", None)
    for tipo in ("inicio_correcto", "inicio_fallido", "espera_aplicada", "cierre_sesion", "acceso_desactivado_en_inicio"):
        assert transaccion(PROV(), evento(tipo, "persona"))[0] == "23514", tipo
    for tipo in ("cierre_sesion", "acceso_desactivado_en_inicio", "revocacion_por_desactivacion"):
        assert transaccion(PROV(), evento(tipo, "operador"))[0] == "23514", tipo


def test_la_provision_solo_lee_el_identificador_y_la_fecha_de_los_eventos():
    with get_owner_engine().begin() as c:
        c.execute(text("insert into evento_autenticacion (tipo, ambito, clave_cuenta, detalle) values ('inicio_fallido', 'persona', :k, '{\"motivo\": \"x\"}')"), {"k": K})
    assert transaccion(PROV(), ("select id, ocurrido_en from evento_autenticacion", {})) == ("ok", None)
    for columna in ("clave_cuenta", "clave_origen", "detalle", "persona_id", "tipo"):
        assert transaccion(PROV(), (f"select {columna} from evento_autenticacion", {}))[0] == "42501", columna
    assert transaccion(PROV(), ("update evento_autenticacion set tipo = 'inicio_correcto'", {}))[0] == "42501"


def test_la_provision_no_puede_fijar_la_fecha_de_un_evento():
    assert transaccion(PROV(), ("insert into evento_autenticacion (tipo, ambito, ocurrido_en) values ('inicio_fallido', 'operador', now() - interval '99 days')", {}))[0] == "42501"


# ===================================================== eventos de solo anexado y retención de 30 días ======================

def test_ningun_rol_actualiza_un_evento_ni_el_propietario():
    with get_owner_engine().begin() as c:
        c.execute(text("insert into evento_autenticacion (tipo, ambito) values ('inicio_fallido', 'persona')"))
    assert transaccion(OWNER(), ("update evento_autenticacion set tipo = 'inicio_correcto'", {}))[0] == "23000"
    assert transaccion(OWNER(), ("update evento_autenticacion set detalle = '{}'::jsonb", {}))[0] == "23000"
    assert filas("select tipo from evento_autenticacion") == [("inicio_fallido",)]


def test_ni_siquiera_un_evento_de_mas_de_30_dias_se_actualiza():
    """Pasados los 30 días solo cambia la retención (se puede borrar); el contenido nunca se reescribe, ni por el propietario."""
    evento_viejo(40)
    assert transaccion(OWNER(), ("update evento_autenticacion set detalle = '{\"x\": 1}'::jsonb", {}))[0] == "23000"
    assert transaccion(OWNER(), ("update evento_autenticacion set tipo = 'inicio_correcto'", {}))[0] == "23000"
    assert filas("select tipo, detalle from evento_autenticacion") == [("inicio_fallido", None)]


def test_un_evento_de_menos_de_30_dias_no_se_borra_ni_por_el_propietario():
    evento_viejo(0)
    evento_viejo(29)
    assert transaccion(OWNER(), ("delete from evento_autenticacion", {}))[0] == "23000"
    assert transaccion(OWNER(), ("delete from evento_autenticacion where ocurrido_en < now() - interval '1 day'", {}))[0] == "23000"
    assert contar("evento_autenticacion") == 2


def test_un_evento_de_mas_de_30_dias_si_se_puede_purgar():
    evento_viejo(31)
    evento_viejo(90)
    assert transaccion(OWNER(), ("delete from evento_autenticacion", {})) == ("ok", None)
    assert contar("evento_autenticacion") == 0


def test_la_provision_purga_solo_lo_de_mas_de_30_dias_y_la_base_lo_comprueba_por_su_cuenta():
    evento_viejo(40)
    evento_viejo(10)
    assert transaccion(PROV(), ("delete from evento_autenticacion where ocurrido_en < now() + interval '100 days'", {}))[0] == "23000"   # intenta incluir lo reciente
    assert contar("evento_autenticacion") == 2
    assert transaccion(PROV(), ("delete from evento_autenticacion where ocurrido_en < now() - interval '30 days'", {})) == ("ok", None)
    assert filas("select count(*) from evento_autenticacion") == [(1,)]


# ===================================================== restricciones de forma ===============================================

@pytest.mark.parametrize("sentencia", [
    "insert into control_de_intentos (clave, intentos, ultimo_intento_en) values ('no-es-hex', 1, now())",
    "insert into control_de_intentos (clave, intentos, ultimo_intento_en) values ('" + "A" * 64 + "', 1, now())",                 # mayúsculas
    "insert into control_de_intentos (clave, intentos, ultimo_intento_en) values ('" + "a" * 63 + "', 1, now())",
    "insert into control_de_intentos (clave, intentos, ultimo_intento_en) values ('" + "a" * 64 + "', 0, now())",
    "insert into control_de_intentos_operador (clave, intentos, ultimo_intento_en) values ('ana.prueba', 1, now())",
    "insert into intento_de_origen (clave_origen, en) values ('203.0.113.7', now())",
])
def test_las_claves_deben_ser_hmac_en_hexadecimal_nunca_un_identificador_ni_una_direccion(sentencia):
    assert transaccion(OWNER(), (sentencia, {}))[0] == "23514"


@pytest.mark.parametrize("sentencia", [
    "insert into evento_autenticacion (tipo, ambito) values ('desconocido', 'persona')",
    "insert into evento_autenticacion (tipo, ambito) values ('inicio_fallido', 'otro')",
    "insert into evento_autenticacion (tipo, ambito, clave_cuenta) values ('inicio_fallido', 'persona', 'ana.prueba')",
    "insert into evento_autenticacion (tipo, ambito, clave_origen) values ('inicio_fallido', 'persona', '203.0.113.7')",
    "insert into evento_autenticacion (tipo, ambito, detalle) values ('inicio_fallido', 'persona', '[1]'::jsonb)",
    "insert into evento_autenticacion (tipo, ambito) values ('revocacion_por_desactivacion', 'persona')",
])
def test_los_eventos_validan_su_forma(sentencia):
    assert transaccion(OWNER(), (sentencia, {}))[0] == "23514"


def test_un_evento_de_operador_no_lleva_persona(persona):
    assert transaccion(OWNER(), (f"insert into evento_autenticacion (tipo, ambito, persona_id) values ('inicio_correcto', 'operador', '{persona}')", {}))[0] == "23514"


def test_las_tablas_no_tienen_ninguna_columna_con_contrasena_cookie_ni_identificador_en_claro():
    for tabla in ("control_de_intentos", "control_de_intentos_operador", "intento_de_origen", "evento_autenticacion"):
        columnas = {f[0] for f in filas("select column_name from information_schema.columns where table_schema = 'public' and table_name = :t", t=tabla)}
        assert not columnas & {"identificador", "identificador_acceso", "contrasena", "hash_contrasena", "secreto", "secreto_hash", "token", "cookie",
                               "direccion", "ip", "origen"}, (tabla, columnas)


# ===================================================== nada cambia sobre identidad, persona y sesion ========================

def test_no_se_amplian_los_permisos_sobre_identidad_persona_ni_sesion():
    def tiene(rol, tabla, privilegio, columna=None):
        sql = ("select has_column_privilege(:r, :t, :c, :p)" if columna else "select has_table_privilege(:r, :t, :p)")
        return filas(sql, r=rol, t=tabla, p=privilegio, **({"c": columna} if columna else {}))[0][0]
    from app.config import get_settings
    app, prov = get_settings().app_db_role, get_settings().provision_db_role
    # La aplicación: solo lee la identidad y las personas; en sesiones inserta y actualiza el último uso y la revocación.
    for tabla in ("identidad", "persona"):
        assert tiene(app, tabla, "SELECT") and not any(tiene(app, tabla, p) for p in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"))
    assert tiene(app, "sesion", "INSERT") and not tiene(app, "sesion", "DELETE")
    assert [c for c in ("secreto_hash", "creada_en", "caduca_absoluta_en", "identidad_id") if tiene(app, "sesion", "UPDATE", c)] == []
    # La provisión: lo mismo que tenía tras M1-T6.
    assert not tiene(prov, "identidad", "SELECT") and tiene(prov, "identidad", "SELECT", "persona_id") and not tiene(prov, "identidad", "SELECT", "hash_contrasena")
    assert not any(tiene(prov, "identidad", p) for p in ("UPDATE", "DELETE")) and not tiene(prov, "sesion", "SELECT", "secreto_hash")
    assert tiene(prov, "persona", "UPDATE", "acceso_desactivado_en") and not tiene(prov, "persona", "UPDATE", "nombre")


# ===================================================== instalación desde cero, datos existentes y reversión =================

def _alembic() -> Config:
    return Config(str(RAIZ / "alembic.ini"))


TABLAS_NUEVAS = ("control_de_intentos", "control_de_intentos_operador", "intento_de_origen", "evento_autenticacion")


def test_la_instalacion_desde_cero_crea_las_cuatro_tablas_y_sus_indices():
    for tabla in TABLAS_NUEVAS:
        assert filas("select to_regclass(:t) is not null", t=f"public.{tabla}") == [(True,)]
    indices = {f[0] for f in filas("select indexname from pg_indexes where schemaname = 'public'")}
    assert {"control_de_intentos_ultimo_intento_idx", "control_de_intentos_operador_ultimo_intento_idx", "intento_de_origen_ventana_idx",
            "intento_de_origen_en_idx", "evento_autenticacion_ocurrido_idx"} <= indices
    assert filas("select version_num >= '0014' from alembic_version") == [(True,)]          # (no se fija a la última: cada migración nueva la movería)


def test_la_migracion_0013_se_aplica_y_se_revierte_con_datos_existentes_sin_alterarlos(persona):
    with get_owner_engine().begin() as c:
        identidad = c.execute(text("select id from identidad")).scalar_one()
        c.execute(text("insert into sesion (identidad_id, secreto_hash, caduca_absoluta_en) values (:i, 's1', now() + interval '1 hour')"), {"i": identidad})
    antes = (filas("select * from persona order by id"), filas("select id, persona_id, identificador_acceso, hash_contrasena from identidad order by id"), filas("select * from sesion order by id"),
             filas("select * from pertenencia order by id"), filas("select * from auditoria order by id"))
    cfg = _alembic()
    command.downgrade(cfg, "0012")
    try:
        assert filas("select version_num from alembic_version") == [("0012",)]
        for tabla in TABLAS_NUEVAS:
            assert filas("select to_regclass(:t) is null", t=f"public.{tabla}") == [(True,)]
        assert filas("select proname from pg_proc where proname in ('evento_autenticacion_solo_anexado', 'evento_autenticacion_segun_rol')") == []
        assert (filas("select * from persona order by id"), filas("select * from sesion order by id")) == (antes[0], antes[2])   # los datos siguen intactos
    finally:
        command.upgrade(cfg, "head")
    despues = (filas("select * from persona order by id"), filas("select id, persona_id, identificador_acceso, hash_contrasena from identidad order by id"), filas("select * from sesion order by id"),
               filas("select * from pertenencia order by id"), filas("select * from auditoria order by id"))
    assert despues == antes
    assert all(contar(t) == 0 for t in TABLAS_NUEVAS)                    # las tablas nuevas empiezan vacías
    assert transaccion(APP(), ("insert into control_de_intentos (clave, intentos, ultimo_intento_en) values (:k, 1, now())", {"k": K})) == ("ok", None)   # y funcionan


def test_la_migracion_exige_que_exista_el_rol_de_provision():
    """Mismo criterio que las migraciones anteriores: sin el rol no se migra (no se puede crear roles desde una migración)."""
    from app.config import get_settings
    assert filas("select count(*) from pg_roles where rolname = :r", r=get_settings().provision_db_role) == [(1,)]
    codigo = (RAIZ / "migrations" / "versions" / "0013_control_de_intentos_y_eventos_de_autenticacion.py").read_text(encoding="utf-8")
    assert "_exigir_rol_de_provision" in codigo and "pg_roles" in codigo


def test_los_tipos_de_evento_del_codigo_coinciden_con_los_de_la_base():
    definicion = filas("select pg_get_constraintdef(oid) from pg_constraint where conrelid = 'evento_autenticacion'::regclass "
                       "and contype = 'c' and pg_get_constraintdef(oid) like '%inicio_correcto%'")[0][0]
    assert set(re.findall(r"'([a-z_]+)'", definicion)) == set(control.TIPOS_DE_EVENTO) and len(control.TIPOS_DE_EVENTO) == 6
