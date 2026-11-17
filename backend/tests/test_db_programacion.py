"""M1-T4 — la base de datos de las operaciones programadas: migración 0011 y sus protecciones.

Intentos REALES con el rol de provisión sobre PostgreSQL. Lo que se prueba:

- el único permiso nuevo del rol de provisión (``DELETE`` sobre ``pertenencia``) y que sigue sin poder tocar nada más;
- ``pertenencia_solo_cambia_lo_programado``: SOLO se borra un intervalo que todavía no ha empezado y SOLO se cambia el fin de un
  intervalo cuando el fin actual y el nuevo son posteriores a hoy, con la fecha actual de la zona horaria de la organización,
  en los límites exactos de los intervalos (hoy y mañana) y con husos horarios distintos del UTC;
- ``pertenencia_supervision_del_equipo`` (diferido) también vigila los borrados (cancelar un alta o un relevo a medias);
- que el propietario no queda limitado (herramientas de desarrollo y pruebas) y que la aplicación sigue sin escribir;
- la migración sobre datos existentes.

Las pruebas destructivas corren solo sobre ``smartwork_test``.
"""

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.db import get_engine, get_owner_engine, get_provision_engine
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, hoy
from tests.test_db_traslados import abre, cierra, transaccion
from tests.utiles_m2 import contar, filas

RAIZ = Path(__file__).resolve().parent.parent
HOY = hoy()
PROV = get_provision_engine


def dia(n: int):
    return HOY + timedelta(days=n)


def borra(persona, desde=None):
    if desde is None:
        return ("delete from pertenencia where persona_id = :p", {"p": persona})
    return ("delete from pertenencia where persona_id = :p and desde = :d", {"p": persona, "d": desde})


def reabre(persona, fecha):
    """Cambia el fin del último intervalo de la persona (``None`` = sin fin)."""
    return ("update pertenencia set hasta_exclusivo = cast(:f as date) where persona_id = :p and "
            "desde = (select max(desde) from pertenencia where persona_id = :p)", {"p": persona, "f": fecha})


@pytest.fixture()
def mundo():
    """Equipo T (supervisor S, colaborador C), equipo U (supervisor SU) y equipo vacío V; personas N y M sin pertenencia."""
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c)
        eq = {"T": crear_equipo(c, org, "T"), "U": crear_equipo(c, org, "U"), "V": crear_equipo(c, org, "V")}
        p = {n: crear_persona(c, n) for n in ("S", "C", "SU", "N", "M")}
        for persona, equipo, rol in (("S", "T", "supervisor"), ("C", "T", "colaborador"), ("SU", "U", "supervisor")):
            crear_pertenencia(c, p[persona], eq[equipo], rol, desde=dia(-30))
            crear_identidad(c, p[persona], persona.lower(), None)
    return {"org": org, "eq": eq, "p": p}


def programado(m, persona, equipo, rol, desde, hasta=None):
    with get_owner_engine().begin() as c:
        crear_pertenencia(c, m["p"][persona], m["eq"][equipo], rol, desde=desde, hasta=hasta)


# ==================================================== privilegios =========================================================

def test_el_rol_de_provision_borra_solo_pertenencias_y_nada_mas(mundo):
    for sentencia in ("delete from persona", "delete from equipo", "delete from identidad", "delete from organizacion", "delete from operador",
                      "delete from auditoria", "delete from bitacora", "delete from actividad", "delete from avance", "delete from planificacion"):
        assert transaccion(PROV(), (sentencia, {}))[0] == "42501", sentencia
    assert transaccion(PROV(), ("truncate pertenencia", {}))[0] == "42501"


def test_la_aplicacion_sigue_sin_poder_borrar_ni_cambiar_pertenencias(mundo):
    for sentencia in ("delete from pertenencia", "update pertenencia set hasta_exclusivo = current_date + 400"):
        assert transaccion(get_engine(), (sentencia, {}))[0] == "42501"


def test_el_rol_de_provision_sigue_sin_poder_cambiar_otra_columna_de_una_pertenencia(mundo):
    for columna in ("equipo_id", "rol", "desde", "persona_id", "id"):
        assert transaccion(PROV(), (f"update pertenencia set {columna} = {columna}", {}))[0] == "42501", columna


# ==================================================== borrar: solo lo programado, en los límites exactos ================

def test_se_borra_un_intervalo_que_empieza_manana(mundo):
    programado(mundo, "N", "V", "supervisor", dia(1))
    assert transaccion(PROV(), borra(mundo["p"]["N"])) == ("ok", None)
    assert filas("select count(*) from pertenencia where persona_id = :p", p=mundo["p"]["N"]) == [(0,)]


def test_un_intervalo_que_empieza_hoy_no_se_borra(mundo):
    programado(mundo, "N", "V", "supervisor", dia(0))
    assert transaccion(PROV(), borra(mundo["p"]["N"])) == ("23514", "pertenencia_solo_cambia_lo_programado")
    assert contar("pertenencia") == 4


def test_un_intervalo_que_empezo_en_el_pasado_no_se_borra_aunque_tenga_fin(mundo):
    programado(mundo, "N", "V", "supervisor", dia(-20), dia(-10))
    assert transaccion(PROV(), borra(mundo["p"]["N"]))[1] == "pertenencia_solo_cambia_lo_programado"
    assert transaccion(PROV(), borra(mundo["p"]["S"]))[1] == "pertenencia_solo_cambia_lo_programado"          # y los vigentes tampoco


def test_un_borrado_masivo_con_una_sola_fila_efectiva_se_rechaza_entero(mundo):
    programado(mundo, "N", "V", "supervisor", dia(5))
    assert transaccion(PROV(), ("delete from pertenencia", {}))[1] == "pertenencia_solo_cambia_lo_programado"
    assert contar("pertenencia") == 4                                   # nada se borró


@pytest.mark.parametrize("zona", ["America/Bogota", "Pacific/Kiritimati", "Pacific/Pago_Pago", "UTC"])
def test_la_fecha_actual_del_control_es_la_de_la_zona_horaria_de_la_organizacion(zona):
    """Con husos de +14 h y -11 h la fecha local difiere de la de UTC durante buena parte del día: el límite entre «hoy» y
    «mañana» es el de la organización, no el del servidor. Un intervalo que empieza hoy (local) no se borra; uno que empieza
    mañana (local) sí."""
    local = datetime.now(ZoneInfo(zona)).date()
    with get_owner_engine().begin() as c:
        org = c.execute(text("insert into organizacion (nombre, zona_horaria) values ('Z', :z) returning id"), {"z": zona}).scalar_one()
        equipo = crear_equipo(c, org, "Z")
        de_hoy, de_manana, jefa = crear_persona(c, "h"), crear_persona(c, "m"), crear_persona(c, "j")
        crear_pertenencia(c, jefa, equipo, "supervisor", desde=local - timedelta(days=30))          # el equipo cumple IR-32
        crear_pertenencia(c, de_hoy, equipo, "colaborador", desde=local)
        crear_pertenencia(c, de_manana, equipo, "colaborador", desde=local + timedelta(days=1))
    assert transaccion(PROV(), borra(de_hoy)) == ("23514", "pertenencia_solo_cambia_lo_programado")
    assert transaccion(PROV(), borra(de_manana)) == ("ok", None)


@pytest.mark.parametrize("zona", ["Pacific/Kiritimati", "Pacific/Pago_Pago"])
def test_el_limite_de_un_fin_se_mide_tambien_en_la_zona_de_la_organizacion(zona):
    local = datetime.now(ZoneInfo(zona)).date()
    with get_owner_engine().begin() as c:
        org = c.execute(text("insert into organizacion (nombre, zona_horaria) values ('Z', :z) returning id"), {"z": zona}).scalar_one()
        equipo = crear_equipo(c, org, "Z")
        persona = crear_persona(c, "p")
        crear_pertenencia(c, persona, equipo, "colaborador", desde=local - timedelta(days=10))
    assert transaccion(PROV(), cierra(persona, local))[1] == "pertenencia_solo_cambia_lo_programado"            # hoy (local): no
    assert transaccion(PROV(), cierra(persona, local + timedelta(days=1))) == ("ok", None)                       # mañana (local): sí


def test_el_control_de_un_borrado_mira_la_ventana_exacta_y_no_solo_el_estado_final(mundo):
    """Cadena de supervisores S [-30, 5), N [5, 8), M [8, ∞) con un colaborador C: retirar a N (programado) deja a C sin
    supervisor SOLO del 5 al 8. El estado final (con M) es correcto: el control debe mirar desde la fecha del intervalo borrado."""
    p, e = mundo["p"], mundo["eq"]
    with get_owner_engine().begin() as c:
        c.execute(text("update pertenencia set hasta_exclusivo = :f where persona_id = :p"), {"f": dia(5), "p": p["S"]})
        crear_pertenencia(c, p["N"], e["T"], "supervisor", desde=dia(5), hasta=dia(8))
        crear_pertenencia(c, p["M"], e["T"], "supervisor", desde=dia(8))
    assert transaccion(PROV(), borra(p["N"])) == ("23514", "pertenencia_supervision_del_equipo")
    assert contar("pertenencia") == 5


def test_el_propietario_no_esta_limitado_por_el_control(mundo):
    p = mundo["p"]
    assert transaccion(get_owner_engine(), borra(p["C"])) == ("ok", None)           # un intervalo efectivo: preparar datos de prueba


# ==================================================== cambiar el fin: solo si el fin actual y el nuevo son futuros =========

def test_el_fin_de_un_intervalo_vigente_se_puede_fijar_a_manana_pero_no_a_hoy(mundo):
    c = mundo["p"]["C"]
    assert transaccion(PROV(), cierra(c, dia(0)))[1] == "pertenencia_solo_cambia_lo_programado"          # hoy: ya no es futuro
    assert transaccion(PROV(), cierra(c, dia(1))) == ("ok", None)


def test_un_fin_que_es_manana_se_puede_restituir_o_mover_y_uno_que_es_hoy_no(mundo):
    c = mundo["p"]["C"]
    with get_owner_engine().begin() as cn:                                           # el fin llega a ser hoy (preparado por el propietario)
        cn.execute(text("update pertenencia set hasta_exclusivo = :f where persona_id = :p"), {"f": dia(0), "p": c})
    assert transaccion(PROV(), reabre(c, None))[1] == "pertenencia_solo_cambia_lo_programado"
    assert transaccion(PROV(), reabre(c, dia(9)))[1] == "pertenencia_solo_cambia_lo_programado"
    with get_owner_engine().begin() as cn:
        cn.execute(text("update pertenencia set hasta_exclusivo = :f where persona_id = :p"), {"f": dia(1), "p": c})
    assert transaccion(PROV(), reabre(c, None)) == ("ok", None)


# ==================================================== IR-32 también vigila los borrados ====================================

def test_cancelar_una_alta_de_un_colaborador_sin_efecto_sobre_la_supervision_se_acepta(mundo):
    programado(mundo, "N", "T", "colaborador", dia(5))
    assert transaccion(PROV(), borra(mundo["p"]["N"])) == ("ok", None)


def test_cancelar_la_alta_de_un_supervisor_programado_que_cubria_a_los_colaboradores_se_rechaza_al_confirmar(mundo):
    """S termina el día 5 y N lo releva (alta programada de supervisor el mismo día). Retirar a N deja a C sin supervisor."""
    p, e = mundo["p"], mundo["eq"]
    assert transaccion(PROV(), cierra(p["S"], dia(5)), abre(p["N"], e["T"], "supervisor", dia(5))) == ("ok", None)
    estado, restriccion = transaccion(PROV(), borra(p["N"]))
    assert (estado, restriccion) == ("23514", "pertenencia_supervision_del_equipo")
    assert contar("pertenencia") == 4                                  # la transacción se deshizo (S, C, SU y N)


def test_cancelar_un_relevo_completo_en_una_transaccion_se_acepta_aunque_entre_sentencias_haya_dos_supervisores_o_ninguno(mundo):
    p, e = mundo["p"], mundo["eq"]
    assert transaccion(PROV(), cierra(p["S"], dia(5)), abre(p["N"], e["T"], "supervisor", dia(5))) == ("ok", None)
    # borrar al entrante y restituir el fin de S, en una sola transacción: válido
    assert transaccion(PROV(), borra(p["N"]), reabre(p["S"], None)) == ("ok", None)
    assert filas("select hasta_exclusivo from pertenencia where persona_id = :p", p=p["S"]) == [(None,)]


def test_restituir_al_saliente_sin_retirar_al_entrante_dejaria_dos_supervisores_y_lo_impide_la_exclusion(mundo):
    p, e = mundo["p"], mundo["eq"]
    assert transaccion(PROV(), cierra(p["S"], dia(5)), abre(p["N"], e["T"], "supervisor", dia(5))) == ("ok", None)
    assert transaccion(PROV(), reabre(p["S"], None))[0] == "23P01"


def test_el_disparador_de_supervision_no_vigila_al_propietario_en_los_borrados(mundo):
    assert transaccion(get_owner_engine(), borra(mundo["p"]["S"])) == ("ok", None)    # deja a C sin supervisor: el propietario puede


def test_el_trigger_de_supervision_es_diferido_y_vigila_insertar_actualizar_y_borrar(mundo):
    assert filas("select tgtype & 2 > 0 as antes, tgtype & 4 > 0 as ins, tgtype & 8 > 0 as del, tgtype & 16 > 0 as upd, tgdeferrable, tginitdeferred "
                 "from pg_trigger where tgname = 'pertenencia_supervision_del_equipo'") == [(False, True, True, True, True, True)]


# ==================================================== la migración ========================================================

def _alembic() -> Config:
    return Config(str(RAIZ / "alembic.ini"))


def test_la_migracion_0011_se_aplica_y_se_revierte_con_datos_sin_alterarlos(mundo):
    cfg = _alembic()
    antes = (filas("select * from pertenencia order by id"), filas("select * from equipo order by id"), filas("select * from persona order by id"))
    command.downgrade(cfg, "0010")
    try:
        assert filas("select version_num from alembic_version") == [("0010",)]
        assert transaccion(PROV(), borra(mundo["p"]["C"]))[0] == "42501"                  # sin el permiso de borrado
        assert transaccion(PROV(), cierra(mundo["p"]["C"], dia(5))) == ("ok", None)         # lo de 0010 sigue
        assert filas("select tgname from pg_trigger where tgname like 'pertenencia_solo%' and not tgisinternal") == [("pertenencia_solo_se_cierra_el_ultimo",)]
        with get_owner_engine().begin() as c:
            c.execute(text("update pertenencia set hasta_exclusivo = null where persona_id = :p"), {"p": mundo["p"]["C"]})
    finally:
        command.upgrade(cfg, "head")
    despues = (filas("select * from pertenencia order by id"), filas("select * from equipo order by id"), filas("select * from persona order by id"))
    assert despues == antes
    assert filas("select tgname from pg_trigger where tgname like 'pertenencia_solo%' and not tgisinternal") == [("pertenencia_solo_cambia_lo_programado",)]
    programado(mundo, "N", "V", "supervisor", dia(5))
    assert transaccion(PROV(), borra(mundo["p"]["N"])) == ("ok", None)                      # el permiso vuelve


def test_la_migracion_no_toca_la_auditoria_ni_los_datos_funcionales(mundo):
    assert contar("auditoria") == 0 and contar("bitacora") == 0 and contar("actividad") == 0
