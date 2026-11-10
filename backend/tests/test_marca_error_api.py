"""T11 — M3-05 y M3-06: marcar una actividad como registrada por error y revertir la marca (PostgreSQL real,
por HTTP).

Criterios: CA-115 a CA-123, CA-287 a CA-290; RN-59, RN-60, RN-109, RN-113; IR-18, IR-25, IR-36; D-04b, PA-28 y
T-04. La marca es LÓGICA: no se borra ninguna fila, no cambia el estado de la actividad y no obliga a reabrir
la jornada. Las pruebas destructivas corren solo sobre ``smartwork_test``.
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
from tests.fabricas import (
    crear_equipo, crear_identidad, crear_persona, crear_pertenencia, escenario_basico, hoy,
)
from tests.utiles_http import API, iniciar_sesion, nuevo_cliente, sesion_iniciada
from tests.utiles_m2 import avanzar, con_clave, contar, filas, iso, planificar_actividad


def marcar(cliente, csrf, actividad_id, motivo="Creada por equivocación", clave="__auto__", **extra):
    """M3-05. ``motivo=None`` omite el campo."""
    cuerpo = {} if motivo is None else {"motivo": motivo}
    return cliente.post(f"{API}/mi/actividades/{actividad_id}/marca-error", json={**cuerpo, **extra},
                        headers=con_clave(csrf, clave))


def revertir(cliente, csrf, actividad_id, clave="__auto__"):
    """M3-06. Sin cuerpo."""
    return cliente.post(f"{API}/mi/actividades/{actividad_id}/marca-error/reversion", headers=con_clave(csrf, clave))


def cerrar(cliente, csrf, fecha, resumen="Resumen de la jornada"):
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
def actividad(sesion):
    """Una actividad planificada el día -6 (jornada de origen = hoy - 6), sin avances."""
    cliente, csrf = sesion
    return planificar_actividad(cliente, csrf, iso(-6))


def fila_actividad(a):
    return filas("select * from actividad where id = :a", a=a)[0]


def entradas(operacion="marca_error"):
    return filas("select * from auditoria where operacion = :o order by momento, id", o=operacion)


def total_auditoria() -> int:
    return contar("auditoria")


def foto_de_registros() -> tuple:
    """Lo que la marca NO puede borrar ni alterar: número de filas de cada tabla de dominio."""
    return tuple(contar(t) for t in ("bitacora", "actividad", "planificacion", "avance"))


# ============================== marcar: caso positivo (CA-115, CA-121) ======================================

def test_marca_una_actividad_sin_avances_con_motivo(sesion, actividad, esc):
    cliente, csrf = sesion
    r = marcar(cliente, csrf, actividad, "Se creó dos veces")
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"actividad"} and d["actividad"]["id"] == actividad
    marca = d["actividad"]["marca_error"]
    assert set(marca) == {"motivo", "marcada_en"} and marca["motivo"] == "Se creó dos veces"
    assert marca["marcada_en"].endswith("Z")
    fila = fila_actividad(actividad)
    assert fila.registrada_por_error is True and fila.motivo_error == "Se creó dos veces"
    assert fila.marcada_por == esc.persona and fila.marcada_en is not None


def test_la_marca_no_es_un_quinto_estado_y_no_cambia_el_estado_actual(sesion, actividad):
    """CA-121: la actividad no se ha borrado y su estado sigue siendo uno de los cuatro."""
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-6), "Bloqueada", "Esperando datos", "Sin acceso")
    antes = fila_actividad(actividad).estado_actual
    d = marcar(cliente, csrf, actividad).json()["actividad"]
    assert d["estado_actual"] == antes == "Bloqueada" and fila_actividad(actividad).estado_actual == "Bloqueada"


def test_marcar_no_borra_ni_modifica_ningun_registro(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-6), "En progreso", "Primer avance")
    antes = foto_de_registros()
    avances_antes = filas("select * from avance order by id")
    plan_antes = filas("select * from planificacion order by id")
    marcar(cliente, csrf, actividad)
    assert foto_de_registros() == antes
    assert filas("select * from avance order by id") == avances_antes
    assert filas("select * from planificacion order by id") == plan_antes


def test_marcar_no_renueva_la_fecha_de_modificacion_de_la_bitacora(sesion, actividad):
    """RN-109: es un cambio lógico de validez, no una corrección del contenido de la bitácora."""
    cliente, csrf = sesion
    antes = filas("select modificada_en, estado, resumen from bitacora")[0]
    marcar(cliente, csrf, actividad)
    assert tuple(filas("select modificada_en, estado, resumen from bitacora")[0]) == tuple(antes)


def test_el_titulo_la_propietaria_y_la_jornada_de_origen_no_cambian(sesion, actividad):
    cliente, csrf = sesion
    antes = fila_actividad(actividad)
    marcar(cliente, csrf, actividad)
    despues = fila_actividad(actividad)
    assert (despues.titulo, despues.propietaria_id, despues.bitacora_origen_id, despues.origen, despues.creada_en) == (
        antes.titulo, antes.propietaria_id, antes.bitacora_origen_id, antes.origen, antes.creada_en)


def test_una_actividad_completada_tambien_se_marca_si_no_tiene_avances_posteriores(sesion):
    cliente, csrf = sesion
    a = cliente.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf),
                     json={"fecha_laboral": iso(-3), "titulo": "Imprevisto", "estado": "Completada",
                           "descripcion": "Lo resolví"}).json()["actividad"]["id"]
    r = marcar(cliente, csrf, a)
    assert r.status_code == 200 and r.json()["actividad"]["estado_actual"] == "Completada"


# ============================== motivo y cuerpo (CA-116) ====================================================

@pytest.mark.parametrize("motivo", [None, "", "   ", "\n\t"])
def test_sin_motivo_no_se_permite_y_no_cambia_nada(sesion, actividad, motivo):
    cliente, csrf = sesion
    antes = total_auditoria()
    r = marcar(cliente, csrf, actividad, motivo)
    assert r.status_code == 422 and r.json()["codigo"] == "MOTIVO_OBLIGATORIO"
    assert fila_actividad(actividad).registrada_por_error is False and total_auditoria() == antes


def test_un_motivo_nulo_explicito_es_motivo_obligatorio(sesion, actividad):
    cliente, csrf = sesion
    r = cliente.post(f"{API}/mi/actividades/{actividad}/marca-error", json={"motivo": None}, headers=con_clave(csrf))
    assert r.status_code == 422 and r.json()["codigo"] == "MOTIVO_OBLIGATORIO"


def test_el_maximo_de_texto_del_motivo_se_valida_con_su_valor(sesion, actividad):
    cliente, csrf = sesion
    maximo = get_settings().text_max_description
    assert marcar(cliente, csrf, actividad, "x" * (maximo + 1)).json()["codigo"] == "TEXTO_DEMASIADO_LARGO"
    assert fila_actividad(actividad).registrada_por_error is False
    assert marcar(cliente, csrf, actividad, "x" * maximo).status_code == 200


@pytest.mark.parametrize("extra", [{"estado": "Completada"}, {"titulo": "Otro"}, {"otra_actividad": "otra"},
                                   {"marcada_por": "alguien"}])
def test_el_cuerpo_no_admite_otros_campos(sesion, actividad, extra):
    cliente, csrf = sesion
    r = marcar(cliente, csrf, actividad, "Duplicada", **extra)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert fila_actividad(actividad).registrada_por_error is False


def test_el_motivo_se_trata_como_datos(sesion, actividad):
    cliente, csrf = sesion
    motivo = "'; drop table actividad; -- <script>alert(1)</script>"
    r = marcar(cliente, csrf, actividad, motivo)
    assert r.status_code == 200 and r.json()["actividad"]["marca_error"]["motivo"] == motivo
    assert fila_actividad(actividad).motivo_error == motivo


def test_un_identificador_mal_formado_es_una_solicitud_invalida(sesion):
    cliente, csrf = sesion
    r = marcar(cliente, csrf, "no-es-un-uuid")
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert revertir(cliente, csrf, "no-es-un-uuid").status_code == 400


# ============================== avances posteriores (CA-115, CA-117, PA-28) =================================

def test_con_avances_en_jornadas_posteriores_a_su_origen_no_procede(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-3), "En progreso", "Seguí otro día")
    antes = total_auditoria()
    r = marcar(cliente, csrf, actividad)
    assert r.status_code == 409 and r.json()["codigo"] == "MARCA_NO_PROCEDE"                              # CA-117
    assert fila_actividad(actividad).registrada_por_error is False and total_auditoria() == antes


def test_un_avance_de_cualquier_tipo_en_una_jornada_posterior_impide_marcar(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-5), "Completada", "Terminé")
    cliente.post(f"{API}/mi/actividades/{actividad}/reactivacion", headers=con_clave(csrf),
                 json={"fecha_laboral": iso(-2), "estado": "En progreso", "descripcion": "Retomo"})
    assert marcar(cliente, csrf, actividad).json()["codigo"] == "MARCA_NO_PROCEDE"


def test_los_avances_de_la_propia_jornada_de_origen_no_lo_impiden(sesion, actividad):
    """RN-59 habla de jornadas POSTERIORES: varios avances el mismo día de origen no impiden marcar."""
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-6), "En progreso", "Uno")
    avanzar(cliente, csrf, actividad, iso(-6), "Bloqueada", "Dos", "Sin acceso")
    assert marcar(cliente, csrf, actividad).status_code == 200


def test_el_origen_es_la_fecha_de_la_bitacora_de_origen_y_no_creada_en(sesion, actividad):
    """PA-28. ``creada_en`` es hoy; el avance del día -3 es anterior a ese instante pero POSTERIOR a la jornada
    de origen (-6): no procede. Comparar con ``creada_en`` lo habría permitido."""
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-3), "En progreso", "Seguí")
    assert fila_actividad(actividad).creada_en.date() >= hoy()
    assert marcar(cliente, csrf, actividad).json()["codigo"] == "MARCA_NO_PROCEDE"


def test_un_avance_anterior_al_origen_no_impide_marcar(sesion, actividad):
    """PA-28 (provisional): se acepta un avance anterior a la jornada de origen; no es «posterior»."""
    cliente, csrf = sesion
    assert avanzar(cliente, csrf, actividad, iso(-8), "En progreso", "Antes del origen").status_code == 201
    assert marcar(cliente, csrf, actividad).status_code == 200


def test_las_continuaciones_planificadas_no_son_avances_y_no_lo_impiden(sesion, actividad):
    cliente, csrf = sesion
    r = cliente.post(f"{API}/mi/actividades/{actividad}/continuaciones-planificadas", headers=con_clave(csrf),
                     json={"fecha_laboral": iso(3), "descripcion": "Seguir"})
    assert r.status_code == 201
    assert marcar(cliente, csrf, actividad).status_code == 200
    assert contar("planificacion") == 2          # se conservan vinculadas a la actividad (IR-18)


# ============================== ya marcada, autorización y visibilidad (CA-118) =============================

def test_marcar_dos_veces_se_rechaza_y_no_duplica_nada(sesion, actividad):
    cliente, csrf = sesion
    primera = marcar(cliente, csrf, actividad, "Primer motivo").json()["actividad"]["marca_error"]
    r = marcar(cliente, csrf, actividad, "Otro motivo")
    assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_MARCADA_POR_ERROR"
    assert fila_actividad(actividad).motivo_error == "Primer motivo" and len(entradas()) == 1
    assert primera["motivo"] == "Primer motivo"


def _otra_persona(identificador="otra.persona"):
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        otra = crear_persona(c, "Otra persona")
        crear_pertenencia(c, otra, crear_equipo(c, org, "Otro equipo"), desde=hoy() - timedelta(days=100))
        crear_identidad(c, otra, identificador, "contraseña-de-prueba-123")
    cliente = nuevo_cliente()
    return cliente, iniciar_sesion(cliente, identificador, "contraseña-de-prueba-123").json()["csrf_token"]


def test_la_actividad_de_otra_persona_no_se_marca_ni_se_revierte(sesion, actividad):
    cliente, csrf = sesion
    ajeno, csrf_ajeno = _otra_persona()
    r = marcar(ajeno, csrf_ajeno, actividad)
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"                         # CA-118
    inexistente = marcar(ajeno, csrf_ajeno, str(uuid.uuid4()))
    assert (inexistente.status_code, inexistente.json()) == (r.status_code, r.json())                     # T-01
    assert fila_actividad(actividad).registrada_por_error is False
    marcar(cliente, csrf, actividad)
    ra = revertir(ajeno, csrf_ajeno, actividad)
    assert ra.status_code == 404 and ra.json()["codigo"] == "RECURSO_NO_DISPONIBLE"                       # CA-123
    assert (ra.status_code, ra.json()) == (revertir(ajeno, csrf_ajeno, str(uuid.uuid4())).status_code,
                                           revertir(ajeno, csrf_ajeno, str(uuid.uuid4())).json())
    assert fila_actividad(actividad).registrada_por_error is True and len(entradas("reversion_marca")) == 0


def test_un_supervisor_del_mismo_equipo_tampoco_marca_ni_revierte(esc):
    cliente, csrf = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf, iso(-4))
    with get_owner_engine().begin() as c:
        sup = crear_persona(c, "Sara supervisora")
        crear_pertenencia(c, sup, esc.equipo, "supervisor", desde=hoy() - timedelta(days=50))
        crear_identidad(c, sup, "sara.sup", "contraseña-de-prueba-123")
    s = nuevo_cliente()
    csrf_s = iniciar_sesion(s, "sara.sup", "contraseña-de-prueba-123").json()["csrf_token"]
    assert marcar(s, csrf_s, a).status_code == 404 and fila_actividad(a).registrada_por_error is False
    marcar(cliente, csrf, a)
    assert revertir(s, csrf_s, a).status_code == 404 and fila_actividad(a).registrada_por_error is True


def test_la_visibilidad_se_evalua_antes_que_el_cuerpo(sesion, actividad):
    ajeno, csrf_ajeno = _otra_persona()
    r = marcar(ajeno, csrf_ajeno, actividad, motivo=None)
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"


def test_sin_sesion_o_con_el_acceso_desactivado_no_se_marca(sesion, esc, actividad):
    cliente, csrf = sesion
    anonimo = nuevo_cliente()
    r = anonimo.post(f"{API}/mi/actividades/{actividad}/marca-error", json={"motivo": "x"},
                     headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": esc.persona})
    r = marcar(cliente, csrf, actividad)
    assert r.status_code in (401, 403) and fila_actividad(actividad).registrada_por_error is False


# ============================== efectos de la marca (CA-119, CA-120) ========================================

def test_la_actividad_marcada_sale_del_listado_operativo(sesion, actividad):
    cliente, csrf = sesion
    otra = planificar_actividad(cliente, csrf, iso(-6), "Otra actividad")
    antes = [e["id"] for e in cliente.get(f"{API}/mi/actividades").json()["elementos"]]
    assert set(antes) == {actividad, otra}
    marcar(cliente, csrf, actividad)
    despues = [e["id"] for e in cliente.get(f"{API}/mi/actividades").json()["elementos"]]
    assert despues == [otra]                                                                              # CA-119
    assert cliente.get(f"{API}/mi/actividades?estado=Pendiente").json()["elementos"] == [
        e for e in cliente.get(f"{API}/mi/actividades?estado=Pendiente").json()["elementos"] if e["id"] == otra]


def test_la_actividad_marcada_sigue_consultable_con_su_historial(sesion, actividad):
    """CA-120 y CA-121: no se oculta ni se borra; el detalle conserva planificación, avances y la marca."""
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-6), "En progreso", "Primer avance")
    marcar(cliente, csrf, actividad, "Duplicada")
    d = cliente.get(f"{API}/mi/actividades/{actividad}").json()
    assert d["actividad"]["marca_error"]["motivo"] == "Duplicada" and d["estado_actual"] == "En progreso"
    assert d["planificacion_original"] is not None and len(d["avances"]) == 1
    b = cliente.get(f"{API}/mi/bitacoras/{iso(-6)}").json()
    marcada = [a for a in b["actividades"] if a["id"] == actividad]
    assert len(marcada) == 1 and marcada[0]["marca_error"]["motivo"] == "Duplicada"
    assert len(b["avances"]) == 1 and len(b["planificaciones"]) == 1


@pytest.mark.parametrize("operacion", ["avance", "continuacion", "reactivacion"])
def test_la_actividad_marcada_no_admite_avances_continuaciones_ni_reactivacion(sesion, actividad, operacion):
    cliente, csrf = sesion
    if operacion == "reactivacion":
        avanzar(cliente, csrf, actividad, iso(-6), "Completada", "Hecho")
    marcar(cliente, csrf, actividad)
    antes = foto_de_registros()
    if operacion == "avance":
        r = avanzar(cliente, csrf, actividad, iso(-3))
    elif operacion == "continuacion":
        r = cliente.post(f"{API}/mi/actividades/{actividad}/continuaciones-planificadas", headers=con_clave(csrf),
                         json={"fecha_laboral": iso(3), "descripcion": "x"})
    else:
        r = cliente.post(f"{API}/mi/actividades/{actividad}/reactivacion", headers=con_clave(csrf),
                         json={"fecha_laboral": iso(-3), "estado": "En progreso", "descripcion": "x"})
    assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_MARCADA_POR_ERROR"                   # IR-18
    assert foto_de_registros() == antes


def test_la_actividad_marcada_no_cuenta_para_cerrar_la_jornada(sesion, actividad):
    """RN-109 y CA-283: una jornada abierta cuya única actividad está marcada no se cierra; al revertir, sí."""
    cliente, csrf = sesion
    marcar(cliente, csrf, actividad)
    r = cerrar(cliente, csrf, iso(-6))
    assert r.status_code == 409 and r.json()["codigo"] == "CONDICIONES_DE_CIERRE_NO_CUMPLIDAS"
    assert {"campo": "actividades", "motivo": "sin_actividad_creada_ni_continuada"} in r.json()["detalles"]
    assert revertir(cliente, csrf, actividad).status_code == 200
    assert cerrar(cliente, csrf, iso(-6)).status_code == 200                                              # CA-290


# ============================== jornada de origen cerrada (RN-109, CA-287 a CA-289) =========================

def test_con_otra_actividad_valida_se_marca_sin_reabrir_la_jornada(sesion, actividad):
    """CA-287."""
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(-6), "Segunda")
    assert cerrar(cliente, csrf, iso(-6)).status_code == 200
    antes = filas("select estado, cerrada_en, modificada_en from bitacora")[0]
    r = marcar(cliente, csrf, actividad)
    assert r.status_code == 200
    assert tuple(filas("select estado, cerrada_en, modificada_en from bitacora")[0]) == tuple(antes)
    assert filas("select estado from bitacora")[0].estado == "cerrada" and entradas("reapertura") == []


def test_si_era_la_unica_actividad_valida_de_una_jornada_cerrada_se_rechaza_sin_cambiar_nada(sesion, actividad):
    """CA-288."""
    cliente, csrf = sesion
    assert cerrar(cliente, csrf, iso(-6)).status_code == 200
    antes = (foto_de_registros(), total_auditoria(), contar("clave_idempotencia"))
    r = marcar(cliente, csrf, actividad)
    assert r.status_code == 409 and r.json()["codigo"] == "MARCA_INVALIDARIA_CIERRE"
    assert r.json()["detalles"] == [{"campo": "actividades", "motivo": "sin_actividad_creada_ni_continuada",
                                     "fecha_laboral": iso(-6)}]
    assert fila_actividad(actividad).registrada_por_error is False and fila_actividad(actividad).motivo_error is None
    assert (foto_de_registros(), total_auditoria(), contar("clave_idempotencia")) == antes
    assert filas("select estado from bitacora")[0].estado == "cerrada"


def test_otra_actividad_iniciada_antes_y_continuada_en_la_jornada_la_mantiene_valida(sesion):
    """CA-289: la jornada conserva una actividad válida CONTINUADA (iniciada en una jornada anterior)."""
    cliente, csrf = sesion
    antigua = planificar_actividad(cliente, csrf, iso(-9), "Antigua")
    creada = planificar_actividad(cliente, csrf, iso(-6), "Creada en la jornada")
    assert avanzar(cliente, csrf, antigua, iso(-6), "En progreso", "La continúo hoy").status_code == 201
    assert cerrar(cliente, csrf, iso(-6)).status_code == 200
    assert marcar(cliente, csrf, creada).status_code == 200
    assert filas("select estado from bitacora where fecha_laboral = :f", f=hoy() - timedelta(days=6))[0].estado == "cerrada"
    # la antigua tiene un avance posterior a su origen (-9 -> -6): no procede marcarla (RN-59)
    assert marcar(cliente, csrf, antigua).json()["codigo"] == "MARCA_NO_PROCEDE"


def test_una_continuacion_planificada_no_mantiene_valida_la_jornada(sesion):
    """CA-184: solo un AVANCE de esa fecha cuenta como continuada."""
    cliente, csrf = sesion
    antigua = planificar_actividad(cliente, csrf, iso(-9), "Antigua")
    creada = planificar_actividad(cliente, csrf, iso(-6), "Creada")
    cliente.post(f"{API}/mi/actividades/{antigua}/continuaciones-planificadas", headers=con_clave(csrf),
                 json={"fecha_laboral": iso(3), "descripcion": "Más adelante"})
    assert cerrar(cliente, csrf, iso(-6)).status_code == 200
    assert marcar(cliente, csrf, creada).json()["codigo"] == "MARCA_INVALIDARIA_CIERRE"


def test_si_la_jornada_de_origen_esta_abierta_no_hay_comprobacion_de_cierre(sesion, actividad):
    cliente, csrf = sesion
    assert filas("select estado from bitacora")[0].estado == "abierta"
    assert marcar(cliente, csrf, actividad).status_code == 200


def test_reabrir_marcar_y_volver_a_cerrar_exige_cumplir_las_condiciones(sesion, actividad):
    """La vía que el contrato indica para marcar la actividad que la comprobación rechaza."""
    cliente, csrf = sesion
    cerrar(cliente, csrf, iso(-6))
    assert marcar(cliente, csrf, actividad).json()["codigo"] == "MARCA_INVALIDARIA_CIERRE"
    assert cliente.post(f"{API}/mi/bitacoras/{iso(-6)}/reapertura", json={"motivo": "Marcar la actividad"},
                        headers=con_clave(csrf)).status_code == 200
    assert marcar(cliente, csrf, actividad).status_code == 200
    nueva = planificar_actividad(cliente, csrf, iso(-6), "Sustituta")
    assert cerrar(cliente, csrf, iso(-6)).status_code == 200 and nueva


def test_una_actividad_con_avance_anterior_al_origen_cuenta_en_esa_jornada_cerrada(sesion, actividad):
    """PA-28 provisional admite un avance anterior al origen: esa jornada cerrada cuenta la actividad como
    continuada, así que marcarla no puede dejarla sin condiciones de cierre."""
    cliente, csrf = sesion
    assert avanzar(cliente, csrf, actividad, iso(-8), "En progreso", "Antes del origen").status_code == 201
    assert cerrar(cliente, csrf, iso(-8)).status_code == 200
    r = marcar(cliente, csrf, actividad)
    assert r.status_code == 409 and r.json()["codigo"] == "MARCA_INVALIDARIA_CIERRE"
    assert r.json()["detalles"][0]["fecha_laboral"] == iso(-8)
    assert fila_actividad(actividad).registrada_por_error is False


# ============================== revertir (M3-06: CA-122, CA-123, CA-290) ====================================

def test_revertir_devuelve_la_actividad_a_las_vistas_operativas(sesion, actividad, esc):
    cliente, csrf = sesion
    marcar(cliente, csrf, actividad, "Duplicada")
    r = revertir(cliente, csrf, actividad)
    assert r.status_code == 200 and set(r.json()) == {"actividad"}
    assert r.json()["actividad"]["id"] == actividad and r.json()["actividad"]["marca_error"] is None
    fila = fila_actividad(actividad)
    assert (fila.registrada_por_error, fila.motivo_error, fila.marcada_por, fila.marcada_en) == (False, None, None, None)
    assert [e["id"] for e in cliente.get(f"{API}/mi/actividades").json()["elementos"]] == [actividad]    # CA-122
    assert cliente.get(f"{API}/mi/actividades/{actividad}").json()["actividad"]["marca_error"] is None


def test_sin_marca_vigente_no_hay_nada_que_revertir(sesion, actividad):
    cliente, csrf = sesion
    antes = total_auditoria()
    r = revertir(cliente, csrf, actividad)
    assert r.status_code == 409 and r.json()["codigo"] == "MARCA_NO_VIGENTE"
    marcar(cliente, csrf, actividad)
    assert revertir(cliente, csrf, actividad).status_code == 200
    r2 = revertir(cliente, csrf, actividad)
    assert r2.status_code == 409 and r2.json()["codigo"] == "MARCA_NO_VIGENTE"
    assert total_auditoria() == antes + 2


def test_revertir_no_exige_motivo_ni_cuerpo(sesion, actividad):
    cliente, csrf = sesion
    marcar(cliente, csrf, actividad)
    assert revertir(cliente, csrf, actividad).status_code == 200


def test_la_jornada_cerrada_sigue_cerrada_y_la_actividad_vuelve_a_contar(sesion):
    """CA-290: revertir no reabre ni invalida la jornada y la actividad recupera su papel en el cierre."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-6), "A")
    planificar_actividad(cliente, csrf, iso(-6), "B")
    assert cerrar(cliente, csrf, iso(-6)).status_code == 200
    assert marcar(cliente, csrf, a).status_code == 200
    antes = filas("select estado, cerrada_en, modificada_en from bitacora")[0]
    assert revertir(cliente, csrf, a).status_code == 200
    assert tuple(filas("select estado, cerrada_en, modificada_en from bitacora")[0]) == tuple(antes)
    assert entradas("reapertura") == [] and len(entradas("reversion_marca")) == 1
    bitacora_id = filas("select id from bitacora")[0].id
    with get_owner_engine().connect() as c:
        n = c.execute(text("select count(*) from actividad where not registrada_por_error and bitacora_origen_id = :b"),
                      {"b": bitacora_id}).scalar_one()
    assert n == 2


def test_tras_revertir_se_admiten_de_nuevo_avances_y_otra_marca(sesion, actividad):
    cliente, csrf = sesion
    marcar(cliente, csrf, actividad, "Primera")
    revertir(cliente, csrf, actividad)
    assert avanzar(cliente, csrf, actividad, iso(-3), "En progreso", "De nuevo").status_code == 201
    # ahora tiene un avance posterior: ya no procede marcarla
    assert marcar(cliente, csrf, actividad, "Segunda").json()["codigo"] == "MARCA_NO_PROCEDE"


def test_un_segundo_ciclo_de_marca_y_reversion_es_valido_y_queda_auditado(sesion, actividad):
    cliente, csrf = sesion
    for motivo in ("Primera", "Segunda"):
        assert marcar(cliente, csrf, actividad, motivo).status_code == 200
        assert revertir(cliente, csrf, actividad).status_code == 200
    assert [e.motivo for e in entradas()] == ["Primera", "Segunda"] and len(entradas("reversion_marca")) == 2
    assert foto_de_registros()[1] == 1


def test_revertir_no_cambia_el_estado_actual_ni_los_avances(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-6), "Bloqueada", "Esperando", "Sin acceso")
    marcar(cliente, csrf, actividad)
    avances = filas("select * from avance order by id")
    d = revertir(cliente, csrf, actividad).json()["actividad"]
    assert d["estado_actual"] == "Bloqueada" and filas("select * from avance order by id") == avances


# ============================== auditoría (CA-122, IR-35, IR-36) ============================================

def test_marcar_deja_una_unica_entrada_con_motivo_autor_y_jornada_de_origen(sesion, actividad, esc):
    cliente, csrf = sesion
    antes = total_auditoria()
    marcar(cliente, csrf, actividad, "Se registró por error")
    nuevas = filas("select * from auditoria order by momento, id")[antes:]
    assert len(nuevas) == 1
    e = nuevas[0]
    assert (e.operacion, e.tipo_objeto, e.objeto_id, e.tipo_autor, e.autor_persona_id) == (
        "marca_error", "actividad", uuid.UUID(actividad), "persona", esc.persona)
    assert e.propietaria_registro_id == esc.persona
    assert e.fecha_laboral_registro == hoy() - timedelta(days=6)                                         # IR-36
    assert e.motivo == "Se registró por error"
    assert e.valor_anterior["marca_error"] is None
    assert e.valor_nuevo["marca_error"]["motivo"] == "Se registró por error"
    assert e.valor_nuevo["marca_error"]["marcada_por"] == str(esc.persona)
    assert e.valor_nuevo["marca_error"]["marcada_en"].endswith("Z")


def test_la_entrada_pertenece_a_la_jornada_de_origen_aunque_la_marca_sea_de_hoy(sesion, esc):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    marcar(cliente, csrf, a)
    assert entradas()[0].fecha_laboral_registro == hoy()                                                  # siempre se audita
    b = planificar_actividad(cliente, csrf, iso(-4), "Pasada")
    marcar(cliente, csrf, b)
    assert entradas()[1].fecha_laboral_registro == hoy() - timedelta(days=4)


def test_revertir_deja_una_unica_entrada_con_la_marca_anterior(sesion, actividad, esc):
    cliente, csrf = sesion
    marcar(cliente, csrf, actividad, "Duplicada")
    marca = fila_actividad(actividad)
    antes = total_auditoria()
    revertir(cliente, csrf, actividad)
    nuevas = filas("select * from auditoria order by momento, id")[antes:]
    assert len(nuevas) == 1
    e = nuevas[0]
    assert (e.operacion, e.tipo_objeto, e.objeto_id, e.autor_persona_id, e.motivo) == (
        "reversion_marca", "actividad", uuid.UUID(actividad), esc.persona, None)
    assert e.valor_anterior["marca_error"]["motivo"] == "Duplicada"                                       # CA-122
    assert e.valor_anterior["marca_error"]["marcada_por"] == str(esc.persona)
    assert e.valor_nuevo["marca_error"] is None
    assert e.fecha_laboral_registro == hoy() - timedelta(days=6)
    assert marca.marcada_en is not None


def test_la_auditoria_no_se_borra_ni_se_reescribe_al_revertir(sesion, actividad):
    cliente, csrf = sesion
    marcar(cliente, csrf, actividad, "Duplicada")
    primera = tuple(entradas()[0])
    revertir(cliente, csrf, actividad)
    assert tuple(entradas()[0]) == primera and len(entradas()) == 1                                       # CA-120


def test_un_rechazo_no_deja_entrada_de_auditoria(sesion, actividad):
    cliente, csrf = sesion
    marcar(cliente, csrf, actividad, motivo=None)                       # sin motivo
    revertir(cliente, csrf, actividad)                                   # sin marca vigente
    avanzar(cliente, csrf, actividad, iso(-3))                           # avance válido de M2-05 (se audita aparte)
    marcar(cliente, csrf, actividad)                                     # con avance posterior
    assert entradas("marca_error") == [] and entradas("reversion_marca") == []


# ============================== idempotencia (T-04) y atomicidad ============================================

def test_la_cabecera_idempotency_key_es_obligatoria(sesion, actividad):
    cliente, csrf = sesion
    r = marcar(cliente, csrf, actividad, clave=None)
    assert r.status_code == 400 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_OBLIGATORIA"
    assert fila_actividad(actividad).registrada_por_error is False
    marcar(cliente, csrf, actividad)
    r = revertir(cliente, csrf, actividad, clave=None)
    assert r.status_code == 400 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_OBLIGATORIA"


def test_repetir_la_misma_marca_con_la_misma_clave_no_duplica(sesion, actividad):
    cliente, csrf = sesion
    r1 = marcar(cliente, csrf, actividad, "Duplicada", clave="k-marca")
    r2 = marcar(cliente, csrf, actividad, "Duplicada", clave="k-marca")
    assert (r1.status_code, r2.status_code) == (200, 200) and r2.json() == r1.json()
    assert r2.headers.get("idempotency-replayed") == "true" and "idempotency-replayed" not in r1.headers
    assert len(entradas()) == 1


def test_repetir_la_misma_reversion_con_la_misma_clave_no_duplica(sesion, actividad):
    cliente, csrf = sesion
    marcar(cliente, csrf, actividad)
    r1 = revertir(cliente, csrf, actividad, clave="k-rev")
    r2 = revertir(cliente, csrf, actividad, clave="k-rev")
    assert (r1.status_code, r2.status_code) == (200, 200) and r2.json() == r1.json()
    assert r2.headers.get("idempotency-replayed") == "true" and len(entradas("reversion_marca")) == 1
    assert fila_actividad(actividad).registrada_por_error is False


def test_reutilizar_la_clave_con_otro_motivo_se_rechaza(sesion, actividad):
    cliente, csrf = sesion
    marcar(cliente, csrf, actividad, "Uno", clave="k-misma")
    r = marcar(cliente, csrf, actividad, "Otro", clave="k-misma")
    assert r.status_code == 422 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_REUTILIZADA"
    assert fila_actividad(actividad).motivo_error == "Uno"


def test_una_peticion_rechazada_no_consume_la_clave(sesion, actividad):
    cliente, csrf = sesion
    assert marcar(cliente, csrf, actividad, motivo=None, clave="k-corregible").status_code == 422
    assert marcar(cliente, csrf, actividad, "Ahora sí", clave="k-corregible").status_code == 200


def test_si_falla_el_guardado_no_queda_ni_la_marca_ni_la_clave(sesion, actividad, monkeypatch):
    cliente, csrf = sesion
    antes = (total_auditoria(), contar("clave_idempotencia"))

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado de la auditoría")

    monkeypatch.setattr(servicio, "registrar_operacion_de_persona", falla)
    r = marcar(cliente, csrf, actividad, clave="k-atomica")
    assert r.status_code == 500 and "fallo simulado" not in r.text
    assert (total_auditoria(), contar("clave_idempotencia")) == antes
    fila = fila_actividad(actividad)
    assert (fila.registrada_por_error, fila.motivo_error, fila.marcada_por, fila.marcada_en) == (False, None, None, None)
    monkeypatch.undo()
    assert marcar(cliente, csrf, actividad, clave="k-atomica").status_code == 200


def test_si_falla_la_reversion_la_marca_sigue_vigente(sesion, actividad, monkeypatch):
    cliente, csrf = sesion
    marcar(cliente, csrf, actividad, "Duplicada")
    antes = (total_auditoria(), contar("clave_idempotencia"))

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado de la auditoría")

    monkeypatch.setattr(servicio, "registrar_operacion_de_persona", falla)
    assert revertir(cliente, csrf, actividad, clave="k-atomica-rev").status_code == 500
    assert (total_auditoria(), contar("clave_idempotencia")) == antes
    fila = fila_actividad(actividad)
    assert fila.registrada_por_error is True and fila.motivo_error == "Duplicada" and fila.marcada_en is not None
    monkeypatch.undo()
    assert revertir(cliente, csrf, actividad, clave="k-atomica-rev").status_code == 200


# ============================== concurrencia: marcar, revertir, cerrar y registrar =========================

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


def test_marcas_simultaneas_con_claves_distintas_marcan_una_sola_vez(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    clientes, csrf = _clientes(esc, 6)
    rs = _en_paralelo(6, lambda i: marcar(clientes[i], csrf, a, f"Motivo {i}"))
    assert sorted(r.status_code for r in rs) == [200] + [409] * 5
    assert {r.json()["codigo"] for r in rs if r.status_code == 409} == {"ACTIVIDAD_MARCADA_POR_ERROR"}
    assert len(entradas()) == 1 and fila_actividad(a).registrada_por_error is True


def test_la_misma_marca_simultanea_con_la_misma_clave_tiene_un_solo_efecto(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    clientes, csrf = _clientes(esc, 6)
    rs = _en_paralelo(6, lambda i: marcar(clientes[i], csrf, a, "Mismo motivo", clave="clave-concurrente"))
    assert {r.status_code for r in rs} <= {200, 409}
    assert sum(r.status_code == 200 and "idempotency-replayed" not in r.headers for r in rs) == 1
    assert len(entradas()) == 1


def test_marca_y_reversion_simultaneas_dejan_un_estado_coherente(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    marcar(cliente, csrf0, a, "Inicial")
    clientes, csrf = _clientes(esc, 6)
    _en_paralelo(6, lambda i: revertir(clientes[i], csrf, a) if i % 2 else marcar(clientes[i], csrf, a, f"M{i}"))
    fila = fila_actividad(a)
    vigente = fila.registrada_por_error
    assert (fila.motivo_error is not None) == vigente and (fila.marcada_en is not None) == vigente
    # Cada operación efectiva dejó exactamente una entrada y se alternan: marcas menos reversiones es 1 si la
    # marca está vigente y 0 si no (no se ordena por ``momento``: es el inicio de la transacción, no su confirmación)
    marcas = len(entradas("marca_error"))
    reversiones = len(entradas("reversion_marca"))
    assert marcas - reversiones == (1 if vigente else 0)


def test_dos_actividades_que_son_las_unicas_de_una_jornada_cerrada_no_se_marcan_a_la_vez(esc):
    """RN-109 con carreras: cada marca, mirada por separado, deja a la otra; juntas dejarían la jornada vacía.
    Las bitácoras afectadas se bloquean antes de comprobar el cierre, así que solo una puede prosperar."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6), "A")
    b = planificar_actividad(cliente, csrf0, iso(-6), "B")
    assert cerrar(cliente, csrf0, iso(-6)).status_code == 200
    clientes, csrf = _clientes(esc, 2)
    rs = _en_paralelo(2, lambda i: marcar(clientes[i], csrf, (a, b)[i]))
    assert sorted(r.status_code for r in rs) == [200, 409]
    assert [r.json()["codigo"] for r in rs if r.status_code == 409] == ["MARCA_INVALIDARIA_CIERRE"]
    validas = filas("select count(*) as n from actividad where not registrada_por_error")[0].n
    assert validas == 1 and filas("select estado from bitacora")[0].estado == "cerrada"


def test_marcar_espera_a_quien_tiene_la_jornada_bloqueada_y_ve_su_cierre(esc):
    """Determinista: otra transacción tiene bloqueada la bitácora de origen (como un cierre en curso). La marca
    debe ESPERAR y, al liberarse, ver la jornada ya cerrada y rechazarse (MARCA_INVALIDARIA_CIERRE)."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    cliente.put(f"{API}/mi/bitacoras/{iso(-6)}/resumen", json={"resumen": "Hecho"}, headers=con_clave(csrf0, None))
    clientes, csrf = _clientes(esc, 1)
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(marcar(clientes[0], csrf, a)))
    with get_owner_engine().begin() as c:
        c.execute(text("select 1 from bitacora for update"))
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "la marca debía esperar al bloqueo de la jornada"
        c.execute(text("update bitacora set estado = 'cerrada', cerrada_en = now()"))
    hilo.join(timeout=15)
    r = resultado[0]
    assert r.status_code == 409 and r.json()["codigo"] == "MARCA_INVALIDARIA_CIERRE"
    assert fila_actividad(a).registrada_por_error is False and entradas() == []


def test_cerrar_espera_a_quien_marca_y_ve_la_actividad_ya_marcada(esc):
    """Determinista y en sentido contrario: una marca confirmada antes de que el cierre cuente las actividades
    hace que el cierre no la cuente (CONDICIONES_DE_CIERRE_NO_CUMPLIDAS)."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    cliente.put(f"{API}/mi/bitacoras/{iso(-6)}/resumen", json={"resumen": "Hecho"}, headers=con_clave(csrf0, None))
    clientes, csrf = _clientes(esc, 1)
    resultado = []
    hilo = threading.Thread(
        target=lambda: resultado.append(clientes[0].post(f"{API}/mi/bitacoras/{iso(-6)}/cierre", headers=con_clave(csrf))))
    with get_owner_engine().begin() as c:
        c.execute(text("select 1 from bitacora for update"))
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "el cierre debía esperar al bloqueo de la jornada"
        c.execute(text("update actividad set registrada_por_error = true, motivo_error = 'x', "
                       "marcada_por = propietaria_id, marcada_en = now() where id = :a"), {"a": a})
    hilo.join(timeout=15)
    r = resultado[0]
    assert r.status_code == 409 and r.json()["codigo"] == "CONDICIONES_DE_CIERRE_NO_CUMPLIDAS"
    assert filas("select estado from bitacora")[0].estado == "abierta"


def test_marcar_y_cerrar_simultaneos_nunca_dejan_una_jornada_cerrada_sin_actividad_valida(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    cliente.put(f"{API}/mi/bitacoras/{iso(-6)}/resumen", json={"resumen": "Hecho"}, headers=con_clave(csrf0, None))
    clientes, csrf = _clientes(esc, 2)
    rs = _en_paralelo(2, lambda i: marcar(clientes[0], csrf, a) if i == 0 else
                      clientes[1].post(f"{API}/mi/bitacoras/{iso(-6)}/cierre", headers=con_clave(csrf)))
    assert sorted(r.status_code for r in rs) == [200, 409]            # exactamente una de las dos prospera
    cerrada = filas("select estado from bitacora")[0].estado == "cerrada"
    validas = filas("select count(*) as n from actividad where not registrada_por_error")[0].n
    assert not (cerrada and validas == 0)


def test_una_marca_espera_a_quien_tiene_la_actividad_bloqueada_y_ve_sus_avances(esc):
    """Determinista: otra transacción tiene la actividad bloqueada y le añade un avance en una jornada posterior.
    La marca debe esperar y, al liberarse, rechazarse (MARCA_NO_PROCEDE)."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    clientes, csrf = _clientes(esc, 1)
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(marcar(clientes[0], csrf, a)))
    with get_owner_engine().begin() as c:
        c.execute(text("select 1 from actividad where id = :a for update"), {"a": a})
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "la marca debía esperar al bloqueo de la actividad"
        b = c.execute(text("insert into bitacora (persona_id, fecha_laboral) select propietaria_id, :f from actividad "
                           "where id = :a returning id"), {"a": a, "f": hoy() - timedelta(days=3)}).scalar_one()
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                       "values (:a, :b, 'En progreso', 'Avance concurrente')"), {"a": a, "b": b})
    hilo.join(timeout=15)
    assert resultado[0].status_code == 409 and resultado[0].json()["codigo"] == "MARCA_NO_PROCEDE"
    assert fila_actividad(a).registrada_por_error is False


def test_un_avance_espera_a_quien_marca_y_ve_la_actividad_marcada(esc):
    """Determinista: una marca todavía sin confirmar tiene la actividad bloqueada. El avance espera y, al
    confirmarse, se rechaza (ACTIVIDAD_MARCADA_POR_ERROR): nunca entra un avance en una actividad marcada."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    clientes, csrf = _clientes(esc, 1)
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(avanzar(clientes[0], csrf, a, iso(-3))))
    with get_owner_engine().begin() as c:
        c.execute(text("update actividad set registrada_por_error = true, motivo_error = 'x', "
                       "marcada_por = propietaria_id, marcada_en = now() where id = :a"), {"a": a})
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "el avance debía esperar a la marca en curso"
    hilo.join(timeout=15)
    assert resultado[0].status_code == 409 and resultado[0].json()["codigo"] == "ACTIVIDAD_MARCADA_POR_ERROR"
    assert contar("avance") == 0


def test_marcas_simultaneas_de_actividades_de_distintas_jornadas_no_se_bloquean_entre_si(esc):
    """Sin bloqueos cruzados: marcas de actividades distintas con avances anteriores al origen en jornadas
    compartidas terminan siempre (el orden de bloqueo es fijo)."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6), "A")
    b = planificar_actividad(cliente, csrf0, iso(-7), "B")
    avanzar(cliente, csrf0, a, iso(-7), "En progreso", "Antes")
    avanzar(cliente, csrf0, b, iso(-8), "En progreso", "Antes")
    otra = planificar_actividad(cliente, csrf0, iso(-7), "Otra")
    assert otra
    clientes, csrf = _clientes(esc, 2)
    rs = _en_paralelo(2, lambda i: marcar(clientes[i], csrf, (a, b)[i]))
    assert all(r.status_code in (200, 409) for r in rs)


# ============================== integración con M2 y M3 =====================================================

def test_la_marca_convive_con_el_flujo_completo_de_la_jornada(sesion):
    """Planificar, avanzar, cerrar, marcar una de varias, reabrir, revertir y volver a cerrar."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-5), "A")
    b = planificar_actividad(cliente, csrf, iso(-5), "B")
    avanzar(cliente, csrf, b, iso(-5), "Completada", "Hecho")
    assert cerrar(cliente, csrf, iso(-5)).status_code == 200
    assert marcar(cliente, csrf, a, "Error de alta").status_code == 200
    d = cliente.get(f"{API}/mi/bitacoras/{iso(-5)}").json()
    assert d["bitacora"]["estado"] == "cerrada" and {x["id"] for x in d["actividades"]} == {a, b}
    assert revertir(cliente, csrf, a).status_code == 200
    assert {e["id"] for e in cliente.get(f"{API}/mi/actividades").json()["elementos"]} == {a, b}
    assert [e.operacion for e in filas("select operacion from auditoria where operacion in "
                                       "('marca_error', 'reversion_marca') order by momento, id")] == [
        "marca_error", "reversion_marca"]


def test_los_no_planificados_y_los_completados_siguen_las_mismas_reglas(sesion):
    cliente, csrf = sesion
    n = cliente.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf),
                     json={"fecha_laboral": iso(-2), "titulo": "Imprevisto", "estado": "En progreso",
                           "descripcion": "Atendí"}).json()["actividad"]["id"]
    assert marcar(cliente, csrf, n).status_code == 200            # su primer avance es de la jornada de origen
    assert [e["id"] for e in cliente.get(f"{API}/mi/actividades").json()["elementos"]] == []
    assert revertir(cliente, csrf, n).status_code == 200
