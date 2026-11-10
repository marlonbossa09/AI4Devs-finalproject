"""Dominio de la secuencia de avances y del estado actual (HU-2.8, HU-2.9; M2-05).

Pruebas unitarias puras: no usan la base de datos.
"""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from app.modulos.bitacoras.secuencia import (
    AvanceEnSecuencia,
    estado_actual,
    estado_actual_tras_insertar,
    finalizacion_vigente,
    con_estado_corregido,
    ordenar,
    quedaria_tras_una_finalizacion,
    violaciones,
    violaciones_nuevas,
    AVANCE_TRAS_FINALIZACION,
    REACTIVACION_COMPLETADA,
    REACTIVACION_SIN_FINALIZACION,
)

LUNES = date(2026, 11, 2)
MARTES = date(2026, 11, 3)
MIERCOLES = date(2026, 11, 4)
T0 = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


def _uuid(n: int) -> UUID:
    return UUID(int=n)


def av(n: int, fecha: date, estado: str, minutos: int = 0, reactivacion: bool = False) -> AvanceEnSecuencia:
    return AvanceEnSecuencia(_uuid(n), fecha, T0 + timedelta(minutes=minutos), estado, reactivacion)


def test_una_actividad_sin_avances_esta_pendiente():  # CA-73, CA-186
    assert estado_actual([]) == "Pendiente"


def test_la_fecha_laboral_posterior_es_posterior_aunque_se_registrara_antes():  # CA-74
    registrado_antes_pero_del_martes = av(1, MARTES, "En progreso", minutos=0)
    registrado_despues_pero_del_lunes = av(2, LUNES, "Bloqueada", minutos=10)
    assert [a.id for a in ordenar([registrado_antes_pero_del_martes, registrado_despues_pero_del_lunes])] == [_uuid(2), _uuid(1)]


def test_a_igual_fecha_laboral_el_registrado_despues_es_posterior():  # CA-75
    primero, segundo = av(5, LUNES, "En progreso", minutos=0), av(4, LUNES, "Completada", minutos=1)
    assert estado_actual([segundo, primero]) == "Completada"


def test_con_igual_fecha_y_momento_decide_el_identificador_siempre_igual():  # CA-76
    a, b = av(1, LUNES, "En progreso"), av(2, LUNES, "Bloqueada")
    assert [x.id for x in ordenar([a, b])] == [x.id for x in ordenar([b, a])] == [_uuid(1), _uuid(2)]
    assert estado_actual([b, a]) == "Bloqueada"


def test_el_estado_actual_es_el_del_ultimo_avance_de_la_secuencia():  # CA-77
    assert estado_actual([av(1, LUNES, "En progreso"), av(2, MARTES, "Bloqueada")]) == "Bloqueada"


def test_un_avance_retroactivo_no_sustituye_el_estado_de_uno_posterior():  # CA-78
    existentes = [av(1, MARTES, "En progreso")]
    assert estado_actual_tras_insertar(existentes, LUNES, "Completada") == "En progreso"


def test_un_avance_al_final_de_la_secuencia_pasa_a_ser_el_estado_actual():
    existentes = [av(1, LUNES, "En progreso")]
    assert estado_actual_tras_insertar(existentes, MARTES, "Bloqueada") == "Bloqueada"
    assert estado_actual_tras_insertar(existentes, LUNES, "Completada") == "Completada"  # misma fecha: va después
    assert estado_actual_tras_insertar([], LUNES, "En progreso") == "En progreso"


def test_registrar_un_avance_cambia_la_secuencia_pero_no_reescribe_los_anteriores():  # CA-46
    anterior = av(1, LUNES, "En progreso")
    nuevo_estado = estado_actual_tras_insertar([anterior], MARTES, "Completada")
    assert nuevo_estado == "Completada" and anterior.estado == "En progreso"


def test_sin_avances_nada_hay_que_reactivar():
    assert not quedaria_tras_una_finalizacion([], LUNES)


def test_un_avance_posterior_a_la_finalizacion_requiere_reactivar():  # CA-190
    assert quedaria_tras_una_finalizacion([av(1, LUNES, "Completada")], MARTES)


def test_un_avance_de_la_misma_fecha_registrado_despues_de_la_finalizacion_requiere_reactivar():  # CA-206
    assert quedaria_tras_una_finalizacion([av(1, LUNES, "Completada")], LUNES)


def test_un_avance_retroactivo_anterior_a_la_finalizacion_se_acepta_sin_reactivar():  # CA-203
    assert not quedaria_tras_una_finalizacion([av(1, MARTES, "Completada")], LUNES)


def test_el_retroactivo_anterior_a_la_finalizacion_deja_la_actividad_completada():  # CA-205
    existentes = [av(1, MARTES, "Completada")]
    assert estado_actual_tras_insertar(existentes, LUNES, "En progreso") == "Completada"


def test_no_se_admite_un_avance_entre_una_finalizacion_y_su_reactivacion():  # CA-207
    existentes = [av(1, LUNES, "Completada"), av(2, MIERCOLES, "En progreso", minutos=5, reactivacion=True)]
    assert quedaria_tras_una_finalizacion(existentes, MARTES)


def test_tras_una_reactivacion_si_se_admiten_avances():
    existentes = [av(1, LUNES, "Completada"), av(2, MARTES, "En progreso", minutos=5, reactivacion=True)]
    assert not quedaria_tras_una_finalizacion(existentes, MIERCOLES)


def test_con_dos_finalizaciones_separadas_por_una_reactivacion_se_valida_cada_tramo():  # CA-207
    existentes = [
        av(1, LUNES, "Completada"),
        av(2, MARTES, "En progreso", minutos=5, reactivacion=True),
        av(3, MIERCOLES, "Completada", minutos=10),
    ]
    assert quedaria_tras_una_finalizacion(existentes, LUNES)       # justo tras la primera finalización
    assert not quedaria_tras_una_finalizacion(existentes, MARTES)  # tras la reactivación, antes de la segunda finalización


# ---- M3-04: la finalización que determina el estado actual

def test_la_finalizacion_vigente_es_el_ultimo_avance_si_es_completada():
    avances = [av(1, LUNES, "En progreso"), av(2, MARTES, "Completada", minutos=5)]
    assert finalizacion_vigente(avances).id == _uuid(2)


def test_sin_avances_o_sin_completada_al_final_no_hay_finalizacion_vigente():
    assert finalizacion_vigente([]) is None
    assert finalizacion_vigente([av(1, LUNES, "Completada"), av(2, MARTES, "En progreso", minutos=5)]) is None


def test_con_dos_ciclos_la_vigente_es_la_segunda_finalizacion():
    avances = [av(1, LUNES, "Completada"), av(2, MARTES, "En progreso", minutos=1, reactivacion=True),
               av(3, MIERCOLES, "Completada", minutos=2)]
    assert finalizacion_vigente(avances).id == _uuid(3)


def test_una_finalizacion_retroactiva_anterior_a_un_avance_posterior_no_es_vigente():
    """PA-27: el estado actual sale del orden laboral completo; la vigente es la del último avance."""
    avances = [av(1, MARTES, "En progreso"), av(2, LUNES, "Completada", minutos=10)]
    assert finalizacion_vigente(avances) is None


def test_el_orden_decide_con_la_misma_fecha_laboral_por_el_momento_de_registro():
    avances = [av(1, LUNES, "Completada", minutos=0), av(2, LUNES, "En progreso", minutos=1, reactivacion=True)]
    assert finalizacion_vigente(avances) is None


# ============================== M3-03: violaciones de IR-11 y corrección (PA-29, opción A) ======================

def motivos(avances):
    return {(v.avance_id, v.motivo) for v in violaciones(avances)}


def test_una_secuencia_valida_no_tiene_violaciones():
    avances = [av(1, LUNES, "En progreso"), av(2, MARTES, "Completada"), av(3, MIERCOLES, "En progreso", reactivacion=True)]
    assert violaciones(avances) == frozenset()


def test_un_avance_ordinario_tras_una_finalizacion_es_una_violacion():
    avances = [av(1, LUNES, "Completada"), av(2, MARTES, "En progreso")]
    assert motivos(avances) == {(_uuid(2), AVANCE_TRAS_FINALIZACION)}


def test_una_reactivacion_sin_finalizacion_inmediatamente_anterior_es_una_violacion():
    avances = [av(1, LUNES, "En progreso"), av(2, MARTES, "En progreso", reactivacion=True)]
    assert motivos(avances) == {(_uuid(2), REACTIVACION_SIN_FINALIZACION)}


def test_una_reactivacion_con_estado_completada_es_una_violacion():
    avances = [av(1, LUNES, "Completada"), av(2, MARTES, "Completada", reactivacion=True)]
    assert (_uuid(2), REACTIVACION_COMPLETADA) in motivos(avances)


def test_varios_ciclos_validos_no_tienen_violaciones():
    avances = [
        av(1, LUNES, "Completada"), av(2, MARTES, "Pendiente", reactivacion=True),
        av(3, MIERCOLES, "Completada"), av(4, date(2026, 11, 5), "Bloqueada", reactivacion=True),
    ]
    assert violaciones(avances) == frozenset()


def test_con_estado_corregido_no_modifica_el_original_ni_reordena_ni_crea_avances():
    original = [av(1, LUNES, "En progreso"), av(2, MARTES, "Completada")]
    despues = con_estado_corregido(original, _uuid(1), "Bloqueada")
    assert [a.estado for a in original] == ["En progreso", "Completada"]
    assert [a.id for a in despues] == [a.id for a in original] and len(despues) == 2
    assert [a.estado for a in despues] == ["Bloqueada", "Completada"]
    assert all(a.es_reactivacion is False for a in despues)                             # CA-239: ninguna reactivación


def test_corregir_a_completada_un_avance_anterior_a_otros_sin_reactivacion_es_una_violacion_nueva():
    """CA-236: lunes y martes En progreso, miércoles Completada, jueves reactivación; el lunes pasa a Completada."""
    jueves = date(2026, 11, 5)
    antes = [av(1, LUNES, "En progreso"), av(2, MARTES, "En progreso"), av(3, MIERCOLES, "Completada"),
             av(4, jueves, "En progreso", reactivacion=True)]
    despues = con_estado_corregido(antes, _uuid(1), "Completada")
    assert [(v.avance_id, v.motivo) for v in violaciones_nuevas(antes, despues)] == [(_uuid(2), AVANCE_TRAS_FINALIZACION)]


def test_corregir_la_finalizacion_a_otro_estado_sin_nada_despues_es_valido():
    """CA-238."""
    antes = [av(1, LUNES, "En progreso"), av(2, MARTES, "Completada")]
    assert violaciones_nuevas(antes, con_estado_corregido(antes, _uuid(2), "En progreso")) == []


def test_corregir_la_finalizacion_deja_una_reactivacion_sin_finalizacion_y_es_una_violacion_nueva():
    antes = [av(1, LUNES, "Completada"), av(2, MARTES, "En progreso", reactivacion=True)]
    nuevas = violaciones_nuevas(antes, con_estado_corregido(antes, _uuid(1), "En progreso"))
    assert [(v.avance_id, v.motivo) for v in nuevas] == [(_uuid(2), REACTIVACION_SIN_FINALIZACION)]


def test_corregir_una_reactivacion_a_completada_es_una_violacion_nueva():
    antes = [av(1, LUNES, "Completada"), av(2, MARTES, "En progreso", reactivacion=True)]
    nuevas = violaciones_nuevas(antes, con_estado_corregido(antes, _uuid(2), "Completada"))
    assert [(v.avance_id, v.motivo) for v in nuevas] == [(_uuid(2), REACTIVACION_COMPLETADA)]


def test_un_par_preexistente_admitido_por_pa27_no_rechaza_una_correccion_que_no_lo_agrava():
    """Un Completada retroactivo del lunes anterior a un En progreso del martes (CA-78): el par es una violación
    preexistente. Corregir la descripción (el estado no cambia) o el estado del martes a otro distinto de Completada
    no introduce ninguna nueva."""
    antes = [av(1, LUNES, "Completada", minutos=10), av(2, MARTES, "En progreso")]
    assert len(violaciones(antes)) == 1                                                   # una violación preexistente
    assert violaciones_nuevas(antes, antes) == []                                         # sin cambio de estado
    assert violaciones_nuevas(antes, con_estado_corregido(antes, _uuid(2), "Bloqueada")) == []


def test_agravar_un_par_preexistente_es_una_violacion_nueva():
    """Con el mismo par, corregir otro avance anterior a Completada crea una violación que no existía."""
    antes = [av(1, date(2026, 11, 1), "En progreso"), av(2, LUNES, "Completada", minutos=10), av(3, MARTES, "En progreso")]
    # el avance 3 ya estaba en violación (tras el Completada del lunes); corregir el 1 a Completada deja al 2 tras una finalización
    nuevas = violaciones_nuevas(antes, con_estado_corregido(antes, _uuid(1), "Completada"))
    assert [(v.avance_id, v.motivo) for v in nuevas] == [(_uuid(2), AVANCE_TRAS_FINALIZACION)]


def test_una_correccion_puede_resolver_una_violacion_preexistente():
    antes = [av(1, LUNES, "Completada", minutos=10), av(2, MARTES, "En progreso")]
    despues = con_estado_corregido(antes, _uuid(1), "Bloqueada")
    assert violaciones(despues) == frozenset() and violaciones_nuevas(antes, despues) == []


def test_el_estado_actual_tras_corregir_sale_del_orden_laboral_completo():
    antes = [av(1, LUNES, "En progreso"), av(2, MARTES, "Completada")]
    assert estado_actual(antes) == "Completada"
    assert estado_actual(con_estado_corregido(antes, _uuid(2), "Bloqueada")) == "Bloqueada"
    assert estado_actual(con_estado_corregido(antes, _uuid(1), "Pendiente")) == "Completada"     # no es el último
