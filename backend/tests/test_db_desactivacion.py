"""M1-T6 — la base de datos de la desactivación del acceso: migración 0012 y sus protecciones.

Intentos REALES con el rol de provisión sobre PostgreSQL. Lo que se prueba:

- los permisos MÍNIMOS: ``UPDATE (acceso_desactivado_en)`` sobre ``persona`` y ``SELECT (identidad_id, revocada_en)`` más
  ``UPDATE (revocada_en)`` sobre ``sesion``; nada más sobre personas, identidades ni sesiones; la lectura de ``identidad`` queda
  reducida a tres columnas (sin el hash de la contraseña);
- ``persona_solo_se_desactiva`` y ``sesion_solo_se_revoca``: el rol de provisión solo pasa de activo a desactivado y de vigente a
  revocada, con la hora actual: no reactiva, no «resucita» una sesión, no fecha en el pasado ni en el futuro;
- que el propietario y la aplicación no quedan limitados por esos disparadores y que la aplicación no recibe permisos nuevos;
- que la migración no crea ningún estado nuevo (la condición de equipo pendiente de supervisión efectiva es derivada) y que se
  aplica y se revierte sobre datos existentes sin alterarlos.

Las pruebas destructivas corren solo sobre ``smartwork_test``.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.db import get_engine, get_owner_engine, get_provision_engine
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, hoy
from tests.test_db_traslados import transaccion
from tests.utiles_m2 import contar, filas

RAIZ = Path(__file__).resolve().parent.parent
PROV = get_provision_engine


@pytest.fixture()
def mundo():
    """Una persona con identidad y dos sesiones (una vigente y una ya revocada), y otra persona con una sesión."""
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c)
        eq = crear_equipo(c, org, "T")
        p, q = crear_persona(c, "P"), crear_persona(c, "Q")
        for x in (p, q):
            crear_pertenencia(c, x, eq, "colaborador", desde=hoy())
        ip, iq = crear_identidad(c, p, "p", "contraseña-de-prueba-123"), crear_identidad(c, q, "q", "contraseña-de-prueba-123")
        for identidad, secreto in ((ip, "s1"), (ip, "s2"), (iq, "s3")):
            c.execute(text("insert into sesion (identidad_id, secreto_hash, caduca_absoluta_en) values (:i, :h, now() + interval '1 hour')"),
                      {"i": identidad, "h": secreto})
        c.execute(text("update sesion set revocada_en = now() - interval '1 hour' where secreto_hash = 's2'"))
    return {"p": p, "q": q, "ip": ip, "iq": iq}


# ==================================================== persona: una sola columna ===========================================

def test_el_rol_de_provision_puede_desactivar_un_acceso_con_la_hora_actual(mundo):
    assert transaccion(PROV(), ("update persona set acceso_desactivado_en = now() where id = :p", {"p": mundo["p"]})) == ("ok", None)
    assert filas("select acceso_desactivado_en is not null from persona where id = :p", p=mundo["p"]) == [(True,)]


@pytest.mark.parametrize("sentencia", ["update persona set nombre = 'x'", "update persona set id = id", "delete from persona", "truncate persona cascade"])
def test_el_rol_de_provision_no_puede_hacer_nada_mas_con_las_personas(mundo, sentencia):
    assert transaccion(PROV(), (sentencia, {}))[0] == "42501", sentencia


@pytest.mark.parametrize("valor", ["null", "now() - interval '1 day'", "now() + interval '1 day'", "now() - interval '1 second'"])
def test_no_se_fecha_la_desactivacion_en_el_pasado_ni_en_el_futuro_ni_se_deja_en_nulo(mundo, valor):
    estado, restriccion = transaccion(PROV(), (f"update persona set acceso_desactivado_en = {valor} where id = :p", {"p": mundo["p"]}))
    assert (estado, restriccion) == ("23514", "persona_solo_se_desactiva")
    assert filas("select acceso_desactivado_en from persona where id = :p", p=mundo["p"]) == [(None,)]


def test_el_rol_de_provision_no_reactiva_ni_reescribe_un_acceso_ya_desactivado(mundo):
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() - interval '2 days' where id = :p"), {"p": mundo["p"]})
    for valor in ("null", "now()", "now() - interval '1 day'"):
        assert transaccion(PROV(), (f"update persona set acceso_desactivado_en = {valor} where id = :p", {"p": mundo["p"]}))[1] == "persona_solo_se_desactiva"
    assert filas("select acceso_desactivado_en < now() - interval '1 day' from persona where id = :p", p=mundo["p"]) == [(True,)]


def test_los_disparadores_son_del_rol_de_provision_el_propietario_y_la_aplicacion_no_quedan_limitados(mundo):
    owner = get_owner_engine()
    assert transaccion(owner, ("update persona set acceso_desactivado_en = now() - interval '3 days' where id = :p", {"p": mundo["p"]})) == ("ok", None)
    assert transaccion(owner, ("update persona set acceso_desactivado_en = null where id = :p", {"p": mundo["p"]})) == ("ok", None)    # preparar datos de prueba
    assert transaccion(get_engine(), ("update sesion set ultimo_uso_en = now()", {})) == ("ok", None)
    assert transaccion(get_engine(), ("update sesion set revocada_en = now() - interval '1 day' where secreto_hash = 's1'", {})) == ("ok", None)


def test_la_aplicacion_sigue_sin_poder_cambiar_el_acceso_de_nadie_y_no_recibe_permisos_nuevos(mundo):
    app = get_engine()
    for sentencia in ("update persona set acceso_desactivado_en = now()", "update persona set nombre = 'x'", "delete from sesion"):
        assert transaccion(app, (sentencia, {}))[0] == "42501", sentencia
    assert transaccion(app, ("select 1 from operador", {}))[0] == "42501"


# ==================================================== sesion: revocar y nada más ===========================================

def test_el_rol_de_provision_revoca_las_sesiones_de_una_persona(mundo):
    sentencia = ("update sesion set revocada_en = now() where revocada_en is null and identidad_id in (select id from identidad where persona_id = :p)", {"p": mundo["p"]})
    assert transaccion(PROV(), sentencia) == ("ok", None)
    assert filas("select count(*) from sesion where revocada_en is null") == [(1,)]       # solo queda la de la otra persona


@pytest.mark.parametrize("sentencia", [
    "select secreto_hash from sesion", "select * from sesion", "select id from sesion", "select ultimo_uso_en from sesion",
    "update sesion set secreto_hash = 'x'", "update sesion set ultimo_uso_en = now()", "update sesion set identidad_id = identidad_id",
    "update sesion set caduca_absoluta_en = now() + interval '9 years'", "delete from sesion",
    "insert into sesion (identidad_id, secreto_hash, caduca_absoluta_en) select id, 'x', now() from identidad", "truncate sesion",
])
def test_el_rol_de_provision_no_lee_los_secretos_ni_toca_nada_mas_de_las_sesiones(mundo, sentencia):
    assert transaccion(PROV(), (sentencia, {}))[0] == "42501", sentencia


def test_el_rol_de_provision_lee_solo_las_dos_columnas_que_necesita_de_la_sesion(mundo):
    assert transaccion(PROV(), ("select identidad_id, revocada_en from sesion", {})) == ("ok", None)


@pytest.mark.parametrize("valor", ["null", "now() - interval '1 day'", "now() + interval '1 day'"])
def test_el_rol_de_provision_no_resucita_ni_fecha_mal_una_sesion(mundo, valor):
    vigente = (f"update sesion set revocada_en = {valor} where identidad_id = :i and revocada_en is null", {"i": mundo["ip"]})
    revocada = (f"update sesion set revocada_en = {valor} where identidad_id = :i and revocada_en is not null", {"i": mundo["ip"]})
    assert transaccion(PROV(), vigente)[1] == "sesion_solo_se_revoca"
    assert transaccion(PROV(), revocada)[1] == "sesion_solo_se_revoca"                         # una sesión ya revocada no se toca
    assert filas("select revocada_en is null from sesion where secreto_hash = 's1'") == [(True,)]


def test_el_rol_de_provision_no_reescribe_la_revocacion_de_una_sesion_ya_revocada(mundo):
    """Aunque el valor nuevo sea «ahora»: la fecha de una revocación ya hecha no se cambia (el historial de sesiones no se reescribe)."""
    antes = filas("select revocada_en from sesion where secreto_hash = 's2'")
    assert transaccion(PROV(), ("update sesion set revocada_en = now() where identidad_id = :i and revocada_en is not null", {"i": mundo["ip"]}))[1] == "sesion_solo_se_revoca"
    assert filas("select revocada_en from sesion where secreto_hash = 's2'") == antes


# ==================================================== identidad: sin el hash de la contraseña ==============================

def test_el_rol_de_provision_ya_no_lee_el_hash_de_la_contrasena_pero_si_lo_que_necesita(mundo):
    assert transaccion(PROV(), ("select hash_contrasena from identidad", {}))[0] == "42501"
    assert transaccion(PROV(), ("select id, persona_id, identificador_acceso, hash_contrasena from identidad", {}))[0] == "42501"
    assert transaccion(PROV(), ("select id, persona_id, identificador_acceso from identidad", {})) == ("ok", None)
    for sentencia in ("update identidad set hash_contrasena = 'x'", "delete from identidad", "update identidad set identificador_acceso = 'x'"):
        assert transaccion(PROV(), (sentencia, {}))[0] == "42501", sentencia


# ==================================================== la migración =========================================================

def test_la_migracion_no_crea_ninguna_tabla_ni_columna_ni_estado_nuevo_para_el_equipo(mundo):
    columnas = lambda t: {f[0] for f in filas("select column_name from information_schema.columns where table_schema = 'public' and table_name = :t", t=t)}   # noqa: E731
    assert columnas("persona") == {"id", "nombre", "acceso_desactivado_en"}
    assert columnas("equipo") == {"id", "organizacion_id", "nombre"}
    assert columnas("sesion") == {"id", "identidad_id", "secreto_hash", "creada_en", "ultimo_uso_en", "caduca_absoluta_en", "revocada_en"}
    assert columnas("pertenencia") == {"id", "persona_id", "equipo_id", "rol", "desde", "hasta_exclusivo"}


def _alembic() -> Config:
    return Config(str(RAIZ / "alembic.ini"))


def test_la_migracion_0012_se_aplica_y_se_revierte_con_datos_sin_alterarlos(mundo):
    cfg = _alembic()
    antes = (filas("select * from persona order by id"), filas("select * from sesion order by id"), filas("select id, persona_id, identificador_acceso, hash_contrasena from identidad order by id"),
             filas("select * from pertenencia order by id"))
    command.downgrade(cfg, "0011")
    try:
        assert filas("select version_num from alembic_version") == [("0011",)]
        assert transaccion(PROV(), ("update persona set acceso_desactivado_en = now()", {}))[0] == "42501"      # el permiso desaparece
        assert transaccion(PROV(), ("select identidad_id from sesion", {}))[0] == "42501"
        assert transaccion(PROV(), ("select hash_contrasena from identidad", {})) == ("ok", None)               # y la lectura de identidad vuelve a la de 0011
        assert filas("select tgname from pg_trigger where tgname in ('persona_solo_se_desactiva', 'sesion_solo_se_revoca') and not tgisinternal") == []
    finally:
        command.upgrade(cfg, "head")
    despues = (filas("select * from persona order by id"), filas("select * from sesion order by id"), filas("select id, persona_id, identificador_acceso, hash_contrasena from identidad order by id"),
               filas("select * from pertenencia order by id"))
    assert despues == antes
    assert transaccion(PROV(), ("update persona set acceso_desactivado_en = now() where id = :p", {"p": mundo["p"]})) == ("ok", None)       # y vuelve


def test_los_dos_disparadores_existen_y_no_son_diferibles(mundo):
    assert filas("select tgname, tgdeferrable from pg_trigger where tgname in ('persona_solo_se_desactiva', 'sesion_solo_se_revoca') order by tgname") == [
        ("persona_solo_se_desactiva", False), ("sesion_solo_se_revoca", False)]


def test_la_migracion_no_toca_la_auditoria_ni_los_datos_funcionales(mundo):
    assert contar("auditoria") == 0 and contar("bitacora") == 0 and contar("actividad") == 0
