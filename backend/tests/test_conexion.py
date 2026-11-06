"""Bloque 2: conexión a PostgreSQL y privilegios mínimos de los roles."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.db import get_engine, get_owner_engine


def test_la_aplicacion_usa_el_rol_de_aplicacion_sin_privilegios_de_administracion():
    with get_engine().connect() as c:
        usuario, base, superusuario = c.execute(
            text("select current_user, current_database(), "
                 "(select rolsuper from pg_roles where rolname = current_user)")
        ).one()
    assert usuario == "smartwork_app"
    assert base.endswith("_test")
    assert superusuario is False


def test_el_rol_de_aplicacion_no_puede_crear_objetos():
    with get_engine().connect() as c, pytest.raises(ProgrammingError):
        c.execute(text("create table prueba_ddl (id int)"))


def test_el_propietario_conecta_a_la_base_de_pruebas():
    with get_owner_engine().connect() as c:
        usuario, base = c.execute(text("select current_user, current_database()")).one()
    assert usuario == "smartwork_owner"
    assert base.endswith("_test")


def test_zona_horaria_del_servidor_de_base_de_datos_es_consultable():
    with get_engine().connect() as c:
        assert c.execute(text("select now()")).scalar() is not None
