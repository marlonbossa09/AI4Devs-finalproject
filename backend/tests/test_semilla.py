"""DB-07: semilla de datos ficticios y sus protecciones."""

import pytest
from sqlalchemy import text

from app.db import get_owner_engine
from app.seguridad.contrasenas import verificar
from scripts.seed_dev import EntornoNoPermitido, comprobar_entorno_local, sembrar
from scripts.verificar_datos import lineas_temporales_incoherentes
from tests.fabricas import hoy


def test_tras_la_semilla_existen_personas_con_pertenencia_vigente_y_un_supervisor():
    credenciales = sembrar(get_owner_engine())
    assert set(credenciales) == {"supervisor.demo", "colaborador1.demo", "colaborador2.demo"}
    with get_owner_engine().connect() as c:
        vigentes = c.execute(
            text("select count(*) from pertenencia where desde <= :h and hasta_exclusivo is null"), {"h": hoy()}
        ).scalar_one()
        supervisores = c.execute(
            text("select count(*) from pertenencia where rol = 'supervisor' and desde <= :h"), {"h": hoy()}
        ).scalar_one()
        assert vigentes == 3 and supervisores == 1
        assert lineas_temporales_incoherentes(c) == []


def test_los_datos_sembrados_son_ficticios_y_las_contrasenas_no_se_guardan_en_claro():
    credenciales = sembrar(get_owner_engine())
    with get_owner_engine().connect() as c:
        nombres = [r[0] for r in c.execute(text("select nombre from persona"))]
        assert all("(demo)" in n for n in nombres)
        hashes = {r[0]: r[1] for r in c.execute(text("select identificador_acceso, hash_contrasena from identidad"))}
    for identificador, datos in credenciales.items():
        assert hashes[identificador].startswith("$argon2id$")
        assert datos["contrasena"] not in hashes[identificador]
        assert verificar(hashes[identificador], datos["contrasena"])
    assert len({d["contrasena"] for d in credenciales.values()}) == 3  # distintas entre sí
    assert all(len(d["contrasena"]) >= 15 for d in credenciales.values())


def test_la_semilla_no_sobrescribe_una_base_con_datos():
    sembrar(get_owner_engine())
    with pytest.raises(EntornoNoPermitido):
        sembrar(get_owner_engine())


@pytest.mark.parametrize("url,entorno", [
    ("postgresql+psycopg://u:p@db.ejemplo.com:5432/smartwork_dev", "development"),   # servidor remoto
    ("postgresql+psycopg://u:p@10.0.0.5:5432/smartwork_dev", "development"),          # no es de bucle local
    ("postgresql+psycopg://u:p@127.0.0.1:5432/smartwork", "development"),             # nombre no permitido
    ("postgresql+psycopg://u:p@127.0.0.1:5432/smartwork_prod", "development"),
    ("postgresql+psycopg://u:p@127.0.0.1:5432/smartwork_dev", "production"),          # entorno no permitido
])
def test_la_semilla_se_niega_fuera_de_un_entorno_local_de_desarrollo(url, entorno):
    with pytest.raises(EntornoNoPermitido):
        comprobar_entorno_local(url, entorno)


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://u:p@127.0.0.1:5433/smartwork_dev",
    "postgresql+psycopg://u:p@localhost:5432/smartwork_test",
])
def test_la_semilla_se_permite_en_una_base_local_dev_o_test(url):
    comprobar_entorno_local(url, "development")


def test_una_base_con_otro_nombre_solo_se_permite_con_autorizacion_explicita_y_exacta(monkeypatch):
    url = "postgresql+psycopg://u:p@127.0.0.1:5432/smartwork_app"
    monkeypatch.delenv("SMARTWORK_SEED_DATABASE", raising=False)
    with pytest.raises(EntornoNoPermitido):
        comprobar_entorno_local(url, "development")
    monkeypatch.setenv("SMARTWORK_SEED_DATABASE", "otra_base")      # otro nombre: no vale
    with pytest.raises(EntornoNoPermitido):
        comprobar_entorno_local(url, "development")
    monkeypatch.setenv("SMARTWORK_SEED_DATABASE", "smartwork_app")  # nombre exacto
    comprobar_entorno_local(url, "development")


def test_la_autorizacion_por_nombre_no_salta_la_exigencia_de_servidor_local(monkeypatch):
    monkeypatch.setenv("SMARTWORK_SEED_DATABASE", "smartwork_app")
    with pytest.raises(EntornoNoPermitido):
        comprobar_entorno_local("postgresql+psycopg://u:p@db.ejemplo.com:5432/smartwork_app", "development")
