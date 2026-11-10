"""Migración 0007: permisos y restricciones de coherencia de la marca de error (M3-05, M3-06).

Intentos reales contra la base de pruebas: lo que la aplicación PUEDE hacer con la marca (solo sus cuatro
columnas), lo que sigue denegado, y lo que la propia base rechaza aunque algo eluda el servicio.
"""

from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from app.db import get_engine, get_owner_engine
from tests.fabricas import escenario_basico, hoy

MARCA = ("update actividad set registrada_por_error = true, motivo_error = 'Duplicada', "
         "marcada_por = propietaria_id, marcada_en = now() where id = :a")
SIN_MARCA = ("update actividad set registrada_por_error = false, motivo_error = null, marcada_por = null, "
             "marcada_en = null where id = :a")


@pytest.fixture()
def ids():
    """Bitácora de origen (hoy - 5), una actividad, un avance de la misma jornada y otra bitácora posterior."""
    with get_owner_engine().begin() as c:
        esc = escenario_basico(c)
        b = c.execute(text("insert into bitacora (persona_id, fecha_laboral) values (:p, :f) returning id"),
                      {"p": esc.persona, "f": hoy() - timedelta(days=5)}).scalar_one()
        posterior = c.execute(text("insert into bitacora (persona_id, fecha_laboral) values (:p, :f) returning id"),
                              {"p": esc.persona, "f": hoy() - timedelta(days=2)}).scalar_one()
        a = c.execute(text("insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen) "
                           "values (:p, :b, 'Preparar informe', 'planificada') returning id"),
                      {"p": esc.persona, "b": b}).scalar_one()
        c.execute(text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) "
                       "values (:a, :b, 'original', 'previsto')"), {"a": a, "b": b})
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                       "values (:a, :b, 'En progreso', 'trabajo')"), {"a": a, "b": b})
    return {"persona": esc.persona, "bitacora": b, "posterior": posterior, "actividad": a}


def _marcar_como_propietario(ids):
    with get_owner_engine().begin() as c:
        c.execute(text(MARCA), {"a": ids["actividad"]})


# ---------------------------------------------------------------------------------------------- permisos

def test_la_aplicacion_puede_marcar_y_retirar_la_marca(ids):
    with get_engine().begin() as c:
        c.execute(text(MARCA), {"a": ids["actividad"]})
    with get_owner_engine().connect() as c:
        fila = c.execute(text("select * from actividad where id = :a"), {"a": ids["actividad"]}).one()
    assert fila.registrada_por_error is True and fila.motivo_error == "Duplicada" and fila.marcada_en is not None
    with get_engine().begin() as c:
        c.execute(text(SIN_MARCA), {"a": ids["actividad"]})
    with get_owner_engine().connect() as c:
        fila = c.execute(text("select * from actividad where id = :a"), {"a": ids["actividad"]}).one()
    assert (fila.registrada_por_error, fila.motivo_error, fila.marcada_por, fila.marcada_en) == (False, None, None, None)


@pytest.mark.parametrize("sentencia", [
    # La identidad de la actividad sigue siendo inmutable
    "update actividad set titulo = 'Otro' where id = :a",
    "update actividad set propietaria_id = propietaria_id where id = :a",
    "update actividad set bitacora_origen_id = bitacora_origen_id where id = :a",
    "update actividad set origen = 'no_planificada' where id = :a",
    "update actividad set creada_en = now() where id = :a",
    # La marca es lógica: no hay borrado físico de nada
    "delete from actividad where id = :a",
    "delete from avance where actividad_id = :a",
    "delete from planificacion where actividad_id = :a",
    "delete from bitacora where id = :b",
    # Los avances y las planificaciones siguen sin edición
    "update avance set registrado_en = now() where actividad_id = :a",
    "update planificacion set descripcion = 'x' where actividad_id = :a",
])
def test_lo_demas_sigue_denegado_para_la_aplicacion(ids, sentencia):
    with pytest.raises(ProgrammingError) as e, get_engine().begin() as c:
        c.execute(text(sentencia), {"a": ids["actividad"], "b": ids["bitacora"]})
    assert e.value.orig.sqlstate == "42501"


# ---------------------------------------------------------------------------------- restricción de coherencia

@pytest.mark.parametrize("sentencia", [
    # marca vigente sin motivo, con motivo vacío, sin autora o sin momento
    "update actividad set registrada_por_error = true, marcada_por = propietaria_id, marcada_en = now() where id = :a",
    "update actividad set registrada_por_error = true, motivo_error = '   ', marcada_por = propietaria_id, marcada_en = now() where id = :a",
    "update actividad set registrada_por_error = true, motivo_error = 'x', marcada_en = now() where id = :a",
    "update actividad set registrada_por_error = true, motivo_error = 'x', marcada_por = propietaria_id where id = :a",
    # restos de marca sin marca vigente
    "update actividad set motivo_error = 'x' where id = :a",
    "update actividad set marcada_por = propietaria_id where id = :a",
    "update actividad set marcada_en = now() where id = :a",
])
def test_la_base_rechaza_una_marca_incoherente(ids, sentencia):
    with pytest.raises(DBAPIError) as e, get_engine().begin() as c:
        c.execute(text(sentencia), {"a": ids["actividad"]})
    assert e.value.orig.sqlstate == "23514"


def test_la_reversion_deja_la_actividad_limpia_y_el_motivo_solo_consta_en_la_auditoria(ids):
    _marcar_como_propietario(ids)
    with get_engine().begin() as c:
        c.execute(text(SIN_MARCA), {"a": ids["actividad"]})
    with pytest.raises(DBAPIError) as e, get_engine().begin() as c:
        # dejar el motivo tras revertir es incoherente
        c.execute(text("update actividad set motivo_error = 'resto' where id = :a"), {"a": ids["actividad"]})
    assert e.value.orig.sqlstate == "23514"


# --------------------------------------------------------------------------------- disparadores (IR-18, RN-59)

def test_una_marca_vigente_no_se_reescribe(ids):
    _marcar_como_propietario(ids)
    for sentencia in ("update actividad set motivo_error = 'Otro motivo' where id = :a",
                      "update actividad set marcada_en = now() + interval '1 hour' where id = :a",
                      "update actividad set marcada_por = (select id from persona where id <> propietaria_id limit 1) where id = :a"):
        with pytest.raises(DBAPIError) as e, get_owner_engine().begin() as c:
            c.execute(text(sentencia), {"a": ids["actividad"]})
        assert e.value.orig.sqlstate in ("23000", "23503", "23514")
    with get_owner_engine().connect() as c:
        assert c.execute(text("select motivo_error from actividad where id = :a"), {"a": ids["actividad"]}).scalar_one() == "Duplicada"


def test_no_se_marca_una_actividad_con_avances_en_jornadas_posteriores_a_su_origen(ids):
    with get_owner_engine().begin() as c:
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                       "values (:a, :b, 'En progreso', 'otro día')"), {"a": ids["actividad"], "b": ids["posterior"]})
    with pytest.raises(DBAPIError) as e, get_engine().begin() as c:
        c.execute(text(MARCA), {"a": ids["actividad"]})
    assert e.value.orig.sqlstate == "23000"
    with get_owner_engine().connect() as c:
        assert c.execute(text("select registrada_por_error from actividad where id = :a"),
                         {"a": ids["actividad"]}).scalar_one() is False


def test_los_avances_de_la_jornada_de_origen_no_impiden_marcar(ids):
    with get_engine().begin() as c:        # el fixture ya tiene un avance de la jornada de origen
        c.execute(text(MARCA), {"a": ids["actividad"]})


def test_una_actividad_marcada_no_admite_avances_ni_continuaciones(ids):
    _marcar_como_propietario(ids)
    for motor in (get_engine(), get_owner_engine()):
        with pytest.raises(DBAPIError) as e, motor.begin() as c:
            c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                           "values (:a, :b, 'En progreso', 'no debe entrar')"),
                      {"a": ids["actividad"], "b": ids["posterior"]})
        assert e.value.orig.sqlstate == "23000"
        with pytest.raises(DBAPIError) as e, motor.begin() as c:
            c.execute(text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) "
                           "values (:a, :b, 'continuacion', 'no debe entrar')"),
                      {"a": ids["actividad"], "b": ids["posterior"]})
        assert e.value.orig.sqlstate == "23000"
    with get_owner_engine().connect() as c:
        assert c.execute(text("select count(*) from avance where actividad_id = :a"), {"a": ids["actividad"]}).scalar_one() == 1


def test_una_actividad_sin_marca_sigue_admitiendo_avances_y_continuaciones(ids):
    with get_engine().begin() as c:
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                       "values (:a, :b, 'En progreso', 'otro día')"), {"a": ids["actividad"], "b": ids["posterior"]})
        c.execute(text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) "
                       "values (:a, :b, 'continuacion', 'más adelante')"), {"a": ids["actividad"], "b": ids["posterior"]})


def test_tras_revertir_la_marca_vuelven_a_admitirse_registros(ids):
    _marcar_como_propietario(ids)
    with get_engine().begin() as c:
        c.execute(text(SIN_MARCA), {"a": ids["actividad"]})
    with get_engine().begin() as c:
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                       "values (:a, :b, 'En progreso', 'de nuevo')"), {"a": ids["actividad"], "b": ids["posterior"]})


def test_la_planificacion_original_de_una_actividad_nueva_se_inserta_sin_problema(ids):
    """El disparador solo vigila las continuaciones: la creación de una actividad (M2-03) no se ve afectada."""
    with get_engine().begin() as c:
        a = c.execute(text("insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen) "
                           "values (:p, :b, 'Nueva', 'planificada') returning id"),
                      {"p": ids["persona"], "b": ids["posterior"]}).scalar_one()
        c.execute(text("insert into planificacion (actividad_id, bitacora_id, tipo, descripcion) "
                       "values (:a, :b, 'original', 'previsto')"), {"a": a, "b": ids["posterior"]})
