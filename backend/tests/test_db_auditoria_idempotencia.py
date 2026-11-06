"""DB-04 (auditoría de solo anexado) y DB-05 (claves de idempotencia)."""

import threading
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError

from app.db import get_engine, get_owner_engine
from tests.fabricas import escenario_basico, hoy

INSERTAR = text(
    "insert into auditoria (tipo_autor, autor_persona_id, referencia_provision, operacion, tipo_objeto, "
    "objeto_id, propietaria_registro_id, fecha_laboral_registro, valor_anterior, valor_nuevo) "
    "values (:t, :a, :r, :o, 'bitacora', gen_random_uuid(), :p, :f, '{}'::jsonb, '{\"x\": 1}'::jsonb)"
)


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c)


def _params(esc, **cambios):
    base = {"t": "persona", "a": esc.persona, "r": None, "o": "modificacion_jornada_pasada",
            "p": esc.persona, "f": hoy() - timedelta(days=3)}
    base.update(cambios)
    return base


def test_la_aplicacion_puede_insertar_y_leer_la_auditoria(esc):
    with get_engine().begin() as c:
        c.execute(INSERTAR, _params(esc))
    with get_engine().connect() as c:
        assert c.execute(text("select count(*) from auditoria")).scalar_one() == 1


@pytest.mark.parametrize("sentencia", ["update auditoria set motivo = 'x'", "delete from auditoria"])
def test_el_rol_de_la_aplicacion_no_puede_actualizar_ni_borrar_la_auditoria(esc, sentencia):
    with get_engine().begin() as c:
        c.execute(INSERTAR, _params(esc))
    with pytest.raises(ProgrammingError) as e, get_engine().begin() as c:
        c.execute(text(sentencia))
    assert e.value.orig.sqlstate == "42501"


@pytest.mark.parametrize("sentencia", ["update auditoria set motivo = 'x'", "delete from auditoria"])
def test_ni_siquiera_el_propietario_puede_alterar_la_auditoria(esc, sentencia):
    with get_engine().begin() as c:
        c.execute(INSERTAR, _params(esc))
    with pytest.raises(DBAPIError) as e, get_owner_engine().begin() as c:
        c.execute(text(sentencia))
    assert e.value.orig.sqlstate == "23000"


def test_el_autor_de_provision_con_autor_persona_es_rechazado(esc):
    with pytest.raises(IntegrityError), get_engine().begin() as c:
        c.execute(INSERTAR, _params(esc, t="provision", a=esc.persona, r="orden-1"))


def test_el_autor_persona_sin_persona_o_con_referencia_de_provision_es_rechazado(esc):
    for cambios in ({"a": None}, {"r": "orden-1"}):
        with pytest.raises(IntegrityError), get_engine().begin() as c:
            c.execute(INSERTAR, _params(esc, **cambios))


def test_una_entrada_de_provision_valida_se_acepta(esc):
    with get_engine().begin() as c:
        c.execute(INSERTAR, _params(esc, t="provision", a=None, r="orden-1", o="alta"))


def test_una_operacion_desconocida_es_rechazada(esc):
    with pytest.raises(IntegrityError), get_engine().begin() as c:
        c.execute(INSERTAR, _params(esc, o="inventada"))


def test_si_falla_la_entrada_de_auditoria_no_queda_el_cambio_de_dominio(esc):
    """IR-24: la operación y su entrada son atómicas; si una falla, ninguna queda."""
    with pytest.raises(IntegrityError), get_owner_engine().begin() as c:
        c.execute(text("insert into bitacora (persona_id, fecha_laboral) values (:p, :f)"),
                  {"p": esc.persona, "f": hoy()})
        c.execute(INSERTAR, _params(esc, o="inventada"))
    with get_owner_engine().connect() as c:
        assert c.execute(text("select count(*) from bitacora")).scalar_one() == 0


# --- DB-05 ----------------------------------------------------------------------------------

CLAVE = text(
    "insert into clave_idempotencia (persona_id, operacion, clave, huella, estado_http, respuesta, caduca_en) "
    "values (:p, 'M2-03', :k, 'h', 201, '{}'::jsonb, now() + interval '1 day')"
)


def test_dos_peticiones_simultaneas_con_la_misma_clave_producen_una_sola_fila(esc):
    resultados: list[str] = []
    barrera = threading.Barrier(2)

    def intentar():
        barrera.wait()
        try:
            with get_engine().begin() as c:
                c.execute(CLAVE, {"p": esc.persona, "k": "clave-1"})
            resultados.append("ok")
        except IntegrityError:
            resultados.append("duplicada")

    hilos = [threading.Thread(target=intentar) for _ in range(2)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert sorted(resultados) == ["duplicada", "ok"]
    with get_owner_engine().connect() as c:
        assert c.execute(text("select count(*) from clave_idempotencia")).scalar_one() == 1


def test_una_clave_caducada_se_puede_eliminar_para_tratarla_como_nueva(esc):
    with get_engine().begin() as c:
        c.execute(CLAVE, {"p": esc.persona, "k": "clave-2"})
    with get_owner_engine().begin() as c:
        c.execute(text("update clave_idempotencia set caduca_en = now() - interval '1 minute'"))
    with get_engine().begin() as c:
        borradas = c.execute(text("delete from clave_idempotencia where caduca_en < now()")).rowcount
        c.execute(CLAVE, {"p": esc.persona, "k": "clave-2"})
    assert borradas == 1
