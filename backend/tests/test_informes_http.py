"""M5-T4 — capa HTTP de los informes (``POST /api/v1/informes/individuales`` y ``/consolidados``) sobre la APLICACIÓN PRINCIPAL (``crear_app()``, con la ruta registrada en ``app/main.py``), con sesión, CSRF y
PostgreSQL REALES y el generador SIMULADO. Sin ningún servicio externo. Destructivas solo sobre ``smartwork_test``. Datos siempre ficticios.

Comprueba la respuesta pública campo por campo (esquema cerrado, referencias opacas y locales, proyecciones neutrales, bloqueos agrupados por actividad, narrativa como lista de secciones con solo ``texto``, cifras idénticas a
las deterministas), la ausencia de datos sensibles, la autorización (403 y 404 uniforme), los límites confirmados (31 días y 400 hechos por solicitud), la generación desactivada por defecto, el simulado solo si se pide,
el informe sin datos sin generador, los fallos del generador con su indicación coherente de reintento, y la ausencia de efectos persistentes. El recorrido con sockets reales está en ``test_informes_http_real``.
"""

import dataclasses
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.compartido.visibilidad import consultante_de
from app.config import Settings, get_settings
from app.db import get_owner_engine
from app.main import crear_app
from app.modulos.informes.consolidado import preparar_informe_consolidado
from app.modulos.informes.generador_simulado import GeneradorSimulado
from app.modulos.informes.individual import preparar_informe_individual
from app.modulos.informes.presentacion import DECLARACION_DE_BASE
from app.modulos.informes.router import obtener_generador
from tests.test_informe_consolidado import CLAVE, H, d, db, mundo, mundo2  # noqa: F401  (escenario de M5-T1 y M5-T2)
from tests.test_informe_individual import ORDEN_MALICIOSA, _actividad, _bitacora
from tests.utiles_http import API, ORIGEN, cabeceras, iniciar_sesion

INDIVIDUALES, CONSOLIDADOS = f"{API}/informes/individuales", f"{API}/informes/consolidados"
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
MOMENTO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z")
SEIS_METRICAS = {"avances", "jornadas_con_registros", "actividades_con_registros", "actividades_por_origen", "actividades_con_bloqueo", "actividades_por_estado_al_corte"}


def cuerpo(desde: int, hasta: int, **extra):
    return {"desde": d(desde).isoformat(), "hasta": d(hasta).isoformat(), **extra}


def entrar(nombre: str, *, habilitado=False, generador="ninguno", generador_objeto=None, **ajustes):
    """Cliente con la sesión de ``nombre`` sobre la aplicación principal. Los ajustes sustituyen los de configuración SOLO para las rutas de informes."""
    app = crear_app()
    settings = get_settings().model_copy(update={"informe_habilitado": habilitado, "informe_generador": generador, **ajustes})
    app.dependency_overrides[get_settings] = lambda: settings
    if generador_objeto is not None:
        app.dependency_overrides[obtener_generador] = lambda: generador_objeto
    cliente = TestClient(app, base_url=ORIGEN, raise_server_exceptions=False)
    r = iniciar_sesion(cliente, f"acceso-{nombre}-privado", CLAVE)
    assert r.status_code == 201, r.text
    return cliente, r.json()["csrf_token"]


def enviar(cliente_y_csrf, ruta, datos):
    cliente, csrf = cliente_y_csrf
    return cliente.post(ruta, json=datos, headers=cabeceras(csrf))


def reintento(r, posible: bool) -> bool:
    return r.json()["detalles"] == [{"campo": "reintento", "reintento": posible, "motivo": "posible" if posible else "no_aplicable"}]


# ------------------------------------------------------------------------------------------------------ comprobaciones del esquema público

def bloque_coherente(bloque: dict):
    """Un bloque (el informe individual, o una persona del consolidado): referencias opacas y locales y colecciones consistentes entre sí."""
    assert set(bloque) >= {"agregaciones", "actividades", "hechos", "bloqueos", "narrativa"}
    refs = [a["ref"] for a in bloque["actividades"]]
    assert all(re.fullmatch(r"a\d+", r) for r in refs) and len(set(refs)) == len(refs)
    for a in bloque["actividades"]:
        assert set(a) == ({"ref", "forma", "titulo", "origen"} if a["forma"] == "completa" else {"ref", "forma", "referencia_neutral"})
        assert a["origen"] in ("planificada", "no_planificada") if a["forma"] == "completa" else a["referencia_neutral"] == "Actividad en continuidad"
    for h in bloque["hechos"]:
        assert set(h) == {"fecha_laboral", "actividad_ref", "estado", "descripcion"} | ({"motivo_bloqueo"} if h["estado"] == "Bloqueada" else set())
        assert h["actividad_ref"] in refs and h["estado"] in ("Pendiente", "En progreso", "Bloqueada", "Completada")
    esperados: dict[str, list] = {}
    for h in bloque["hechos"]:
        if h["estado"] == "Bloqueada":
            esperados.setdefault(h["actividad_ref"], []).append({"fecha_laboral": h["fecha_laboral"], "motivo": h["motivo_bloqueo"]})
    assert bloque["bloqueos"] == [{"actividad_ref": ref, "ocurrencias": oc} for ref, oc in esperados.items()]                     # P-3: agrupados por actividad, sin motivos que no estén en los hechos
    if bloque["agregaciones"] is not None:
        assert set(bloque["agregaciones"]) == SEIS_METRICAS
    if bloque["narrativa"] is not None:
        assert bloque["narrativa"] and all(set(s) == {"texto"} and isinstance(s["texto"], str) for s in bloque["narrativa"])     # P-11: solo texto, sin referencias


def individual_coherente(j: dict):
    assert set(j) == {"tipo", "periodo", "generado_en", "base", "sin_datos", "persona", "agregaciones", "actividades", "hechos", "bloqueos", "narrativa"}
    assert (j["tipo"], j["base"], set(j["periodo"]), set(j["persona"])) == ("individual", DECLARACION_DE_BASE, {"desde", "hasta"}, {"id", "nombre"})
    assert MOMENTO.fullmatch(j["generado_en"])
    assert abs(datetime.now(timezone.utc) - datetime.fromisoformat(j["generado_en"].replace("Z", "+00:00"))) < timedelta(minutes=2)
    bloque_coherente(j)


def consolidado_coherente(j: dict):
    assert set(j) == {"tipo", "periodo", "generado_en", "base", "sin_datos", "personas", "agregaciones_del_equipo"}                # sin colecciones de actividades, hechos ni bloqueos al nivel del informe
    assert (j["tipo"], j["base"]) == ("consolidado", DECLARACION_DE_BASE) and MOMENTO.fullmatch(j["generado_en"])
    for p in j["personas"]:
        assert set(p) == {"persona", "agregaciones", "actividades", "hechos", "bloqueos", "narrativa"} and set(p["persona"]) == {"id", "nombre"}
        bloque_coherente(p)
    if j["agregaciones_del_equipo"] is not None:
        assert set(j["agregaciones_del_equipo"]) == SEIS_METRICAS


# ------------------------------------------------------------------------------------------------------ 200: individual y consolidado

def test_el_informe_individual_propio_se_devuelve_con_el_esquema_publico_cerrado_y_las_cifras_deterministas(db, mundo2):
    g = GeneradorSimulado()
    r = enviar(entrar("ana", habilitado=True, generador_objeto=g), INDIVIDUALES, cuerpo(-10, 0))
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    j = r.json()
    individual_coherente(j)
    assert (g.llamadas, j["sin_datos"], j["persona"]) == (1, False, {"id": str(mundo2["ana"]), "nombre": "ana"})
    assert j["periodo"] == {"desde": d(-10).isoformat(), "hasta": d(0).isoformat()}
    assert j["actividades"] == [{"ref": "a1", "forma": "completa", "titulo": "Informe de Ana", "origen": "planificada"},
                                {"ref": "a2", "forma": "completa", "titulo": "Tarea imprevista", "origen": "no_planificada"}]
    assert [(h["fecha_laboral"], h["actividad_ref"], h["estado"]) for h in j["hechos"]] == [(d(-6).isoformat(), "a1", "En progreso"), (d(-5).isoformat(), "a1", "Bloqueada"),
                                                                                           (d(-5).isoformat(), "a2", "Completada"), (d(-4).isoformat(), "a1", "En progreso")]
    assert j["hechos"][1]["motivo_bloqueo"] == "falta acceso al servidor" and j["hechos"][3]["descripcion"] == ORDEN_MALICIOSA        # el texto libre viaja como dato, tal cual
    assert j["bloqueos"] == [{"actividad_ref": "a1", "ocurrencias": [{"fecha_laboral": d(-5).isoformat(), "motivo": "falta acceso al servidor"}]}]      # un bloqueo histórico, no un estado actual
    assert j["narrativa"] == [{"texto": "ana registró 4 avances en 3 jornadas, sobre 2 actividades."}, {"texto": f"ana tuvo bloqueos registrados el {d(-5).isoformat()}."}]
    directo = preparar_informe_individual(db, consultante_de(db, mundo2["ana"], hoy=H), None, d(-10), d(0))                            # las cifras son EXACTAMENTE las deterministas
    assert j["agregaciones"] == dataclasses.asdict(directo.agregaciones) and j["agregaciones"]["avances"] == 4


def test_el_supervisor_obtiene_el_informe_de_su_persona_y_la_actividad_heredada_sale_neutral_sin_datos_protegidos(db, mundo2):
    def informe(quien, persona):
        r = enviar(entrar(quien, habilitado=True, generador_objeto=GeneradorSimulado()), INDIVIDUALES, cuerpo(-30, 0, persona_id=str(mundo2[persona])))
        assert r.status_code == 200, r.text
        individual_coherente(r.json())
        return r.json()

    de_ana = informe("supt", "ana")
    assert de_ana["persona"]["nombre"] == "ana" and de_ana["agregaciones"]["avances"] == 4
    t = informe("supt", "pablo")                                                                  # supervisor del equipo anterior: solo lo de su equipo
    assert [h["fecha_laboral"] for h in t["hechos"]] == [d(-30).isoformat()] * 2 and t["actividades"][0]["titulo"] == "Tarea secreta del equipo T"
    assert t["bloqueos"][0]["ocurrencias"][0]["motivo"] == "motivo-reservado-del-equipo-T" and t["agregaciones"]["actividades_por_estado_al_corte"]["estado_no_disponible"] == 1
    u = informe("supu", "pablo")                                                                  # supervisor del equipo nuevo: actividad neutral y nada ajeno
    assert u["actividades"][0] == {"ref": "a1", "forma": "neutral", "referencia_neutral": "Actividad en continuidad"} and u["actividades"][1]["titulo"] == "Tarea nueva en U"
    assert u["bloqueos"] == [] and u["agregaciones"]["actividades_por_origen"]["origen_no_disponible"] == 1
    assert u["agregaciones"]["actividades_por_estado_al_corte"] == {"pendiente": 1, "en_progreso": 1, "bloqueada": 0, "completada": 0, "estado_no_disponible": 0}
    for protegido in ("Tarea secreta del equipo T", "Avance interno del equipo T", "Bloqueo en el equipo T", "motivo-reservado-del-equipo-T", "resumen reservado del equipo T", "Equipo T-reservado"):
        assert protegido not in json.dumps(u, ensure_ascii=False)


def test_el_consolidado_se_devuelve_por_persona_con_la_seccion_de_equipo_determinista_y_sin_tocar_las_cifras(db, mundo2):
    g = GeneradorSimulado()
    r = enviar(entrar("supt", habilitado=True, generador_objeto=g), CONSOLIDADOS, cuerpo(-30, 0))                      # 31 días con ambos extremos: el máximo
    assert r.status_code == 200
    j = r.json()
    consolidado_coherente(j)
    assert [p["persona"]["nombre"] for p in j["personas"]] == ["ana", "beto", "gina", "pablo", "supt"] and (g.llamadas, j["sin_datos"]) == (5, False)
    assert all(p["narrativa"] and p["narrativa"][0]["texto"].startswith(p["persona"]["nombre"]) for p in j["personas"])             # una narrativa por persona
    assert sum(len(p["hechos"]) for p in j["personas"]) == 13
    assert len({a["ref"] for p in j["personas"] for a in p["actividades"]}) == sum(len(p["actividades"]) for p in j["personas"])        # referencias únicas en todo el informe
    directo = preparar_informe_consolidado(db, consultante_de(db, mundo2["supt"], hoy=H), None, d(-30), d(0))
    assert j["agregaciones_del_equipo"] == dataclasses.asdict(directo.agregaciones_del_equipo)
    assert [p["agregaciones"] for p in j["personas"]] == [dataclasses.asdict(p.agregaciones) for p in directo.personas]
    assert j["agregaciones_del_equipo"]["avances"] == sum(p["agregaciones"]["avances"] for p in j["personas"]) == 13               # el equipo es la suma, no una copia
    texto = json.dumps(j, ensure_ascii=False)
    assert "ranking" not in texto and "puntuacion" not in texto and "%" not in texto
    equipo = db.execute(text("select equipo_id from pertenencia where persona_id = :p and hasta_exclusivo is null"), {"p": mundo2["supt"]}).scalar_one()
    assert enviar(entrar("supt", habilitado=True, generador_objeto=GeneradorSimulado()), CONSOLIDADOS, cuerpo(-30, 0, equipo_id=str(equipo))).json()["agregaciones_del_equipo"] == j["agregaciones_del_equipo"]


def test_un_informe_sin_datos_lleva_la_base_y_no_ejecuta_el_generador_este_o_no_habilitado(db, mundo2):
    for habilitado in (False, True):
        g = GeneradorSimulado("error_inesperado")                                                                          # si se invocase, fallaría
        r = enviar(entrar("ana", habilitado=habilitado, generador_objeto=g), INDIVIDUALES, cuerpo(-3, 2))
        j = r.json()
        assert r.status_code == 200 and g.llamadas == 0
        individual_coherente(j)
        assert (j["sin_datos"], j["agregaciones"], j["actividades"], j["hechos"], j["bloqueos"], j["narrativa"], j["base"]) == (True, None, [], [], [], None, DECLARACION_DE_BASE)
        assert j["persona"] == {"id": str(mundo2["ana"]), "nombre": "ana"}
    g = GeneradorSimulado("error_inesperado")
    j = enviar(entrar("supt", generador_objeto=g), CONSOLIDADOS, cuerpo(1, 10)).json()
    consolidado_coherente(j)
    assert (j["sin_datos"], j["personas"], j["agregaciones_del_equipo"], j["base"], g.llamadas) == (True, [], None, DECLARACION_DE_BASE, 0)


def test_la_respuesta_no_lleva_identificadores_internos_ni_datos_de_acceso_ni_de_equipo(db, mundo2):
    ids_de_actividades = {str(f[0]) for f in db.execute(text("select id from actividad")).all()}
    ids_de_personas = {str(v) for v in mundo2.values() if isinstance(v, uuid.UUID)}
    for quien, ruta, datos in (("ana", INDIVIDUALES, cuerpo(-10, 0)), ("supt", CONSOLIDADOS, cuerpo(-30, 0)), ("supu", CONSOLIDADOS, cuerpo(-30, 0)),
                               ("supt", INDIVIDUALES, cuerpo(-30, 0, persona_id=str(mundo2["pablo"])))):
        r = enviar(entrar(quien, habilitado=True, generador_objeto=GeneradorSimulado()), ruta, datos)
        assert r.status_code == 200
        encontrados = set(UUID.findall(r.text))
        assert encontrados and encontrados <= ids_de_personas and not encontrados & ids_de_actividades          # solo identificadores de las personas del informe: ninguno de actividad ni de la base de datos
        for sensible in ("acceso-", "-privado", CLAVE, "argon2", "@", "Equipo T-reservado", "Equipo U-reservado", "Equipo W-reservado", "resumen reservado", "hash_contrasena", "token"):
            assert sensible not in r.text, (quien, sensible)


def _claves_de(valor, acumulado: set) -> set:
    if isinstance(valor, dict):
        for k, v in valor.items():
            acumulado.add(k)
            _claves_de(v, acumulado)
    elif isinstance(valor, list):
        for v in valor:
            _claves_de(v, acumulado)
    return acumulado


def test_el_nombre_y_el_identificador_de_la_persona_no_llegan_al_generador_y_el_consolidado_no_expone_titulos_ni_motivos_protegidos(db, mundo2):
    """P-13: ``persona`` (``id`` y ``nombre``) solo está en la RESPUESTA autorizada. Al generador solo viaja el alias; las referencias de la respuesta (``a1``…) no son identificadores de la base de datos."""
    protegidos = ("Tarea secreta del equipo T", "Avance interno del equipo T", "Bloqueo en el equipo T", "motivo-reservado-del-equipo-T", "resumen reservado del equipo T")
    ids_de_la_base = {str(f[0]) for tabla in ("actividad", "avance", "bitacora", "persona", "equipo") for f in db.execute(text(f"select id from {tabla}")).all()}
    for quien, ruta, datos in (("ana", INDIVIDUALES, cuerpo(-10, 0)), ("supt", CONSOLIDADOS, cuerpo(-30, 0)), ("supu", CONSOLIDADOS, cuerpo(-30, 0))):
        g = GeneradorSimulado()
        r = enviar(entrar(quien, habilitado=True, generador_objeto=g), ruta, datos)
        assert r.status_code == 200 and g.llamadas >= 1
        for recibido in g.recibido:
            assert recibido["persona"] == {"alias": "Persona 1"} and not {"id", "nombre", "persona_id"} & _claves_de(recibido, set())      # sin nombre ni identificador públicos
            assert not UUID.search(json.dumps(recibido))
        j = r.json()
        bloques = j["personas"] if "personas" in j else [j]
        referencias = [x["ref"] for b in bloques for x in b["actividades"]] + [x["actividad_ref"] for b in bloques for x in b["hechos"]] + [x["actividad_ref"] for b in bloques for x in b["bloqueos"]]
        assert referencias and not set(referencias) & ids_de_la_base and all(re.fullmatch(r"a\d+", x) for x in referencias)          # opacas, locales y no identificadores reales
    j = enviar(entrar("supu", habilitado=True, generador_objeto=GeneradorSimulado()), CONSOLIDADOS, cuerpo(-30, 0)).json()
    assert [p["persona"]["nombre"] for p in j["personas"]] == ["celia", "pablo"]                         # solo personas de la población autorizada (el avance de supw en U es de hace 50 días: fuera del período)
    assert not any(x in json.dumps(j, ensure_ascii=False) for x in protegidos)


# ------------------------------------------------------------------------------------------------------ autorización: 403 y 404 uniforme

def test_un_companero_visible_sin_permiso_recibe_403_y_lo_invisible_o_inexistente_el_mismo_404(db, mundo2):
    g = GeneradorSimulado()
    r = enviar(entrar("beto", habilitado=True, generador_objeto=g), INDIVIDUALES, cuerpo(-10, 0, persona_id=str(mundo2["ana"])))
    assert (r.status_code, r.json()["codigo"], g.llamadas, r.json()["detalles"]) == (403, "OPERACION_NO_PERMITIDA", 0, [])
    cuerpos = []
    for quien, datos in (("supt", cuerpo(-10, 0, persona_id=str(mundo2["celia"]))), ("ana", cuerpo(-10, 0, persona_id=str(uuid.uuid4()))),
                         ("ana", cuerpo(-9, 0, persona_id=str(mundo2["pablo"]))), ("externa", cuerpo(-10, 0, persona_id=str(mundo2["ana"])))):
        r = enviar(entrar(quien, habilitado=True, generador_objeto=g), INDIVIDUALES, datos)
        assert r.status_code == 404, (quien, r.status_code)
        cuerpos.append(r.json())
    assert all(c == cuerpos[0] for c in cuerpos) and cuerpos[0]["codigo"] == "RECURSO_NO_DISPONIBLE" and g.llamadas == 0
    assert enviar(entrar("ana"), INDIVIDUALES, cuerpo(-100, 10, persona_id=str(mundo2["celia"]))).status_code == 404         # un límite no revela lo que la autorización oculta


def test_el_consolidado_rechaza_a_quien_no_supervisa_y_un_equipo_ajeno_o_inexistente_es_el_mismo_404(db, mundo2):
    g = GeneradorSimulado()
    for quien in ("ana", "exsup"):
        r = enviar(entrar(quien, habilitado=True, generador_objeto=g), CONSOLIDADOS, cuerpo(-30, 0))
        assert (r.status_code, r.json()["codigo"]) == (403, "OPERACION_NO_PERMITIDA")
    equipo_u = db.execute(text("select equipo_id from pertenencia where persona_id = :p and hasta_exclusivo is null"), {"p": mundo2["supu"]}).scalar_one()
    ajenos = [enviar(entrar("supt", habilitado=True, generador_objeto=g), CONSOLIDADOS, cuerpo(-30, 0, equipo_id=str(e))) for e in (equipo_u, uuid.uuid4())]
    assert [r.status_code for r in ajenos] == [404, 404] and ajenos[0].json() == ajenos[1].json() and ajenos[0].json()["codigo"] == "RECURSO_NO_DISPONIBLE"
    cliente = entrar("supu", habilitado=True, generador_objeto=g)                                  # un supervisor con sesión abierta cuyo acceso se desactiva: ya no supervisa (RA-12)
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() - interval '1 minute' where id = :p"), {"p": mundo2["supu"]})
    r = enviar(cliente, CONSOLIDADOS, cuerpo(-30, 0))
    assert (r.status_code, r.json()["codigo"]) == (403, "ACCESO_DESACTIVADO") and g.llamadas == 0


# ------------------------------------------------------------------------------------------------------ límites

def test_el_rango_maximo_es_de_31_dias_con_ambos_extremos(db, mundo2):
    assert (get_settings().informe_max_range_days, get_settings().informe_max_hechos) == (31, 400)
    g = GeneradorSimulado()
    assert enviar(entrar("supt", habilitado=True, generador_objeto=g), CONSOLIDADOS, cuerpo(-30, 0)).status_code == 200                # 31 días
    for ruta, quien in ((CONSOLIDADOS, "supt"), (INDIVIDUALES, "ana")):
        r = enviar(entrar(quien, habilitado=True, generador_objeto=g), ruta, cuerpo(-31, 0))                                           # 32 días
        assert (r.status_code, r.json()["codigo"]) == (422, "INFORME_EXCEDE_LIMITES")
        assert r.json()["detalles"] == [{"campo": "hasta", "motivo": "rango_excede_el_maximo", "maximo_dias": 31}, {"campo": "reintento", "reintento": False, "motivo": "no_aplicable"}]
    assert g.llamadas == 5


def test_mas_de_400_hechos_autorizados_se_rechazan_sin_truncar_y_el_limite_es_el_total_del_consolidado(db, mundo2):
    g = GeneradorSimulado()
    r = enviar(entrar("supt", habilitado=True, generador_objeto=g, informe_max_hechos=12), CONSOLIDADOS, cuerpo(-30, 0))        # 13 hechos en total; ninguna persona pasa de 5
    assert (r.status_code, r.json()["codigo"]) == (422, "INFORME_EXCEDE_LIMITES")
    assert r.json()["detalles"] == [{"campo": "hechos", "motivo": "hechos_exceden_el_maximo", "maximo_hechos": 12}, {"campo": "reintento", "reintento": False, "motivo": "no_aplicable"}]
    assert enviar(entrar("supt", habilitado=True, generador_objeto=g, informe_max_hechos=13), CONSOLIDADOS, cuerpo(-30, 0)).status_code == 200           # el límite exacto se admite
    with get_owner_engine().begin() as c:                                                                                              # con el valor real: 401 avances autorizados de una sola persona
        b = _bitacora(c, mundo2["ana"], d(-1))
        a = _actividad(c, mundo2["ana"], b, "Tarea con muchos avances")
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion, registrado_en) select :a, :b, 'En progreso', 'nota', clock_timestamp() from generate_series(1, 401)"), {"a": a, "b": b})
    antes = g.llamadas
    for ruta, quien in ((INDIVIDUALES, "ana"), (CONSOLIDADOS, "supt")):
        r = enviar(entrar(quien, habilitado=True, generador_objeto=g), ruta, cuerpo(-5, 0))
        assert (r.status_code, r.json()["codigo"]) == (422, "INFORME_EXCEDE_LIMITES")
        assert r.json()["detalles"] == [{"campo": "hechos", "motivo": "hechos_exceden_el_maximo", "maximo_hechos": 400}, {"campo": "reintento", "reintento": False, "motivo": "no_aplicable"}]
        assert "401" not in r.text and "nota" not in r.text and "Tarea con muchos" not in r.text                  # ni el recuento real ni datos de los registros; nada se trunca
    assert g.llamadas == antes


# ------------------------------------------------------------------------------------------------------ habilitación y generador

def test_la_generacion_esta_desactivada_por_defecto_y_ninguna_solicitud_ejecuta_el_generador(db, mundo2):
    assert get_settings().informe_habilitado is False and get_settings().informe_generador == "ninguno"
    g = GeneradorSimulado()
    for ruta, quien, datos in ((INDIVIDUALES, "ana", cuerpo(-10, 0)), (CONSOLIDADOS, "supt", cuerpo(-30, 0))):
        r = enviar(entrar(quien, generador_objeto=g), ruta, datos)                                                                  # habilitado=False
        assert (r.status_code, r.json()["codigo"], reintento(r, False)) == (503, "INFORME_NO_GENERADO", True)                       # un interruptor desactivado no es un fallo transitorio
    assert g.llamadas == 0
    r = enviar(entrar("ana"), INDIVIDUALES, cuerpo(-10, 0))                                                                         # sin sustituir el generador
    assert (r.status_code, r.json()["codigo"]) == (503, "INFORME_NO_GENERADO")


def test_el_simulado_solo_se_usa_si_se_pide_expresamente_y_nunca_como_alternativa_silenciosa(db, mundo2):
    r = enviar(entrar("ana", habilitado=True, generador="simulado"), INDIVIDUALES, cuerpo(-10, 0))                                  # expresamente
    assert r.status_code == 200 and r.json()["narrativa"][0]["texto"].startswith("ana registró")
    r = enviar(entrar("ana", habilitado=True, generador="ninguno"), INDIVIDUALES, cuerpo(-10, 0))                                   # habilitado pero SIN generador configurado: no se elige el simulado
    assert (r.status_code, r.json()["codigo"], reintento(r, False)) == (503, "INFORME_NO_GENERADO", True) and "narrativa" not in r.json()
    with pytest.raises(ValidationError):
        Settings(informe_reintentos_validacion=1)                                                                                   # los reintentos solo admiten 0 hasta que existan


@pytest.mark.parametrize("modo,transitorio", [("no_disponible", True), ("tiempo_agotado", True), ("error_inesperado", True), ("cifra_contradictoria", False), ("campo_extra", False),
                                              ("no_es_un_objeto", False), ("enlace", False), ("obedece_orden_con_enlace", False)])
def test_un_fallo_del_generador_o_una_salida_rechazada_es_503_con_el_reintento_coherente_y_sin_contenido_parcial(db, mundo2, modo, transitorio):
    g = GeneradorSimulado(modo)
    r = enviar(entrar("ana", habilitado=True, generador_objeto=g), INDIVIDUALES, cuerpo(-10, 0))
    assert (r.status_code, r.json()["codigo"], reintento(r, transitorio)) == (503, "INFORME_NO_GENERADO", True)
    assert set(r.json()) == {"codigo", "mensaje", "detalles"} and g.llamadas == 1                                                    # un solo intento
    for ajeno in ("secreto", "777", "ejemplo.invalid", "Persona 1", "Informe de Ana", ORDEN_MALICIOSA, "999", "narrativa", "hechos"):
        assert ajeno not in r.text, ajeno
    r = enviar(entrar("supt", habilitado=True, generador_objeto=GeneradorSimulado(modo)), CONSOLIDADOS, cuerpo(-30, 0))             # en el consolidado, una persona que falla hace fallar todo
    assert r.status_code == 503 and set(r.json()) == {"codigo", "mensaje", "detalles"}


# ------------------------------------------------------------------------------------------------------ formato, sesión y ausencia de efectos

def test_el_formato_la_sesion_y_el_csrf_se_validan_antes_que_cualquier_dato(db, mundo2):
    cliente, csrf = entrar("ana", habilitado=True, generador_objeto=GeneradorSimulado())
    casos = [{**cuerpo(-10, 0), "otro": 1}, {"desde": "2026/11/01", "hasta": d(0).isoformat()}, cuerpo(-10, 0, persona_id="no-es-un-identificador"), {"desde": d(-10).isoformat()},
             cuerpo(0, -10, persona_id=str(mundo2["celia"]))]                                    # el orden de las fechas se valida antes que la persona: no revela existencia
    for datos in casos:
        r = cliente.post(INDIVIDUALES, json=datos, headers=cabeceras(csrf))
        assert (r.status_code, r.json()["codigo"]) == (400, "SOLICITUD_INVALIDA"), datos
    assert cliente.post(INDIVIDUALES, json=cuerpo(-10, 0), headers={"Origin": ORIGEN}).json()["detalles"] == [{"campo": "X-CSRF-Token", "motivo": "csrf_invalido"}]
    assert cliente.post(INDIVIDUALES, json=cuerpo(-10, 0), headers={"Origin": "https://otro-origen.invalid", "X-CSRF-Token": csrf}).json()["detalles"] == [{"campo": "Origin", "motivo": "origen_no_permitido"}]
    sin_sesion = TestClient(crear_app(), base_url=ORIGEN, raise_server_exceptions=False)
    r = sin_sesion.post(INDIVIDUALES, json=cuerpo(-10, 0), headers={"Origin": ORIGEN})
    assert (r.status_code, r.json()["codigo"]) == (401, "NO_IDENTIFICADA")
    assert sin_sesion.get(INDIVIDUALES).status_code == 405                                      # la ruta existe en la aplicación principal y solo admite POST


def test_las_solicitudes_no_escriben_ni_registran_contenido(db, mundo2, caplog):
    tablas = ("bitacora", "actividad", "planificacion", "avance", "auditoria", "persona", "pertenencia", "equipo", "clave_idempotencia")
    with get_owner_engine().connect() as c:
        antes = {t: c.execute(text(f"select count(*) from {t}")).scalar() for t in tablas}
    caplog.set_level(logging.INFO, logger="smartwork.informes")
    assert enviar(entrar("ana", habilitado=True, generador_objeto=GeneradorSimulado()), INDIVIDUALES, cuerpo(-10, 0)).status_code == 200
    assert enviar(entrar("supt", habilitado=True, generador_objeto=GeneradorSimulado()), CONSOLIDADOS, cuerpo(-30, 0)).status_code == 200
    with get_owner_engine().connect() as c:
        assert {t: c.execute(text(f"select count(*) from {t}")).scalar() for t in tablas} == antes
    mensajes = [r.getMessage() for r in caplog.records if r.name == "smartwork.informes"]
    assert mensajes and all(re.fullmatch(r"informe tipo=(individual|consolidado) resultado=ok hechos=\d+ ms=\d+", m) for m in mensajes)
    assert not any(UUID.search(m) or "ana" in m.lower() for m in mensajes) and ORDEN_MALICIOSA not in " ".join(mensajes)
