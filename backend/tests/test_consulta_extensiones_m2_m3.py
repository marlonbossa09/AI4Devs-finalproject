"""M4-T6 — extensiones aprobadas de M2 y M3 (D-M4-01), con FastAPI y PostgreSQL reales y el mundo de traslados de M4-T4.

A. Seis escrituras de M2/M3 sobre registros de otra persona (CA-72, CA-101, CA-107, CA-118, CA-123, CA-127, CA-178, CA-183, CA-194): ``OPERACION_NO_PERMITIDA`` (403) si el registro le es
   VISIBLE a quien opera según la política de visibilidad histórica de M1 (``decidir_lectura``) y ``RECURSO_NO_DISPONIBLE`` (404) indistinguible si no lo es o no existe (T-01). Nada
   cambia en la base. Las operaciones propias siguen igual y el detalle ajeno de M2-07 conserva su 404 (el contrato remite a M4-04).
B. Auditoría de M3-07 (CA-110 a CA-113, CA-286): la propietaria y el supervisor vigente del equipo del registro por su fecha laboral; nadie más; sin auditoría de provisión; y el
   supervisor trasladado, sin rol vigente o desactivado pierde el acceso. Destructivas solo sobre ``smartwork_test``.
"""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.compartido import visibilidad
from app.db import get_owner_engine, new_session
from app.modulos.auditoria import repositorio as auditoria
from tests.test_consulta_bitacora import CLAVE, H, d
from tests.test_consulta_supervision_herencia import herencia  # noqa: F401
from tests.test_correccion_api import corregir
from tests.test_marca_error_api import marcar, revertir
from tests.test_reactivacion_api import reactivar
from tests.utiles_http import API, iniciar_sesion, nuevo_cliente
from tests.utiles_m2 import avanzar, con_clave, iso

NO_EXISTE = "00000000-0000-4000-8000-0000000000bb"
SECRETO = "descripción de Ana que no se ve en otro equipo"


def entrar_con_csrf(nombre):
    cliente = nuevo_cliente()
    r = iniciar_sesion(cliente, nombre, CLAVE)
    assert r.status_code == 201
    return cliente, r.json()["csrf_token"]


def seis_escrituras(sesion, actividad, avance):
    cliente, csrf = sesion
    return {
        "M2-05 avance": avanzar(cliente, csrf, actividad, iso(0)),
        "M2-04 continuación": cliente.post(f"{API}/mi/actividades/{actividad}/continuaciones-planificadas", json={"fecha_laboral": iso(3), "descripcion": "x"}, headers=con_clave(csrf)),
        "M3-04 reactivación": reactivar(cliente, csrf, actividad, iso(0)),
        "M3-05 marca de error": marcar(cliente, csrf, actividad),
        "M3-06 reversión de la marca": revertir(cliente, csrf, actividad),
        "M3-03 corrección": corregir(cliente, csrf, avance, descripcion="Intento"),
    }


def id_de_avance(descripcion):
    with get_owner_engine().connect() as c:
        return c.execute(text("select id from avance where descripcion = :d"), {"d": descripcion}).scalar_one()


def instantanea():
    with get_owner_engine().connect() as c:
        return c.execute(text("select (select count(*) from avance) || '/' || (select count(*) from planificacion) || '/' || (select count(*) from auditoria) || '/' || "
                              "(select count(*) filter (where registrada_por_error) from actividad) || '/' || (select string_agg(estado_actual, ',' order by id) from actividad)")).scalar_one()


# ------------------------------------------------------------------------------------------------------ A. 403 y 404 en las escrituras

def test_las_seis_escrituras_sobre_un_registro_visible_de_otra_persona_responden_403_y_no_cambian_nada(herencia):
    av_ana, av_pablo = id_de_avance("avance de Ana"), id_de_avance("bloqueo en T")
    antes = instantanea()
    casos = [("luis", "colaborador del equipo de Ana", herencia["A1"], av_ana), ("supt", "supervisor del equipo de Ana", herencia["A1"], av_ana),
             ("supt", "supervisor del equipo de T con la persona ya trasladada a U (CA-178)", herencia["P1"], av_pablo)]
    for quien, descripcion, actividad, avance in casos:
        for operacion, r in seis_escrituras(entrar_con_csrf(quien), actividad, avance).items():
            assert r.status_code == 403 and r.json()["codigo"] == "OPERACION_NO_PERMITIDA", (quien, descripcion, operacion, r.status_code)
    assert instantanea() == antes                                                                                     # ninguna escritura prosperó, ni siquiera parcialmente


def test_lo_que_no_es_visible_y_lo_inexistente_responden_el_mismo_404_en_las_seis(herencia):
    av_ana = id_de_avance("avance de Ana")
    antes = instantanea()
    inexistente = seis_escrituras(entrar_con_csrf("supt"), NO_EXISTE, NO_EXISTE)
    assert {r.status_code for r in inexistente.values()} == {404}
    for quien, actividad, avance in (("supu", herencia["A1"], av_ana),                   # el supervisor de otro equipo
                                     ("celia", herencia["A1"], av_ana),                  # una colaboradora de otro equipo
                                     ("supu", herencia["P1"], id_de_avance("bloqueo en T"))):          # la persona hoy es de su equipo, pero el registro es de T
        for operacion, r in seis_escrituras(entrar_con_csrf(quien), actividad, avance).items():
            assert r.status_code == 404 and r.json() == inexistente[operacion].json() and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE", (quien, operacion)   # T-01
    assert instantanea() == antes


def test_las_operaciones_propias_siguen_funcionando_y_el_detalle_ajeno_de_m2_07_conserva_su_404(herencia):
    ana, csrf = entrar_con_csrf("ana")
    av = id_de_avance("avance de Ana")
    assert marcar(ana, csrf, herencia["A1"]).status_code == 200 and revertir(ana, csrf, herencia["A1"]).status_code == 200     # antes de que haya avances posteriores al origen (M3-05)
    assert avanzar(ana, csrf, herencia["A1"], iso(0)).status_code == 201
    assert ana.post(f"{API}/mi/actividades/{herencia['A1']}/continuaciones-planificadas", json={"fecha_laboral": iso(3), "descripcion": "x"}, headers=con_clave(csrf)).status_code == 201
    assert corregir(ana, csrf, av, descripcion="Corregido por Ana").status_code == 200
    # M2-07 (detalle propio): el contrato dice «las demás personas: M4-04», así que NO pasa a 403; un compañero y el supervisor siguen recibiendo el 404 de siempre
    assert ana.get(f"{API}/mi/actividades/{herencia['A1']}").status_code == 200
    inexistente = entrar_con_csrf("supt")[0].get(f"{API}/mi/actividades/{NO_EXISTE}")
    for quien in ("luis", "supt"):
        r = entrar_con_csrf(quien)[0].get(f"{API}/mi/actividades/{herencia['A1']}")
        assert r.status_code == 404 and r.json() == inexistente.json(), quien


# ------------------------------------------------------------------------------------------------------ B. auditoría del supervisor

def _auditar(herencia):
    """Entradas reales (marca y reversión de Ana por la API) y entradas escritas directamente: de un avance de T, de uno de U y de provisión."""
    ana, csrf = entrar_con_csrf("ana")
    r = marcar(ana, csrf, herencia["A1"])
    assert r.status_code == 200, r.text
    assert revertir(ana, csrf, herencia["A1"]).status_code == 200
    av_t, av_u = id_de_avance("bloqueo en T"), id_de_avance("continúa en U")
    with get_owner_engine().begin() as c:
        for avance, fecha, motivo in ((av_t, d(-12), "corrección en T"), (av_u, d(-3), "corrección en U")):
            c.execute(text("insert into auditoria (tipo_autor, autor_persona_id, operacion, tipo_objeto, objeto_id, propietaria_registro_id, fecha_laboral_registro, motivo, valor_anterior, valor_nuevo) "
                           "values ('persona', :p, 'correccion', 'avance', :o, :p, :f, :m, '{}', '{}')"), {"p": herencia["pablo"], "o": avance, "f": fecha, "m": motivo})
        c.execute(text("insert into auditoria (tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id, propietaria_registro_id, fecha_laboral_registro, valor_nuevo) "
                       "values ('provision', 'procedimiento-1', 'alta', 'actividad', :o, :p, :f, '{}')"), {"o": herencia["A1"], "p": herencia["ana"], "f": d(-6)})
    return ana, av_t, av_u


def auditoria_de(cliente, tipo, objeto, **parametros):
    return cliente.get(f"{API}/auditoria", params={"tipo_objeto": tipo, "objeto_id": str(objeto), **parametros})


def test_el_supervisor_consulta_la_auditoria_del_equipo_de_cada_registro_y_nadie_mas(herencia):
    ana, av_t, av_u = _auditar(herencia)
    supt, supu, luis = entrar_con_csrf("supt")[0], entrar_con_csrf("supu")[0], entrar_con_csrf("luis")[0]
    propia = auditoria_de(ana, "actividad", herencia["A1"]).json()
    r = auditoria_de(supt, "actividad", herencia["A1"])
    assert r.status_code == 200 and r.json() == propia and [e["operacion"] for e in propia["elementos"]] == ["marca_error", "reversion_marca"]            # CA-111, orden cronológico
    assert all(e["tipo_autor"] == "persona" for e in r.json()["elementos"]) and "alta" not in json.dumps(r.json())                                        # sin auditoría de provisión (D-11)
    # por el equipo HISTÓRICO de cada registro: el avance de Pablo de cuando era de T lo consulta el supervisor de T, y el de cuando es de U, el de U
    assert [e["motivo"] for e in auditoria_de(supt, "avance", av_t).json()["elementos"]] == ["corrección en T"] and auditoria_de(supu, "avance", av_t).status_code == 404
    assert [e["motivo"] for e in auditoria_de(supu, "avance", av_u).json()["elementos"]] == ["corrección en U"] and auditoria_de(supt, "avance", av_u).status_code == 404
    # un compañero que no es la propietaria ni el supervisor, y el supervisor de otro equipo: lo mismo que un registro inexistente (CA-112, CA-113, CA-286)
    inexistente = auditoria_de(supt, "actividad", NO_EXISTE)
    for cliente in (luis, supu):
        r = auditoria_de(cliente, "actividad", herencia["A1"])
        assert r.status_code == 404 and r.json() == inexistente.json() and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"
    assert auditoria_de(supt, "bitacora", herencia["A1"]).status_code == 404                                                                       # un id de otro tipo: tampoco existe


def test_la_paginacion_de_la_auditoria_del_supervisor_es_estable_y_no_filtra_nada(herencia):
    ana, _, av_u = _auditar(herencia)
    supt = entrar_con_csrf("supt")[0]
    completa = auditoria_de(supt, "actividad", herencia["A1"]).json()["elementos"]
    paginas, cursor = [], None
    for _ in range(5):
        r = auditoria_de(supt, "actividad", herencia["A1"], limite="1", **({"continuar_desde": cursor} if cursor else {})).json()
        paginas += r["elementos"]
        cursor = r["siguiente"]
        if cursor is None:
            break
    assert paginas == completa and len(paginas) == 2
    # un cursor fabricado (solo una posición) no da más que lo autorizado, y un parámetro desconocido se rechaza antes de mirar el registro
    forjado = auditoria_de(supt, "actividad", herencia["A1"], continuar_desde="eyJtIjoiMjAwMC0wMS0wMVQwMDowMDowMCswMDowMCIsImkiOiIwMDAwMDAwMC0wMDAwLTQwMDAtODAwMC0wMDAwMDAwMDAwMDAifQ")
    assert forjado.status_code == 200 and {e["id"] for e in forjado.json()["elementos"]} <= {e["id"] for e in completa}
    assert auditoria_de(supt, "avance", av_u, extra="x").status_code == 400


@pytest.mark.parametrize("cambio", ["trasladado", "desactivado"])
def test_el_supervisor_trasladado_o_desactivado_pierde_la_autorizacion(herencia, cambio):
    _auditar(herencia)
    supt, _ = entrar_con_csrf("supt")
    assert auditoria_de(supt, "actividad", herencia["A1"]).status_code == 200
    with get_owner_engine().begin() as c:
        if cambio == "desactivado":
            c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": herencia["supt"]})
        else:                                                                    # deja de supervisar T y pasa a ser colaborador de U desde hoy
            c.execute(text("update pertenencia set hasta_exclusivo = :h where persona_id = :p and rol = 'supervisor'"), {"h": d(0), "p": herencia["supt"]})
            equipo_u = c.execute(text("select equipo_id from pertenencia where persona_id = :p and rol = 'supervisor'"), {"p": herencia["supu"]}).scalar_one()
            c.execute(text("insert into pertenencia (persona_id, equipo_id, rol, desde) values (:p, :e, 'colaborador', :d)"), {"p": herencia["supt"], "e": equipo_u, "d": d(0)})
    r = auditoria_de(supt, "actividad", herencia["A1"])
    if cambio == "desactivado":
        assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"
    else:
        assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"                                                                  # ya no es supervisor de T
        assert supt.get(f"{API}/equipo/supervision", params={"desde": iso(-5), "hasta": iso(0)}).status_code == 403                                   # y la misma regla en M4-03


def test_la_consulta_sql_de_la_auditoria_coincide_con_la_decision_de_la_politica_y_leer_no_escribe(herencia):
    _auditar(herencia)
    antes = instantanea()
    db = new_session()
    try:
        ahora = datetime.now(timezone.utc)
        with get_owner_engine().connect() as c:
            entradas = c.execute(text("select id, tipo_objeto, objeto_id, propietaria_registro_id, fecha_laboral_registro, tipo_autor from auditoria")).all()
        assert len(entradas) >= 5
        for quien in ("supt", "supu", "luis", "ana", "pablo"):
            consultante = visibilidad.consultante_de(db, herencia[quien], hoy=H, ahora=ahora)
            for tipo, objeto in {(e.tipo_objeto, e.objeto_id) for e in entradas}:
                esperadas = {e.id for e in entradas if e.tipo_objeto == tipo and e.objeto_id == objeto and visibilidad.decidir_lectura_de_auditoria(
                    db, consultante, visibilidad.EntradaDeAuditoria(e.propietaria_registro_id, e.fecha_laboral_registro, e.tipo_autor)).visible}
                obtenidas = {f.id for f in auditoria.listar_entradas(db, consultante, tipo, objeto, None, None, 100)}
                assert obtenidas == esperadas, (quien, tipo)
    finally:
        db.close()
    assert instantanea() == antes
