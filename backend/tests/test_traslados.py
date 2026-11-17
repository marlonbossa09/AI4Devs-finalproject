"""M1-T3 — traslados y cambios de rol (contrato M1-05) con PostgreSQL real y el rol de PROVISIÓN (privilegios mínimos).

Criterios: CA-11 a CA-14, CA-240 a CA-243, CA-248 y CA-249; reglas IR-02, IR-03, IR-28, IR-30, IR-32 e IR-35. Las pruebas
destructivas corren solo sobre ``smartwork_test``. Una orden = una transacción con el rol de provisión: si falla, se deshace
por completo y no deja pertenencias ni auditoría.
"""

import json
import random
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido import pertenencias
from app.compartido.visibilidad import Registro, consultante_de, decidir_lectura
from app.db import get_engine, get_owner_engine, get_provision_engine
from app.provision.errores import ErrorDeProvision
from app.provision.linea_temporal import Tramo, primera_irregularidad_de_persona, primera_violacion_de_supervision
from app.provision.operadores import Operador, crear_primer_operador
from app.provision.servicio import CambioSolicitado, crear_equipo, crear_persona, registrar_traslado
from tests.fabricas import crear_organizacion, hoy
from tests.utiles_m2 import contar, filas

CREDENCIAL = "credencial-de-prueba-123"
HOY = hoy()


def dia(n: int) -> date:
    return HOY + timedelta(days=n)


@dataclass
class Mundo:
    org: uuid.UUID
    eq: dict
    p: dict


def orden(funcion, operador, **kw):
    """Una orden = una transacción con el rol de provisión."""
    with get_provision_engine().begin() as c:
        return funcion(c, operador, **kw)


@pytest.fixture()
def operador() -> Operador:
    with get_owner_engine().begin() as c:
        return crear_primer_operador(c, "Operadora.Uno", CREDENCIAL, uuid.uuid4())


@pytest.fixture()
def mundo(operador) -> Mundo:
    """Provisionado con las órdenes oficiales. Equipo T: supervisor ST y colaboradores C1 y C2. Equipo U: supervisor SU y
    colaborador CU. Equipo W: solo su supervisor SW (sin colaboradores). Equipo X: vacío (en provisión)."""
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c)
    eq = {n: orden(crear_equipo, operador, organizacion_id=org, nombre=n).equipo_id for n in ("T", "U", "W", "X")}
    p: dict = {}
    for clave, equipo, rol in (("ST", "T", "supervisor"), ("C1", "T", "colaborador"), ("C2", "T", "colaborador"),
                               ("SU", "U", "supervisor"), ("CU", "U", "colaborador"), ("SW", "W", "supervisor")):
        p[clave] = orden(crear_persona, operador, nombre=clave, identificador_acceso=clave.lower(), equipo_id=eq[equipo],
                         rol=rol, desde=HOY).persona_id
    return Mundo(org, eq, p)


def cambio(m: Mundo, persona: str, equipo: str, rol: str, fecha: date) -> CambioSolicitado:
    return CambioSolicitado(m.p[persona], m.eq[equipo], rol, fecha)


def trasladar(operador, m: Mundo, *cambios, **kw):
    return orden(registrar_traslado, operador, cambios=list(cambios), **kw)


def rechaza(codigo, operador, m: Mundo, *cambios, **kw) -> ErrorDeProvision:
    """La orden se rechaza con ese código y NO deja ningún cambio: pertenencias y auditoría idénticas."""
    antes = foto()
    with pytest.raises(ErrorDeProvision) as e:
        trasladar(operador, m, *cambios, **kw)
    assert e.value.codigo == codigo
    assert foto() == antes, "una orden rechazada no puede dejar cambios parciales"
    return e.value


def foto():
    return (filas("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia order by id"),
            filas("select id, operacion, objeto_id from auditoria order by id"))


def historial(m: Mundo, persona: str):
    return filas("select e.nombre, p.rol, p.desde, p.hasta_exclusivo from pertenencia p join equipo e on e.id = p.equipo_id "
                 "where p.persona_id = :p order by p.desde", p=m.p[persona])


def motivo(error: ErrorDeProvision) -> str:
    return error.detalles[0]["motivo"]


# ===================================================== traslados y cambios de rol válidos =================================

def test_un_traslado_programado_cierra_la_pertenencia_actual_y_abre_la_nueva_el_mismo_dia(operador, mundo):
    r = trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)))
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(3)), ("U", "colaborador", dia(3), None)]
    a = r.cambios[0]
    assert (a.tipo, a.equipo_anterior_id, a.equipo_id, a.rol_anterior, a.rol) == ("traslado", mundo.eq["T"], mundo.eq["U"], "colaborador", "colaborador")


def test_ca12_la_persona_figura_en_el_equipo_nuevo_y_deja_de_figurar_en_el_anterior(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)))
    composicion = lambda equipo, fecha: sorted(f[0] for f in filas(   # noqa: E731
        "select p.nombre from pertenencia pe join persona p on p.id = pe.persona_id where pe.equipo_id = :e and "
        "daterange(pe.desde, pe.hasta_exclusivo, '[)') @> cast(:f as date)", e=mundo.eq[equipo], f=fecha))
    assert "C1" in composicion("T", dia(2)) and "C1" not in composicion("U", dia(2))        # hasta el día anterior sigue en T
    assert "C1" not in composicion("T", dia(3)) and "C1" in composicion("U", dia(3))         # desde la fecha efectiva, en U
    assert "C1" in composicion("U", dia(100)) and "C1" not in composicion("T", dia(100))


def test_ca14_en_cada_fecha_la_persona_pertenece_a_un_unico_equipo_incluidos_traslados_sucesivos(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)))
    trasladar(operador, mundo, cambio(mundo, "C1", "T", "colaborador", dia(7)))
    for k in range(0, 30):                                      # la persona empieza hoy (alta de la provisión)
        cubiertas = filas("select count(*) from pertenencia where persona_id = :p and daterange(desde, hasta_exclusivo, '[)') @> cast(:f as date)",
                          p=mundo.p["C1"], f=dia(k))
        assert cubiertas == [(1,)], f"día {k}: {cubiertas}"


def test_ca248_la_linea_temporal_resultante_no_tiene_solapes_ni_huecos(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)))
    trasladar(operador, mundo, cambio(mundo, "C1", "T", "colaborador", dia(9)))
    filas_ = filas("select persona_id, rol, desde, hasta_exclusivo from pertenencia where persona_id = :p", p=mundo.p["C1"])
    assert primera_irregularidad_de_persona([Tramo(*f) for f in filas_]) is None
    assert len(filas_) == 3


def test_el_supervisor_de_un_equipo_sin_colaboradores_se_puede_trasladar(operador, mundo):
    """W solo tiene a su supervisor: al irse, W queda en provisión sin supervisor (CA-250), lo que IR-32 permite."""
    r = trasladar(operador, mundo, cambio(mundo, "SW", "X", "supervisor", dia(2)))
    assert historial(mundo, "SW") == [("W", "supervisor", HOY, dia(2)), ("X", "supervisor", dia(2), None)]
    assert r.cambios[0].tipo == "traslado"


def test_el_cambio_de_rol_cruzado_en_el_mismo_equipo_es_una_operacion_valida(operador, mundo):
    """ST pasa a colaborador de T y C1 a supervisor de T el mismo día: dos cambios de rol, una operación atómica."""
    r = trasladar(operador, mundo, cambio(mundo, "ST", "T", "colaborador", dia(4)), cambio(mundo, "C1", "T", "supervisor", dia(4)))
    assert historial(mundo, "ST") == [("T", "supervisor", HOY, dia(4)), ("T", "colaborador", dia(4), None)]
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(4)), ("T", "supervisor", dia(4), None)]
    assert {a.tipo for a in r.cambios} == {"cambio_de_rol"}


def test_ca242_el_relevo_de_supervisor_acepta_y_el_equipo_no_queda_ningun_dia_sin_supervisor(operador, mundo):
    """ST sale de T hacia X y C1 asume la supervisión de T el mismo día."""
    trasladar(operador, mundo, cambio(mundo, "ST", "X", "supervisor", dia(5)), cambio(mundo, "C1", "T", "supervisor", dia(5)))
    for k in range(0, 15):
        supervisores = filas("select count(*) from pertenencia where equipo_id = :e and rol = 'supervisor' and "
                             "daterange(desde, hasta_exclusivo, '[)') @> cast(:f as date)", e=mundo.eq["T"], f=dia(k))
        assert supervisores == [(1,)], f"día {k}"


def test_un_traslado_con_cambio_de_rol_a_la_vez_se_clasifica_como_tal(operador, mundo):
    r = trasladar(operador, mundo, cambio(mundo, "CU", "X", "supervisor", dia(3)))              # CU deja U (que sigue con SU) y supervisa X
    assert r.cambios[0].tipo == "traslado_y_cambio_de_rol"
    assert historial(mundo, "CU")[-1] == ("X", "supervisor", dia(3), None)


def test_dos_supervisores_pueden_intercambiar_sus_equipos_en_una_sola_operacion(operador, mundo):
    """ST pasa a supervisar U y SU a supervisar T el mismo día: cada equipo conserva exactamente un supervisor."""
    r = trasladar(operador, mundo, cambio(mundo, "ST", "U", "supervisor", dia(6)), cambio(mundo, "SU", "T", "supervisor", dia(6)))
    assert {a.tipo for a in r.cambios} == {"traslado"}
    assert historial(mundo, "ST")[-1] == ("U", "supervisor", dia(6), None) and historial(mundo, "SU")[-1] == ("T", "supervisor", dia(6), None)
    for k in range(5, 9):
        for equipo in ("T", "U"):
            assert filas("select count(*) from pertenencia where equipo_id = :e and rol = 'supervisor' and "
                         "daterange(desde, hasta_exclusivo, '[)') @> cast(:f as date)", e=mundo.eq[equipo], f=dia(k)) == [(1,)]


def test_dos_traslados_sucesivos_programados_son_validos_y_el_segundo_se_apoya_en_el_primero(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(5)))
    trasladar(operador, mundo, cambio(mundo, "C1", "T", "colaborador", dia(9)))
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(5)), ("U", "colaborador", dia(5), dia(9)), ("T", "colaborador", dia(9), None)]


def test_el_traslado_hacia_un_equipo_vacio_como_supervisor_es_valido(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "C2", "X", "supervisor", dia(2)))
    assert historial(mundo, "C2")[-1] == ("X", "supervisor", dia(2), None)


def test_ca11_una_persona_recien_creada_en_una_fecha_futura_se_puede_trasladar_despues_de_su_inicio(operador, mundo):
    nueva = orden(crear_persona, operador, nombre="Nueva", identificador_acceso="nueva", equipo_id=mundo.eq["U"], rol="colaborador", desde=dia(10))
    mundo.p["N"] = nueva.persona_id
    trasladar(operador, mundo, cambio(mundo, "N", "T", "colaborador", dia(12)))
    assert historial(mundo, "N") == [("U", "colaborador", dia(10), dia(12)), ("T", "colaborador", dia(12), None)]


# ===================================================== fechas efectivas ===================================================

def test_ca243_una_fecha_efectiva_igual_o_anterior_a_hoy_se_rechaza_y_la_posterior_se_acepta(operador, mundo):
    for f in (HOY, dia(-1), dia(-30)):
        e = rechaza("FECHA_EFECTIVA_INVALIDA", operador, mundo, cambio(mundo, "C1", "U", "colaborador", f))
        assert e.detalles == [{"campo": "fecha_efectiva", "indice": 0}]
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(1)))
    assert historial(mundo, "C1")[-1] == ("U", "colaborador", dia(1), None)


def test_la_fecha_actual_la_da_un_reloj_inyectable_y_se_mide_en_la_zona_de_la_organizacion(operador, mundo):
    """03:00 UTC del 10 de enero de 2030 son las 22:00 del día 9 en Bogotá (UTC-5): hoy es el 9."""
    reloj = lambda: datetime(2030, 1, 10, 3, 0, tzinfo=timezone.utc)      # noqa: E731
    rechaza("FECHA_EFECTIVA_INVALIDA", operador, mundo, cambio(mundo, "C1", "U", "colaborador", date(2030, 1, 9)), reloj=reloj)
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", date(2030, 1, 10)), reloj=reloj)
    assert historial(mundo, "C1")[-1] == ("U", "colaborador", date(2030, 1, 10), None)


def test_cerca_de_la_medianoche_de_la_organizacion_el_cambio_de_dia_se_mide_en_su_zona(operador, mundo):
    antes = lambda: datetime(2030, 3, 4, 4, 59, tzinfo=timezone.utc)      # 23:59 del día 3 en Bogotá  # noqa: E731
    despues = lambda: datetime(2030, 3, 4, 5, 0, tzinfo=timezone.utc)     # 00:00 del día 4 en Bogotá  # noqa: E731
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", date(2030, 3, 4)), reloj=antes)       # el 4 es posterior a «hoy» (3)
    rechaza("FECHA_EFECTIVA_INVALIDA", operador, mundo, cambio(mundo, "C2", "U", "colaborador", date(2030, 3, 4)), reloj=despues)


def test_el_reloj_inyectable_solo_afecta_a_la_orden_que_lo_recibe(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", date(2030, 1, 10)), reloj=lambda: datetime(2030, 1, 1, tzinfo=timezone.utc))
    rechaza("FECHA_EFECTIVA_INVALIDA", operador, mundo, cambio(mundo, "C2", "U", "colaborador", dia(-1)))         # sin reloj: el real


def test_un_traslado_no_puede_fijarse_en_o_antes_del_inicio_de_la_ultima_pertenencia_ni_modificar_lo_programado(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(5)))
    for f in (dia(5), dia(3), dia(1)):
        assert motivo(rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "C1", "T", "colaborador", f))) == \
            "fecha_no_posterior_al_inicio_de_la_ultima_pertenencia"
    trasladar(operador, mundo, cambio(mundo, "C1", "T", "colaborador", dia(6)))                 # uno posterior sí


def test_una_pertenencia_con_inicio_futuro_solo_se_traslada_despues_de_ese_inicio(operador, mundo):
    n = orden(crear_persona, operador, nombre="Futura", identificador_acceso="futura", equipo_id=mundo.eq["U"], rol="colaborador", desde=dia(10))
    mundo.p["F"] = n.persona_id
    for f in (dia(10), dia(5)):
        rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "F", "T", "colaborador", f))


# ===================================================== supervisión: IR-03 e IR-32 =========================================

def test_ca241_trasladar_al_unico_supervisor_de_un_equipo_con_colaboradores_se_rechaza_sin_cambios(operador, mundo):
    e = rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "ST", "X", "supervisor", dia(3)))
    assert e.detalles[0]["motivo"] == "el_equipo_quedaria_sin_supervisor" and e.detalles[0]["equipo"] == str(mundo.eq["T"])
    assert e.detalles[0]["fecha"] == dia(3).isoformat()


def test_un_cambio_de_rol_que_deja_a_colaboradores_sin_supervisor_se_rechaza(operador, mundo):
    rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "ST", "T", "colaborador", dia(3)))


def test_la_base_rechaza_con_el_mismo_error_lo_que_el_servicio_no_llegue_a_detectar(operador, mundo, monkeypatch):
    """Defensa en profundidad: aunque la validación del servicio fallara, el disparador diferido de la base rechaza la orden
    (se fuerza su comprobación dentro de la orden) con el mismo código y sin dejar nada."""
    from app.provision import servicio
    monkeypatch.setattr(servicio, "primera_violacion_de_supervision", lambda *a, **k: None)
    e = rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "ST", "X", "supervisor", dia(3)))
    assert e.detalles[0]["motivo"] == "la_supervision_del_equipo_no_se_cumple"


def test_dos_supervisores_a_la_vez_se_rechazan(operador, mundo):
    e = rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "C1", "T", "supervisor", dia(3)))
    assert motivo(e) == "el_equipo_tendria_mas_de_un_supervisor"


def test_el_relevo_con_un_dia_de_hueco_se_rechaza(operador, mundo):
    """ST sale el día 5 y C1 asume el día 6: el 5 el equipo no tiene supervisor."""
    e = rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "ST", "X", "supervisor", dia(5)), cambio(mundo, "C1", "T", "supervisor", dia(6)))
    assert e.detalles[0]["fecha"] == dia(5).isoformat() and e.detalles[0]["motivo"] == "el_equipo_quedaria_sin_supervisor"


def test_el_relevo_con_un_solape_de_un_dia_se_rechaza(operador, mundo):
    rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "ST", "X", "supervisor", dia(6)), cambio(mundo, "C1", "T", "supervisor", dia(5)))


def test_ca241_relevo_que_deja_sin_supervisor_al_equipo_de_origen_del_entrante(operador, mundo):
    """SU releva a ST en T, pero entonces U (con CU) se queda sin supervisor: se rechaza el conjunto entero."""
    antes_u = historial(mundo, "SU")
    e = rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "ST", "X", "supervisor", dia(6)), cambio(mundo, "SU", "T", "supervisor", dia(6)))
    assert e.detalles[0]["equipo"] == str(mundo.eq["U"]) and historial(mundo, "SU") == antes_u


def test_un_colaborador_no_puede_entrar_en_un_equipo_sin_supervisor_desde_esa_fecha(operador, mundo):
    rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "C1", "X", "colaborador", dia(3)))


def test_un_colaborador_entra_en_un_equipo_desde_el_dia_en_que_empieza_su_supervisor_y_no_antes(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "C2", "X", "supervisor", dia(2)))                 # X tendrá supervisor desde el día 2
    trasladar(operador, mundo, cambio(mundo, "C1", "X", "colaborador", dia(2)))                # el mismo día: válido
    assert historial(mundo, "C1")[-1] == ("X", "colaborador", dia(2), None)
    e = rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "CU", "X", "colaborador", dia(1)))      # el día 1 X aún no tiene supervisor
    assert e.detalles[0]["fecha"] == dia(1).isoformat()


def test_un_supervisor_con_fin_programado_no_admite_colaboradores_despues_de_ese_fin(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "SW", "X", "supervisor", dia(4)))          # W queda sin supervisor desde el día 4
    rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "C1", "W", "colaborador", dia(5)))
    rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "C1", "W", "colaborador", dia(2)))


def test_ir32_se_valida_en_cualquier_fecha_posterior_no_solo_en_la_fecha_efectiva(operador, mundo):
    """El supervisor de W (sin colaboradores) se va el día 8: es válido. Un colaborador que llegue a W el día 3 estaría cubierto
    ese día, pero no desde el 8: se rechaza aunque la fecha efectiva (3) sí tenga supervisor."""
    trasladar(operador, mundo, cambio(mundo, "SW", "X", "supervisor", dia(8)))
    e = rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "C1", "W", "colaborador", dia(3)))
    assert e.detalles[0]["fecha"] == dia(8).isoformat()


# ===================================================== validaciones de la solicitud ======================================

def test_la_lista_de_cambios_no_puede_estar_vacia(operador, mundo):
    with pytest.raises(ErrorDeProvision) as e:
        trasladar(operador, mundo)
    assert e.value.codigo == "CAMPO_OBLIGATORIO"


def test_una_persona_no_puede_figurar_dos_veces_en_la_misma_operacion(operador, mundo):
    rechaza("SOLICITUD_INVALIDA", operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)), cambio(mundo, "C1", "W", "colaborador", dia(4)))


@pytest.mark.parametrize("rol", ["", "administrador", "SUPERVISOR", None])
def test_el_rol_debe_ser_colaborador_o_supervisor(operador, mundo, rol):
    rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "C1", "U", rol, dia(3)))


def test_una_persona_inexistente_se_rechaza(operador, mundo):
    rechaza("RECURSO_NO_DISPONIBLE", operador, mundo, CambioSolicitado(uuid.uuid4(), mundo.eq["U"], "colaborador", dia(3)))


def test_un_equipo_inexistente_se_rechaza(operador, mundo):
    rechaza("RECURSO_NO_DISPONIBLE", operador, mundo, CambioSolicitado(mundo.p["C1"], uuid.uuid4(), "colaborador", dia(3)))


def test_un_cambio_sin_efecto_se_rechaza(operador, mundo):
    assert motivo(rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "C1", "T", "colaborador", dia(3)))) == "sin_cambio"


def test_no_se_traslada_entre_organizaciones(operador, mundo):
    with get_owner_engine().begin() as c:
        otra = crear_organizacion(c)
    ajeno = orden(crear_equipo, operador, organizacion_id=otra, nombre="Ajeno").equipo_id
    e = rechaza("PERTENENCIA_INVALIDA", operador, mundo, CambioSolicitado(mundo.p["C1"], ajeno, "supervisor", dia(3)))
    assert motivo(e) == "otra_organizacion"


def test_una_persona_con_pertenencia_finalizada_no_se_traslada(operador, mundo):
    with get_owner_engine().begin() as c:        # una finalización (M1-T4) todavía no existe como orden: se prepara con el propietario
        c.execute(text("update pertenencia set hasta_exclusivo = :f where persona_id = :p"), {"f": dia(20), "p": mundo.p["C2"]})
    assert motivo(rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "C2", "U", "colaborador", dia(25)))) == "pertenencia_finalizada"


def test_una_persona_sin_ninguna_pertenencia_no_se_traslada(operador, mundo):
    with get_owner_engine().begin() as c:
        sola = c.execute(text("insert into persona (nombre) values ('Sola') returning id")).scalar_one()
    mundo.p["SOLA"] = sola
    assert motivo(rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "SOLA", "U", "colaborador", dia(3)))) == "sin_pertenencia"


def test_el_indice_del_cambio_erroneo_se_informa(operador, mundo):
    e = rechaza("PERTENENCIA_INVALIDA", operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)), cambio(mundo, "C2", "T", "colaborador", dia(3)))
    assert e.detalles[0]["indice"] == 1 and e.detalles[0]["motivo"] == "sin_cambio"


# ===================================================== atomicidad =========================================================

def test_si_un_cambio_del_conjunto_falla_no_cambia_ninguno(operador, mundo):
    """El primer cambio es válido por sí solo; el segundo no: ninguno se aplica y no queda auditoría."""
    solo = [cambio(mundo, "C1", "U", "colaborador", dia(3))]
    segundo = cambio(mundo, "ST", "X", "supervisor", dia(3))             # dejaría a T sin supervisor
    rechaza("PERTENENCIA_INVALIDA", operador, mundo, *solo, segundo)
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, None)]
    assert contar("auditoria") == 1 + 4 + 6                              # solo la instalación, los 4 equipos y las 6 personas del escenario


def test_un_fallo_en_la_base_a_mitad_de_la_aplicacion_deshace_todo(operador, mundo, monkeypatch):
    """Si algo falla tras cerrar los intervalos (aquí, la auditoría), la transacción entera se deshace."""
    from app.provision import servicio

    def falla(*a, **k):
        raise RuntimeError("fallo simulado")
    monkeypatch.setattr(servicio, "_auditar", falla)
    antes = foto()
    with pytest.raises(RuntimeError):
        trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)))
    assert foto() == antes


# ===================================================== conservación del historial =========================================

def test_las_pertenencias_anteriores_se_conservan_intactas_y_solo_se_cierra_la_ultima(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)))
    antes = {f[0]: f for f in filas("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia")}
    trasladar(operador, mundo, cambio(mundo, "C1", "T", "colaborador", dia(8)), cambio(mundo, "C2", "U", "colaborador", dia(8)))
    despues = {f[0]: f for f in filas("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia")}
    assert set(antes) <= set(despues)                                       # nada se borra
    cambiadas = [i for i in antes if antes[i] != despues[i]]
    assert len(cambiadas) == 2                                              # solo las dos últimas pertenencias (una por persona)
    for i in cambiadas:
        assert antes[i][5] is None and despues[i][5] == dia(8)              # sin fin -> con fin; nada más cambió
        assert antes[i][:5] == despues[i][:5]
    assert len(despues) == len(antes) + 2                                   # y se abren dos nuevas


def test_los_registros_de_m2_y_m3_no_se_modifican(operador, mundo):
    """Bitácoras y actividades existentes (la jornada de hoy incluida): idénticas antes y después del traslado."""
    with get_owner_engine().begin() as c:
        b = c.execute(text("insert into bitacora (persona_id, fecha_laboral, resumen) values (:p, :f, 'trabajo de hoy') returning id"),
                      {"p": mundo.p["C1"], "f": HOY}).scalar_one()
        c.execute(text("insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen) values (:p, :b, 'Informe', 'no_planificada')"),
                  {"p": mundo.p["C1"], "b": b})
    leer = lambda: (filas("select b::text from bitacora b order by id"), filas("select a::text from actividad a order by id"))   # noqa: E731
    antes = leer()
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(1)))
    assert leer() == antes


# ===================================================== auditoría ==========================================================

def test_ir35_una_sola_entrada_con_los_valores_anterior_y_nuevo_de_todos_los_cambios(operador, mundo):
    antes = contar("auditoria")
    r = trasladar(operador, mundo, cambio(mundo, "ST", "X", "supervisor", dia(5)), cambio(mundo, "C1", "T", "supervisor", dia(5)))
    entradas = filas("select tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id, propietaria_registro_id, "
                     "valor_anterior, valor_nuevo from auditoria where operacion = 'cambio_pertenencia'")
    assert contar("auditoria") == antes + 1 and len(entradas) == 1
    tipo_autor, referencia, operacion, tipo_objeto, objeto_id, propietaria, anterior, nuevo = entradas[0]
    assert (tipo_autor, operacion, tipo_objeto, objeto_id, propietaria) == ("provision", "cambio_pertenencia", "operacion_de_pertenencia", r.invocacion, None)
    assert referencia == f"operador:{operador.identificador}|invocacion:{r.invocacion}"
    assert {c["persona"] for c in anterior["cambios"]} == {c["persona"] for c in nuevo["cambios"]} == {str(mundo.p["ST"]), str(mundo.p["C1"])}


def test_la_auditoria_permite_reconstruir_cada_cambio(operador, mundo):
    """Del valor anterior y el nuevo se reconstruye: la pertenencia cerrada, la nueva y las fechas."""
    r = trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)))
    anterior, nuevo = filas("select valor_anterior, valor_nuevo from auditoria where operacion = 'cambio_pertenencia'")[0]
    previa = anterior["cambios"][0]
    despues = nuevo["cambios"][0]
    assert previa["persona"] == despues["persona"] == str(mundo.p["C1"])
    assert previa["pertenencia"] == {"id": previa["pertenencia"]["id"], "equipo": str(mundo.eq["T"]), "rol": "colaborador",
                                     "desde": HOY.isoformat(), "hasta_exclusivo": None}
    assert despues["tipo"] == "traslado" and despues["fecha_efectiva"] == dia(3).isoformat()
    assert despues["pertenencia_cerrada"] == {"id": previa["pertenencia"]["id"], "hasta_exclusivo": dia(3).isoformat()}
    assert despues["pertenencia_nueva"]["equipo"] == str(mundo.eq["U"]) and despues["pertenencia_nueva"]["desde"] == dia(3).isoformat()
    assert despues["pertenencia_nueva"]["id"] == str(r.historiales[mundo.p["C1"]][-1].id)


def test_la_auditoria_de_un_traslado_no_contiene_credenciales_ni_identificadores_de_acceso(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)))
    texto = json.dumps(filas("select referencia_provision, valor_anterior, valor_nuevo from auditoria where operacion = 'cambio_pertenencia'"), default=str)
    assert CREDENCIAL not in texto and "argon" not in texto.lower() and "identificador_acceso" not in texto
    assert '"c1"' not in texto.lower()                                    # el identificador de acceso de la persona


def test_las_entradas_de_auditoria_anteriores_no_cambian(operador, mundo):
    previas = filas("select * from auditoria order by id")
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)))
    assert filas("select * from auditoria where operacion <> 'cambio_pertenencia' order by id") == previas


# ===================================================== respuesta: historial completo ======================================

def test_ca13_la_respuesta_trae_el_historial_completo_de_cada_persona_afectada(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)))
    r = trasladar(operador, mundo, cambio(mundo, "C1", "T", "colaborador", dia(9)), cambio(mundo, "C2", "U", "colaborador", dia(9)))
    h = [(x.equipo, x.rol, x.desde, x.hasta_exclusivo) for x in r.historiales[mundo.p["C1"]]]
    assert h == [("T", "colaborador", HOY, dia(3)), ("U", "colaborador", dia(3), dia(9)), ("T", "colaborador", dia(9), None)]
    assert [(x.equipo, x.desde, x.hasta_exclusivo) for x in r.historiales[mundo.p["C2"]]] == [("T", HOY, dia(9)), ("U", dia(9), None)]


# ===================================================== visibilidad histórica (límites de M1-T1) ===========================

def _lee(db, mundo, consultante, dueña, fecha, hoy_):
    """¿Puede ``consultante`` (con la situación que tiene el día ``hoy_``) leer el registro de ``dueña`` de esa fecha laboral?"""
    return decidir_lectura(db, consultante_de(db, mundo.p[consultante], hoy=hoy_), Registro(mundo.p[dueña], fecha)).visible


def test_la_politica_de_visibilidad_usa_el_equipo_de_cada_fecha_tras_un_traslado_real(operador, mundo):
    """C1 pasa de T a U el día 3. Sus registros de hasta el día 2 son de T (visibles para C2, no para CU); los desde el día 3,
    de U (visibles para CU, no para C2). Los registros de HOY, creados antes del traslado, siguen siendo de T (CA-249)."""
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(3)))
    with Session(get_engine()) as db:
        for fecha, lee_c2, lee_cu in ((HOY, True, False), (dia(1), True, False), (dia(2), True, False), (dia(3), False, True), (dia(30), False, True)):
            assert _lee(db, mundo, "C2", "C1", fecha, dia(5)) is lee_c2, f"C2 sobre {fecha}"
            assert _lee(db, mundo, "CU", "C1", fecha, dia(5)) is lee_cu, f"CU sobre {fecha}"
        assert pertenencias.equipo_en_fecha(db, mundo.p["C1"], HOY) == mundo.eq["T"]                         # CA-249
        assert pertenencias.equipo_en_fecha(db, mundo.p["C1"], dia(2)) == mundo.eq["T"]
        assert pertenencias.equipo_en_fecha(db, mundo.p["C1"], dia(3)) == mundo.eq["U"]
        assert pertenencias.equipo_en_fecha(db, mundo.p["C1"], dia(300)) == mundo.eq["U"]


def test_el_traslado_programado_no_cambia_quien_puede_leer_hoy_la_jornada_de_hoy(operador, mundo):
    with Session(get_engine()) as db:
        antes = (_lee(db, mundo, "C2", "C1", HOY, HOY), _lee(db, mundo, "CU", "C1", HOY, HOY))
    trasladar(operador, mundo, cambio(mundo, "C1", "U", "colaborador", dia(1)))
    with Session(get_engine()) as db:
        assert (_lee(db, mundo, "C2", "C1", HOY, HOY), _lee(db, mundo, "CU", "C1", HOY, HOY)) == antes == (True, False)


def test_tras_un_cambio_de_rol_el_equipo_de_la_persona_no_cambia_y_su_situacion_vigente_es_la_del_dia(operador, mundo):
    trasladar(operador, mundo, cambio(mundo, "ST", "T", "colaborador", dia(4)), cambio(mundo, "C1", "T", "supervisor", dia(4)))
    with Session(get_engine()) as db:
        assert pertenencias.pertenencia_en_fecha(db, mundo.p["C1"], dia(3)).rol == "colaborador"
        assert pertenencias.pertenencia_en_fecha(db, mundo.p["C1"], dia(4)).rol == "supervisor"
        assert pertenencias.equipo_en_fecha(db, mundo.p["C1"], dia(3)) == pertenencias.equipo_en_fecha(db, mundo.p["C1"], dia(4)) == mundo.eq["T"]
        c = consultante_de(db, mundo.p["C1"], hoy=dia(5))
        assert c.puede_operar and c.pertenencia.rol == "supervisor"


def test_el_supervisor_saliente_deja_de_serlo_y_el_entrante_no_hereda_nada_antes_de_la_fecha(operador, mundo):
    """El supervisor de la fecha anterior no conserva la supervisión; el entrante no la tiene el día anterior (RA-12)."""
    trasladar(operador, mundo, cambio(mundo, "ST", "X", "supervisor", dia(4)), cambio(mundo, "C1", "T", "supervisor", dia(4)))
    with Session(get_engine()) as db:
        assert consultante_de(db, mundo.p["ST"], hoy=dia(3)).pertenencia.equipo_id == mundo.eq["T"]
        assert consultante_de(db, mundo.p["ST"], hoy=dia(4)).pertenencia.equipo_id == mundo.eq["X"]
        assert consultante_de(db, mundo.p["C1"], hoy=dia(3)).pertenencia.rol == "colaborador"
        assert consultante_de(db, mundo.p["C1"], hoy=dia(4)).pertenencia.rol == "supervisor"


# ===================================================== concurrencia =======================================================

def _esperar_bloqueo_consultivo(segundos: float = 10.0) -> bool:
    """``pg_locks`` es visible para cualquier rol: espera a que alguna sesión esté bloqueada en un bloqueo consultivo."""
    fin = time.time() + segundos
    while time.time() < fin:
        if filas("select count(*) from pg_locks where locktype = 'advisory' and not granted")[0][0] >= 1:
            return True
        time.sleep(0.05)
    return False


def _sin_violaciones():
    """Invariantes de TODA la base: ningún equipo viola IR-03 ni IR-32 y ninguna persona tiene solapes ni huecos."""
    por_equipo, por_persona = {}, {}
    for f in filas("select equipo_id, persona_id, rol, desde, hasta_exclusivo from pertenencia"):
        por_equipo.setdefault(f[0], []).append(Tramo(f[1], f[2], f[3], f[4]))
        por_persona.setdefault(f[1], []).append(Tramo(f[1], f[0], f[3], f[4]))
    for equipo, tramos in por_equipo.items():
        assert primera_violacion_de_supervision(tramos, dia(-1000)) is None, f"equipo {equipo}"
    for persona, tramos in por_persona.items():
        assert primera_irregularidad_de_persona(tramos) is None, f"persona {persona}"


def test_dos_ordenes_validas_por_separado_pero_invalidas_juntas_se_serializan_por_equipo(operador, mundo):
    """Sesgo de escritura de IR-32. W tiene supervisor (SW) y ningún colaborador. A: SW se va de W (válido: W sin
    colaboradores). B: C1 entra en W como colaborador el mismo día (válido SI SW sigue). Juntas dejarían a W con un colaborador
    sin supervisor. B debe esperar a A (bloqueo del equipo) y, al verlo confirmado, rechazarse."""
    resultado: dict = {}
    conexion = get_provision_engine().connect()
    try:
        registrar_traslado(conexion, operador, cambios=[cambio(mundo, "SW", "X", "supervisor", dia(2))])          # A: sin confirmar todavía

        def orden_b():
            try:
                orden(registrar_traslado, operador, cambios=[cambio(mundo, "C1", "W", "colaborador", dia(2))])
                resultado["b"] = "aceptada"
            except ErrorDeProvision as e:
                resultado["b"] = e.codigo
            except Exception as e:  # noqa: BLE001
                resultado["b"] = f"error inesperado: {type(e).__name__}"

        hilo = threading.Thread(target=orden_b)
        hilo.start()
        assert _esperar_bloqueo_consultivo(), "B debía quedar esperando el bloqueo del equipo mientras A no confirma"
        conexion.commit()                                                                                         # A confirma
    finally:
        conexion.close()
    hilo.join(20)
    assert not hilo.is_alive() and resultado["b"] == "PERTENENCIA_INVALIDA"
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, None)]
    _sin_violaciones()


def test_el_alta_de_un_colaborador_frente_a_la_salida_del_supervisor_tambien_se_serializa(operador, mundo):
    """La misma carrera con ``crear_persona`` (que comparte el bloqueo del equipo con los traslados)."""
    resultado: dict = {}
    conexion = get_provision_engine().connect()
    try:
        registrar_traslado(conexion, operador, cambios=[cambio(mundo, "SW", "X", "supervisor", dia(2))])

        def alta():
            try:
                orden(crear_persona, operador, nombre="Nuevo", identificador_acceso="nuevo", equipo_id=mundo.eq["W"], rol="colaborador", desde=dia(2))
                resultado["b"] = "aceptada"
            except ErrorDeProvision as e:
                resultado["b"] = e.codigo

        hilo = threading.Thread(target=alta)
        hilo.start()
        assert _esperar_bloqueo_consultivo()
        conexion.commit()
    finally:
        conexion.close()
    hilo.join(20)
    assert resultado["b"] == "PERTENENCIA_INVALIDA"
    _sin_violaciones()


def test_dos_traslados_de_la_misma_persona_se_serializan_y_el_segundo_ve_el_primero(operador, mundo):
    resultado: dict = {}
    conexion = get_provision_engine().connect()
    try:
        registrar_traslado(conexion, operador, cambios=[cambio(mundo, "C1", "U", "colaborador", dia(3))])

        def segundo():
            try:
                orden(registrar_traslado, operador, cambios=[cambio(mundo, "C1", "T", "colaborador", dia(3))])    # misma fecha: ya no es posterior
                resultado["b"] = "aceptada"
            except ErrorDeProvision as e:
                resultado["b"] = e.codigo

        hilo = threading.Thread(target=segundo)
        hilo.start()
        assert _esperar_bloqueo_consultivo()
        conexion.commit()
    finally:
        conexion.close()
    hilo.join(20)
    assert resultado["b"] == "PERTENENCIA_INVALIDA"
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, dia(3)), ("U", "colaborador", dia(3), None)]
    _sin_violaciones()


def test_dos_relevos_simultaneos_del_mismo_supervisor_dejan_uno_solo_y_la_base_consistente(operador, mundo):
    resultados: list = []

    def relevo(sustituto):
        try:
            orden(registrar_traslado, operador, cambios=[cambio(mundo, "ST", "X", "supervisor", dia(5)), cambio(mundo, sustituto, "T", "supervisor", dia(5))])
            resultados.append("aceptada")
        except ErrorDeProvision as e:
            resultados.append(e.codigo)

    hilos = [threading.Thread(target=relevo, args=(s,)) for s in ("C1", "C2")]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(30)
    assert sorted(resultados) == ["PERTENENCIA_INVALIDA", "aceptada"]
    _sin_violaciones()
    assert filas("select count(*) from auditoria where operacion = 'cambio_pertenencia'") == [(1,)]


def test_muchas_ordenes_concurrentes_no_se_bloquean_entre_si_ni_rompen_ninguna_regla(operador, mundo):
    """Ocho trabajadores lanzan traslados, cambios de rol y relevos al azar sobre los mismos equipos y personas. Ninguno
    debe fallar por un bloqueo mutuo ni por un error de la base, y el resultado cumple todas las reglas."""
    claves = list(mundo.p)
    equipos = list(mundo.eq)
    resultados, inesperados = [], []

    def trabajador(semilla):
        azar = random.Random(semilla)
        for _ in range(6):
            n = azar.choice([1, 1, 2])
            cambios = [cambio(mundo, persona, azar.choice(equipos), azar.choice(["colaborador", "supervisor"]), dia(azar.randint(1, 4)))
                       for persona in azar.sample(claves, n)]
            try:
                orden(registrar_traslado, operador, cambios=cambios)
                resultados.append("aceptada")
            except ErrorDeProvision as e:
                resultados.append(e.codigo)
            except Exception as e:  # noqa: BLE001
                inesperados.append(repr(e)[:200])

    hilos = [threading.Thread(target=trabajador, args=(s,)) for s in range(8)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(120)
    assert not any(h.is_alive() for h in hilos), "algún trabajador quedó bloqueado"
    assert inesperados == []
    assert len(resultados) == 48 and set(resultados) <= {"aceptada", "PERTENENCIA_INVALIDA", "FECHA_EFECTIVA_INVALIDA"}
    _sin_violaciones()
    # cada orden aceptada dejó UNA entrada; ninguna rechazada dejó nada
    assert filas("select count(*) from auditoria where operacion = 'cambio_pertenencia'") == [(resultados.count("aceptada"),)]


# ===================================================== autorización =======================================================

def test_la_aplicacion_no_puede_ejecutar_un_traslado_aunque_se_llame_al_caso_de_uso(operador, mundo):
    from sqlalchemy.exc import DBAPIError
    antes = foto()
    with pytest.raises(DBAPIError) as e, get_engine().begin() as c:
        registrar_traslado(c, operador, cambios=[cambio(mundo, "C1", "U", "colaborador", dia(3))])
    assert e.value.orig.sqlstate == "42501" and foto() == antes
