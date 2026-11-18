"""T12 — M3-03: corregir un avance ya registrado (PostgreSQL real, por HTTP).

Criterios: CA-79, CA-80, CA-101 a CA-107, CA-211, CA-236 a CA-239, CA-284, CA-297, CA-298; RN-45, RN-67, RN-80,
RN-91 a RN-93, RN-113; D-04, D-05, PA-27, PA-29 (opción A) y T-04. Una corrección modifica el avance existente
(estado, descripción o motivo de bloqueo) y se distingue de un avance nuevo: no crea, borra ni reordena nada y no
crea nunca una reactivación. Las pruebas destructivas corren solo sobre ``smartwork_test``.
"""

import threading
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db import get_owner_engine
from app.modulos.bitacoras import servicio
from app.seguridad.sesiones import NOMBRE_COOKIE
from scripts.verificar_datos import estados_actuales_incoherentes
from tests.fabricas import (
    crear_equipo, crear_identidad, crear_persona, crear_pertenencia, escenario_basico, hoy,
)
from tests.utiles_http import API, iniciar_sesion, nuevo_cliente, sesion_iniciada
from tests.utiles_m2 import avanzar, con_clave, contar, filas, iso, planificar_actividad


def corregir(cliente, csrf, avance_id, clave="__auto__", **campos):
    """M3-03. Solo envía los campos indicados (un valor ``None`` explícito se envía como nulo)."""
    return cliente.patch(f"{API}/mi/avances/{avance_id}", json=campos, headers=con_clave(csrf, clave))


def crear_avance(cliente, csrf, actividad, fecha, estado="En progreso", descripcion="Avancé", motivo=None):
    r = avanzar(cliente, csrf, actividad, fecha, estado, descripcion, motivo)
    assert r.status_code == 201, r.text
    return r.json()["avance"]["id"]


def reactivar(cliente, csrf, actividad, fecha, estado="En progreso", descripcion="Retomo", motivo=None):
    cuerpo = {"fecha_laboral": fecha, "estado": estado, "descripcion": descripcion}
    if motivo:
        cuerpo["motivo_bloqueo"] = motivo
    r = cliente.post(f"{API}/mi/actividades/{actividad}/reactivacion", json=cuerpo, headers=con_clave(csrf))
    assert r.status_code == 201, r.text
    return r.json()["avance"]["id"]


def cerrar(cliente, csrf, fecha, resumen="Resumen"):
    cliente.put(f"{API}/mi/bitacoras/{fecha}/resumen", json={"resumen": resumen}, headers=con_clave(csrf, None))
    return cliente.post(f"{API}/mi/bitacoras/{fecha}/cierre", headers=con_clave(csrf))


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c, desde=hoy() - timedelta(days=400))


@pytest.fixture()
def sesion(esc):
    return sesion_iniciada(esc)


@pytest.fixture()
def serie(sesion):
    """Actividad creada el día -6 con avances: En progreso (-5), En progreso (-4) y Completada (-3)."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-6))
    ids = [crear_avance(cliente, csrf, a, iso(-5), "En progreso", "Lunes"),
           crear_avance(cliente, csrf, a, iso(-4), "En progreso", "Martes"),
           crear_avance(cliente, csrf, a, iso(-3), "Completada", "Miércoles")]
    return a, ids


def fila_avance(v):
    return filas("select av.*, b.fecha_laboral from avance av join bitacora b on b.id = av.bitacora_id where av.id = :v", v=v)[0]


def avances_de(a):
    return filas("select av.id, av.estado, av.descripcion, av.motivo_bloqueo, av.es_reactivacion, av.registrado_en, "
                 "av.modificado_en, b.fecha_laboral from avance av join bitacora b on b.id = av.bitacora_id "
                 "where av.actividad_id = :a order by b.fecha_laboral, av.registrado_en, av.id", a=a)


def estado_de(a) -> str:
    return filas("select estado_actual from actividad where id = :a", a=a)[0].estado_actual


def entradas(operacion="correccion"):
    return filas("select * from auditoria where operacion = :o order by momento, id", o=operacion)


def instantanea(a):
    """Todo lo que una corrección rechazada no puede cambiar (CA-237)."""
    return ([tuple(x) for x in avances_de(a)], estado_de(a), contar("auditoria"), contar("clave_idempotencia"),
            contar("avance"), contar("actividad"), contar("planificacion"), contar("bitacora"))


def coherente() -> bool:
    with get_owner_engine().connect() as c:
        return estados_actuales_incoherentes(c) == []


# ============================== corrección válida (CA-79, CA-80, CA-103, CA-211) ==============================

def test_corrige_la_descripcion_de_un_avance_y_conserva_todo_lo_demas(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    antes = fila_avance(ids[0])
    r = corregir(cliente, csrf, ids[0], descripcion="Lunes, con un detalle más")
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"avance", "actividad", "estado_actual_cambio"}
    assert d["avance"]["id"] == ids[0] and d["avance"]["descripcion"] == "Lunes, con un detalle más"
    assert d["avance"]["estado"] == "En progreso" and d["avance"]["fecha_laboral"] == iso(-5)
    assert d["avance"]["es_reactivacion"] is False and d["estado_actual_cambio"] is False
    assert d["avance"]["registrado_en"].endswith("Z") and d["avance"]["modificado_en"] > d["avance"]["registrado_en"]
    despues = fila_avance(ids[0])
    assert (despues.id, despues.actividad_id, despues.bitacora_id, despues.registrado_en, despues.es_reactivacion,
            despues.fecha_laboral) == (antes.id, antes.actividad_id, antes.bitacora_id, antes.registrado_en,
                                       antes.es_reactivacion, antes.fecha_laboral)
    assert despues.descripcion == "Lunes, con un detalle más" and despues.modificado_en > antes.modificado_en
    assert d["actividad"]["id"] == a and d["actividad"]["estado_actual"] == "Completada"


def test_una_correccion_no_crea_borra_ni_reordena_avances(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    antes = [x.id for x in avances_de(a)]
    totales = (contar("avance"), contar("actividad"), contar("planificacion"), contar("bitacora"))
    corregir(cliente, csrf, ids[1], estado="Bloqueada", motivo_bloqueo="Esperando datos")
    corregir(cliente, csrf, ids[0], descripcion="Otro texto")
    assert [x.id for x in avances_de(a)] == antes
    assert (contar("avance"), contar("actividad"), contar("planificacion"), contar("bitacora")) == totales


def test_cambiar_el_estado_del_ultimo_avance_recalcula_el_estado_actual(sesion, serie):
    """CA-79 y CA-238: la finalización pasa a otro estado y la secuencia sigue siendo válida."""
    cliente, csrf = sesion
    a, ids = serie
    r = corregir(cliente, csrf, ids[2], estado="En progreso")
    assert r.status_code == 200 and r.json()["estado_actual_cambio"] is True
    assert r.json()["actividad"]["estado_actual"] == "En progreso" and estado_de(a) == "En progreso" and coherente()
    e = entradas()
    assert len(e) == 1
    assert e[0].valor_anterior["estado_actual"] == "Completada" and e[0].valor_nuevo["estado_actual"] == "En progreso"


def test_cambiar_el_estado_de_un_avance_que_no_es_el_ultimo_no_cambia_el_estado_actual(sesion, serie):
    """CA-80: el estado actual sigue siendo el del último avance y la corrección se audita igual."""
    cliente, csrf = sesion
    a, ids = serie
    r = corregir(cliente, csrf, ids[0], estado="Bloqueada", motivo_bloqueo="Sin acceso")
    assert r.status_code == 200 and r.json()["estado_actual_cambio"] is False
    assert estado_de(a) == "Completada" and len(entradas()) == 1
    assert "estado_actual" not in entradas()[0].valor_nuevo


def test_corregir_el_ultimo_avance_a_otro_estado_se_refleja_en_el_detalle_y_el_listado(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    corregir(cliente, csrf, ids[2], estado="Bloqueada", motivo_bloqueo="Falta una firma")
    d = cliente.get(f"{API}/mi/actividades/{a}").json()
    assert d["estado_actual"] == "Bloqueada" and d["avances"][-1]["estado"] == "Bloqueada"
    assert d["avances"][-1]["motivo_bloqueo"] == "Falta una firma"
    elementos = cliente.get(f"{API}/mi/actividades").json()["elementos"]
    assert [e["estado_actual"] for e in elementos if e["id"] == a] == ["Bloqueada"]
    assert [e["id"] for e in cliente.get(f"{API}/mi/actividades?estado=Completada").json()["elementos"]] == []


def test_corregir_con_una_actividad_completada_la_descripcion_de_un_avance_anterior_no_la_reactiva(sesion, serie):
    """CA-211: se acepta sin reactivar la actividad y no se registra como un avance nuevo."""
    cliente, csrf = sesion
    a, ids = serie
    r = corregir(cliente, csrf, ids[1], descripcion="Martes, corregido")
    assert r.status_code == 200 and estado_de(a) == "Completada"
    assert contar("avance") == 3 and not any(x.es_reactivacion for x in avances_de(a))


def test_la_correccion_de_una_jornada_de_hoy_tambien_se_audita(sesion):
    """CA-103: toda corrección de un avance queda auditada, no solo las de jornadas pasadas."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    v = crear_avance(cliente, csrf, a, iso(0), "En progreso", "Hoy")
    assert corregir(cliente, csrf, v, descripcion="Hoy, corregido").status_code == 200
    e = entradas()
    assert len(e) == 1 and e[0].fecha_laboral_registro == hoy()


def test_corregir_no_renueva_la_fecha_de_modificacion_de_la_bitacora_ni_la_toca(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    antes = filas("select modificada_en, estado, resumen from bitacora order by fecha_laboral")
    corregir(cliente, csrf, ids[0], descripcion="Nuevo texto")
    assert [tuple(x) for x in filas("select modificada_en, estado, resumen from bitacora order by fecha_laboral")] == [tuple(x) for x in antes]


def test_el_avance_corregido_muestra_su_fecha_de_modificacion_y_los_demas_la_de_registro(sesion, serie):
    """CA-62."""
    cliente, csrf = sesion
    a, ids = serie
    corregir(cliente, csrf, ids[1], descripcion="Martes, corregido")
    d = {x["id"]: x for x in cliente.get(f"{API}/mi/actividades/{a}").json()["avances"]}
    assert d[ids[1]]["modificado_en"] > d[ids[1]]["registrado_en"]
    assert d[ids[0]]["modificado_en"] == d[ids[0]]["registrado_en"]
    b = cliente.get(f"{API}/mi/bitacoras/{iso(-4)}").json()["avances"]
    assert b[0]["modificado_en"] > b[0]["registrado_en"]


# ============================== Bloqueada y motivo (IR-08, decisión aprobada) ==================================

def test_corregir_hacia_bloqueada_exige_motivo(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    antes = instantanea(a)
    for campos in ({"estado": "Bloqueada"}, {"estado": "Bloqueada", "motivo_bloqueo": ""},
                   {"estado": "Bloqueada", "motivo_bloqueo": "   "}, {"estado": "Bloqueada", "motivo_bloqueo": None}):
        r = corregir(cliente, csrf, ids[0], **campos)
        assert r.status_code == 422 and r.json()["codigo"] == "MOTIVO_BLOQUEO_OBLIGATORIO", campos
    assert instantanea(a) == antes


def test_corregir_el_motivo_de_un_avance_bloqueado_sin_cambiar_el_estado(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-4))
    v = crear_avance(cliente, csrf, a, iso(-3), "Bloqueada", "Esperando", "Motivo inicial")
    r = corregir(cliente, csrf, v, motivo_bloqueo="Motivo corregido")
    assert r.status_code == 200 and r.json()["avance"]["motivo_bloqueo"] == "Motivo corregido"
    e = entradas()[0]
    assert e.valor_anterior["avance"] == {"motivo_bloqueo": "Motivo inicial"}
    assert e.valor_nuevo["avance"] == {"motivo_bloqueo": "Motivo corregido"}


def test_corregir_un_bloqueo_a_otro_estado_limpia_el_motivo_y_la_auditoria_lo_conserva(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-4))
    v = crear_avance(cliente, csrf, a, iso(-3), "Bloqueada", "Esperando", "Falta el acceso")
    r = corregir(cliente, csrf, v, estado="En progreso")
    assert r.status_code == 200 and r.json()["avance"]["motivo_bloqueo"] is None
    assert fila_avance(v).motivo_bloqueo is None
    e = entradas()[0]
    assert e.valor_anterior["avance"] == {"estado": "Bloqueada", "motivo_bloqueo": "Falta el acceso"}
    assert e.valor_nuevo["avance"] == {"estado": "En progreso", "motivo_bloqueo": None}


def test_un_motivo_para_un_estado_que_no_es_bloqueada_no_es_una_solicitud_valida(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    antes = instantanea(a)
    for campos in ({"estado": "En progreso", "motivo_bloqueo": "sobra"}, {"motivo_bloqueo": "sobra"}):
        r = corregir(cliente, csrf, ids[0], **campos)
        assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA", campos
    assert instantanea(a) == antes


def test_corregir_a_bloqueada_con_motivo_lo_guarda(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    r = corregir(cliente, csrf, ids[1], estado="Bloqueada", motivo_bloqueo="Sin respuesta del cliente")
    assert r.status_code == 200 and r.json()["avance"]["motivo_bloqueo"] == "Sin respuesta del cliente"
    assert fila_avance(ids[1]).motivo_bloqueo == "Sin respuesta del cliente"


# ============================== validación del cuerpo ==========================================================

def test_un_cuerpo_vacio_no_es_una_correccion(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    r = corregir(cliente, csrf, ids[0])
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


@pytest.mark.parametrize("campo", [{"fecha_laboral": "2026-11-01"}, {"id": "otro"}, {"actividad_id": "otra"},
                                   {"bitacora_id": "otra"}, {"es_reactivacion": True}, {"registrado_en": "2026-01-01T00:00:00Z"},
                                   {"modificado_en": "2026-01-01T00:00:00Z"}, {"titulo": "Otro"}, {"planificacion": "x"}])
def test_los_campos_que_no_se_corrigen_se_rechazan(sesion, serie, campo):
    """La fecha laboral no se acepta (PP-44) ni el título ni la planificación (RN-104)."""
    cliente, csrf = sesion
    a, ids = serie
    antes = instantanea(a)
    r = corregir(cliente, csrf, ids[0], descripcion="Texto", **campo)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert instantanea(a) == antes


@pytest.mark.parametrize("estado", ["Pausada", "", "en progreso", None])
def test_un_estado_fuera_de_los_cuatro_es_estado_invalido(sesion, serie, estado):
    cliente, csrf = sesion
    a, ids = serie
    r = corregir(cliente, csrf, ids[0], estado=estado)
    assert r.status_code == 422 and r.json()["codigo"] == "ESTADO_INVALIDO"


@pytest.mark.parametrize("descripcion", ["", "   ", "\n\t", None])
def test_una_descripcion_vacia_no_se_permite(sesion, serie, descripcion):
    cliente, csrf = sesion
    a, ids = serie
    antes = instantanea(a)
    r = corregir(cliente, csrf, ids[0], descripcion=descripcion)
    assert r.status_code == 422 and r.json()["codigo"] == "DESCRIPCION_OBLIGATORIA"
    assert instantanea(a) == antes


def test_el_maximo_de_texto_se_valida_con_su_valor(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    maximo = get_settings().text_max_description
    r = corregir(cliente, csrf, ids[0], descripcion="x" * (maximo + 1))
    assert r.status_code == 422 and r.json()["codigo"] == "TEXTO_DEMASIADO_LARGO"
    assert corregir(cliente, csrf, ids[0], descripcion="x" * maximo).status_code == 200


def test_el_texto_se_trata_como_datos(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    texto = "'; drop table avance; -- <script>alert(1)</script>"
    r = corregir(cliente, csrf, ids[0], descripcion=texto)
    assert r.status_code == 200 and fila_avance(ids[0]).descripcion == texto


def test_un_identificador_mal_formado_es_una_solicitud_invalida(sesion):
    cliente, csrf = sesion
    r = corregir(cliente, csrf, "no-es-un-uuid", descripcion="x")
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


# ============================== sin cambios (T-04) =============================================================

def test_una_correccion_con_los_valores_vigentes_no_hace_nada(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    antes = instantanea(a)
    modificado = fila_avance(ids[1]).modificado_en
    r = corregir(cliente, csrf, ids[1], estado="En progreso", descripcion="Martes")
    assert r.status_code == 200 and r.json()["estado_actual_cambio"] is False
    assert r.json()["avance"]["descripcion"] == "Martes" and r.json()["avance"]["modificado_en"] == r.json()["avance"]["registrado_en"]
    assert fila_avance(ids[1]).modificado_en == modificado
    assert entradas() == []
    antes_sin_clave = antes[:3] + antes[4:]
    despues = instantanea(a)
    assert despues[:3] + despues[4:] == antes_sin_clave                       # nada cambió (la clave puede guardarse)


def test_repetir_la_misma_correccion_con_otra_clave_no_vuelve_a_auditar(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    corregir(cliente, csrf, ids[0], descripcion="Nuevo texto")
    r = corregir(cliente, csrf, ids[0], descripcion="Nuevo texto")
    assert r.status_code == 200 and len(entradas()) == 1


# ============================== bitácora cerrada (CA-284, D-04) ===============================================

def test_una_bitacora_cerrada_exige_reabrirla_antes(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    assert cerrar(cliente, csrf, iso(-4)).status_code == 200
    antes = instantanea(a)
    r = corregir(cliente, csrf, ids[1], descripcion="Martes, corregido")
    assert r.status_code == 409 and r.json()["codigo"] == "BITACORA_CERRADA"
    assert instantanea(a) == antes
    assert cliente.post(f"{API}/mi/bitacoras/{iso(-4)}/reapertura", json={"motivo": "Corregir un avance"},
                        headers=con_clave(csrf)).status_code == 200
    assert corregir(cliente, csrf, ids[1], descripcion="Martes, corregido").status_code == 200
    assert [e.operacion for e in filas("select operacion from auditoria where operacion in ('reapertura', 'correccion') order by momento, id")] == ["reapertura", "correccion"]


def test_solo_importa_la_bitacora_del_propio_avance(sesion, serie):
    """D-04: otra jornada cerrada de la misma actividad no impide corregir un avance de una jornada abierta, y no se reabre."""
    cliente, csrf = sesion
    a, ids = serie
    assert cerrar(cliente, csrf, iso(-3)).status_code == 200
    assert corregir(cliente, csrf, ids[0], descripcion="Lunes, corregido").status_code == 200
    assert filas("select estado from bitacora where fecha_laboral = :f", f=hoy() - timedelta(days=3))[0].estado == "cerrada"
    assert entradas("reapertura") == []


def test_una_jornada_cerrada_rechaza_tambien_una_correccion_que_no_cambia_nada(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    cerrar(cliente, csrf, iso(-4))
    r = corregir(cliente, csrf, ids[1], descripcion="Martes")
    assert r.status_code == 409 and r.json()["codigo"] == "BITACORA_CERRADA"


# ============================== actividad marcada por error (D-05, CA-297, CA-298) =============================

def _marcada(cliente, csrf):
    a = cliente.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf),
                     json={"fecha_laboral": iso(-3), "titulo": "Imprevisto", "estado": "En progreso", "descripcion": "Atendí"}).json()
    v = a["avance"]["id"]
    assert cliente.post(f"{API}/mi/actividades/{a['actividad']['id']}/marca-error", json={"motivo": "Duplicada"},
                        headers=con_clave(csrf)).status_code == 200
    return a["actividad"]["id"], v


def test_los_avances_de_una_actividad_marcada_no_se_corrigen(sesion):
    cliente, csrf = sesion
    a, v = _marcada(cliente, csrf)
    antes = instantanea(a)
    r = corregir(cliente, csrf, v, descripcion="Intento")
    assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_MARCADA_POR_ERROR"
    assert instantanea(a) == antes


def test_revertida_la_marca_se_pueden_corregir(sesion):
    cliente, csrf = sesion
    a, v = _marcada(cliente, csrf)
    assert cliente.post(f"{API}/mi/actividades/{a}/marca-error/reversion", headers=con_clave(csrf)).status_code == 200
    assert corregir(cliente, csrf, v, descripcion="Ahora sí").status_code == 200
    assert len(entradas()) == 1


def test_la_marca_se_evalua_antes_que_el_cuerpo_pero_despues_de_la_visibilidad(sesion):
    cliente, csrf = sesion
    a, v = _marcada(cliente, csrf)
    assert corregir(cliente, csrf, v, estado="Pausada").json()["codigo"] == "ACTIVIDAD_MARCADA_POR_ERROR"


# ============================== autorización y visibilidad (CA-101, CA-107) ====================================

def _otra_persona(identificador="otra.persona"):
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        otra = crear_persona(c, "Otra persona")
        crear_pertenencia(c, otra, crear_equipo(c, org, "Otro equipo"), desde=hoy() - timedelta(days=100))
        crear_identidad(c, otra, identificador, "contraseña-de-prueba-123")
    cliente = nuevo_cliente()
    return cliente, iniciar_sesion(cliente, identificador, "contraseña-de-prueba-123").json()["csrf_token"]


def test_el_avance_de_otra_persona_no_se_corrige(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    ajeno, csrf_ajeno = _otra_persona()
    antes = instantanea(a)
    r = corregir(ajeno, csrf_ajeno, ids[0], descripcion="Intento ajeno")
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"
    inexistente = corregir(ajeno, csrf_ajeno, str(uuid.uuid4()), descripcion="x")
    assert (inexistente.status_code, inexistente.json()) == (r.status_code, r.json())            # T-01
    assert instantanea(a) == antes


def test_un_supervisor_del_mismo_equipo_tampoco_corrige(esc):
    cliente, csrf = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf, iso(-4))
    v = crear_avance(cliente, csrf, a, iso(-3))
    with get_owner_engine().begin() as c:
        sup = crear_persona(c, "Sara supervisora")
        crear_pertenencia(c, sup, esc.equipo, "supervisor", desde=hoy() - timedelta(days=50))
        crear_identidad(c, sup, "sara.sup", "contraseña-de-prueba-123")
    s = nuevo_cliente()
    csrf_s = iniciar_sesion(s, "sara.sup", "contraseña-de-prueba-123").json()["csrf_token"]
    r = corregir(s, csrf_s, v, descripcion="Intento")
    # M4-T6: el avance de un integrante de su equipo le es VISIBLE a la supervisora (decidir_lectura), así que no corregirlo es un 403 y ya no un 404 (convenciones 3.1, CA-101, CA-107, CA-178)
    assert r.status_code == 403 and r.json()["codigo"] == "OPERACION_NO_PERMITIDA" and fila_avance(v).descripcion == "Avancé"


def test_la_visibilidad_se_evalua_antes_que_el_cuerpo(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    ajeno, csrf_ajeno = _otra_persona()
    r = corregir(ajeno, csrf_ajeno, ids[0], estado="Pausada", fecha_laboral="x")
    assert r.status_code == 404 or r.status_code == 400
    r = ajeno.patch(f"{API}/mi/avances/{ids[0]}", json={"estado": "Pausada"}, headers=con_clave(csrf_ajeno))
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"


def test_sin_sesion_no_se_corrige(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    anonimo = nuevo_cliente()
    r = anonimo.patch(f"{API}/mi/avances/{ids[0]}", json={"descripcion": "x"}, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"


# ============================== secuencia: PA-29 y casos retroactivos de PA-27 =================================

def test_corregir_a_completada_un_avance_anterior_a_otros_sin_reactivacion_se_rechaza(sesion):
    """CA-236: lunes y martes En progreso, miércoles Completada, jueves una reactivación; el lunes pasa a Completada."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-7))
    lunes = crear_avance(cliente, csrf, a, iso(-6), "En progreso", "Lunes")
    crear_avance(cliente, csrf, a, iso(-5), "En progreso", "Martes")
    crear_avance(cliente, csrf, a, iso(-4), "Completada", "Miércoles")
    reactivar(cliente, csrf, a, iso(-3))
    antes = instantanea(a)
    r = corregir(cliente, csrf, lunes, estado="Completada")
    assert r.status_code == 409 and r.json()["codigo"] == "SECUENCIA_INVALIDA"
    assert r.json()["detalles"][0]["motivo"] == "avance_tras_finalizacion_sin_reactivacion"
    assert instantanea(a) == antes and coherente()                                  # CA-237: nada cambió, ni la auditoría


def test_una_correccion_rechazada_no_crea_ninguna_reactivacion(sesion, serie):
    """CA-239, tanto si se acepta como si se rechaza."""
    cliente, csrf = sesion
    a, ids = serie
    corregir(cliente, csrf, ids[0], estado="Completada")                            # rechazada: el martes quedaría tras ella
    corregir(cliente, csrf, ids[2], estado="Bloqueada", motivo_bloqueo="x")         # aceptada
    assert not any(x.es_reactivacion for x in avances_de(a)) and contar("avance") == 3


def test_corregir_la_finalizacion_cuando_hay_una_reactivacion_posterior_se_rechaza(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-6))
    fin = crear_avance(cliente, csrf, a, iso(-5), "Completada", "Terminé")
    reactivar(cliente, csrf, a, iso(-4))
    antes = instantanea(a)
    r = corregir(cliente, csrf, fin, estado="En progreso")
    assert r.status_code == 409 and r.json()["codigo"] == "SECUENCIA_INVALIDA"
    assert r.json()["detalles"][0]["motivo"] == "reactivacion_sin_finalizacion"
    assert instantanea(a) == antes


def test_corregir_la_descripcion_de_una_finalizacion_con_reactivacion_posterior_es_valido(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-6))
    fin = crear_avance(cliente, csrf, a, iso(-5), "Completada", "Terminé")
    reactivar(cliente, csrf, a, iso(-4))
    assert corregir(cliente, csrf, fin, descripcion="Terminé, con matices").status_code == 200


def test_se_corrige_el_avance_de_una_reactivacion_y_sigue_siendo_una_reactivacion(sesion):
    """Cuando el contrato lo permite: estado entre los tres de una reactivación (o descripción y motivo)."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-6))
    crear_avance(cliente, csrf, a, iso(-5), "Completada", "Terminé")
    reac = reactivar(cliente, csrf, a, iso(-4), "En progreso", "Retomo")
    r = corregir(cliente, csrf, reac, estado="Bloqueada", motivo_bloqueo="Falta el acceso", descripcion="Retomo, con un bloqueo")
    assert r.status_code == 200 and r.json()["avance"]["es_reactivacion"] is True
    assert r.json()["estado_actual_cambio"] is True and estado_de(a) == "Bloqueada" and fila_avance(reac).es_reactivacion is True
    r = corregir(cliente, csrf, reac, estado="Pendiente")
    assert r.status_code == 200 and r.json()["avance"]["motivo_bloqueo"] is None and r.json()["avance"]["es_reactivacion"] is True


def test_una_reactivacion_no_se_corrige_a_completada(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-6))
    crear_avance(cliente, csrf, a, iso(-5), "Completada", "Terminé")
    reac = reactivar(cliente, csrf, a, iso(-4))
    antes = instantanea(a)
    r = corregir(cliente, csrf, reac, estado="Completada")
    assert r.status_code == 409 and r.json()["codigo"] == "SECUENCIA_INVALIDA"
    assert {d["motivo"] for d in r.json()["detalles"]} == {"reactivacion_con_estado_completada"}
    assert instantanea(a) == antes


def _con_par_preexistente(cliente, csrf):
    """PA-27 (CA-78): un Completada retroactivo del día -4 entre un En progreso del -5 y otro del -3. El avance del -3
    queda tras una finalización sin reactivación: una violación preexistente ADMITIDA por la inserción retroactiva."""
    a = planificar_actividad(cliente, csrf, iso(-7))
    primero = crear_avance(cliente, csrf, a, iso(-5), "En progreso", "Primero")
    posterior = crear_avance(cliente, csrf, a, iso(-3), "En progreso", "Posterior")
    retro = crear_avance(cliente, csrf, a, iso(-4), "Completada", "Retroactivo")
    assert estado_de(a) == "En progreso"
    return a, primero, retro, posterior


def test_un_par_preexistente_admitido_por_pa27_no_rechaza_una_correccion_que_no_lo_agrava(sesion):
    cliente, csrf = sesion
    a, primero, retro, posterior = _con_par_preexistente(cliente, csrf)
    assert corregir(cliente, csrf, posterior, descripcion="Posterior, corregido").status_code == 200       # no toca el estado
    assert corregir(cliente, csrf, posterior, estado="Bloqueada", motivo_bloqueo="x").status_code == 200   # no agrava
    assert corregir(cliente, csrf, retro, descripcion="Retroactivo, corregido").status_code == 200
    assert corregir(cliente, csrf, primero, descripcion="Primero, corregido").status_code == 200
    assert estado_de(a) == "Bloqueada" and coherente()


def test_corregir_el_estado_del_avance_en_violacion_a_completada_no_agrava_el_par(sesion):
    cliente, csrf = sesion
    a, primero, retro, posterior = _con_par_preexistente(cliente, csrf)
    r = corregir(cliente, csrf, posterior, estado="Completada")
    assert r.status_code == 200 and r.json()["estado_actual_cambio"] is True and estado_de(a) == "Completada"


def test_una_correccion_puede_resolver_el_par_preexistente(sesion):
    cliente, csrf = sesion
    a, primero, retro, posterior = _con_par_preexistente(cliente, csrf)
    r = corregir(cliente, csrf, retro, estado="Bloqueada", motivo_bloqueo="Sin acceso")
    assert r.status_code == 200 and estado_de(a) == "En progreso"           # el último avance del orden laboral sigue siendo el posterior


def test_una_correccion_que_agrava_el_par_preexistente_se_rechaza(sesion):
    """Corregir el primer avance a Completada deja al retroactivo (Completada) justo tras una finalización: violación NUEVA."""
    cliente, csrf = sesion
    a, primero, retro, posterior = _con_par_preexistente(cliente, csrf)
    antes = instantanea(a)
    r = corregir(cliente, csrf, primero, estado="Completada")
    assert r.status_code == 409 and r.json()["codigo"] == "SECUENCIA_INVALIDA"
    assert r.json()["detalles"] == [{"campo": "estado", "motivo": "avance_tras_finalizacion_sin_reactivacion", "avance_id": retro}]
    assert instantanea(a) == antes


def test_corregir_el_estado_de_un_avance_intermedio_a_completada_con_otro_posterior_se_rechaza(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    r = corregir(cliente, csrf, ids[1], estado="Completada")
    assert r.status_code == 409 and r.json()["codigo"] == "SECUENCIA_INVALIDA"


def test_el_orden_de_los_avances_no_cambia_al_corregir(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    corregir(cliente, csrf, ids[0], estado="Bloqueada", motivo_bloqueo="x")
    corregir(cliente, csrf, ids[1], descripcion="y")
    assert [x["id"] for x in cliente.get(f"{API}/mi/actividades/{a}").json()["avances"]] == ids


# ============================== auditoría (CA-103, CA-104, CA-106, IR-35, IR-36) ===============================

def test_una_correccion_deja_una_unica_entrada_con_autor_valores_y_jornada_del_avance(sesion, serie, esc):
    cliente, csrf = sesion
    a, ids = serie
    antes = contar("auditoria")
    corregir(cliente, csrf, ids[1], estado="Bloqueada", descripcion="Martes, con un bloqueo", motivo_bloqueo="Sin acceso")
    nuevas = filas("select * from auditoria order by momento, id")[antes:]
    assert len(nuevas) == 1
    e = nuevas[0]
    assert (e.operacion, e.tipo_objeto, e.objeto_id, e.tipo_autor, e.autor_persona_id) == (
        "correccion", "avance", uuid.UUID(ids[1]), "persona", esc.persona)
    assert e.propietaria_registro_id == esc.persona and e.fecha_laboral_registro == hoy() - timedelta(days=4)
    assert e.valor_anterior["avance"] == {"estado": "En progreso", "descripcion": "Martes", "motivo_bloqueo": None}
    assert e.valor_nuevo["avance"] == {"estado": "Bloqueada", "descripcion": "Martes, con un bloqueo", "motivo_bloqueo": "Sin acceso"}
    assert e.valor_anterior["actividad_id"] == a and e.motivo is None


def test_varias_correcciones_sucesivas_se_reconstruyen_en_orden(sesion, serie):
    """CA-104."""
    cliente, csrf = sesion
    a, ids = serie
    corregir(cliente, csrf, ids[0], descripcion="Uno")
    corregir(cliente, csrf, ids[0], descripcion="Dos")
    corregir(cliente, csrf, ids[0], descripcion="Tres")
    e = entradas()
    assert [(x.valor_anterior["avance"]["descripcion"], x.valor_nuevo["avance"]["descripcion"]) for x in e] == [
        ("Lunes", "Uno"), ("Uno", "Dos"), ("Dos", "Tres")]


def test_la_entrada_incluye_el_estado_actual_anterior_y_nuevo_solo_si_varia(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    corregir(cliente, csrf, ids[0], descripcion="No cambia el estado actual")
    corregir(cliente, csrf, ids[2], estado="Bloqueada", motivo_bloqueo="x")
    primera, segunda = entradas()
    assert "estado_actual" not in primera.valor_anterior and "estado_actual" not in primera.valor_nuevo
    assert (segunda.valor_anterior["estado_actual"], segunda.valor_nuevo["estado_actual"]) == ("Completada", "Bloqueada")


def test_un_rechazo_no_deja_entrada_de_auditoria(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    corregir(cliente, csrf, ids[0], estado="Completada")
    corregir(cliente, csrf, ids[0], estado="Pausada")
    corregir(cliente, csrf, ids[0])
    assert entradas() == []


def test_la_auditoria_de_una_correccion_no_se_reescribe_al_corregir_otra_vez(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    corregir(cliente, csrf, ids[0], descripcion="Uno")
    primera = tuple(entradas()[0])
    corregir(cliente, csrf, ids[0], descripcion="Dos")
    assert tuple(entradas()[0]) == primera and len(entradas()) == 2


# ============================== idempotencia (T-04) y atomicidad ===============================================

def test_la_cabecera_idempotency_key_es_obligatoria(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    r = corregir(cliente, csrf, ids[0], clave=None, descripcion="x")
    assert r.status_code == 400 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_OBLIGATORIA"
    assert fila_avance(ids[0]).descripcion == "Lunes"


def test_repetir_la_misma_correccion_con_la_misma_clave_no_duplica(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    r1 = corregir(cliente, csrf, ids[0], clave="k-corr", descripcion="Nuevo texto")
    r2 = corregir(cliente, csrf, ids[0], clave="k-corr", descripcion="Nuevo texto")
    assert (r1.status_code, r2.status_code) == (200, 200) and r2.json() == r1.json()
    assert r2.headers.get("idempotency-replayed") == "true" and len(entradas()) == 1


def test_reutilizar_la_clave_con_otra_correccion_se_rechaza(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    corregir(cliente, csrf, ids[0], clave="k-misma", descripcion="Uno")
    r = corregir(cliente, csrf, ids[0], clave="k-misma", descripcion="Dos")
    assert r.status_code == 422 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_REUTILIZADA"
    assert fila_avance(ids[0]).descripcion == "Uno"


def test_una_peticion_rechazada_no_consume_la_clave(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    assert corregir(cliente, csrf, ids[0], clave="k-corregible", estado="Completada").status_code == 409
    assert corregir(cliente, csrf, ids[0], clave="k-corregible", estado="Completada").status_code == 409
    assert corregir(cliente, csrf, ids[0], clave="k-corregible", descripcion="Ahora sí").status_code == 200


def test_si_falla_el_guardado_no_queda_ni_el_cambio_ni_el_estado_ni_la_clave(sesion, serie, monkeypatch):
    cliente, csrf = sesion
    a, ids = serie
    antes = instantanea(a)

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado de la auditoría")

    monkeypatch.setattr(servicio, "registrar_operacion_de_persona", falla)
    r = corregir(cliente, csrf, ids[2], clave="k-atomica", estado="Bloqueada", motivo_bloqueo="x")
    assert r.status_code == 500 and "fallo simulado" not in r.text
    assert instantanea(a) == antes and estado_de(a) == "Completada"
    monkeypatch.undo()
    assert corregir(cliente, csrf, ids[2], clave="k-atomica", estado="Bloqueada", motivo_bloqueo="x").status_code == 200


# ============================== concurrencia =================================================================

def _clientes(esc, n):
    base, _ = sesion_iniciada(esc)
    secreto = base.cookies.get(NOMBRE_COOKIE)
    csrf = base.get(f"{API}/sesion").json()["csrf_token"]
    return [nuevo_cliente({NOMBRE_COOKIE: secreto}) for _ in range(n)], csrf


def _en_paralelo(n, tarea):
    resultados, barrera = [], threading.Barrier(n)

    def hilo(i):
        barrera.wait()
        resultados.append(tarea(i))

    hs = [threading.Thread(target=hilo, args=(i,)) for i in range(n)]
    [h.start() for h in hs]
    [h.join() for h in hs]
    return resultados


def _serie_de(esc):
    cliente, csrf = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf, iso(-6))
    ids = [crear_avance(cliente, csrf, a, iso(-5), "En progreso", "Lunes"),
           crear_avance(cliente, csrf, a, iso(-4), "Completada", "Martes")]
    return a, ids


def test_correcciones_simultaneas_del_mismo_avance_se_encadenan_sin_pisarse(esc):
    a, ids = _serie_de(esc)
    clientes, csrf = _clientes(esc, 6)
    rs = _en_paralelo(6, lambda i: corregir(clientes[i], csrf, ids[0], descripcion=f"Versión {i}"))
    assert all(r.status_code == 200 for r in rs)
    e = sorted(entradas(), key=lambda x: x.valor_nuevo["avance"]["descripcion"])
    assert len(e) == 6                                                  # cada una dejó su entrada
    por_anterior = {x.valor_anterior["avance"]["descripcion"]: x.valor_nuevo["avance"]["descripcion"] for x in e}
    final = fila_avance(ids[0]).descripcion
    cadena, actual, vistos = [], "Lunes", 0
    while actual in por_anterior and vistos < 7:                       # el valor anterior de cada una es el nuevo de otra
        actual = por_anterior[actual]
        cadena.append(actual)
        vistos += 1
    assert len(cadena) == 6 and cadena[-1] == final


def test_la_misma_correccion_simultanea_con_la_misma_clave_tiene_un_solo_efecto(esc):
    a, ids = _serie_de(esc)
    clientes, csrf = _clientes(esc, 6)
    rs = _en_paralelo(6, lambda i: corregir(clientes[i], csrf, ids[0], clave="clave-concurrente", descripcion="Mismo texto"))
    assert {r.status_code for r in rs} <= {200, 409}
    assert sum(r.status_code == 200 and "idempotency-replayed" not in r.headers for r in rs) == 1
    assert len(entradas()) == 1


def test_correcciones_simultaneas_de_estado_dejan_el_estado_actual_coherente(esc):
    a, ids = _serie_de(esc)
    clientes, csrf = _clientes(esc, 6)
    estados = ["En progreso", "Pendiente", "Completada", "Bloqueada", "En progreso", "Pendiente"]
    _en_paralelo(6, lambda i: corregir(clientes[i], csrf, ids[1], estado=estados[i], motivo_bloqueo="x" if estados[i] == "Bloqueada" else None)
                 if estados[i] == "Bloqueada" else corregir(clientes[i], csrf, ids[1], estado=estados[i]))
    assert coherente() and estado_de(a) == fila_avance(ids[1]).estado


def test_una_correccion_espera_a_quien_tiene_la_actividad_bloqueada_y_ve_su_marca(esc):
    """Determinista: una marca todavía sin confirmar tiene la actividad bloqueada; la corrección espera y, al
    confirmarse, se rechaza (ACTIVIDAD_MARCADA_POR_ERROR): nunca se corrige un avance de una actividad marcada."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = cliente.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf0),
                     json={"fecha_laboral": iso(-3), "titulo": "Imprevisto", "estado": "En progreso", "descripcion": "Atendí"}).json()
    act, v = a["actividad"]["id"], a["avance"]["id"]
    clientes, csrf = _clientes(esc, 1)
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(corregir(clientes[0], csrf, v, descripcion="Intento")))
    with get_owner_engine().begin() as c:
        c.execute(text("update actividad set registrada_por_error = true, motivo_error = 'x', "
                       "marcada_por = propietaria_id, marcada_en = now() where id = :a"), {"a": act})
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "la corrección debía esperar a la marca en curso"
    hilo.join(timeout=15)
    assert resultado[0].status_code == 409 and resultado[0].json()["codigo"] == "ACTIVIDAD_MARCADA_POR_ERROR"
    assert fila_avance(v).descripcion == "Atendí" and entradas() == []


def test_una_marca_espera_a_una_correccion_en_curso_y_las_dos_conviven(esc):
    """Una corrección confirmada antes de marcar no impide marcar (el avance es de la jornada de origen)."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = cliente.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf0),
                     json={"fecha_laboral": iso(-3), "titulo": "Imprevisto", "estado": "En progreso", "descripcion": "Atendí"}).json()
    act, v = a["actividad"]["id"], a["avance"]["id"]
    clientes, csrf = _clientes(esc, 2)
    rs = _en_paralelo(2, lambda i: corregir(clientes[0], csrf, v, descripcion="Corregido") if i == 0 else
                      clientes[1].post(f"{API}/mi/actividades/{act}/marca-error", json={"motivo": "Duplicada"}, headers=con_clave(csrf)))
    assert sorted(r.status_code for r in rs) in ([200, 200], [200, 409])
    marcada = filas("select registrada_por_error from actividad where id = :a", a=act)[0].registrada_por_error
    corregida = fila_avance(v).descripcion == "Corregido"
    assert marcada is True                                              # la marca siempre prospera
    if not corregida:                                                    # si la marca fue primero, la corrección se rechazó
        assert any(r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_MARCADA_POR_ERROR" for r in rs)


def test_una_correccion_espera_a_quien_cierra_la_jornada_y_se_rechaza(esc):
    """Determinista: otra transacción tiene bloqueada la bitácora del avance (como un cierre en curso) y la cierra."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-4))
    v = crear_avance(cliente, csrf0, a, iso(-3), "En progreso", "Atendí")
    cliente.put(f"{API}/mi/bitacoras/{iso(-3)}/resumen", json={"resumen": "Hecho"}, headers=con_clave(csrf0, None))
    clientes, csrf = _clientes(esc, 1)
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(corregir(clientes[0], csrf, v, descripcion="Intento")))
    with get_owner_engine().begin() as c:
        c.execute(text("select 1 from bitacora where fecha_laboral = :f for update"), {"f": hoy() - timedelta(days=3)})
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "la corrección debía esperar al bloqueo de la jornada"
        c.execute(text("update bitacora set estado = 'cerrada', cerrada_en = now() where fecha_laboral = :f"), {"f": hoy() - timedelta(days=3)})
    hilo.join(timeout=15)
    assert resultado[0].status_code == 409 and resultado[0].json()["codigo"] == "BITACORA_CERRADA"
    assert fila_avance(v).descripcion == "Atendí" and entradas() == []


def test_una_correccion_espera_a_un_avance_nuevo_y_valida_la_secuencia_con_el_nuevo(esc):
    """Determinista: otra transacción tiene la actividad bloqueada y le añade un avance ordinario posterior. La
    corrección espera y, al liberarse, valida la secuencia con ese avance: pasar el último a Completada deja al
    nuevo tras una finalización (SECUENCIA_INVALIDA)."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    v = crear_avance(cliente, csrf0, a, iso(-5), "En progreso", "Lunes")
    clientes, csrf = _clientes(esc, 1)
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(corregir(clientes[0], csrf, v, estado="Completada")))
    with get_owner_engine().begin() as c:
        c.execute(text("select 1 from actividad where id = :a for update"), {"a": a})
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "la corrección debía esperar al bloqueo de la actividad"
        b = c.execute(text("insert into bitacora (persona_id, fecha_laboral) select propietaria_id, :f from actividad "
                           "where id = :a returning id"), {"a": a, "f": hoy() - timedelta(days=3)}).scalar_one()
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                       "values (:a, :b, 'En progreso', 'Avance concurrente')"), {"a": a, "b": b})
        c.execute(text("update actividad set estado_actual = 'En progreso' where id = :a"), {"a": a})
    hilo.join(timeout=15)
    assert resultado[0].status_code == 409 and resultado[0].json()["codigo"] == "SECUENCIA_INVALIDA"
    assert fila_avance(v).estado == "En progreso" and entradas() == [] and coherente()


# ============================== integración con M2 y M3 ======================================================

def test_la_correccion_convive_con_el_flujo_de_la_jornada_y_con_la_reactivacion(sesion):
    """Completar, corregir la finalización, volver a completar, reactivar y corregir la reactivación."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-6))
    v1 = crear_avance(cliente, csrf, a, iso(-5), "En progreso", "Empecé")
    v2 = crear_avance(cliente, csrf, a, iso(-4), "Completada", "Terminé")
    assert corregir(cliente, csrf, v2, estado="Bloqueada", motivo_bloqueo="Falta una firma").json()["estado_actual_cambio"] is True
    v3 = crear_avance(cliente, csrf, a, iso(-3), "Completada", "Terminé de verdad")
    reac = reactivar(cliente, csrf, a, iso(-2), "En progreso", "Retomo")
    assert corregir(cliente, csrf, v1, descripcion="Empecé, con más detalle").status_code == 200
    assert corregir(cliente, csrf, reac, estado="Pendiente").status_code == 200
    assert estado_de(a) == "Pendiente" and coherente()
    assert [x["id"] for x in cliente.get(f"{API}/mi/actividades/{a}").json()["avances"]] == [v1, v2, v3, reac]
    assert [e.operacion for e in filas("select operacion from auditoria where operacion in ('correccion', 'reactivacion') order by momento, id")] == [
        "correccion", "reactivacion", "correccion", "correccion"]


def test_corregir_no_cambia_lo_que_cuenta_para_cerrar_la_jornada(sesion):
    """Una corrección no crea ni quita actividades ni avances: la jornada sigue cerrándose según sus condiciones."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-4))
    v = crear_avance(cliente, csrf, a, iso(-3), "En progreso", "Atendí")
    assert corregir(cliente, csrf, v, estado="Bloqueada", motivo_bloqueo="x").status_code == 200
    assert cerrar(cliente, csrf, iso(-3)).status_code == 200


def test_el_listado_y_la_bitacora_reflejan_el_estado_tras_corregir(sesion, serie):
    cliente, csrf = sesion
    a, ids = serie
    corregir(cliente, csrf, ids[2], estado="En progreso")
    assert [e["estado_actual"] for e in cliente.get(f"{API}/mi/actividades").json()["elementos"]] == ["En progreso"]
    b = cliente.get(f"{API}/mi/bitacoras/{iso(-3)}").json()
    assert [x["estado_actual"] for x in b["actividades"] if x["id"] == a] == ["En progreso"]
    assert [x["estado"] for x in b["avances"]] == ["En progreso"]
