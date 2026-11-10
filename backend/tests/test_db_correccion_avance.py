"""Migración 0008: ``avance.modificado_en``, permisos mínimos de corrección e inmutabilidad (M3-03).

Intentos reales contra la base de pruebas: lo que la aplicación PUEDE corregir (cuatro columnas), lo que sigue
denegado y lo que la propia base rechaza aunque algo eluda el servicio.
"""

from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from app.db import get_engine, get_owner_engine
from tests.fabricas import escenario_basico, hoy

CORRECCION = ("update avance set estado = 'Bloqueada', descripcion = 'Corregido', motivo_bloqueo = 'Sin acceso', "
              "modificado_en = clock_timestamp() where id = :v")


@pytest.fixture()
def ids():
    """Una actividad con un avance (jornada hoy - 3) y otra bitácora (hoy - 2)."""
    with get_owner_engine().begin() as c:
        esc = escenario_basico(c)
        b = c.execute(text("insert into bitacora (persona_id, fecha_laboral) values (:p, :f) returning id"),
                      {"p": esc.persona, "f": hoy() - timedelta(days=3)}).scalar_one()
        otra = c.execute(text("insert into bitacora (persona_id, fecha_laboral) values (:p, :f) returning id"),
                         {"p": esc.persona, "f": hoy() - timedelta(days=2)}).scalar_one()
        a = c.execute(text("insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen) "
                           "values (:p, :b, 'Preparar informe', 'planificada') returning id"),
                      {"p": esc.persona, "b": b}).scalar_one()
        v = c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion) "
                           "values (:a, :b, 'En progreso', 'trabajo') returning id"), {"a": a, "b": b}).scalar_one()
        r = c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion, es_reactivacion) "
                           "values (:a, :b, 'En progreso', 'retomo', true) returning id"), {"a": a, "b": otra}).scalar_one()
    return {"persona": esc.persona, "bitacora": b, "otra": otra, "actividad": a, "avance": v, "reactivacion": r}


def _avance(ids, clave="avance"):
    with get_owner_engine().connect() as c:
        return c.execute(text("select * from avance where id = :v"), {"v": ids[clave]}).one()


# ---------------------------------------------------------------------------------- modificado_en

def test_un_avance_nuevo_nace_con_modificado_en_igual_a_registrado_en(ids):
    a = _avance(ids)
    assert a.modificado_en == a.registrado_en


def test_un_insert_que_indica_modificado_en_lo_conserva(ids):
    with get_owner_engine().begin() as c:
        v = c.execute(text("insert into avance (actividad_id, bitacora_id, registrado_en, modificado_en, estado, descripcion) "
                           "values (:a, :b, now(), now() + interval '1 minute', 'En progreso', 'x') returning id"),
                      {"a": ids["actividad"], "b": ids["bitacora"]}).scalar_one()
    with get_owner_engine().connect() as c:
        fila = c.execute(text("select registrado_en, modificado_en from avance where id = :v"), {"v": v}).one()
    assert fila.modificado_en > fila.registrado_en


def test_modificado_en_no_puede_ser_anterior_al_registro(ids):
    with pytest.raises(DBAPIError) as e, get_owner_engine().begin() as c:
        c.execute(text("insert into avance (actividad_id, bitacora_id, registrado_en, modificado_en, estado, descripcion) "
                       "values (:a, :b, now(), now() - interval '1 hour', 'En progreso', 'x')"),
                  {"a": ids["actividad"], "b": ids["bitacora"]})
    assert e.value.orig.sqlstate == "23514"


# ---------------------------------------------------------------------------------- permisos

def test_la_aplicacion_puede_corregir_estado_descripcion_motivo_y_modificado_en(ids):
    antes = _avance(ids)
    with get_engine().begin() as c:
        c.execute(text(CORRECCION), {"v": ids["avance"]})
    despues = _avance(ids)
    assert (despues.estado, despues.descripcion, despues.motivo_bloqueo) == ("Bloqueada", "Corregido", "Sin acceso")
    assert despues.modificado_en > antes.modificado_en
    assert (despues.id, despues.actividad_id, despues.bitacora_id, despues.registrado_en, despues.es_reactivacion) == (
        antes.id, antes.actividad_id, antes.bitacora_id, antes.registrado_en, antes.es_reactivacion)


@pytest.mark.parametrize("sentencia", [
    "update avance set registrado_en = now() where id = :v",
    "update avance set es_reactivacion = not es_reactivacion where id = :v",
    "update avance set bitacora_id = bitacora_id where id = :v",
    "update avance set actividad_id = actividad_id where id = :v",
    "update avance set id = gen_random_uuid() where id = :v",
    "delete from avance where id = :v",
    "delete from avance",
    "update planificacion set descripcion = 'x'",
])
def test_lo_demas_sigue_denegado_para_la_aplicacion(ids, sentencia):
    """No hay permiso de borrado (RN-52) ni de actualización de lo que no se corrige."""
    with pytest.raises(ProgrammingError) as e, get_engine().begin() as c:
        c.execute(text(sentencia), {"v": ids["avance"]})
    assert e.value.orig.sqlstate == "42501"
    with get_owner_engine().connect() as c:
        assert c.execute(text("select count(*) from avance")).scalar_one() == 2


# ---------------------------------------------------------------------------------- inmutabilidad

@pytest.mark.parametrize("columna,valor", [
    ("id", "gen_random_uuid()"),
    ("registrado_en", "registrado_en + interval '1 minute'"),
    ("registrado_en", "registrado_en - interval '1 minute'"),      # hacia atrás: la restricción de modificado_en no lo frena
    ("es_reactivacion", "not es_reactivacion"),
    ("bitacora_id", "(select id from bitacora where fecha_laboral = current_date - 2 limit 1)"),
    ("actividad_id", "(select id from actividad limit 1) "),
])
def test_la_identidad_de_un_avance_es_inmutable_aunque_se_eluda_el_servicio(ids, columna, valor):
    """Incluso el propietario del esquema: el disparador protege la fecha laboral (la bitácora), el momento de registro y
    la condición de reactivación."""
    if columna == "actividad_id":
        with get_owner_engine().begin() as c:
            otra = c.execute(text("insert into actividad (propietaria_id, bitacora_origen_id, titulo, origen) "
                                  "values (:p, :b, 'Otra', 'planificada') returning id"),
                             {"p": ids["persona"], "b": ids["bitacora"]}).scalar_one()
        valor = f"'{otra}'"
    with pytest.raises(DBAPIError) as e, get_owner_engine().begin() as c:
        c.execute(text(f"update avance set {columna} = {valor} where id = :v"), {"v": ids["avance"]})
    assert e.value.orig.sqlstate in ("23000", "23503", "23514")
    despues = _avance(ids)
    assert despues.registrado_en == _avance(ids).registrado_en


def test_modificado_en_solo_avanza_cuando_cambia_el_contenido(ids):
    with pytest.raises(DBAPIError) as e, get_owner_engine().begin() as c:
        c.execute(text("update avance set modificado_en = modificado_en + interval '1 minute' where id = :v"),
                  {"v": ids["avance"]})
    assert e.value.orig.sqlstate == "23000"


def test_modificado_en_no_retrocede(ids):
    with get_engine().begin() as c:
        c.execute(text(CORRECCION), {"v": ids["avance"]})
    with pytest.raises(DBAPIError) as e, get_owner_engine().begin() as c:
        c.execute(text("update avance set descripcion = 'Otra', modificado_en = registrado_en where id = :v"),
                  {"v": ids["avance"]})
    assert e.value.orig.sqlstate == "23000"


def test_una_actualizacion_sin_cambios_en_el_contenido_con_el_mismo_modificado_en_es_inocua(ids):
    antes = _avance(ids)
    with get_engine().begin() as c:
        c.execute(text("update avance set estado = estado, descripcion = descripcion where id = :v"), {"v": ids["avance"]})
    assert _avance(ids).modificado_en == antes.modificado_en


# ---------------------------------------------------------------------------------- coherencia y marca

def test_el_motivo_de_bloqueo_solo_existe_con_el_estado_bloqueada(ids):
    with pytest.raises(DBAPIError) as e, get_engine().begin() as c:
        c.execute(text("update avance set motivo_bloqueo = 'sobra', modificado_en = clock_timestamp() where id = :v"),
                  {"v": ids["avance"]})
    assert e.value.orig.sqlstate == "23514"
    with pytest.raises(DBAPIError) as e, get_owner_engine().begin() as c:
        c.execute(text("insert into avance (actividad_id, bitacora_id, estado, descripcion, motivo_bloqueo) "
                       "values (:a, :b, 'Pendiente', 'x', 'sobra')"), {"a": ids["actividad"], "b": ids["bitacora"]})
    assert e.value.orig.sqlstate == "23514"


def test_corregir_hacia_un_estado_distinto_de_bloqueada_exige_limpiar_el_motivo(ids):
    with get_engine().begin() as c:
        c.execute(text(CORRECCION), {"v": ids["avance"]})
    with pytest.raises(DBAPIError) as e, get_engine().begin() as c:
        c.execute(text("update avance set estado = 'En progreso', modificado_en = clock_timestamp() where id = :v"),
                  {"v": ids["avance"]})
    assert e.value.orig.sqlstate == "23514"
    with get_engine().begin() as c:
        c.execute(text("update avance set estado = 'En progreso', motivo_bloqueo = null, modificado_en = clock_timestamp() where id = :v"),
                  {"v": ids["avance"]})


def test_un_avance_de_una_actividad_marcada_no_se_corrige(ids):
    with get_owner_engine().begin() as c:
        c.execute(text("delete from avance where id = :v"), {"v": ids["reactivacion"]})   # una marcada no tiene avances posteriores
        c.execute(text("update actividad set registrada_por_error = true, motivo_error = 'x', marcada_por = propietaria_id, "
                       "marcada_en = now() where id = :a"), {"a": ids["actividad"]})
    with pytest.raises(DBAPIError) as e, get_engine().begin() as c:
        c.execute(text(CORRECCION), {"v": ids["avance"]})
    assert e.value.orig.sqlstate == "23000"


def test_revertida_la_marca_se_vuelve_a_poder_corregir(ids):
    with get_owner_engine().begin() as c:
        c.execute(text("delete from avance where id = :v"), {"v": ids["reactivacion"]})
        c.execute(text("update actividad set registrada_por_error = true, motivo_error = 'x', marcada_por = propietaria_id, "
                       "marcada_en = now() where id = :a"), {"a": ids["actividad"]})
        c.execute(text("update actividad set registrada_por_error = false, motivo_error = null, marcada_por = null, "
                       "marcada_en = null where id = :a"), {"a": ids["actividad"]})
    with get_engine().begin() as c:
        c.execute(text(CORRECCION), {"v": ids["avance"]})


def test_la_correccion_de_una_reactivacion_conserva_su_condicion(ids):
    with get_engine().begin() as c:
        c.execute(text("update avance set descripcion = 'Retomo, corregido', modificado_en = clock_timestamp() where id = :v"),
                  {"v": ids["reactivacion"]})
    assert _avance(ids, "reactivacion").es_reactivacion is True
