"""M1-T7 — uniformidad del inicio de sesión: el coste de verificación y el uso de conexiones no delatan si la cuenta existe.

No se comparan tiempos de pared (serían inestables): se comprueba la ESTRUCTURA que hace comparable el tiempo: el mismo número de
verificaciones Argon2 con los mismos parámetros para una cuenta que existe, una que no y una sin primer acceso; ninguna verificación
mientras dura una espera (el 429 responde sin calcular el hash); y que ninguna conexión queda con una transacción abierta mientras se
registra un evento tras un rechazo.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.db import get_owner_engine
from app.main import crear_app
from app.modulos.acceso import router
from app.seguridad import control_de_intentos as control
from tests.fabricas import crear_identidad, crear_persona, escenario_basico
from tests.utiles_http import ORIGEN, iniciar_sesion

MALA = "contraseña-incorrecta-123"


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        e = escenario_basico(c)
        crear_identidad(c, crear_persona(c, "Sin primer acceso"), "pendiente", None)
    return e


def cliente(host):
    return TestClient(crear_app(), base_url=ORIGEN, client=(host, 50000), raise_server_exceptions=False)


@pytest.fixture()
def verificaciones(monkeypatch):
    """Registra los parámetros Argon2 de cada hash contra el que se verifica una contraseña."""
    vistas, original = [], router.verificar

    def espia(hash_guardado, contrasena):
        vistas.append(hash_guardado.split("$")[1:4])          # ['argon2id', 'v=19', 'm=...,t=...,p=...']
        return original(hash_guardado, contrasena)
    monkeypatch.setattr(router, "verificar", espia)
    return vistas


def test_una_cuenta_que_existe_una_que_no_y_una_sin_primer_acceso_verifican_el_mismo_numero_de_veces_con_los_mismos_parametros(esc, verificaciones):
    for i, ident in enumerate((esc.identificador, "no.existe.nadie", "pendiente")):
        antes = len(verificaciones)
        assert iniciar_sesion(cliente(f"203.0.113.{10 + i}"), ident, MALA).status_code == 401
        assert len(verificaciones) == antes + 1                                          # exactamente una verificación por intento
    assert verificaciones[0] == verificaciones[1] == verificaciones[2]
    s = get_settings()
    assert verificaciones[0][2] == f"m={s.argon2_memory_kib},t={s.argon2_iterations},p={s.argon2_parallelism}"


def test_mientras_dura_una_espera_no_se_calcula_ningun_hash(esc, verificaciones):
    c = cliente("203.0.113.5")
    for _ in range(5):
        iniciar_sesion(c, esc.identificador, MALA)
    assert len(verificaciones) == 5
    for contrasena in (esc.contrasena, MALA, esc.contrasena):
        assert iniciar_sesion(c, esc.identificador, contrasena).status_code == 429
    assert len(verificaciones) == 5                                                      # ni con la contraseña buena ni con la mala


def test_el_limite_de_origen_tampoco_calcula_el_hash(esc, verificaciones):
    c = cliente("203.0.113.6")
    for i in range(30):
        iniciar_sesion(c, f"cuenta.{i}", MALA)
    assert len(verificaciones) == 30
    assert iniciar_sesion(c, esc.identificador, esc.contrasena).status_code == 429
    assert len(verificaciones) == 30


def test_tras_un_rechazo_el_evento_se_registra_sin_otra_conexion_con_una_transaccion_abierta(esc, monkeypatch):
    """Un acceso desactivado con credenciales correctas se rechaza (403) y su evento va en otra transacción: la de la petición ya
    no debe retener una conexión (ni su bloqueo de persona) mientras tanto, o 30 peticiones a la vez agotarían el pool."""
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() - interval '1 minute'"))
    rol, capturas, original = get_settings().app_db_role, [], control.registrar_evento

    def espia(conexion, tipo, **kw):
        with get_owner_engine().connect() as c:
            # ``pg_stat_activity.state`` está oculto a un rol sin privilegios: se cuentan los bloqueos ``virtualxid`` (transacciones abiertas).
            capturas.append((tipo, c.execute(text("select count(*) from pg_locks l join pg_stat_activity a on a.pid = l.pid "
                                                  "where a.usename = :r and l.locktype = 'virtualxid' and l.granted"), {"r": rol}).scalar_one(),
                             c.execute(text("select count(*) from pg_locks l join pg_stat_activity a on a.pid = l.pid "
                                            "where a.usename = :r and l.locktype = 'advisory' and l.granted"), {"r": rol}).scalar_one()))
        return original(conexion, tipo, **kw)
    monkeypatch.setattr(control, "registrar_evento", espia)
    assert iniciar_sesion(cliente("203.0.113.7"), esc.identificador, esc.contrasena).status_code == 403
    assert [c[0] for c in capturas] == ["acceso_desactivado_en_inicio"]
    assert capturas[0][1] == 0, "la transacción de la petición debe estar ya cerrada al registrar el evento"
    assert capturas[0][2] == 0, "ningún bloqueo consultivo retenido (ni el de la reserva ni el de la persona)"
