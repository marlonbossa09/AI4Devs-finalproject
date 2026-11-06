"""DB-01: personas, equipos y pertenencias (IR-02, IR-03, IR-27, IR-28)."""

from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.db import get_engine, get_owner_engine
from scripts.verificar_datos import lineas_temporales_incoherentes
from tests.fabricas import crear_equipo, crear_organizacion, crear_persona, crear_pertenencia

D = date(2026, 1, 1)


@pytest.fixture()
def base():
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c)
        return {"org": org, "equipo": crear_equipo(c, org), "otro_equipo": crear_equipo(c, org, "Otro")}


def test_dos_intervalos_solapados_de_una_persona_fallan_en_la_base_de_datos(base):
    with get_owner_engine().begin() as c:
        p = crear_persona(c)
        crear_pertenencia(c, p, base["equipo"], desde=D, hasta=D + timedelta(days=10))
    with pytest.raises(IntegrityError) as e, get_owner_engine().begin() as c:
        crear_pertenencia(c, p, base["otro_equipo"], desde=D + timedelta(days=5), hasta=D + timedelta(days=20))
    assert e.value.orig.sqlstate == "23P01"  # exclusion_violation


def test_solo_el_ultimo_intervalo_puede_carecer_de_fin(base):
    with get_owner_engine().begin() as c:
        p = crear_persona(c)
        crear_pertenencia(c, p, base["equipo"], desde=D)  # sin fin
    with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
        crear_pertenencia(c, p, base["otro_equipo"], desde=D + timedelta(days=30))  # también sin fin


def test_intervalos_contiguos_semiabiertos_son_validos(base):
    with get_owner_engine().begin() as c:
        p = crear_persona(c)
        crear_pertenencia(c, p, base["equipo"], desde=D, hasta=D + timedelta(days=10))
        crear_pertenencia(c, p, base["otro_equipo"], desde=D + timedelta(days=10))
        assert lineas_temporales_incoherentes(c) == []


def test_un_hueco_entre_intervalos_lo_detecta_el_script_de_verificacion(base):
    with get_owner_engine().begin() as c:
        p = crear_persona(c)
        crear_pertenencia(c, p, base["equipo"], desde=D, hasta=D + timedelta(days=10))
        crear_pertenencia(c, p, base["otro_equipo"], desde=D + timedelta(days=12))
        assert lineas_temporales_incoherentes(c) == [p]


def test_dos_supervisores_simultaneos_de_un_equipo_fallan(base):
    with get_owner_engine().begin() as c:
        crear_pertenencia(c, crear_persona(c, "S1"), base["equipo"], "supervisor", desde=D)
    with pytest.raises(IntegrityError) as e, get_owner_engine().begin() as c:
        crear_pertenencia(c, crear_persona(c, "S2"), base["equipo"], "supervisor", desde=D + timedelta(days=3))
    assert e.value.orig.sqlstate == "23P01"


def test_supervisor_consecutivo_y_colaboradores_simultaneos_son_validos(base):
    with get_owner_engine().begin() as c:
        crear_pertenencia(c, crear_persona(c, "S1"), base["equipo"], "supervisor", desde=D,
                          hasta=D + timedelta(days=10))
        crear_pertenencia(c, crear_persona(c, "S2"), base["equipo"], "supervisor", desde=D + timedelta(days=10))
        crear_pertenencia(c, crear_persona(c, "C1"), base["equipo"], desde=D)
        crear_pertenencia(c, crear_persona(c, "C2"), base["equipo"], desde=D)


def test_el_fin_debe_ser_posterior_al_inicio(base):
    with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
        crear_pertenencia(c, crear_persona(c), base["equipo"], desde=D, hasta=D)


def test_la_zona_horaria_de_la_organizacion_es_un_dato_consultable(base):
    with get_engine().connect() as c:
        zona = c.execute(text("select zona_horaria from organizacion where id = :i"),
                         {"i": base["org"]}).scalar_one()
    assert zona == "America/Bogota"


@pytest.mark.parametrize("sentencia", [
    "insert into persona (nombre) values ('x')",
    "update persona set nombre = 'y'",
    "delete from pertenencia",
    "delete from persona",
])
def test_la_aplicacion_no_escribe_ni_borra_personas_ni_pertenencias(sentencia, base):
    with pytest.raises(ProgrammingError) as e, get_engine().begin() as c:
        c.execute(text(sentencia))
    assert e.value.orig.sqlstate == "42501"  # insufficient_privilege
