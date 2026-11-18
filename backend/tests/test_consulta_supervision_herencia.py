"""M4-T4 — M4-03, herencia y continuidad de actividades entre equipos (``GET /api/v1/equipo/supervision``) con FastAPI y PostgreSQL reales y traslados reales.

Mundo: tres equipos. Pablo pasó de S a T (d(-50)) y de T a U (d(-10)); Luis estaba en U y pasó a T en d(-10). Sus actividades cruzan equipos: algunas empezaron en otro equipo y se
continuaron en el actual (heredadas). Se prueban: referencia mínima con su lista cerrada de campos (CA-218 a CA-220, CA-232), forma neutral con avances del equipo nuevo (CA-223,
CA-272, CA-301), estado al corte autorizado y no autorizado (CA-230, CA-231), el equipo anterior y el nuevo (CA-196, CA-197, CA-221, CA-222), marcada por error en otro equipo
(CA-268, CA-147), totales, orden y cursor sin filtraciones y la equivalencia entre la política en Python y los predicados SQL.
Destructivas solo sobre ``smartwork_test``.
"""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.compartido import paginacion, visibilidad
from app.db import get_owner_engine, new_session
from app.modulos.consulta import repositorio
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia
from tests.test_consulta_bitacora import CLAVE, H, _actividad, _avance, _bitacora, _marcar, _plan, d, entrar
from tests.test_consulta_supervision import por_id, supervision

NEUTRAL = {"forma", "id", "propietaria_id", "referencia_neutral"}
REFERENCIA = {"tipo", "actividad", "propietaria_id", "iniciada_en_otro_equipo", "estado_actual"}


@pytest.fixture()
def herencia():
    m: dict = {}
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c)
        s, t, u = crear_equipo(c, org, "Equipo S"), crear_equipo(c, org, "Equipo T"), crear_equipo(c, org, "Equipo U")

        def alta(nombre, equipo, rol, desde, hasta=None):
            if nombre not in m:
                m[nombre] = crear_persona(c, nombre)
                crear_identidad(c, m[nombre], nombre, CLAVE)
            crear_pertenencia(c, m[nombre], equipo, rol, desde=desde, hasta=hasta)

        alta("sam", s, "supervisor", d(-200)); alta("supt", t, "supervisor", d(-200)); alta("supu", u, "supervisor", d(-200))
        alta("ana", t, "colaborador", d(-200)); alta("celia", u, "colaborador", d(-200))
        alta("pablo", s, "colaborador", d(-100), d(-50)); alta("pablo", t, "colaborador", d(-50), d(-10)); alta("pablo", u, "colaborador", d(-10))
        alta("luis", u, "colaborador", d(-100), d(-10)); alta("luis", t, "colaborador", d(-10))

        # Ana y Celia: actividades propias del equipo
        ab6 = _bitacora(c, m["ana"], d(-6), "resumen de Ana")
        m["A1"] = a = _actividad(c, m["ana"], ab6, "Informe de Ana", estado="En progreso"); _plan(c, a, ab6); _avance(c, a, ab6, "En progreso", "avance de Ana")
        cb5 = _bitacora(c, m["celia"], d(-5), "resumen de Celia")
        m["C1"] = a = _actividad(c, m["celia"], cb5, "Tarea de Celia", estado="Pendiente"); _plan(c, a, cb5)

        # Luis: de U a T. Todo lo anterior a d(-10) es de U (protegido para T)
        lb30, lb28, lb5, lb2 = (_bitacora(c, m["luis"], d(-30), "resumen reservado de U"), _bitacora(c, m["luis"], d(-28)), _bitacora(c, m["luis"], d(-5)), _bitacora(c, m["luis"], d(-2)))
        m["H1"] = a = _actividad(c, m["luis"], lb30, "Heredada sin registros de T", estado="En progreso")
        _plan(c, a, lb30, descripcion="plan original protegido de U"); _avance(c, a, lb30, "En progreso", "descripción protegida de U")
        m["H2"] = a = _actividad(c, m["luis"], lb30, "Heredada con avance de T", estado="Bloqueada")
        _plan(c, a, lb30); _avance(c, a, lb30, "En progreso", "descripción protegida de U"); _avance(c, a, lb5, "Bloqueada", "bloqueo de Luis en T", "motivo de Luis en T")
        m["H3"] = a = _actividad(c, m["luis"], lb30, "Heredada con planificación de T", estado="En progreso")
        _plan(c, a, lb30); _avance(c, a, lb30, "En progreso", "descripción protegida de U"); _plan(c, a, lb2, "continuacion", "continuación planificada en T")
        m["H4"] = a = _actividad(c, m["luis"], lb30, "Heredada completada antes", estado="Completada")
        _plan(c, a, lb30); _avance(c, a, lb28, "Completada", "terminada en U")
        m["H5"] = a = _actividad(c, m["luis"], lb30, "Heredada marcada por error", estado="En progreso")
        _plan(c, a, lb30); _avance(c, a, lb30, "En progreso", "avance protegido"); _marcar(c, a, m["luis"])

        # Pablo: S (hasta d(-50)), T (hasta d(-10)) y U
        pb60, pb30, pb12, pb3 = (_bitacora(c, m["pablo"], d(-60), "resumen reservado de S"), _bitacora(c, m["pablo"], d(-30), "resumen reservado de T"),
                                 _bitacora(c, m["pablo"], d(-12)), _bitacora(c, m["pablo"], d(-3)))
        m["P1"] = a = _actividad(c, m["pablo"], pb30, "Tarea de Pablo", estado="En progreso")
        _plan(c, a, pb30, descripcion="plan original protegido de T"); _avance(c, a, pb30, "En progreso", "arranque en T")
        _avance(c, a, pb12, "Bloqueada", "bloqueo en T", "motivo reservado de T"); _avance(c, a, pb3, "En progreso", "continúa en U")
        m["P2"] = a = _actividad(c, m["pablo"], pb60, "Tarea heredada de S", estado="En progreso")
        _plan(c, a, pb60); _avance(c, a, pb60, "En progreso", "avance en S")
    return m


def ids(cuerpo):
    return {e["actividad"]["id"] for e in cuerpo["elementos"]}


def completo(cuerpo):
    """Todo lo que la respuesta contiene, como texto: para comprobar que algo NO está en ninguna parte."""
    return json.dumps(cuerpo, ensure_ascii=False)


SECRETOS_DE_U = ("Heredada sin registros de T", "Heredada con avance de T", "Heredada con planificación de T", "descripción protegida de U", "plan original protegido de U",
                 "resumen reservado de U", "terminada en U", "Equipo U", "Equipo S", "Equipo T", "motivo de Luis en T", "bloqueo de Luis en T", "continuación planificada en T")


# ------------------------------------------------------------------------------------------------------ referencia mínima

def test_la_actividad_heredada_sin_registros_del_equipo_es_una_referencia_minima_con_la_lista_cerrada_de_campos(herencia):
    c = supervision(entrar("supt"), d(-20), d(0)).json()
    r = next(e for e in c["elementos"] if e["tipo"] == "referencia_minima")
    assert set(r) == REFERENCIA and r["tipo"] == "referencia_minima" and r["iniciada_en_otro_equipo"] is True                      # CA-218, CA-232: distinta del acceso completo
    assert set(r["actividad"]) == NEUTRAL and r["actividad"]["referencia_neutral"] == "Actividad en continuidad" and r["actividad"]["id"] == str(herencia["H1"])
    assert r["propietaria_id"] == str(herencia["luis"]) and r["estado_actual"] == "En progreso"                                    # CA-218: propietaria y estado actual
    assert "fecha_ultimo_avance" not in r                                                                                           # CA-220: el último avance es del equipo anterior
    texto = completo(r)
    for protegido in SECRETOS_DE_U + ("origen", "titulo", "marca", "creada_en", "motivo", "descripcion", "avances", "estado_al_corte"):
        assert protegido not in texto, protegido                                                                                    # CA-219
    assert "elementos" in c and sum(1 for e in c["elementos"] if e["tipo"] == "referencia_minima") == 1


def test_las_referencias_minimas_tienen_su_recuento_aparte_y_nunca_entran_en_los_totales_por_estado(herencia):
    c = supervision(entrar("supt"), d(-20), d(0)).json()
    assert c["sin_estado_al_corte"] == {"referencias_minimas": 1, "actividades": 2}                                                  # H1 / H3 y P1
    assert c["totales_por_estado"] == {"Pendiente": 0, "En progreso": 1, "Bloqueada": 1, "Completada": 0}                            # solo A1 y H2, con estado al corte mostrado
    assert sum(c["totales_por_estado"].values()) + sum(c["sin_estado_al_corte"].values()) == len(c["elementos"])
    assert not any("estado_al_corte" in e for e in c["elementos"] if e["tipo"] == "referencia_minima")


def test_una_referencia_minima_muestra_la_fecha_del_ultimo_avance_solo_si_ese_avance_esta_autorizado(herencia):
    # corte d(-6): el avance de Luis en T (d(-5)) es posterior al corte, pero es el último de la actividad y es del equipo T
    rs = {e["actividad"]["id"]: e for e in supervision(entrar("supt"), d(-20), d(-6)).json()["elementos"] if e["tipo"] == "referencia_minima"}
    assert set(rs) == {str(herencia["H1"]), str(herencia["H2"]), str(herencia["H3"])}
    assert set(rs[str(herencia["H2"])]) == REFERENCIA | {"fecha_ultimo_avance"} and rs[str(herencia["H2"])]["fecha_ultimo_avance"] == d(-5).isoformat()
    assert rs[str(herencia["H2"])]["estado_actual"] == "Bloqueada"
    assert "fecha_ultimo_avance" not in rs[str(herencia["H1"])] and "fecha_ultimo_avance" not in rs[str(herencia["H3"])]               # CA-220


def test_si_el_estado_actual_no_se_puede_informar_la_referencia_minima_no_se_emite(herencia):
    # corte d(-12): Pablo era de T, pero hoy es de U. Su actividad heredada de S sería una referencia, pero el supervisor de T no puede informar su estado actual: no se emite (CA-221)
    c = supervision(entrar("supt"), d(-45), d(-12)).json()
    assert str(herencia["P2"]) not in completo(c) and "Tarea heredada de S" not in completo(c) and "Equipo S" not in completo(c)
    assert c["sin_estado_al_corte"]["referencias_minimas"] == 0


# ------------------------------------------------------------------------------------------------------ forma neutral y estado al corte

def test_con_un_avance_del_equipo_nuevo_la_actividad_se_identifica_con_la_referencia_neutral_y_su_estado_al_corte_se_muestra(herencia):
    c = supervision(entrar("supt"), d(-20), d(0)).json()
    h2 = por_id(c)[str(herencia["H2"])]
    assert h2["tipo"] == "actividad" and set(h2["actividad"]) == NEUTRAL and h2["actividad"]["referencia_neutral"] == "Actividad en continuidad"        # CA-223, CA-272, CA-301
    assert h2["motivo_inclusion"] == ["con_avances_en_el_periodo", "pendiente_al_corte"]
    assert h2["estado_al_corte"] == "Bloqueada" and "estado_actual_si_difiere" not in h2                                                                  # CA-231: el avance es de T
    for protegido in SECRETOS_DE_U:
        assert protegido not in completo(h2), protegido                                                                                                    # CA-272, CA-273


def test_el_estado_al_corte_determinado_por_un_avance_de_otro_equipo_no_se_muestra_ni_se_sustituye(herencia):
    c = supervision(entrar("supt"), d(-20), d(0)).json()
    e = por_id(c)
    h3 = e[str(herencia["H3"])]                                                                                                       # el último avance hasta el corte es de U; T solo tiene una planificación
    assert h3["tipo"] == "actividad" and h3["actividad"]["forma"] == "neutral" and h3["motivo_inclusion"] == ["planificada_en_el_periodo", "pendiente_al_corte"]
    assert "estado_al_corte" not in h3 and "estado_actual_si_difiere" not in h3                                                       # CA-230: sin estado al corte visible no hay diferencia que establecer
    p1 = e[str(herencia["P1"])]                                                                                                       # origen de T autorizado, pero el último avance hasta el corte es de U
    assert p1["actividad"]["forma"] == "completa" and p1["actividad"]["titulo"] == "Tarea de Pablo" and "estado_al_corte" not in p1
    assert "estado_actual_si_difiere" not in p1                                                                                        # Pablo ya no es de T: ni estado actual (CA-221)
    assert "continúa en U" not in completo(c) and "motivo reservado de T" not in completo(c)


def test_el_estado_al_corte_cambia_con_el_corte_y_se_muestra_cuando_lo_determina_un_avance_autorizado(herencia):
    e = por_id(supervision(entrar("supt"), d(-45), d(-12)).json())                                                                    # corte d(-12): Pablo aún era de T
    p1 = e[str(herencia["P1"])]
    assert p1["actividad"]["titulo"] == "Tarea de Pablo" and p1["estado_al_corte"] == "Bloqueada"                                       # CA-222: conserva lo autorizado y su estado al corte
    assert "estado_actual_si_difiere" not in p1 and p1["motivo_inclusion"] == ["planificada_en_el_periodo", "con_avances_en_el_periodo", "pendiente_al_corte"]


# ------------------------------------------------------------------------------------------------------ el equipo anterior y el nuevo

def test_el_supervisor_del_equipo_anterior_no_ve_lo_posterior_al_traslado_ni_presenta_pendiente_a_la_persona_trasladada(herencia):
    c = supervision(entrar("supt"), d(-5), d(0)).json()                                                                               # solo fechas posteriores al traslado de Pablo
    assert str(herencia["P1"]) not in completo(c) and str(herencia["P2"]) not in completo(c) and "Tarea de Pablo" not in completo(c)     # CA-197, CA-221
    assert "continúa en U" not in completo(c)


def test_el_supervisor_del_equipo_nuevo_ve_la_actividad_continuada_en_forma_neutral_sin_nada_del_equipo_anterior(herencia):
    c = supervision(entrar("supu"), d(-20), d(0)).json()
    p1 = por_id(c)[str(herencia["P1"])]
    assert p1["tipo"] == "actividad" and set(p1["actividad"]) == NEUTRAL and p1["estado_al_corte"] == "En progreso"                      # CA-223: el avance es de U
    assert p1["motivo_inclusion"] == ["con_avances_en_el_periodo", "pendiente_al_corte"] and "estado_actual_si_difiere" not in p1
    texto = completo(c)
    for protegido in ("Tarea de Pablo", "motivo reservado de T", "bloqueo en T", "arranque en T", "plan original protegido de T", "resumen reservado de T", "Equipo T", "Equipo S"):
        assert protegido not in texto, protegido                                                                                          # CA-196
    p2 = next(e for e in c["elementos"] if e["tipo"] == "referencia_minima")                                                          # de S: sin registros de U
    assert p2["actividad"]["id"] == str(herencia["P2"]) and set(p2) == REFERENCIA and p2["estado_actual"] == "En progreso"
    assert "Tarea heredada de S" not in texto and "avance en S" not in texto and "resumen reservado de S" not in texto


def test_antes_del_primer_avance_de_u_la_actividad_es_una_referencia_minima_con_la_fecha_de_ese_avance(herencia):
    rs = {e["actividad"]["id"]: e for e in supervision(entrar("supu"), d(-20), d(-5)).json()["elementos"] if e["tipo"] == "referencia_minima"}
    assert set(rs) == {str(herencia["P1"]), str(herencia["P2"])}
    assert rs[str(herencia["P1"])]["fecha_ultimo_avance"] == d(-3).isoformat() and "fecha_ultimo_avance" not in rs[str(herencia["P2"])]


def test_el_equipo_anterior_conserva_sus_registros_autorizados_con_su_estado_al_corte_y_sin_estado_actual(herencia):
    c = supervision(entrar("supu"), d(-45), d(-12)).json()                                                                            # Luis aún era de U; hoy es de T
    e = por_id(c)
    assert {k: e[str(herencia[k])]["actividad"].get("titulo") for k in ("H1", "H2", "H3", "H4")} == {
        "H1": "Heredada sin registros de T", "H2": "Heredada con avance de T", "H3": "Heredada con planificación de T", "H4": "Heredada completada antes"}      # su origen es de U
    assert [e[str(herencia[k])]["estado_al_corte"] for k in ("H1", "H2", "H3", "H4")] == ["En progreso", "En progreso", "En progreso", "Completada"]
    assert not any("estado_actual_si_difiere" in x for x in c["elementos"] if x["propietaria_id"] == str(herencia["luis"]))             # CA-222
    assert "motivo de Luis en T" not in completo(c) and "Bloqueada" not in [x.get("estado_al_corte") for x in c["elementos"]]


def test_una_actividad_marcada_por_error_no_aparece_de_ninguna_forma_en_ningun_equipo(herencia):
    for quien, desde, hasta in (("supt", -20, 0), ("supt", -20, -6), ("supu", -45, -12), ("supu", -20, 0)):
        c = supervision(entrar(quien), d(desde), d(hasta)).json()
        assert str(herencia["H5"]) not in completo(c) and "Heredada marcada por error" not in completo(c) and "motivo de la marca" not in completo(c), (quien, desde, hasta)   # CA-268, CA-147


# ------------------------------------------------------------------------------------------------------ totales, orden y cursor sin filtraciones

def test_el_orden_agrupa_primero_los_estados_mostrados_despues_los_ocultos_y_al_final_las_referencias(herencia):
    c = supervision(entrar("supt"), d(-20), d(0)).json()
    tipos = [("referencia" if e["tipo"] == "referencia_minima" else ("con_estado" if "estado_al_corte" in e else "sin_estado")) for e in c["elementos"]]
    assert tipos == ["con_estado", "con_estado", "sin_estado", "sin_estado", "referencia"]
    assert [e["estado_al_corte"] for e in c["elementos"][:2]] == ["En progreso", "Bloqueada"]


@pytest.mark.parametrize("limite", [1, 2, 3])
def test_la_paginacion_con_referencias_y_actividades_sin_estado_es_estable_y_los_totales_no_cambian(herencia, limite):
    supt = entrar("supt")
    todo = supervision(supt, d(-20), d(0), limite="100").json()
    elementos, cursor, vistos = [], None, []
    for _ in range(10):
        pag = supervision(supt, d(-20), d(0), limite=str(limite), **({"continuar_desde": cursor} if cursor else {})).json()
        elementos += pag["elementos"]
        vistos.append((pag["totales_por_estado"], pag["sin_estado_al_corte"]))
        cursor = pag["siguiente"]
        if cursor is None:
            break
    assert [e["actividad"]["id"] for e in elementos] == [e["actividad"]["id"] for e in todo["elementos"]] and len(elementos) == 5
    assert all(v == (todo["totales_por_estado"], todo["sin_estado_al_corte"]) for v in vistos)


def test_un_cursor_forjado_o_con_un_grupo_inexistente_no_entrega_nada_que_la_consulta_no_entregaria(herencia):
    supt = entrar("supt")
    todo = ids(supervision(supt, d(-20), d(0)).json())
    cero = "00000000-0000-4000-8000-000000000000"
    for grupo, esperado in (("referencia_minima", {str(herencia["H1"])}), ("En progreso", todo - set()), ("sin_estado_al_corte", {str(herencia["H3"]), str(herencia["P1"]), str(herencia["H1"])})):
        c = supervision(supt, d(-20), d(0), continuar_desde=paginacion.emitir_cursor(grupo, cero, cero)).json()
        assert ids(c) <= todo and (grupo != "referencia_minima" or ids(c) == esperado) and str(herencia["H5"]) not in completo(c), grupo
    assert supervision(supt, d(-20), d(0), continuar_desde=paginacion.emitir_cursor("Inventado", cero, cero)).status_code == 400


def test_lo_que_no_se_puede_mostrar_no_cambia_nada_de_la_respuesta(herencia):
    supt, supu = entrar("supt"), entrar("supu")
    antes_t, antes_u = supervision(supt, d(-20), d(0)).json(), supervision(supu, d(-20), d(0)).json()
    with get_owner_engine().begin() as c:                                       # cambia lo PROTEGIDO de otro equipo: el estado, la descripción y el motivo de los avances de U y de T
        c.execute(text("update avance set estado = 'Bloqueada', descripcion = 'otra cosa protegida', motivo_bloqueo = 'otro motivo protegido' "
                       "where actividad_id in (:h1, :h3) and descripcion = 'descripción protegida de U'"), {"h1": herencia["H1"], "h3": herencia["H3"]})
        c.execute(text("update avance set estado = 'En progreso', motivo_bloqueo = null where actividad_id = :p and descripcion = 'bloqueo en T'"), {"p": herencia["P1"]})
        c.execute(text("update bitacora set resumen = 'otro resumen protegido' where resumen like 'resumen reservado%'"))
        c.execute(text("update planificacion set descripcion = 'otro plan protegido' where descripcion like 'plan original protegido%'"))
    assert supervision(supt, d(-20), d(0)).json() == antes_t                    # el estado oculto de H1, H3 y P1 no cambia nada: ni lista, ni totales, ni orden, ni cursor
    assert supervision(supu, d(-20), d(0)).json() == antes_u


def test_limite_conocido_la_actividad_heredada_se_incluye_solo_si_estaba_pendiente_al_corte(herencia):
    """RN-47 exige incluir la heredada «pendiente» al corte, así que ese único dato (completada o no) sí interviene aunque el estado al corte no se pueda mostrar. Se documenta como
    riesgo residual en el plan de M4: cambiar a Completada un avance PROTEGIDO de U hace que la referencia mínima de H1 desaparezca de la vista de T."""
    supt = entrar("supt")
    assert str(herencia["H1"]) in ids(supervision(supt, d(-20), d(0)).json())
    with get_owner_engine().begin() as c:
        c.execute(text("update avance set estado = 'Completada' where actividad_id = :h and descripcion = 'descripción protegida de U'"), {"h": herencia["H1"]})
        c.execute(text("update actividad set estado_actual = 'Completada' where id = :h"), {"h": herencia["H1"]})
    c = supervision(supt, d(-20), d(0)).json()
    assert str(herencia["H1"]) not in completo(c) and c["sin_estado_al_corte"]["referencias_minimas"] == 0


# ------------------------------------------------------------------------------------------------------ la política compartida

def test_las_reglas_de_presentacion_son_las_de_la_politica_compartida():
    f = visibilidad.forma_en_supervision
    assert [f(o, r) for o in (True, False) for r in (True, False)] == ["completa", "completa", "neutral", "referencia_minima"]
    e = visibilidad.estado_al_corte_es_visible
    assert [e(hay, ultimo, origen) for hay in (True, False) for ultimo in (True, False) for origen in (True, False)] == [
        True, True, False, False,                      # hay avances: manda el último
        True, False, True, False]                      # sin avances: manda el origen


def test_los_hechos_que_calcula_sql_coinciden_con_la_politica_en_python_y_no_sacan_lo_protegido(herencia):
    db = new_session()
    try:
        supt = visibilidad.consultante_de(db, herencia["supt"], hoy=H, ahora=datetime.now(timezone.utc))
        filas = repositorio.actividades_candidatas(db, supt, d(-45), d(0))
        assert filas
        with get_owner_engine().connect() as c:
            origen = {r.id: r.fecha for r in c.execute(text("select a.id, b.fecha_laboral as fecha from actividad a join bitacora b on b.id = a.bitacora_origen_id")).all()}
            planes = c.execute(text("select pl.actividad_id as a, b.fecha_laboral as f from planificacion pl join bitacora b on b.id = pl.bitacora_id")).all()
        for fila in filas:
            python = visibilidad.pertenece_al_equipo_en(db, supt, fila.propietaria_id, origen[fila.id])
            assert fila.origen_autorizado == python, fila.id
            assert (fila.titulo is not None) == python and (fila.fecha_laboral_origen is not None) == python and (fila.creada_en is not None) == python   # lo protegido no sale de la base
            if fila.propietaria_id != supt.persona_id:                                                           # para los demás, es la misma decisión que M4-01 (forma_de_actividad)
                forma = visibilidad.forma_de_actividad(db, supt, visibilidad.Registro(fila.propietaria_id, origen[fila.id]), marcada_por_error=False)
                assert (forma == visibilidad.Forma.COMPLETA) == python
        avances = repositorio.avances_de_las_actividades(db, supt, [f.id for f in filas])
        with get_owner_engine().connect() as c:
            fechas = {r.id: r.fecha for r in c.execute(text("select av.id, b.fecha_laboral as fecha from avance av join bitacora b on b.id = av.bitacora_id")).all()}
        propietaria = {f.id: f.propietaria_id for f in filas}
        assert avances
        for a in avances:
            assert a.autorizado == visibilidad.pertenece_al_equipo_en(db, supt, propietaria[a.actividad_id], fechas[a.id]), a.id
        esperadas = {a for a, f in ((p.a, p.f) for p in planes) if a in propietaria and f <= d(0) and visibilidad.pertenece_al_equipo_en(db, supt, propietaria[a], f)}
        assert repositorio.actividades_con_planificacion_autorizada(db, supt, [f.id for f in filas], d(0)) == esperadas
    finally:
        db.close()
