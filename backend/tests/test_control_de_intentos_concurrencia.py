"""M1-T7 — concurrencia del control de intentos: la reserva es atómica y nadie se espera en círculo.

Con hilos y PostgreSQL reales. Sin reloj simulado: el tiempo es el real, pero las esperas (30 s) son mayores que lo que dura cada prueba,
así que lo concedido en cada ronda queda determinado solo por el orden de las reservas. Las pruebas destructivas corren solo sobre
``smartwork_test``.
"""

import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine, get_owner_engine
from app.main import crear_app
from app.seguridad import control_de_intentos as control
from tests.fabricas import escenario_basico
from tests.utiles_http import ORIGEN, iniciar_sesion
from tests.utiles_m2 import contar, filas

MALA = "contraseña-incorrecta-123"


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c)


def en_paralelo(n, tarea):
    """Lanza ``n`` hilos a la vez (barrera) y devuelve sus resultados; si alguno lanza, la prueba falla con esa excepción."""
    barrera = threading.Barrier(n)

    def ejecutar(i):
        barrera.wait(timeout=30)
        return tarea(i)
    with ThreadPoolExecutor(max_workers=n) as pool:
        return [f.result(timeout=120) for f in [pool.submit(ejecutar, i) for i in range(n)]]


def cliente(host):
    return TestClient(crear_app(), base_url=ORIGEN, client=(host, 50000), raise_server_exceptions=False)


# ===================================================== la reserva es atómica ==============================================

def test_veinte_reservas_simultaneas_de_la_misma_clave_conceden_exactamente_los_cinco_libres():
    resultados = en_paralelo(20, lambda i: control.reservar(get_engine(), "ana.prueba", "203.0.113.7"))
    concedidos = [r for r in resultados if isinstance(r, control.Reserva)]
    denegados = [r for r in resultados if isinstance(r, control.Denegado)]
    assert len(concedidos) == 5 and len(denegados) == 15
    assert all(d.motivo == "espera" and 1 <= d.espera_segundos <= 30 for d in denegados)
    assert sorted(r.espera_resultante or 0 for r in concedidos) == [0, 0, 0, 0, 30]
    assert filas("select intentos from control_de_intentos") == [(5,)]                          # contador exacto, sin duplicados ni pérdidas
    assert contar("intento_de_origen") == 5


def test_el_primer_intento_en_paralelo_nunca_duplica_la_fila_ni_viola_la_clave():
    for ronda in range(5):
        en_paralelo(12, lambda i: control.reservar(get_engine(), f"cuenta.{ronda}", f"198.51.100.{ronda}"))
    assert filas("select count(*), count(distinct clave) from control_de_intentos") == [(5, 5)]


def test_cincuenta_intentos_de_cuentas_distintas_desde_un_origen_conceden_exactamente_30():
    resultados = en_paralelo(50, lambda i: control.reservar(get_engine(), f"cuenta.{i}", "203.0.113.9"))
    assert Counter(type(r).__name__ for r in resultados) == {"Reserva": 30, "Denegado": 20}
    assert all(d.motivo == "limite_de_origen" and 1 <= d.espera_segundos <= 300 for d in resultados if isinstance(d, control.Denegado))
    assert contar("intento_de_origen") == 30


def test_claves_y_origenes_independientes_no_se_esperan_entre_si():
    """Se retiene el bloqueo de una clave: otra clave de otro origen se concede enseguida y la misma queda esperando (pg_locks)."""
    clave = control.clave_de_cuenta("ana.prueba", "203.0.113.7")
    retenido, resultado = get_owner_engine().connect(), {}
    try:
        retenido.execute(text("select pg_advisory_xact_lock(hashtextextended(:c, 0))"), {"c": f"smartwork:intentos:cuenta:{clave}"})
        hilo = threading.Thread(target=lambda: resultado.update(misma=control.reservar(get_engine(), "ana.prueba", "203.0.113.7")))
        hilo.start()
        fin = time.time() + 10
        while time.time() < fin and filas("select count(*) from pg_locks where locktype = 'advisory' and not granted")[0][0] < 1:
            time.sleep(0.05)
        assert filas("select count(*) from pg_locks where locktype = 'advisory' and not granted")[0][0] == 1       # la misma clave espera
        inicio = time.time()
        otra = control.reservar(get_engine(), "otra.persona", "198.51.100.1")
        assert isinstance(otra, control.Reserva) and time.time() - inicio < 5                      # otra clave y otro origen: sin esperas
        assert "misma" not in resultado
    finally:
        retenido.rollback()
        retenido.close()
    hilo.join(30)
    assert isinstance(resultado["misma"], control.Reserva)


def test_las_reservas_de_dos_cuentas_del_mismo_origen_en_ambos_ordenes_no_se_bloquean_en_circulo():
    """Muchas parejas de reservas cruzadas (cuenta A y B desde un origen, y B y A desde otro): el orden fijo de bloqueos evita el interbloqueo."""
    def tarea(i):
        return control.reservar(get_engine(), "A" if i % 2 else "B", "203.0.113.%d" % (i % 3))
    for _ in range(5):
        resultados = en_paralelo(24, tarea)
        assert all(isinstance(r, (control.Reserva, control.Denegado)) for r in resultados)
    assert contar("control_de_intentos") <= 6


def test_la_limpieza_concurrente_de_filas_caducadas_no_interbloquea(monkeypatch):
    monkeypatch.setattr(control, "LIMITE_DE_LIMPIEZA", 2)
    with get_owner_engine().begin() as c:
        for i in range(40):
            c.execute(text("insert into control_de_intentos (clave, intentos, ultimo_intento_en) values (:k, 1, now() - interval '3 days')"),
                      {"k": control.clave_de_cuenta(f"vieja{i}", "x")})
            c.execute(text("insert into intento_de_origen (clave_origen, en) values (:k, now() - interval '3 days')"),
                      {"k": control.clave_de_origen(f"vieja{i}")})
    en_paralelo(16, lambda i: control.reservar(get_engine(), f"nueva.{i}", f"198.51.100.{i}"))
    assert contar("control_de_intentos") <= 40 + 16 and contar("control_de_intentos") >= 16


# ===================================================== el inicio de sesión HTTP en paralelo ================================

def test_veinte_inicios_de_sesion_simultaneos_con_contrasena_mala_dan_cinco_401_y_quince_429(esc):
    clientes = [cliente("203.0.113.5") for _ in range(20)]
    resultados = en_paralelo(20, lambda i: iniciar_sesion(clientes[i], esc.identificador, MALA))
    assert Counter(r.status_code for r in resultados) == {401: 5, 429: 15}
    assert filas("select intentos from control_de_intentos") == [(5,)]
    assert (len(filas("select 1 from evento_autenticacion where tipo = 'inicio_fallido'")),
            len(filas("select 1 from evento_autenticacion where tipo = 'espera_aplicada'"))) == (5, 1)
    assert contar("sesion") == 0
    assert all(r.headers["retry-after"].isdigit() and 1 <= int(r.headers["retry-after"]) <= 30 for r in resultados if r.status_code == 429)


def test_un_acierto_y_varios_fallos_a_la_vez_no_fallan_ni_dejan_un_estado_incoherente(esc):
    clientes = [cliente("203.0.113.5") for _ in range(5)]
    resultados = en_paralelo(5, lambda i: iniciar_sesion(clientes[i], esc.identificador, esc.contrasena if i == 0 else MALA))
    assert sorted(r.status_code for r in resultados) == [201, 401, 401, 401, 401]       # los cinco caben en los intentos libres
    assert contar("sesion") == 1
    restante = filas("select intentos from control_de_intentos")
    assert restante == [] or 1 <= restante[0][0] <= 4                                   # o se reinició al final, o quedan los fallos posteriores
    assert contar("intento_de_origen") <= 4


def test_cuentas_distintas_desde_origenes_distintos_a_la_vez_no_se_penalizan_entre_si(esc):
    clientes = [cliente(f"203.0.113.{10 + i}") for i in range(10)]
    resultados = en_paralelo(10, lambda i: iniciar_sesion(clientes[i], esc.identificador, esc.contrasena))
    assert [r.status_code for r in resultados] == [201] * 10


def test_muchos_inicios_correctos_a_la_vez_de_la_misma_cuenta_y_origen_no_agotan_los_intentos_de_nadie(esc):
    """Pesimista pero acotado: caben los 5 libres a la vez; los siguientes ven la espera de la reserva y se deniegan, nunca un 500."""
    clientes = [cliente("203.0.113.5") for _ in range(8)]
    resultados = en_paralelo(8, lambda i: iniciar_sesion(clientes[i], esc.identificador, esc.contrasena))
    assert {r.status_code for r in resultados} <= {201, 429}
    assert Counter(r.status_code for r in resultados)[201] >= 5
    assert contar("sesion") == Counter(r.status_code for r in resultados)[201]
    # Tras la ráfaga, quien espera puede volver a entrar: la espera caduca (aquí se adelanta en la base) y nada queda bloqueado.
    with get_owner_engine().begin() as c:
        c.execute(text("update control_de_intentos set permitido_desde = null"))
    assert iniciar_sesion(cliente("203.0.113.5"), esc.identificador, esc.contrasena).status_code == 201


def test_la_cli_de_la_persona_operadora_en_paralelo_tambien_reserva_de_forma_atomica():
    """Los intentos de la persona operadora usan su propio contador con el rol de provisión."""
    from app.db import get_provision_engine

    def tarea(i):
        with get_provision_engine().begin() as c:
            return control.reservar_operador(c, "operadora.cli")
    resultados = en_paralelo(15, tarea)
    assert Counter(type(r).__name__ for r in resultados) == {"Reserva": 5, "Denegado": 10}
    assert filas("select intentos from control_de_intentos_operador") == [(5,)]
    assert contar("control_de_intentos") == 0                                           # nada del contador de las personas


def test_con_el_acceso_desactivado_los_inicios_validos_simultaneos_dan_403_o_429_sin_sesiones_ni_reinicios(esc):
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() - interval '1 minute'"))
    clientes = [cliente("203.0.113.5") for _ in range(12)]
    resultados = en_paralelo(12, lambda i: iniciar_sesion(clientes[i], esc.identificador, esc.contrasena))
    cuenta = Counter(r.status_code for r in resultados)
    assert set(cuenta) <= {403, 429} and cuenta[403] == 5 and cuenta[429] == 7          # los cinco libres se gastan; el resto, a la espera
    assert contar("sesion") == 0 and filas("select intentos from control_de_intentos") == [(5,)] and contar("intento_de_origen") == 5
