"""Bloque 5: M2-01a (consultar), M2-01b (abrir) y M2-03 (planificar) sobre PostgreSQL real.

Criterios: CA-32, CA-33, CA-35, CA-36, CA-37, CA-38, CA-40, CA-41, CA-42, CA-43, CA-59, CA-60,
CA-61, CA-62, CA-63, CA-64, CA-264, CA-280, CA-281, CA-282, CA-295 y las reglas D-01, D-02, D-03
y T-04 de los contratos.
"""

import threading
import uuid
from datetime import timedelta
from zoneinfo import ZoneInfo
from datetime import datetime

import pytest
from sqlalchemy import text

from app.compartido import auditoria
from app.db import get_owner_engine
from app.seguridad.sesiones import NOMBRE_COOKIE
from scripts.verificar_datos import estados_actuales_incoherentes
from tests.fabricas import (
    crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, escenario_basico, hoy,
)
from tests.utiles_http import API, cabeceras, iniciar_sesion, nuevo_cliente, sesion_iniciada

HOY = hoy


def iso(dias: int) -> str:
    return (hoy() + timedelta(days=dias)).isoformat()


def contar(tabla: str) -> int:
    with get_owner_engine().connect() as c:
        return c.execute(text(f"select count(*) from {tabla}")).scalar_one()


def consultar(cliente, fecha: str):
    return cliente.get(f"{API}/mi/bitacoras/{fecha}")


def abrir(cliente, csrf, fecha: str, **extra):
    return cliente.post(f"{API}/mi/bitacoras", json={"fecha_laboral": fecha, **extra}, headers=cabeceras(csrf))


def planificar(cliente, csrf, fecha: str, cuerpo=None, clave="__auto__"):
    encabezados = cabeceras(csrf)
    if clave == "__auto__":
        clave = str(uuid.uuid4())
    if clave is not None:
        encabezados["Idempotency-Key"] = clave
    return cliente.post(f"{API}/mi/bitacoras/{fecha}/planificaciones",
                        json={"titulo": "Preparar informe", "descripcion": "Revisar cifras"} if cuerpo is None else cuerpo,
                        headers=encabezados)


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c, desde=hoy() - timedelta(days=400))


@pytest.fixture()
def sesion(esc):
    return sesion_iniciada(esc)


# =============================== M2-01a: consultar ==================================================

def test_sin_sesion_no_se_muestra_ninguna_bitacora(esc):
    r = consultar(nuevo_cliente(), hoy().isoformat())
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"           # CA-01


def test_consultar_una_fecha_sin_bitacora_no_crea_nada(sesion):
    cliente, _ = sesion
    r = consultar(cliente, hoy().isoformat())
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"
    assert contar("bitacora") == 0                                                    # CA-282


@pytest.mark.parametrize("fecha", ["2026-13-45", "20261105", "hoy", "2026-1-5", "2026-02-30", ""])
def test_formato_de_fecha_invalido(sesion, fecha):
    cliente, _ = sesion
    r = consultar(cliente, fecha or "%20")
    assert r.status_code in (400, 404)
    if r.status_code == 400:
        assert r.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_la_identificacion_se_evalua_antes_que_el_formato(esc):
    r = consultar(nuevo_cliente(), "no-es-fecha")
    assert r.status_code == 401


def test_con_el_acceso_desactivado_no_se_consulta(sesion):
    cliente, _ = sesion
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now()"))
    r = consultar(cliente, hoy().isoformat())
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"


def test_una_persona_no_ve_la_bitacora_de_otra_con_la_misma_fecha(sesion):
    cliente, csrf = sesion
    assert abrir(cliente, csrf, hoy().isoformat()).status_code == 201
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        otra = crear_persona(c, "Otra persona")
        crear_pertenencia(c, otra, crear_equipo(c, org, "Otro equipo"), desde=hoy() - timedelta(days=5))
        crear_identidad(c, otra, "otra.persona", "contraseña-de-prueba-123")
    otro = nuevo_cliente()
    iniciar_sesion(otro, "otra.persona", "contraseña-de-prueba-123")
    r = consultar(otro, hoy().isoformat())
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"     # CA-36, T-01


# =============================== M2-01b: abrir ======================================================

def test_abrir_crea_la_bitacora_y_abrir_de_nuevo_devuelve_la_misma_sin_cambios(sesion):
    cliente, csrf = sesion
    primera = abrir(cliente, csrf, hoy().isoformat())
    assert primera.status_code == 201 and primera.json()["creada"] is True
    segunda = abrir(cliente, csrf, hoy().isoformat())
    assert segunda.status_code == 200 and segunda.json()["creada"] is False
    assert segunda.json()["bitacora"] == primera.json()["bitacora"]                   # CA-280: sin cambios
    assert contar("bitacora") == 1 and contar("auditoria") == 0                       # CA-33


def test_la_bitacora_muestra_por_separado_las_tres_fechas(sesion):
    cliente, csrf = sesion
    b = abrir(cliente, csrf, iso(-3)).json()["bitacora"]
    assert b["fecha_laboral"] == iso(-3) and b["clase_jornada"] == "pasada"
    assert b["creada_en"] and b["modificada_en"] and b["creada_en"].endswith("Z")     # CA-61, CA-62
    assert b["estado"] == "abierta" and b["resumen"] == "" and b["cerrada_en"] is None


def test_aperturas_simultaneas_de_la_misma_fecha_dejan_una_sola_bitacora(esc):
    _, csrf = sesion_iniciada(esc)
    cliente_base, _ = sesion_iniciada(esc)
    secreto = cliente_base.cookies.get(NOMBRE_COOKIE)
    csrf_base = cliente_base.get(f"{API}/sesion").json()["csrf_token"]
    resultados, barrera = [], threading.Barrier(8)

    def intentar():
        c = nuevo_cliente({NOMBRE_COOKIE: secreto})
        barrera.wait()
        resultados.append(abrir(c, csrf_base, hoy().isoformat()))

    hilos = [threading.Thread(target=intentar) for _ in range(8)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    estados = sorted(r.status_code for r in resultados)
    assert estados == [200] * 7 + [201], estados                                      # solo una recibe 201
    assert len({r.json()["bitacora"]["id"] for r in resultados}) == 1
    assert contar("bitacora") == 1
    assert csrf is not None


def test_una_fecha_anterior_a_la_primera_pertenencia_no_se_permite(sesion):
    cliente, csrf = sesion
    r = abrir(cliente, csrf, iso(-401))
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_NO_CUBIERTA"         # CA-264
    assert abrir(cliente, csrf, iso(-400)).status_code == 201                          # primer día cubierto
    assert contar("bitacora") == 1


def test_una_jornada_de_hace_meses_no_se_rechaza_por_su_antiguedad(sesion):
    cliente, csrf = sesion
    r = abrir(cliente, csrf, iso(-200))
    assert r.status_code == 201 and r.json()["bitacora"]["clase_jornada"] == "pasada"  # CA-59, CA-60


def test_se_puede_abrir_una_jornada_futura_y_no_hay_restriccion_por_festivos(sesion):
    cliente, csrf = sesion
    assert abrir(cliente, csrf, iso(10)).json()["bitacora"]["clase_jornada"] == "futura"
    assert abrir(cliente, csrf, "2026-12-25").status_code == 201                       # CA-64


def test_abrir_una_jornada_pasada_vacia_no_genera_auditoria(sesion):
    cliente, csrf = sesion
    abrir(cliente, csrf, iso(-5))
    assert contar("auditoria") == 0                                                    # D-02


def test_abrir_no_reabre_una_bitacora_cerrada(sesion):
    cliente, csrf = sesion
    abrir(cliente, csrf, iso(-1))
    with get_owner_engine().begin() as c:
        c.execute(text("update bitacora set estado = 'cerrada', cerrada_en = now()"))
    r = abrir(cliente, csrf, iso(-1))
    assert r.status_code == 200 and r.json()["bitacora"]["estado"] == "cerrada"


def test_el_cuerpo_no_admite_a_otra_persona_ni_campos_desconocidos(sesion):
    cliente, csrf = sesion
    r = abrir(cliente, csrf, hoy().isoformat(), persona_id=str(uuid.uuid4()))
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert contar("bitacora") == 0


def test_cada_persona_dispone_de_su_propia_bitacora_aunque_sea_el_mismo_dia(sesion):
    cliente, csrf = sesion
    a = abrir(cliente, csrf, hoy().isoformat()).json()["bitacora"]
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        sup = crear_persona(c, "Sara supervisora")
        crear_pertenencia(c, sup, crear_equipo(c, org, "Equipo S"), "supervisor", desde=hoy() - timedelta(days=5))
        crear_identidad(c, sup, "sara.sup", "contraseña-de-prueba-123")
    otro = nuevo_cliente()
    csrf_sup = iniciar_sesion(otro, "sara.sup", "contraseña-de-prueba-123").json()["csrf_token"]
    b = abrir(otro, csrf_sup, hoy().isoformat()).json()["bitacora"]
    assert a["id"] != b["id"] and a["persona_id"] != b["persona_id"] and contar("bitacora") == 2   # CA-32, CA-35


def test_abrir_sin_csrf_se_rechaza(sesion):
    cliente, _ = sesion
    r = cliente.post(f"{API}/mi/bitacoras", json={"fecha_laboral": hoy().isoformat()}, headers={"Origin": "https://testserver"})
    assert r.status_code == 400 and contar("bitacora") == 0


# =============================== M2-03: planificar ==================================================

def test_planificar_crea_actividad_pendiente_y_planificacion_original_y_se_consulta_despues(sesion):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, hoy().isoformat())
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["bitacora_creada"] is True                                           # CA-281, D-01
    act, plan = cuerpo["actividad"], cuerpo["planificacion"]
    assert act["estado_actual"] == "Pendiente" and act["origen"] == "planificada"      # CA-38
    assert act["titulo"] == "Preparar informe" and act["marca_error"] is None
    assert plan["tipo"] == "original" and plan["actividad_id"] == act["id"]
    assert plan["descripcion"] == "Revisar cifras"
    assert (contar("bitacora"), contar("actividad"), contar("planificacion"), contar("avance")) == (1, 1, 1, 0)
    assert contar("auditoria") == 0                                                    # jornada actual: sin entrada

    # Consulta posterior: lo persistido (CA-37), con la planificación diferenciada del avance (CA-40)
    g = consultar(cliente, hoy().isoformat()).json()
    assert [a["id"] for a in g["actividades"]] == [act["id"]]
    assert [p["id"] for p in g["planificaciones"]] == [plan["id"]]
    assert g["avances"] == [] and g["bitacora"]["id"]
    assert g["actividades"][0]["estado_actual"] == "Pendiente"
    with get_owner_engine().connect() as c:
        assert estados_actuales_incoherentes(c) == []


def test_la_planificacion_original_conserva_su_contenido(sesion):
    cliente, csrf = sesion
    plan = planificar(cliente, csrf, hoy().isoformat()).json()["planificacion"]
    # Una segunda actividad no altera la primera (CA-263 en lo que aplica a esta entrega)
    planificar(cliente, csrf, hoy().isoformat(), {"titulo": "Otra", "descripcion": "x"})
    g = consultar(cliente, hoy().isoformat()).json()
    original = next(p for p in g["planificaciones"] if p["id"] == plan["id"])
    assert original == plan


@pytest.mark.parametrize("titulo", ["", "   ", "\t\n ", None])
def test_un_titulo_vacio_o_de_solo_espacios_no_se_permite(sesion, titulo):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, hoy().isoformat(), {"titulo": titulo})
    assert r.status_code == 422 and r.json()["codigo"] == "CAMPO_OBLIGATORIO"          # CA-295, RN-112
    assert r.json()["detalles"][0]["campo"] == "titulo"
    assert (contar("bitacora"), contar("actividad"), contar("planificacion")) == (0, 0, 0)


def test_un_titulo_ausente_se_rechaza_como_campo_obligatorio(sesion):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, hoy().isoformat(), {"descripcion": "sin título"})
    assert r.status_code == 422 and r.json()["codigo"] == "CAMPO_OBLIGATORIO"


@pytest.mark.parametrize("extra", [{"estado": "Completada"}, {"propietaria_id": "x"}, {"avances": []}, {"origen": "x"}])
def test_el_cuerpo_no_admite_estado_propietaria_ni_avances(sesion, extra):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, hoy().isoformat(), {"titulo": "T", **extra})
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"         # CA-41, CA-43
    assert contar("actividad") == 0


def test_los_textos_tienen_un_maximo_configurable_y_nunca_se_truncan(sesion):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, hoy().isoformat(), {"titulo": "x" * 201})
    assert r.status_code == 422 and r.json()["codigo"] == "TEXTO_DEMASIADO_LARGO"
    assert r.json()["detalles"][0] == {"campo": "titulo", "maximo": 200}
    r = planificar(cliente, csrf, hoy().isoformat(), {"titulo": "ok", "descripcion": "d" * 4001})
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "descripcion"
    # En el límite exacto (con espacios alrededor que no cuentan) se acepta y se conserva tal cual
    titulo = "  " + "y" * 200 + "  "
    r = planificar(cliente, csrf, hoy().isoformat(), {"titulo": titulo, "descripcion": "d" * 4000})
    assert r.status_code == 201 and r.json()["actividad"]["titulo"] == titulo


def test_la_descripcion_es_opcional(sesion):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, hoy().isoformat(), {"titulo": "Solo título"})
    assert r.status_code == 201 and r.json()["planificacion"]["descripcion"] == ""


def test_los_textos_se_tratan_como_datos(sesion):
    cliente, csrf = sesion
    raro = "'; drop table actividad; -- <script>alert(1)</script>"
    r = planificar(cliente, csrf, hoy().isoformat(), {"titulo": raro, "descripcion": raro})
    assert r.status_code == 201 and r.json()["actividad"]["titulo"] == raro
    assert contar("actividad") == 1                                                    # RN-31


def test_sin_idempotency_key_se_rechaza_sin_crear_nada(sesion):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, hoy().isoformat(), clave=None)
    assert r.status_code == 400 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_OBLIGATORIA"
    assert contar("actividad") == 0 and contar("bitacora") == 0


def test_el_reintento_con_la_misma_clave_devuelve_la_respuesta_original_sin_duplicar(sesion):
    cliente, csrf = sesion
    primera = planificar(cliente, csrf, hoy().isoformat(), clave="clave-1")
    reintento = planificar(cliente, csrf, hoy().isoformat(), clave="clave-1")
    assert reintento.status_code == primera.status_code == 201
    assert reintento.json() == primera.json()
    assert reintento.headers["idempotency-replayed"] == "true" and "idempotency-replayed" not in primera.headers
    assert contar("actividad") == 1 and contar("planificacion") == 1 and contar("clave_idempotencia") == 1


def test_la_misma_clave_con_otra_peticion_se_rechaza(sesion):
    cliente, csrf = sesion
    planificar(cliente, csrf, hoy().isoformat(), clave="clave-2")
    r = planificar(cliente, csrf, hoy().isoformat(), {"titulo": "Distinta"}, clave="clave-2")
    assert r.status_code == 422 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_REUTILIZADA"
    assert contar("actividad") == 1


def test_claves_distintas_son_intenciones_distintas(sesion):
    cliente, csrf = sesion
    planificar(cliente, csrf, hoy().isoformat(), clave="a")
    planificar(cliente, csrf, hoy().isoformat(), clave="b")
    assert contar("actividad") == 2 and contar("bitacora") == 1


def test_una_peticion_rechazada_no_guarda_la_clave_y_se_puede_reintentar_corregida(sesion):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, hoy().isoformat(), {"titulo": ""}, clave="clave-3")
    assert r.status_code == 422 and contar("clave_idempotencia") == 0
    r = planificar(cliente, csrf, hoy().isoformat(), {"titulo": "Corregido"}, clave="clave-3")
    assert r.status_code == 201 and contar("actividad") == 1


def test_una_clave_caducada_se_trata_como_nueva(sesion):
    cliente, csrf = sesion
    planificar(cliente, csrf, hoy().isoformat(), clave="clave-4")
    with get_owner_engine().begin() as c:
        c.execute(text("update clave_idempotencia set caduca_en = now() - interval '1 minute'"))
    r = planificar(cliente, csrf, hoy().isoformat(), clave="clave-4")
    assert r.status_code == 201 and "idempotency-replayed" not in r.headers
    assert contar("actividad") == 2 and contar("clave_idempotencia") == 1


def test_una_persona_desactivada_no_recibe_el_resultado_guardado(sesion):
    cliente, csrf = sesion
    planificar(cliente, csrf, hoy().isoformat(), clave="clave-5")
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now()"))
    r = planificar(cliente, csrf, hoy().isoformat(), clave="clave-5")
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"


def test_peticiones_simultaneas_con_la_misma_clave_crean_una_sola_actividad(esc):
    cliente_base, _ = sesion_iniciada(esc)
    secreto = cliente_base.cookies.get(NOMBRE_COOKIE)
    csrf = cliente_base.get(f"{API}/sesion").json()["csrf_token"]
    resultados, barrera = [], threading.Barrier(6)

    def intentar():
        c = nuevo_cliente({NOMBRE_COOKIE: secreto})
        barrera.wait()
        resultados.append(planificar(c, csrf, hoy().isoformat(), clave="clave-concurrente"))

    hilos = [threading.Thread(target=intentar) for _ in range(6)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert {r.status_code for r in resultados} <= {201, 409}
    assert [r.json()["codigo"] for r in resultados if r.status_code == 409] == \
        ["OPERACION_EN_CURSO"] * sum(r.status_code == 409 for r in resultados)
    assert sum(r.status_code == 201 and "idempotency-replayed" not in r.headers for r in resultados) == 1
    assert contar("actividad") == 1 and contar("planificacion") == 1


def test_planificaciones_simultaneas_con_claves_distintas_en_una_fecha_nueva_dejan_una_bitacora(esc):
    cliente_base, _ = sesion_iniciada(esc)
    secreto = cliente_base.cookies.get(NOMBRE_COOKIE)
    csrf = cliente_base.get(f"{API}/sesion").json()["csrf_token"]
    resultados, barrera = [], threading.Barrier(6)

    def intentar(i):
        c = nuevo_cliente({NOMBRE_COOKIE: secreto})
        barrera.wait()
        resultados.append(planificar(c, csrf, hoy().isoformat(), {"titulo": f"Actividad {i}"}))

    hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(6)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert [r.status_code for r in resultados] == [201] * 6, [r.text for r in resultados if r.status_code != 201]
    assert contar("bitacora") == 1 and contar("actividad") == 6                       # IR-01
    assert sum(r.json()["bitacora_creada"] for r in resultados) == 1


def test_planificar_para_una_fecha_futura_es_valido_y_no_se_audita(sesion):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, iso(3))
    assert r.status_code == 201 and r.json()["actividad"]["estado_actual"] == "Pendiente"   # CA-42
    assert contar("auditoria") == 0


def test_planificar_en_una_jornada_pasada_deja_una_unica_entrada_de_auditoria(sesion, esc):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, iso(-4), clave="pasada-1")
    assert r.status_code == 201 and r.json()["bitacora_creada"] is True
    with get_owner_engine().connect() as c:
        filas = c.execute(text("select * from auditoria")).all()
    assert len(filas) == 1                                                             # una entrada por operación
    e = filas[0]
    assert (e.tipo_autor, e.operacion, e.tipo_objeto) == ("persona", "modificacion_jornada_pasada", "actividad")
    assert e.autor_persona_id == esc.persona and e.propietaria_registro_id == esc.persona
    assert e.fecha_laboral_registro.isoformat() == iso(-4)
    assert e.valor_nuevo["bitacora_creada"] is True                                    # la creación implícita va en la misma entrada
    assert e.valor_nuevo["actividad"]["titulo"] == "Preparar informe"
    assert str(e.objeto_id) == r.json()["actividad"]["id"]
    # El reintento no duplica los efectos ni la auditoría
    planificar(cliente, csrf, iso(-4), clave="pasada-1")
    assert contar("auditoria") == 1 and contar("actividad") == 1
    # Una escritura nueva sobre la misma jornada pasada es otra operación, con su entrada
    r2 = planificar(cliente, csrf, iso(-4), {"titulo": "Segunda"})
    assert r2.json()["bitacora_creada"] is False and contar("auditoria") == 2


def test_planificar_en_una_jornada_de_hace_meses_se_acepta(sesion):
    cliente, csrf = sesion
    assert planificar(cliente, csrf, iso(-300)).status_code == 201                    # CA-59, CA-60


def test_una_fecha_no_cubierta_se_rechaza_sin_cambios_ni_auditoria(sesion):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, iso(-500))
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_NO_CUBIERTA"
    assert (contar("bitacora"), contar("actividad"), contar("auditoria"), contar("clave_idempotencia")) == (0, 0, 0, 0)


def test_una_bitacora_cerrada_exige_reabrirla_antes(sesion):
    cliente, csrf = sesion
    abrir(cliente, csrf, iso(-1))
    with get_owner_engine().begin() as c:
        c.execute(text("update bitacora set estado = 'cerrada', cerrada_en = now()"))
    r = planificar(cliente, csrf, iso(-1))
    assert r.status_code == 409 and r.json()["codigo"] == "BITACORA_CERRADA"
    assert (contar("actividad"), contar("auditoria"), contar("clave_idempotencia")) == (0, 0, 0)


def test_si_falla_la_auditoria_no_queda_ningun_cambio(sesion, monkeypatch):
    """IR-24: la operación de dominio y su entrada de auditoría son atómicas."""
    cliente, csrf = sesion

    def fallar(*args, **kwargs):
        raise RuntimeError("fallo simulado de la auditoría")

    monkeypatch.setattr("app.modulos.bitacoras.servicio.registrar_operacion_de_persona", fallar)
    r = planificar(cliente, csrf, iso(-2))
    assert r.status_code == 500 and r.json()["codigo"] == "ERROR_INTERNO"
    assert "fallo simulado" not in r.text
    assert (contar("bitacora"), contar("actividad"), contar("planificacion"), contar("clave_idempotencia")) == (0, 0, 0, 0)
    assert auditoria is not None


# --------------------------- Orden de evaluación (convenciones 3.2) --------------------------------

def test_sin_sesion_prevalece_sobre_un_cuerpo_invalido(esc):
    r = nuevo_cliente().post(f"{API}/mi/bitacoras/{hoy().isoformat()}/planificaciones",
                             json={"titulo": "T", "estado": "x"}, headers={"Idempotency-Key": "k"})
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"


def test_el_acceso_desactivado_prevalece_sobre_el_resto(sesion):
    cliente, csrf = sesion
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now()"))
    r = cliente.post(f"{API}/mi/bitacoras/no-es-fecha/planificaciones", json={"estado": "x"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"


def test_un_formato_de_fecha_invalido_se_rechaza_antes_de_las_reglas_de_negocio(sesion):
    cliente, csrf = sesion
    r = planificar(cliente, csrf, "2026-99-99", {"titulo": ""})
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


# --------------------------- Fecha actual en la zona de la organización (CA-63) ---------------------

@pytest.mark.parametrize("zona", ["Pacific/Kiritimati", "Pacific/Pago_Pago", "America/Bogota"])
def test_la_fecha_actual_la_calcula_el_servidor_en_la_zona_de_la_organizacion(zona):
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c, zona)
        p = crear_persona(c)
        crear_pertenencia(c, p, crear_equipo(c, org), desde=datetime.now(ZoneInfo(zona)).date() - timedelta(days=3))
        crear_identidad(c, p, "zona.prueba", "contraseña-de-prueba-123")
    cliente = nuevo_cliente()
    iniciar_sesion(cliente, "zona.prueba", "contraseña-de-prueba-123")
    esperada = datetime.now(ZoneInfo(zona)).date().isoformat()
    assert cliente.get(f"{API}/sesion").json()["fecha_actual"] == esperada
