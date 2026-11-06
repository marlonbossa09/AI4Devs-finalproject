"""DB-03: bitácoras, actividades, planificaciones y avances (IR-01, IR-06, IR-08, IR-16, IR-33)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError

from app.db import get_engine, get_owner_engine
from scripts.verificar_datos import estados_actuales_incoherentes
from tests.fabricas import escenario_basico, hoy


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c)


def _bitacora(c, esc, fecha=None):
    return c.execute(text("insert into bitacora (persona_id, fecha_laboral) values (:p, :f) returning id"),
                     {"p": esc.persona, "f": fecha or hoy()}).scalar_one()


def _actividad(c, esc, bitacora, titulo="Preparar informe"):
    return c.execute(text("insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen) "
                          "values (:p, :b, :t, 'planificada') returning id"),
                     {"p": esc.persona, "b": bitacora, "t": titulo}).scalar_one()


def test_dos_bitacoras_de_la_misma_persona_y_fecha_no_pueden_coexistir(esc):
    with get_owner_engine().begin() as c:
        _bitacora(c, esc)
    with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
        _bitacora(c, esc)


def test_una_actividad_sin_titulo_o_con_solo_espacios_es_rechazada(esc):
    with get_owner_engine().begin() as c:
        b = _bitacora(c, esc)
    for titulo in ("", "   "):
        with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
            _actividad(c, esc, b, titulo)


def test_la_propietaria_y_el_titulo_de_una_actividad_no_se_pueden_cambiar(esc):
    with get_owner_engine().begin() as c:
        b = _bitacora(c, esc)
        a = _actividad(c, esc, b)
        otra = c.execute(text("insert into persona (nombre) values ('Otra') returning id")).scalar_one()
    for sentencia, params in (
        ("update actividad set propietaria_id = :o where id = :a", {"o": otra, "a": a}),
        ("update actividad set titulo = 'Otro' where id = :a", {"a": a}),
    ):
        with pytest.raises(DBAPIError) as e, get_owner_engine().begin() as c:
            c.execute(text(sentencia), params)
        assert e.value.orig.sqlstate == "23000"


def test_el_estado_actual_si_se_puede_actualizar(esc):
    with get_owner_engine().begin() as c:
        a = _actividad(c, esc, _bitacora(c, esc))
        c.execute(text("update actividad set estado_actual = 'En progreso' where id = :a"), {"a": a})


@pytest.mark.parametrize("estado,motivo,valido", [
    ("Bloqueada", None, False), ("Bloqueada", "  ", False), ("Bloqueada", "Falta acceso", True),
    ("En progreso", None, True),
])
def test_un_avance_bloqueada_exige_motivo(esc, estado, motivo, valido):
    with get_owner_engine().begin() as c:
        b = _bitacora(c, esc)
        a = _actividad(c, esc, b)
    sentencia = text("insert into avance (actividad_id, bitacora_id, estado, descripcion, motivo_bloqueo) "
                     "values (:a, :b, :e, 'trabajo', :m)")
    parametros = {"a": a, "b": b, "e": estado, "m": motivo}
    if valido:
        with get_owner_engine().begin() as c:
            c.execute(sentencia, parametros)
    else:
        with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
            c.execute(sentencia, parametros)


def test_un_avance_con_descripcion_vacia_es_rechazado(esc):
    with get_owner_engine().begin() as c:
        b = _bitacora(c, esc)
        a = _actividad(c, esc, b)
    with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                       "values (:a, :b, 'En progreso', '  ')"), {"a": a, "b": b})


def test_una_actividad_tiene_una_sola_planificacion_original_pero_varias_continuaciones(esc):
    ins = text("insert into planificacion (actividad_id, bitacora_id, tipo) values (:a, :b, :t)")
    with get_owner_engine().begin() as c:
        b = _bitacora(c, esc)
        a = _actividad(c, esc, b)
        c.execute(ins, {"a": a, "b": b, "t": "original"})
        c.execute(ins, {"a": a, "b": b, "t": "continuacion"})
        c.execute(ins, {"a": a, "b": b, "t": "continuacion"})
    with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
        c.execute(ins, {"a": a, "b": b, "t": "original"})


def test_la_bitacora_cerrada_exige_el_momento_de_cierre(esc):
    with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
        c.execute(text("insert into bitacora (persona_id, fecha_laboral, estado) values (:p, :f, 'cerrada')"),
                  {"p": esc.persona, "f": hoy()})


@pytest.mark.parametrize("sentencia", [
    "delete from avance", "delete from planificacion", "delete from actividad", "delete from bitacora",
    "update planificacion set descripcion = 'x'", "update avance set descripcion = 'x'",
])
def test_la_aplicacion_no_borra_avances_ni_edita_planificaciones(esc, sentencia):
    with pytest.raises(ProgrammingError) as e, get_engine().begin() as c:
        c.execute(text(sentencia))
    assert e.value.orig.sqlstate == "42501"


def test_la_comprobacion_derivar_y_comparar_detecta_un_estado_actual_incoherente(esc):
    with get_owner_engine().begin() as c:
        b = _bitacora(c, esc)
        a = _actividad(c, esc, b)
        assert estados_actuales_incoherentes(c) == []                 # sin avances: Pendiente
        c.execute(text("update actividad set estado_actual = 'Completada' where id = :a"), {"a": a})
        assert estados_actuales_incoherentes(c) == [a]               # almacenado distinto del derivado
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                       "values (:a, :b, 'Completada', 'terminado')"), {"a": a, "b": b})
        assert estados_actuales_incoherentes(c) == []                 # ahora coincide
