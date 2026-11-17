"""M1-T4 — finalizar una pertenencia (M1-06) y cancelar o sustituir operaciones programadas (M1-07) con PostgreSQL real y el rol de
PROVISIÓN (privilegios mínimos).

Criterios: CA-30, CA-31, CA-240, CA-244 a CA-247, CA-257, CA-258, CA-262, CA-278 y CA-279; reglas IR-02, IR-03, IR-26, IR-28 a IR-32
e IR-39. Las pruebas destructivas corren solo sobre ``smartwork_test``. Una orden = una transacción con el rol de provisión: si
falla, se deshace por completo y no deja pertenencias ni auditoría. Se reutilizan el escenario y los asistentes de
``test_traslados`` (equipo T: supervisor ST, colaboradores C1 y C2; equipo U: supervisor SU y colaborador CU; equipo W: solo su
supervisor SW; equipo X: vacío).
"""

import json
import random
import threading
import uuid
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.compartido import pertenencias
from app.compartido.politica_acceso import fecha_cubierta
from app.compartido.visibilidad import Registro, consultante_de, decidir_lectura
from app.db import get_engine, get_owner_engine, get_provision_engine
from app.errores import AppError
from app.provision import programacion
from app.provision.errores import ErrorDeProvision
from app.provision.programacion import CancelacionSolicitada, FinalizacionSolicitada, cancelar_operacion_programada, finalizar_pertenencia
from app.provision.servicio import CambioSolicitado, crear_equipo, crear_persona, registrar_traslado
from app.seguridad.contrasenas import calcular_hash
from tests.test_traslados import (  # noqa: F401  (fixtures y asistentes compartidos)
    HOY, _esperar_bloqueo_consultivo, _sin_violaciones, cambio, dia, foto, historial, mundo, operador, orden,
)
from tests.fabricas import crear_organizacion
from tests.utiles_http import nuevo_cliente, iniciar_sesion, API, cabeceras
from tests.utiles_m2 import contar, filas, planificar_actividad


def fin(m, persona, fecha):
    return FinalizacionSolicitada(m.p[persona], fecha)


def canc(m, persona, tipo, fecha):
    return CancelacionSolicitada(m.p[persona], tipo, fecha)


def finalizar(operador, *finalizaciones, **kw):
    return orden(finalizar_pertenencia, operador, finalizaciones=list(finalizaciones), **kw)


def cancelar(operador, *cancelaciones, **kw):
    return orden(cancelar_operacion_programada, operador, cancelaciones=list(cancelaciones), **kw)


def rechaza(codigo, funcion, operador, **kw) -> ErrorDeProvision:
    """La orden se rechaza con ese código y NO deja ningún cambio: pertenencias y auditoría idénticas."""
    antes = foto()
    with pytest.raises(ErrorDeProvision) as e:
        orden(funcion, operador, **kw)
    assert e.value.codigo == codigo
    assert foto() == antes, "una orden rechazada no puede dejar cambios parciales"
    return e.value


def rechaza_fin(codigo, operador, *finalizaciones, **kw):
    return rechaza(codigo, finalizar_pertenencia, operador, finalizaciones=list(finalizaciones), **kw)


def rechaza_canc(codigo, operador, *cancelaciones, **kw):
    return rechaza(codigo, cancelar_operacion_programada, operador, cancelaciones=list(cancelaciones), **kw)


def motivo(e: ErrorDeProvision) -> str:
    return e.detalles[0]["motivo"]


def entradas(operacion: str):
    return filas("select tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id, propietaria_registro_id, valor_anterior, valor_nuevo "
                 "from auditoria where operacion = :o order by momento, id", o=operacion)


def reloj_en(fecha: date, hora: int = 12):
    """Un reloj que marca ``fecha`` a mediodía en la zona de la organización de las pruebas (Bogotá)."""
    return lambda: datetime.combine(fecha, time(hora), tzinfo=ZoneInfo("America/Bogota")).astimezone(timezone.utc)


def supervisores_por_dia(mundo, equipo, desde=0, hasta=20):
    return [filas("select count(*) from pertenencia where equipo_id = :e and rol = 'supervisor' and daterange(desde, hasta_exclusivo, '[)') @> "
                  "cast(:f as date)", e=mundo.eq[equipo], f=dia(k))[0][0] for k in range(desde, hasta)]


# ===================================================== M1-06: finalizar =================================================

def test_finalizar_cierra_el_ultimo_intervalo_con_la_fecha_efectiva_y_no_abre_otro(operador, mundo):
    r = finalizar(operador, fin(mundo, "C2", dia(3)))
    assert historial(mundo, "C2") == [("T", "colaborador", HOY, dia(3))]
    assert r.operacion == "finalizacion_pertenencia" and [(n.tipo, n.fecha_efectiva) for n in r.nuevas] == [("finalizacion", dia(3))]
    assert r.canceladas == () and len(entradas("finalizacion_pertenencia")) == 1


def test_ca258_la_fecha_efectiva_debe_ser_posterior_a_hoy_en_el_limite_exacto(operador, mundo):
    for f in (HOY, dia(-1), dia(-30)):
        e = rechaza_fin("FECHA_EFECTIVA_INVALIDA", operador, fin(mundo, "C2", f))
        assert e.detalles[0]["campo"] == "fecha_efectiva" and motivo(e) == "fecha_efectiva_no_posterior_a_hoy"
    finalizar(operador, fin(mundo, "C2", dia(1)))                                     # mañana: el mínimo válido
    assert historial(mundo, "C2") == [("T", "colaborador", HOY, dia(1))]


def test_el_reloj_inyectable_mueve_el_limite_de_la_fecha_efectiva(operador, mundo):
    rechaza_fin("FECHA_EFECTIVA_INVALIDA", operador, fin(mundo, "C2", date(2030, 6, 1)), reloj=reloj_en(date(2030, 6, 1)))
    finalizar(operador, fin(mundo, "C2", date(2030, 6, 2)), reloj=reloj_en(date(2030, 6, 1)))
    assert historial(mundo, "C2")[-1] == ("T", "colaborador", HOY, date(2030, 6, 2))


def test_cerca_de_la_medianoche_de_la_organizacion_la_fecha_actual_es_la_de_su_zona(operador, mundo):
    """23:59 del 3 de marzo en Bogotá son las 04:59 UTC del día 4: hoy es el 3 y el 4 es válido; a las 00:00 del 4 ya no."""
    antes = lambda: datetime(2030, 3, 4, 4, 59, tzinfo=timezone.utc)      # noqa: E731
    despues = lambda: datetime(2030, 3, 4, 5, 0, tzinfo=timezone.utc)     # noqa: E731
    rechaza_fin("FECHA_EFECTIVA_INVALIDA", operador, fin(mundo, "C2", date(2030, 3, 4)), reloj=despues)
    finalizar(operador, fin(mundo, "C2", date(2030, 3, 4)), reloj=antes)


def test_la_fecha_efectiva_debe_ser_posterior_al_inicio_del_ultimo_intervalo_aunque_este_programado(operador, mundo):
    registrar = lambda *c: orden(registrar_traslado, operador, cambios=list(c))      # noqa: E731
    registrar(cambio(mundo, "C1", "U", "colaborador", dia(5)))
    for f in (dia(5), dia(4), dia(2)):
        assert motivo(rechaza_fin("PERTENENCIA_INVALIDA", operador, fin(mundo, "C1", f))) == "fecha_no_posterior_al_inicio_de_la_ultima_pertenencia"
    finalizar(operador, fin(mundo, "C1", dia(6)))
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(5)), ("U", "colaborador", dia(5), dia(6))]


def test_una_pertenencia_con_inicio_futuro_tambien_se_finaliza_despues_de_ese_inicio(operador, mundo):
    n = orden(crear_persona, operador, nombre="Futura", identificador_acceso="futura", equipo_id=mundo.eq["U"], rol="colaborador", desde=dia(10))
    mundo.p["N"] = n.persona_id
    rechaza_fin("PERTENENCIA_INVALIDA", operador, fin(mundo, "N", dia(10)))
    finalizar(operador, fin(mundo, "N", dia(12)))
    assert historial(mundo, "N") == [("U", "colaborador", dia(10), dia(12))]


def test_una_pertenencia_ya_finalizada_no_se_finaliza_otra_vez(operador, mundo):
    finalizar(operador, fin(mundo, "C2", dia(3)))
    assert motivo(rechaza_fin("PERTENENCIA_INVALIDA", operador, fin(mundo, "C2", dia(5)))) == "pertenencia_finalizada"


def test_una_persona_sin_pertenencia_o_inexistente_no_se_finaliza(operador, mundo):
    with get_owner_engine().begin() as c:
        sola = c.execute(text("insert into persona (nombre) values ('Sola') returning id")).scalar_one()
    mundo.p["SOLA"] = sola
    assert motivo(rechaza_fin("PERTENENCIA_INVALIDA", operador, fin(mundo, "SOLA", dia(3)))) == "sin_pertenencia"
    rechaza_fin("RECURSO_NO_DISPONIBLE", operador, FinalizacionSolicitada(uuid.uuid4(), dia(3)))


def test_la_lista_de_finalizaciones_no_puede_estar_vacia_ni_repetir_personas(operador, mundo):
    with pytest.raises(ErrorDeProvision) as e:
        finalizar(operador)
    assert e.value.codigo == "CAMPO_OBLIGATORIO"
    rechaza_fin("SOLICITUD_INVALIDA", operador, fin(mundo, "C2", dia(3)), fin(mundo, "C2", dia(4)))


def test_ca240_no_se_finaliza_al_unico_supervisor_de_un_equipo_con_colaboradores(operador, mundo):
    e = rechaza_fin("PERTENENCIA_INVALIDA", operador, fin(mundo, "ST", dia(4)))
    assert e.detalles[0]["motivo"] == "el_equipo_quedaria_sin_supervisor" and e.detalles[0]["equipo"] == str(mundo.eq["T"])
    assert e.detalles[0]["fecha"] == dia(4).isoformat()


def test_el_relevo_de_un_supervisor_que_se_finaliza_es_una_sola_operacion_atomica(operador, mundo):
    """ST se finaliza el día 4 y C1 asume la supervisión de T el mismo día."""
    r = finalizar(operador, fin(mundo, "ST", dia(4)), cambios=[cambio(mundo, "C1", "T", "supervisor", dia(4))])
    assert supervisores_por_dia(mundo, "T") == [1] * 20
    assert historial(mundo, "ST") == [("T", "supervisor", HOY, dia(4))] and historial(mundo, "C1")[-1] == ("T", "supervisor", dia(4), None)
    assert {n.tipo for n in r.nuevas} == {"finalizacion", "cambio_de_rol"} and len(entradas("finalizacion_pertenencia")) == 1


def test_un_relevo_con_un_dia_sin_supervisor_o_con_un_dia_de_solape_se_rechaza(operador, mundo):
    e = rechaza_fin("PERTENENCIA_INVALIDA", operador, fin(mundo, "ST", dia(4)), cambios=[cambio(mundo, "C1", "T", "supervisor", dia(5))])
    assert e.detalles[0]["fecha"] == dia(4).isoformat()
    rechaza_fin("PERTENENCIA_INVALIDA", operador, fin(mundo, "ST", dia(5)), cambios=[cambio(mundo, "C1", "T", "supervisor", dia(4))])


def test_la_validacion_de_un_equipo_empieza_en_la_primera_fecha_afectada_aunque_otra_orden_afecte_a_una_posterior(operador, mundo):
    """C1 asume la supervisión el día 4 y ST se finaliza el día 6: del 4 al 6 habría dos supervisores. La fecha de control del
    equipo es la MENOR de las afectadas (4), no la de la última que se procesa (6)."""
    e = rechaza_fin("PERTENENCIA_INVALIDA", operador, fin(mundo, "ST", dia(6)), cambios=[cambio(mundo, "C1", "T", "supervisor", dia(4))])
    assert motivo(e) == "el_equipo_tendria_mas_de_un_supervisor" and e.detalles[0]["fecha"] == dia(4).isoformat()


def test_se_finaliza_a_todo_un_equipo_en_la_misma_fecha(operador, mundo):
    finalizar(operador, fin(mundo, "ST", dia(4)), fin(mundo, "C1", dia(4)), fin(mundo, "C2", dia(4)))
    assert [historial(mundo, p)[-1][3] for p in ("ST", "C1", "C2")] == [dia(4)] * 3


def test_se_finaliza_al_supervisor_de_un_equipo_sin_colaboradores(operador, mundo):
    finalizar(operador, fin(mundo, "SW", dia(3)))
    assert historial(mundo, "SW") == [("W", "supervisor", HOY, dia(3))]


def test_finalizar_a_quien_tiene_el_acceso_desactivado_esta_permitido(operador, mundo):
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": mundo.p["C2"]})
    finalizar(operador, fin(mundo, "C2", dia(3)))
    assert historial(mundo, "C2")[-1][3] == dia(3)


def test_si_una_finalizacion_del_conjunto_falla_no_se_aplica_ninguna(operador, mundo):
    rechaza_fin("PERTENENCIA_INVALIDA", operador, fin(mundo, "C2", dia(3)), fin(mundo, "ST", dia(3)))
    assert historial(mundo, "C2") == [("T", "colaborador", HOY, None)]


def test_finalizar_conserva_el_historial_y_no_borra_nada(operador, mundo):
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "C1", "U", "colaborador", dia(3))])
    antes = {f[0]: f for f in filas("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia")}
    finalizar(operador, fin(mundo, "C1", dia(8)), fin(mundo, "C2", dia(8)))
    despues = {f[0]: f for f in filas("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia")}
    assert set(antes) == set(despues)                                              # no se borra ni se crea ninguna
    cambiadas = [i for i in antes if antes[i] != despues[i]]
    assert len(cambiadas) == 2 and all(antes[i][5] is None and despues[i][5] == dia(8) and antes[i][:5] == despues[i][:5] for i in cambiadas)


# ===================================================== CA-30, CA-31, CA-257, CA-262: finalizar y los registros de M2 =====

def _registros_de_m2():
    return (filas("select b::text from bitacora b order by id"), filas("select a::text from actividad a order by id"),
            filas("select p::text from planificacion p order by id"), filas("select v::text from avance v order by id"))


def test_ca31_ninguna_bitacora_actividad_planificacion_ni_avance_se_elimina_ni_se_modifica(operador, mundo):
    with get_owner_engine().begin() as c:
        for k in (0, 5, 9):
            b = c.execute(text("insert into bitacora (persona_id, fecha_laboral, resumen) values (:p, :f, 'x') returning id"),
                          {"p": mundo.p["C2"], "f": dia(k)}).scalar_one()
            a = c.execute(text("insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen) values (:p, :b, 'Informe', 'planificada') "
                               "returning id"), {"p": mundo.p["C2"], "b": b}).scalar_one()
            c.execute(text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) values (:a, :b, 'original', 'plan')"), {"a": a, "b": b})
    antes = _registros_de_m2()
    assert len(antes[0]) == 3 and len(antes[2]) == 3
    finalizar(operador, fin(mundo, "C2", dia(3)))                                  # la planificación de los días 5 y 9 queda después del fin
    assert _registros_de_m2() == antes


def test_ca262_la_planificacion_posterior_a_la_finalizacion_se_conserva_con_su_actividad_y_su_propietaria(operador, mundo):
    """Por HTTP real: C2 planifica el día 5 y el día 9, se le finaliza la pertenencia el día 3, y la planificación sigue
    siendo suya, se puede consultar mientras tiene pertenencia vigente y no se puede registrar nada nuevo desde el día 3 (CA-257)."""
    with get_owner_engine().begin() as c:
        c.execute(text("update identidad set hash_contrasena = :h where persona_id = :p"), {"h": calcular_hash("contraseña-de-prueba-123"), "p": mundo.p["C2"]})
    cliente = nuevo_cliente()
    r = iniciar_sesion(cliente, "c2", "contraseña-de-prueba-123")
    assert r.status_code == 201, r.text
    csrf = r.json()["csrf_token"]
    a5 = planificar_actividad(cliente, csrf, dia(5).isoformat(), "Plan del día cinco")
    a9 = planificar_actividad(cliente, csrf, dia(9).isoformat(), "Plan del día nueve")
    antes = _registros_de_m2()

    finalizar(operador, fin(mundo, "C2", dia(3)))

    assert _registros_de_m2() == antes                                              # nada cambia ni se elimina
    assert filas("select propietaria_id from actividad where id in (:a, :b)", a=a5, b=a9) == [(mundo.p["C2"],)] * 2
    for actividad, titulo in ((a5, "Plan del día cinco"), (a9, "Plan del día nueve")):          # CA-262: sigue consultable
        resp = cliente.get(f"{API}/mi/actividades/{actividad}")
        assert resp.status_code == 200 and titulo in resp.text
    assert dia(5).isoformat() in cliente.get(f"{API}/mi/bitacoras/{dia(5).isoformat()}").text
    # CA-257: ni la fecha efectiva ni las posteriores admiten registros; las anteriores, sí
    for f in (dia(3), dia(4), dia(30)):
        rechazo = cliente.post(f"{API}/mi/bitacoras/{f.isoformat()}/planificaciones", json={"titulo": "Nueva", "descripcion": ""},
                               headers={**cabeceras(csrf), "Idempotency-Key": str(uuid.uuid4())})
        assert rechazo.status_code == 422 and rechazo.json()["codigo"] == "FECHA_NO_CUBIERTA", f
    assert planificar_actividad(cliente, csrf, dia(2).isoformat(), "Antes del fin")


def test_ca257_la_fecha_efectiva_exacta_ya_no_esta_cubierta_y_el_dia_anterior_si(operador, mundo):
    finalizar(operador, fin(mundo, "C2", dia(7)))
    with Session(get_engine()) as db:
        assert fecha_cubierta(db, mundo.p["C2"], dia(6)) and not fecha_cubierta(db, mundo.p["C2"], dia(7))
        assert pertenencias.pertenencia_en_fecha(db, mundo.p["C2"], dia(7)) is None


def test_ca30_tras_la_baja_los_registros_anteriores_siguen_siendo_de_su_equipo_y_la_planificacion_conservada_no_tiene_equipo(operador, mundo):
    finalizar(operador, fin(mundo, "C2", dia(3)))
    with Session(get_engine()) as db:
        def lee(quien, fecha):
            return decidir_lectura(db, consultante_de(db, mundo.p[quien], hoy=dia(10)), Registro(mundo.p["C2"], fecha)).visible
        assert lee("C1", HOY) and lee("C1", dia(2)) and lee("ST", dia(2))             # jornadas anteriores a la baja: del equipo T
        assert not lee("C1", dia(3)) and not lee("C1", dia(9))                         # planificación conservada: sin equipo (RA-11)
        assert not consultante_de(db, mundo.p["C2"], hoy=dia(10)).puede_operar         # y la persona dada de baja ya no opera (IR-38)
        assert consultante_de(db, mundo.p["C2"], hoy=dia(2)).puede_operar              # antes de la fecha efectiva, sí


# ===================================================== M1-07: cancelar =================================================

def _traslado(operador, mundo, persona="C1", equipo="U", rol="colaborador", fecha=3):
    return orden(registrar_traslado, operador, cambios=[cambio(mundo, persona, equipo, rol, dia(fecha))])


def test_ca244_cancelar_un_traslado_programado_deja_a_la_persona_en_su_equipo_y_conserva_la_auditoria(operador, mundo):
    _traslado(operador, mundo)
    original = entradas("cambio_pertenencia")
    r = cancelar(operador, canc(mundo, "C1", "traslado", dia(3)))
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, None)]
    assert r.operacion == "cancelacion_operacion" and r.nuevas == () and r.historiales[mundo.p["C1"]][0].hasta_exclusivo is None
    assert entradas("cambio_pertenencia") == original                                # la entrada original NO se toca
    (tipo_autor, referencia, operacion, tipo_objeto, objeto_id, propietaria, anterior, nuevo), = entradas("cancelacion_operacion")
    assert (tipo_autor, operacion, tipo_objeto, objeto_id, propietaria) == ("provision", "cancelacion_operacion", "operacion_de_pertenencia", r.invocacion, None)
    assert referencia == f"operador:{operador.identificador}|invocacion:{r.invocacion}"


def test_la_entrada_de_cancelacion_conserva_los_valores_retirados_y_enlaza_con_la_operacion_original(operador, mundo):
    _traslado(operador, mundo)
    original_nuevo = entradas("cambio_pertenencia")[0][7]["cambios"][0]
    cancelar(operador, canc(mundo, "C1", "traslado", dia(3)))
    anterior, nuevo = entradas("cancelacion_operacion")[0][6:8]
    retirada = anterior["pertenencias_retiradas"][0]
    assert retirada["id"] == original_nuevo["pertenencia_nueva"]["id"]                # el enlace con la operación original
    assert (retirada["persona"], retirada["equipo"], retirada["rol"], retirada["desde"], retirada["hasta_exclusivo"]) == (
        str(mundo.p["C1"]), str(mundo.eq["U"]), "colaborador", dia(3).isoformat(), None)
    assert anterior["operaciones_canceladas"] == nuevo["operaciones_canceladas"] == [
        {"persona": str(mundo.p["C1"]), "tipo": "traslado", "fecha_efectiva": dia(3).isoformat(), "pertenencias_retiradas": [retirada["id"]]}]
    assert anterior["fines_anteriores"] == [{"id": original_nuevo["pertenencia_cerrada"]["id"], "persona": str(mundo.p["C1"]), "hasta_exclusivo": dia(3).isoformat()}]
    assert nuevo["fines_nuevos"] == [{"id": original_nuevo["pertenencia_cerrada"]["id"], "persona": str(mundo.p["C1"]), "hasta_exclusivo": None}]
    assert nuevo["operaciones_nuevas"] == [] and nuevo["pertenencias_nuevas"] == []


def test_ca245_una_operacion_ya_efectiva_no_se_cancela_en_el_limite_exacto_de_hoy(operador, mundo):
    """Con el reloj en el día 3 (a mediodía, hora de la organización) el traslado del día 3 ya es efectivo; con el reloj en el
    día 2, mañana: todavía se cancela."""
    _traslado(operador, mundo)
    antes = foto()
    with pytest.raises(ErrorDeProvision) as e:
        cancelar(operador, canc(mundo, "C1", "traslado", dia(3)), reloj=reloj_en(dia(3)))
    assert e.value.codigo == "FECHA_EFECTIVA_INVALIDA" and motivo(e.value) == "la_operacion_ya_es_efectiva" and foto() == antes
    with pytest.raises(ErrorDeProvision):
        cancelar(operador, canc(mundo, "C1", "traslado", dia(3)), reloj=reloj_en(dia(5)))
    cancelar(operador, canc(mundo, "C1", "traslado", dia(3)), reloj=reloj_en(dia(2)))
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, None)]


def test_ca245_el_alta_de_hoy_y_las_operaciones_pasadas_ya_son_efectivas(operador, mundo):
    rechaza_canc("FECHA_EFECTIVA_INVALIDA", operador, canc(mundo, "C1", "alta", HOY))
    rechaza_canc("FECHA_EFECTIVA_INVALIDA", operador, canc(mundo, "C1", "alta", dia(-3)))


def test_ca279_cancelar_un_cambio_de_rol_programado_conserva_el_rol_y_el_cruce_se_cancela_junto(operador, mundo):
    """ST pasa a colaborador y C1 a supervisor el día 4. Cancelar los dos juntos restituye ambos roles (S-20)."""
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "ST", "T", "colaborador", dia(4)), cambio(mundo, "C1", "T", "supervisor", dia(4))])
    cancelar(operador, canc(mundo, "ST", "cambio_de_rol", dia(4)), canc(mundo, "C1", "cambio_de_rol", dia(4)))
    assert historial(mundo, "ST") == [("T", "supervisor", HOY, None)] and historial(mundo, "C1") == [("T", "colaborador", HOY, None)]
    assert supervisores_por_dia(mundo, "T") == [1] * 20
    anterior = entradas("cancelacion_operacion")[0][6]
    assert len(anterior["operaciones_canceladas"]) == 2 and len(entradas("cancelacion_operacion")) == 1        # una sola entrada


def test_ca246_cancelar_solo_una_mitad_de_un_relevo_se_rechaza_sin_cambios(operador, mundo):
    """S-19: dejar a la entrante como supervisora y cancelar solo la salida dejaría dos supervisores; cancelar solo la entrada
    dejaría a los colaboradores sin supervisor."""
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "ST", "X", "supervisor", dia(5)), cambio(mundo, "C1", "T", "supervisor", dia(5))])
    sin = rechaza_canc("PERTENENCIA_INVALIDA", operador, canc(mundo, "C1", "cambio_de_rol", dia(5)))
    assert sin.detalles[0]["motivo"] == "el_equipo_quedaria_sin_supervisor" and sin.detalles[0]["equipo"] == str(mundo.eq["T"])
    dos = rechaza_canc("PERTENENCIA_INVALIDA", operador, canc(mundo, "ST", "traslado", dia(5)))
    assert dos.detalles[0]["motivo"] == "el_equipo_tendria_mas_de_un_supervisor"
    cancelar(operador, canc(mundo, "ST", "traslado", dia(5)), canc(mundo, "C1", "cambio_de_rol", dia(5)))         # los dos juntos: S-20
    assert supervisores_por_dia(mundo, "T") == [1] * 20


def test_ca278_cancelar_un_alta_futura_deja_a_la_persona_sin_pertenencia_y_sin_poder_operar(operador, mundo):
    n = orden(crear_persona, operador, nombre="Futura", identificador_acceso="futura", equipo_id=mundo.eq["U"], rol="colaborador", desde=dia(10))
    mundo.p["N"] = n.persona_id
    alta = entradas("alta")
    r = cancelar(operador, canc(mundo, "N", "alta", dia(10)))
    assert historial(mundo, "N") == [] and r.historiales[mundo.p["N"]] == ()
    assert entradas("alta") == alta                                                  # la operación original queda
    assert len(entradas("cancelacion_operacion")) == 1 and filas("select count(*) from persona where id = :p", p=n.persona_id) == [(1,)]   # la persona se conserva
    with Session(get_engine()) as db:
        assert pertenencias.pertenencia_en_fecha(db, n.persona_id, dia(10)) is None
        from app.compartido.politica_acceso import contexto_de_operacion
        with pytest.raises(AppError) as e:
            contexto_de_operacion(db, n.persona_id)
        assert e.value.codigo == "SIN_PERTENENCIA_VIGENTE"
    anterior = entradas("cancelacion_operacion")[0][6]
    assert anterior["pertenencias_retiradas"][0]["desde"] == dia(10).isoformat() and anterior["fines_anteriores"] == []


def test_una_alta_con_un_traslado_programado_despues_no_se_cancela_sola_sino_junto_con_el_traslado(operador, mundo):
    n = orden(crear_persona, operador, nombre="Futura", identificador_acceso="futura", equipo_id=mundo.eq["U"], rol="colaborador", desde=dia(10))
    mundo.p["N"] = n.persona_id
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "N", "T", "colaborador", dia(12))])
    assert motivo(rechaza_canc("PERTENENCIA_INVALIDA", operador, canc(mundo, "N", "alta", dia(10)))) == "hay_operaciones_posteriores_que_dependen_de_ella"
    cancelar(operador, canc(mundo, "N", "traslado", dia(12)), canc(mundo, "N", "alta", dia(10)))
    assert historial(mundo, "N") == []


def test_se_cancela_una_finalizacion_programada_y_el_intervalo_vuelve_a_no_tener_fin(operador, mundo):
    finalizar(operador, fin(mundo, "C2", dia(3)))
    cancelar(operador, canc(mundo, "C2", "finalizacion", dia(3)))
    assert historial(mundo, "C2") == [("T", "colaborador", HOY, None)]
    anterior, nuevo = entradas("cancelacion_operacion")[0][6:8]
    assert anterior["pertenencias_retiradas"] == [] and nuevo["fines_nuevos"][0]["hasta_exclusivo"] is None


def test_no_se_cancela_una_operacion_de_la_que_dependen_otras_pero_si_las_posteriores_primero(operador, mundo):
    _traslado(operador, mundo, "C1", "U", "colaborador", 3)
    _traslado(operador, mundo, "C1", "W", "colaborador", 6)
    assert motivo(rechaza_canc("PERTENENCIA_INVALIDA", operador, canc(mundo, "C1", "traslado", dia(3)))) == "hay_operaciones_posteriores_que_dependen_de_ella"
    cancelar(operador, canc(mundo, "C1", "traslado", dia(6)))
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(3)), ("U", "colaborador", dia(3), None)]
    cancelar(operador, canc(mundo, "C1", "traslado", dia(3)))
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, None)]


def test_se_cancela_una_cadena_entera_en_una_sola_operacion_en_cualquier_orden(operador, mundo):
    _traslado(operador, mundo, "C1", "U", "colaborador", 3)
    _traslado(operador, mundo, "C1", "W", "colaborador", 6)
    finalizar(operador, fin(mundo, "C1", dia(9)))
    cancelar(operador, canc(mundo, "C1", "finalizacion", dia(9)), canc(mundo, "C1", "traslado", dia(3)), canc(mundo, "C1", "traslado", dia(6)))
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, None)]
    assert len(entradas("cancelacion_operacion")) == 1


def test_una_operacion_inexistente_de_otro_tipo_repetida_o_de_una_persona_ajena_se_rechaza(operador, mundo):
    _traslado(operador, mundo)
    assert motivo(rechaza_canc("RECURSO_NO_DISPONIBLE", operador, canc(mundo, "C1", "traslado", dia(4)))) == "operacion_no_encontrada"
    assert motivo(rechaza_canc("RECURSO_NO_DISPONIBLE", operador, canc(mundo, "C2", "traslado", dia(3)))) == "operacion_no_encontrada"
    e = rechaza_canc("SOLICITUD_INVALIDA", operador, canc(mundo, "C1", "finalizacion", dia(3)))
    assert motivo(e) == "tipo_no_coincide" and e.detalles[0]["tipo_real"] == "traslado"
    assert motivo(rechaza_canc("SOLICITUD_INVALIDA", operador, canc(mundo, "C1", "traslado", dia(3)), canc(mundo, "C1", "traslado", dia(3)))) == "operacion_repetida"
    rechaza_canc("RECURSO_NO_DISPONIBLE", operador, CancelacionSolicitada(uuid.uuid4(), "traslado", dia(3)))
    with pytest.raises(ErrorDeProvision) as c:
        cancelar(operador)
    assert c.value.codigo == "CAMPO_OBLIGATORIO"


def test_los_traslados_efectivos_de_la_cadena_no_se_pueden_cancelar_aunque_haya_programados(operador, mundo):
    """El primer traslado se hace efectivo (reloj en el día 4); el segundo, programado, sí se cancela y el primero no."""
    _traslado(operador, mundo, "C1", "U", "colaborador", 3)
    _traslado(operador, mundo, "C1", "W", "colaborador", 6)
    rechaza_canc("FECHA_EFECTIVA_INVALIDA", operador, canc(mundo, "C1", "traslado", dia(3)), reloj=reloj_en(dia(4)))
    cancelar(operador, canc(mundo, "C1", "traslado", dia(6)), reloj=reloj_en(dia(4)))
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(3)), ("U", "colaborador", dia(3), None)]


# ===================================================== M1-07: sustituir ================================================

def test_ca247_sustituir_un_traslado_deja_vigente_solo_el_nuevo_y_la_auditoria_conserva_ambas_operaciones(operador, mundo):
    _traslado(operador, mundo, "C1", "U", "colaborador", 3)
    original = entradas("cambio_pertenencia")
    r = cancelar(operador, canc(mundo, "C1", "traslado", dia(3)), cambios=[cambio(mundo, "C1", "W", "colaborador", dia(5))])
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(5)), ("W", "colaborador", dia(5), None)]
    assert r.operacion == "sustitucion_operacion" and [(n.tipo, n.fecha_efectiva) for n in r.nuevas] == [("traslado", dia(5))]
    assert entradas("cambio_pertenencia") == original and len(entradas("sustitucion_operacion")) == 1 and entradas("cancelacion_operacion") == []
    anterior, nuevo = entradas("sustitucion_operacion")[0][6:8]
    assert anterior["operaciones_canceladas"][0]["tipo"] == "traslado" and nuevo["operaciones_nuevas"][0]["fecha_efectiva"] == dia(5).isoformat()
    assert nuevo["pertenencias_nuevas"][0]["equipo"] == str(mundo.eq["W"])
    assert nuevo["pertenencias_nuevas"][0]["id"] == str(r.historiales[mundo.p["C1"]][-1].id)


def test_sustituir_solo_la_fecha_de_un_traslado_conserva_el_destino(operador, mundo):
    _traslado(operador, mundo, "C1", "U", "colaborador", 3)
    cancelar(operador, canc(mundo, "C1", "traslado", dia(3)), cambios=[cambio(mundo, "C1", "U", "colaborador", dia(8))])
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(8)), ("U", "colaborador", dia(8), None)]


def test_una_sustitucion_invalida_no_cambia_nada_y_el_traslado_original_sigue_vigente(operador, mundo):
    _traslado(operador, mundo, "C1", "U", "colaborador", 3)
    for nuevo, codigo in ((cambio(mundo, "C1", "W", "colaborador", HOY), "FECHA_EFECTIVA_INVALIDA"),            # no es futura
                          (cambio(mundo, "C1", "T", "colaborador", dia(6)), "PERTENENCIA_INVALIDA")):              # T = origen: sin cambio
        rechaza_canc(codigo, operador, canc(mundo, "C1", "traslado", dia(3)), cambios=[nuevo])
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(3)), ("U", "colaborador", dia(3), None)]


def test_sustituir_un_relevo_de_supervisor_por_otro_con_otra_fecha_es_una_sola_operacion_atomica(operador, mundo):
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "ST", "X", "supervisor", dia(5)), cambio(mundo, "C1", "T", "supervisor", dia(5))])
    cancelar(operador, canc(mundo, "ST", "traslado", dia(5)), canc(mundo, "C1", "cambio_de_rol", dia(5)),
             cambios=[cambio(mundo, "ST", "X", "supervisor", dia(7)), cambio(mundo, "C1", "T", "supervisor", dia(7))])
    assert supervisores_por_dia(mundo, "T") == [1] * 20
    assert historial(mundo, "ST")[-1] == ("X", "supervisor", dia(7), None) and historial(mundo, "C1")[-1] == ("T", "supervisor", dia(7), None)


def test_sustituir_un_relevo_con_un_dia_de_hueco_se_rechaza_entero(operador, mundo):
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "ST", "X", "supervisor", dia(5)), cambio(mundo, "C1", "T", "supervisor", dia(5))])
    rechaza_canc("PERTENENCIA_INVALIDA", operador, canc(mundo, "ST", "traslado", dia(5)), canc(mundo, "C1", "cambio_de_rol", dia(5)),
                 cambios=[cambio(mundo, "ST", "X", "supervisor", dia(7)), cambio(mundo, "C1", "T", "supervisor", dia(8))])
    assert supervisores_por_dia(mundo, "T") == [1] * 20


def test_los_cambios_de_una_sustitucion_se_validan_como_en_el_traslado(operador, mundo):
    """Otra organización, rol no válido, persona repetida y equipo inexistente se rechazan y el traslado original sigue vigente."""
    _traslado(operador, mundo)
    with get_owner_engine().begin() as c:
        otra = crear_organizacion(c)
    ajeno = orden(crear_equipo, operador, organizacion_id=otra, nombre="Ajeno").equipo_id
    cancelacion = canc(mundo, "C1", "traslado", dia(3))
    assert motivo(rechaza_canc("PERTENENCIA_INVALIDA", operador, cancelacion, cambios=[CambioSolicitado(mundo.p["C1"], ajeno, "colaborador", dia(5))])) == "otra_organizacion"
    rechaza_canc("PERTENENCIA_INVALIDA", operador, cancelacion, cambios=[cambio(mundo, "C1", "W", "jefe", dia(5))])
    rechaza_canc("SOLICITUD_INVALIDA", operador, cancelacion, cambios=[cambio(mundo, "C1", "W", "colaborador", dia(5)), cambio(mundo, "C1", "X", "supervisor", dia(6))])
    rechaza_canc("RECURSO_NO_DISPONIBLE", operador, cancelacion, cambios=[CambioSolicitado(mundo.p["C1"], uuid.uuid4(), "colaborador", dia(5))])
    rechaza_fin("SOLICITUD_INVALIDA", operador, fin(mundo, "C2", dia(3)), cambios=[cambio(mundo, "C1", "U", "colaborador", dia(4)), cambio(mundo, "C1", "W", "colaborador", dia(5))])
    rechaza_fin("PERTENENCIA_INVALIDA", operador, fin(mundo, "C2", dia(3)), cambios=[cambio(mundo, "C1", "U", "jefe", dia(4))])
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(3)), ("U", "colaborador", dia(3), None)]


def test_se_sustituye_la_fecha_de_una_finalizacion(operador, mundo):
    finalizar(operador, fin(mundo, "C2", dia(4)))
    r = cancelar(operador, canc(mundo, "C2", "finalizacion", dia(4)), finalizaciones=[fin(mundo, "C2", dia(7))])
    assert historial(mundo, "C2") == [("T", "colaborador", HOY, dia(7))] and r.operacion == "sustitucion_operacion"


def test_se_sustituye_un_traslado_por_una_finalizacion(operador, mundo):
    _traslado(operador, mundo, "C1", "U", "colaborador", 3)
    cancelar(operador, canc(mundo, "C1", "traslado", dia(3)), finalizaciones=[fin(mundo, "C1", dia(4))])
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(4))]


def test_se_cancela_un_traslado_y_se_conserva_la_finalizacion_registrandola_de_nuevo_en_la_misma_operacion(operador, mundo):
    _traslado(operador, mundo, "C1", "U", "colaborador", 3)
    finalizar(operador, fin(mundo, "C1", dia(9)))
    assert motivo(rechaza_canc("PERTENENCIA_INVALIDA", operador, canc(mundo, "C1", "traslado", dia(3)))) == "hay_operaciones_posteriores_que_dependen_de_ella"
    cancelar(operador, canc(mundo, "C1", "traslado", dia(3)), canc(mundo, "C1", "finalizacion", dia(9)), finalizaciones=[fin(mundo, "C1", dia(9))])
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(9))]


# ===================================================== atomicidad, historial y auditoría ================================

def test_un_fallo_a_mitad_de_la_aplicacion_deshace_todo(operador, mundo, monkeypatch):
    _traslado(operador, mundo)
    antes = foto()

    def falla(*a, **k):
        raise RuntimeError("fallo simulado")
    monkeypatch.setattr(programacion, "_auditar", falla)
    with pytest.raises(RuntimeError):
        cancelar(operador, canc(mundo, "C1", "traslado", dia(3)), cambios=[cambio(mundo, "C1", "W", "colaborador", dia(5))])
    assert foto() == antes
    with pytest.raises(RuntimeError):
        finalizar(operador, fin(mundo, "C2", dia(3)))
    assert foto() == antes


def test_cancelar_y_sustituir_nunca_tocan_el_historial_efectivo(operador, mundo):
    """Un traslado ya efectivo (reloj en el día 4) y otro programado: lo efectivo queda idéntico tras cancelar lo programado."""
    _traslado(operador, mundo, "C1", "U", "colaborador", 3)
    _traslado(operador, mundo, "C1", "W", "colaborador", 6)
    efectivos = [f for f in filas("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia where persona_id = :p and desde <= :f",
                                  p=mundo.p["C1"], f=dia(3))]
    cancelar(operador, canc(mundo, "C1", "traslado", dia(6)), cambios=[cambio(mundo, "C1", "T", "colaborador", dia(9))], reloj=reloj_en(dia(4)))
    despues = filas("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia where persona_id = :p and desde <= :f",
                    p=mundo.p["C1"], f=dia(3))
    assert [f[:5] for f in despues] == [f[:5] for f in efectivos] and despues[0] == efectivos[0]


def test_una_sola_entrada_por_orden_y_sin_credenciales_ni_identificadores_de_acceso(operador, mundo):
    antes = contar("auditoria")
    _traslado(operador, mundo)
    cancelar(operador, canc(mundo, "C1", "traslado", dia(3)))
    finalizar(operador, fin(mundo, "C2", dia(4)))
    cancelar(operador, canc(mundo, "C2", "finalizacion", dia(4)), finalizaciones=[fin(mundo, "C2", dia(6))])
    assert contar("auditoria") == antes + 4
    texto = json.dumps(filas("select referencia_provision, valor_anterior, valor_nuevo from auditoria where tipo_objeto = 'operacion_de_pertenencia'"), default=str).lower()
    from tests.test_traslados import CREDENCIAL
    assert CREDENCIAL not in texto and "argon" not in texto and "identificador_acceso" not in texto and '"c1"' not in texto and '"c2"' not in texto


def test_las_entradas_anteriores_de_la_auditoria_no_cambian(operador, mundo):
    _traslado(operador, mundo)
    previas = filas("select * from auditoria order by id")
    cancelar(operador, canc(mundo, "C1", "traslado", dia(3)))
    assert filas("select * from auditoria where operacion <> 'cancelacion_operacion' order by id") == previas


# ===================================================== autorización =====================================================

def test_la_aplicacion_no_puede_ejecutar_estas_ordenes_aunque_se_llame_al_caso_de_uso(operador, mundo):
    _traslado(operador, mundo)
    antes = foto()
    for funcion, kw in ((finalizar_pertenencia, {"finalizaciones": [fin(mundo, "C2", dia(3))]}),
                        (cancelar_operacion_programada, {"cancelaciones": [canc(mundo, "C1", "traslado", dia(3))]})):
        with pytest.raises(DBAPIError) as e, get_engine().begin() as c:
            funcion(c, operador, **kw)
        assert e.value.orig.sqlstate == "42501" and foto() == antes


def test_la_base_rechaza_con_el_mismo_error_lo_que_el_servicio_no_llegue_a_detectar(operador, mundo, monkeypatch):
    """Defensa en profundidad: aunque la validación del servicio fallara, el disparador diferido rechaza la orden."""
    monkeypatch.setattr(programacion, "primera_violacion_de_supervision", lambda *a, **k: None)
    e = rechaza_fin("PERTENENCIA_INVALIDA", operador, fin(mundo, "ST", dia(4)))
    assert motivo(e) == "la_supervision_del_equipo_no_se_cumple"


# ===================================================== concurrencia =====================================================

def _en_hilo(resultado: dict, clave: str, funcion, **kw):
    def ejecutar():
        try:
            orden(funcion, kw.pop("operador"), **kw)
            resultado[clave] = "aceptada"
        except ErrorDeProvision as e:
            resultado[clave] = e.codigo
        except Exception as e:  # noqa: BLE001
            resultado[clave] = f"error inesperado: {type(e).__name__}"
    return threading.Thread(target=ejecutar)


def _carrera(operador, primera, segunda):
    """``primera`` se ejecuta sin confirmar; ``segunda`` arranca en otro hilo y debe quedar esperando un bloqueo; después se
    confirma la primera. Devuelve el resultado de la segunda."""
    resultado: dict = {}
    conexion = get_provision_engine().connect()
    try:
        funcion, kw = primera
        funcion(conexion, operador, **kw)
        hilo = _en_hilo(resultado, "b", segunda[0], operador=operador, **segunda[1])
        hilo.start()
        assert _esperar_bloqueo_consultivo(), "la segunda orden debía quedar esperando el bloqueo mientras la primera no confirma"
        conexion.commit()
    finally:
        conexion.close()
    hilo.join(20)
    assert not hilo.is_alive()
    return resultado["b"]


def test_cancelar_y_finalizar_a_la_misma_persona_se_serializan_y_la_segunda_ve_a_la_primera(operador, mundo):
    _traslado(operador, mundo)
    res = _carrera(operador,
                   (cancelar_operacion_programada, {"cancelaciones": [canc(mundo, "C1", "traslado", dia(3))]}),
                   (finalizar_pertenencia, {"finalizaciones": [fin(mundo, "C1", dia(6))]}))
    assert res == "aceptada"
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(6))]               # la finalización se apoyó en la cancelación ya confirmada
    _sin_violaciones()


def test_dos_cancelaciones_simultaneas_de_la_misma_operacion_dejan_una_sola_efectiva(operador, mundo):
    _traslado(operador, mundo)
    res = _carrera(operador,
                   (cancelar_operacion_programada, {"cancelaciones": [canc(mundo, "C1", "traslado", dia(3))]}),
                   (cancelar_operacion_programada, {"cancelaciones": [canc(mundo, "C1", "traslado", dia(3))]}))
    assert res == "RECURSO_NO_DISPONIBLE"
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, None)] and len(entradas("cancelacion_operacion")) == 1
    _sin_violaciones()


def test_la_salida_del_supervisor_de_un_equipo_sin_colaboradores_frente_al_alta_de_un_colaborador_se_serializa(operador, mundo):
    """Sesgo de escritura de IR-32 con una finalización: W tiene supervisor (SW) y ningún colaborador. A: SW se finaliza el día 2
    (válido). B: un colaborador entra en W el día 2 (válido si SW sigue). Juntos dejarían un colaborador sin supervisor."""
    res = _carrera(operador,
                   (finalizar_pertenencia, {"finalizaciones": [fin(mundo, "SW", dia(2))]}),
                   (crear_persona, {"nombre": "Nuevo", "identificador_acceso": "nuevo", "equipo_id": mundo.eq["W"], "rol": "colaborador", "desde": dia(2)}))
    assert res == "PERTENENCIA_INVALIDA"
    _sin_violaciones()


def test_cancelar_un_relevo_frente_a_un_alta_de_colaborador_en_el_mismo_equipo_se_serializa(operador, mundo):
    """El relevo (ST sale el día 5, C1 asume) se cancela mientras otra orden da de alta a un colaborador desde el día 5."""
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "ST", "X", "supervisor", dia(5)), cambio(mundo, "C1", "T", "supervisor", dia(5))])
    res = _carrera(operador,
                   (cancelar_operacion_programada, {"cancelaciones": [canc(mundo, "ST", "traslado", dia(5)), canc(mundo, "C1", "cambio_de_rol", dia(5))]}),
                   (crear_persona, {"nombre": "Nuevo", "identificador_acceso": "nuevo", "equipo_id": mundo.eq["T"], "rol": "colaborador", "desde": dia(6)}))
    assert res == "aceptada"                                                         # ST vuelve a ser el supervisor de T: el alta es válida
    assert supervisores_por_dia(mundo, "T") == [1] * 20
    _sin_violaciones()


def test_muchas_ordenes_concurrentes_de_todo_tipo_no_se_bloquean_entre_si_ni_rompen_ninguna_regla(operador, mundo):
    """Ocho trabajadores lanzan traslados, finalizaciones, cancelaciones y sustituciones al azar sobre las mismas personas y
    equipos. Ninguno debe fallar por un bloqueo mutuo ni por un error de la base, y el resultado cumple todas las reglas."""
    claves, equipos = list(mundo.p), list(mundo.eq)
    resultados, inesperados = [], []
    permitidos = {"aceptada", "PERTENENCIA_INVALIDA", "FECHA_EFECTIVA_INVALIDA", "RECURSO_NO_DISPONIBLE", "SOLICITUD_INVALIDA"}

    def programadas_de(persona):
        return filas("select desde, hasta_exclusivo from pertenencia where persona_id = :p order by desde", p=mundo.p[persona])

    def trabajador(semilla):
        azar = random.Random(semilla)
        for _ in range(6):
            persona = azar.choice(claves)
            fecha = dia(azar.randint(1, 5))
            accion = azar.choice(["traslado", "finalizar", "cancelar", "sustituir", "relevo"])
            try:
                if accion == "traslado":
                    orden(registrar_traslado, operador, cambios=[cambio(mundo, persona, azar.choice(equipos), azar.choice(["colaborador", "supervisor"]), fecha)])
                elif accion == "finalizar":
                    orden(finalizar_pertenencia, operador, finalizaciones=[fin(mundo, persona, fecha)])
                elif accion == "relevo":
                    otro = azar.choice([c for c in claves if c != persona])
                    orden(finalizar_pertenencia, operador, finalizaciones=[fin(mundo, persona, fecha)], cambios=[cambio(mundo, otro, "T", "supervisor", fecha)])
                else:
                    tramos = programadas_de(persona)
                    candidatas = [d for d, _ in tramos[1:] if d > HOY] or [h for _, h in tramos if h and h > HOY]
                    if not candidatas:
                        continue
                    f = azar.choice(candidatas)
                    tipo = azar.choice(["traslado", "cambio_de_rol", "traslado_y_cambio_de_rol", "finalizacion"])
                    nuevos = {"cambios": [cambio(mundo, persona, azar.choice(equipos), azar.choice(["colaborador", "supervisor"]), fecha)]} if accion == "sustituir" else {}
                    orden(cancelar_operacion_programada, operador, cancelaciones=[CancelacionSolicitada(mundo.p[persona], tipo, f)], **nuevos)
                resultados.append("aceptada")
            except ErrorDeProvision as e:
                resultados.append(e.codigo)
            except Exception as e:  # noqa: BLE001
                inesperados.append(repr(e)[:200])

    hilos = [threading.Thread(target=trabajador, args=(s,)) for s in range(8)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(180)
    assert not any(h.is_alive() for h in hilos), "algún trabajador quedó bloqueado"
    assert inesperados == [] and set(resultados) <= permitidos
    _sin_violaciones()
    aceptadas = filas("select count(*) from auditoria where operacion in ('cambio_pertenencia', 'finalizacion_pertenencia', 'cancelacion_operacion', 'sustitucion_operacion')")
    assert aceptadas == [(resultados.count("aceptada"),)]                            # cada orden aceptada dejó UNA entrada; ninguna rechazada dejó nada
