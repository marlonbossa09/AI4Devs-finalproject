"""M4-T2 — M4-02 «Consultar el histórico por colaborador y fechas» (``GET /api/v1/historico``) con FastAPI y PostgreSQL reales.

Pruebas focalizadas (metodología ligera): rango válido, obligatorio, invertido, de más de 92 días y futuro; histórico propio y compartido autorizado; filtro por persona
(autorizada, no autorizada, inexistente); traslados entre equipos; personas finalizadas o desactivadas; lo no autorizado sin efecto en elementos, tamaño de las páginas ni
cursor; cursor válido, inválido y forjado, sin duplicados ni omisiones; parámetros no admitidos; y que no se filtra nada a través de las actividades neutrales.
Reutiliza el escenario de ``test_consulta_bitacora``. Destructivas solo sobre ``smartwork_test``.
"""

import base64
import json
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.compartido import paginacion
from app.config import get_settings
from app.db import get_owner_engine
from tests.fabricas import hoy
from tests.test_consulta_bitacora import API, CLAVE, H, _actividad, _bitacora, _plan, d, entrar, mundo  # noqa: F401  (fixture ``mundo``)
from tests.utiles_http import nuevo_cliente
from tests.utiles_m2 import contar

CAMPOS = {"persona_id", "fecha_laboral", "estado", "resumen", "actividades"}


def consultar(cliente, desde=None, hasta=None, **extra):
    parametros = {k: v for k, v in {"desde": None if desde is None else desde.isoformat(), "hasta": None if hasta is None else hasta.isoformat(), **extra}.items() if v is not None}
    return cliente.get(f"{API}/historico", params=parametros)


def todo(cliente, desde, hasta, limite, **extra):
    """Recorre todas las páginas siguiendo ``siguiente``. Devuelve (elementos, tamaños de página)."""
    elementos, tamanos, cursor = [], [], None
    for _ in range(50):
        r = consultar(cliente, desde, hasta, limite=str(limite), **({"continuar_desde": cursor} if cursor else {}), **extra)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        elementos += cuerpo["elementos"]
        tamanos.append(len(cuerpo["elementos"]))
        cursor = cuerpo["siguiente"]
        if cursor is None:
            return elementos, tamanos
    raise AssertionError("la paginación no termina")


def clave(e):
    return (e["fecha_laboral"], e["persona_id"])


@pytest.fixture()
def con_propia(mundo):
    """El escenario más una bitácora propia de Beto (d(-1))."""
    with get_owner_engine().begin() as c:
        _bitacora(c, mundo["beto"], d(-1), "resumen de Beto")
    return mundo


def esperadas_de_beto(m):
    return sorted([(d(-30).isoformat(), str(m["ana"])), (d(-4).isoformat(), str(m["ana"])), (d(-3).isoformat(), str(m["ana"])), (d(-30).isoformat(), str(m["pablo"])),
                   (d(-30).isoformat(), str(m["fina"])), (d(-2).isoformat(), str(m["zeta"])), (d(-3).isoformat(), str(m["supt"])), (d(-1).isoformat(), str(m["beto"]))])


# ------------------------------------------------------------------------------------------------------ rango y forma de la respuesta

def test_un_rango_valido_devuelve_solo_lo_autorizado_con_los_campos_del_contrato_y_orden_estable(con_propia):
    r = consultar(entrar("beto"), d(-60), d(10))
    cuerpo = r.json()
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store" and set(cuerpo) == {"elementos", "siguiente"}
    assert all(set(e) == CAMPOS for e in cuerpo["elementos"])                                           # lista cerrada de campos
    assert [clave(e) for e in cuerpo["elementos"]] == esperadas_de_beto(con_propia)                      # solo lo autorizado, ordenado por fecha laboral y persona
    celia_externa_y_pablo_en_u = {str(con_propia["celia"]), str(con_propia["externa"])}
    assert not celia_externa_y_pablo_en_u & {e["persona_id"] for e in cuerpo["elementos"]}
    assert (d(-3).isoformat(), str(con_propia["pablo"])) not in [clave(e) for e in cuerpo["elementos"]]    # lo de Pablo en U no es de T


def test_el_rango_es_inclusivo_y_se_limita_a_las_fechas_pedidas(con_propia):
    r = consultar(entrar("beto"), d(-4), d(-3)).json()
    assert [clave(e) for e in r["elementos"]] == sorted([(d(-4).isoformat(), str(con_propia["ana"])), (d(-3).isoformat(), str(con_propia["ana"])), (d(-3).isoformat(), str(con_propia["supt"]))])
    assert consultar(entrar("beto"), d(5), d(6)).json() == {"elementos": [], "siguiente": None}


def test_las_fechas_son_obligatorias_estan_en_orden_y_el_rango_no_supera_el_maximo(mundo):
    beto = entrar("beto")
    for desde, hasta, campo, motivo in ((None, d(0), "desde", "obligatorio"), (d(-5), None, "hasta", "obligatorio"), (None, None, "desde", "obligatorio"), (d(0), d(-1), "desde", "posterior_a_hasta")):
        r = consultar(beto, desde, hasta)
        assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA" and r.json()["detalles"][0]["campo"] == campo and r.json()["detalles"][0]["motivo"] == motivo, (desde, hasta)
    assert consultar(beto, d(-91), d(0)).status_code == 200                                               # 92 días con los extremos incluidos
    r = consultar(beto, d(-92), d(0))                                                                     # 93 días
    assert r.status_code == 400 and r.json()["detalles"] == [{"campo": "hasta", "motivo": "rango_excede_el_maximo", "maximo_dias": 92}]


def test_el_maximo_es_configurable_y_una_fecha_futura_se_admite(mundo, monkeypatch):
    beto = entrar("beto")
    assert consultar(beto, d(-30), d(30)).status_code == 200                                              # D-M4-04: hasta puede ser futuro
    monkeypatch.setattr(get_settings(), "query_max_range_days", 10)
    assert consultar(beto, d(-4), d(5)).status_code == 200
    r = consultar(beto, d(-5), d(5))
    assert r.status_code == 400 and r.json()["detalles"][0]["maximo_dias"] == 10


@pytest.mark.parametrize("extra", [{"q": "informe"}, {"texto": "informe"}, {"busqueda": "x"}, {"corte": "2026-11-01"}, {"estado": "Completada"}, {"equipo": "x"}, {"persona": "x"}])
def test_no_hay_busqueda_por_texto_ni_otros_filtros(mundo, extra):
    r = consultar(entrar("beto"), d(-10), d(0), **extra)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA" and r.json()["detalles"][0]["motivo"] == "parametro_no_soportado"       # CA-136


def test_los_formatos_y_los_parametros_repetidos_se_rechazan_antes_de_consultar(mundo):
    beto = entrar("beto")
    casos = [{"desde": "03-11-2026", "hasta": d(0).isoformat()}, {"desde": d(-5).isoformat(), "hasta": "2026-13-45"}, {"desde": d(-5).isoformat(), "hasta": d(0).isoformat(), "persona_id": "no-es-uuid"},
             {"desde": d(-5).isoformat(), "hasta": d(0).isoformat(), "limite": "0"}, {"desde": d(-5).isoformat(), "hasta": d(0).isoformat(), "limite": "101"},
             {"desde": d(-5).isoformat(), "hasta": d(0).isoformat(), "limite": "abc"}]
    for parametros in casos:
        r = beto.get(f"{API}/historico", params=parametros)
        assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA", parametros
    assert beto.get(f"{API}/historico", params={**casos[3], "limite": "101"}).json()["detalles"] == [{"campo": "limite", "maximo": 100}]
    r = beto.get(f"{API}/historico", params=[("desde", d(-5).isoformat()), ("desde", d(-4).isoformat()), ("hasta", d(0).isoformat())])
    assert r.status_code == 400 and r.json()["detalles"][0]["motivo"] == "parametro_repetido"


def test_sin_sesion_o_sin_acceso_efectivo_no_se_consulta_nada(mundo):
    assert nuevo_cliente().get(f"{API}/historico", params={"desde": d(-5).isoformat(), "hasta": d(0).isoformat()}).status_code == 401
    beto, ana = entrar("beto"), entrar("ana")
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": mundo["beto"]})
        c.execute(text("update pertenencia set hasta_exclusivo = :h where persona_id = :p"), {"h": H, "p": mundo["ana"]})
    r = consultar(beto, d(-10), d(0))
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"
    r = consultar(ana, d(-10), d(0))                                                                       # ni lo propio (IR-38)
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERTENENCIA_VIGENTE"


def test_la_ruta_solo_admite_get(mundo):
    r = entrar("beto").post(f"{API}/historico", headers={"Origin": "https://testserver"})
    assert r.status_code == 405 and r.headers["allow"] == "GET"


# ------------------------------------------------------------------------------------------------------ histórico propio y filtro por persona

def test_el_historico_propio_incluye_todo_lo_suyo_aunque_cruce_equipos(mundo):
    pablo = entrar("pablo")                                                                                # RA-03: la propietaria ve todos sus registros, de T y de U
    r = consultar(pablo, d(-60), d(0)).json()["elementos"]
    propios = {clave(e) for e in r if e["persona_id"] == str(mundo["pablo"])}
    assert propios == {(d(-30).isoformat(), str(mundo["pablo"])), (d(-3).isoformat(), str(mundo["pablo"]))}
    # y de su equipo actual (U) ve lo de Celia, pero no lo de T
    assert (d(-3).isoformat(), str(mundo["celia"])) in {clave(e) for e in r} and (d(-30).isoformat(), str(mundo["ana"])) not in {clave(e) for e in r}


def test_el_filtro_por_persona_devuelve_solo_lo_autorizado_de_esa_persona(mundo):
    beto = entrar("beto")
    ana = consultar(beto, d(-60), d(10), persona_id=str(mundo["ana"])).json()["elementos"]
    assert [clave(e) for e in ana] == sorted([(d(-30).isoformat(), str(mundo["ana"])), (d(-4).isoformat(), str(mundo["ana"])), (d(-3).isoformat(), str(mundo["ana"]))])
    vacia = {"elementos": [], "siguiente": None}
    for persona in (str(mundo["celia"]), str(mundo["externa"]), "00000000-0000-4000-8000-000000000001"):   # otro equipo, otra organización o inexistente: igual
        r = consultar(beto, d(-60), d(10), persona_id=persona)
        assert r.status_code == 200 and r.json() == vacia, persona
    pablo = consultar(beto, d(-60), d(10), persona_id=str(mundo["pablo"])).json()["elementos"]              # trasladado: de T solo lo anterior al traslado
    assert [clave(e) for e in pablo] == [(d(-30).isoformat(), str(mundo["pablo"]))]


def test_tras_un_traslado_cada_equipo_ve_su_periodo(mundo):
    celia, supt, supu = entrar("celia"), entrar("supt"), entrar("supu")
    de_celia = [clave(e) for e in consultar(celia, d(-60), d(0), persona_id=str(mundo["pablo"])).json()["elementos"]]
    assert de_celia == [(d(-3).isoformat(), str(mundo["pablo"]))]                                           # CA-18 y CA-16
    assert [clave(e) for e in consultar(supt, d(-60), d(0), persona_id=str(mundo["pablo"])).json()["elementos"]] == [(d(-30).isoformat(), str(mundo["pablo"]))]
    assert [clave(e) for e in consultar(supu, d(-60), d(0), persona_id=str(mundo["pablo"])).json()["elementos"]] == [(d(-3).isoformat(), str(mundo["pablo"]))]


def test_los_registros_de_personas_finalizadas_o_desactivadas_siguen_visibles_para_su_equipo(mundo):
    r = consultar(entrar("supt"), d(-60), d(0)).json()["elementos"]
    assert (d(-30).isoformat(), str(mundo["fina"])) in {clave(e) for e in r}                                # CA-30
    assert (d(-2).isoformat(), str(mundo["zeta"])) in {clave(e) for e in r}                                 # CA-256
    en_u = {clave(e) for e in consultar(entrar("celia"), d(-60), d(0)).json()["elementos"]}
    assert (d(-30).isoformat(), str(mundo["fina"])) not in en_u and (d(-2).isoformat(), str(mundo["zeta"])) not in en_u


# ------------------------------------------------------------------------------------------------------ proyecciones seguras

def test_las_actividades_neutrales_no_filtran_nada_del_equipo_anterior(mundo):
    r = consultar(entrar("celia"), d(-3), d(-3), persona_id=str(mundo["pablo"])).json()
    elemento = r["elementos"][0]
    heredada = next(a for a in elemento["actividades"] if a["id"] == str(mundo["a_tarea_t"]))
    assert heredada == {"forma": "neutral", "id": str(mundo["a_tarea_t"]), "propietaria_id": str(mundo["pablo"]), "referencia_neutral": "Actividad en continuidad"}
    assert {a["id"] for a in elemento["actividades"]} == {str(mundo["a_tarea_t"]), str(mundo["a_tarea_u"])}      # la marcada de T no aparece
    texto = json.dumps(r, ensure_ascii=False)
    for prohibido in ("Tarea secreta del equipo T", "motivo-reservado-del-equipo-T", "Avance interno del equipo T", "Bloqueo en el equipo T", "Equipo T", "resumen reservado del equipo T",
                      d(-30).isoformat(), "Tarea marcada del equipo T", "continuación de la marcada"):
        assert prohibido not in texto, prohibido
    # y quien sí estuvo en T ve lo suyo completo, sin el estado actual de quien ya no es de su equipo
    de_t = consultar(entrar("beto"), d(-30), d(-30), persona_id=str(mundo["pablo"])).json()["elementos"][0]["actividades"]
    tarea = next(a for a in de_t if a["id"] == str(mundo["a_tarea_t"]))
    assert tarea["forma"] == "completa" and tarea["titulo"] == "Tarea secreta del equipo T" and "estado_actual" not in tarea


# ------------------------------------------------------------------------------------------------------ paginación y cursor

@pytest.mark.parametrize("limite", [1, 2, 3, 100])
def test_recorrer_todas_las_paginas_no_duplica_ni_omite_y_lo_no_autorizado_no_acorta_ninguna(con_propia, limite):
    beto = entrar("beto")
    elementos, tamanos = todo(beto, d(-60), d(10), limite)
    esperadas = esperadas_de_beto(con_propia)
    assert [clave(e) for e in elementos] == esperadas and len({clave(e) for e in elementos}) == len(esperadas)      # sin duplicados ni omisiones, en orden
    # todas las páginas están llenas salvo la última: los registros de otros equipos (que existen en el mismo rango) no dejan huecos ni páginas cortas
    assert all(t == limite for t in tamanos[:-1]) and 1 <= tamanos[-1] <= limite and sum(tamanos) == len(esperadas)


def test_el_cursor_no_aparece_si_no_hay_mas_y_un_cursor_valido_continua_donde_se_quedo(con_propia):
    beto = entrar("beto")
    primera = consultar(beto, d(-60), d(10), limite="3").json()
    assert len(primera["elementos"]) == 3 and primera["siguiente"]
    segunda = consultar(beto, d(-60), d(10), limite="3", continuar_desde=primera["siguiente"]).json()
    todas = esperadas_de_beto(con_propia)
    assert [clave(e) for e in segunda["elementos"]] == todas[3:6]
    assert consultar(beto, d(-60), d(10), limite="100").json()["siguiente"] is None


@pytest.mark.parametrize("cursor", [
    "esto-no-es-un-cursor", "", base64.urlsafe_b64encode(b"no es json").decode(),
    base64.urlsafe_b64encode(json.dumps({"f": "2026-01-01"}).encode()).decode(),
    base64.urlsafe_b64encode(json.dumps(["2026-01-01", "x", "y"]).encode()).decode(),
    base64.urlsafe_b64encode(json.dumps(["2026-01-01", "00000000-0000-4000-8000-000000000001"]).encode()).decode(),
    base64.urlsafe_b64encode(json.dumps([1, 2, 3]).encode()).decode(),
    base64.urlsafe_b64encode(json.dumps(["no-es-fecha", "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002"]).encode()).decode(),
])
def test_un_cursor_invalido_se_rechaza(mundo, cursor):
    r = consultar(entrar("beto"), d(-60), d(10), continuar_desde=cursor)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA" and r.json()["detalles"][0]["campo"] == "continuar_desde"


def test_un_cursor_fabricado_solo_es_una_posicion_y_no_entrega_nada_no_autorizado(con_propia):
    """Un cursor es una posición: la autorización se aplica siempre al seleccionar. Uno colocado justo antes de registros ajenos no los entrega."""
    cursor = paginacion.emitir_cursor(d(-4).isoformat(), "00000000-0000-4000-8000-000000000000", "00000000-0000-4000-8000-000000000000")
    r = consultar(entrar("beto"), d(-60), d(10), continuar_desde=cursor).json()
    assert [clave(e) for e in r["elementos"]] == [c for c in esperadas_de_beto(con_propia) if c[0] >= d(-4).isoformat()]
    ajenos = {str(con_propia["celia"]), str(con_propia["externa"])}
    assert not ajenos & {e["persona_id"] for e in r["elementos"]}


def test_la_utilidad_de_paginacion_ida_y_vuelta_y_rango():
    from datetime import date
    from uuid import UUID
    c = paginacion.emitir_cursor("2026-11-17", "00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002")
    assert "=" not in c and paginacion.leer_cursor(c, date.fromisoformat, UUID, UUID) == (date(2026, 11, 17), UUID("00000000-0000-4000-8000-000000000001"), UUID("00000000-0000-4000-8000-000000000002"))
    assert paginacion.leer_cursor(None, date.fromisoformat) is None
    assert paginacion.rango_de_fechas({"desde": "2026-01-01", "hasta": "2026-04-02"}) == (date(2026, 1, 1), date(2026, 4, 2))        # 92 días con extremos
