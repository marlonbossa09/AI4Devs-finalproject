"""M4-T1 — M4-01 «Consultar la bitácora de un compañero» (``GET /api/v1/personas/{persona_id}/bitacoras/{fecha_laboral}``) con FastAPI y PostgreSQL reales.

Pruebas focalizadas (metodología ligera): acceso propio; compañeros y supervisor; incorporado después; traslados entre equipos (CA-15 a CA-18, CA-176, CA-177, CA-216,
CA-217); recursos inexistentes y no autorizados indistinguibles (CA-132, CA-291); consultante desactivado o sin pertenencia; registros históricos de personas finalizadas y
desactivadas (CA-30, CA-256); proyecciones neutrales y ocultas sin filtrar nada del equipo anterior (RA-04 a RA-08); y que no hay escritura ajena (CA-131, CA-194).
Destructivas solo sobre ``smartwork_test``.
"""

import json
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.compartido import visibilidad
from app.db import get_engine, get_owner_engine
from app.modulos.consulta.proyecciones import REFERENCIA_NEUTRAL
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, hoy
from tests.utiles_http import API, iniciar_sesion, nuevo_cliente
from tests.utiles_m2 import contar

CLAVE = "contraseña-de-prueba-123"
H = hoy()


def d(n: int):
    return H + timedelta(days=n)


# ------------------------------------------------------------------------------------------------------ datos (SQL directo, propietario)

def _bitacora(c, persona, fecha, resumen="resumen de la jornada"):
    return c.execute(text("insert into bitacora (persona_id, fecha_laboral, resumen) values (:p, :f, :r) returning id"), {"p": persona, "f": fecha, "r": resumen}).scalar_one()


def _actividad(c, persona, bitacora, titulo, *, estado="En progreso", marcada=False):
    return c.execute(
        text("insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen, estado_actual, registrada_por_error, motivo_error, marcada_por, marcada_en) "
             "values (:p, :b, :t, 'planificada', :e, :m, :me, :mp, :mn) returning id"),
        {"p": persona, "b": bitacora, "t": titulo, "e": estado, "m": marcada, "me": "motivo de la marca" if marcada else None, "mp": persona if marcada else None,
         "mn": None if not marcada else d(-1)}).scalar_one()


def _marcar(c, actividad, persona):
    """Marca la actividad como registrada por error DESPUÉS de sus registros: la base impide registrar sobre una actividad ya marcada."""
    c.execute(text("update actividad set registrada_por_error = true, motivo_error = 'motivo de la marca', marcada_por = :p, marcada_en = now() where id = :a"), {"p": persona, "a": actividad})


def _plan(c, actividad, bitacora, tipo="original", descripcion="descripción de la planificación"):
    return c.execute(text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) values (:a, :b, :t, :d) returning id"),
                     {"a": actividad, "b": bitacora, "t": tipo, "d": descripcion}).scalar_one()


def _avance(c, actividad, bitacora, estado, descripcion, motivo=None):
    return c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion, motivo_bloqueo) values (:a, :b, :e, :d, :m) returning id"),
                     {"a": actividad, "b": bitacora, "e": estado, "d": descripcion, "m": motivo}).scalar_one()


@pytest.fixture()
def mundo():
    """Equipos T (supervisora, Ana, Beto, Quique —incorporado después—, Fina —finalizada—, Zeta —desactivada— y Pablo hasta d(-10)) y U (supervisor, Celia y Pablo desde d(-10)),
    más una persona de otra organización."""
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

        alta("supt", t, "supervisor", d(-60))
        alta("supu", u, "supervisor", d(-60))
        for nombre in ("ana", "beto", "zeta"):
            alta(nombre, t, "colaborador", d(-60))
        alta("quique", t, "colaborador", d(-5))
        alta("fina", t, "colaborador", d(-60), d(-20))
        alta("celia", u, "colaborador", d(-60))
        pablo = alta("pablo", t, "colaborador", d(-60), d(-10))          # trasladado de T a U en d(-10)
        crear_pertenencia(c, pablo, u, "colaborador", desde=d(-10))
        c.execute(text("update persona set acceso_desactivado_en = now() - interval '1 day' where id = :p"), {"p": m["zeta"]})
        org2 = crear_organizacion(c)
        v = crear_equipo(c, org2, "Equipo V")
        alta("externa", v, "supervisor", d(-60))

        # Ana: una jornada antigua (anterior a Quique), una con una actividad marcada por error y una reciente con continuación
        b = m["b_ana_30"] = _bitacora(c, m["ana"], d(-30), "resumen de Ana del día -30")
        m["a_informe"] = a = _actividad(c, m["ana"], b, "Informe de Ana")
        _plan(c, a, b)
        _avance(c, a, b, "En progreso", "Primer avance de Ana")
        b = m["b_ana_4"] = _bitacora(c, m["ana"], d(-4))
        m["a_error"] = a = _actividad(c, m["ana"], b, "Tarea registrada por error")
        _plan(c, a, b)
        _marcar(c, a, m["ana"])
        b = m["b_ana_3"] = _bitacora(c, m["ana"], d(-3))
        _plan(c, m["a_informe"], b, "continuacion", "continúa el informe")
        _avance(c, m["a_informe"], b, "En progreso", "Seguimiento del informe")

        # Pablo: en T trabaja una actividad con un bloqueo; ya en U la continúa, empieza otra y tiene otra marcada por error con una continuación
        b = m["b_pablo_30"] = _bitacora(c, m["pablo"], d(-30), "resumen reservado del equipo T")
        m["a_tarea_t"] = a = _actividad(c, m["pablo"], b, "Tarea secreta del equipo T")
        _plan(c, a, b)
        _avance(c, a, b, "En progreso", "Avance interno del equipo T")
        _avance(c, a, b, "Bloqueada", "Bloqueo en el equipo T", "motivo-reservado-del-equipo-T")
        m["a_marcada_t"] = a2 = _actividad(c, m["pablo"], b, "Tarea marcada del equipo T")
        _plan(c, a2, b)
        b = m["b_pablo_3"] = _bitacora(c, m["pablo"], d(-3), "resumen de Pablo en U")
        _avance(c, m["a_tarea_t"], b, "En progreso", "Continúa en el equipo U")
        _plan(c, m["a_marcada_t"], b, "continuacion", "continuación de la marcada")
        _marcar(c, a2, m["pablo"])
        m["a_tarea_u"] = a = _actividad(c, m["pablo"], b, "Tarea nueva en U", estado="Pendiente")
        _plan(c, a, b)
        _avance(c, a, b, "Pendiente", "Arranca en U")

        m["b_fina_30"] = _bitacora(c, m["fina"], d(-30), "resumen de Fina")
        _plan(c, _actividad(c, m["fina"], m["b_fina_30"], "Tarea de Fina"), m["b_fina_30"])
        m["b_zeta_2"] = _bitacora(c, m["zeta"], d(-2), "resumen de Zeta")
        _plan(c, _actividad(c, m["zeta"], m["b_zeta_2"], "Tarea de Zeta"), m["b_zeta_2"])
        m["b_supt_3"] = _bitacora(c, m["supt"], d(-3), "resumen de la supervisora")
        _plan(c, _actividad(c, m["supt"], m["b_supt_3"], "Plan de la supervisora"), m["b_supt_3"])
        m["b_celia_3"] = _bitacora(c, m["celia"], d(-3))
        m["b_externa_3"] = _bitacora(c, m["externa"], d(-3))
        m["t"], m["u"] = t, u
    return m


def entrar(nombre: str):
    cliente = nuevo_cliente()
    assert iniciar_sesion(cliente, nombre, CLAVE).status_code == 201
    return cliente


def leer(cliente, persona, fecha):
    return cliente.get(f"{API}/personas/{persona}/bitacoras/{fecha.isoformat() if hasattr(fecha, 'isoformat') else fecha}")


def huella(r):
    return (r.status_code, r.json(), r.headers.get("cache-control"))


def sin_forma(cuerpo: dict) -> dict:
    return {**cuerpo, "actividades": [{k: v for k, v in a.items() if k != "forma"} for a in cuerpo["actividades"]]}


# ------------------------------------------------------------------------------------------------------ acceso propio

def test_la_propia_bitacora_equivale_a_m2_01a(mundo):
    ana = entrar("ana")
    r = leer(ana, mundo["ana"], d(-3))
    propia = ana.get(f"{API}/mi/bitacoras/{d(-3).isoformat()}")
    assert r.status_code == 200 and propia.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert sin_forma(r.json()) == propia.json()                                                    # mismo contenido, más el campo ``forma``
    assert {a["forma"] for a in r.json()["actividades"]} == {"completa"} and all("estado_actual" in a for a in r.json()["actividades"])


# ------------------------------------------------------------------------------------------------------ compañeros y supervisor

def test_un_companero_lee_la_bitacora_de_otro_con_el_detalle_propio_de_cada_registro_y_en_solo_lectura(mundo):
    r = leer(entrar("beto"), mundo["ana"], d(-3))
    cuerpo = r.json()
    assert r.status_code == 200 and cuerpo["bitacora"]["persona_id"] == str(mundo["ana"]) and cuerpo["bitacora"]["fecha_laboral"] == d(-3).isoformat()
    informe = next(a for a in cuerpo["actividades"] if a["id"] == str(mundo["a_informe"]))
    assert informe["forma"] == "completa" and informe["titulo"] == "Informe de Ana" and informe["estado_actual"] == "En progreso"       # Ana sigue en T
    assert [a["descripcion"] for a in cuerpo["avances"]] == ["Seguimiento del informe"] and [p["tipo"] for p in cuerpo["planificaciones"]] == ["continuacion"]
    assert all("titulo" not in x for x in cuerpo["avances"] + cuerpo["planificaciones"])           # el detalle propio no lleva el título (RA-05)


def test_el_supervisor_lee_a_su_colaboradora_y_el_colaborador_lee_al_supervisor_del_equipo(mundo):
    assert leer(entrar("supt"), mundo["ana"], d(-3)).status_code == 200
    r = leer(entrar("beto"), mundo["supt"], d(-3))                                                   # CA-133
    assert r.status_code == 200 and r.json()["bitacora"]["resumen"] == "resumen de la supervisora"


def test_quien_se_incorporo_despues_lee_los_registros_historicos_de_su_equipo(mundo):
    r = leer(entrar("quique"), mundo["ana"], d(-30))                                                 # CA-193: Quique llegó en d(-5)
    assert r.status_code == 200 and r.json()["bitacora"]["resumen"] == "resumen de Ana del día -30"


def test_ninguna_ruta_de_m4_escribe_y_leer_no_cambia_nada(mundo):
    beto = entrar("beto")
    antes = (contar("bitacora"), contar("avance"), contar("planificacion"), contar("auditoria"))
    ruta = f"{API}/personas/{mundo['ana']}/bitacoras/{d(-3).isoformat()}"
    for metodo in ("post", "put", "patch", "delete"):                                                # CA-131, CA-194: no existe ninguna operación de escritura
        r = getattr(beto, metodo)(ruta, headers={"Origin": "https://testserver"})
        assert r.status_code == 405 and r.headers["allow"] == "GET", metodo
    assert leer(beto, mundo["ana"], d(-3)).status_code == 200
    assert leer(beto, mundo["ana"], d(-1)).status_code == 404                                        # una fecha sin bitácora no la crea
    assert (contar("bitacora"), contar("avance"), contar("planificacion"), contar("auditoria")) == antes


# ------------------------------------------------------------------------------------------------------ traslados entre equipos

def test_los_equipos_ven_solo_los_registros_de_su_periodo_tras_un_traslado(mundo):
    beto, celia = entrar("beto"), entrar("celia")                                                    # beto: T, celia: U; Pablo pasó de T a U en d(-10)
    assert leer(beto, mundo["pablo"], d(-30)).status_code == 200                                     # CA-15 (anterior al traslado, equipo anterior)
    assert leer(celia, mundo["pablo"], d(-30)).status_code == 404                                    # CA-16 (anterior, equipo nuevo)
    assert leer(beto, mundo["pablo"], d(-3)).status_code == 404                                      # CA-17 (posterior, equipo anterior)
    assert leer(celia, mundo["pablo"], d(-3)).status_code == 200                                     # CA-18 (posterior, equipo nuevo)
    assert leer(entrar("supt"), mundo["pablo"], d(-30)).status_code == 200 and leer(entrar("supt"), mundo["pablo"], d(-3)).status_code == 404
    assert leer(entrar("supu"), mundo["pablo"], d(-30)).status_code == 404 and leer(entrar("supu"), mundo["pablo"], d(-3)).status_code == 200


def test_quien_se_incorpora_despues_lee_lo_del_equipo_en_esa_fecha_pero_no_lo_del_otro(mundo):
    quique = entrar("quique")                                                                         # CA-176 y CA-177
    assert leer(quique, mundo["pablo"], d(-30)).status_code == 200 and leer(quique, mundo["pablo"], d(-3)).status_code == 404


def test_el_equipo_anterior_no_ve_el_estado_actual_de_una_persona_trasladada(mundo):
    r = leer(entrar("beto"), mundo["pablo"], d(-30))                                                  # CA-221: Pablo ya está en U
    cuerpo = r.json()
    tarea = next(a for a in cuerpo["actividades"] if a["id"] == str(mundo["a_tarea_t"]))
    assert tarea["forma"] == "completa" and tarea["titulo"] == "Tarea secreta del equipo T" and "estado_actual" not in tarea
    assert {a["descripcion"] for a in cuerpo["avances"]} == {"Avance interno del equipo T", "Bloqueo en el equipo T"}      # el equipo T ve lo suyo
    # el equipo nuevo ve el estado actual de lo que Pablo trabaja ahora en U
    nueva = next(a for a in leer(entrar("celia"), mundo["pablo"], d(-3)).json()["actividades"] if a["id"] == str(mundo["a_tarea_u"]))
    assert nueva["forma"] == "completa" and nueva["estado_actual"] == "Pendiente"


# ------------------------------------------------------------------------------------------------------ proyecciones neutrales y ocultas

def test_el_equipo_nuevo_ve_la_actividad_heredada_en_forma_neutral_sin_nada_del_equipo_anterior(mundo):
    r = leer(entrar("celia"), mundo["pablo"], d(-3))
    cuerpo = r.json()
    heredada = next(a for a in cuerpo["actividades"] if a["id"] == str(mundo["a_tarea_t"]))
    assert heredada == {"forma": "neutral", "id": str(mundo["a_tarea_t"]), "propietaria_id": str(mundo["pablo"]), "referencia_neutral": REFERENCIA_NEUTRAL}   # lista cerrada de campos
    assert "Continúa en el equipo U" in [a["descripcion"] for a in cuerpo["avances"]]                  # el avance de U se muestra con su detalle propio (CA-223)
    assert next(a for a in cuerpo["avances"] if a["descripcion"] == "Continúa en el equipo U")["actividad_id"] == heredada["id"]
    # recorrido completo del JSON: nada del equipo anterior, ni del título, ni del motivo, ni del nombre del equipo, ni de la jornada de origen
    texto = json.dumps(cuerpo, ensure_ascii=False)
    for prohibido in ("Tarea secreta del equipo T", "motivo-reservado-del-equipo-T", "Avance interno del equipo T", "Bloqueo en el equipo T", "Equipo T",
                      "resumen reservado del equipo T", d(-30).isoformat()):
        assert prohibido not in texto, prohibido


def test_una_actividad_marcada_por_error_de_otro_equipo_no_aparece_ni_sus_registros(mundo):
    cuerpo = leer(entrar("celia"), mundo["pablo"], d(-3)).json()                                       # la marcada nació en T; en U solo hay una continuación suya (RA-08)
    assert str(mundo["a_marcada_t"]) not in json.dumps(cuerpo) and "continuación de la marcada" not in json.dumps(cuerpo)
    assert {a["id"] for a in cuerpo["actividades"]} == {str(mundo["a_tarea_t"]), str(mundo["a_tarea_u"])}


def test_quien_esta_autorizado_sobre_el_origen_ve_la_marca_de_error_con_su_motivo(mundo):
    cuerpo = leer(entrar("beto"), mundo["ana"], d(-4)).json()                                          # RA-04: el origen es de su equipo
    marcada = next(a for a in cuerpo["actividades"] if a["id"] == str(mundo["a_error"]))
    assert marcada["forma"] == "completa" and marcada["marca_error"]["motivo"] == "motivo de la marca"


# ------------------------------------------------------------------------------------------------------ recursos inexistentes y no autorizados

def test_inexistente_y_no_autorizado_son_indistinguibles(mundo):
    beto = entrar("beto")
    casos = [
        leer(beto, "00000000-0000-4000-8000-000000000001", d(-3)),            # persona inexistente
        leer(beto, mundo["celia"], d(-3)),                                      # persona de otro equipo (con bitácora ese día)
        leer(beto, mundo["externa"], d(-3)),                                    # persona de otra organización (con bitácora ese día)
        leer(beto, mundo["pablo"], d(-3)),                                      # fecha en que pertenecía a otro equipo
        leer(beto, mundo["ana"], d(-1)),                                        # autorizado, pero sin bitácora ese día
        leer(beto, mundo["ana"], d(-70)),                                       # fecha anterior a toda pertenencia
    ]
    assert len({json.dumps(huella(r), sort_keys=True) for r in casos}) == 1
    assert casos[0].status_code == 404 and casos[0].json()["codigo"] == "RECURSO_NO_DISPONIBLE" and casos[0].json()["detalles"] == []


def test_el_formato_se_valida_antes_que_el_recurso_y_sin_sesion_no_se_ve_nada(mundo):
    beto = entrar("beto")
    for persona, fecha in (("no-es-un-uuid", d(-3).isoformat()), (str(mundo["celia"]), "03-11-2026"), (str(mundo["celia"]), "2026-13-45")):
        r = leer(beto, persona, fecha)
        assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA", (persona, fecha)
    r = nuevo_cliente().get(f"{API}/personas/{mundo['ana']}/bitacoras/{d(-3).isoformat()}")
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"


# ------------------------------------------------------------------------------------------------------ consultante sin acceso y registros históricos

def test_un_consultante_desactivado_o_sin_pertenencia_no_consulta_nada_ni_lo_propio(mundo):
    beto, ana = entrar("beto"), entrar("ana")
    assert leer(beto, mundo["ana"], d(-3)).status_code == 200
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": mundo["beto"]})
        c.execute(text("update pertenencia set hasta_exclusivo = :h where persona_id = :p"), {"h": H, "p": mundo["ana"]})
    r = leer(beto, mundo["ana"], d(-3))
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"
    r = leer(ana, mundo["ana"], d(-3))                                                                  # ni siquiera lo propio (IR-38)
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERTENENCIA_VIGENTE"


def test_los_registros_de_personas_finalizadas_o_desactivadas_siguen_siendo_del_equipo_de_su_fecha(mundo):
    beto, supt = entrar("beto"), entrar("supt")
    fina = leer(beto, mundo["fina"], d(-30))                                                            # CA-30: finalizó en d(-20)
    zeta = leer(supt, mundo["zeta"], d(-2))                                                             # CA-256: acceso desactivado
    assert fina.status_code == 200 and fina.json()["bitacora"]["resumen"] == "resumen de Fina"
    assert zeta.status_code == 200 and zeta.json()["bitacora"]["resumen"] == "resumen de Zeta"
    assert "estado_actual" not in fina.json()["actividades"][0]                                           # Fina ya no pertenece al equipo
    assert "estado_actual" in zeta.json()["actividades"][0]                                               # Zeta sigue perteneciendo a T (solo se desactivó su acceso)
    assert leer(entrar("celia"), mundo["fina"], d(-30)).status_code == 404 and leer(entrar("celia"), mundo["zeta"], d(-2)).status_code == 404   # y siguen sin ser de U


# ------------------------------------------------------------------------------------------------------ una sola política

def test_el_estado_actual_lo_decide_la_politica_de_m1(mundo):
    from datetime import datetime, timezone
    from app.db import new_session
    db = new_session()
    try:
        yo = visibilidad.consultante_de(db, mundo["beto"], hoy=H, ahora=datetime.now(timezone.utc))
        assert visibilidad.puede_ver_estado_actual(db, yo, mundo["beto"])                       # lo propio
        assert visibilidad.puede_ver_estado_actual(db, yo, mundo["ana"])                        # alguien que pertenece hoy a su equipo
        assert not visibilidad.puede_ver_estado_actual(db, yo, mundo["pablo"])                  # pasó a otro equipo
        assert not visibilidad.puede_ver_estado_actual(db, yo, mundo["fina"])                   # ya no pertenece a ningún equipo
        assert not visibilidad.puede_ver_estado_actual(db, yo, mundo["celia"])                  # otro equipo
        sin_acceso = visibilidad.consultante_de(db, mundo["zeta"], hoy=H, ahora=datetime.now(timezone.utc))
        assert not visibilidad.puede_ver_estado_actual(db, sin_acceso, mundo["zeta"])           # quien no puede operar no ve nada, ni lo propio
    finally:
        db.close()
