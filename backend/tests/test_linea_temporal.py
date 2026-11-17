"""M1-T2 y M1-T3 — reglas puras de la línea temporal (IR-02, IR-03, IR-28, IR-32), contrastadas con una comprobación día a día."""

import random
from datetime import date, timedelta

import pytest

from app.provision.linea_temporal import (
    IntervaloDeSupervisor as S, Tramo, primera_irregularidad_de_persona, primera_violacion_de_supervision, solapa_con_supervisor,
    supervision_cubre_desde, supervision_en,
)

D = date(2026, 1, 1)


def dia(n):
    return D + timedelta(days=n)


def test_sin_supervisores_no_hay_cobertura_ni_solape():
    assert not supervision_cubre_desde([], dia(0)) and not solapa_con_supervisor([], dia(0))


def test_un_supervisor_sin_fin_cubre_desde_su_inicio_y_no_antes():
    s = [S(dia(5), None)]
    assert supervision_cubre_desde(s, dia(5)) and supervision_cubre_desde(s, dia(50))
    assert not supervision_cubre_desde(s, dia(4))
    assert solapa_con_supervisor(s, dia(0)) and solapa_con_supervisor(s, dia(99))


def test_un_supervisor_con_fin_no_cubre_para_siempre_y_el_fin_es_exclusivo():
    s = [S(dia(0), dia(10))]
    assert not supervision_cubre_desde(s, dia(0)) and not supervision_cubre_desde(s, dia(9))
    assert solapa_con_supervisor(s, dia(9)) and not solapa_con_supervisor(s, dia(10))     # el día `hasta_exclusivo` ya está libre


def test_dos_supervisores_contiguos_cubren_sin_hueco_y_con_hueco_no():
    assert supervision_cubre_desde([S(dia(0), dia(10)), S(dia(10), None)], dia(3))
    assert not supervision_cubre_desde([S(dia(0), dia(10)), S(dia(11), None)], dia(3))
    assert supervision_cubre_desde([S(dia(10), None), S(dia(0), dia(10))], dia(0))           # el orden de entrada no importa


def _cubre_por_fuerza_bruta(supervisores, desde, horizonte):
    return all(any(s.desde <= d and (s.hasta_exclusivo is None or d < s.hasta_exclusivo) for s in supervisores)
               for d in (desde + timedelta(days=k) for k in range(horizonte)))


@pytest.mark.parametrize("semilla", range(40))
def test_propiedad_cobertura_y_solape_coinciden_con_la_comprobacion_dia_a_dia(semilla):
    azar = random.Random(semilla)
    cursor, supervisores = dia(azar.randint(0, 5)), []
    for _ in range(azar.randint(0, 4)):          # intervalos disjuntos (IR-03), con huecos o contiguos, a veces sin fin
        largo = azar.randint(1, 15)
        fin = None if azar.random() < 0.25 else cursor + timedelta(days=largo)
        supervisores.append(S(cursor, fin))
        if fin is None:
            break
        cursor = fin + timedelta(days=azar.choice([0, 0, 1, 3]))
    for desde in (dia(k) for k in range(0, 60, 3)):
        # fuera de los intervalos acotados, solo importa que el último no tenga fin: se mira un horizonte largo
        cubre = _cubre_por_fuerza_bruta(supervisores, desde, 200)
        esperado = cubre and any(s.hasta_exclusivo is None for s in supervisores)   # cubrir 200 días solo basta si hay uno sin fin
        solapa = any(s.hasta_exclusivo is None or s.hasta_exclusivo > desde for s in supervisores)
        assert solapa_con_supervisor(supervisores, desde) == solapa
        if esperado:
            assert supervision_cubre_desde(supervisores, desde)
        if not cubre:
            assert not supervision_cubre_desde(supervisores, desde)


# ==================================================== M1-T3: línea temporal completa de un equipo (IR-03, IR-32) =============

def sup(persona, desde, hasta=None):
    return Tramo(persona, "supervisor", dia(desde), None if hasta is None else dia(hasta))


def col(persona, desde, hasta=None):
    return Tramo(persona, "colaborador", dia(desde), None if hasta is None else dia(hasta))


def test_un_equipo_sin_colaboradores_puede_carecer_de_supervisor():
    assert primera_violacion_de_supervision([], dia(0)) is None
    assert primera_violacion_de_supervision([sup("S", 0, 10)], dia(0)) is None            # solo supervisor, con fin: sin colaboradores


def test_un_colaborador_exige_un_supervisor_en_cada_fecha():
    assert primera_violacion_de_supervision([sup("S", 0), col("C", 5)], dia(0)) is None
    v = primera_violacion_de_supervision([sup("S", 0, 10), col("C", 5)], dia(0))
    assert (v.fecha, v.motivo) == (dia(10), "sin_supervisor")                              # el día `hasta_exclusivo` ya no hay supervisor


def test_el_relevo_en_la_misma_fecha_es_valido_y_con_un_dia_de_hueco_no():
    assert primera_violacion_de_supervision([sup("S1", 0, 10), sup("S2", 10), col("C", 0)], dia(0)) is None
    v = primera_violacion_de_supervision([sup("S1", 0, 10), sup("S2", 11), col("C", 0)], dia(0))
    assert (v.fecha, v.motivo) == (dia(10), "sin_supervisor")


def test_dos_supervisores_a_la_vez_se_rechazan_aunque_no_haya_colaboradores():
    v = primera_violacion_de_supervision([sup("S1", 0), sup("S2", 5)], dia(0))
    assert (v.fecha, v.motivo) == (dia(5), "mas_de_un_supervisor")
    assert primera_violacion_de_supervision([sup("S1", 0, 5), sup("S2", 5)], dia(0)) is None   # contiguos: nunca coinciden


def test_el_cambio_de_un_colaborador_a_supervisor_se_valida_en_su_fecha():
    # C pasa a supervisor el día 10 mientras S sigue: dos supervisores
    v = primera_violacion_de_supervision([sup("S", 0), col("C", 0, 10), sup("C", 10)], dia(0))
    assert (v.fecha, v.motivo) == (dia(10), "mas_de_un_supervisor")
    # relevo: S termina el día 10 y C asume ese mismo día; otro colaborador permanece
    assert primera_violacion_de_supervision([sup("S", 0, 10), col("C", 0, 10), sup("C", 10), col("D", 0)], dia(0)) is None


def test_solo_se_miran_las_fechas_desde_la_indicada():
    tramos = [sup("S", 0, 10), col("C", 0)]            # incumple desde el día 10
    assert primera_violacion_de_supervision(tramos, dia(0)).fecha == dia(10)
    assert primera_violacion_de_supervision(tramos, dia(11)).fecha == dia(11)                 # el estado persiste: también incumple
    assert primera_violacion_de_supervision([sup("S", 0, 3), col("C", 0, 2)], dia(5)) is None  # ya no hay colaboradores


def _viola_por_fuerza_bruta(tramos, desde, horizonte):
    for k in range(horizonte):
        f = desde + timedelta(days=k)
        s = sum(1 for t in tramos if t.rol == "supervisor" and t.cubre(f))
        c = sum(1 for t in tramos if t.rol == "colaborador" and t.cubre(f))
        if s > 1 or (c > 0 and s == 0):
            return f
    return None


@pytest.mark.parametrize("semilla", range(120))
def test_propiedad_la_violacion_de_supervision_coincide_con_la_comprobacion_dia_a_dia(semilla):
    azar = random.Random(1000 + semilla)
    tramos = []
    for i in range(azar.randint(0, 6)):
        desde = azar.randint(0, 30)
        hasta = None if azar.random() < 0.4 else desde + azar.randint(1, 20)
        tramos.append(Tramo(f"P{i}", azar.choice(["supervisor", "colaborador"]), dia(desde), None if hasta is None else dia(hasta)))
    for desde in (dia(k) for k in range(0, 40, 5)):
        esperado = _viola_por_fuerza_bruta(tramos, desde, 200)         # 200 días: más allá de cualquier fecha de cambio
        obtenido = primera_violacion_de_supervision(tramos, desde)
        assert (obtenido.fecha if obtenido else None) == esperado


# ==================================================== M1-T3: línea temporal completa de una persona (IR-02, IR-28) ===========

def tp(equipo, desde, hasta=None):
    return Tramo("P", equipo, dia(desde), None if hasta is None else dia(hasta))


def test_una_persona_con_intervalos_contiguos_y_el_ultimo_abierto_es_regular():
    assert primera_irregularidad_de_persona([]) is None
    assert primera_irregularidad_de_persona([tp("a", 0)]) is None
    assert primera_irregularidad_de_persona([tp("a", 0, 10), tp("b", 10, 20), tp("c", 20)]) is None
    assert primera_irregularidad_de_persona([tp("c", 20), tp("a", 0, 10), tp("b", 10, 20)]) is None      # el orden de entrada no importa


def test_un_hueco_de_un_dia_es_una_irregularidad():
    assert primera_irregularidad_de_persona([tp("a", 0, 10), tp("b", 11)]) == "hueco"


def test_un_solape_de_un_dia_o_un_intervalo_sin_fin_seguido_de_otro_es_una_irregularidad():
    assert primera_irregularidad_de_persona([tp("a", 0, 11), tp("b", 10)]) == "solape"
    assert primera_irregularidad_de_persona([tp("a", 0), tp("b", 10)]) == "solape"                      # solo el último puede carecer de fin


def test_un_intervalo_vacio_o_invertido_es_una_irregularidad():
    assert primera_irregularidad_de_persona([tp("a", 5, 5)]) == "intervalo_invalido"
    assert primera_irregularidad_de_persona([tp("a", 5, 3)]) == "intervalo_invalido"


# ==================================================== M1-T6: supervisión efectiva en una fecha (DM-09, RA-12) ==================

def test_un_equipo_con_colaboradores_cuyo_supervisor_asignado_no_tiene_acceso_esta_pendiente():
    tramos = [sup("S", 0), col("C1", 0), col("C2", 3)]
    assert supervision_en(tramos, dia(1), {"S"}).pendiente and supervision_en(tramos, dia(1), {"S"}).colaboradores == 1
    assert supervision_en(tramos, dia(5), {"S"}).colaboradores == 2
    assert not supervision_en(tramos, dia(1), set()).pendiente                          # con acceso efectivo: supervisión efectiva
    assert not supervision_en(tramos, dia(1), {"C1"}).pendiente                         # un colaborador sin acceso no deja al equipo sin supervisión


def test_un_equipo_sin_colaboradores_esta_en_provision_y_no_esta_pendiente():
    assert not supervision_en([sup("S", 0)], dia(1), {"S"}).pendiente
    assert not supervision_en([], dia(1), {"S"}).pendiente
    assert not supervision_en([sup("S", 0), col("C", 5)], dia(4), {"S"}).pendiente      # el colaborador aún no empezó
    assert supervision_en([sup("S", 0), col("C", 5)], dia(5), {"S"}).pendiente          # el día exacto de su inicio, sí


def test_sin_supervisor_asignado_y_con_colaboradores_tambien_esta_pendiente():
    assert supervision_en([col("C", 0)], dia(1)).pendiente and supervision_en([col("C", 0)], dia(1)).supervisor is None


def test_la_supervision_se_evalua_con_el_supervisor_asignado_en_esa_fecha_y_el_fin_es_exclusivo():
    tramos = [sup("S1", 0, 10), sup("S2", 10), col("C", 0)]                             # relevo el día 10
    assert supervision_en(tramos, dia(9), {"S1"}).pendiente and supervision_en(tramos, dia(9), {"S1"}).supervisor == "S1"
    assert not supervision_en(tramos, dia(10), {"S1"}).pendiente and supervision_en(tramos, dia(10), {"S1"}).supervisor == "S2"
