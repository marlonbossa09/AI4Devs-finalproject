"""DB-02: identidad y sesiones. Solo hashes; identificador único y normalizado."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.db import get_engine, get_owner_engine
from tests.fabricas import crear_identidad, crear_persona, escenario_basico


def test_un_identificador_con_mayusculas_no_es_un_identificador_normalizado():
    with get_owner_engine().begin() as c:
        persona = crear_persona(c)
    with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
        c.execute(text("insert into identidad (persona_id, identificador_acceso) values (:p, 'Ana')"),
                  {"p": persona})


def test_el_identificador_repetido_con_otra_capitalizacion_es_rechazado():
    with get_owner_engine().begin() as c:
        crear_identidad(c, crear_persona(c, "A"), "ana", "contraseña-1234567")
        otra = crear_persona(c, "B")
    with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
        crear_identidad(c, otra, "ANA", "contraseña-1234567")  # el normalizador lo lleva a 'ana'


def test_una_persona_tiene_como_maximo_una_identidad():
    with get_owner_engine().begin() as c:
        p = crear_persona(c)
        crear_identidad(c, p, "ana", None)
    with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
        crear_identidad(c, p, "otra", None)


def test_ninguna_tabla_contiene_la_contrasena_en_claro_y_el_hash_es_argon2id():
    with get_owner_engine().begin() as c:
        esc = escenario_basico(c)
    with get_owner_engine().connect() as c:
        h = c.execute(text("select hash_contrasena from identidad")).scalar_one()
        assert h.startswith("$argon2id$")
        tablas = [r[0] for r in c.execute(text(
            "select table_name from information_schema.tables where table_schema='public' "
            "and table_name <> 'alembic_version'"))]
        for t in tablas:
            n = c.execute(text(f"select count(*) from {t} x where x::text like :p"),
                          {"p": f"%{esc.contrasena}%"}).scalar_one()
            assert n == 0, f"La contraseña aparece en claro en {t}"


def test_las_tablas_de_acceso_no_tienen_columnas_para_secretos_en_claro():
    with get_owner_engine().connect() as c:
        columnas = {r[0] for r in c.execute(text(
            "select column_name from information_schema.columns where table_schema='public' "
            "and table_name in ('identidad','sesion')"))}
    assert "contrasena" not in columnas and "secreto" not in columnas and "csrf_token" not in columnas
    assert {"hash_contrasena", "secreto_hash"} <= columnas


def test_la_aplicacion_solo_puede_actualizar_el_uso_y_la_revocacion_de_la_sesion():
    with get_owner_engine().begin() as c:
        escenario_basico(c)
        identidad = c.execute(text("select id from identidad")).scalar_one()
        c.execute(text("insert into sesion (identidad_id, secreto_hash, caduca_absoluta_en) "
                       "values (:i, 'h', now() + interval '1 hour')"), {"i": identidad})
    with get_engine().begin() as c:
        c.execute(text("update sesion set revocada_en = now(), ultimo_uso_en = now()"))
    for sentencia in ("update sesion set secreto_hash = 'otro'", "delete from sesion",
                      "update identidad set hash_contrasena = 'x'"):
        with pytest.raises(ProgrammingError), get_engine().begin() as c:
            c.execute(text(sentencia))
