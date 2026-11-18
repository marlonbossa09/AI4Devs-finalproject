"""T8 — M3-01 (cerrar mi jornada) y M3-02 (reabrir mi bitácora cerrada), PostgreSQL real, por HTTP.

Criterios: CA-89 a CA-102, CA-109, CA-184, CA-266, CA-283 y CA-284; RN-10, RN-19, RN-21, RN-22, RN-46,
RN-50, RN-103, RN-108 y RN-109; D-01, D-04 y T-04. Las pruebas destructivas corren solo sobre ``smartwork_test``.
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
from tests.utiles_http import API, cabeceras, iniciar_sesion, nuevo_cliente, sesion_iniciada
from tests.utiles_m2 import avanzar, con_clave, contar, filas, iso, planificar_actividad


def cerrar(cliente, csrf, fecha=None, clave="__auto__"):
    return cliente.post(f"{API}/mi/bitacoras/{iso(0) if fecha is None else fecha}/cierre", headers=con_clave(csrf, clave))


def reabrir(cliente, csrf, fecha=None, motivo="Corregir el resumen", clave="__auto__", **extra):
    """M3-02. ``motivo=None`` omite el campo."""
    cuerpo = {} if motivo is None else {"motivo": motivo}
    return cliente.post(f"{API}/mi/bitacoras/{iso(0) if fecha is None else fecha}/reapertura",
                        json={**cuerpo, **extra}, headers=con_clave(csrf, clave))


def guardar(cliente, csrf, fecha, resumen="Hoy avancé con el informe"):
    return cliente.put(f"{API}/mi/bitacoras/{fecha}/resumen", json={"resumen": resumen}, headers=cabeceras(csrf))


def consultar(cliente, fecha):
    return cliente.get(f"{API}/mi/bitacoras/{fecha}")


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c, desde=hoy() - timedelta(days=400))


@pytest.fixture()
def sesion(esc):
    return sesion_iniciada(esc)


def lista(cliente, csrf, fecha=None, resumen="Hoy avancé con el informe", titulo="Preparar informe"):
    """Una jornada que cumple las condiciones de cierre: una actividad creada en ella y un resumen."""
    fecha = iso(0) if fecha is None else fecha
    a = planificar_actividad(cliente, csrf, fecha, titulo)
    assert guardar(cliente, csrf, fecha, resumen).status_code == 200
    return a


def estado_de(fecha):
    return filas("select estado, cerrada_en from bitacora where fecha_laboral = :f", f=fecha)[0]


def entradas(operacion):
    return filas("select * from auditoria where tipo_objeto = 'bitacora' and operacion = :o order by momento, id", o=operacion)


# ============================== cerrar: caso positivo (CA-90, CA-95) =========================================

def test_cierra_una_jornada_con_una_actividad_creada_y_un_resumen(sesion):
    cliente, csrf = sesion
    lista(cliente, csrf)
    antes = consultar(cliente, iso(0)).json()["bitacora"]
    r = cerrar(cliente, csrf)
    assert r.status_code == 200 and set(r.json()) == {"bitacora"}
    b = r.json()["bitacora"]
    assert b["estado"] == "cerrada" and b["cerrada_en"] is not None and b["fecha_laboral"] == iso(0)
    assert b["resumen"] == "Hoy avancé con el informe" and b["modificada_en"] == antes["modificada_en"]
    fila = estado_de(iso(0))
    assert fila.estado == "cerrada" and fila.cerrada_en is not None
    assert consultar(cliente, iso(0)).json()["bitacora"]["estado"] == "cerrada"


def test_deja_una_unica_entrada_de_auditoria_del_cierre(sesion, esc):
    cliente, csrf = sesion
    lista(cliente, csrf)
    b = cerrar(cliente, csrf).json()["bitacora"]
    [e] = entradas("cierre")
    assert (e.tipo_autor, e.autor_persona_id, e.propietaria_registro_id) == ("persona", esc.persona, esc.persona)
    assert e.objeto_id == uuid.UUID(b["id"]) and e.fecha_laboral_registro.isoformat() == iso(0) and e.motivo is None
    assert e.valor_anterior == {"estado": "abierta", "cerrada_en": None}
    assert e.valor_nuevo == {"estado": "cerrada", "cerrada_en": b["cerrada_en"]}
    assert e.momento is not None


def test_las_actividades_conservan_su_estado_en_los_cuatro_estados(sesion):
    cliente, csrf = sesion
    ids = {}
    for nombre in ("Pendiente", "En progreso", "Bloqueada", "Completada"):
        a = planificar_actividad(cliente, csrf, iso(0), f"Actividad {nombre}")
        if nombre != "Pendiente":
            assert avanzar(cliente, csrf, a, iso(0), nombre, "Trabajo", "Falta acceso" if nombre == "Bloqueada" else None).status_code == 201
        ids[nombre] = a
    guardar(cliente, csrf, iso(0))
    assert cerrar(cliente, csrf).status_code == 200                                         # CA-95
    for nombre, a in ids.items():
        assert filas("select estado_actual from actividad where id = :a", a=a)[0].estado_actual == nombre
    assert contar("avance") == 3 and contar("actividad") == 4                                # no se tocó nada más


def test_una_actividad_continuada_con_un_avance_de_esa_fecha_cuenta(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-3))                                         # creada otro día
    assert avanzar(cliente, csrf, a, iso(0)).status_code == 201                              # continuada hoy
    guardar(cliente, csrf, iso(0))
    assert cerrar(cliente, csrf).status_code == 200                                          # CA-91
    assert estado_de(iso(0)).estado == "cerrada" and estado_de(iso(-3)).estado == "abierta"


def test_una_actividad_no_planificada_creada_en_la_jornada_cuenta(sesion):
    cliente, csrf = sesion
    r = cliente.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf),
                     json={"fecha_laboral": iso(0), "titulo": "Imprevisto", "estado": "Completada", "descripcion": "Lo resolví"})
    assert r.status_code == 201
    guardar(cliente, csrf, iso(0))
    assert cerrar(cliente, csrf).status_code == 200


def test_se_puede_cerrar_una_jornada_pasada_y_el_cierre_sigue_auditado(sesion):
    cliente, csrf = sesion
    lista(cliente, csrf, iso(-4))
    assert cerrar(cliente, csrf, iso(-4)).status_code == 200
    assert estado_de(iso(-4)).estado == "cerrada" and len(entradas("cierre")) == 1


def test_cerrar_es_solo_manual_el_paso_del_tiempo_no_cierra(sesion):
    """CA-89: una jornada pasada que cumple todas las condiciones permanece abierta mientras no se cierre."""
    cliente, csrf = sesion
    lista(cliente, csrf, iso(-10))
    assert consultar(cliente, iso(-10)).json()["bitacora"]["estado"] == "abierta"
    assert estado_de(iso(-10)).estado == "abierta" and entradas("cierre") == []


# ============================== cerrar: condiciones (CA-92 a CA-94, CA-184, CA-283) =========================

def detalles(r):
    return {(d["campo"], d["motivo"]) for d in r.json()["detalles"]}


def test_sin_actividad_creada_ni_continuada_no_se_cierra(sesion):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(0))
    r = cerrar(cliente, csrf)
    assert r.status_code == 409 and r.json()["codigo"] == "CONDICIONES_DE_CIERRE_NO_CUMPLIDAS"
    assert detalles(r) == {("actividades", "sin_actividad_creada_ni_continuada")}           # CA-92
    assert estado_de(iso(0)).estado == "abierta" and entradas("cierre") == []


@pytest.mark.parametrize("resumen", ["", "   ", "\n\t  \n"])
def test_un_resumen_vacio_o_de_solo_espacios_no_permite_cerrar(sesion, resumen):
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(0))
    guardar(cliente, csrf, iso(0), resumen)
    r = cerrar(cliente, csrf)
    assert r.status_code == 409 and r.json()["codigo"] == "CONDICIONES_DE_CIERRE_NO_CUMPLIDAS"
    assert detalles(r) == {("resumen", "vacio")}                                              # CA-93, CA-94
    assert estado_de(iso(0)).estado == "abierta"


def test_sin_resumen_guardado_nunca_tiene_texto(sesion):
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(0))                                               # la bitácora nace con resumen vacío
    assert detalles(cerrar(cliente, csrf)) == {("resumen", "vacio")}


def test_si_falta_todo_se_informa_de_todo_a_la_vez(sesion):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(0), "  ")
    r = cerrar(cliente, csrf)
    assert detalles(r) == {("resumen", "vacio"), ("actividades", "sin_actividad_creada_ni_continuada")}


def test_una_continuacion_planificada_no_cuenta_como_actividad_continuada(sesion, esc):
    """CA-184: solo un avance de esa fecha cuenta. La continuación se prepara por SQL en una jornada que ya no es futura."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-3))
    guardar(cliente, csrf, iso(0))
    with get_owner_engine().begin() as c:
        b = c.execute(text("select id from bitacora where persona_id = :p and fecha_laboral = :f"),
                      {"p": esc.persona, "f": hoy()}).scalar_one()
        c.execute(text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) values (:a, :b, 'continuacion', 'x')"),
                  {"a": a, "b": b})
    r = cerrar(cliente, csrf)
    assert r.status_code == 409 and detalles(r) == {("actividades", "sin_actividad_creada_ni_continuada")}
    assert avanzar(cliente, csrf, a, iso(0)).status_code == 201                                # con un avance ya cuenta
    assert cerrar(cliente, csrf).status_code == 200


def marcar_por_error(actividad):
    with get_owner_engine().begin() as c:                                                      # la marca es M3-05: se prepara por SQL
        c.execute(text("update actividad set registrada_por_error = true, motivo_error = 'x', "
                       "marcada_por = propietaria_id, marcada_en = now() where id = :a"), {"a": actividad})


def test_una_actividad_marcada_por_error_no_cuenta(sesion):
    cliente, csrf = sesion
    a = lista(cliente, csrf)
    marcar_por_error(a)
    r = cerrar(cliente, csrf)
    assert r.status_code == 409 and detalles(r) == {("actividades", "sin_actividad_creada_ni_continuada")}   # CA-283
    b = planificar_actividad(cliente, csrf, iso(0), "Otra, válida")
    assert cerrar(cliente, csrf).status_code == 200 and b


def test_un_avance_sobre_una_actividad_marcada_por_error_no_cuenta_como_continuada(sesion):
    """La marca solo procede sin avances POSTERIORES al origen (M3-05), así que el avance que cuenta como
    «continuada» es uno retroactivo, anterior a la jornada de origen (PA-28 provisional)."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    assert avanzar(cliente, csrf, a, iso(-2)).status_code == 201
    guardar(cliente, csrf, iso(-2))
    marcar_por_error(a)
    r = cerrar(cliente, csrf, iso(-2))
    assert r.status_code == 409 and detalles(r) == {("actividades", "sin_actividad_creada_ni_continuada")}


def test_no_cuenta_la_actividad_de_otra_jornada_sin_avances_en_esta(sesion):
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(-2))
    guardar(cliente, csrf, iso(0))
    r = cerrar(cliente, csrf)                                                                  # la bitácora de hoy solo tiene resumen
    assert r.status_code == 409 and detalles(r) == {("actividades", "sin_actividad_creada_ni_continuada")}
    assert estado_de(iso(-2)).estado == "abierta"


# ============================== cerrar: fechas, existencia y autorización ===================================

def test_una_jornada_futura_no_se_cierra(sesion):
    cliente, csrf = sesion
    lista(cliente, csrf, iso(3))
    r = cerrar(cliente, csrf, iso(3))
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_FUTURA_NO_PERMITIDA"           # CA-97
    assert estado_de(iso(3)).estado == "abierta" and entradas("cierre") == []


def test_cerrar_no_crea_la_bitacora(sesion):
    cliente, csrf = sesion
    antes = contar("bitacora")
    r = cerrar(cliente, csrf, iso(-1))
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"                # D-01
    assert contar("bitacora") == antes and entradas("cierre") == []


def _otra_persona(identificador="otra.persona"):
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        otra = crear_persona(c, "Otra persona")
        crear_pertenencia(c, otra, crear_equipo(c, org, "Otro equipo"), desde=hoy() - timedelta(days=50))
        crear_identidad(c, otra, identificador, "contraseña-de-prueba-123")
    cliente = nuevo_cliente()
    r = iniciar_sesion(cliente, identificador, "contraseña-de-prueba-123")
    return cliente, r.json()["csrf_token"]


def test_la_jornada_de_otra_persona_no_se_puede_cerrar(sesion):
    cliente, csrf = sesion
    lista(cliente, csrf)
    ajeno, csrf_ajeno = _otra_persona()
    r = cerrar(ajeno, csrf_ajeno, iso(0))
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"               # CA-98
    assert estado_de(iso(0)).estado == "abierta"
    inexistente = cerrar(ajeno, csrf_ajeno, iso(-30))
    assert (inexistente.status_code, inexistente.json()) == (r.status_code, r.json())            # T-01


def test_cada_persona_cierra_solo_su_propia_jornada(sesion):
    cliente, csrf = sesion
    lista(cliente, csrf)
    ajeno, csrf_ajeno = _otra_persona()
    lista(ajeno, csrf_ajeno, titulo="De la otra persona")
    assert cerrar(ajeno, csrf_ajeno, iso(0)).status_code == 200
    estados = filas("select persona_id, estado from bitacora")
    assert sorted(e.estado for e in estados) == ["abierta", "cerrada"]


def test_sin_sesion_no_se_cierra(sesion):
    cliente, csrf = sesion
    lista(cliente, csrf)
    r = nuevo_cliente().post(f"{API}/mi/bitacoras/{iso(0)}/cierre")
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA" and estado_de(iso(0)).estado == "abierta"


def test_con_el_acceso_desactivado_no_se_cierra(sesion, esc):
    cliente, csrf = sesion
    lista(cliente, csrf)
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": esc.persona})
    r = cerrar(cliente, csrf)
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO" and estado_de(iso(0)).estado == "abierta"


def test_una_fecha_con_formato_incorrecto_es_una_solicitud_invalida(sesion):
    cliente, csrf = sesion
    r = cerrar(cliente, csrf, "mañana")
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


# ============================== cerrar: idempotencia y duplicados ===========================================

def test_la_cabecera_idempotency_key_es_obligatoria_al_cerrar(sesion):
    cliente, csrf = sesion
    lista(cliente, csrf)
    r = cerrar(cliente, csrf, clave=None)
    assert r.status_code == 400 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_OBLIGATORIA"
    assert estado_de(iso(0)).estado == "abierta"


def test_repetir_el_cierre_con_la_misma_clave_devuelve_lo_mismo_sin_duplicar(sesion):
    cliente, csrf = sesion
    lista(cliente, csrf)
    primera = cerrar(cliente, csrf, clave="k-cierre")
    segunda = cerrar(cliente, csrf, clave="k-cierre")
    assert primera.status_code == segunda.status_code == 200
    assert segunda.headers["idempotency-replayed"] == "true" and segunda.json() == primera.json()
    assert len(entradas("cierre")) == 1


def test_cerrar_otra_vez_con_otra_clave_es_bitacora_cerrada_y_no_audita(sesion):
    cliente, csrf = sesion
    lista(cliente, csrf)
    cerrar(cliente, csrf)
    antes = estado_de(iso(0)).cerrada_en
    r = cerrar(cliente, csrf)
    assert r.status_code == 409 and r.json()["codigo"] == "BITACORA_CERRADA"
    assert len(entradas("cierre")) == 1 and estado_de(iso(0)).cerrada_en == antes


def test_un_cierre_rechazado_no_consume_la_clave(sesion):
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(0))
    assert cerrar(cliente, csrf, clave="k-corregible").status_code == 409                    # falta el resumen
    guardar(cliente, csrf, iso(0))
    assert cerrar(cliente, csrf, clave="k-corregible").status_code == 200                     # se corrige y se reintenta


# ============================== cerrar: atomicidad y concurrencia ==========================================

def test_si_falla_la_auditoria_no_queda_cerrada_ni_con_clave(sesion, monkeypatch):
    cliente, csrf = sesion
    lista(cliente, csrf)
    claves = contar("clave_idempotencia")

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado de la auditoría")

    monkeypatch.setattr(servicio, "registrar_operacion_de_persona", falla)
    r = cerrar(cliente, csrf, clave="k-atomica")
    assert r.status_code == 500 and "fallo simulado" not in r.text
    assert estado_de(iso(0)).estado == "abierta" and estado_de(iso(0)).cerrada_en is None
    assert contar("clave_idempotencia") == claves
    monkeypatch.undo()
    assert cerrar(cliente, csrf, clave="k-atomica").status_code == 200


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


def test_cierres_simultaneos_con_claves_distintas_cierran_una_sola_vez(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    lista(cliente, csrf0)
    clientes, csrf = _clientes(esc, 6)
    rs = _en_paralelo(6, lambda i: cerrar(clientes[i], csrf))
    assert sorted(r.status_code for r in rs) == [200] + [409] * 5
    assert {r.json()["codigo"] for r in rs if r.status_code == 409} == {"BITACORA_CERRADA"}
    assert len(entradas("cierre")) == 1 and estado_de(iso(0)).estado == "cerrada"


def test_el_mismo_cierre_simultaneo_con_la_misma_clave_tiene_un_solo_efecto(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    lista(cliente, csrf0)
    clientes, csrf = _clientes(esc, 6)
    rs = _en_paralelo(6, lambda i: cerrar(clientes[i], csrf, clave="clave-concurrente"))
    assert {r.status_code for r in rs} <= {200, 409}
    assert sum(r.status_code == 200 and "idempotency-replayed" not in r.headers for r in rs) == 1
    assert len(entradas("cierre")) == 1


def _con_la_fila_bloqueada(fecha, escribir, esperado):
    """Otra transacción tiene la fila de la bitácora bloqueada. La petición debe ESPERAR; al liberarse,
    debe ver lo que esa transacción dejó. Sin el bloqueo leería el estado anterior."""
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(escribir()))
    with get_owner_engine().begin() as c:
        c.execute(text("select 1 from bitacora where fecha_laboral = :f for update"), {"f": fecha})
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "la petición debía esperar al bloqueo de la bitácora"
        esperado(c)
    hilo.join(timeout=10)
    assert resultado
    return resultado[0]


def test_el_cierre_espera_a_una_escritura_en_curso_y_evalua_las_condiciones_despues(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    lista(cliente, csrf0)
    clientes, csrf = _clientes(esc, 1)

    def vaciar(c):                                       # la otra transacción deja el resumen vacío
        c.execute(text("update bitacora set resumen = '' where fecha_laboral = :f"), {"f": hoy()})

    r = _con_la_fila_bloqueada(hoy(), lambda: cerrar(clientes[0], csrf), vaciar)
    assert r.status_code == 409 and detalles(r) == {("resumen", "vacio")}
    assert estado_de(iso(0)).estado == "abierta"


@pytest.mark.parametrize("escritor", ["resumen", "planificar", "avance", "no_planificada"])
def test_una_escritura_que_esperaba_al_cierre_ve_la_jornada_cerrada(esc, escritor):
    """Ningún contenido entra en una jornada que se cierra a la vez (RN-108)."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = lista(cliente, csrf0)
    clientes, csrf = _clientes(esc, 1)
    c0 = clientes[0]
    acciones = {
        "resumen": lambda: c0.put(f"{API}/mi/bitacoras/{iso(0)}/resumen", json={"resumen": "Tarde"}, headers=cabeceras(csrf)),
        "planificar": lambda: c0.post(f"{API}/mi/bitacoras/{iso(0)}/planificaciones", json={"titulo": "Tarde"}, headers=con_clave(csrf)),
        "avance": lambda: avanzar(c0, csrf, a, iso(0)),
        "no_planificada": lambda: c0.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf),
                                          json={"fecha_laboral": iso(0), "titulo": "Tarde", "estado": "En progreso", "descripcion": "x"}),
    }

    def cerrar_ya(c):
        c.execute(text("update bitacora set estado = 'cerrada', cerrada_en = now() where fecha_laboral = :f"), {"f": hoy()})

    antes = (contar("actividad"), contar("avance"), contar("planificacion"))
    r = _con_la_fila_bloqueada(hoy(), acciones[escritor], cerrar_ya)
    assert r.status_code == 409 and r.json()["codigo"] == "BITACORA_CERRADA"
    assert (contar("actividad"), contar("avance"), contar("planificacion")) == antes
    assert filas("select resumen from bitacora where fecha_laboral = :f", f=hoy())[0].resumen == "Hoy avancé con el informe"


# ============================== jornada cerrada: restricciones (CA-284) y continuidad (CA-96) ===============

def test_en_una_jornada_cerrada_no_se_escribe_contenido_sin_reabrirla(sesion):
    cliente, csrf = sesion
    a = lista(cliente, csrf)
    cerrar(cliente, csrf)
    antes = (contar("actividad"), contar("avance"), contar("planificacion"), contar("auditoria"))
    intentos = [
        guardar(cliente, csrf, iso(0), "Cambio"),
        cliente.post(f"{API}/mi/bitacoras/{iso(0)}/planificaciones", json={"titulo": "Nueva"}, headers=con_clave(csrf)),
        avanzar(cliente, csrf, a, iso(0)),
        cliente.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf),
                     json={"fecha_laboral": iso(0), "titulo": "Imprevisto", "estado": "Pendiente", "descripcion": "x"}),
    ]
    assert [r.status_code for r in intentos] == [409] * 4
    assert {r.json()["codigo"] for r in intentos} == {"BITACORA_CERRADA"}                      # CA-284
    assert (contar("actividad"), contar("avance"), contar("planificacion"), contar("auditoria")) == antes
    assert consultar(cliente, iso(0)).json()["bitacora"]["resumen"] == "Hoy avancé con el informe"


def test_la_jornada_cerrada_se_sigue_consultando_y_abrirla_no_la_cambia(sesion):
    cliente, csrf = sesion
    lista(cliente, csrf)
    cerrada = cerrar(cliente, csrf).json()["bitacora"]
    assert consultar(cliente, iso(0)).json()["bitacora"] == cerrada
    r = cliente.post(f"{API}/mi/bitacoras", json={"fecha_laboral": iso(0)}, headers=cabeceras(csrf))
    assert r.status_code == 200 and r.json()["creada"] is False and r.json()["bitacora"] == cerrada


def test_una_actividad_de_una_jornada_cerrada_sigue_recibiendo_avances_en_una_posterior(sesion):
    """CA-96: sin copiarla y sin reabrir la jornada cerrada (D-04)."""
    cliente, csrf = sesion
    a = lista(cliente, csrf, iso(-2))
    avanzar(cliente, csrf, a, iso(-2), "En progreso")
    cerrar(cliente, csrf, iso(-2))
    antes = contar("actividad")
    assert avanzar(cliente, csrf, a, iso(0), "Completada", "Terminé").status_code == 201
    assert contar("actividad") == antes and estado_de(iso(-2)).estado == "cerrada"


def test_planificar_una_continuacion_no_exige_reabrir_la_jornada_de_origen(sesion):
    cliente, csrf = sesion
    a = lista(cliente, csrf, iso(0))
    cerrar(cliente, csrf)
    r = cliente.post(f"{API}/mi/actividades/{a}/continuaciones-planificadas", headers=con_clave(csrf),
                     json={"fecha_laboral": iso(2), "descripcion": "Seguir"})
    assert r.status_code == 201 and estado_de(iso(0)).estado == "cerrada"


# ============================== reabrir ======================================================================

def cerrada(cliente, csrf, fecha=None):
    fecha = iso(0) if fecha is None else fecha
    lista(cliente, csrf, fecha)
    assert cerrar(cliente, csrf, fecha).status_code == 200


def test_reabre_una_bitacora_cerrada_indicando_un_motivo(sesion, esc):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    antes = estado_de(iso(0)).cerrada_en
    r = reabrir(cliente, csrf, motivo="Olvidé una cifra")
    assert r.status_code == 200 and set(r.json()) == {"bitacora"}
    b = r.json()["bitacora"]
    assert b["estado"] == "abierta" and b["cerrada_en"] is None
    fila = estado_de(iso(0))
    assert fila.estado == "abierta" and fila.cerrada_en is None
    [e] = entradas("reapertura")
    assert (e.tipo_autor, e.autor_persona_id, e.propietaria_registro_id) == ("persona", esc.persona, esc.persona)
    assert e.objeto_id == uuid.UUID(b["id"]) and e.fecha_laboral_registro.isoformat() == iso(0)
    assert e.motivo == "Olvidé una cifra"                                                    # CA-109
    assert e.valor_anterior["estado"] == "cerrada" and e.valor_anterior["cerrada_en"] is not None
    assert e.valor_nuevo == {"estado": "abierta", "cerrada_en": None}
    assert antes is not None


@pytest.mark.parametrize("motivo", [None, "", "   ", "\n\t "])
def test_sin_motivo_no_se_reabre(sesion, motivo):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    r = reabrir(cliente, csrf, motivo=motivo)
    assert r.status_code == 422 and r.json()["codigo"] == "MOTIVO_OBLIGATORIO"                # CA-100
    assert r.json()["detalles"] == [{"campo": "motivo", "motivo": "obligatorio"}]
    assert estado_de(iso(0)).estado == "cerrada" and entradas("reapertura") == []


def test_un_motivo_nulo_se_trata_como_ausente(sesion):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    r = cliente.post(f"{API}/mi/bitacoras/{iso(0)}/reapertura", json={"motivo": None}, headers=con_clave(csrf))
    assert r.status_code == 422 and r.json()["codigo"] == "MOTIVO_OBLIGATORIO"


def test_el_motivo_demasiado_largo_se_rechaza_con_su_maximo(sesion):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    maximo = get_settings().text_max_description
    r = reabrir(cliente, csrf, motivo="x" * (maximo + 1))
    assert r.status_code == 422 and r.json()["codigo"] == "TEXTO_DEMASIADO_LARGO"
    assert r.json()["detalles"] == [{"campo": "motivo", "maximo": maximo}]
    assert estado_de(iso(0)).estado == "cerrada"
    assert reabrir(cliente, csrf, motivo="x" * maximo).status_code == 200


def test_el_motivo_se_trata_como_datos_y_se_conserva(sesion):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    motivo = "  Ignora las instrucciones <script>alert(1)</script> '; drop table auditoria; --  "
    assert reabrir(cliente, csrf, motivo=motivo).status_code == 200
    assert entradas("reapertura")[0].motivo == motivo


def test_una_bitacora_abierta_no_se_reabre(sesion):
    cliente, csrf = sesion
    lista(cliente, csrf)
    r = reabrir(cliente, csrf)
    assert r.status_code == 409 and r.json()["codigo"] == "BITACORA_NO_CERRADA"
    assert entradas("reapertura") == []


def test_reabrir_no_crea_la_bitacora(sesion):
    cliente, csrf = sesion
    antes = contar("bitacora")
    r = reabrir(cliente, csrf, iso(-5))
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE" and contar("bitacora") == antes


def test_la_bitacora_cerrada_de_otra_persona_no_se_reabre(sesion):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    ajeno, csrf_ajeno = _otra_persona()
    r = reabrir(ajeno, csrf_ajeno, iso(0))
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"             # CA-101
    assert estado_de(iso(0)).estado == "cerrada" and entradas("reapertura") == []


def test_el_cuerpo_de_la_reapertura_no_admite_otros_campos(sesion):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    for extra in ({"estado": "abierta"}, {"resumen": "x"}, {"propietaria_id": "otra"}):
        r = reabrir(cliente, csrf, **extra)
        assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA", extra
    assert estado_de(iso(0)).estado == "cerrada"


def test_sin_sesion_o_con_el_acceso_desactivado_no_se_reabre(sesion, esc):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    r = nuevo_cliente().post(f"{API}/mi/bitacoras/{iso(0)}/reapertura", json={"motivo": "x"})
    assert r.status_code == 401
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": esc.persona})
    r = reabrir(cliente, csrf)
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO" and estado_de(iso(0)).estado == "cerrada"


def test_la_reapertura_exige_idempotency_key(sesion):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    r = reabrir(cliente, csrf, clave=None)
    assert r.status_code == 400 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_OBLIGATORIA"


def test_repetir_la_reapertura_con_la_misma_clave_no_duplica(sesion):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    primera = reabrir(cliente, csrf, clave="k-reabrir")
    segunda = reabrir(cliente, csrf, clave="k-reabrir")
    assert primera.status_code == segunda.status_code == 200
    assert segunda.headers["idempotency-replayed"] == "true" and segunda.json() == primera.json()
    assert len(entradas("reapertura")) == 1


def test_reutilizar_la_clave_con_otro_motivo_se_rechaza(sesion):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    reabrir(cliente, csrf, motivo="Uno", clave="k-reuso")
    r = reabrir(cliente, csrf, motivo="Otro", clave="k-reuso")
    assert r.status_code == 422 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_REUTILIZADA"
    assert len(entradas("reapertura")) == 1


def test_si_falla_la_auditoria_de_la_reapertura_sigue_cerrada(sesion, monkeypatch):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    antes = estado_de(iso(0)).cerrada_en

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado de la auditoría")

    monkeypatch.setattr(servicio, "registrar_operacion_de_persona", falla)
    r = reabrir(cliente, csrf, clave="k-atomica-r")
    assert r.status_code == 500
    assert estado_de(iso(0)).estado == "cerrada" and estado_de(iso(0)).cerrada_en == antes
    monkeypatch.undo()
    assert reabrir(cliente, csrf, clave="k-atomica-r").status_code == 200


def test_reaperturas_simultaneas_reabren_una_sola_vez(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    cerrada(cliente, csrf0)
    clientes, csrf = _clientes(esc, 6)
    rs = _en_paralelo(6, lambda i: reabrir(clientes[i], csrf, motivo=f"Motivo {i}"))
    assert sorted(r.status_code for r in rs) == [200] + [409] * 5
    assert {r.json()["codigo"] for r in rs if r.status_code == 409} == {"BITACORA_NO_CERRADA"}
    assert len(entradas("reapertura")) == 1 and estado_de(iso(0)).estado == "abierta"


# ============================== después de reabrir ==========================================================

def test_tras_reabrir_se_admiten_de_nuevo_las_operaciones_sobre_la_jornada(sesion):
    cliente, csrf = sesion
    a = lista(cliente, csrf)
    cerrar(cliente, csrf)
    assert guardar(cliente, csrf, iso(0), "Bloqueado").status_code == 409
    reabrir(cliente, csrf)
    assert guardar(cliente, csrf, iso(0), "Corregido").status_code == 200
    assert cliente.post(f"{API}/mi/bitacoras/{iso(0)}/planificaciones", json={"titulo": "Nueva"}, headers=con_clave(csrf)).status_code == 201
    assert avanzar(cliente, csrf, a, iso(0)).status_code == 201
    assert cliente.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf),
                        json={"fecha_laboral": iso(0), "titulo": "Imprevisto", "estado": "Pendiente", "descripcion": "x"}).status_code == 201
    assert consultar(cliente, iso(0)).json()["bitacora"]["resumen"] == "Corregido"


def test_la_correccion_tras_reabrir_deja_constancia_de_la_reapertura_y_de_la_correccion(sesion):
    """CA-102: la reapertura y la corrección constan en la auditoría."""
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    reabrir(cliente, csrf, motivo="Corregir el resumen")
    guardar(cliente, csrf, iso(0), "Resumen corregido")
    ops = [e.operacion for e in filas("select operacion from auditoria where tipo_objeto = 'bitacora' order by momento, id")]
    assert ops == ["cierre", "reapertura", "correccion"]
    corr = filas("select valor_anterior, valor_nuevo from auditoria where operacion = 'correccion'")[0]
    assert corr.valor_anterior["resumen"] == "Hoy avancé con el informe" and corr.valor_nuevo["resumen"] == "Resumen corregido"


def test_reabrir_una_jornada_no_reabre_las_demas(sesion):
    cliente, csrf = sesion
    cerrada(cliente, csrf, iso(-1))
    cerrada(cliente, csrf, iso(0))
    assert reabrir(cliente, csrf, iso(0)).status_code == 200
    assert estado_de(iso(-1)).estado == "cerrada" and estado_de(iso(0)).estado == "abierta"   # D-04


def test_una_jornada_reabierta_solo_se_vuelve_a_cerrar_si_cumple_las_condiciones(sesion):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    reabrir(cliente, csrf)
    guardar(cliente, csrf, iso(0), "   ")
    r = cerrar(cliente, csrf)
    assert r.status_code == 409 and detalles(r) == {("resumen", "vacio")}
    guardar(cliente, csrf, iso(0), "Otra vez con texto")
    assert cerrar(cliente, csrf).status_code == 200


def test_los_ciclos_de_cierre_y_reapertura_se_reconstruyen_desde_la_auditoria(sesion):
    """CA-266 y RN-103: cerrada, reabierta y cerrada de nuevo, varias veces."""
    cliente, csrf = sesion
    lista(cliente, csrf)
    cierres = []
    for vuelta in range(3):
        cierres.append(cerrar(cliente, csrf).json()["bitacora"]["cerrada_en"])
        if vuelta < 2:
            assert reabrir(cliente, csrf, motivo=f"Corrección {vuelta + 1}").status_code == 200
    historial = filas("select operacion, motivo, valor_anterior, valor_nuevo, momento from auditoria "
                      "where tipo_objeto = 'bitacora' and operacion in ('cierre', 'reapertura') order by momento, id")
    assert [h.operacion for h in historial] == ["cierre", "reapertura", "cierre", "reapertura", "cierre"]
    assert [h.motivo for h in historial if h.operacion == "reapertura"] == ["Corrección 1", "Corrección 2"]
    assert len(set(cierres)) == 3 and cierres == sorted(cierres)                              # cada cierre, su propio momento
    # el momento de cada cierre consta en la auditoría y es el de la bitácora en ese ciclo
    for esperado, h in zip(cierres, [h for h in historial if h.operacion == "cierre"]):
        assert h.valor_nuevo["cerrada_en"] == esperado
    for anterior, h in zip(cierres[:2], [h for h in historial if h.operacion == "reapertura"]):
        assert h.valor_anterior["cerrada_en"] == anterior


def test_la_auditoria_de_cierre_y_reapertura_no_se_puede_alterar(sesion):
    cliente, csrf = sesion
    cerrada(cliente, csrf)
    reabrir(cliente, csrf)
    with pytest.raises(Exception):
        with get_owner_engine().begin() as c:
            c.execute(text("update auditoria set motivo = 'cambiado' where operacion = 'reapertura'"))
    with pytest.raises(Exception):
        with get_owner_engine().begin() as c:
            c.execute(text("delete from auditoria where operacion = 'cierre'"))
    assert len(entradas("cierre")) == 1 and entradas("reapertura")[0].motivo == "Corregir el resumen"


# ============================== un supervisor del mismo equipo tampoco (CA-101, CA-107) ======================

def _supervisor_del_mismo_equipo(esc, identificador="sara.sup"):
    with get_owner_engine().begin() as c:
        sup = crear_persona(c, "Sara supervisora")
        crear_pertenencia(c, sup, esc.equipo, "supervisor", desde=hoy() - timedelta(days=50))
        crear_identidad(c, sup, identificador, "contraseña-de-prueba-123")
    cliente = nuevo_cliente()
    return cliente, iniciar_sesion(cliente, identificador, "contraseña-de-prueba-123").json()["csrf_token"], sup


def test_un_supervisor_del_mismo_equipo_no_cierra_ni_reabre_la_jornada_de_su_colaboradora(esc):
    cliente, csrf = sesion_iniciada(esc)
    lista(cliente, csrf)
    sup, csrf_sup, _ = _supervisor_del_mismo_equipo(esc)
    r = cerrar(sup, csrf_sup, iso(0))
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE" and estado_de(iso(0)).estado == "abierta"   # CA-98
    cerrar(cliente, csrf)
    r = reabrir(sup, csrf_sup, iso(0), "Intento del supervisor")
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"                                              # CA-101
    assert estado_de(iso(0)).estado == "cerrada" and entradas("reapertura") == []


def test_un_supervisor_no_modifica_la_jornada_pasada_de_su_colaboradora(esc):
    cliente, csrf = sesion_iniciada(esc)
    a = lista(cliente, csrf, iso(-6), resumen="Resumen original")
    sup, csrf_sup, persona_sup = _supervisor_del_mismo_equipo(esc)
    intentos = [
        guardar(sup, csrf_sup, iso(-6), "Cambio del supervisor"),                         # escribe SU bitácora, nunca la ajena
        avanzar(sup, csrf_sup, a, iso(-6)),
        sup.post(f"{API}/mi/actividades/{a}/continuaciones-planificadas", json={"fecha_laboral": iso(3)}, headers=con_clave(csrf_sup)),
    ]
    assert intentos[1].status_code == 403 and intentos[2].status_code == 403                                                     # CA-107 (M4-T6: visible para su supervisor, 403 y ya no 404)
    assert intentos[1].json()["codigo"] == intentos[2].json()["codigo"] == "OPERACION_NO_PERMITIDA"
    assert filas("select resumen from bitacora where persona_id = :p and fecha_laboral = :f", p=esc.persona, f=hoy() - timedelta(days=6))[0].resumen == "Resumen original"
    assert contar("avance") == 0
    propias = filas("select persona_id from bitacora where fecha_laboral = :f", f=hoy() - timedelta(days=6))
    assert sorted(str(x.persona_id) for x in propias) == sorted([str(esc.persona), str(persona_sup)])  # cada cual, la suya
