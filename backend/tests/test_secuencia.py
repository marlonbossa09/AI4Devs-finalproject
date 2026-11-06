"""Dominio de la secuencia de avances y del estado actual (HU-2.8, HU-2.9; M2-05).

Pruebas unitarias puras: no usan la base de datos.
"""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from app.modulos.bitacoras.secuencia import (
    AvanceEnSecuencia,
    estado_actual,
    estado_actual_tras_insertar,
    ordenar,
    quedaria_tras_una_finalizacion,
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
