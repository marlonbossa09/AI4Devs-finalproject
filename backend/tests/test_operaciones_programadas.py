"""M1-T4 — reglas puras de las operaciones de pertenencia programadas (finalizar, cancelar y sustituir; M1-06 y M1-07).

Sin base de datos. Las propiedades contrastan el resultado con una comprobación DÍA A DÍA, independiente de la implementación.
"""

import random
from datetime import date, timedelta

import pytest

from app.provision.operaciones_programadas import (
    Incumplimiento, Intervalo, aplicar_cambio, aplicar_finalizacion, cancelar, operaciones_programadas, tipo_de_transicion,
)

D = date(2030, 1, 10)
HOY = D


def dia(n: int) -> date:
    return D + timedelta(days=n)


def i(id_, equipo, rol, desde, hasta=None):
    return Intervalo(id_, equipo, rol, dia(desde), None if hasta is None else dia(hasta))


def codigo(funcion, *args):
    with pytest.raises(Incumplimiento) as e:
        funcion(*args)
    return e.value.codigo, e.value.motivo


# ==================================================== derivación de las operaciones programadas ==========================

def test_un_intervalo_que_ya_empezo_es_historial_y_uno_que_empieza_manana_es_una_alta_programada():
    assert operaciones_programadas([i(1, "T", "colaborador", 0)], HOY) == []                       # empieza hoy: efectivo
    assert operaciones_programadas([i(1, "T", "colaborador", -5)], HOY) == []
    ops = operaciones_programadas([i(1, "T", "colaborador", 1)], HOY)
    assert [(o.tipo, o.fecha) for o in ops] == [("alta", dia(1))]


def test_un_traslado_programado_empieza_manana_y_uno_que_empieza_hoy_ya_es_efectivo():
    assert operaciones_programadas([i(1, "T", "colaborador", -5, 0), i(2, "U", "colaborador", 0)], HOY) == []
    ops = operaciones_programadas([i(1, "T", "colaborador", -5, 1), i(2, "U", "colaborador", 1)], HOY)
    assert [(o.tipo, o.fecha) for o in ops] == [("traslado", dia(1))]


def test_una_finalizacion_cuyo_fin_es_hoy_ya_es_efectiva_y_una_que_termina_manana_esta_programada():
    assert operaciones_programadas([i(1, "T", "colaborador", -5, 0)], HOY) == []
    assert [(o.tipo, o.fecha) for o in operaciones_programadas([i(1, "T", "colaborador", -5, 1)], HOY)] == [("finalizacion", dia(1))]


def test_el_tipo_de_cada_transicion_depende_de_lo_que_cambia():
    a = i(1, "T", "colaborador", 0, 5)
    assert tipo_de_transicion(a, i(2, "U", "colaborador", 5)) == "traslado"
    assert tipo_de_transicion(a, i(2, "T", "supervisor", 5)) == "cambio_de_rol"
    assert tipo_de_transicion(a, i(2, "U", "supervisor", 5)) == "traslado_y_cambio_de_rol"


def test_las_operaciones_se_ordenan_por_fecha_aunque_se_entreguen_desordenadas():
    linea = [i(3, "W", "colaborador", 9, 12), i(1, "T", "colaborador", -3, 4), i(2, "U", "supervisor", 4, 9)]
    assert [(o.tipo, o.fecha) for o in operaciones_programadas(linea, HOY)] == [
        ("traslado_y_cambio_de_rol", dia(4)), ("traslado_y_cambio_de_rol", dia(9)), ("finalizacion", dia(12))]


# ==================================================== cancelar ===========================================================

BASE = [i(1, "T", "colaborador", -10, 3), i(2, "U", "colaborador", 3)]          # traslado programado el día 3


def test_cancelar_un_traslado_retira_el_intervalo_y_restituye_el_fin_del_anterior():
    resultado, detalle = cancelar(BASE, HOY, [("traslado", dia(3))])
    assert resultado == [i(1, "T", "colaborador", -10)]
    assert len(detalle) == 1 and detalle[0].tipo == "traslado" and detalle[0].retirados == (BASE[1],)
    assert detalle[0].restituido == (1, dia(3), None)


def test_cancelar_una_finalizacion_deja_el_intervalo_sin_fin():
    resultado, detalle = cancelar([i(1, "T", "colaborador", -10, 4)], HOY, [("finalizacion", dia(4))])
    assert resultado == [i(1, "T", "colaborador", -10)] and detalle[0].restituido == (1, dia(4), None) and detalle[0].retirados == ()


def test_cancelar_una_alta_futura_deja_a_la_persona_sin_pertenencia():
    resultado, detalle = cancelar([i(1, "T", "colaborador", 5)], HOY, [("alta", dia(5))])
    assert resultado == [] and detalle[0].restituido is None and detalle[0].retirados == (i(1, "T", "colaborador", 5),)


def test_cancelar_un_cambio_de_rol_conserva_el_rol_anterior():
    linea = [i(1, "T", "colaborador", -10, 2), i(2, "T", "supervisor", 2)]
    resultado, _ = cancelar(linea, HOY, [("cambio_de_rol", dia(2))])
    assert resultado == [i(1, "T", "colaborador", -10)]


def test_la_fecha_efectiva_exacta_de_hoy_ya_no_se_puede_cancelar_y_la_de_manana_si():
    efectiva = [i(1, "T", "colaborador", -10, 0), i(2, "U", "colaborador", 0)]
    assert codigo(cancelar, efectiva, HOY, [("traslado", dia(0))]) == ("FECHA_EFECTIVA_INVALIDA", "la_operacion_ya_es_efectiva")
    assert cancelar([i(1, "T", "colaborador", -10, 1), i(2, "U", "colaborador", 1)], HOY, [("traslado", dia(1))])[0] == [i(1, "T", "colaborador", -10)]


def test_una_fecha_pasada_se_rechaza_aunque_no_exista_ninguna_operacion_en_ella():
    assert codigo(cancelar, BASE, HOY, [("traslado", dia(-4))])[0] == "FECHA_EFECTIVA_INVALIDA"


def test_una_operacion_inexistente_o_de_otro_tipo_se_rechaza():
    assert codigo(cancelar, BASE, HOY, [("traslado", dia(4))]) == ("RECURSO_NO_DISPONIBLE", "operacion_no_encontrada")
    assert codigo(cancelar, BASE, HOY, [("finalizacion", dia(3))]) == ("SOLICITUD_INVALIDA", "tipo_no_coincide")
    assert codigo(cancelar, BASE, HOY, [("cambio_de_rol", dia(3))]) == ("SOLICITUD_INVALIDA", "tipo_no_coincide")
    assert codigo(cancelar, BASE, HOY, [("viaje", dia(3))]) == ("SOLICITUD_INVALIDA", "tipo_no_valido")


def test_la_misma_operacion_dos_veces_se_rechaza():
    assert codigo(cancelar, BASE, HOY, [("traslado", dia(3)), ("traslado", dia(3))]) == ("SOLICITUD_INVALIDA", "operacion_repetida")


CADENA = [i(1, "T", "colaborador", -10, 3), i(2, "U", "colaborador", 3, 7), i(3, "W", "colaborador", 7, 12)]   # dos traslados y una finalización


def test_no_se_cancela_una_operacion_de_la_que_dependen_otras_posteriores():
    assert codigo(cancelar, CADENA, HOY, [("traslado", dia(3))]) == ("PERTENENCIA_INVALIDA", "hay_operaciones_posteriores_que_dependen_de_ella")
    assert codigo(cancelar, CADENA, HOY, [("traslado", dia(7))]) == ("PERTENENCIA_INVALIDA", "hay_operaciones_posteriores_que_dependen_de_ella")


def test_se_cancela_un_sufijo_de_las_operaciones_programadas():
    una, _ = cancelar(CADENA, HOY, [("finalizacion", dia(12))])
    assert una == [i(1, "T", "colaborador", -10, 3), i(2, "U", "colaborador", 3, 7), i(3, "W", "colaborador", 7)]
    dos, _ = cancelar(CADENA, HOY, [("finalizacion", dia(12)), ("traslado", dia(7))])
    assert dos == [i(1, "T", "colaborador", -10, 3), i(2, "U", "colaborador", 3)]
    todas, detalle = cancelar(CADENA, HOY, [("traslado", dia(7)), ("finalizacion", dia(12)), ("traslado", dia(3))])
    assert todas == [i(1, "T", "colaborador", -10)] and [d.fecha for d in detalle] == [dia(3), dia(7), dia(12)]


def test_las_operaciones_que_se_cancelan_juntas_se_aceptan_en_cualquier_orden():
    a, _ = cancelar(CADENA, HOY, [("traslado", dia(3)), ("traslado", dia(7)), ("finalizacion", dia(12))])
    b, _ = cancelar(CADENA, HOY, [("finalizacion", dia(12)), ("traslado", dia(7)), ("traslado", dia(3))])
    assert a == b


def test_una_cancelacion_vacia_no_cambia_nada():
    assert cancelar(BASE, HOY, []) == (BASE, [])


def test_las_operaciones_efectivas_de_la_cadena_no_se_tocan():
    """El primer traslado ya es efectivo (día -2): solo el segundo y la finalización se pueden cancelar."""
    linea = [i(1, "T", "colaborador", -10, -2), i(2, "U", "colaborador", -2, 7), i(3, "W", "colaborador", 7, 12)]
    resultado, _ = cancelar(linea, HOY, [("traslado", dia(7)), ("finalizacion", dia(12))])
    assert resultado == [i(1, "T", "colaborador", -10, -2), i(2, "U", "colaborador", -2)]
    assert codigo(cancelar, linea, HOY, [("traslado", dia(-2))])[0] == "FECHA_EFECTIVA_INVALIDA"


# ==================================================== registrar de nuevo (sustituir) =====================================

def test_un_cambio_nuevo_cierra_el_ultimo_intervalo_y_abre_otro():
    r = aplicar_cambio([i(1, "T", "colaborador", -10)], HOY, "U", "colaborador", dia(4))
    assert r == [i(1, "T", "colaborador", -10, 4), Intervalo(None, "U", "colaborador", dia(4), None)]


@pytest.mark.parametrize("fecha,esperado", [(0, "FECHA_EFECTIVA_INVALIDA"), (-3, "FECHA_EFECTIVA_INVALIDA"), (1, None)])
def test_el_cambio_exige_una_fecha_posterior_a_hoy(fecha, esperado):
    if esperado:
        assert codigo(aplicar_cambio, [i(1, "T", "colaborador", -10)], HOY, "U", "colaborador", dia(fecha))[0] == esperado
    else:
        assert aplicar_cambio([i(1, "T", "colaborador", -10)], HOY, "U", "colaborador", dia(fecha))[-1].desde == dia(1)


def test_el_cambio_exige_una_fecha_posterior_al_inicio_del_ultimo_intervalo_y_algo_que_cambie():
    programado = [i(1, "T", "colaborador", 5)]
    assert codigo(aplicar_cambio, programado, HOY, "U", "colaborador", dia(5))[1] == "fecha_no_posterior_al_inicio_de_la_ultima_pertenencia"
    assert codigo(aplicar_cambio, programado, HOY, "U", "colaborador", dia(3))[1] == "fecha_no_posterior_al_inicio_de_la_ultima_pertenencia"
    assert aplicar_cambio(programado, HOY, "U", "colaborador", dia(6))[-1].desde == dia(6)
    assert codigo(aplicar_cambio, programado, HOY, "T", "colaborador", dia(6))[1] == "sin_cambio"


def test_no_se_cambia_a_quien_no_tiene_pertenencia_o_ya_tiene_un_fin():
    assert codigo(aplicar_cambio, [], HOY, "U", "colaborador", dia(2))[1] == "sin_pertenencia"
    assert codigo(aplicar_cambio, [i(1, "T", "colaborador", -10, 5)], HOY, "U", "colaborador", dia(8))[1] == "pertenencia_finalizada"


@pytest.mark.parametrize("fecha,esperado", [(0, "FECHA_EFECTIVA_INVALIDA"), (-2, "FECHA_EFECTIVA_INVALIDA")])
def test_la_finalizacion_exige_una_fecha_posterior_a_hoy(fecha, esperado):
    assert codigo(aplicar_finalizacion, [i(1, "T", "colaborador", -10)], HOY, dia(fecha))[0] == esperado


def test_la_finalizacion_cierra_el_ultimo_intervalo_y_no_abre_otro():
    assert aplicar_finalizacion([i(1, "T", "colaborador", -10)], HOY, dia(1)) == [i(1, "T", "colaborador", -10, 1)]
    assert aplicar_finalizacion([i(1, "T", "colaborador", 5)], HOY, dia(6)) == [i(1, "T", "colaborador", 5, 6)]
    assert codigo(aplicar_finalizacion, [i(1, "T", "colaborador", 5)], HOY, dia(5))[1] == "fecha_no_posterior_al_inicio_de_la_ultima_pertenencia"
    assert codigo(aplicar_finalizacion, [i(1, "T", "colaborador", -10, 4)], HOY, dia(6))[1] == "pertenencia_finalizada"
    assert codigo(aplicar_finalizacion, [], HOY, dia(6))[1] == "sin_pertenencia"


# ==================================================== propiedad: contraste día a día =====================================

def _equipo_en(linea, fecha):
    for t in linea:
        if t.desde <= fecha and (t.hasta is None or fecha < t.hasta):
            return (t.equipo, t.rol)
    return None


def _cadena_al_azar(azar: random.Random):
    """Una línea contigua: intervalos efectivos y programados, con o sin finalización."""
    cursor = -azar.randint(5, 40)
    linea, k = [], 0
    for _ in range(azar.randint(1, 5)):
        fin = cursor + azar.randint(1, 12)
        k += 1
        linea.append([k, azar.choice("TUWX"), azar.choice(["colaborador", "supervisor"]), cursor, fin])
        cursor = fin
    if azar.random() < 0.5:
        linea[-1][4] = None
    resultado = []
    for n, (id_, eq, rol, desde, hasta) in enumerate(linea):
        # evita dos intervalos consecutivos idénticos (no serían una operación)
        if resultado and (resultado[-1].equipo, resultado[-1].rol) == (eq, rol):
            rol = "supervisor" if rol == "colaborador" else "colaborador"
        resultado.append(Intervalo(id_, eq, rol, dia(desde), None if hasta is None else dia(hasta)))
    return resultado


@pytest.mark.parametrize("semilla", range(200))
def test_propiedad_cancelar_un_sufijo_equivale_a_prolongar_el_ultimo_estado_efectivo(semilla):
    azar = random.Random(7000 + semilla)
    linea = _cadena_al_azar(azar)
    ops = operaciones_programadas(linea, HOY)
    if not ops:
        return
    j = azar.randrange(len(ops))
    sufijo = ops[j:]
    resultado, detalle = cancelar(linea, HOY, [(o.tipo, o.fecha) for o in sufijo])
    primera = sufijo[0].fecha
    assert [d.fecha for d in detalle] == [o.fecha for o in sufijo]
    for k in range(-60, 80):
        fecha = dia(k)
        if fecha < primera:
            esperado = _equipo_en(linea, fecha)               # lo anterior no cambia
        else:
            esperado = _equipo_en(linea, primera - timedelta(days=1))   # el último estado anterior continúa sin fin
        assert _equipo_en(resultado, fecha) == esperado, (semilla, k)
    # ningún intervalo efectivo desaparece ni cambia (salvo el fin del último, que se restituye)
    for original in linea:
        if original.desde <= HOY:
            encontrado = next(x for x in resultado if x.id == original.id)
            assert (encontrado.equipo, encontrado.rol, encontrado.desde) == (original.equipo, original.rol, original.desde)


@pytest.mark.parametrize("semilla", range(100))
def test_propiedad_una_cancelacion_que_deja_posteriores_se_rechaza(semilla):
    azar = random.Random(9000 + semilla)
    linea = _cadena_al_azar(azar)
    ops = operaciones_programadas(linea, HOY)
    if len(ops) < 2:
        return
    j = azar.randrange(len(ops) - 1)                          # una operación con otras posteriores sin cancelar
    assert codigo(cancelar, linea, HOY, [(ops[j].tipo, ops[j].fecha)])[1] == "hay_operaciones_posteriores_que_dependen_de_ella"


@pytest.mark.parametrize("semilla", range(100))
def test_propiedad_sustituir_deja_una_linea_contigua_y_el_pasado_intacto(semilla):
    azar = random.Random(11000 + semilla)
    linea = _cadena_al_azar(azar)
    ops = operaciones_programadas(linea, HOY)
    if not ops:
        return
    sufijo = ops[azar.randrange(len(ops)):]
    base, _ = cancelar(linea, HOY, [(o.tipo, o.fecha) for o in sufijo])
    if not base or base[-1].hasta is not None:
        return
    minimo = max(1, (base[-1].desde - D).days + 1)
    nuevo = sorted(aplicar_cambio(base, HOY, "Z", "colaborador", dia(minimo + azar.randint(0, 5))), key=lambda t: t.desde)
    for a, b in zip(nuevo, nuevo[1:]):
        assert a.hasta == b.desde                              # sin solapes ni huecos
    assert nuevo[-1].hasta is None and nuevo[-1].equipo == "Z"
