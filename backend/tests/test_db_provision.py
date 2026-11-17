"""M1-T2 — la base de datos de la provisión: privilegios mínimos del rol de provisión, restricciones y migración 0009.

Intentos REALES con cada rol (provisión, aplicación y propietario) sobre PostgreSQL. Las pruebas destructivas corren solo
sobre ``smartwork_test``. Garantías comprobadas: una credencial de la aplicación no permite ejecutar órdenes de provisión;
la persona operadora no puede alterar la información funcional de M2 ni de M3; la auditoría sigue siendo de solo anexado.
"""

import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.config import get_settings
from app.db import get_engine, get_owner_engine, get_provision_engine
from app.provision import servicio
from app.provision.operadores import Operador
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, hoy
from tests.utiles_m2 import contar, filas

RAIZ = Path(__file__).resolve().parent.parent
FUNCIONALES = ("bitacora", "actividad", "planificacion", "avance", "clave_idempotencia")   # sesion: ver test_db_desactivacion.py (M1-T6)


def sqlstate(motor, sql: str, **parametros) -> str:
    """Ejecuta una sentencia con ese rol y la DESHACE siempre. Devuelve ``ok`` o el SQLSTATE del rechazo."""
    try:
        with motor.connect() as c:
            c.execute(text(sql), parametros)
            c.rollback()
            return "ok"
    except DBAPIError as error:
        return error.orig.sqlstate


@pytest.fixture()
def base():
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c)
        eq = crear_equipo(c, org, "Equipo")
        p = crear_persona(c, "Persona")
        crear_pertenencia(c, p, eq, "supervisor", desde=hoy())
        crear_identidad(c, p, "persona", None)
        c.execute(text("insert into operador (identificador, hash_credencial) values ('operadora', 'hash-de-prueba')"))
        op_id = c.execute(text("select id from operador")).scalar_one()
    return {"org": org, "equipo": eq, "persona": p, "operador": op_id}


# ==================================================== privilegios del rol de provisión ====================================

def test_el_rol_de_provision_es_un_rol_distinto_sin_privilegios_de_administracion():
    rol = get_settings().provision_db_role
    fila = filas("select rolname, rolsuper, rolcreaterole, rolcreatedb, rolreplication from pg_roles where rolname = :r", r=rol)[0]
    assert fila == (rol, False, False, False, False)
    assert rol not in (get_settings().app_db_role, "smartwork_owner")
    with get_provision_engine().connect() as c:
        assert c.execute(text("select current_user")).scalar_one() == rol


@pytest.mark.parametrize("tabla", ["organizacion", "equipo", "persona", "pertenencia", "operador"])
def test_el_rol_de_provision_lee_lo_que_necesita(base, tabla):
    assert sqlstate(get_provision_engine(), f"select * from {tabla} limit 1") == "ok"


def test_el_rol_de_provision_lee_de_identidad_solo_lo_que_necesita(base):
    """M1-T6 retiró la lectura del hash de la contraseña: solo el identificador de acceso, la persona y el identificador de la identidad."""
    assert sqlstate(get_provision_engine(), "select id, persona_id, identificador_acceso from identidad limit 1") == "ok"
    assert sqlstate(get_provision_engine(), "select id, persona_id, identificador_acceso, hash_contrasena from identidad limit 1") == "42501"


def test_el_rol_de_provision_inserta_solo_lo_que_necesita(base):
    p = get_provision_engine()
    assert sqlstate(p, "insert into equipo (organizacion_id, nombre) values (:o, 'Nuevo')", o=base["org"]) == "ok"
    assert sqlstate(p, "insert into persona (nombre) values ('X')") == "ok"
    assert sqlstate(p, "insert into pertenencia (persona_id, equipo_id, rol, desde) values (:p, :e, 'colaborador', :d)",
                    p=base["persona"], e=base["equipo"], d=hoy() + timedelta(days=400)) in ("ok", "23P01")   # permiso concedido; la restricción puede rechazar
    assert sqlstate(p, "insert into identidad (persona_id, identificador_acceso) values (:p, 'otro')", p=base["persona"]) in ("ok", "23505")
    assert sqlstate(p, "insert into auditoria (tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id) "
                       "values ('provision', 'x', 'alta', 'equipo', :o)", o=uuid.uuid4()) == "ok"


@pytest.mark.parametrize("sentencia", [
    "update equipo set nombre = 'x'", "delete from equipo",
    "update persona set nombre = 'x'", "delete from persona",   # M1-T6 concede UN permiso por columna: acceso_desactivado_en (ver test_db_desactivacion.py)
    # M1-T3 concede UN permiso de actualización: ``hasta_exclusivo`` (ver test_db_traslados.py). Nada más se puede cambiar.
    "update pertenencia set equipo_id = equipo_id", "update pertenencia set rol = rol", "update pertenencia set desde = desde",
    "update pertenencia set persona_id = persona_id", "update pertenencia set id = id",
    "update identidad set hash_contrasena = 'x'", "delete from identidad",
    "update organizacion set nombre = 'x'", "insert into organizacion (nombre, zona_horaria) values ('x', 'UTC')", "delete from organizacion",
    "insert into operador (identificador, hash_credencial) values ('otra', 'x')", "update operador set estado = 'revocado', revocado_en = now()", "delete from operador",
    "update auditoria set motivo = 'x'", "delete from auditoria", "select 1 from auditoria limit 1",
    "truncate persona cascade", "create table intruso (x int)",
])
def test_el_rol_de_provision_no_puede_hacer_nada_mas(base, sentencia):
    assert sqlstate(get_provision_engine(), sentencia) == "42501", sentencia      # insufficient_privilege


@pytest.mark.parametrize("tabla", FUNCIONALES)
def test_la_persona_operadora_no_puede_alterar_la_informacion_funcional_de_m2_y_m3(base, tabla):
    p = get_provision_engine()
    for sentencia in (f"select 1 from {tabla} limit 1", f"delete from {tabla}", f"update {tabla} set id = id", f"truncate {tabla} cascade"):
        assert sqlstate(p, sentencia) == "42501", sentencia
    assert sqlstate(p, f"insert into {tabla} default values") == "42501"


# ==================================================== la aplicación no puede provisionar ==================================

def test_la_aplicacion_no_lee_las_credenciales_de_las_personas_operadoras(base):
    assert sqlstate(get_engine(), "select * from operador limit 1") == "42501"
    assert sqlstate(get_engine(), "select hash_credencial from operador") == "42501"


@pytest.mark.parametrize("sentencia", [
    "insert into equipo (organizacion_id, nombre) values (gen_random_uuid(), 'x')", "insert into persona (nombre) values ('x')",
    "insert into pertenencia (persona_id, equipo_id, rol, desde) values (gen_random_uuid(), gen_random_uuid(), 'colaborador', current_date)",
    "insert into identidad (persona_id, identificador_acceso) values (gen_random_uuid(), 'x')",
    "insert into operador (identificador, hash_credencial) values ('x', 'y')", "update persona set acceso_desactivado_en = now()",
])
def test_la_aplicacion_no_puede_ejecutar_ninguna_orden_de_provision(base, sentencia):
    assert sqlstate(get_engine(), sentencia) == "42501", sentencia


def test_una_credencial_de_la_aplicacion_no_ejecuta_los_casos_de_uso_de_provision(base):
    """Aunque se llamara al caso de uso con la conexión de la aplicación, la base lo rechaza y no queda nada."""
    antes = (contar("equipo"), contar("auditoria"))
    with pytest.raises(DBAPIError) as e, get_engine().begin() as c:
        servicio.crear_equipo(c, Operador(uuid.uuid4(), "x"), organizacion_id=base["org"], nombre="Intruso")
    assert e.value.orig.sqlstate == "42501" and (contar("equipo"), contar("auditoria")) == antes


# ==================================================== restricciones nuevas ================================================

def test_el_identificador_de_la_persona_operadora_se_guarda_normalizado_y_es_unico(base):
    o = get_owner_engine()
    assert sqlstate(o, "insert into operador (identificador, hash_credencial) values ('Mayúscula', 'x')") == "23514"
    assert sqlstate(o, "insert into operador (identificador, hash_credencial) values (' espacios ', 'x')") == "23514"
    assert sqlstate(o, "insert into operador (identificador, hash_credencial) values ('', 'x')") == "23514"
    assert sqlstate(o, "insert into operador (identificador, hash_credencial) values ('operadora', 'x')") == "23505"
    assert sqlstate(o, "insert into operador (identificador, hash_credencial) values ('otra', 'x')") == "ok"


def test_el_estado_y_la_revocacion_de_la_persona_operadora_son_coherentes(base):
    o = get_owner_engine()
    assert sqlstate(o, "insert into operador (identificador, hash_credencial, estado) values ('a', 'x', 'revocado')") == "23514"
    assert sqlstate(o, "insert into operador (identificador, hash_credencial, estado, revocado_en) values ('a', 'x', 'activo', now())") == "23514"
    assert sqlstate(o, "insert into operador (identificador, hash_credencial, estado) values ('a', 'x', 'otro')") == "23514"
    assert sqlstate(o, "insert into operador (identificador, hash_credencial, estado, revocado_en) values ('a', 'x', 'revocado', now())") == "ok"


def test_una_persona_operadora_no_es_una_persona_ni_tiene_pertenencia(base):
    assert filas("select count(*) from operador o join persona p on p.id = o.id") == [(0,)]
    assert contar("pertenencia") == 1      # solo la de la persona de la prueba


@pytest.mark.parametrize("duplicado", ["equipo", "EQUIPO", " Equipo ", "\tequipo "])
def test_la_base_impide_nombres_de_equipo_repetidos_aunque_se_salte_el_servicio(base, duplicado):
    assert sqlstate(get_owner_engine(), "insert into equipo (organizacion_id, nombre) values (:o, :n)", o=base["org"], n=duplicado) == "23505"


@pytest.mark.parametrize("distinto", ["Equipo  2", "Équipo", "Equipo2", "Equip"])
def test_la_base_admite_nombres_que_solo_se_parecen(base, distinto):
    assert sqlstate(get_owner_engine(), "insert into equipo (organizacion_id, nombre) values (:o, :n)", o=base["org"], n=distinto) == "ok"


def test_la_auditoria_de_provision_no_exige_propietaria_pero_la_de_personas_si(base):
    o = get_owner_engine()
    prov = "insert into auditoria (tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id) values ('provision', 'r', 'alta', 'equipo', gen_random_uuid())"
    pers = ("insert into auditoria (tipo_autor, autor_persona_id, operacion, tipo_objeto, objeto_id) "
            "values ('persona', :p, 'cierre', 'bitacora', gen_random_uuid())")
    assert sqlstate(o, prov) == "ok"
    assert sqlstate(o, pers, p=base["persona"]) == "23514"          # una entrada de persona sigue exigiendo su propietaria


def test_la_auditoria_sigue_siendo_de_solo_anexado_tras_la_migracion(base):
    with get_owner_engine().begin() as c:
        c.execute(text("insert into auditoria (tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id) "
                       "values ('provision', 'r', 'alta', 'equipo', gen_random_uuid())"))
    o = get_owner_engine()
    assert sqlstate(o, "update auditoria set motivo = 'x'") == "23000"      # el disparador (incluso para el propietario)
    assert sqlstate(o, "delete from auditoria") == "23000"


# ==================================================== la migración con datos existentes ===================================

def _alembic() -> Config:
    return Config(str(RAIZ / "alembic.ini"))


def test_la_migracion_se_aplica_sobre_una_base_con_datos_y_no_los_altera():
    """Se revierte a 0008, se crean datos de un esquema anterior (incluida una entrada de auditoría de una persona) y se
    vuelve a migrar: nada se pierde ni cambia."""
    cfg = _alembic()
    command.downgrade(cfg, "0008")
    try:
        with get_owner_engine().begin() as c:
            org = crear_organizacion(c)
            eq1, eq2 = crear_equipo(c, org, "Ventas"), crear_equipo(c, org, "Soporte")
            p = crear_persona(c, "Ana")
            crear_pertenencia(c, p, eq1, "supervisor", desde=date(2026, 1, 1))
            crear_identidad(c, p, "ana", "contraseña-de-prueba-123")
            c.execute(text("insert into auditoria (tipo_autor, autor_persona_id, operacion, tipo_objeto, objeto_id, "
                           "propietaria_registro_id, valor_nuevo) values ('persona', :p, 'cierre', 'bitacora', gen_random_uuid(), :p, '{}')"),
                      {"p": p})
        antes = (filas("select * from equipo order by nombre"), filas("select * from persona"), filas("select * from pertenencia"),
                 filas("select id, persona_id, identificador_acceso, hash_contrasena from identidad"), filas("select * from auditoria"))
    finally:
        command.upgrade(cfg, "head")
    despues = (filas("select * from equipo order by nombre"), filas("select * from persona"), filas("select * from pertenencia"),
               filas("select id, persona_id, identificador_acceso, hash_contrasena from identidad"), filas("select * from auditoria"))
    assert despues == antes
    assert sqlstate(get_provision_engine(), "select * from operador") == "ok"        # y los privilegios vuelven a estar


def test_una_base_con_nombres_de_equipo_repetidos_hace_fallar_la_migracion_sin_dejarla_a_medias():
    """La migración no borra ni renombra nada por su cuenta: con nombres repetidos (que P6 prohíbe) falla entera, de modo
    que hay que resolverlos antes. Una migración fallida se deshace por completo."""
    cfg = _alembic()
    command.downgrade(cfg, "0008")
    try:
        with get_owner_engine().begin() as c:
            org = crear_organizacion(c)
            crear_equipo(c, org, "Ventas")
            crear_equipo(c, org, "VENTAS ")
        with pytest.raises(Exception) as e:
            command.upgrade(cfg, "head")
        assert "equipo_nombre_unico_por_organizacion" in str(e.value) or "duplicate" in str(e.value).lower() or "duplicad" in str(e.value).lower()
        assert filas("select version_num from alembic_version") == [("0008",)]        # no quedó a medias
        assert sqlstate(get_owner_engine(), "select 1 from operador") == "42P01"        # la tabla nueva no existe
    finally:
        with get_owner_engine().begin() as c:
            c.execute(text("delete from equipo"))
            c.execute(text("delete from organizacion"))
        command.upgrade(cfg, "head")


def test_revertir_y_volver_a_aplicar_la_migracion_es_posible_y_conserva_la_auditoria_de_provision():
    cfg = _alembic()
    with get_owner_engine().begin() as c:
        c.execute(text("insert into auditoria (tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id) "
                       "values ('provision', 'r', 'alta', 'equipo', gen_random_uuid())"))
    command.downgrade(cfg, "0008")
    try:
        assert contar("auditoria") == 1                              # revertir no borra la auditoría
        assert sqlstate(get_owner_engine(), "select 1 from operador") == "42P01"
    finally:
        command.upgrade(cfg, "head")
    assert contar("auditoria") == 1
