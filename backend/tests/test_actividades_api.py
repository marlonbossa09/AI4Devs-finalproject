"""T4 — M2-07 (detalle de una actividad propia) y M2-08 (listado de mis actividades), por HTTP sobre
PostgreSQL real.

Criterios: CA-39, CA-40, CA-47, CA-51, CA-52, CA-61, CA-62, CA-70, CA-73 a CA-78, CA-82 a CA-85, CA-88,
CA-119 a CA-121, CA-185, CA-186, CA-191, CA-265 y las reglas T-01 (404 indistinguible), D-10
(paginación) y las convenciones 3.2, 3.3 y 6.1.
"""

import base64
import json
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db import get_owner_engine
from scripts.verificar_datos import estados_actuales_incoherentes
from tests.fabricas import (
    crear_equipo, crear_identidad, crear_persona, crear_pertenencia, escenario_basico, hoy,
)
from tests.utiles_http import API, iniciar_sesion, nuevo_cliente, sesion_iniciada
from tests.utiles_m2 import avanzar, contar, filas, iso, planificar_actividad


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c, desde=hoy() - timedelta(days=400))


@pytest.fixture()
def sesion(esc):
    return sesion_iniciada(esc)


def detalle(cliente, actividad_id):
    return cliente.get(f"{API}/mi/actividades/{actividad_id}")


def listar(cliente, **parametros):
    return cliente.get(f"{API}/mi/actividades", params=parametros)


def otra_persona(identificador="otra.persona"):
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        persona = crear_persona(c, "Otra persona")
        crear_pertenencia(c, persona, crear_equipo(c, org, "Otro equipo"), desde=hoy() - timedelta(days=50))
        crear_identidad(c, persona, identificador, "contraseña-de-prueba-123")
    cliente = nuevo_cliente()
    r = iniciar_sesion(cliente, identificador, "contraseña-de-prueba-123")
    return cliente, r.json()["csrf_token"], persona


def crear_actividades(persona, titulos, *, creada_en=None, estado="Pendiente", fecha=None):
    """Inserta actividades por SQL (con ``creada_en`` explícito si se indica). Devuelve sus ids."""
    ids = []
    with get_owner_engine().begin() as c:
        b = c.execute(text("insert into bitacora (persona_id, fecha_laboral) values (:p, :f) "
                           "on conflict (persona_id, fecha_laboral) do update set persona_id = excluded.persona_id "
                           "returning id"), {"p": persona, "f": fecha or hoy()}).scalar_one()
        for titulo in titulos:
            ids.append(str(c.execute(text(
                "insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen, estado_actual, creada_en) "
                "values (:p, :b, :t, 'planificada', :e, coalesce(:c, now())) returning id"),
                {"p": persona, "b": b, "t": titulo, "e": estado, "c": creada_en}).scalar_one()))
    return ids


# ======================================= M2-07: detalle ===============================================

def test_el_detalle_distingue_la_planificacion_de_la_ejecucion_y_del_estado_actual(sesion):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0), "Preparar informe")
    r = detalle(cliente, actividad)
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"actividad", "planificacion_original", "continuaciones_planificadas", "avances", "estado_actual"}
    assert d["planificacion_original"]["tipo"] == "original" and d["planificacion_original"]["descripcion"] == "Revisar cifras"
    assert d["avances"] == [] and d["continuaciones_planificadas"] == []                    # CA-40: no es un avance
    assert d["estado_actual"] == "Pendiente" and d["actividad"]["estado_actual"] == "Pendiente"   # CA-73
    assert d["actividad"]["origen"] == "planificada" and d["actividad"]["marca_error"] is None


def test_lo_previsto_originalmente_sigue_consultable_tras_actualizar_lo_realizado(sesion):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0))
    antes = detalle(cliente, actividad).json()["planificacion_original"]
    avanzar(cliente, csrf, actividad, iso(0), "En progreso")
    avanzar(cliente, csrf, actividad, iso(0), "Completada")
    despues = detalle(cliente, actividad).json()
    assert despues["planificacion_original"] == antes                                        # CA-39, CA-191
    assert despues["estado_actual"] == "Completada"


def test_los_avances_van_en_el_orden_de_la_secuencia_y_cada_uno_con_su_fecha_y_su_estado(sesion):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0))
    # Se registran en un orden distinto del cronológico laboral
    avanzar(cliente, csrf, actividad, iso(0), "Bloqueada", "Hoy", "Sin acceso")
    avanzar(cliente, csrf, actividad, iso(-3), "Pendiente", "Hace tres días")
    avanzar(cliente, csrf, actividad, iso(-1), "En progreso", "Ayer")
    avanzar(cliente, csrf, actividad, iso(-1), "En progreso", "Ayer, más tarde")
    d = detalle(cliente, actividad).json()
    assert [(a["fecha_laboral"], a["descripcion"]) for a in d["avances"]] == [
        (iso(-3), "Hace tres días"), (iso(-1), "Ayer"), (iso(-1), "Ayer, más tarde"), (iso(0), "Hoy")]
    # CA-74 (la fecha laboral manda sobre el momento de registro) y CA-75 (a igual fecha, el registrado después)
    assert [a["estado"] for a in d["avances"]] == ["Pendiente", "En progreso", "En progreso", "Bloqueada"]  # CA-84
    assert d["estado_actual"] == "Bloqueada"                                                 # CA-77


def test_un_avance_retroactivo_no_sustituye_el_estado_actual(sesion):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0))
    avanzar(cliente, csrf, actividad, iso(-1), "En progreso", "Martes")
    avanzar(cliente, csrf, actividad, iso(-2), "Completada", "Lunes")
    d = detalle(cliente, actividad).json()
    assert d["estado_actual"] == "En progreso"                                               # CA-78
    assert [a["estado"] for a in d["avances"]] == ["Completada", "En progreso"]
    with get_owner_engine().connect() as c:
        assert estados_actuales_incoherentes(c) == []


def test_la_secuencia_de_tres_jornadas_muestra_tres_avances_y_una_sola_actividad(sesion):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0))
    for dias in (-2, -1, 0):
        avanzar(cliente, csrf, actividad, iso(dias), "En progreso", f"Jornada {dias}")
    d = detalle(cliente, actividad).json()
    assert len(d["avances"]) == 3 and {a["fecha_laboral"] for a in d["avances"]} == {iso(-2), iso(-1), iso(0)}   # CA-83
    assert contar("actividad") == 1 and d["actividad"]["titulo"] == "Preparar informe"       # CA-82, CA-265


def test_el_motivo_de_un_bloqueo_anterior_sigue_constando_en_el_historial(sesion):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0))
    avanzar(cliente, csrf, actividad, iso(-1), "Bloqueada", "Detenida", "Falta el acceso")
    avanzar(cliente, csrf, actividad, iso(0), "En progreso", "Ya hay acceso")
    avances = detalle(cliente, actividad).json()["avances"]
    assert [(a["estado"], a["motivo_bloqueo"]) for a in avances] == [("Bloqueada", "Falta el acceso"), ("En progreso", None)]  # CA-51, CA-52


def test_se_muestran_la_fecha_laboral_la_real_de_registro_y_la_de_modificacion(sesion):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(-4))                                 # creada hoy para una jornada pasada
    avanzar(cliente, csrf, actividad, iso(-4), "En progreso", "Retroactivo")
    d = detalle(cliente, actividad).json()
    assert d["actividad"]["fecha_laboral_origen"] == iso(-4)
    assert d["actividad"]["creada_en"].startswith(iso(0)) or d["actividad"]["creada_en"][:10] >= iso(-1)   # momento real, UTC
    assert d["actividad"]["creada_en"] != d["actividad"]["fecha_laboral_origen"]            # CA-61: se muestran por separado
    avance = d["avances"][0]
    assert avance["fecha_laboral"] == iso(-4) and avance["registrado_en"] and avance["modificado_en"]   # CA-62, CA-70
    assert avance["registrado_en"][:10] != avance["fecha_laboral"]
    assert d["planificacion_original"]["fecha_laboral"] == iso(-4) and d["planificacion_original"]["registrada_en"]


def test_las_continuaciones_planificadas_se_listan_aparte_y_no_forman_parte_de_la_secuencia(sesion, esc):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0))
    with get_owner_engine().begin() as c:     # M2-04 todavía no existe: se prepara por SQL
        b = c.execute(text("insert into bitacora (persona_id, fecha_laboral) values (:p, :f) returning id"),
                      {"p": esc.persona, "f": hoy() + timedelta(days=3)}).scalar_one()
        c.execute(text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) "
                       "values (:a, :b, 'continuacion', 'Seguir el viernes')"), {"a": actividad, "b": b})
    d = detalle(cliente, actividad).json()
    assert [(p["tipo"], p["fecha_laboral"], p["descripcion"]) for p in d["continuaciones_planificadas"]] == [
        ("continuacion", iso(3), "Seguir el viernes")]
    assert d["avances"] == [] and d["estado_actual"] == "Pendiente"                          # CA-185, CA-186
    assert d["planificacion_original"]["tipo"] == "original"


def test_una_actividad_no_planificada_no_tiene_planificacion_original(sesion, esc):
    cliente, _ = sesion
    [actividad] = crear_actividades(esc.persona, ["Imprevisto"])
    with get_owner_engine().begin() as c:
        c.execute(text("update actividad set origen = 'no_planificada' where id = :a"), {"a": actividad})
    d = detalle(cliente, actividad).json()
    assert d["actividad"]["origen"] == "no_planificada" and d["planificacion_original"] is None


def test_una_actividad_marcada_por_error_sigue_siendo_consultable(sesion, esc):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0))
    avanzar(cliente, csrf, actividad, iso(0), "En progreso")
    with get_owner_engine().begin() as c:     # la marca es M3-05: se prepara por SQL
        c.execute(text("update actividad set registrada_por_error = true, motivo_error = 'duplicada', "
                       "marcada_por = propietaria_id, marcada_en = now()"))
    d = detalle(cliente, actividad).json()
    assert d["actividad"]["marca_error"]["motivo"] == "duplicada" and d["actividad"]["marca_error"]["marcada_en"]  # CA-120
    assert d["estado_actual"] == "En progreso" and contar("actividad") == 1                  # CA-121: no se ha borrado


def test_consultar_el_detalle_no_modifica_nada(sesion, esc):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(-2))
    avanzar(cliente, csrf, actividad, iso(-2), "En progreso")
    antes = (contar("avance"), contar("actividad"), contar("bitacora"), contar("auditoria"), contar("clave_idempotencia"),
             filas("select modificada_en from bitacora order by fecha_laboral"))
    for _ in range(3):
        detalle(cliente, actividad)
    assert antes == (contar("avance"), contar("actividad"), contar("bitacora"), contar("auditoria"),
                     contar("clave_idempotencia"), filas("select modificada_en from bitacora order by fecha_laboral"))


# ---- autorización y visibilidad (T-01, convenciones 3.2) ----

def test_la_actividad_de_otra_persona_y_una_inexistente_tienen_la_misma_respuesta(sesion):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0), "Confidencial: despido de Pérez")
    ajeno, _, _ = otra_persona()
    ajena = detalle(ajeno, actividad)
    inexistente = detalle(ajeno, str(uuid.uuid4()))
    assert ajena.status_code == inexistente.status_code == 404                               # CA-88
    assert ajena.json() == inexistente.json() and ajena.json()["codigo"] == "RECURSO_NO_DISPONIBLE"
    assert ajena.json()["detalles"] == [] and "Pérez" not in ajena.text and "Confidencial" not in ajena.text


def test_un_identificador_mal_formado_es_una_solicitud_invalida_y_no_consulta_el_recurso(sesion):
    cliente, _ = sesion
    for valor in ("no-es-un-uuid", "123", "00000000-0000-0000-0000-00000000000z"):
        r = detalle(cliente, valor)
        assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA", valor


def test_sin_sesion_no_se_muestra_ninguna_actividad(sesion):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0))
    r = detalle(nuevo_cliente(), actividad)
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"
    r = listar(nuevo_cliente())
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"


def test_con_el_acceso_desactivado_no_se_consulta_nada(sesion, esc):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0))
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": esc.persona})
    for r in (detalle(cliente, actividad), listar(cliente)):
        assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"


def test_el_detalle_nunca_devuelve_la_actividad_de_otra_persona_aunque_comparta_titulo(sesion):
    cliente, csrf = sesion
    propia = planificar_actividad(cliente, csrf, iso(0), "Informe mensual")
    ajeno, csrf_ajeno, _ = otra_persona()
    otra = planificar_actividad(ajeno, csrf_ajeno, iso(0), "Informe mensual")
    assert propia != otra                                                                    # CA-85
    assert detalle(cliente, propia).json()["actividad"]["id"] == propia
    assert detalle(ajeno, propia).status_code == 404 and detalle(cliente, otra).status_code == 404


# ======================================= M2-08: listado ===============================================

def test_el_listado_devuelve_mis_actividades_con_los_campos_del_contrato(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0), "Preparar informe")
    r = listar(cliente)
    assert r.status_code == 200
    cuerpo = r.json()
    assert set(cuerpo) == {"elementos", "siguiente"} and cuerpo["siguiente"] is None
    assert cuerpo["elementos"] == [{"id": a, "titulo": "Preparar informe", "origen": "planificada", "estado_actual": "Pendiente"}]


def test_el_listado_solo_incluye_actividades_propias(sesion):
    cliente, csrf = sesion
    propia = planificar_actividad(cliente, csrf, iso(0), "Mía")
    ajeno, csrf_ajeno, _ = otra_persona()
    planificar_actividad(ajeno, csrf_ajeno, iso(0), "De otra persona")
    assert [e["id"] for e in listar(cliente).json()["elementos"]] == [propia]                # CA-88
    assert [e["titulo"] for e in listar(ajeno).json()["elementos"]] == ["De otra persona"]


def test_una_actividad_con_avances_en_varias_jornadas_cuenta_una_sola_vez(sesion):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0))
    for dias in (-2, -1, 0):
        avanzar(cliente, csrf, actividad, iso(dias), "En progreso")
    elementos = listar(cliente).json()["elementos"]
    assert [e["id"] for e in elementos] == [actividad]                                       # CA-82


def test_dos_actividades_con_el_mismo_titulo_siguen_siendo_distintas(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0), "Informe")
    b = planificar_actividad(cliente, csrf, iso(0), "Informe")
    c = planificar_actividad(cliente, csrf, iso(0), "informe ")
    assert {e["id"] for e in listar(cliente).json()["elementos"]} == {a, b, c}               # CA-85


def test_las_actividades_marcadas_por_error_no_aparecen_en_el_listado(sesion, esc):
    cliente, csrf = sesion
    visible = planificar_actividad(cliente, csrf, iso(0), "Visible")
    oculta = planificar_actividad(cliente, csrf, iso(0), "Por error")
    with get_owner_engine().begin() as c:
        c.execute(text("update actividad set registrada_por_error = true, motivo_error = 'x', "
                       "marcada_por = propietaria_id, marcada_en = now() where id = :a"), {"a": oculta})
    assert [e["id"] for e in listar(cliente).json()["elementos"]] == [visible]               # CA-119
    assert detalle(cliente, oculta).status_code == 200                                       # pero sigue consultable (CA-120)
    assert [e["id"] for e in listar(cliente, estado="Pendiente").json()["elementos"]] == [visible]


def test_el_filtro_por_estado_usa_el_estado_actual(sesion):
    cliente, csrf = sesion
    pendiente = planificar_actividad(cliente, csrf, iso(0), "Pendiente")
    progreso = planificar_actividad(cliente, csrf, iso(0), "En progreso")
    bloqueada = planificar_actividad(cliente, csrf, iso(0), "Bloqueada")
    hecha = planificar_actividad(cliente, csrf, iso(0), "Hecha")
    avanzar(cliente, csrf, progreso, iso(0), "En progreso")
    avanzar(cliente, csrf, bloqueada, iso(0), "Bloqueada", motivo_bloqueo="Falta acceso")
    avanzar(cliente, csrf, hecha, iso(0), "En progreso")
    avanzar(cliente, csrf, hecha, iso(0), "Completada")

    def ids(**p):
        return {e["id"] for e in listar(cliente, **p).json()["elementos"]}

    assert ids(estado="Pendiente") == {pendiente}
    assert ids(estado="En progreso") == {progreso}
    assert ids(estado="Bloqueada") == {bloqueada}
    assert ids(estado="Completada") == {hecha}                                               # sobre el estado ACTUAL
    assert ids(estado=["Pendiente", "Bloqueada"]) == {pendiente, bloqueada}                  # uno o varios
    assert ids() == {pendiente, progreso, bloqueada, hecha}
    assert ids(estado=["Pendiente", "Pendiente"]) == {pendiente}                             # repetidos no cambian nada


def test_un_filtro_sin_resultados_es_una_lista_vacia_y_no_un_error(sesion):
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(0))
    r = listar(cliente, estado="Completada")
    assert r.status_code == 200 and r.json() == {"elementos": [], "siguiente": None}


@pytest.mark.parametrize("parametros", [
    {"estado": "Terminada"}, {"estado": "pendiente"}, {"estado": ""}, {"estado": ["Pendiente", "Otra"]},
    {"q": "informe"}, {"buscar": "x"}, {"titulo": "Informe"}, {"persona_id": "x"}, {"orden": "asc"},
    {"incluir_error": "true"}, {"pagina": "2"},
])
def test_los_filtros_y_parametros_no_soportados_se_rechazan(sesion, parametros):
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(0))
    r = listar(cliente, **parametros)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA", parametros   # no hay búsqueda por texto


# ---- paginación ----

def test_el_orden_es_de_la_mas_reciente_a_la_mas_antigua_con_el_identificador_como_desempate(sesion, esc):
    cliente, _ = sesion
    mismo_momento = hoy() - timedelta(days=1)
    empatadas = crear_actividades(esc.persona, [f"Empate {i}" for i in range(4)], creada_en=f"{mismo_momento}T10:00:00+00:00")
    reciente = crear_actividades(esc.persona, ["Reciente"], creada_en=f"{hoy()}T09:00:00+00:00")
    antigua = crear_actividades(esc.persona, ["Antigua"], creada_en=f"{hoy() - timedelta(days=9)}T09:00:00+00:00")
    ids = [e["id"] for e in listar(cliente).json()["elementos"]]
    assert ids == reciente + sorted(empatadas, reverse=True) + antigua
    assert ids == [e["id"] for e in listar(cliente).json()["elementos"]]                     # determinista


def test_la_paginacion_no_repite_ni_omite_elementos(sesion, esc):
    cliente, _ = sesion
    base = hoy() - timedelta(days=2)
    # Varias con el mismo instante, para que el desempate por identificador sea imprescindible
    ids = crear_actividades(esc.persona, [f"A{i}" for i in range(11)], creada_en=f"{base}T08:00:00+00:00")
    ids += crear_actividades(esc.persona, [f"B{i}" for i in range(6)], creada_en=f"{base}T09:00:00+00:00")
    esperado = [e["id"] for e in listar(cliente, limite=100).json()["elementos"]]
    assert len(esperado) == 17 and set(esperado) == set(ids)
    for tamano in (1, 2, 3, 5, 16, 17, 18):
        visto, cursor = [], None
        for _ in range(40):
            parametros = {"limite": tamano, **({"continuar_desde": cursor} if cursor else {})}
            cuerpo = listar(cliente, **parametros).json()
            assert 1 <= len(cuerpo["elementos"]) <= tamano
            visto += [e["id"] for e in cuerpo["elementos"]]
            cursor = cuerpo["siguiente"]
            if cursor is None:
                break
        assert visto == esperado, tamano                                                     # ni repite ni omite, mismo orden


def test_siguiente_es_nulo_en_la_ultima_pagina_y_tambien_cuando_justo_cabe_todo(sesion, esc):
    cliente, _ = sesion
    crear_actividades(esc.persona, ["a", "b", "c"])
    assert listar(cliente, limite=3).json()["siguiente"] is None
    cuerpo = listar(cliente, limite=2).json()
    assert len(cuerpo["elementos"]) == 2 and cuerpo["siguiente"] is not None
    ultimo = listar(cliente, limite=2, continuar_desde=cuerpo["siguiente"]).json()
    assert len(ultimo["elementos"]) == 1 and ultimo["siguiente"] is None


def test_el_filtro_y_la_paginacion_se_combinan(sesion, esc):
    cliente, _ = sesion
    pendientes = crear_actividades(esc.persona, [f"P{i}" for i in range(5)], estado="Pendiente")
    crear_actividades(esc.persona, [f"C{i}" for i in range(4)], estado="Completada")
    visto, cursor = [], None
    while True:
        cuerpo = listar(cliente, estado="Pendiente", limite=2, **({"continuar_desde": cursor} if cursor else {})).json()
        visto += [e["id"] for e in cuerpo["elementos"]]
        cursor = cuerpo["siguiente"]
        if cursor is None:
            break
    assert sorted(visto) == sorted(pendientes) and len(visto) == 5


def test_el_valor_por_defecto_y_el_maximo_de_limite_son_configurables(sesion, esc):
    cliente, _ = sesion
    ajustes = get_settings()
    crear_actividades(esc.persona, [f"X{i}" for i in range(ajustes.pagination_default_limit + 1)])
    primera = listar(cliente).json()
    assert len(primera["elementos"]) == ajustes.pagination_default_limit and primera["siguiente"] is not None
    assert listar(cliente, limite=ajustes.pagination_max_limit).status_code == 200


@pytest.mark.parametrize("limite", ["0", "-1", "abc", "1.5", "", " 5", "٣", "999999999999", "101", "1e2"])
def test_un_limite_invalido_o_superior_al_maximo_se_rechaza_con_el_maximo_en_los_detalles(sesion, limite):
    cliente, _ = sesion
    r = listar(cliente, limite=limite)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA", limite
    assert r.json()["detalles"] == [{"campo": "limite", "maximo": get_settings().pagination_max_limit}]


def _cursor(contenido) -> str:
    return base64.urlsafe_b64encode(json.dumps(contenido).encode()).decode().rstrip("=")


@pytest.mark.parametrize("cursor", [
    "basura", "!!!", "e30", _cursor({}), _cursor({"c": "no-es-fecha", "i": str(uuid.uuid4())}),
    _cursor({"c": "2026-01-01T00:00:00", "i": str(uuid.uuid4())}),           # sin zona horaria
    _cursor({"c": "2026-01-01T00:00:00+00:00", "i": "no-es-uuid"}), _cursor([1, 2]), _cursor("texto"), "a" * 5000,
])
def test_un_cursor_invalido_se_rechaza(sesion, cursor):
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(0))
    r = listar(cliente, continuar_desde=cursor)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA", cursor[:30]
    assert r.json()["detalles"][0]["campo"] == "continuar_desde"


def test_el_cursor_es_opaco_y_no_revela_datos_de_otras_personas(sesion, esc):
    cliente, _ = sesion
    crear_actividades(esc.persona, ["a", "b", "c"])
    cursor = listar(cliente, limite=1).json()["siguiente"]
    assert cursor and "=" not in cursor and not any(c in cursor for c in "+/ ")             # seguro en una URL


def test_las_actividades_de_otras_personas_no_cuentan_ni_cambian_siguiente(sesion, esc):
    """El filtro de autorización se aplica antes de paginar (convenciones 3.3 y 6.1)."""
    cliente, _ = sesion
    _, _, otra = otra_persona()
    propias = crear_actividades(esc.persona, ["a", "b", "c"], creada_en=f"{hoy() - timedelta(days=3)}T08:00:00+00:00")
    crear_actividades(otra, [f"ajena {i}" for i in range(10)], creada_en=f"{hoy()}T08:00:00+00:00")  # más recientes
    cuerpo = listar(cliente, limite=3).json()
    assert [e["id"] for e in cuerpo["elementos"]] == sorted(propias, reverse=True)
    assert cuerpo["siguiente"] is None                                                       # nada de otras personas


def test_usar_el_cursor_de_otra_persona_no_expone_nada_ajeno(sesion, esc):
    cliente, _ = sesion
    ajeno, _, otra = otra_persona()
    propias = crear_actividades(esc.persona, ["p1", "p2"], creada_en=f"{hoy() - timedelta(days=2)}T08:00:00+00:00")
    crear_actividades(otra, ["a1", "a2", "a3"], creada_en=f"{hoy()}T08:00:00+00:00")
    cursor_ajeno = listar(ajeno, limite=1).json()["siguiente"]
    ids = [e["id"] for e in listar(cliente, continuar_desde=cursor_ajeno).json()["elementos"]]
    assert set(ids) <= set(propias)                                                          # solo mis actividades


def test_actividades_creadas_entre_paginas_no_provocan_repetidos_ni_omisiones(sesion, esc):
    cliente, _ = sesion
    originales = crear_actividades(esc.persona, [f"o{i}" for i in range(6)], creada_en=f"{hoy() - timedelta(days=1)}T08:00:00+00:00")
    primera = listar(cliente, limite=2).json()
    crear_actividades(esc.persona, ["nueva 1", "nueva 2"])                                   # llegan a la cabecera
    visto = [e["id"] for e in primera["elementos"]]
    cursor = primera["siguiente"]
    while cursor:
        cuerpo = listar(cliente, limite=2, continuar_desde=cursor).json()
        visto += [e["id"] for e in cuerpo["elementos"]]
        cursor = cuerpo["siguiente"]
    assert sorted(visto) == sorted(originales) and len(visto) == len(set(visto))             # sin repetidos ni omisiones


def test_listar_no_modifica_nada(sesion, esc):
    cliente, csrf = sesion
    actividad = planificar_actividad(cliente, csrf, iso(0))
    avanzar(cliente, csrf, actividad, iso(0), "En progreso")
    antes = (contar("avance"), contar("actividad"), contar("bitacora"), contar("auditoria"), contar("clave_idempotencia"))
    listar(cliente)
    listar(cliente, estado="Completada")
    assert antes == (contar("avance"), contar("actividad"), contar("bitacora"), contar("auditoria"), contar("clave_idempotencia"))
