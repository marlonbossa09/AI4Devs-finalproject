"""Migración 0006: permisos mínimos de actualización del rol de la aplicación.

El rol de la aplicación solo puede actualizar las columnas que las operaciones aprobadas necesitan
(``actividad.estado_actual``; ``bitacora.resumen``, ``modificada_en``, ``estado`` y ``cerrada_en``).
Todo lo demás sigue denegado, con intentos reales contra la base de pruebas.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from app.db import get_engine, get_owner_engine
from tests.fabricas import escenario_basico, hoy


@pytest.fixture()
def ids():
    """Una bitácora, una actividad y un avance creados por el propietario del esquema."""
    with get_owner_engine().begin() as c:
        esc = escenario_basico(c)
        b = c.execute(text("insert into bitacora (persona_id, fecha_laboral) values (:p, :f) returning id"),
                      {"p": esc.persona, "f": hoy()}).scalar_one()
        a = c.execute(text("insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen) "
                           "values (:p, :b, 'Preparar informe', 'planificada') returning id"),
                      {"p": esc.persona, "b": b}).scalar_one()
        av = c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                            "values (:a, :b, 'En progreso', 'trabajo') returning id"), {"a": a, "b": b}).scalar_one()
    return {"persona": esc.persona, "bitacora": b, "actividad": a, "avance": av}


def test_la_aplicacion_puede_actualizar_el_estado_actual_de_una_actividad(ids):
    with get_engine().begin() as c:
        c.execute(text("update actividad set estado_actual = 'En progreso' where id = :a"), {"a": ids["actividad"]})
    with get_owner_engine().connect() as c:
        assert c.execute(text("select estado_actual from actividad where id = :a"),
                         {"a": ids["actividad"]}).scalar_one() == "En progreso"


def test_la_aplicacion_puede_guardar_el_resumen_y_cerrar_y_reabrir_una_bitacora(ids):
    with get_engine().begin() as c:
        c.execute(text("update bitacora set resumen = 'Hecho', modificada_en = now() where id = :b"),
                  {"b": ids["bitacora"]})
        c.execute(text("update bitacora set estado = 'cerrada', cerrada_en = now() where id = :b"),
                  {"b": ids["bitacora"]})
        c.execute(text("update bitacora set estado = 'abierta', cerrada_en = null where id = :b"),
                  {"b": ids["bitacora"]})
    with get_owner_engine().connect() as c:
        fila = c.execute(text("select resumen, estado, cerrada_en from bitacora where id = :b"),
                         {"b": ids["bitacora"]}).one()
    assert fila.resumen == "Hecho" and fila.estado == "abierta" and fila.cerrada_en is None


@pytest.mark.parametrize("sentencia", [
    # La identidad de la actividad: propietaria, bitácora de origen y título (IR-06, IR-33)
    "update actividad set titulo = 'Otro' where id = :a",
    "update actividad set propietaria_id = propietaria_id where id = :a",
    "update actividad set bitacora_origen_id = bitacora_origen_id where id = :a",
    # La marca de error pertenece a M3-05, que no forma parte de esta entrega
    "update actividad set registrada_por_error = true where id = :a",
    "update actividad set motivo_error = 'x' where id = :a",
    # La identidad de la bitácora: persona y fecha laboral
    "update bitacora set persona_id = persona_id where id = :b",
    "update bitacora set fecha_laboral = fecha_laboral + 1 where id = :b",
    "update bitacora set creada_en = now() where id = :b",
    # Avances y planificaciones no se editan ni se borran (las correcciones son de M3-03)
    "update avance set estado = 'Completada' where id = :v",
    "update avance set descripcion = 'x' where id = :v",
    "update planificacion set descripcion = 'x'",
    "delete from avance where id = :v",
    "delete from actividad where id = :a",
    "delete from bitacora where id = :b",
])
def test_lo_demas_sigue_denegado_para_la_aplicacion(ids, sentencia):
    parametros = {"a": ids["actividad"], "b": ids["bitacora"], "v": ids["avance"]}
    with pytest.raises(ProgrammingError) as e, get_engine().begin() as c:
        c.execute(text(sentencia), parametros)
    assert e.value.orig.sqlstate == "42501"


def test_el_cierre_sin_momento_de_cierre_sigue_siendo_rechazado_por_la_base(ids):
    """El permiso de columna no debilita la restricción de coherencia del cierre (0003)."""
    with pytest.raises(DBAPIError) as e, get_engine().begin() as c:
        c.execute(text("update bitacora set estado = 'cerrada' where id = :b"), {"b": ids["bitacora"]})
    assert e.value.orig.sqlstate == "23514"
