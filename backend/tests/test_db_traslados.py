"""M1-T3 — la base de datos de los traslados y cambios de rol: migración 0010 y sus protecciones.

Intentos REALES con el rol de provisión sobre PostgreSQL. Lo que se prueba:

- el único permiso nuevo del rol de provisión (``UPDATE (hasta_exclusivo)`` sobre ``pertenencia``) y que sigue sin poder
  tocar nada más ni borrar;
- ``pertenencia_solo_cambia_lo_programado`` (0011, sustituye al de 0010): el historial efectivo no se modifica (IR-30), y
  solo se cambia o se borra lo programado (M1-T4: ver también test_db_programacion.py);
- ``pertenencia_supervision_del_equipo`` (disparador DIFERIDO de IR-03 e IR-32): COMPATIBLE con traslados, cambios de rol y
  relevos de supervisor hechos en una misma transacción (entre dos sentencias el equipo queda un instante sin supervisor), y
  capaz de rechazar al hacer efectiva la transacción lo que la violaría;
- que ambas protecciones son del rol de provisión (las herramientas de desarrollo y las pruebas preparan líneas temporales
  arbitrarias con el rol propietario);
- la migración sobre una base con datos.

Las pruebas destructivas corren solo sobre ``smartwork_test``.
"""

import threading
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db import get_owner_engine, get_provision_engine
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, hoy
from tests.utiles_m2 import contar, filas

RAIZ = Path(__file__).resolve().parent.parent
HOY = hoy()


def dia(n: int):
    return HOY + timedelta(days=n)


def transaccion(motor, *sentencias):
    """Ejecuta las sentencias en UNA transacción y la CONFIRMA. Devuelve ``("ok", None)`` o ``(sqlstate, restricción)``."""
    try:
        with motor.begin() as c:
            for sql, parametros in sentencias:
                c.execute(text(sql), parametros)
        return "ok", None
    except DBAPIError as error:
        return error.orig.sqlstate, getattr(error.orig.diag, "constraint_name", None)


def cierra(persona, fecha):
    return ("update pertenencia set hasta_exclusivo = :f where persona_id = :p and hasta_exclusivo is null", {"p": persona, "f": fecha})


def abre(persona, equipo, rol, fecha):
    return ("insert into pertenencia (persona_id, equipo_id, rol, desde) values (:p, :e, :r, :d)",
            {"p": persona, "e": equipo, "r": rol, "d": fecha})


@pytest.fixture()
def mundo():
    """Equipo T (supervisor S, colaborador C), equipo U (supervisor SU, colaborador R) y un equipo vacío V, con el rol propietario."""
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c)
        eq = {"T": crear_equipo(c, org, "T"), "U": crear_equipo(c, org, "U"), "V": crear_equipo(c, org, "V")}
        p = {n: crear_persona(c, n) for n in ("S", "C", "SU", "R", "N")}
        for persona, equipo, rol in (("S", "T", "supervisor"), ("C", "T", "colaborador"), ("SU", "U", "supervisor"), ("R", "U", "colaborador")):
            crear_pertenencia(c, p[persona], eq[equipo], rol, desde=dia(-30))
            crear_identidad(c, p[persona], persona.lower(), None)
    return {"org": org, "eq": eq, "p": p}


PROV = get_provision_engine


# ==================================================== privilegios =========================================================

def test_el_rol_de_provision_puede_cerrar_un_intervalo_sin_fin_y_nada_mas(mundo):
    p = mundo["p"]
    assert transaccion(PROV(), cierra(p["C"], dia(5))) == ("ok", None)
    assert filas("select hasta_exclusivo from pertenencia where persona_id = :p", p=p["C"]) == [(dia(5),)]


@pytest.mark.parametrize("sentencia", [
    "update pertenencia set equipo_id = equipo_id", "update pertenencia set rol = rol", "update pertenencia set desde = desde",
    "update pertenencia set persona_id = persona_id", "update pertenencia set id = id",
    "truncate pertenencia",
])
def test_el_rol_de_provision_sigue_sin_poder_cambiar_nada_mas_de_una_pertenencia(mundo, sentencia):
    assert transaccion(PROV(), (sentencia, {}))[0] == "42501", sentencia


def test_la_aplicacion_sigue_sin_poder_escribir_pertenencias(mundo):
    from app.db import get_engine
    assert transaccion(get_engine(), ("update pertenencia set hasta_exclusivo = current_date + 5", {}))[0] == "42501"


def test_el_rol_de_provision_no_tiene_permisos_nuevos_sobre_m2_m3_ni_la_auditoria(mundo):
    for tabla in ("bitacora", "actividad", "planificacion", "avance"):
        assert transaccion(PROV(), (f"update {tabla} set id = id", {}))[0] == "42501"
    for sentencia in ("update auditoria set motivo = 'x'", "delete from auditoria", "select 1 from auditoria"):
        assert transaccion(PROV(), (sentencia, {}))[0] == "42501"


# ==================================================== historial: solo se cierra el último =================================

def test_un_intervalo_cuyo_fin_ya_llego_no_se_modifica_con_el_rol_de_provision(mundo):
    """El historial efectivo (fin igual o anterior a hoy, preparado con el propietario) no se cambia ni se reabre."""
    p, e = mundo["p"], mundo["eq"]
    with get_owner_engine().begin() as c:
        crear_pertenencia(c, p["N"], e["V"], "supervisor", desde=dia(-20), hasta=dia(-10))
    for nuevo in (dia(9), None):
        estado, restriccion = transaccion(PROV(), ("update pertenencia set hasta_exclusivo = cast(:f as date) where persona_id = :p", {"p": p["N"], "f": nuevo}))
        assert (estado, restriccion) == ("23514", "pertenencia_solo_cambia_lo_programado")
    assert filas("select hasta_exclusivo from pertenencia where persona_id = :p", p=p["N"]) == [(dia(-10),)]


def test_un_fin_programado_si_se_puede_mover_o_restituir_pero_no_llevarlo_al_pasado(mundo):
    """Cancelar y sustituir (M1-T4): el fin de un intervalo todavía programado se mueve a otra fecha futura o se restituye."""
    p = mundo["p"]
    assert transaccion(PROV(), cierra(p["C"], dia(5))) == ("ok", None)
    assert transaccion(PROV(), ("update pertenencia set hasta_exclusivo = :f where persona_id = :p", {"p": p["C"], "f": dia(9)})) == ("ok", None)
    assert transaccion(PROV(), ("update pertenencia set hasta_exclusivo = null where persona_id = :p", {"p": p["C"]})) == ("ok", None)
    assert transaccion(PROV(), ("update pertenencia set hasta_exclusivo = null where persona_id = :p", {"p": p["R"]})) == ("ok", None)    # sin cambio
    assert transaccion(PROV(), cierra(p["C"], dia(0)))[1] == "pertenencia_solo_cambia_lo_programado"       # hoy ya no es futuro
    assert transaccion(PROV(), cierra(p["C"], dia(-1)))[1] == "pertenencia_solo_cambia_lo_programado"


def test_el_cierre_debe_ser_posterior_al_inicio_del_intervalo(mundo):
    """Un intervalo que empezará en el futuro no puede cerrarse antes de su inicio (restricción de la tabla)."""
    p, e = mundo["p"], mundo["eq"]
    with get_owner_engine().begin() as c:
        crear_pertenencia(c, p["N"], e["V"], "supervisor", desde=dia(10))
    assert transaccion(PROV(), cierra(p["N"], dia(5)))[1] == "pertenencia_intervalo_valido"
    assert transaccion(PROV(), cierra(p["N"], dia(10)))[1] == "pertenencia_intervalo_valido"
    assert transaccion(PROV(), cierra(p["N"], dia(11))) == ("ok", None)


def test_la_proteccion_del_historial_es_del_rol_de_provision_no_del_propietario(mundo):
    """El propietario (migraciones, desarrollo y pruebas) conserva su libertad de preparar datos."""
    p = mundo["p"]
    assert transaccion(get_owner_engine(), cierra(p["C"], dia(5))) == ("ok", None)
    assert transaccion(get_owner_engine(), ("update pertenencia set hasta_exclusivo = :f where persona_id = :p", {"p": p["C"], "f": dia(9)})) == ("ok", None)


# ==================================================== IR-03 e IR-32: disparador diferido ==================================

def test_un_traslado_de_un_colaborador_a_otro_equipo_con_supervisor_se_acepta(mundo):
    p, e = mundo["p"], mundo["eq"]
    assert transaccion(PROV(), cierra(p["C"], dia(3)), abre(p["C"], e["U"], "colaborador", dia(3))) == ("ok", None)


def test_el_relevo_de_supervisor_en_una_sola_transaccion_se_acepta_aunque_entre_sentencias_el_equipo_quede_sin_supervisor(mundo):
    """El saliente (S) deja T y el entrante (R, que era colaborador de U) asume la supervisión de T el mismo día."""
    p, e = mundo["p"], mundo["eq"]
    f = dia(4)
    assert transaccion(PROV(), cierra(p["S"], f), cierra(p["R"], f), abre(p["R"], e["T"], "supervisor", f), abre(p["S"], e["U"], "colaborador", f)) == ("ok", None)
    assert filas("select rol from pertenencia where equipo_id = :t and desde = :f", t=e["T"], f=f) == [("supervisor",)]


def test_una_comprobacion_inmediata_rechazaria_ese_mismo_relevo_valido(mundo):
    """Por qué el disparador es DIFERIDO: forzado a inmediato, la primera sentencia del relevo ya lo rechaza."""
    p, e = mundo["p"], mundo["eq"]
    f = dia(4)
    estado, restriccion = transaccion(
        PROV(), ("set constraints pertenencia_supervision_del_equipo immediate", {}), cierra(p["S"], f))
    assert (estado, restriccion) == ("23514", "pertenencia_supervision_del_equipo")


def test_el_orden_de_las_sentencias_de_un_relevo_no_importa_para_el_disparador_diferido(mundo):
    """Aperturas y cierres en cualquier orden: solo el resultado final cuenta (las exclusiones de la base sí exigen cerrar antes de abrir)."""
    p, e = mundo["p"], mundo["eq"]
    f = dia(4)
    assert transaccion(PROV(), cierra(p["R"], f), cierra(p["S"], f), abre(p["S"], e["U"], "colaborador", f), abre(p["R"], e["T"], "supervisor", f)) == ("ok", None)


def test_el_cambio_de_rol_cruzado_dentro_del_mismo_equipo_se_acepta(mundo):
    """S pasa a colaborador y C a supervisor de T el mismo día."""
    p, e = mundo["p"], mundo["eq"]
    f = dia(2)
    assert transaccion(PROV(), cierra(p["S"], f), cierra(p["C"], f), abre(p["C"], e["T"], "supervisor", f), abre(p["S"], e["T"], "colaborador", f)) == ("ok", None)


def test_un_traslado_sucesivo_programado_se_acepta(mundo):
    p, e = mundo["p"], mundo["eq"]
    assert transaccion(PROV(), cierra(p["C"], dia(3)), abre(p["C"], e["U"], "colaborador", dia(3))) == ("ok", None)
    assert transaccion(PROV(), cierra(p["C"], dia(6)), abre(p["C"], e["V"], "supervisor", dia(6))) == ("ok", None)     # V estaba vacío


def test_sacar_al_unico_supervisor_con_colaboradores_se_rechaza_al_confirmar(mundo):
    p = mundo["p"]
    estado, restriccion = transaccion(PROV(), cierra(p["S"], dia(5)))
    assert (estado, restriccion) == ("23514", "pertenencia_supervision_del_equipo")
    assert filas("select hasta_exclusivo from pertenencia where persona_id = :p", p=p["S"]) == [(None,)]    # la transacción se deshizo


def test_un_relevo_con_un_dia_sin_supervisor_se_rechaza(mundo):
    p, e = mundo["p"], mundo["eq"]
    assert transaccion(PROV(), cierra(p["S"], dia(5)), cierra(p["R"], dia(6)), abre(p["R"], e["T"], "supervisor", dia(6)))[1] == "pertenencia_supervision_del_equipo"


def test_un_colaborador_sin_supervisor_en_el_equipo_destino_se_rechaza(mundo):
    p, e = mundo["p"], mundo["eq"]
    assert transaccion(PROV(), cierra(p["C"], dia(3)), abre(p["C"], e["V"], "colaborador", dia(3)))[1] == "pertenencia_supervision_del_equipo"


def test_un_supervisor_puede_entrar_en_un_equipo_vacio_y_despues_un_colaborador(mundo):
    p, e = mundo["p"], mundo["eq"]
    assert transaccion(PROV(), abre(p["N"], e["V"], "supervisor", dia(1))) == ("ok", None)


def test_dos_supervisores_a_la_vez_los_impide_la_exclusion_de_la_base_antes_de_confirmar(mundo):
    p, e = mundo["p"], mundo["eq"]
    estado, restriccion = transaccion(PROV(), cierra(p["C"], dia(3)), abre(p["C"], e["T"], "supervisor", dia(3)))
    assert (estado, restriccion) == ("23P01", "pertenencia_un_supervisor_por_equipo_y_fecha")


def test_el_disparador_solo_mira_desde_la_fecha_afectada(mundo):
    """Una situación irregular PREVIA y pasada (preparada con el propietario) no bloquea un cambio válido y posterior."""
    p, e = mundo["p"], mundo["eq"]
    with get_owner_engine().begin() as c:
        crear_pertenencia(c, p["N"], e["V"], "colaborador", desde=dia(-20), hasta=dia(-10))     # colaborador sin supervisor, en el pasado
    assert transaccion(PROV(), cierra(p["C"], dia(3)), abre(p["C"], e["U"], "colaborador", dia(3))) == ("ok", None)


def test_el_disparador_es_del_rol_de_provision_el_propietario_prepara_lineas_arbitrarias(mundo):
    p = mundo["p"]
    assert transaccion(get_owner_engine(), cierra(p["S"], dia(5))) == ("ok", None)      # deja a T sin supervisor: el propietario puede (datos de prueba y desarrollo)


def test_muchas_filas_del_mismo_equipo_en_una_transaccion_se_evaluan_juntas(mundo):
    p, e = mundo["p"], mundo["eq"]
    with get_owner_engine().begin() as c:
        extra = [crear_persona(c, f"X{i}") for i in range(3)]
        for x in extra:
            crear_pertenencia(c, x, e["T"], "colaborador", desde=dia(-30))
    sentencias = []
    for x in extra:
        sentencias += [cierra(x, dia(3)), abre(x, e["U"], "colaborador", dia(3))]
    assert transaccion(PROV(), *sentencias) == ("ok", None)


# ==================================================== índice y migración ==================================================

def test_el_indice_por_equipo_existe(mundo):
    assert filas("select indexname from pg_indexes where indexname = 'pertenencia_equipo_idx'") == [("pertenencia_equipo_idx",)]


def _alembic() -> Config:
    return Config(str(RAIZ / "alembic.ini"))


def test_la_migracion_0010_se_aplica_sobre_datos_existentes_sin_alterarlos_y_se_revierte(mundo):
    cfg = _alembic()
    antes = (filas("select * from pertenencia order by id"), filas("select * from equipo order by id"), filas("select * from persona order by id"))
    command.downgrade(cfg, "0009")                      # revierte 0011 y 0010
    try:
        assert filas("select version_num from alembic_version") == [("0009",)]
        assert transaccion(PROV(), cierra(mundo["p"]["C"], dia(5)))[0] == "42501"        # el permiso nuevo desaparece al revertir
        assert filas("select indexname from pg_indexes where indexname = 'pertenencia_equipo_idx'") == []
        assert filas("select tgname from pg_trigger where tgname like 'pertenencia_%' and not tgisinternal") == []
    finally:
        command.upgrade(cfg, "head")
    despues = (filas("select * from pertenencia order by id"), filas("select * from equipo order by id"), filas("select * from persona order by id"))
    assert despues == antes
    assert transaccion(PROV(), cierra(mundo["p"]["C"], dia(5))) == ("ok", None)           # y vuelve


def test_los_dos_disparadores_existen_y_el_de_supervision_es_diferido(mundo):
    fila = filas("select tgname, tgdeferrable, tginitdeferred from pg_trigger where tgname in "
                 "('pertenencia_supervision_del_equipo', 'pertenencia_solo_cambia_lo_programado') order by tgname")
    assert fila == [("pertenencia_solo_cambia_lo_programado", False, False), ("pertenencia_supervision_del_equipo", True, True)]


def test_la_migracion_no_toca_la_auditoria_ni_los_datos_funcionales(mundo):
    assert contar("auditoria") == 0 and contar("bitacora") == 0
