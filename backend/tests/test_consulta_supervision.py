"""M4-T3 — M4-03 núcleo «Vista de supervisión del equipo en un período» (``GET /api/v1/equipo/supervision``) con FastAPI y PostgreSQL reales.

Pruebas focalizadas (metodología ligera): supervisor autorizado; colaborador (403); supervisor desactivado y equipo pendiente; inclusión por planificación, avances y pendiente
al corte (RN-47); exclusión de lo completado antes del período y de lo marcado por error; estado al corte frente al actual (D-M4-05); totales sobre lo autorizado; registros de
otro equipo, de otra organización y planificaciones conservadas sin efecto en totales, lista ni cursor; paginación estable; fechas y rango máximo; y que lo que necesita M4-T4
(actividad heredada, estado al corte determinado por otro equipo) falla cerrado sin exponer nada. Los criterios reservados a M4-T4 NO se prueban como cumplidos.
Destructivas solo sobre ``smartwork_test``.
"""

import json
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.compartido import visibilidad
from app.db import get_owner_engine
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia
from tests.test_consulta_bitacora import API, CLAVE, H, _actividad, _avance, _bitacora, _marcar, _plan, d, entrar  # noqa: F401
from tests.utiles_http import nuevo_cliente

ESTADOS = ["Pendiente", "En progreso", "Bloqueada", "Completada"]


@pytest.fixture()
def mundo():
    """Equipo T (supervisora ``supt``; Ana, Beto, Pablo —pasa a U en d(-10)—, Luis —viene de U en d(-10)—, Fina —finalizada en d(-20)— y Gina —hasta d(+3)—), equipo U (``supu``,
    Celia) y otra organización (``externa``). Las actividades están descritas en el comentario de cada una."""
    m: dict = {}
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c)
        t, u = crear_equipo(c, org, "Equipo T"), crear_equipo(c, org, "Equipo U")

        def alta(nombre, equipo, rol, desde, hasta=None):
            p = crear_persona(c, nombre)
            crear_pertenencia(c, p, equipo, rol, desde=desde, hasta=hasta)
            crear_identidad(c, p, nombre, CLAVE)
            m[nombre] = p
            return p

        alta("supt", t, "supervisor", d(-80)); alta("supu", u, "supervisor", d(-80))
        for n in ("ana", "beto"):
            alta(n, t, "colaborador", d(-80))
        alta("celia", u, "colaborador", d(-80))
        alta("pablo", t, "colaborador", d(-80), d(-10)); crear_pertenencia(c, m["pablo"], u, "colaborador", desde=d(-10))
        alta("luis", u, "colaborador", d(-80), d(-10)); crear_pertenencia(c, m["luis"], t, "colaborador", desde=d(-10))
        alta("fina", t, "colaborador", d(-80), d(-20))
        alta("gina", t, "colaborador", d(-80), d(3))
        org2 = crear_organizacion(c)
        alta("externa", crear_equipo(c, org2, "Equipo V"), "supervisor", d(-80))

        def jornada(persona, dias, resumen="resumen"):
            return _bitacora(c, m[persona], d(dias), resumen)

        # Ana
        b15, b5, b40 = jornada("ana", -15), jornada("ana", -5), jornada("ana", -40)
        m["A1"] = a = _actividad(c, m["ana"], b15, "Informe de Ana", estado="Bloqueada"); _plan(c, a, b15); _avance(c, a, b15, "En progreso", "avance 1 de Ana"); _avance(c, a, b5, "Bloqueada", "bloqueo de Ana", "motivo de Ana")
        m["A2"] = a = _actividad(c, m["ana"], b40, "Revisión antigua de Ana", estado="En progreso"); _avance(c, a, b40, "En progreso", "arranque antiguo")
        m["A3"] = a = _actividad(c, m["ana"], b40, "Completada hace mucho", estado="Completada"); _avance(c, a, b40, "Completada", "terminada")
        m["A8"] = a = _actividad(c, m["ana"], b5, "Registrada por error", estado="Pendiente"); _plan(c, a, b5); _marcar(c, a, m["ana"])
        # Beto
        b10, b25, b8 = jornada("beto", -10), jornada("beto", -25), jornada("beto", -8)
        m["A4"] = a = _actividad(c, m["beto"], b10, "Plan de Beto", estado="Pendiente"); _plan(c, a, b10)
        m["A5"] = a = _actividad(c, m["beto"], b25, "Terminada en el período", estado="Completada"); _avance(c, a, b25, "En progreso", "inicio"); _avance(c, a, b8, "Completada", "fin")
        # la supervisora
        b3 = jornada("supt", -3)
        m["A7"] = a = _actividad(c, m["supt"], b3, "Plan de la supervisora", estado="Pendiente"); _plan(c, a, b3)
        # Pablo: empezó en T, pasó a U en d(-10) y sigue en U (CASO RESERVADO A M4-T4 cuando el corte es posterior al traslado)
        p30, p12, p3 = jornada("pablo", -30, "resumen reservado de T"), jornada("pablo", -12), jornada("pablo", -3)
        m["A9"] = a = _actividad(c, m["pablo"], p30, "Tarea de Pablo", estado="En progreso")
        _avance(c, a, p30, "En progreso", "arranque en T"); _avance(c, a, p12, "Bloqueada", "bloqueo en T", "motivo reservado de T"); _avance(c, a, p3, "En progreso", "continúa en U")
        # Luis: empezó en U (d(-30)) y ahora es de T (ACTIVIDAD HEREDADA: M4-T4)
        l30 = jornada("luis", -30, "resumen reservado de U")
        m["A11"] = a = _actividad(c, m["luis"], l30, "Tarea heredada de Luis", estado="En progreso"); _avance(c, a, l30, "En progreso", "trabajo previo en U")
        # Planificaciones CONSERVADAS: la fecha no está cubierta por ninguna pertenencia de su propietaria
        f5, g5 = jornada("fina", 5), jornada("gina", 5)
        m["A12"] = a = _actividad(c, m["fina"], f5, "Conservada de Fina", estado="Pendiente"); _plan(c, a, f5)
        m["A13"] = a = _actividad(c, m["gina"], g5, "Conservada de Gina", estado="Pendiente"); _plan(c, a, g5)
        # Otros equipos
        c5 = jornada("celia", -5)
        m["A10"] = a = _actividad(c, m["celia"], c5, "Tarea de Celia", estado="Pendiente"); _plan(c, a, c5)
        e5 = jornada("externa", -5)
        m["A14"] = a = _actividad(c, m["externa"], e5, "Tarea de Externa", estado="Pendiente"); _plan(c, a, e5)
    return m


def supervision(cliente, desde, hasta, **extra):
    parametros = {k: v for k, v in {"desde": None if desde is None else desde.isoformat(), "hasta": None if hasta is None else hasta.isoformat(), **extra}.items() if v is not None}
    return cliente.get(f"{API}/equipo/supervision", params=parametros)


def por_id(cuerpo):
    return {e["actividad"]["id"]: e for e in cuerpo["elementos"]}


def todas_las_paginas(cliente, desde, hasta, limite):
    elementos, tamanos, totales, cursor = [], [], [], None
    for _ in range(30):
        extra = {"limite": str(limite), **({"continuar_desde": cursor} if cursor else {})}
        cuerpo = supervision(cliente, desde, hasta, **extra).json()
        elementos += cuerpo["elementos"]
        tamanos.append(len(cuerpo["elementos"]))
        totales.append(cuerpo["totales_por_estado"])
        cursor = cuerpo["siguiente"]
        if cursor is None:
            return elementos, tamanos, totales
    raise AssertionError("la paginación no termina")


# ------------------------------------------------------------------------------------------------------ autorización

def test_el_supervisor_con_acceso_efectivo_obtiene_la_vista_con_la_forma_del_contrato(mundo):
    r = supervision(entrar("supt"), d(-20), d(0))
    c = r.json()
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert set(c) == {"periodo", "corte", "totales_por_estado", "elementos", "siguiente"}
    assert c["periodo"] == {"desde": d(-20).isoformat(), "hasta": d(0).isoformat()} and c["corte"] == d(0).isoformat()           # el corte es el último día (D-06)
    assert all({"tipo", "actividad", "propietaria_id", "motivo_inclusion", "estado_al_corte"} <= set(e) <= {"tipo", "actividad", "propietaria_id", "motivo_inclusion", "estado_al_corte", "estado_actual_si_difiere"}
               for e in c["elementos"])
    assert all(e["tipo"] == "actividad" and e["actividad"]["forma"] == "completa" and "estado_actual" not in e["actividad"] for e in c["elementos"])
    assert not any(palabra in json.dumps(c).lower() for palabra in ("ranking", "puntuacion", "clasificacion"))                    # CA-145


def test_un_colaborador_recibe_403_y_nadie_mas_supervisa_aunque_el_supervisor_este_desactivado(mundo):
    beto, ana = entrar("beto"), entrar("ana")
    r = supervision(beto, d(-20), d(0))
    assert r.status_code == 403 and r.json()["codigo"] == "OPERACION_NO_PERMITIDA"
    supt = entrar("supt")
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": mundo["supt"]})
    r = supervision(supt, d(-20), d(0))                                                                    # el supervisor desactivado no accede
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"
    for colaborador in (beto, ana):                                                                         # el equipo queda pendiente de supervisión efectiva: nadie hereda el permiso (RA-12)
        r = supervision(colaborador, d(-20), d(0))
        assert r.status_code == 403 and r.json()["codigo"] == "OPERACION_NO_PERMITIDA"


def test_cada_supervisor_ve_solo_las_actividades_de_su_equipo(mundo):
    u = supervision(entrar("supu"), d(-20), d(0)).json()
    assert {e["actividad"]["titulo"] for e in u["elementos"]} == {"Tarea de Celia"} and u["totales_por_estado"]["Pendiente"] == 1          # CA-146
    otra_org = supervision(entrar("externa"), d(-20), d(0)).json()
    assert {e["actividad"]["titulo"] for e in otra_org["elementos"]} == {"Tarea de Externa"}
    texto = json.dumps(u) + json.dumps(otra_org)
    for ajeno in ("Informe de Ana", "Plan de Beto", "Plan de la supervisora", "Revisión antigua de Ana", "Terminada en el período"):
        assert ajeno not in texto, ajeno


def test_ningun_metodo_de_escritura_existe_en_la_ruta(mundo):
    r = entrar("supt").post(f"{API}/equipo/supervision", headers={"Origin": "https://testserver"})
    assert r.status_code == 405 and r.headers["allow"] == "GET"                                          # CA-195 en lo que toca a M4


# ------------------------------------------------------------------------------------------------------ inclusión, estado al corte y totales

def test_inclusion_por_planificacion_avances_y_pendiente_con_sus_motivos_y_los_totales_exactos(mundo):
    c = supervision(entrar("supt"), d(-20), d(0)).json()
    e = por_id(c)
    assert set(e) == {str(mundo[k]) for k in ("A1", "A2", "A4", "A5", "A7")}
    assert e[str(mundo["A1"])]["motivo_inclusion"] == ["planificada_en_el_periodo", "con_avances_en_el_periodo", "pendiente_al_corte"] and e[str(mundo["A1"])]["estado_al_corte"] == "Bloqueada"   # CA-138, CA-139, CA-140
    assert e[str(mundo["A2"])]["motivo_inclusion"] == ["pendiente_al_corte"] and e[str(mundo["A2"])]["estado_al_corte"] == "En progreso"                                            # CA-140: sin registros en el período
    assert e[str(mundo["A4"])]["motivo_inclusion"] == ["planificada_en_el_periodo", "pendiente_al_corte"] and e[str(mundo["A4"])]["estado_al_corte"] == "Pendiente"
    assert e[str(mundo["A5"])]["motivo_inclusion"] == ["con_avances_en_el_periodo"] and e[str(mundo["A5"])]["estado_al_corte"] == "Completada"                                       # completada en el período: ya no está pendiente
    assert e[str(mundo["A7"])]["propietaria_id"] == str(mundo["supt"])                                                                                                                  # CA-142: las propias
    assert c["totales_por_estado"] == {"Pendiente": 2, "En progreso": 1, "Bloqueada": 1, "Completada": 1}
    assert [x["estado_al_corte"] for x in c["elementos"]] == ["Pendiente", "Pendiente", "En progreso", "Bloqueada", "Completada"]                                                       # orden por estado


def test_lo_completado_antes_del_periodo_y_lo_marcado_por_error_no_aparecen(mundo):
    ids = set(por_id(supervision(entrar("supt"), d(-20), d(0)).json()))
    assert str(mundo["A3"]) not in ids                                                                       # CA-141: completada antes y sin avances en el período
    assert str(mundo["A8"]) not in ids                                                                       # CA-147: registrada por error (aunque su origen sea del equipo)
    # pero si hubo avances en el período, una completada sí aparece: el período que incluye su día de fin la contiene
    assert str(mundo["A3"]) in por_id(supervision(entrar("supt"), d(-45), d(-30)).json())


def test_el_estado_al_corte_se_distingue_del_actual_solo_si_difiere_y_la_propietaria_sigue_en_el_equipo(mundo):
    c = supervision(entrar("supt"), d(-20), d(-10)).json()                                                    # corte d(-10)
    e = por_id(c)
    assert e[str(mundo["A1"])]["estado_al_corte"] == "En progreso" and e[str(mundo["A1"])]["estado_actual_si_difiere"] == "Bloqueada"     # CA-143
    assert e[str(mundo["A5"])]["estado_al_corte"] == "En progreso" and e[str(mundo["A5"])]["estado_actual_si_difiere"] == "Completada"
    assert "estado_actual_si_difiere" not in e[str(mundo["A2"])]                                              # CA-144: coinciden, un único estado
    # Pablo ya no es del equipo: se conserva lo autorizado y su estado al corte, pero no su estado actual (D-M4-05)
    pablo = e[str(mundo["A9"])]
    assert pablo["estado_al_corte"] == "Bloqueada" and pablo["motivo_inclusion"] == ["con_avances_en_el_periodo"] and "estado_actual_si_difiere" not in pablo
    assert str(mundo["A7"]) not in e                                                                          # una actividad creada después del corte no entra
    assert c["totales_por_estado"] == {"Pendiente": 1, "En progreso": 3, "Bloqueada": 1, "Completada": 0}


def test_una_continuacion_planificada_posterior_al_corte_no_cambia_el_estado_al_corte(mundo):
    with get_owner_engine().begin() as c:
        b = _bitacora(c, mundo["ana"], d(5), "jornada futura")
        _plan(c, mundo["A1"], b, "continuacion", "continúa más adelante")
    e = por_id(supervision(entrar("supt"), d(-20), d(-10)).json())[str(mundo["A1"])]
    assert e["estado_al_corte"] == "En progreso"                                                              # CA-198: la planificación posterior no interviene


def test_el_periodo_puede_ser_futuro_y_las_planificaciones_conservadas_no_cuentan_como_trabajo_de_nadie(mundo):
    c = supervision(entrar("supt"), d(0), d(10)).json()                                                       # D-M4-04
    titulos = {e["actividad"]["titulo"] for e in c["elementos"]}
    assert "Conservada de Fina" not in titulos and "Conservada de Gina" not in titulos                       # CA-274: ni vigentes ni pendientes de ningún equipo (D-M4-07)
    assert "Conservada de Fina" not in json.dumps(c) and "Conservada de Gina" not in json.dumps(c)
    assert {"Informe de Ana", "Revisión antigua de Ana", "Plan de Beto", "Plan de la supervisora"} <= titulos      # lo pendiente de los integrantes actuales sigue ahí
    assert sum(c["totales_por_estado"].values()) == len(c["elementos"])


# ------------------------------------------------------------------------------------------------------ información derivada y falla cerrado (M4-T4)

def test_lo_de_otros_equipos_no_cambia_ni_los_totales_ni_la_lista(mundo):
    antes = supervision(entrar("supt"), d(-20), d(0)).json()
    with get_owner_engine().begin() as c:                                                                       # más actividad ajena en el mismo período: no puede cambiar nada
        for persona, dias in (("celia", -6), ("celia", -7), ("externa", -6)):
            b = _bitacora(c, mundo[persona], d(dias))
            _avance(c, _actividad(c, mundo[persona], b, f"Ajena {persona} {dias}", estado="Bloqueada"), b, "Bloqueada", "ajeno", "motivo ajeno")
    despues = supervision(entrar("supt"), d(-20), d(0)).json()
    assert despues == antes


def test_las_actividades_heredadas_y_el_estado_determinado_por_otro_equipo_fallan_cerrado(mundo):
    c = supervision(entrar("supt"), d(-20), d(0)).json()
    texto = json.dumps(c)
    assert str(mundo["A11"]) not in texto and "Tarea heredada de Luis" not in texto                          # origen de otro equipo (T4: referencia mínima)
    assert str(mundo["A9"]) not in texto and "Tarea de Pablo" not in texto                                   # el último avance hasta el corte es de U (T4: CA-230)
    for filtrado in ("resumen reservado", "motivo reservado de T", "bloqueo en T", "continúa en U", "trabajo previo en U", "Equipo U", "Equipo T", "Tarea de Celia"):
        assert filtrado not in texto, filtrado
    assert "referencias_minimas" not in c                                                                     # el recuento llega con M4-T4: no se anuncia algo que no se muestra
    # y lo que es del equipo sigue siendo exactamente lo calculado: lo omitido no se cuenta
    assert sum(c["totales_por_estado"].values()) == 5


def test_el_equipo_nuevo_no_ve_lo_que_empezo_en_el_anterior(mundo):
    u = supervision(entrar("supu"), d(-20), d(0)).json()
    texto = json.dumps(u)
    assert "Tarea de Pablo" not in texto and "Informe de Ana" not in texto and sum(u["totales_por_estado"].values()) == 1


# ------------------------------------------------------------------------------------------------------ paginación y parámetros

@pytest.mark.parametrize("limite", [1, 2, 3, 100])
def test_la_paginacion_es_estable_sin_duplicados_ni_omisiones_y_los_totales_no_dependen_de_la_pagina(mundo, limite):
    supt = entrar("supt")
    todos = supervision(supt, d(-20), d(0), limite="100").json()
    elementos, tamanos, totales = todas_las_paginas(supt, d(-20), d(0), limite)
    assert [e["actividad"]["id"] for e in elementos] == [e["actividad"]["id"] for e in todos["elementos"]]
    assert len({e["actividad"]["id"] for e in elementos}) == len(elementos) == 5
    assert all(t == limite for t in tamanos[:-1]) and sum(tamanos) == 5
    assert all(t == todos["totales_por_estado"] for t in totales)                                              # los totales son de todo el período, no de la página


@pytest.mark.parametrize("parametros,campo,motivo", [
    ({"hasta": d(0)}, "desde", "obligatorio"), ({"desde": d(-5)}, "hasta", "obligatorio"), ({"desde": d(0), "hasta": d(-1)}, "desde", "posterior_a_hasta"),
])
def test_el_periodo_es_obligatorio_y_ordenado(mundo, parametros, campo, motivo):
    r = supervision(entrar("supt"), parametros.get("desde"), parametros.get("hasta"))
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA" and r.json()["detalles"][0]["campo"] == campo and r.json()["detalles"][0]["motivo"] == motivo


def test_el_rango_maximo_el_corte_independiente_y_los_parametros_no_admitidos_se_rechazan(mundo):
    supt = entrar("supt")
    assert supervision(supt, d(-91), d(0)).status_code == 200
    r = supervision(supt, d(-92), d(0))
    assert r.status_code == 400 and r.json()["detalles"] == [{"campo": "hasta", "motivo": "rango_excede_el_maximo", "maximo_dias": 92}]
    for extra in ({"corte": d(-5).isoformat()}, {"estado": "Bloqueada"}, {"q": "x"}, {"persona_id": str(mundo["ana"])}):                    # D-06: no hay parámetro `corte`
        r = supervision(supt, d(-20), d(0), **extra)
        assert r.status_code == 400 and r.json()["detalles"][0]["motivo"] == "parametro_no_soportado", extra
    for malo in ("2026-13-45", "03-11-2026"):
        assert supervision(supt, d(-20), d(0), limite="0").status_code == 400 and supt.get(f"{API}/equipo/supervision", params={"desde": malo, "hasta": d(0).isoformat()}).status_code == 400
    r = supt.get(f"{API}/equipo/supervision", params=[("desde", d(-5).isoformat()), ("desde", d(-4).isoformat()), ("hasta", d(0).isoformat())])
    assert r.status_code == 400 and r.json()["detalles"][0]["motivo"] == "parametro_repetido"


def test_el_formato_se_valida_antes_del_permiso_y_sin_sesion_no_se_ve_nada(mundo):
    assert supervision(entrar("beto"), None, d(0)).status_code == 400                                          # convenciones 3.2: formato antes que permiso
    assert nuevo_cliente().get(f"{API}/equipo/supervision", params={"desde": d(-5).isoformat(), "hasta": d(0).isoformat()}).status_code == 401


@pytest.mark.parametrize("cursor", ["no-es-un-cursor", "", "W10", "WyJQZW5kaWVudGUiXQ"])
def test_un_cursor_invalido_se_rechaza(mundo, cursor):
    r = supervision(entrar("supt"), d(-20), d(0), continuar_desde=cursor)
    assert r.status_code == 400 and r.json()["detalles"][0]["campo"] == "continuar_desde"


def test_un_cursor_con_un_estado_inexistente_o_forjado_no_entrega_nada_que_la_consulta_no_entregaria(mundo):
    from app.compartido import paginacion
    r = supervision(entrar("supt"), d(-20), d(0), continuar_desde=paginacion.emitir_cursor("Inventado", "00000000-0000-4000-8000-000000000000", "00000000-0000-4000-8000-000000000000"))
    assert r.status_code == 400
    forjado = paginacion.emitir_cursor("En progreso", "00000000-0000-4000-8000-000000000000", "00000000-0000-4000-8000-000000000000")
    c = supervision(entrar("supt"), d(-20), d(0), continuar_desde=forjado).json()
    assert {e["actividad"]["titulo"] for e in c["elementos"]} <= {"Revisión antigua de Ana", "Informe de Ana", "Terminada en el período"}               # solo lo autorizado posterior a esa posición


# ------------------------------------------------------------------------------------------------------ la política compartida

def test_pertenece_al_equipo_en_y_condicion_equipo_son_la_misma_regla_y_no_conceden_lo_propio(mundo):
    from datetime import datetime, timezone
    from app.db import new_session
    db = new_session()
    try:
        ahora = datetime.now(timezone.utc)
        for quien in ("supt", "supu", "pablo", "luis"):
            consultante = visibilidad.consultante_de(db, mundo[quien], hoy=H, ahora=ahora)
            for persona in ("ana", "pablo", "luis", "fina", "gina", "celia", "externa", "supt"):
                for dias in (-90, -40, -15, -11, -10, 0, 2, 5):
                    py = visibilidad.pertenece_al_equipo_en(db, consultante, mundo[persona], d(dias))
                    condicion, parametros = visibilidad.condicion_equipo(consultante, "q.pid", "q.f")
                    sql = db.execute(text(f"select {condicion} from (select cast(:pid as uuid) as pid, cast(:f as date) as f) q"), {"pid": mundo[persona], "f": d(dias), **parametros}).scalar_one()
                    assert py == sql, (quien, persona, dias)
        pablo = visibilidad.consultante_de(db, mundo["pablo"], hoy=H, ahora=ahora)                # Pablo está hoy en U
        propio_en_t = visibilidad.Registro(mundo["pablo"], d(-30))
        assert visibilidad.decidir_lectura(db, pablo, propio_en_t).visible                          # lo propio se lee siempre (RA-03)…
        assert not visibilidad.pertenece_al_equipo_en(db, pablo, mundo["pablo"], d(-30))             # …pero no es del equipo U
    finally:
        db.close()
