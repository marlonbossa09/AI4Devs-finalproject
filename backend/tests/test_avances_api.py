"""T2 — M2-05: registrar un avance sobre una actividad propia (PostgreSQL real, por HTTP).

Criterios: CA-45 a CA-52, CA-66 a CA-72, CA-74 a CA-78, CA-96, CA-182, CA-190, CA-203 a CA-208 y las
reglas D-01, D-02, D-03, D-04 y T-04 del contrato. Las pruebas destructivas corren solo sobre
``smartwork_test`` (ver conftest y aislamiento).
"""

import threading
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.db import get_owner_engine
from app.seguridad.sesiones import NOMBRE_COOKIE
from scripts.verificar_datos import estados_actuales_incoherentes
from tests.fabricas import (
    crear_equipo, crear_identidad, crear_persona, crear_pertenencia, escenario_basico, hoy,
)
from tests.utiles_http import API, iniciar_sesion, nuevo_cliente, sesion_iniciada
from tests.utiles_m2 import (
    avanzar, con_clave, contar, estado_actual_de, filas, iso, planificar_actividad,
)


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


# ============================== registro, estado actual y estado histórico =========================

def test_registrar_un_avance_actualiza_la_actividad_y_conserva_el_estado_historico(sesion, actividad):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, actividad, iso(0), "En progreso", "Empecé el informe")
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["avance"]["estado"] == "En progreso" and cuerpo["avance"]["fecha_laboral"] == iso(0)   # CA-45, CA-66
    assert cuerpo["avance"]["descripcion"] == "Empecé el informe"
    assert cuerpo["actividad"]["estado_actual"] == "En progreso"                                          # CA-67
    assert cuerpo["bitacora_creada"] is False and estado_actual_de(actividad) == "En progreso"
    avanzar(cliente, csrf, actividad, iso(0), "Completada", "Lo terminé")
    estados = [f.estado for f in filas("select estado from avance order by registrado_en")]
    assert estados == ["En progreso", "Completada"]                                                       # CA-46
    assert estado_actual_de(actividad) == "Completada"


def test_el_avance_no_modifica_la_planificacion_ni_el_titulo(sesion, actividad):
    cliente, csrf = sesion
    antes = filas("select titulo from actividad")[0].titulo, filas("select descripcion from planificacion")
    avanzar(cliente, csrf, actividad, iso(0), "En progreso")
    assert (filas("select titulo from actividad")[0].titulo, filas("select descripcion from planificacion")) == antes
    assert contar("planificacion") == 1


def test_la_consulta_de_la_bitacora_muestra_el_avance_con_su_fecha_estado_y_descripcion(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(0), "En progreso", "Primera parte")
    b = cliente.get(f"{API}/mi/bitacoras/{iso(0)}").json()
    assert [(a["fecha_laboral"], a["estado"], a["descripcion"]) for a in b["avances"]] == [
        (iso(0), "En progreso", "Primera parte")]                                                         # CA-70
    assert b["actividades"][0]["estado_actual"] == "En progreso"


def test_dos_avances_en_la_misma_fecha_constan_y_el_segundo_es_el_estado_actual(sesion, actividad):
    cliente, csrf = sesion
    assert avanzar(cliente, csrf, actividad, iso(0), "En progreso", "Mañana").status_code == 201
    assert avanzar(cliente, csrf, actividad, iso(0), "Bloqueada", "Tarde", "Espero datos").status_code == 201
    assert contar("avance") == 2                                                                          # CA-71
    assert estado_actual_de(actividad) == "Bloqueada"                                                     # CA-75, CA-77


def test_registrar_el_avance_abre_la_bitacora_de_esa_fecha_en_la_misma_transaccion(sesion, actividad):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, actividad, iso(-1), "En progreso")                                          # D-01
    assert r.status_code == 201 and r.json()["bitacora_creada"] is True
    assert avanzar(cliente, csrf, actividad, iso(-1), "En progreso").json()["bitacora_creada"] is False
    assert contar("bitacora") == 2


# ============================== transiciones de estado y bloqueo ===================================

@pytest.mark.parametrize("origen,destino", [
    ("Pendiente", "En progreso"), ("En progreso", "Bloqueada"), ("Bloqueada", "En progreso"),
    ("En progreso", "Pendiente"), ("Pendiente", "Completada"), ("Pendiente", "Bloqueada"),
])
def test_se_admite_cualquier_cambio_de_estado_entre_los_cuatro(sesion, actividad, origen, destino):
    """CA-67: cambio a otro de los cuatro estados. (Desde Completada solo con reactivación, M3-04.)"""
    cliente, csrf = sesion
    if origen != "Pendiente":
        avanzar(cliente, csrf, actividad, iso(0), origen, motivo_bloqueo="Falta acceso" if origen == "Bloqueada" else None)
    r = avanzar(cliente, csrf, actividad, iso(0), destino, motivo_bloqueo="Falta acceso" if destino == "Bloqueada" else None)
    assert r.status_code == 201 and estado_actual_de(actividad) == destino


@pytest.mark.parametrize("estado", ["Terminada", "pendiente", "", "COMPLETADA"])
def test_un_estado_distinto_de_los_cuatro_no_se_acepta(sesion, actividad, estado):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, actividad, iso(0), estado)
    assert r.status_code == 422 and r.json()["codigo"] == "ESTADO_INVALIDO"                               # CA-48
    assert contar("avance") == 0


def test_un_estado_ausente_no_se_acepta(sesion, actividad):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, actividad, iso(0), estado=None)
    assert r.status_code == 422 and r.json()["codigo"] == "ESTADO_INVALIDO"


@pytest.mark.parametrize("motivo", [None, "", "   "])
def test_bloquear_sin_motivo_no_se_permite(sesion, actividad, motivo):
    cliente, csrf = sesion
    cuerpo = {"fecha_laboral": iso(0), "estado": "Bloqueada", "descripcion": "Me detuve"}
    if motivo is not None:
        cuerpo["motivo_bloqueo"] = motivo
    r = cliente.post(f"{API}/mi/actividades/{actividad}/avances", json=cuerpo, headers=con_clave(sesion[1]))
    assert r.status_code == 422 and r.json()["codigo"] == "MOTIVO_BLOQUEO_OBLIGATORIO"                    # CA-49
    assert contar("avance") == 0 and estado_actual_de(actividad) == "Pendiente"


def test_el_motivo_del_bloqueo_consta_y_sigue_constando_al_cambiar_de_estado(sesion, actividad):
    cliente, csrf = sesion
    assert avanzar(cliente, csrf, actividad, iso(0), "Bloqueada", "Sin acceso", "Falta el acceso al servidor"
                   ).status_code == 201                                                                    # CA-50
    avanzar(cliente, csrf, actividad, iso(0), "En progreso", "Ya hay acceso")
    avances = cliente.get(f"{API}/mi/bitacoras/{iso(0)}").json()["avances"]
    assert [(a["estado"], a["motivo_bloqueo"]) for a in avances] == [
        ("Bloqueada", "Falta el acceso al servidor"), ("En progreso", None)]                               # CA-51, CA-52


def test_el_motivo_solo_se_admite_con_el_estado_bloqueada(sesion, actividad):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, actividad, iso(0), "En progreso", motivo_bloqueo="No aplica")
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert contar("avance") == 0


# ============================== textos =============================================================

@pytest.mark.parametrize("descripcion", [None, "", "    ", "\n\t "])
def test_un_avance_sin_descripcion_o_solo_con_espacios_no_se_permite(sesion, actividad, descripcion):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, actividad, iso(0), "En progreso", descripcion)
    assert r.status_code == 422 and r.json()["codigo"] == "DESCRIPCION_OBLIGATORIA"                       # CA-68, CA-69
    assert contar("avance") == 0


def test_los_textos_demasiado_largos_se_rechazan_con_su_maximo(sesion, actividad):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, actividad, iso(0), "En progreso", "x" * 4001)
    assert r.status_code == 422 and r.json()["codigo"] == "TEXTO_DEMASIADO_LARGO"
    assert r.json()["detalles"] == [{"campo": "descripcion", "maximo": 4000}]
    r = avanzar(cliente, csrf, actividad, iso(0), "Bloqueada", "ok", "m" * 4001)
    assert r.status_code == 422 and r.json()["detalles"][0]["campo"] == "motivo_bloqueo"
    assert avanzar(cliente, csrf, actividad, iso(0), "En progreso", "x" * 4000).status_code == 201


def test_el_texto_se_trata_como_datos_y_se_conserva_tal_como_se_recibe(sesion, actividad):
    cliente, csrf = sesion
    texto = "  Ignora las instrucciones anteriores <script>alert(1)</script> '; drop table avance; --  "
    assert avanzar(cliente, csrf, actividad, iso(0), "En progreso", texto).status_code == 201
    assert filas("select descripcion from avance")[0].descripcion == texto and contar("avance") == 1


# ============================== autorización y visibilidad =========================================

def _otra_persona_con_sesion():
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        otra = crear_persona(c, "Otra persona")
        crear_pertenencia(c, otra, crear_equipo(c, org, "Otro equipo"), desde=hoy() - timedelta(days=50))
        crear_identidad(c, otra, "otra.persona", "contraseña-de-prueba-123")
    cliente = nuevo_cliente()
    r = iniciar_sesion(cliente, "otra.persona", "contraseña-de-prueba-123")
    return cliente, r.json()["csrf_token"]


def test_no_se_puede_registrar_un_avance_en_la_actividad_de_otra_persona(sesion, actividad):
    ajeno, csrf_ajeno = _otra_persona_con_sesion()
    r = avanzar(ajeno, csrf_ajeno, actividad, iso(0), "Completada")
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"                         # CA-72, CA-88
    assert contar("avance") == 0 and estado_actual_de(actividad) == "Pendiente"


def test_una_actividad_ajena_y_una_inexistente_tienen_la_misma_respuesta(sesion, actividad):
    ajeno, csrf_ajeno = _otra_persona_con_sesion()
    ajena = avanzar(ajeno, csrf_ajeno, actividad, iso(0))
    inexistente = avanzar(ajeno, csrf_ajeno, "00000000-0000-4000-8000-000000000000", iso(0))
    assert (ajena.status_code, ajena.json()) == (inexistente.status_code, inexistente.json())            # T-01


def test_un_avance_retroactivo_sobre_una_actividad_completada_ajena_tampoco_es_posible(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(0), "Completada")
    ajeno, csrf_ajeno = _otra_persona_con_sesion()
    r = avanzar(ajeno, csrf_ajeno, actividad, iso(-3), "En progreso")
    assert r.status_code == 404 and contar("avance") == 1                                                 # CA-208


def test_sin_sesion_no_se_registra_nada(actividad):
    r = nuevo_cliente().post(f"{API}/mi/actividades/{actividad}/avances", json={"fecha_laboral": iso(0)})
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"
    assert contar("avance") == 0


@pytest.mark.parametrize("extra", [{"actividad_id": "otra"}, {"propietaria_id": "x"}, {"registrado_en": "2020-01-01T00:00:00Z"},
                                   {"es_reactivacion": True}, {"id": "x"}])
def test_el_cuerpo_no_admite_campos_desconocidos(sesion, actividad, extra):
    cliente, csrf = sesion
    cuerpo = {"fecha_laboral": iso(0), "estado": "En progreso", "descripcion": "Trabajo", **extra}
    r = cliente.post(f"{API}/mi/actividades/{actividad}/avances", json=cuerpo, headers=con_clave(csrf))
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert contar("avance") == 0


def test_un_identificador_de_actividad_mal_formado_es_una_solicitud_invalida(sesion):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, "no-es-un-uuid", iso(0))
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


# ============================== fechas =============================================================

def test_no_se_registra_ejecucion_con_fecha_futura(sesion, actividad):
    cliente, csrf = sesion
    antes = contar("bitacora")
    r = avanzar(cliente, csrf, actividad, iso(1), "En progreso")
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_FUTURA_NO_PERMITIDA"                     # CA-182
    assert contar("avance") == 0 and contar("bitacora") == antes


def test_la_fecha_debe_estar_cubierta_por_una_pertenencia(sesion, actividad):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, actividad, iso(-401), "En progreso")                                       # antes de la primera pertenencia
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_NO_CUBIERTA"
    assert contar("avance") == 0 and contar("bitacora") == 1


@pytest.mark.parametrize("fecha", ["hoy", "2026-13-45", "01/01/2026", ""])
def test_una_fecha_con_formato_incorrecto_es_una_solicitud_invalida(sesion, actividad, fecha):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, actividad, fecha, "En progreso")
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


# ============================== bitácora cerrada (D-04) ============================================

def _cerrar_por_sql(fecha: str):
    """Cierra una bitácora directamente (el cierre manual es T8); solo para preparar el escenario."""
    with get_owner_engine().begin() as c:
        c.execute(text("update bitacora set estado = 'cerrada', cerrada_en = now() where fecha_laboral = :f"), {"f": fecha})


def test_no_se_registra_un_avance_en_una_jornada_cerrada(sesion, actividad):
    cliente, csrf = sesion
    _cerrar_por_sql(iso(0))
    r = avanzar(cliente, csrf, actividad, iso(0), "En progreso")
    assert r.status_code == 409 and r.json()["codigo"] == "BITACORA_CERRADA"
    assert contar("avance") == 0 and estado_actual_de(actividad) == "Pendiente"


def test_solo_debe_estar_abierta_la_bitacora_de_la_fecha_del_avance(sesion, actividad):
    """CA-96: una jornada anterior cerrada, con avances de la actividad, no impide continuarla hoy."""
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-1), "En progreso", "Ayer")
    _cerrar_por_sql(iso(-1))
    r = avanzar(cliente, csrf, actividad, iso(0), "En progreso", "Hoy")
    assert r.status_code == 201
    estado_ayer = filas("select estado from bitacora where fecha_laboral = :f", f=iso(-1))[0].estado
    assert estado_ayer == "cerrada" and contar("avance") == 2                                              # la jornada anterior sigue cerrada


# ============================== actividad completada y secuencia ===================================

def test_una_actividad_completada_no_recibe_avances_posteriores_sin_reactivarla(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-1), "Completada", "Terminada ayer")
    for fecha in (iso(0), iso(-1)):                    # posterior (CA-190) y misma fecha registrado después (CA-206)
        r = avanzar(cliente, csrf, actividad, fecha, "En progreso")
        assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_COMPLETADA", fecha
    assert contar("avance") == 1 and estado_actual_de(actividad) == "Completada"


def test_un_rechazo_por_actividad_completada_no_deja_rastro_ni_abre_la_bitacora(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-1), "Completada")
    bitacoras, auditorias = contar("bitacora"), contar("auditoria")
    r = avanzar(cliente, csrf, actividad, iso(0), "En progreso")
    assert r.status_code == 409
    assert contar("bitacora") == bitacoras and contar("avance") == 1 and contar("auditoria") == auditorias


def test_un_avance_retroactivo_anterior_a_la_finalizacion_se_acepta_sin_reactivar(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-1), "Completada", "Terminada")
    r = avanzar(cliente, csrf, actividad, iso(-3), "En progreso", "Trabajo olvidado")
    assert r.status_code == 201                                                                            # CA-203
    assert estado_actual_de(actividad) == "Completada"                                                     # CA-205
    assert r.json()["actividad"]["estado_actual"] == "Completada"
    assert not [f for f in filas("select es_reactivacion from avance") if f.es_reactivacion]              # sin reactivar


def test_un_avance_retroactivo_no_sustituye_el_estado_de_uno_posterior(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(-1), "En progreso", "Martes")
    r = avanzar(cliente, csrf, actividad, iso(-2), "Completada", "Lunes")
    assert r.status_code == 201 and r.json()["actividad"]["estado_actual"] == "En progreso"                # CA-78
    assert estado_actual_de(actividad) == "En progreso" and estados_actuales_incoherentes_vacio()


def estados_actuales_incoherentes_vacio() -> bool:
    with get_owner_engine().connect() as c:
        return estados_actuales_incoherentes(c) == []


# ============================== auditoría ==========================================================

def test_un_avance_de_la_jornada_actual_no_deja_entrada_de_auditoria(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(0), "En progreso")
    assert contar("auditoria") == 0


def test_un_avance_en_una_jornada_pasada_deja_una_unica_entrada_con_el_estado_anterior_y_el_nuevo(sesion, esc, actividad):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, actividad, iso(-3), "Bloqueada", "Retroactivo", "Sin datos", clave="retro-1")
    assert r.status_code == 201
    entradas = filas("select * from auditoria")
    assert len(entradas) == 1                                                                              # CA-204; una por operación
    e = entradas[0]
    assert (e.tipo_autor, e.operacion, e.tipo_objeto) == ("persona", "modificacion_jornada_pasada", "avance")
    assert e.autor_persona_id == esc.persona and e.propietaria_registro_id == esc.persona
    assert e.fecha_laboral_registro.isoformat() == iso(-3) and str(e.objeto_id) == r.json()["avance"]["id"]
    assert e.valor_anterior["estado_actual"] == "Pendiente" and e.valor_nuevo["estado_actual"] == "Bloqueada"
    assert e.valor_nuevo["bitacora_creada"] is True and e.valor_nuevo["avance"]["motivo_bloqueo"] == "Sin datos"
    avanzar(cliente, csrf, actividad, iso(-3), "Bloqueada", "Retroactivo", "Sin datos", clave="retro-1")  # reintento
    assert contar("auditoria") == 1 and contar("avance") == 1


def test_un_avance_retroactivo_sobre_una_actividad_completada_se_audita(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(0), "Completada")
    assert contar("auditoria") == 0
    avanzar(cliente, csrf, actividad, iso(-2), "En progreso", "Olvidado")
    entradas = filas("select * from auditoria")
    assert len(entradas) == 1 and entradas[0].valor_anterior["estado_actual"] == "Completada"             # CA-204
    assert entradas[0].valor_nuevo["estado_actual"] == "Completada"


# ============================== idempotencia (T-04) ================================================

def test_la_cabecera_idempotency_key_es_obligatoria(sesion, actividad):
    cliente, csrf = sesion
    r = avanzar(cliente, csrf, actividad, iso(0), clave=None)
    assert r.status_code == 400 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_OBLIGATORIA"
    assert contar("avance") == 0


def test_repetir_la_misma_peticion_con_la_misma_clave_no_crea_un_segundo_avance(sesion, actividad):
    cliente, csrf = sesion
    primera = avanzar(cliente, csrf, actividad, iso(0), "En progreso", "Uno", clave="k-1")
    segunda = avanzar(cliente, csrf, actividad, iso(0), "En progreso", "Uno", clave="k-1")
    assert primera.status_code == segunda.status_code == 201
    assert segunda.headers["idempotency-replayed"] == "true" and segunda.json() == primera.json()
    assert contar("avance") == 1


def test_reutilizar_la_clave_con_otra_peticion_se_rechaza(sesion, actividad):
    cliente, csrf = sesion
    avanzar(cliente, csrf, actividad, iso(0), "En progreso", "Uno", clave="k-2")
    r = avanzar(cliente, csrf, actividad, iso(0), "Bloqueada", "Dos", "Motivo", clave="k-2")
    assert r.status_code == 422 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_REUTILIZADA"
    assert contar("avance") == 1


def test_una_peticion_rechazada_no_consume_la_clave_y_se_puede_corregir(sesion, actividad):
    cliente, csrf = sesion
    assert avanzar(cliente, csrf, actividad, iso(0), "Bloqueada", "Sin motivo", clave="k-3").status_code == 422
    assert avanzar(cliente, csrf, actividad, iso(0), "Bloqueada", "Con motivo", "Falta acceso", clave="k-3").status_code == 201
    assert contar("avance") == 1


# ============================== actividad marcada por error ========================================

def test_una_actividad_marcada_por_error_no_recibe_avances(sesion, actividad):
    cliente, csrf = sesion
    with get_owner_engine().begin() as c:   # la marca es M3-05 (fuera de esta entrega): se prepara por SQL
        c.execute(text("update actividad set registrada_por_error = true, motivo_error = 'duplicada', "
                       "marcada_por = propietaria_id, marcada_en = now()"))
    r = avanzar(cliente, csrf, actividad, iso(0), "En progreso")
    assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_MARCADA_POR_ERROR"
    assert contar("avance") == 0


# ============================== concurrencia (DM-01, DM-02) ========================================

def _clientes_concurrentes(esc, n):
    base, _ = sesion_iniciada(esc)
    secreto = base.cookies.get(NOMBRE_COOKIE)
    csrf = base.get(f"{API}/sesion").json()["csrf_token"]
    return [nuevo_cliente({NOMBRE_COOKIE: secreto}) for _ in range(n)], csrf


def test_registros_simultaneos_sobre_una_actividad_dejan_un_estado_actual_coherente(esc):
    cliente, csrf = sesion_iniciada(esc)
    actividad = planificar_actividad(cliente, csrf, iso(0))
    clientes, csrf = _clientes_concurrentes(esc, 8)
    estados = ["En progreso", "Pendiente", "En progreso", "Bloqueada", "Pendiente", "En progreso", "Bloqueada", "Pendiente"]
    resultados, barrera = [], threading.Barrier(8)

    def intentar(i):
        barrera.wait()
        resultados.append(avanzar(clientes[i], csrf, actividad, iso(0), estados[i], f"Avance {i}",
                                  "Esperando" if estados[i] == "Bloqueada" else None))

    hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(8)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert [r.status_code for r in resultados] == [201] * 8, [r.text for r in resultados if r.status_code != 201]
    assert contar("avance") == 8
    ultimo = filas("select estado from avance order by registrado_en desc, id desc limit 1")[0].estado
    assert estado_actual_de(actividad) == ultimo and estados_actuales_incoherentes_vacio()               # DM-02


def test_un_registro_espera_al_que_tiene_bloqueada_la_actividad_y_valida_contra_su_resultado(esc):
    """Prueba determinista de la serialización por actividad (DM-01). Otra transacción tiene la
    actividad bloqueada: el registro debe ESPERAR y, al liberarse, validar contra lo ya confirmado.
    Sin el bloqueo respondería de inmediato (201) con una lectura anterior a la finalización."""
    cliente, csrf = sesion_iniciada(esc)
    actividad = planificar_actividad(cliente, csrf, iso(0))
    clientes, csrf = _clientes_concurrentes(esc, 1)
    resultado = []

    def registrar():
        resultado.append(avanzar(clientes[0], csrf, actividad, iso(0), "En progreso", "Tras la finalización"))

    with get_owner_engine().begin() as c:
        c.execute(text("select 1 from actividad where id = :a for update"), {"a": actividad})
        hilo = threading.Thread(target=registrar)
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "el registro debía esperar al bloqueo de la actividad"
        # La otra transacción finaliza la actividad y confirma al salir del bloque
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                       "select id, bitacora_origen_id, 'Completada', 'Finalizada' from actividad where id = :a"),
                  {"a": actividad})
        c.execute(text("update actividad set estado_actual = 'Completada' where id = :a"), {"a": actividad})
    hilo.join(timeout=10)
    assert resultado and resultado[0].status_code == 409 and resultado[0].json()["codigo"] == "ACTIVIDAD_COMPLETADA"
    assert contar("avance") == 1 and estado_actual_de(actividad) == "Completada"


def test_una_finalizacion_simultanea_con_otro_avance_deja_la_secuencia_valida(esc):
    """Si gana la finalización, el otro avance se rechaza; si gana el otro, ambos se aceptan. Nunca
    queda un avance tras una finalización sin reactivar."""
    cliente, csrf = sesion_iniciada(esc)
    actividad = planificar_actividad(cliente, csrf, iso(0))
    clientes, csrf = _clientes_concurrentes(esc, 2)
    resultados, barrera = {}, threading.Barrier(2)

    def intentar(i, estado):
        barrera.wait()
        resultados[estado] = avanzar(clientes[i], csrf, actividad, iso(0), estado, f"Avance {estado}")

    hilos = [threading.Thread(target=intentar, args=(0, "Completada")), threading.Thread(target=intentar, args=(1, "En progreso"))]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert resultados["Completada"].status_code == 201
    secuencia = [f.estado for f in filas("select estado from avance order by registrado_en, id")]
    if resultados["En progreso"].status_code == 201:
        assert secuencia == ["En progreso", "Completada"]
    else:
        assert resultados["En progreso"].json()["codigo"] == "ACTIVIDAD_COMPLETADA" and secuencia == ["Completada"]
    assert estado_actual_de(actividad) == "Completada" and estados_actuales_incoherentes_vacio()
