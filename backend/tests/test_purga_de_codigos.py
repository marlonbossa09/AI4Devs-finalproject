"""M1-T8.6 — purga de los códigos de un solo uso terminados (orden ``purgar-codigos`` de la CLI de provisión; migración 0017) con PostgreSQL real.

Pruebas esenciales (metodología ligera): borra solo los usados, invalidados o caducados hace 30 días o más (con el reloj de PostgreSQL, no el de Python); conserva los
pendientes vigentes y los recientes; es repetible; no toca la auditoría funcional; no imprime códigos, hashes ni personas; exige identificar a la persona operadora; y los
privilegios mínimos (solo la provisión borra; no lee hashes; la aplicación nada; la base protege por su cuenta). Destructivas solo sobre ``smartwork_test``.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine, get_owner_engine, get_provision_engine
from app.provision import emision
from app.provision.operadores import Operador
from app.seguridad import codigos
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, hoy
from tests.test_db_traslados import transaccion
from tests.test_provision_cli import CREDENCIAL, ejecutar, instalada, sin_secretos  # noqa: F401  (fixture ``instalada``)
from tests.utiles_m2 import contar, filas

RAIZ = Path(__file__).resolve().parent.parent
OPERADOR = Operador(uuid.uuid4(), "operadora.test")
MALA = "credencial-equivocada-123"


@pytest.fixture()
def mundo():
    with get_owner_engine().begin() as c:
        eq = crear_equipo(c, crear_organizacion(c), "T")
        p = {}
        for nombre in ("ana", "beto", "clara"):
            p[nombre] = crear_persona(c, nombre)
            crear_pertenencia(c, p[nombre], eq, "colaborador", desde=hoy() - timedelta(days=1))
            crear_identidad(c, p[nombre], nombre, None)
        ids = {r.persona_id: r.id for r in c.execute(text("select id, persona_id from identidad"))}
    return {n: ids[p[n]] for n in p} | {"personas": p}


def insertar(identidad, *, termino, dias=0):
    """Inserta un código ya envejecido, sin pasar por los disparadores (envejecer una fila exige saltárselos; es el propietario, solo en la prueba).

    ``termino``: ``usado``, ``invalidado``, ``caducado`` (pendiente que ya caducó) o ``pendiente`` (vigente). ``dias``: hace cuántos días terminó."""
    h = codigos.hash_de_octetos(codigos.generar_octetos())
    fin = "now() - make_interval(days => :d)"
    if termino == "pendiente":
        valores = ("now()", "now() + interval '10 minutes'", "null", "null")
    else:
        emitido = f"{fin} - interval '2 hours'"
        valores = {"usado": (emitido, f"{fin} + interval '1 hour'", fin, "null"),
                   "invalidado": (emitido, f"{fin} + interval '1 hour'", "null", fin),
                   "caducado": (emitido, fin, "null", "null")}[termino]
    emitido, caduca, usado, invalidado = valores
    with get_owner_engine().begin() as c:
        c.execute(text("alter table codigo_unico disable trigger user"))
        c.execute(text(f"insert into codigo_unico (identidad_id, finalidad, hash_codigo, emitido_en, caduca_en, usado_en, invalidado_en, emitido_por) "
                       f"values (:i, 'primer_acceso', :h, {emitido}, {caduca}, {usado}, {invalidado}, 'operador:x|invocacion:y')"),
                  {"i": identidad, "h": h, "d": dias})
        c.execute(text("alter table codigo_unico enable trigger user"))
    return h


def purgar(instalada, credencial=CREDENCIAL, **extra):
    return ejecutar(["purgar-codigos", "--operador", instalada["operador"]], credencial=credencial, **extra)


@pytest.fixture()
def variados(mundo):
    """Un código por cada estado a ambos lados del límite de 30 días y un pendiente vigente."""
    casos = {"usado_31": ("ana", "usado", 31), "usado_29": ("ana", "usado", 29), "invalidado_45": ("ana", "invalidado", 45), "invalidado_10": ("ana", "invalidado", 10),
             "caducado_40": ("beto", "caducado", 40), "caducado_5": ("clara", "caducado", 5)}
    for nombre, (quien, termino, dias) in casos.items():
        insertar(mundo[quien], termino=termino, dias=dias)
    insertar(mundo["ana"], termino="pendiente")
    return mundo


def conservados():
    """Cuántos códigos quedan por estado: (usado, invalidado, caducado sin fin, pendiente vigente)."""
    return filas("select count(*) filter (where usado_en is not null), count(*) filter (where invalidado_en is not null), "
                 "count(*) filter (where usado_en is null and invalidado_en is null and caduca_en <= now()), "
                 "count(*) filter (where usado_en is null and invalidado_en is null and caduca_en > now()) from codigo_unico")[0]


def test_la_purga_borra_solo_los_terminados_hace_30_dias_o_mas_y_conserva_los_pendientes_vigentes_y_los_recientes(instalada, variados):
    assert contar("codigo_unico") == 7
    codigo, salida, error = purgar(instalada)
    r = json.loads(salida)
    assert codigo == 0 and error == "" and r["orden"] == "purgar-codigos" and r["codigos_purgados"] == 3 and r["retencion_dias"] == 30
    assert contar("codigo_unico") == 4
    assert conservados() == (1, 1, 1, 1)                      # usado de 29 días, invalidado de 10, caducado de 5 y el pendiente vigente
    dias = sorted(round(f[0]) for f in filas("select extract(day from now() - coalesce(usado_en, invalidado_en, caduca_en)) from codigo_unico where caduca_en <= now()"))
    assert dias == [5, 10, 29]
    assert filas("select count(*) from codigo_unico where caduca_en > now()") == [(1,)]


def test_la_purga_es_repetible_y_la_segunda_vez_no_borra_nada(instalada, variados):
    assert json.loads(purgar(instalada)[1])["codigos_purgados"] == 3
    assert json.loads(purgar(instalada)[1])["codigos_purgados"] == 0
    assert contar("codigo_unico") == 4


def test_sin_codigos_la_purga_no_hace_nada_y_lo_dice(instalada, mundo):
    codigo, salida, error = purgar(instalada)
    assert codigo == 0 and json.loads(salida)["codigos_purgados"] == 0 and error == ""


def test_la_purga_usa_el_reloj_de_postgresql_y_no_el_del_proceso(instalada, variados):
    """Un reloj de Python adelantado 10 años no adelanta la retención: se sigue conservando lo de menos de 30 días."""
    futuro = lambda: datetime.now() + timedelta(days=3650)  # noqa: E731
    codigo, salida, error = purgar(instalada, reloj=futuro)
    assert codigo == 0 and json.loads(salida)["codigos_purgados"] == 3 and contar("codigo_unico") == 4 and conservados() == (1, 1, 1, 1)


def test_la_purga_no_toca_la_auditoria_funcional(instalada, mundo):
    """Una emisión real deja un código y su auditoría; aunque el código se purgue (ya envejecido), la auditoría de la emisión permanece intacta."""
    with get_provision_engine().begin() as c:
        emision.emitir_codigo(c, OPERADOR, persona_id=mundo["personas"]["ana"], finalidad="primer_acceso", verificacion=None, presentar=lambda cod, caduca: None)
    antes = filas("select id, operacion, valor_nuevo from auditoria order by id")
    assert len(antes) >= 1 and any(f[1] == "entrega_acceso" for f in antes)
    with get_owner_engine().begin() as c:
        c.execute(text("alter table codigo_unico disable trigger user"))
        c.execute(text("update codigo_unico set emitido_en = now() - interval '60 days', caduca_en = now() - interval '59 days', usado_en = now() - interval '40 days'"))
        c.execute(text("alter table codigo_unico enable trigger user"))
    assert json.loads(purgar(instalada)[1])["codigos_purgados"] == 1 and contar("codigo_unico") == 0
    despues = filas("select id, operacion, valor_nuevo from auditoria order by id")
    assert despues[: len(antes)] == antes and contar("persona") == 3 and contar("identidad") == 3        # y tampoco se tocan las personas


def test_la_salida_no_revela_codigos_hashes_ni_personas(instalada, variados):
    hashes = [f[0] for f in filas("select hash_codigo from codigo_unico")]
    identificadores = [f[0] for f in filas("select identificador_acceso from identidad")]
    codigo, salida, error = purgar(instalada)
    assert set(json.loads(salida)) == {"orden", "operador_id", "invocacion", "base", "codigos_purgados", "anteriores_a", "retencion_dias"}
    assert not any(h in salida + error for h in hashes) and not any(i in salida + error for i in identificadores)
    sin_secretos(salida, error)


def test_la_purga_exige_identificar_a_la_persona_operadora_y_si_falla_no_borra_nada(instalada, variados):
    codigo, salida, error = purgar(instalada, MALA)
    assert codigo == 2 and json.loads(error)["error"] == "OPERADOR_NO_AUTORIZADO" and salida == "" and contar("codigo_unico") == 7


def test_la_base_protege_por_su_cuenta_los_pendientes_y_los_recientes_aunque_la_orden_fallara(variados):
    """Sin pasar por la orden: borrar todo con el rol de provisión se rechaza mientras quede un código pendiente o reciente, y solo prospera con lo antiguo."""
    assert transaccion(get_provision_engine(), ("delete from codigo_unico", {}))[0] == "23514" and contar("codigo_unico") == 7
    assert transaccion(get_provision_engine(), ("delete from codigo_unico where caduca_en > now() or usado_en > now() - interval '30 days'", {}))[0] == "23514"
    assert transaccion(get_provision_engine(), ("delete from codigo_unico where coalesce(usado_en, invalidado_en, caduca_en) <= now() - interval '30 days'", {})) == ("ok", None)
    assert contar("codigo_unico") == 4


# ===================================================== privilegios mínimos ===================================================

def test_solo_la_provision_puede_borrar_codigos_y_ningun_rol_lee_el_hash_ni_puede_vaciar_la_tabla(variados):
    s = get_settings()
    privilegio = lambda rol, p: filas("select has_table_privilege(:r, 'codigo_unico', :p)", r=rol, p=p)[0][0]  # noqa: E731
    assert privilegio(s.provision_db_role, "DELETE") and not privilegio(s.app_db_role, "DELETE") and not privilegio("public", "DELETE")
    for rol in (s.provision_db_role, s.app_db_role):
        assert not privilegio(rol, "TRUNCATE")
        assert filas("select has_column_privilege(:r, 'codigo_unico', 'hash_codigo', 'SELECT')", r=rol) == [(False,)]
    assert transaccion(get_engine(), ("delete from codigo_unico", {}))[0] == "42501"                           # la aplicación, nada
    assert transaccion(get_provision_engine(), ("select hash_codigo from codigo_unico", {}))[0] == "42501"      # la provisión borra pero no lee hashes
    assert transaccion(get_provision_engine(), ("truncate codigo_unico", {}))[0] == "42501"
    assert transaccion(get_provision_engine(), ("update codigo_unico set usado_en = now()", {}))[0] == "42501"
    assert transaccion(get_provision_engine(), ("delete from auditoria", {}))[0] == "42501"                    # y la auditoría sigue fuera de su alcance


def test_la_migracion_0017_solo_concede_delete_y_se_puede_revertir(variados):
    cfg = Config(str(RAIZ / "alembic.ini"))
    s = get_settings()
    antes = filas("select grantee, privilege_type from information_schema.role_table_grants where table_name = 'codigo_unico' order by 1, 2")
    command.downgrade(cfg, "0016")
    try:
        assert filas("select has_table_privilege(:r, 'codigo_unico', 'DELETE')", r=s.provision_db_role) == [(False,)]
        sin = filas("select grantee, privilege_type from information_schema.role_table_grants where table_name = 'codigo_unico' order by 1, 2")
        assert set(antes) - set(sin) == {(s.provision_db_role, "DELETE")} and not set(sin) - set(antes)       # lo único que cambia
    finally:
        command.upgrade(cfg, "head")
    assert filas("select has_table_privilege(:r, 'codigo_unico', 'DELETE')", r=s.provision_db_role) == [(True,)]
    assert contar("codigo_unico") == 7                                                                          # datos intactos
