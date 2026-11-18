"""M1-T1 — «Equipo en una fecha» (DM-04) y política de visibilidad histórica (BE-02, RA-01 a RA-12, RN-36).

Se prueba con PostgreSQL real y líneas temporales de pertenencia preparadas, sin ninguna operación HTTP: la política es una
base interna que todavía no usa ninguna consulta. Criterios relacionados (solo a nivel de política interna; su prueba de
extremo a extremo es de M4): CA-15 a CA-21, CA-176 a CA-178, CA-212 a CA-217, CA-249 y CA-286; RA-01 a RA-12, IR-27, IR-37 e IR-38.
Las pruebas destructivas corren solo sobre ``smartwork_test``; la política lee con el rol de la aplicación (solo SELECT).
"""

import random
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido import pertenencias
from app.compartido.visibilidad import (
    Consultante, Decision, EntradaDeAuditoria, Forma, Motivo, Registro, condicion_lectura,
    condicion_lectura_auditoria, consultante_de, decidir_lectura, decidir_lectura_de_auditoria, forma_de_actividad,
)
from app.db import get_engine, get_owner_engine
from tests.fabricas import crear_equipo, crear_organizacion, crear_persona, crear_pertenencia

D = date
X = D(2026, 3, 1)            # fecha efectiva del traslado de P del equipo T al equipo U
HOY = D(2026, 6, 15)
AHORA = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
ABIERTO = None
RAIZ = Path(__file__).resolve().parent.parent


@dataclass
class Mundo:
    """Líneas temporales preparadas. ``p`` son personas, ``eq`` equipos (T, U, W en la organización A; V en la B)."""

    p: dict
    eq: dict


@pytest.fixture()
def mundo():
    with get_owner_engine().begin() as c:
        org_a, org_b = crear_organizacion(c), crear_organizacion(c)
        eq = {"T": crear_equipo(c, org_a, "T"), "U": crear_equipo(c, org_a, "U"), "W": crear_equipo(c, org_a, "W"),
              "Y": crear_equipo(c, org_a, "Y"), "V": crear_equipo(c, org_b, "V")}
        p = {n: crear_persona(c, n) for n in ("P", "QT", "ST", "Q2", "QU", "SU", "EX", "RC", "WC", "N", "D", "F", "Z", "SZ", "DSV")}

        def pert(persona, equipo, rol, desde, hasta=ABIERTO):
            crear_pertenencia(c, p[persona], eq[equipo], rol, desde=desde, hasta=hasta)

        pert("ST", "T", "supervisor", D(2025, 1, 1))
        pert("SU", "U", "supervisor", D(2025, 1, 1))
        pert("P", "T", "colaborador", D(2025, 1, 1), X)          # P se traslada de T a U el 2026-03-01
        pert("P", "U", "colaborador", X)
        pert("QT", "T", "colaborador", D(2025, 1, 1))
        pert("Q2", "T", "colaborador", D(2026, 4, 1))             # se incorporó a T después del traslado
        pert("QU", "U", "colaborador", D(2025, 1, 1))
        pert("EX", "T", "supervisor", D(2024, 1, 1), D(2025, 1, 1))  # supervisor ANTERIOR de T
        pert("EX", "U", "colaborador", D(2025, 1, 1))
        pert("WC", "W", "colaborador", D(2025, 1, 1))
        pert("RC", "W", "colaborador", D(2025, 1, 1), D(2026, 2, 1))  # cambio de rol dentro del mismo equipo
        pert("RC", "W", "supervisor", D(2026, 2, 1))
        pert("N", "T", "colaborador", D(2025, 1, 1), D(2026, 5, 1))   # su pertenencia terminó antes de hoy
        pert("D", "T", "colaborador", D(2025, 1, 1))                  # acceso desactivado (abajo)
        pert("F", "T", "colaborador", D(2026, 7, 1))                  # su pertenencia empieza después de hoy
        pert("Z", "V", "colaborador", D(2025, 1, 1))                  # otra organización
        pert("SZ", "V", "supervisor", D(2025, 1, 1))
        pert("DSV", "Y", "supervisor", D(2025, 1, 1))                 # supervisor con el acceso desactivado
        c.execute(text("update persona set acceso_desactivado_en = :t where id in (:d, :s)"),
                  {"t": datetime(2026, 6, 1, tzinfo=timezone.utc), "d": p["D"], "s": p["DSV"]})
    return Mundo(p, eq)


@pytest.fixture()
def db():
    with Session(get_engine()) as sesion:  # el rol de la aplicación: solo SELECT sobre estas tablas
        yield sesion


def quien(db, mundo, nombre, hoy=HOY, ahora=AHORA) -> Consultante:
    return consultante_de(db, mundo.p[nombre], hoy=hoy, ahora=ahora)


def lectura(db, mundo, consultante, dueña, fecha) -> Decision:
    return decidir_lectura(db, quien(db, mundo, consultante), Registro(mundo.p[dueña], fecha))


TODOS = ["P", "QT", "ST", "Q2", "QU", "SU", "EX", "RC", "WC", "N", "D", "F", "Z", "SZ", "DSV"]


# ==================================================== equipo en una fecha (DM-04) =========================================

def test_los_intervalos_son_semiabiertos_y_el_limite_exacto_pertenece_al_siguiente(db, mundo):
    p = mundo.p["P"]
    assert pertenencias.pertenencia_en_fecha(db, p, D(2024, 12, 31)) is None            # un día antes de la primera
    assert pertenencias.equipo_en_fecha(db, p, D(2025, 1, 1)) == mundo.eq["T"]           # `desde` es inclusivo
    assert pertenencias.equipo_en_fecha(db, p, X - timedelta(days=1)) == mundo.eq["T"]   # último día de T
    assert pertenencias.equipo_en_fecha(db, p, X) == mundo.eq["U"]                       # `hasta_exclusivo` ya no es de T
    assert pertenencias.equipo_en_fecha(db, p, D(2030, 1, 1)) == mundo.eq["U"]           # el último intervalo no tiene fin


def test_una_persona_sin_fin_de_pertenencia_y_una_programada(db, mundo):
    n, f = mundo.p["N"], mundo.p["F"]
    assert pertenencias.equipo_en_fecha(db, n, D(2026, 4, 30)) == mundo.eq["T"]
    assert pertenencias.equipo_en_fecha(db, n, D(2026, 5, 1)) is None                    # el día de `hasta_exclusivo`
    assert pertenencias.equipo_en_fecha(db, f, D(2026, 6, 30)) is None                   # todavía no empieza
    assert pertenencias.equipo_en_fecha(db, f, D(2026, 7, 1)) == mundo.eq["T"]           # programada: se evalúa (RA-02)


def test_el_cambio_de_rol_dentro_del_mismo_equipo_conserva_el_equipo(db, mundo):
    rc = mundo.p["RC"]
    antes, despues = (pertenencias.pertenencia_en_fecha(db, rc, D(2026, 1, 31)), pertenencias.pertenencia_en_fecha(db, rc, D(2026, 2, 1)))
    assert (antes.rol, despues.rol) == ("colaborador", "supervisor")
    assert antes.equipo_id == despues.equipo_id == mundo.eq["W"]


def test_la_pertenencia_incluye_la_organizacion_del_equipo(db, mundo):
    z = pertenencias.pertenencia_en_fecha(db, mundo.p["Z"], HOY)
    p = pertenencias.pertenencia_en_fecha(db, mundo.p["P"], HOY)
    assert z.organizacion_id != p.organizacion_id
    assert z.equipo_id == mundo.eq["V"] and p.equipo_id == mundo.eq["U"]


def test_una_persona_inexistente_no_tiene_equipo(db, mundo):
    import uuid
    assert pertenencias.pertenencia_en_fecha(db, uuid.uuid4(), HOY) is None


# ==================================================== el consultante ======================================================

def test_la_situacion_vigente_del_consultante(db, mundo):
    assert quien(db, mundo, "P").puede_operar and quien(db, mundo, "P").pertenencia.equipo_id == mundo.eq["U"]
    assert not quien(db, mundo, "N").puede_operar and quien(db, mundo, "N").acceso_activo       # sin pertenencia vigente
    assert not quien(db, mundo, "F").puede_operar                                                # empieza después de hoy
    assert not quien(db, mundo, "D").puede_operar and not quien(db, mundo, "D").acceso_activo    # acceso desactivado


def test_los_limites_de_la_pertenencia_vigente_y_de_la_desactivacion(db, mundo):
    assert quien(db, mundo, "N", hoy=D(2026, 4, 30)).puede_operar and not quien(db, mundo, "N", hoy=D(2026, 5, 1)).puede_operar
    assert not quien(db, mundo, "F", hoy=D(2026, 6, 30)).puede_operar and quien(db, mundo, "F", hoy=D(2026, 7, 1)).puede_operar
    antes = datetime(2026, 5, 31, 23, 59, 59, tzinfo=timezone.utc)
    justo = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert quien(db, mundo, "D", ahora=antes).acceso_activo and not quien(db, mundo, "D", ahora=justo).acceso_activo


def test_una_persona_inexistente_no_puede_consultar(db, mundo):
    import uuid
    c = consultante_de(db, uuid.uuid4(), hoy=HOY, ahora=AHORA)
    assert not c.puede_operar and decidir_lectura(db, c, Registro(mundo.p["P"], X)).motivo == Motivo.ACCESO_DESACTIVADO


# ==================================================== matriz de lectura (RA-01, RA-03, RA-11, RN-36) ======================

# Registros de P (trasladada de T a U el 2026-03-01) y quién los lee. Cada fila: fecha laboral -> consultantes autorizados.
LECTORES_DE_P = {
    D(2025, 1, 1): {"P", "QT", "ST", "Q2"},      # primer día de P en T (límite inferior inclusivo)
    X - timedelta(days=1): {"P", "QT", "ST", "Q2"},   # último día de P en T: lo leen los de T, también quien se incorporó después (CA-15, CA-176)
    X: {"P", "QU", "SU", "EX"},                 # primer día de P en U: lo leen los de U y no los de T (CA-16, CA-17, CA-18)
    D(2026, 7, 1): {"P", "QU", "SU", "EX"},     # planificación futura: se evalúa con la pertenencia aplicable a su fecha (RA-02, CA-216, CA-217)
    D(2024, 12, 31): {"P"},                     # sin pertenencia en esa fecha: planificación conservada, solo la propietaria (RA-11)
}


@pytest.mark.parametrize("fecha", sorted(LECTORES_DE_P))
def test_matriz_de_lectura_de_los_registros_de_una_persona_trasladada(db, mundo, fecha):
    lee = {n for n in TODOS if lectura(db, mundo, n, "P", fecha).visible}
    assert lee == LECTORES_DE_P[fecha], (fecha, lee ^ LECTORES_DE_P[fecha])


def test_motivos_internos_de_cada_caso(db, mundo):
    en_t = X - timedelta(days=1)
    m = lambda c, f=en_t, dueña="P": lectura(db, mundo, c, dueña, f).motivo  # noqa: E731
    assert m("P") == Motivo.PROPIETARIA
    assert m("QT") == m("ST") == m("Q2") == Motivo.EQUIPO_HISTORICO
    assert m("QU") == m("SU") == m("EX") == Motivo.OTRO_EQUIPO         # equipo actual distinto del de la fecha
    assert m("WC") == m("RC") == Motivo.OTRO_EQUIPO
    assert m("Z") == m("SZ") == Motivo.OTRA_ORGANIZACION
    assert m("N") == m("F") == Motivo.SIN_PERTENENCIA_VIGENTE
    assert m("D") == m("DSV") == Motivo.ACCESO_DESACTIVADO
    assert m("QT", D(2024, 12, 31)) == Motivo.SIN_EQUIPO_EN_LA_FECHA   # RA-11
    assert m("P", D(2024, 12, 31)) == Motivo.PROPIETARIA


def test_quien_se_incorporo_despues_lee_el_historico_de_su_equipo_pero_no_el_de_otro(db, mundo):
    """CA-176 y CA-177: Q2 entró en T el 2026-04-01 y lee lo de T de fechas anteriores a su ingreso, nunca lo de U."""
    assert lectura(db, mundo, "Q2", "QT", D(2025, 5, 5)).visible
    assert lectura(db, mundo, "Q2", "P", D(2025, 5, 5)).visible
    assert not lectura(db, mundo, "Q2", "P", D(2026, 5, 5)).visible          # P ya estaba en U
    assert not lectura(db, mundo, "Q2", "QU", D(2026, 5, 5)).visible


def test_el_supervisor_de_un_equipo_anterior_conserva_lo_de_su_equipo_y_no_lo_ajeno(db, mundo):
    """El supervisor de T sigue leyendo lo que P hizo en T tras su traslado a U (CA-15) y no lo que hace en U (CA-17)."""
    assert lectura(db, mundo, "ST", "P", D(2026, 1, 15)).visible
    assert not lectura(db, mundo, "ST", "P", D(2026, 4, 15)).visible
    # y el supervisor ANTERIOR de T (ahora colaborador de U) no conserva ninguna lectura de T
    assert not lectura(db, mundo, "EX", "QT", D(2025, 5, 5)).visible
    assert lectura(db, mundo, "EX", "QU", D(2025, 5, 5)).visible


def test_el_cambio_de_rol_no_cambia_el_equipo_de_los_registros(db, mundo):
    """RC fue colaborador de W y ahora supervisa W: lee lo de W de antes y de después de su ascenso; WC lee los de RC."""
    for fecha in (D(2025, 6, 1), D(2026, 1, 31), D(2026, 2, 1), D(2026, 5, 1)):
        assert lectura(db, mundo, "RC", "WC", fecha).visible
        assert lectura(db, mundo, "WC", "RC", fecha).visible


def test_nadie_cruza_organizaciones(db, mundo):
    for dueña in ("P", "QT", "ST", "WC"):
        for fecha in (D(2025, 5, 5), D(2026, 5, 5)):
            assert not lectura(db, mundo, "Z", dueña, fecha).visible and not lectura(db, mundo, "SZ", dueña, fecha).visible
    for consultante in ("P", "QT", "ST", "SU", "WC"):
        assert not lectura(db, mundo, consultante, "Z", D(2026, 5, 5)).visible
        assert not lectura(db, mundo, consultante, "SZ", D(2026, 5, 5)).visible


def test_con_el_acceso_desactivado_o_sin_pertenencia_no_se_consulta_ni_lo_propio(db, mundo):
    for nombre in ("D", "DSV", "N", "F"):
        assert not lectura(db, mundo, nombre, nombre, D(2025, 5, 5)).visible


def test_un_registro_sin_fecha_solo_lo_lee_la_propietaria(db, mundo):
    assert lectura(db, mundo, "P", "P", None).visible
    assert lectura(db, mundo, "QT", "P", None).motivo == Motivo.SIN_EQUIPO_EN_LA_FECHA


# ==================================================== auditoría (RA-10) y supervisión (RA-12) =============================

def _aud(db, mundo, consultante, dueña, fecha, autor="persona") -> Decision:
    return decidir_lectura_de_auditoria(db, quien(db, mundo, consultante), EntradaDeAuditoria(mundo.p[dueña], fecha, autor))


def test_matriz_de_auditoria_propietaria_y_supervisor_autorizado_del_equipo_de_la_fecha(db, mundo):
    en_t, en_u = X - timedelta(days=1), X
    lee_en_t = {n for n in TODOS if _aud(db, mundo, n, "P", en_t).visible}
    lee_en_u = {n for n in TODOS if _aud(db, mundo, n, "P", en_u).visible}
    assert lee_en_t == {"P", "ST"}          # la propietaria y el supervisor de T; ni los compañeros ni el de U
    assert lee_en_u == {"P", "SU"}
    assert {n for n in TODOS if _aud(db, mundo, n, "P", D(2024, 12, 31)).visible} == {"P"}


def test_motivos_de_la_auditoria(db, mundo):
    en_t = X - timedelta(days=1)
    assert _aud(db, mundo, "P", "P", en_t).motivo == Motivo.PROPIETARIA
    assert _aud(db, mundo, "ST", "P", en_t).motivo == Motivo.SUPERVISION_DEL_EQUIPO_HISTORICO
    assert _aud(db, mundo, "QT", "P", en_t).motivo == Motivo.NO_ES_SUPERVISION     # un compañero lee el registro, no su auditoría
    assert _aud(db, mundo, "SU", "P", en_t).motivo == Motivo.OTRO_EQUIPO
    assert _aud(db, mundo, "SZ", "P", en_t).motivo == Motivo.OTRA_ORGANIZACION
    assert _aud(db, mundo, "DSV", "QT", en_t).motivo == Motivo.ACCESO_DESACTIVADO
    assert _aud(db, mundo, "EX", "QT", en_t).motivo == Motivo.OTRO_EQUIPO          # el supervisor anterior ya no supervisa T


def test_el_supervisor_actual_ve_la_auditoria_de_fechas_anteriores_a_su_ascenso(db, mundo):
    """RA-10: «supervisor autorizado del equipo de fecha_laboral_registro»: RC supervisa W desde 2026-02-01 y ve la de antes."""
    assert _aud(db, mundo, "RC", "WC", D(2025, 6, 1)).visible
    assert not _aud(db, mundo, "WC", "RC", D(2025, 6, 1)).visible


def test_las_entradas_de_provision_no_se_muestran_a_nadie(db, mundo):
    for nombre in TODOS:
        d = _aud(db, mundo, nombre, "P", X - timedelta(days=1), autor="provision")
        assert not d.visible
    assert _aud(db, mundo, "P", "P", X, autor="provision").motivo == Motivo.PROVISION_SIN_VISIBILIDAD_DEFINIDA
    assert _aud(db, mundo, "D", "P", X, autor="provision").motivo == Motivo.ACCESO_DESACTIVADO   # el acceso se evalúa antes


def test_la_supervision_deriva_solo_de_un_intervalo_vigente_con_acceso_efectivo(db, mundo):
    sup = lambda n, e: quien(db, mundo, n).supervisa(mundo.eq[e])  # noqa: E731
    assert sup("ST", "T") and sup("SU", "U") and sup("RC", "W") and sup("SZ", "V")
    assert not sup("ST", "U") and not sup("SU", "T")        # un supervisor no supervisa otro equipo
    assert not sup("QT", "T") and not sup("WC", "W")        # un colaborador no supervisa
    assert not sup("EX", "T") and not sup("EX", "U")        # el supervisor anterior no conserva ni transfiere permisos
    assert not sup("DSV", "Y")                              # con el acceso desactivado no ejerce supervisión
    assert not sup("F", "T") and not sup("N", "T")          # sin pertenencia vigente


def test_con_la_fecha_actual_anterior_al_ascenso_no_se_supervisa(db, mundo):
    assert not consultante_de(db, mundo.p["RC"], hoy=D(2026, 1, 31), ahora=AHORA).supervisa(mundo.eq["W"])
    assert consultante_de(db, mundo.p["RC"], hoy=D(2026, 2, 1), ahora=AHORA).supervisa(mundo.eq["W"])


# ==================================================== forma de la actividad (RA-04, RA-08) ================================

def test_forma_de_una_actividad_segun_la_jornada_de_origen(db, mundo):
    origen = Registro(mundo.p["P"], X - timedelta(days=1))    # iniciada en T
    forma = lambda c, marcada=False: forma_de_actividad(db, quien(db, mundo, c), origen, marcada_por_error=marcada)  # noqa: E731
    for autorizados in ("P", "QT", "ST", "Q2"):
        assert forma(autorizados) == Forma.COMPLETA and forma(autorizados, True) == Forma.COMPLETA
    for ajeno in ("QU", "SU", "EX", "Z", "SZ", "WC"):
        assert forma(ajeno) == Forma.NEUTRAL                 # RA-04: referencia neutral, sin título
        assert forma(ajeno, True) == Forma.OCULTA            # RA-08: la marcada no aparece ni como referencia mínima
    for fuera in ("D", "DSV", "N", "F"):
        assert forma(fuera) == Forma.OCULTA and forma(fuera, True) == Forma.OCULTA


# ==================================================== el predicado SQL es la misma regla ==================================

def _visibles_por_sql(db, consultante, registros):
    """``registros``: lista de (id, propietaria, fecha). Selecciona con el predicado compuesto, sobre una lista de valores."""
    if not registros:
        return set()
    filas = ", ".join(f"(cast(:i{k} as int), cast(:p{k} as uuid), cast(:f{k} as date))" for k in range(len(registros)))
    parametros = {}
    for k, (i, dueña, fecha) in enumerate(registros):
        parametros.update({f"i{k}": i, f"p{k}": dueña, f"f{k}": fecha})
    sql, extra = condicion_lectura(consultante, "r.prop", "r.fecha")
    consulta = f"select r.id from (values {filas}) as r(id, prop, fecha) where {sql}"
    return {fila[0] for fila in db.execute(text(consulta), {**parametros, **extra})}


def _visibles_por_sql_auditoria(db, consultante, registros):
    filas = ", ".join(f"(cast(:i{k} as int), cast(:p{k} as uuid), cast(:f{k} as date), :a{k})" for k in range(len(registros)))
    parametros = {}
    for k, (i, dueña, fecha, autor) in enumerate(registros):
        parametros.update({f"i{k}": i, f"p{k}": dueña, f"f{k}": fecha, f"a{k}": autor})
    sql, extra = condicion_lectura_auditoria(consultante, "r.prop", "r.fecha", "r.autor")
    consulta = f"select r.id from (values {filas}) as r(id, prop, fecha, autor) where {sql}"
    return {fila[0] for fila in db.execute(text(consulta), {**parametros, **extra})}


def test_el_predicado_sql_selecciona_exactamente_lo_que_decide_la_politica(db, mundo):
    registros = [(k, mundo.p[dueña], fecha) for k, (dueña, fecha) in enumerate(
        (d, f) for d in ("P", "QT", "QU", "ST", "WC", "RC", "Z", "N", "D") for f in
        (D(2024, 12, 31), D(2025, 1, 1), D(2026, 2, 28), D(2026, 3, 1), D(2026, 4, 1), D(2026, 7, 1)))]
    for nombre in TODOS:
        c = quien(db, mundo, nombre)
        por_politica = {i for i, dueña, fecha in registros if decidir_lectura(db, c, Registro(dueña, fecha)).visible}
        assert _visibles_por_sql(db, c, registros) == por_politica, nombre


def test_el_predicado_sql_de_auditoria_selecciona_exactamente_lo_que_decide_la_politica(db, mundo):
    registros = [(k, mundo.p[d], f, a) for k, (d, f, a) in enumerate(
        (d, f, a) for d in ("P", "QT", "QU", "WC", "RC", "Z") for f in (D(2025, 1, 1), D(2026, 2, 28), D(2026, 3, 1), D(2026, 7, 1))
        for a in ("persona", "provision"))]
    for nombre in TODOS:
        c = quien(db, mundo, nombre)
        por_politica = {i for i, dueña, fecha, autor in registros
                        if decidir_lectura_de_auditoria(db, c, EntradaDeAuditoria(dueña, fecha, autor)).visible}
        assert _visibles_por_sql_auditoria(db, c, registros) == por_politica, nombre


def test_quien_no_puede_operar_no_selecciona_nada(db, mundo):
    for nombre in ("D", "DSV", "N", "F"):
        sql, params = condicion_lectura(quien(db, mundo, nombre), "r.prop", "r.fecha")
        assert (sql, params) == ("false", {})
        assert condicion_lectura_auditoria(quien(db, mundo, nombre), "r.prop", "r.fecha", "r.autor") == ("false", {})


def test_los_predicados_solo_aceptan_identificadores_escritos_por_el_codigo(db, mundo):
    c = quien(db, mundo, "P")
    for malo in ("r.prop; drop table pertenencia", "r.prop or true", "1", "a.b.c", "r.prop --"):
        with pytest.raises(ValueError):
            condicion_lectura(c, malo, "r.fecha")
        with pytest.raises(ValueError):
            condicion_lectura(c, "r.prop", malo)
    with pytest.raises(ValueError):
        condicion_lectura(c, "r.prop", "r.fecha", prefijo="x; drop")


def test_dos_condiciones_en_la_misma_consulta_no_colisionan(db, mundo):
    c = quien(db, mundo, "QT")
    s1, p1 = condicion_lectura(c, "r.a", "r.fa", prefijo="uno")
    s2, p2 = condicion_lectura(c, "r.b", "r.fb", prefijo="dos")
    assert not (set(p1) & set(p2))
    fila = db.execute(text(f"select 1 from (select cast(:a as uuid) as a, cast(:b as uuid) as b, date '2026-02-28' as fa, "
                           f"date '2026-02-28' as fb) r where {s1} and {s2}"),
                      {**p1, **p2, "a": mundo.p["P"], "b": mundo.p["ST"]}).first()
    assert fila is not None


# ==================================================== propiedades sobre líneas temporales aleatorias ======================

def _mundo_aleatorio(semilla: int):
    """Personas con líneas temporales aleatorias (con huecos, traslados y cambios de rol) en dos organizaciones. Devuelve
    (ids de persona, modelo en Python de los intervalos) para contrastar con la política sin usar SQL."""
    azar = random.Random(semilla)
    modelo: dict = {}   # persona -> lista de (equipo, organizacion, rol, desde, hasta)
    ids: dict = {}
    with get_owner_engine().begin() as c:
        orgs = [crear_organizacion(c), crear_organizacion(c)]
        equipos = [(crear_equipo(c, orgs[k % 2], f"E{k}"), orgs[k % 2]) for k in range(6)]
        base = D(2025, 1, 1)
        for n in range(24):
            persona = crear_persona(c, f"A{n}")
            ids[n] = persona
            modelo[persona] = []
            cursor = base + timedelta(days=azar.randint(0, 120))
            for _ in range(azar.randint(1, 4)):
                equipo, org = azar.choice(equipos)
                rol = "colaborador"
                largo = azar.randint(1, 200)
                hasta = None if azar.random() < 0.2 else cursor + timedelta(days=largo)
                crear_pertenencia(c, persona, equipo, rol, desde=cursor, hasta=hasta)
                modelo[persona].append((equipo, org, rol, cursor, hasta))
                if hasta is None:
                    break
                cursor = hasta + timedelta(days=azar.choice([0, 0, 0, 1, 5, 30]))  # contiguo, o con hueco
        # supervisores: un intervalo por persona y equipo, en ventanas disjuntas dentro de cada equipo
        for k, (equipo, org) in enumerate(equipos):
            inicio = base
            for s in range(3):
                persona = crear_persona(c, f"S{k}-{s}")
                ids[f"S{k}-{s}"] = persona
                fin = inicio + timedelta(days=azar.randint(30, 150))
                ultimo = s == 2
                crear_pertenencia(c, persona, equipo, "supervisor", desde=inicio, hasta=None if ultimo else fin)
                modelo[persona] = [(equipo, org, "supervisor", inicio, None if ultimo else fin)]
                inicio = fin
    return ids, modelo


def _equipo_modelo(modelo, persona, fecha):
    """Búsqueda lineal independiente de SQL: el intervalo [desde, hasta) que contiene la fecha."""
    for equipo, org, rol, desde, hasta in modelo[persona]:
        if desde <= fecha and (hasta is None or fecha < hasta):
            return equipo, org, rol
    return None


def _lectura_modelo(modelo, consultante, propietaria, fecha, hoy):
    vigente = _equipo_modelo(modelo, consultante, hoy)
    if vigente is None:
        return False
    if propietaria == consultante:
        return True
    del_registro = _equipo_modelo(modelo, propietaria, fecha)
    return del_registro is not None and del_registro[0] == vigente[0] and del_registro[1] == vigente[1]


@pytest.mark.parametrize("semilla", [11, 23, 47])
def test_propiedad_equipo_en_una_fecha_coincide_con_la_busqueda_lineal_en_todas_las_fronteras(db, semilla):
    ids, modelo = _mundo_aleatorio(semilla)
    for persona, intervalos in modelo.items():
        fechas = {d for _, _, _, desde, hasta in intervalos for d in
                  (desde - timedelta(days=1), desde, desde + timedelta(days=1)) + (() if hasta is None else (hasta - timedelta(days=1), hasta, hasta + timedelta(days=1)))}
        fechas |= {D(2024, 6, 1), D(2027, 6, 1)}
        for fecha in fechas:
            esperado = _equipo_modelo(modelo, persona, fecha)
            real = pertenencias.pertenencia_en_fecha(db, persona, fecha)
            assert (None if real is None else (real.equipo_id, real.organizacion_id, real.rol)) == esperado, (persona, fecha)


@pytest.mark.parametrize("semilla", [5, 31])
def test_propiedad_la_politica_y_el_predicado_coinciden_con_el_modelo_y_no_filtran_entre_organizaciones_ni_periodos(db, semilla):
    ids, modelo = _mundo_aleatorio(semilla)
    azar = random.Random(semilla)
    personas = list(modelo)
    fechas = [D(2025, 1, 1) + timedelta(days=azar.randint(0, 500)) for _ in range(40)]
    for _ in range(25):
        hoy = D(2025, 1, 1) + timedelta(days=azar.randint(0, 450))
        consultante_id = azar.choice(personas)
        c = consultante_de(db, consultante_id, hoy=hoy, ahora=AHORA)
        registros = [(k, azar.choice(personas), azar.choice(fechas)) for k in range(30)]
        por_modelo = {i for i, prop, f in registros if _lectura_modelo(modelo, consultante_id, prop, f, hoy)}
        por_politica = {i for i, prop, f in registros if decidir_lectura(db, c, Registro(prop, f)).visible}
        assert por_politica == por_modelo
        assert _visibles_por_sql(db, c, registros) == por_modelo
        for i, prop, f in registros:   # ausencia de filtración: lo visto ajeno es siempre del mismo equipo, organización y fecha cubierta
            if i in por_politica and prop != consultante_id:
                propio = _equipo_modelo(modelo, consultante_id, hoy)
                del_registro = _equipo_modelo(modelo, prop, f)
                assert del_registro is not None and del_registro[:2] == propio[:2]


@pytest.mark.parametrize("semilla", [7, 19])
def test_propiedad_solo_el_supervisor_vigente_del_equipo_de_la_fecha_ve_auditoria_ajena(db, semilla):
    ids, modelo = _mundo_aleatorio(semilla)
    azar = random.Random(semilla)
    personas = list(modelo)
    for _ in range(25):
        hoy = D(2025, 1, 1) + timedelta(days=azar.randint(0, 450))
        consultante_id = azar.choice(personas)
        c = consultante_de(db, consultante_id, hoy=hoy, ahora=AHORA)
        vigente = _equipo_modelo(modelo, consultante_id, hoy)
        for _ in range(30):
            prop, fecha = azar.choice(personas), D(2025, 1, 1) + timedelta(days=azar.randint(0, 500))
            d = decidir_lectura_de_auditoria(db, c, EntradaDeAuditoria(prop, fecha, "persona"))
            del_registro = _equipo_modelo(modelo, prop, fecha)
            esperado = vigente is not None and (
                prop == consultante_id
                or (vigente[2] == "supervisor" and del_registro is not None and del_registro[:2] == vigente[:2]))
            assert d.visible == esperado


# ==================================================== invariantes del ticket ==============================================

def test_la_politica_no_escribe_nada(db, mundo):
    tablas = ("persona", "pertenencia", "equipo", "organizacion", "auditoria", "bitacora")
    antes = {t: db.execute(text(f"select count(*) from {t}")).scalar() for t in tablas}
    for nombre in TODOS:
        for dueña in ("P", "QT", "Z"):
            lectura(db, mundo, nombre, dueña, X)
            _aud(db, mundo, nombre, dueña, X)
    db.rollback()
    assert {t: db.execute(text(f"select count(*) from {t}")).scalar() for t in tablas} == antes


def test_la_politica_de_visibilidad_historica_solo_la_usan_los_modulos_aprobados():
    """Actualizada a propósito en M4-T1 y de nuevo en M4-T6 (D-M4-01, aprobada): la política de visibilidad histórica la usa el módulo de M4 (``app/modulos/consulta``) y, para elegir
    entre 403 y 404 en las escrituras sobre registros ajenos (convenciones 3.1) y para autorizar la auditoría del supervisor (RA-10), SOLO el servicio de M2/M3 y el servicio y el
    repositorio de la auditoría. Ningún otro archivo (otro servicio, repositorio o ruta) puede usarla: una lista cerrada, no «cualquier cosa fuera de M4»."""
    usos = sorted(f.relative_to(RAIZ).as_posix() for f in (RAIZ / "app" / "modulos").rglob("*.py")
                  if "compartido.visibilidad" in f.read_text(encoding="utf-8") or "import visibilidad" in f.read_text(encoding="utf-8"))
    permitidos = {"app/modulos/bitacoras/servicio.py", "app/modulos/auditoria/servicio.py", "app/modulos/auditoria/repositorio.py"}
    # Actualizada a propósito en M5-T1 (D-M5-09, aprobada): los informes usan la MISMA política (RN-86, RA-09), solo desde el servicio y el repositorio del informe individual.
    # M5-T2 añade el consolidado y ``estructura.py`` (solo el tipo ``Consultante`` para exigir que puede operar) a la lista cerrada; ``agregaciones.py`` no usa la política: recibe hechos ya autorizados.
    # M5-T4 añade ``servicio.py`` (la canalización construye al consultante con ``consultante_de``).
    de_informes = {"app/modulos/informes/individual.py", "app/modulos/informes/consolidado.py", "app/modulos/informes/estructura.py", "app/modulos/informes/repositorio.py",
                   "app/modulos/informes/servicio.py"}
    assert usos and all(u.startswith("app/modulos/consulta/") or u in permitidos or u in de_informes for u in usos), usos
    assert de_informes <= set(usos), "la lista de permitidos no debe tener entradas que ya no usan la política"
    assert permitidos <= set(usos), "la lista de permitidos no debe tener entradas que ya no usan la política"


def test_la_definicion_del_intervalo_de_pertenencia_esta_en_un_solo_lugar():
    """Ningún otro módulo de la aplicación calcula a mano qué intervalo cubre una fecha (DM-04).

    Única excepción, justificada: ``app/provision/linea_temporal.py`` hace aritmética de intervalos de SUPERVISIÓN para las
    reglas de provisión (IR-03 e IR-32: ¿está cubierto el equipo desde una fecha, sin huecos y sin fin?). No responde a
    «en qué equipo está una persona en una fecha» y se contrasta con una comprobación día a día en ``test_linea_temporal``.
    Segunda excepción (M1-T3): ``app/provision/servicio.py`` solo cierra el último intervalo SIN FIN de una persona
    (``update ... where hasta_exclusivo is null``) y lee las líneas temporales para validarlas con ``linea_temporal``; tampoco
    decide qué equipo cubre una fecha."""
    otros = [str(f.relative_to(RAIZ)) for f in (RAIZ / "app").rglob("*.py")
             if f.name not in ("pertenencias.py", "linea_temporal.py") and not (f.parent.name == "provision" and f.name == "servicio.py") and re.search(r"daterange\(|hasta_exclusivo\s*(is null|>|<)", f.read_text(encoding="utf-8"))]
    assert otros == []
