"""M4-T7 — M4-05, integrantes vigentes de mi equipo (``GET /api/v1/equipo/integrantes``) con FastAPI y PostgreSQL reales y el mundo de traslados de M4-T4.

Solo lo esencial: quién aparece (exactitud: los vigentes de MI equipo, no los que salieron ni los programados), que no se enumera ningún otro equipo ni otra organización, la
sesión y el acceso efectivo, los campos de salida mínimos, la paginación y la lectura sin escritura. Destructivas solo sobre ``smartwork_test``.
"""

import json
from datetime import datetime, timezone

from sqlalchemy import text

from app.compartido import visibilidad
from app.db import get_owner_engine, new_session
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia
from tests.test_consulta_bitacora import API, CLAVE, H, d, entrar
from tests.test_consulta_supervision_herencia import herencia  # noqa: F401
from tests.utiles_http import nuevo_cliente


def integrantes(cliente, **parametros):
    return cliente.get(f"{API}/equipo/integrantes", params=parametros)


def lista(cuerpo):
    return [(e["nombre"], e["rol"]) for e in cuerpo["elementos"]]


def test_cada_persona_ve_a_los_integrantes_vigentes_de_su_equipo_con_los_tres_campos_minimos(herencia):
    r = integrantes(entrar("supt"))
    c = r.json()
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store" and set(c) == {"elementos", "siguiente"} and c["siguiente"] is None
    # T hoy: supt (supervisor), ana y luis (desde d(-10)). Pablo salió de T en d(-10): no aparece, aunque sus registros de T sigan siendo consultables
    assert lista(c) == [("ana", "colaborador"), ("luis", "colaborador"), ("supt", "supervisor")]
    assert all(set(e) == {"persona_id", "nombre", "rol"} for e in c["elementos"])                              # nada más: ni correo, ni acceso, ni historial
    assert {e["persona_id"] for e in c["elementos"]} == {str(herencia[n]) for n in ("ana", "luis", "supt")}
    # un colaborador ve exactamente la misma lista, y el equipo U la suya (Pablo ya es de U; Luis dejó de serlo)
    assert integrantes(entrar("luis")).json() == c
    assert lista(integrantes(entrar("supu")).json()) == [("celia", "colaborador"), ("pablo", "colaborador"), ("supu", "supervisor")]


def test_la_lista_coincide_con_la_politica_de_pertenencia_de_m1_y_no_enumera_otros_equipos_ni_organizaciones(herencia):
    with get_owner_engine().begin() as c:                                        # otra organización con su propio equipo y su persona
        org2 = crear_organizacion(c)
        externa = crear_persona(c, "externa")
        crear_pertenencia(c, externa, crear_equipo(c, org2, "Equipo V"), "supervisor", desde=d(-200))
        crear_identidad(c, externa, "externa", CLAVE)
        todas = {n: p for n, p in herencia.items() if isinstance(p, type(externa)) and n in ("sam", "supt", "supu", "ana", "celia", "pablo", "luis")} | {"externa": externa}
    db = new_session()
    try:
        ahora = datetime.now(timezone.utc)
        for quien in ("supt", "supu", "luis", "externa"):
            consultante = visibilidad.consultante_de(db, todas[quien], hoy=H, ahora=ahora)
            esperados = sorted(n for n, p in todas.items() if visibilidad.pertenece_al_equipo_en(db, consultante, p, H))        # la misma regla en Python
            r = integrantes(entrar(quien))
            assert [e["nombre"] for e in r.json()["elementos"]] == esperados, quien
        assert [e["nombre"] for e in integrantes(entrar("externa")).json()["elementos"]] == ["externa"]                          # no cruza organizaciones
    finally:
        db.close()
    texto = json.dumps(integrantes(entrar("supt")).json())
    assert "externa" not in texto and "celia" not in texto and "sam" not in texto


def test_quien_no_puede_operar_o_no_tiene_sesion_no_enumera_a_nadie(herencia):
    supt = entrar("supt")
    assert integrantes(nuevo_cliente()).status_code == 401
    with get_owner_engine().begin() as c:
        sin_equipo = crear_persona(c, "sin_equipo")
        crear_pertenencia(c, sin_equipo, c.execute(text("select equipo_id from pertenencia where persona_id = :p limit 1"), {"p": herencia["ana"]}).scalar_one(), "colaborador", desde=d(-50))
        crear_identidad(c, sin_equipo, "sin_equipo", CLAVE)
    sesion = entrar("sin_equipo")
    assert integrantes(sesion).status_code == 200
    with get_owner_engine().begin() as c:                                        # su pertenencia termina hoy: con la sesión abierta ya no ve el equipo que dejó
        c.execute(text("update pertenencia set hasta_exclusivo = :h where persona_id = :p"), {"h": d(0), "p": sin_equipo})
    r = integrantes(sesion)
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERTENENCIA_VIGENTE"
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": herencia["supt"]})
    r = integrantes(supt)
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"


def test_no_aparecen_los_programados_ni_los_finalizados_pero_si_quien_tiene_el_acceso_desactivado(herencia):
    with get_owner_engine().begin() as c:
        equipo_t = c.execute(text("select equipo_id from pertenencia where persona_id = :p and rol = 'supervisor'"), {"p": herencia["supt"]}).scalar_one()
        for nombre, desde, hasta in (("programado", d(5), None), ("finalizado", d(-30), d(-1)), ("desactivado", d(-30), None)):
            p = crear_persona(c, nombre)
            crear_pertenencia(c, p, equipo_t, "colaborador", desde=desde, hasta=hasta)
            if nombre == "desactivado":
                c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": p})
    nombres = [e["nombre"] for e in integrantes(entrar("supt")).json()["elementos"]]
    assert "programado" not in nombres and "finalizado" not in nombres                                      # RA-02: solo la pertenencia que cubre hoy
    assert "desactivado" in nombres                                                                          # sigue siendo del equipo y sus registros se consultan (CA-30, CA-256)


def test_la_paginacion_es_estable_los_parametros_se_validan_y_la_ruta_es_de_solo_lectura(herencia):
    supt = entrar("supt")
    todo = integrantes(supt).json()["elementos"]
    paginas, cursor = [], None
    for _ in range(5):
        r = integrantes(supt, limite="1", **({"continuar_desde": cursor} if cursor else {})).json()
        paginas += r["elementos"]
        cursor = r["siguiente"]
        if cursor is None:
            break
    assert paginas == todo and len(todo) == 3
    for malo in ({"limite": "0"}, {"limite": "9999"}, {"continuar_desde": "no-es-un-cursor"}, {"equipo_id": "x"}, {"q": "ana"}):
        assert integrantes(supt, **malo).status_code == 400, malo                                           # sin parámetro de equipo ni búsqueda por texto
    r = supt.post(f"{API}/equipo/integrantes", headers={"Origin": "https://testserver"})
    assert r.status_code == 405 and r.headers["allow"] == "GET"
