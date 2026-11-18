"""T10 — M3-04: reactivar una actividad Completada (PostgreSQL real, por HTTP).

Criterios: CA-124 a CA-129, CA-187 a CA-192, CA-207, CA-210, CA-269 a CA-271; RN-24, RN-40, RN-68, RN-70,
RN-73, RN-74, RN-100; D-01, D-02, D-03, D-04 y T-04. Una reactivación es un avance de la secuencia
(``es_reactivacion``) posterior a la finalización vigente; no borra ni reordena nada. Las pruebas destructivas
corren solo sobre ``smartwork_test``.
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


def reactivar(cliente, csrf, actividad_id, fecha=None, estado="En progreso", descripcion="Retomo la actividad",
              motivo_bloqueo=None, clave="__auto__", **extra):
    """M3-04. Un campo con valor ``None`` se omite."""
    cuerpo = {"fecha_laboral": iso(0) if fecha is None else fecha, "estado": estado, "descripcion": descripcion,
              "motivo_bloqueo": motivo_bloqueo, **extra}
    cuerpo = {k: v for k, v in cuerpo.items() if v is not None}
    return cliente.post(f"{API}/mi/actividades/{actividad_id}/reactivacion", json=cuerpo, headers=con_clave(csrf, clave))


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c, desde=hoy() - timedelta(days=400))


@pytest.fixture()
def sesion(esc):
    return sesion_iniciada(esc)


@pytest.fixture()
def completada(sesion):
    """Una actividad creada el día -6 y completada el día -4 (F = hoy - 4)."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-6))
    assert avanzar(cliente, csrf, a, iso(-5), "En progreso", "Avancé").status_code == 201
    assert avanzar(cliente, csrf, a, iso(-4), "Completada", "Terminé").status_code == 201
    return a


def estado_de(a) -> str:
    return filas("select estado_actual from actividad where id = :a", a=a)[0].estado_actual


def avances_de(a):
    return filas("select av.id, av.estado, av.es_reactivacion, b.fecha_laboral from avance av join bitacora b on b.id = av.bitacora_id "
                 "where av.actividad_id = :a order by b.fecha_laboral, av.registrado_en, av.id", a=a)


def entradas(operacion="reactivacion"):
    return filas("select * from auditoria where operacion = :o order by momento, id", o=operacion)


def contar_entradas_de(fecha: str) -> int:
    return filas("select count(*) as n from auditoria where fecha_laboral_registro = :f", f=fecha)[0].n


def coherente() -> bool:
    with get_owner_engine().connect() as c:
        return estados_actuales_incoherentes(c) == []


# ============================== reactivar: caso positivo (CA-124, CA-126, CA-269, CA-271) ====================

@pytest.mark.parametrize("estado,motivo", [("Pendiente", None), ("En progreso", None), ("Bloqueada", "Falta el acceso")])
def test_reactiva_hacia_los_tres_estados_permitidos(sesion, completada, estado, motivo):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(-2), estado, "Vuelvo a ella", motivo)
    assert r.status_code == 201
    d = r.json()
    assert set(d) == {"avance", "actividad", "bitacora_creada"}
    assert d["avance"]["es_reactivacion"] is True and d["avance"]["estado"] == estado and d["avance"]["fecha_laboral"] == iso(-2)
    assert d["avance"]["motivo_bloqueo"] == motivo and d["avance"]["descripcion"] == "Vuelvo a ella"
    assert d["actividad"]["id"] == completada and d["actividad"]["estado_actual"] == estado          # CA-124, CA-269, CA-271
    assert estado_de(completada) == estado and coherente()


def test_la_reactivacion_es_un_avance_posterior_a_la_finalizacion_y_la_historia_se_conserva(sesion, completada):
    cliente, csrf = sesion
    antes = avances_de(completada)
    r = reactivar(cliente, csrf, completada, iso(-2))
    despues = avances_de(completada)
    assert [a.id for a in despues[:2]] == [a.id for a in antes] and len(antes) == 2                    # nada se borra ni se reordena
    assert [(a.estado, a.es_reactivacion) for a in despues] == [
        ("En progreso", False), ("Completada", False), ("En progreso", True)]                         # CA-126
    assert (contar("actividad"), contar("avance")) == (1, 3)                                          # una sola actividad (CA-191)
    assert r.json()["actividad"]["id"] == completada


def test_la_actividad_conserva_su_identidad_su_planificacion_y_sus_avances(sesion, completada):
    cliente, csrf = sesion
    original = cliente.get(f"{API}/mi/actividades/{completada}").json()
    reactivar(cliente, csrf, completada, iso(-2))
    d = cliente.get(f"{API}/mi/actividades/{completada}").json()
    assert d["actividad"]["id"] == completada and d["actividad"]["titulo"] == original["actividad"]["titulo"]
    assert d["planificacion_original"] == original["planificacion_original"]                           # CA-191
    assert [a["id"] for a in d["avances"][:2]] == [a["id"] for a in original["avances"]]
    assert d["avances"][-1]["es_reactivacion"] is True and d["estado_actual"] == "En progreso"
    assert contar("actividad") == 1 and contar("planificacion") == 1


def test_la_finalizacion_anterior_se_conserva_sin_cambios(sesion, completada):
    cliente, csrf = sesion
    fin = filas("select id, estado, descripcion, registrado_en from avance where estado = 'Completada'")[0]
    reactivar(cliente, csrf, completada, iso(-2), "Pendiente")
    despues = filas("select id, estado, descripcion, registrado_en from avance where id = :i", i=fin.id)[0]
    assert tuple(despues) == tuple(fin)                                                                # CA-269


def test_una_actividad_no_planificada_completada_tambien_se_reactiva(sesion):
    cliente, csrf = sesion
    a = cliente.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf),
                     json={"fecha_laboral": iso(-3), "titulo": "Imprevisto", "estado": "Completada", "descripcion": "Lo resolví"}
                     ).json()["actividad"]["id"]
    assert reactivar(cliente, csrf, a, iso(-1)).status_code == 201 and estado_de(a) == "En progreso"


# ============================== fechas respecto a la finalización (CA-187, CA-188, CA-189, CA-192) ==========

def test_la_misma_fecha_de_la_finalizacion_se_acepta_y_queda_despues_de_ella(sesion, completada):
    """CA-187: mismo día laboral F; el momento de registro lo asigna el servidor, posterior al de la finalización."""
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(-4), "En progreso")
    assert r.status_code == 201
    secuencia = [(a.estado, a.es_reactivacion) for a in avances_de(completada)]
    assert secuencia == [("En progreso", False), ("Completada", False), ("En progreso", True)]
    fin, rea = filas("select registrado_en from avance where estado = 'Completada'")[0], filas("select registrado_en from avance where es_reactivacion")[0]
    assert rea.registrado_en > fin.registrado_en and estado_de(completada) == "En progreso"
    assert cliente.get(f"{API}/mi/actividades/{completada}").json()["estado_actual"] == "En progreso"


@pytest.mark.parametrize("dias", [-5, -6, -30])
def test_una_fecha_anterior_a_la_finalizacion_no_se_permite(sesion, completada, dias):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(dias))
    assert r.status_code == 409 and r.json()["codigo"] == "SECUENCIA_INVALIDA"                         # CA-188
    assert r.json()["detalles"][0]["campo"] == "fecha_laboral" and r.json()["detalles"][0]["fecha_finalizacion"] == iso(-4)
    assert estado_de(completada) == "Completada" and contar("avance") == 2 and entradas() == []


@pytest.mark.parametrize("dias", [1, 5])
def test_una_fecha_futura_no_se_permite(sesion, completada, dias):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(dias))
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_FUTURA_NO_PERMITIDA"                  # CA-189
    assert estado_de(completada) == "Completada" and contar("avance") == 2


def test_se_admite_hoy_y_una_jornada_pasada_posterior_a_la_finalizacion_con_una_sola_entrada(sesion, completada):
    """CA-192: una reactivación en una jornada pasada posterior a F queda en su sitio de la secuencia."""
    cliente, csrf = sesion
    assert reactivar(cliente, csrf, completada, iso(-2), "Bloqueada", motivo_bloqueo="Sin acceso").status_code == 201
    assert [a.es_reactivacion for a in avances_de(completada)][-1] is True
    e = entradas()
    assert len(e) == 1 and e[0].fecha_laboral_registro.isoformat() == iso(-2)                           # CA-125: una sola, la de la jornada
    assert contar_entradas_de(iso(-2)) == 1                                                             # no hay una segunda entrada por ser jornada pasada


def test_hoy_es_una_fecha_valida(sesion, completada):
    cliente, csrf = sesion
    assert reactivar(cliente, csrf, completada, iso(0)).status_code == 201
    assert estado_de(completada) == "En progreso"


def test_la_fecha_debe_estar_cubierta_por_una_pertenencia(sesion, esc):
    cliente, csrf = sesion
    with get_owner_engine().begin() as c:
        c.execute(text("update pertenencia set desde = :d where persona_id = :p"), {"d": hoy() - timedelta(days=10), "p": esc.persona})
    a = planificar_actividad(cliente, csrf, iso(-9))
    avanzar(cliente, csrf, a, iso(-9), "Completada", "Hecho")
    r = reactivar(cliente, csrf, a, iso(-1))
    assert r.status_code == 201


# ============================== estados y textos (CA-128, CA-129, CA-270) ====================================

@pytest.mark.parametrize("estado", ["Pendiente", "En progreso", "Bloqueada"])
def test_una_actividad_que_no_esta_completada_no_se_reactiva(sesion, estado):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-3))
    if estado != "Pendiente":
        avanzar(cliente, csrf, a, iso(-2), estado, "Trabajo", "Falta acceso" if estado == "Bloqueada" else None)
    r = reactivar(cliente, csrf, a, iso(-1))
    assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_NO_COMPLETADA"
    assert estado_de(a) == estado and entradas() == []


def test_Completada_no_es_un_estado_de_reactivacion(sesion, completada):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(-2), "Completada")
    assert r.status_code == 422 and r.json()["codigo"] == "ESTADO_INVALIDO"
    assert contar("avance") == 2


@pytest.mark.parametrize("estado", ["Pausada", "", "en progreso", None])
def test_un_estado_fuera_de_los_cuatro_o_ausente_es_estado_invalido(sesion, completada, estado):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(-2), estado)
    assert r.status_code == 422 and r.json()["codigo"] == "ESTADO_INVALIDO" and contar("avance") == 2


@pytest.mark.parametrize("motivo", [None, "", "   "])
def test_bloqueada_sin_motivo_no_se_permite(sesion, completada, motivo):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(-2), "Bloqueada", "Me detuve", motivo)
    assert r.status_code == 422 and r.json()["codigo"] == "MOTIVO_BLOQUEO_OBLIGATORIO"                  # CA-128, CA-270
    assert estado_de(completada) == "Completada" and contar("avance") == 2


def test_bloqueada_con_motivo_conserva_el_motivo_en_el_historial(sesion, completada):
    cliente, csrf = sesion
    reactivar(cliente, csrf, completada, iso(-2), "Bloqueada", "Espero a un tercero", "Falta la firma")
    d = cliente.get(f"{API}/mi/actividades/{completada}").json()
    assert d["avances"][-1]["motivo_bloqueo"] == "Falta la firma" and d["avances"][-1]["estado"] == "Bloqueada"   # CA-271


def test_el_motivo_solo_existe_para_bloqueada(sesion, completada):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(-2), "En progreso", motivo_bloqueo="sobra")
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA" and contar("avance") == 2


@pytest.mark.parametrize("descripcion", [None, "", "   ", "\n\t"])
def test_sin_descripcion_no_se_permite(sesion, completada, descripcion):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(-2), "En progreso", descripcion)
    assert r.status_code == 422 and r.json()["codigo"] == "DESCRIPCION_OBLIGATORIA"                      # CA-129
    assert contar("avance") == 2


def test_el_maximo_de_texto_se_valida_con_su_valor(sesion, completada):
    cliente, csrf = sesion
    maximo = get_settings().text_max_description
    r = reactivar(cliente, csrf, completada, iso(-2), "En progreso", "x" * (maximo + 1))
    assert r.status_code == 422 and r.json()["codigo"] == "TEXTO_DEMASIADO_LARGO" and r.json()["detalles"][0]["maximo"] == maximo
    assert reactivar(cliente, csrf, completada, iso(-2), "En progreso", "x" * maximo).status_code == 201


@pytest.mark.parametrize("extra", [{"es_reactivacion": True}, {"actividad": "otra"}, {"titulo": "Otro"}, {"origen": "planificada"}])
def test_el_cuerpo_no_admite_otros_campos(sesion, completada, extra):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(-2), **extra)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA" and contar("avance") == 2


@pytest.mark.parametrize("fecha", ["mañana", "2026-13-40", ""])
def test_una_fecha_con_formato_incorrecto_es_una_solicitud_invalida(sesion, completada, fecha):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, fecha)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_el_texto_se_trata_como_datos(sesion, completada):
    cliente, csrf = sesion
    texto = "  <script>alert(1)</script> '; drop table avance; --  "
    assert reactivar(cliente, csrf, completada, iso(-2), "En progreso", texto).status_code == 201
    assert filas("select descripcion from avance where es_reactivacion")[0].descripcion == texto


# ============================== actividad marcada por error y jornadas cerradas ==============================

def test_una_actividad_marcada_por_error_no_se_reactiva(sesion):
    """Una Completada solo se marca (M3-05) si todos sus avances son de su jornada de origen."""
    cliente, csrf = sesion
    a = cliente.post(f"{API}/mi/actividades-no-planificadas", headers=con_clave(csrf),
                     json={"fecha_laboral": iso(-3), "titulo": "Imprevisto", "estado": "Completada",
                           "descripcion": "Lo resolví"}).json()["actividad"]["id"]
    assert cliente.post(f"{API}/mi/actividades/{a}/marca-error", json={"motivo": "Duplicada"},
                        headers=con_clave(csrf)).status_code == 200
    r = reactivar(cliente, csrf, a, iso(-2))
    assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_MARCADA_POR_ERROR" and contar("avance") == 1


def cerrar_dia(cliente, csrf, fecha):
    cliente.put(f"{API}/mi/bitacoras/{fecha}/resumen", json={"resumen": "Resumen"}, headers={**con_clave(csrf, None)})
    return cliente.post(f"{API}/mi/bitacoras/{fecha}/cierre", headers=con_clave(csrf))


def test_si_la_bitacora_de_la_fecha_esta_cerrada_se_rechaza_y_no_se_crea_nada(sesion, completada):
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(-2), "Otra del día")
    assert cerrar_dia(cliente, csrf, iso(-2)).status_code == 200
    r = reactivar(cliente, csrf, completada, iso(-2))
    assert r.status_code == 409 and r.json()["codigo"] == "BITACORA_CERRADA"
    assert estado_de(completada) == "Completada" and entradas() == [] and contar("avance") == 2


def test_no_hace_falta_reabrir_la_jornada_cerrada_de_la_finalizacion(sesion, completada):
    """D-04: reactivar es una ejecución nueva; la jornada donde se completó puede seguir cerrada."""
    cliente, csrf = sesion
    assert cerrar_dia(cliente, csrf, iso(-4)).status_code == 200
    antes = filas("select estado from bitacora where fecha_laboral = :f", f=hoy() - timedelta(days=4))[0].estado
    assert reactivar(cliente, csrf, completada, iso(-2)).status_code == 201
    assert antes == "cerrada" and filas("select estado from bitacora where fecha_laboral = :f", f=hoy() - timedelta(days=4))[0].estado == "cerrada"
    assert entradas("reapertura") == []


def test_la_bitacora_de_la_fecha_se_crea_en_la_misma_operacion_y_una_sola_vez(sesion, completada):
    cliente, csrf = sesion
    antes = contar("bitacora")
    r1 = reactivar(cliente, csrf, completada, iso(-2), "En progreso")
    assert r1.json()["bitacora_creada"] is True and contar("bitacora") == antes + 1
    avanzar(cliente, csrf, completada, iso(-2), "Completada", "De nuevo")
    r2 = reactivar(cliente, csrf, completada, iso(-2), "Pendiente")
    assert r2.json()["bitacora_creada"] is False and contar("bitacora") == antes + 1


# ============================== autorización y visibilidad (CA-127) ==========================================

def _otra_persona(identificador="otra.persona"):
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        otra = crear_persona(c, "Otra persona")
        crear_pertenencia(c, otra, crear_equipo(c, org, "Otro equipo"), desde=hoy() - timedelta(days=100))
        crear_identidad(c, otra, identificador, "contraseña-de-prueba-123")
    cliente = nuevo_cliente()
    return cliente, iniciar_sesion(cliente, identificador, "contraseña-de-prueba-123").json()["csrf_token"]


def test_la_actividad_completada_de_otra_persona_no_se_reactiva(sesion, completada):
    ajeno, csrf_ajeno = _otra_persona()
    r = reactivar(ajeno, csrf_ajeno, completada, iso(-2))
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"                        # CA-127
    inexistente = reactivar(ajeno, csrf_ajeno, str(uuid.uuid4()), iso(-2))
    assert (inexistente.status_code, inexistente.json()) == (r.status_code, r.json())                    # T-01
    assert estado_de(completada) == "Completada" and contar("avance") == 2


def test_un_supervisor_del_mismo_equipo_tampoco_la_reactiva(esc):
    cliente, csrf = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf, iso(-6))
    avanzar(cliente, csrf, a, iso(-5), "Completada", "Hecho")
    with get_owner_engine().begin() as c:
        sup = crear_persona(c, "Sara supervisora")
        crear_pertenencia(c, sup, esc.equipo, "supervisor", desde=hoy() - timedelta(days=50))
        crear_identidad(c, sup, "sara.sup", "contraseña-de-prueba-123")
    s = nuevo_cliente()
    csrf_s = iniciar_sesion(s, "sara.sup", "contraseña-de-prueba-123").json()["csrf_token"]
    r = reactivar(s, csrf_s, a, iso(-2))
    # M4-T6: la actividad es visible para la supervisora de su equipo: 403 y ya no 404 (convenciones 3.1, CA-127)
    assert r.status_code == 403 and r.json()["codigo"] == "OPERACION_NO_PERMITIDA" and estado_de(a) == "Completada"


def test_la_visibilidad_se_evalua_antes_que_el_cuerpo(sesion, completada):
    ajeno, csrf_ajeno = _otra_persona()
    r = reactivar(ajeno, csrf_ajeno, completada, iso(5), "Completada", "")
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"


def test_un_identificador_mal_formado_es_una_solicitud_invalida(sesion):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, "no-es-un-uuid")
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_sin_sesion_o_con_el_acceso_desactivado_no_se_reactiva(sesion, esc, completada):
    cliente, csrf = sesion
    r = nuevo_cliente().post(f"{API}/mi/actividades/{completada}/reactivacion", json={"fecha_laboral": iso(0), "estado": "En progreso", "descripcion": "x"})
    assert r.status_code == 401
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": esc.persona})
    r = reactivar(cliente, csrf, completada, iso(-2))
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO" and contar("avance") == 2


# ============================== después de reactivar ==========================================================

def test_tras_reactivar_se_pueden_registrar_avances_y_completar_de_nuevo(sesion, completada):
    cliente, csrf = sesion
    reactivar(cliente, csrf, completada, iso(-2), "En progreso")
    assert avanzar(cliente, csrf, completada, iso(-1), "Bloqueada", "Me paro", "Falta algo").status_code == 201
    assert avanzar(cliente, csrf, completada, iso(0), "Completada", "Ahora sí").status_code == 201
    assert estado_de(completada) == "Completada" and coherente()
    assert [a.estado for a in avances_de(completada)] == ["En progreso", "Completada", "En progreso", "Bloqueada", "Completada"]


def test_un_segundo_ciclo_de_reactivacion_es_valido(sesion, completada):
    cliente, csrf = sesion
    reactivar(cliente, csrf, completada, iso(-3), "En progreso")
    avanzar(cliente, csrf, completada, iso(-2), "Completada", "Otra vez")
    assert reactivar(cliente, csrf, completada, iso(-1), "Pendiente").status_code == 201
    assert estado_de(completada) == "Pendiente" and [a.es_reactivacion for a in avances_de(completada)].count(True) == 2


def test_la_finalizacion_relevante_es_la_del_ultimo_avance_del_orden_laboral(sesion, completada):
    """Tras un segundo ciclo la fecha mínima de reactivación es la de la SEGUNDA finalización, no la primera."""
    cliente, csrf = sesion
    reactivar(cliente, csrf, completada, iso(-3), "En progreso")
    avanzar(cliente, csrf, completada, iso(-1), "Completada", "Segunda")
    r = reactivar(cliente, csrf, completada, iso(-2), "En progreso")
    assert r.status_code == 409 and r.json()["codigo"] == "SECUENCIA_INVALIDA" and r.json()["detalles"][0]["fecha_finalizacion"] == iso(-1)
    assert reactivar(cliente, csrf, completada, iso(-1), "En progreso").status_code == 201


def test_sin_reactivar_no_se_admite_un_avance_entre_una_finalizacion_y_su_reactivacion(sesion, completada):
    """CA-207 con una reactivación REAL: dos finalizaciones separadas por una reactivación."""
    cliente, csrf = sesion
    reactivar(cliente, csrf, completada, iso(-2), "En progreso")
    avanzar(cliente, csrf, completada, iso(-1), "Completada", "Segunda")
    r = avanzar(cliente, csrf, completada, iso(-3), "En progreso", "Entre la primera finalización y la reactivación")
    assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_COMPLETADA"                         # CA-207
    assert contar("avance") == 4


def test_tras_reactivar_un_avance_retroactivo_anterior_a_la_primera_finalizacion_sigue_siendo_valido(sesion, completada):
    cliente, csrf = sesion
    reactivar(cliente, csrf, completada, iso(-2), "En progreso")
    assert avanzar(cliente, csrf, completada, iso(-5), "En progreso", "Retroactivo").status_code == 201
    assert estado_de(completada) == "En progreso" and coherente()                                         # CA-203, CA-78


def test_la_reactivacion_cuenta_como_actividad_continuada_para_cerrar_la_jornada(sesion, completada):
    cliente, csrf = sesion
    reactivar(cliente, csrf, completada, iso(-2), "En progreso")
    cliente.put(f"{API}/mi/bitacoras/{iso(-2)}/resumen", json={"resumen": "Retomé la actividad"}, headers=con_clave(csrf, None))
    assert cliente.post(f"{API}/mi/bitacoras/{iso(-2)}/cierre", headers=con_clave(csrf)).status_code == 200


def test_despues_de_reactivar_se_puede_planificar_su_continuacion(sesion, completada):
    """CA-210: una Completada que se ha reactivado admite su continuación planificada, sin crear otra actividad."""
    cliente, csrf = sesion
    r = cliente.post(f"{API}/mi/actividades/{completada}/continuaciones-planificadas", json={"fecha_laboral": iso(3)}, headers=con_clave(csrf))
    assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_COMPLETADA"
    reactivar(cliente, csrf, completada, iso(-2), "En progreso")
    r = cliente.post(f"{API}/mi/actividades/{completada}/continuaciones-planificadas", json={"fecha_laboral": iso(3), "descripcion": "Seguir"}, headers=con_clave(csrf))
    assert r.status_code == 201 and r.json()["actividad"]["id"] == completada and contar("actividad") == 1
    assert estado_de(completada) == "En progreso"


def test_el_detalle_y_el_listado_reflejan_la_reactivacion(sesion, completada):
    cliente, csrf = sesion
    reactivar(cliente, csrf, completada, iso(-2), "Bloqueada", motivo_bloqueo="Falta firma")
    d = cliente.get(f"{API}/mi/actividades/{completada}").json()
    assert [a["es_reactivacion"] for a in d["avances"]] == [False, False, True] and d["estado_actual"] == "Bloqueada"
    lista = cliente.get(f"{API}/mi/actividades", params={"estado": "Bloqueada"}).json()["elementos"]
    assert [x["id"] for x in lista] == [completada]
    dia = cliente.get(f"{API}/mi/bitacoras/{iso(-2)}").json()
    assert [a["es_reactivacion"] for a in dia["avances"]] == [True] and dia["actividades"][0]["estado_actual"] == "Bloqueada"


# ============================== auditoría y persistencia (CA-125) ============================================

def test_deja_una_unica_entrada_de_auditoria_con_el_autor_el_objeto_y_la_fecha_correctos(sesion, esc, completada):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(-2), "En progreso", "Retomo")
    [e] = entradas()
    assert (e.tipo_autor, e.autor_persona_id, e.propietaria_registro_id) == ("persona", esc.persona, esc.persona)
    assert e.tipo_objeto == "avance" and str(e.objeto_id) == r.json()["avance"]["id"]
    assert e.fecha_laboral_registro.isoformat() == iso(-2)
    assert e.valor_anterior["estado_actual"] == "Completada" and e.valor_anterior["actividad_id"] == completada
    assert e.valor_nuevo["estado_actual"] == "En progreso" and e.valor_nuevo["avance"]["es_reactivacion"] is True
    assert e.valor_nuevo["finalizacion_anterior"]["fecha_laboral"] == iso(-4) and e.valor_nuevo["bitacora_creada"] is True
    assert contar_entradas_de(iso(-2)) == 1                                                              # una sola entrada por operación


def test_una_reactivacion_en_hoy_tambien_se_audita(sesion, completada):
    cliente, csrf = sesion
    reactivar(cliente, csrf, completada, iso(0), "Pendiente")
    [e] = entradas()
    assert e.fecha_laboral_registro.isoformat() == iso(0)


def test_la_persistencia_es_coherente_en_la_base(sesion, completada):
    cliente, csrf = sesion
    reactivar(cliente, csrf, completada, iso(-2), "Bloqueada", "Espero", "Falta algo")
    fila = filas("select av.es_reactivacion, av.estado, av.motivo_bloqueo, av.descripcion, b.estado as bit from avance av "
                 "join bitacora b on b.id = av.bitacora_id where av.es_reactivacion")[0]
    assert (fila.es_reactivacion, fila.estado, fila.motivo_bloqueo, fila.descripcion, fila.bit) == (True, "Bloqueada", "Falta algo", "Espero", "abierta")
    assert estado_de(completada) == "Bloqueada" and coherente() and contar("auditoria") >= 1


# ============================== idempotencia, atomicidad y concurrencia ======================================

def test_la_cabecera_idempotency_key_es_obligatoria(sesion, completada):
    cliente, csrf = sesion
    r = reactivar(cliente, csrf, completada, iso(-2), clave=None)
    assert r.status_code == 400 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_OBLIGATORIA" and contar("avance") == 2


def test_repetir_la_misma_peticion_con_la_misma_clave_no_duplica(sesion, completada):
    cliente, csrf = sesion
    primera = reactivar(cliente, csrf, completada, iso(-2), clave="k-reactiva")
    segunda = reactivar(cliente, csrf, completada, iso(-2), clave="k-reactiva")
    assert primera.status_code == segunda.status_code == 201
    assert segunda.headers["idempotency-replayed"] == "true" and segunda.json() == primera.json()
    assert contar("avance") == 3 and len(entradas()) == 1


def test_reutilizar_la_clave_con_otra_peticion_se_rechaza(sesion, completada):
    cliente, csrf = sesion
    reactivar(cliente, csrf, completada, iso(-2), "En progreso", clave="k-reuso")
    r = reactivar(cliente, csrf, completada, iso(-2), "Pendiente", clave="k-reuso")
    assert r.status_code == 422 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_REUTILIZADA" and contar("avance") == 3


def test_una_peticion_rechazada_no_consume_la_clave(sesion, completada):
    cliente, csrf = sesion
    assert reactivar(cliente, csrf, completada, iso(-5), clave="k-corregible").status_code == 409      # antes de la finalización
    assert reactivar(cliente, csrf, completada, iso(-5), clave="k-corregible").status_code == 409
    assert reactivar(cliente, csrf, completada, iso(-2), "En progreso", "Otra descripción", clave="k-otra").status_code == 201


def test_si_falla_el_guardado_no_queda_ni_el_avance_ni_la_bitacora_ni_la_clave(sesion, completada, monkeypatch):
    cliente, csrf = sesion
    antes = (contar("avance"), contar("bitacora"), contar("clave_idempotencia"), contar("auditoria"))

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado de la auditoría")

    monkeypatch.setattr(servicio, "registrar_operacion_de_persona", falla)
    r = reactivar(cliente, csrf, completada, iso(-2), clave="k-atomica")
    assert r.status_code == 500 and "fallo simulado" not in r.text
    assert (contar("avance"), contar("bitacora"), contar("clave_idempotencia"), contar("auditoria")) == antes
    assert estado_de(completada) == "Completada"
    monkeypatch.undo()
    assert reactivar(cliente, csrf, completada, iso(-2), clave="k-atomica").status_code == 201


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


def test_reactivaciones_simultaneas_con_claves_distintas_reactivan_una_sola_vez(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    avanzar(cliente, csrf0, a, iso(-4), "Completada", "Hecho")
    clientes, csrf = _clientes(esc, 6)
    rs = _en_paralelo(6, lambda i: reactivar(clientes[i], csrf, a, iso(-2), "En progreso", f"Intento {i}"))
    assert sorted(r.status_code for r in rs) == [201] + [409] * 5
    assert {r.json()["codigo"] for r in rs if r.status_code == 409} == {"ACTIVIDAD_NO_COMPLETADA"}
    assert [x.es_reactivacion for x in avances_de(a)].count(True) == 1 and len(entradas()) == 1 and coherente()


def test_la_misma_reactivacion_simultanea_con_la_misma_clave_tiene_un_solo_efecto(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    avanzar(cliente, csrf0, a, iso(-4), "Completada", "Hecho")
    clientes, csrf = _clientes(esc, 6)
    rs = _en_paralelo(6, lambda i: reactivar(clientes[i], csrf, a, iso(-2), clave="clave-concurrente"))
    assert {r.status_code for r in rs} <= {201, 409}
    assert sum(r.status_code == 201 and "idempotency-replayed" not in r.headers for r in rs) == 1
    assert [x.es_reactivacion for x in avances_de(a)].count(True) == 1


def test_una_reactivacion_espera_a_quien_tiene_la_actividad_bloqueada_y_ve_su_resultado(esc):
    """Determinista: otra transacción tiene la actividad bloqueada y la reactiva por su cuenta. La petición
    debe ESPERAR y, al liberarse, ver que ya no está Completada (ACTIVIDAD_NO_COMPLETADA)."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    avanzar(cliente, csrf0, a, iso(-4), "Completada", "Hecho")
    clientes, csrf = _clientes(esc, 1)
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(reactivar(clientes[0], csrf, a, iso(-2))))
    with get_owner_engine().begin() as c:
        c.execute(text("select 1 from actividad where id = :a for update"), {"a": a})
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "la reactivación debía esperar al bloqueo de la actividad"
        b = c.execute(text("insert into bitacora (persona_id, fecha_laboral) select propietaria_id, :f from actividad where id = :a returning id"),
                      {"a": a, "f": hoy() - timedelta(days=3)}).scalar_one()
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion, es_reactivacion) "
                       "values (:a, :b, 'En progreso', 'Reactivada por otra vía', true)"), {"a": a, "b": b})
        c.execute(text("update actividad set estado_actual = 'En progreso' where id = :a"), {"a": a})
    hilo.join(timeout=10)
    assert resultado and resultado[0].status_code == 409 and resultado[0].json()["codigo"] == "ACTIVIDAD_NO_COMPLETADA"
    assert [x.es_reactivacion for x in avances_de(a)].count(True) == 1


def test_una_reactivacion_y_un_avance_simultaneos_dejan_el_estado_coherente(esc):
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-6))
    avanzar(cliente, csrf0, a, iso(-4), "Completada", "Hecho")
    clientes, csrf = _clientes(esc, 4)

    def tarea(i):
        if i == 0:
            return reactivar(clientes[0], csrf, a, iso(-2), "En progreso")
        return avanzar(clientes[i], csrf, a, iso(-2), "Bloqueada", f"Avance {i}", "Falta algo")

    rs = _en_paralelo(4, tarea)
    assert sum(r.status_code == 201 for r in rs) >= 1 and all(r.status_code in (201, 409) for r in rs)
    assert coherente()
    # ningún avance ordinario quedó justo detrás de la finalización: todos los aceptados van tras la reactivación
    secuencia = [(x.estado, x.es_reactivacion) for x in avances_de(a)]
    pos_rea = next(i for i, x in enumerate(secuencia) if x[1])
    assert secuencia[pos_rea - 1][0] == "Completada" and all(not r for _, r in secuencia[pos_rea + 1:])
