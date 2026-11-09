"""T7 — M2-04: planificar la continuación de una actividad propia (PostgreSQL real, por HTTP).

Criterios: CA-179 a CA-186, CA-209, CA-210 (la reactivación es M3-04: aquí una Completada siempre se
rechaza), RN-46, RN-75, RN-76, RN-78, IR-14, IR-16 e IR-17, y las reglas D-01, D-03 y T-04. Una
continuación es una PLANIFICACIÓN: no crea avances, no cambia el estado y no audita. Las pruebas
destructivas corren solo sobre ``smartwork_test``.
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


def continuar(cliente, csrf, actividad_id, fecha=None, descripcion="Seguir con la revisión", clave="__auto__", **extra):
    """M2-04. ``descripcion=None`` omite el campo."""
    cuerpo = {"fecha_laboral": iso(3) if fecha is None else fecha}
    if descripcion is not None:
        cuerpo["descripcion"] = descripcion
    return cliente.post(f"{API}/mi/actividades/{actividad_id}/continuaciones-planificadas",
                        json={**cuerpo, **extra}, headers=con_clave(csrf, clave))


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c, desde=hoy() - timedelta(days=400))


@pytest.fixture()
def sesion(esc):
    return sesion_iniciada(esc)


@pytest.fixture()
def actividad(sesion):
    cliente, csrf = sesion
    return planificar_actividad(cliente, csrf, iso(0))


def coherente() -> bool:
    with get_owner_engine().connect() as c:
        return estados_actuales_incoherentes(c) == []


# ============================== crear la continuación (CA-179, CA-180) ======================================

def test_registra_la_continuacion_sin_crear_otra_actividad_ni_un_avance(sesion, actividad):
    cliente, csrf = sesion
    r = continuar(cliente, csrf, actividad, iso(3), "Cerrar las cifras del informe")
    assert r.status_code == 201
    d = r.json()
    assert set(d) == {"planificacion", "actividad", "bitacora_creada"} and d["bitacora_creada"] is True
    p, a = d["planificacion"], d["actividad"]
    assert (p["tipo"], p["fecha_laboral"], p["descripcion"], p["actividad_id"]) == (
        "continuacion", iso(3), "Cerrar las cifras del informe", actividad)
    assert p["clase"] == "vigente" and a["id"] == actividad                                   # CA-179: es la misma actividad
    assert (contar("actividad"), contar("avance")) == (1, 0)                                   # ni otra actividad ni un avance
    assert contar("planificacion") == 2                                                        # la original y la continuación


def test_el_estado_actual_no_cambia_al_planificar(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(0), "En progreso")
    r = continuar(cliente, csrf, actividad, iso(2))
    assert r.json()["actividad"]["estado_actual"] == "En progreso"                              # CA-180
    assert filas("select estado_actual from actividad")[0].estado_actual == "En progreso"
    assert coherente()


@pytest.mark.parametrize("estado,motivo", [("Pendiente", None), ("En progreso", None), ("Bloqueada", "Falta acceso")])
def test_se_admite_en_cualquier_estado_no_completado_sin_cambiarlo(sesion, actividad, estado, motivo):
    cliente, csrf = sesion
    if estado != "Pendiente":
        avanzar(cliente, csrf, actividad, iso(0), estado, motivo_bloqueo=motivo)
    assert continuar(cliente, csrf, actividad, iso(5)).status_code == 201
    assert filas("select estado_actual from actividad")[0].estado_actual == estado


def test_la_continuacion_no_forma_parte_de_la_secuencia_ni_del_estado(sesion, actividad):
    cliente, csrf = sesion
    continuar(cliente, csrf, actividad, iso(4), "Prevista")
    d = cliente.get(f"{API}/mi/actividades/{actividad}").json()
    assert d["avances"] == [] and d["estado_actual"] == "Pendiente"                            # CA-181, CA-186
    assert [(c["tipo"], c["fecha_laboral"], c["descripcion"]) for c in d["continuaciones_planificadas"]] == [
        ("continuacion", iso(4), "Prevista")]
    assert d["planificacion_original"]["tipo"] == "original" and d["planificacion_original"]["fecha_laboral"] == iso(0)
    avanzar(cliente, csrf, actividad, iso(0), "En progreso")
    d = cliente.get(f"{API}/mi/actividades/{actividad}").json()
    assert d["estado_actual"] == "En progreso" and len(d["avances"]) == 1                       # CA-185


def test_la_planificacion_original_no_cambia(sesion, actividad):
    cliente, csrf = sesion
    antes = cliente.get(f"{API}/mi/actividades/{actividad}").json()["planificacion_original"]
    continuar(cliente, csrf, actividad, iso(3))
    assert cliente.get(f"{API}/mi/actividades/{actividad}").json()["planificacion_original"] == antes


def test_la_jornada_futura_la_muestra_como_planificacion_de_esa_actividad(sesion, actividad):
    cliente, csrf = sesion
    continuar(cliente, csrf, actividad, iso(3), "Para el jueves")
    b = cliente.get(f"{API}/mi/bitacoras/{iso(3)}").json()
    assert [(p["tipo"], p["descripcion"]) for p in b["planificaciones"]] == [("continuacion", "Para el jueves")]
    assert [x["id"] for x in b["actividades"]] == [actividad] and b["avances"] == []
    assert b["bitacora"]["clase_jornada"] == "futura" and b["actividades"][0]["fecha_laboral_origen"] == iso(0)


def test_una_actividad_no_planificada_tambien_puede_continuarse(sesion):
    cliente, csrf = sesion
    a = cliente.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf),
                     json={"fecha_laboral": iso(0), "titulo": "Imprevisto", "estado": "En progreso", "descripcion": "Empecé"}
                     ).json()["actividad"]["id"]
    assert continuar(cliente, csrf, a, iso(2)).status_code == 201
    assert contar("actividad") == 1 and contar("planificacion") == 1                           # solo la continuación (no tiene original)


def test_dos_continuaciones_con_claves_distintas_son_dos_intenciones(sesion, actividad):
    cliente, csrf = sesion
    continuar(cliente, csrf, actividad, iso(3), "Primera parte")
    continuar(cliente, csrf, actividad, iso(3), "Segunda parte")
    continuar(cliente, csrf, actividad, iso(6), "Otra jornada")
    assert contar("planificacion") == 4 and contar("actividad") == 1                           # las continuaciones son varias (IR-16)
    d = cliente.get(f"{API}/mi/actividades/{actividad}").json()
    assert [c["fecha_laboral"] for c in d["continuaciones_planificadas"]] == [iso(3), iso(3), iso(6)]


def test_planificar_una_continuacion_no_impide_registrar_avances_ni_completar(sesion, actividad):
    cliente, csrf = sesion
    continuar(cliente, csrf, actividad, iso(3))
    assert avanzar(cliente, csrf, actividad, iso(0), "Completada", "Terminé").status_code == 201
    assert filas("select estado_actual from actividad")[0].estado_actual == "Completada"


# ============================== fechas (RN-76) =============================================================

@pytest.mark.parametrize("dias", [1, 2, 30, 365])
def test_se_acepta_cualquier_fecha_posterior_a_la_actual_cubierta(sesion, actividad, dias):
    cliente, csrf = sesion
    r = continuar(cliente, csrf, actividad, iso(dias))
    assert r.status_code == 201 and r.json()["planificacion"]["fecha_laboral"] == iso(dias)


@pytest.mark.parametrize("dias", [0, -1, -30])
def test_la_fecha_de_hoy_o_pasada_no_es_una_fecha_futura(sesion, actividad, dias):
    cliente, csrf = sesion
    r = continuar(cliente, csrf, actividad, iso(dias))
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_NO_FUTURA"                    # RN-76
    assert contar("planificacion") == 1 and contar("bitacora") == 1                            # nada nuevo; solo la jornada de origen


def test_la_fecha_futura_debe_estar_cubierta_por_una_pertenencia(sesion, esc, actividad):
    cliente, csrf = sesion
    with get_owner_engine().begin() as c:    # la pertenencia termina dentro de 10 días
        c.execute(text("update pertenencia set hasta_exclusivo = :h where persona_id = :p"),
                  {"h": hoy() + timedelta(days=10), "p": esc.persona})
    assert continuar(cliente, csrf, actividad, iso(9)).status_code == 201
    r = continuar(cliente, csrf, actividad, iso(20))
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_NO_CUBIERTA"
    assert contar("planificacion") == 2 and contar("bitacora") == 2


@pytest.mark.parametrize("fecha", ["mañana", "2026-13-45", "01-01-2030", "", None])
def test_una_fecha_con_formato_incorrecto_o_ausente_es_una_solicitud_invalida(sesion, actividad, fecha):
    cliente, csrf = sesion
    cuerpo = {"descripcion": "x"} if fecha is None else {"fecha_laboral": fecha, "descripcion": "x"}
    r = cliente.post(f"{API}/mi/actividades/{actividad}/continuaciones-planificadas", json=cuerpo, headers=con_clave(csrf))
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert contar("planificacion") == 1


# ============================== actividad completada o marcada (RN-78, IR-17) ===============================

def test_una_actividad_completada_no_se_continua_sin_reactivarla(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(0), "Completada", "Terminé")
    r = continuar(cliente, csrf, actividad, iso(3))
    assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_COMPLETADA"              # CA-209
    assert contar("planificacion") == 1 and contar("bitacora") == 1


def test_una_completada_por_un_avance_retroactivo_posterior_a_otro_no_la_bloquea(sesion, actividad):
    """CA-78: un avance Completada retroactivo anterior a uno posterior En progreso no cambia el estado
    actual, así que la actividad no está Completada y puede continuarse."""
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-1), "En progreso", "Martes")
    avanzar(cliente, csrf, actividad, iso(-2), "Completada", "Lunes")
    assert filas("select estado_actual from actividad")[0].estado_actual == "En progreso"
    assert continuar(cliente, csrf, actividad, iso(3)).status_code == 201


def test_una_actividad_marcada_por_error_no_se_continua(sesion, actividad):
    cliente, csrf = sesion
    with get_owner_engine().begin() as c:    # la marca es M3-05: se prepara por SQL
        c.execute(text("update actividad set registrada_por_error = true, motivo_error = 'x', "
                       "marcada_por = propietaria_id, marcada_en = now()"))
    r = continuar(cliente, csrf, actividad, iso(3))
    assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_MARCADA_POR_ERROR"
    assert contar("planificacion") == 1


# ============================== autorización y visibilidad (T-01, CA-183) ===================================

def _otra_persona(identificador="otra.persona"):
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        otra = crear_persona(c, "Otra persona")
        crear_pertenencia(c, otra, crear_equipo(c, org, "Otro equipo"), desde=hoy() - timedelta(days=50))
        crear_identidad(c, otra, identificador, "contraseña-de-prueba-123")
    cliente = nuevo_cliente()
    r = iniciar_sesion(cliente, identificador, "contraseña-de-prueba-123")
    return cliente, r.json()["csrf_token"]


def test_no_se_planifica_la_continuacion_de_la_actividad_de_otra_persona(sesion, actividad):
    ajeno, csrf_ajeno = _otra_persona()
    r = continuar(ajeno, csrf_ajeno, actividad, iso(3), "Intento ajeno")
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"              # CA-183
    assert contar("planificacion") == 1 and contar("bitacora") == 1


def test_una_actividad_ajena_y_una_inexistente_tienen_la_misma_respuesta(sesion, actividad):
    ajeno, csrf_ajeno = _otra_persona()
    ajena = continuar(ajeno, csrf_ajeno, actividad, iso(3))
    inexistente = continuar(ajeno, csrf_ajeno, str(uuid.uuid4()), iso(3))
    assert (ajena.status_code, ajena.json()) == (inexistente.status_code, inexistente.json())   # T-01


def test_la_visibilidad_se_evalua_antes_que_el_cuerpo(sesion, actividad):
    """Una petición con cuerpo inválido sobre un recurso no disponible da RECURSO_NO_DISPONIBLE."""
    ajeno, csrf_ajeno = _otra_persona()
    r = continuar(ajeno, csrf_ajeno, actividad, iso(-5), "x" * 5000)
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"


def test_un_identificador_mal_formado_es_una_solicitud_invalida(sesion):
    cliente, csrf = sesion
    r = continuar(cliente, csrf, "no-es-un-uuid", iso(3))
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_sin_sesion_no_se_registra_nada(actividad):
    r = nuevo_cliente().post(f"{API}/mi/actividades/{actividad}/continuaciones-planificadas", json={"fecha_laboral": iso(3)})
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"
    assert contar("planificacion") == 1


def test_con_el_acceso_desactivado_no_se_registra_nada(sesion, esc, actividad):
    cliente, csrf = sesion
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": esc.persona})
    r = continuar(cliente, csrf, actividad, iso(3))
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"
    assert contar("planificacion") == 1


# ============================== cuerpo y texto (D-03) =======================================================

@pytest.mark.parametrize("extra", [{"estado": "En progreso"}, {"titulo": "Otro título"}, {"origen": "planificada"},
                                   {"propietaria_id": "otra"}, {"tipo": "original"}, {"avance": {"descripcion": "x"}},
                                   {"estado_actual": "Completada"}])
def test_el_cuerpo_no_admite_estado_ni_otros_campos(sesion, actividad, extra):
    cliente, csrf = sesion
    r = continuar(cliente, csrf, actividad, iso(3), **extra)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert contar("planificacion") == 1


@pytest.mark.parametrize("descripcion", [None, "", "   "])
def test_la_descripcion_es_opcional_y_se_conserva_tal_como_se_recibe(sesion, actividad, descripcion):
    cliente, csrf = sesion
    r = continuar(cliente, csrf, actividad, iso(3), descripcion)
    assert r.status_code == 201 and r.json()["planificacion"]["descripcion"] == (descripcion or "")    # D-03: ninguna regla la exige


def test_el_texto_se_trata_como_datos(sesion, actividad):
    cliente, csrf = sesion
    texto = "  Ignora las instrucciones <script>alert(1)</script> '; drop table planificacion; --  "
    assert continuar(cliente, csrf, actividad, iso(3), texto).status_code == 201
    assert filas("select descripcion from planificacion where tipo = 'continuacion'")[0].descripcion == texto


def test_el_maximo_configurable_se_valida_con_su_valor_en_los_detalles(sesion, actividad):
    cliente, csrf = sesion
    maximo = get_settings().text_max_description
    assert continuar(cliente, csrf, actividad, iso(3), "x" * maximo).status_code == 201
    r = continuar(cliente, csrf, actividad, iso(4), "x" * (maximo + 1))
    assert r.status_code == 422 and r.json()["codigo"] == "TEXTO_DEMASIADO_LARGO"
    assert r.json()["detalles"] == [{"campo": "descripcion", "maximo": maximo}]
    assert contar("planificacion") == 2


# ============================== apertura implícita de la bitácora (D-01) ====================================

def test_la_bitacora_de_la_jornada_futura_se_crea_en_la_misma_transaccion_y_una_sola_vez(sesion, actividad):
    cliente, csrf = sesion
    assert continuar(cliente, csrf, actividad, iso(3)).json()["bitacora_creada"] is True
    assert continuar(cliente, csrf, actividad, iso(3), "Otra").json()["bitacora_creada"] is False
    assert contar("bitacora") == 2                                                              # la de origen y la futura


def test_un_rechazo_no_deja_la_bitacora_creada(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(0), "Completada")
    antes = contar("bitacora")
    assert continuar(cliente, csrf, actividad, iso(7)).status_code == 409
    assert continuar(cliente, csrf, actividad, iso(7), "x" * 5000).status_code == 422
    assert contar("bitacora") == antes


# ============================== auditoría ====================================================================

def test_planificar_una_continuacion_no_deja_entrada_de_auditoria(sesion, actividad):
    cliente, csrf = sesion
    continuar(cliente, csrf, actividad, iso(3))
    continuar(cliente, csrf, actividad, iso(9), "Otra")
    assert contar("auditoria") == 0                                                              # no modifica una jornada pasada


# ============================== idempotencia (T-04) ==========================================================

def test_la_cabecera_idempotency_key_es_obligatoria(sesion, actividad):
    cliente, csrf = sesion
    r = continuar(cliente, csrf, actividad, iso(3), clave=None)
    assert r.status_code == 400 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_OBLIGATORIA"
    assert contar("planificacion") == 1


def test_repetir_la_misma_peticion_con_la_misma_clave_no_duplica_la_continuacion(sesion, actividad):
    cliente, csrf = sesion
    primera = continuar(cliente, csrf, actividad, iso(3), "Igual", clave="k-1")
    segunda = continuar(cliente, csrf, actividad, iso(3), "Igual", clave="k-1")
    assert primera.status_code == segunda.status_code == 201
    assert segunda.headers["idempotency-replayed"] == "true" and segunda.json() == primera.json()
    assert contar("planificacion") == 2


def test_reutilizar_la_clave_con_otra_peticion_se_rechaza(sesion, actividad):
    cliente, csrf = sesion
    continuar(cliente, csrf, actividad, iso(3), "Uno", clave="k-2")
    r = continuar(cliente, csrf, actividad, iso(4), "Uno", clave="k-2")
    assert r.status_code == 422 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_REUTILIZADA"
    assert contar("planificacion") == 2


def test_una_peticion_rechazada_no_consume_la_clave_y_se_puede_corregir(sesion, actividad):
    cliente, csrf = sesion
    assert continuar(cliente, csrf, actividad, iso(0), clave="k-3").status_code == 422        # fecha de hoy
    assert continuar(cliente, csrf, actividad, iso(3), clave="k-3").status_code == 201
    assert contar("planificacion") == 2


# ============================== atomicidad y concurrencia ====================================================

def test_si_falla_el_guardado_no_queda_ni_la_bitacora_ni_la_clave(sesion, actividad, monkeypatch):
    cliente, csrf = sesion

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado al guardar la continuación")

    monkeypatch.setattr(servicio.repositorio, "insertar_continuacion_planificada", falla)
    antes = (contar("bitacora"), contar("planificacion"), contar("clave_idempotencia"))
    r = continuar(cliente, csrf, actividad, iso(5), clave="k-atomica")
    assert r.status_code == 500 and r.json()["codigo"] == "ERROR_INTERNO" and "fallo simulado" not in r.text
    assert (contar("bitacora"), contar("planificacion"), contar("clave_idempotencia")) == antes
    monkeypatch.undo()
    assert continuar(cliente, csrf, actividad, iso(5), clave="k-atomica").status_code == 201   # la clave puede reintentarse


def _clientes_concurrentes(esc, n):
    base, _ = sesion_iniciada(esc)
    secreto = base.cookies.get(NOMBRE_COOKIE)
    csrf = base.get(f"{API}/sesion").json()["csrf_token"]
    return [nuevo_cliente({NOMBRE_COOKIE: secreto}) for _ in range(n)], csrf


def test_la_misma_peticion_simultanea_con_la_misma_clave_crea_una_sola_continuacion(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(0))
    clientes, csrf = _clientes_concurrentes(esc, 6)
    resultados, barrera = [], threading.Barrier(6)

    def intentar(i):
        barrera.wait()
        resultados.append(continuar(clientes[i], csrf, a, iso(3), "Igual", clave="clave-concurrente"))

    hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(6)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert {r.status_code for r in resultados} <= {201, 409}
    assert sum(r.status_code == 201 and "idempotency-replayed" not in r.headers for r in resultados) == 1
    assert contar("planificacion") == 2 and contar("actividad") == 1


def test_continuaciones_simultaneas_con_claves_distintas_en_una_fecha_nueva_dejan_una_bitacora(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(0))
    clientes, csrf = _clientes_concurrentes(esc, 6)
    resultados, barrera = [], threading.Barrier(6)

    def intentar(i):
        barrera.wait()
        resultados.append(continuar(clientes[i], csrf, a, iso(4), f"Parte {i}"))

    hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(6)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert [r.status_code for r in resultados] == [201] * 6, [r.text for r in resultados if r.status_code != 201]
    assert contar("bitacora") == 2 and contar("planificacion") == 7                             # IR-01: una sola bitácora futura
    assert sum(r.json()["bitacora_creada"] for r in resultados) == 1
    assert contar("avance") == 0 and coherente()


def test_una_continuacion_espera_al_que_tiene_bloqueada_la_actividad_y_se_rechaza_si_la_completo(esc):
    """Prueba determinista de la serialización: otra transacción tiene la actividad bloqueada y la
    completa. La continuación debe ESPERAR y, al liberarse, ver la finalización y rechazarse (IR-17).
    Sin el bloqueo respondería 201 con una lectura anterior a la finalización."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(0))
    clientes, csrf = _clientes_concurrentes(esc, 1)
    resultado = []

    def registrar():
        resultado.append(continuar(clientes[0], csrf, a, iso(3), "Tras la finalización"))

    with get_owner_engine().begin() as c:
        c.execute(text("select 1 from actividad where id = :a for update"), {"a": a})
        hilo = threading.Thread(target=registrar)
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "la continuación debía esperar al bloqueo de la actividad"
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                       "select id, bitacora_origen_id, 'Completada', 'Finalizada' from actividad where id = :a"), {"a": a})
        c.execute(text("update actividad set estado_actual = 'Completada' where id = :a"), {"a": a})
    hilo.join(timeout=10)
    assert resultado and resultado[0].status_code == 409 and resultado[0].json()["codigo"] == "ACTIVIDAD_COMPLETADA"
    assert contar("planificacion") == 1 and contar("bitacora") == 1                              # nada quedó
