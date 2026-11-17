"""M1-T7 — el control de intentos fallidos de autenticación (ADR-002, A9 y A11; decisiones del 2026-11-17), nivel de la máquina de estados.

Curva de espera (cinco intentos libres y 30 s, 1, 2, 4, 8, 16, 32 min y 1 hora de máximo), contador por (cuenta, origen), límites por
origen (30 en 5 minutos y 200 en 1 hora), olvido tras 24 horas, reinicio tras un acierto, claves HMAC y determinación del origen.
El tiempo se controla sustituyendo ``control._ahora``: no se espera de verdad. Las pruebas destructivas corren solo sobre ``smartwork_test``.
"""

import re
from datetime import datetime, timedelta, timezone

import pytest

from app.config import Settings, get_settings
from app.db import get_engine
from app.seguridad import control_de_intentos as control
from tests.utiles_m2 import contar, filas

ID = "ana.prueba"
ORIGEN = "203.0.113.7"


class Reloj:
    def __init__(self):
        self.ahora = datetime(2026, 11, 17, 9, 0, tzinfo=timezone.utc)

    def __call__(self, conexion=None):
        return self.ahora

    def avanzar(self, **kw):
        self.ahora += timedelta(**kw)


@pytest.fixture()
def reloj(monkeypatch):
    r = Reloj()
    monkeypatch.setattr(control, "_ahora", r)
    return r


def reservar(identificador=ID, origen=ORIGEN):
    return control.reservar(get_engine(), identificador, origen)


def fallar(identificador=ID, origen=ORIGEN):
    """Un intento concedido que termina mal (el contador ya lo contó al reservar)."""
    r = reservar(identificador, origen)
    assert isinstance(r, control.Reserva), r
    return r


def contador(identificador=ID, origen=ORIGEN):
    return filas("select intentos, permitido_desde from control_de_intentos where clave = :k", k=control.clave_de_cuenta(identificador, origen))


# ======================================================= curva de espera =================================================

def test_la_curva_de_espera_son_los_valores_aprobados():
    esperado = {1: None, 2: None, 3: None, 4: None, 5: 30, 6: 60, 7: 120, 8: 240, 9: 480, 10: 960, 11: 1920, 12: 3600, 13: 3600, 50: 3600, 10 ** 6: 3600}
    assert {n: control.espera_tras_el_intento(n) for n in esperado} == esperado


def test_la_curva_nunca_supera_el_maximo_de_una_hora():
    assert max(control.espera_tras_el_intento(n) or 0 for n in range(1, 500)) == 3600


def test_los_valores_por_defecto_son_los_aprobados_el_2026_11_17():
    """Sin .env ni variables: lo que está fijado en el código es exactamente lo aprobado."""
    s = Settings(_env_file=None)
    assert (s.login_free_attempts, s.login_wait_base_seconds, s.login_wait_max_seconds) == (5, 30, 3600)
    assert s.login_counter_forget_hours == 24
    assert (s.login_origin_short_attempts, s.login_origin_short_window_seconds) == (30, 300)
    assert (s.login_origin_long_attempts, s.login_origin_long_window_seconds) == (200, 3600)
    assert (s.session_idle_minutes, s.session_absolute_minutes) == (60, 1440)
    assert s.auth_event_retention_days == 30 and s.trusted_proxies == []


def test_la_curva_y_los_limites_son_configurables(monkeypatch):
    monkeypatch.setattr(get_settings(), "login_free_attempts", 2)
    monkeypatch.setattr(get_settings(), "login_wait_base_seconds", 10)
    monkeypatch.setattr(get_settings(), "login_wait_max_seconds", 45)
    assert [control.espera_tras_el_intento(n) for n in (1, 2, 3, 4, 5)] == [None, 10, 20, 40, 45]


def test_la_retencion_de_eventos_nunca_baja_de_treinta_dias():
    with pytest.raises(ValueError):
        Settings(_env_file=None, auth_event_retention_days=29)
    assert Settings(_env_file=None, auth_event_retention_days=45).auth_event_retention_days == 45


def test_el_secreto_de_las_claves_exige_longitud_y_no_se_imprime():
    with pytest.raises(ValueError):
        Settings(_env_file=None, auth_pepper="corto")
    ajustes = Settings(_env_file=None, auth_pepper="x" * 40)
    assert "x" * 40 not in repr(ajustes) and "x" * 40 not in str(ajustes.auth_pepper)


@pytest.mark.parametrize("valor", ["no-es-una-red", "10.0.0.0/99", "10.0.0.1, abc"])
def test_los_proxies_de_confianza_deben_ser_direcciones_o_redes(valor):
    with pytest.raises(ValueError):
        Settings(_env_file=None, trusted_proxies=valor)


def test_retry_after_son_segundos_enteros_redondeados_hacia_arriba_y_como_minimo_uno():
    assert control.segundos_de_espera(timedelta(seconds=29.2)) == 30
    assert control.segundos_de_espera(timedelta(seconds=30)) == 30
    assert control.segundos_de_espera(timedelta(milliseconds=1)) == 1
    assert control.segundos_de_espera(timedelta(0)) == 1
    assert isinstance(control.segundos_de_espera(timedelta(seconds=0.5)), int)


# ======================================================= claves HMAC =====================================================

def test_las_claves_son_hmac_deterministas_y_no_contienen_el_identificador_ni_el_origen():
    k = control.clave_de_cuenta(ID, ORIGEN)
    assert re.fullmatch(r"[0-9a-f]{64}", k) and k == control.clave_de_cuenta(ID, ORIGEN)
    assert ID not in k and ORIGEN not in k
    assert control.clave_de_cuenta(ID, "198.51.100.1") != k and control.clave_de_cuenta("otra", ORIGEN) != k


def test_las_claves_de_distinto_ambito_nunca_coinciden_aunque_se_les_de_la_misma_entrada():
    assert len({control.clave_de_cuenta("a", "b"), control.clave_de_origen("a"), control.clave_de_operador("a"), control.clave_de_origen("b"),
                control.clave_de_operador("b")}) == 5


def test_la_clave_de_la_persona_operadora_no_coincide_con_la_de_una_cuenta_aunque_el_origen_este_vacio():
    """Aunque cada una viva en su tabla, los dominios de los HMAC son distintos (defensa en profundidad ante un cruce de tablas)."""
    assert control.clave_de_operador("operadora.cli") not in {control.clave_de_cuenta("operadora.cli", ""), control.clave_de_cuenta("operadora.cli", "desconocido"),
                                                             control.clave_de_origen("operadora.cli")}


def test_la_concatenacion_ambigua_no_produce_la_misma_clave():
    assert control.clave_de_cuenta("ab", "c") != control.clave_de_cuenta("a", "bc")


def test_otro_secreto_da_otras_claves(monkeypatch):
    antes = control.clave_de_cuenta(ID, ORIGEN)
    monkeypatch.setattr(get_settings(), "auth_pepper", type(get_settings().auth_pepper)("y" * 40))
    assert control.clave_de_cuenta(ID, ORIGEN) != antes


def test_sin_secreto_el_control_falla_cerrado(monkeypatch):
    monkeypatch.setattr(get_settings(), "auth_pepper", None)
    with pytest.raises(control.ProteccionNoConfigurada):
        control.comprobar_configuracion()
    with pytest.raises(control.ProteccionNoConfigurada):
        control.reservar(get_engine(), ID, ORIGEN)


# ======================================================= cinco intentos libres y esperas progresivas ====================

def test_los_cinco_primeros_intentos_no_tienen_espera_y_el_quinto_fija_la_primera(reloj):
    for n in range(1, 5):
        r = fallar()
        assert r.espera_resultante is None
    assert contador()[0][1] is None
    quinto = fallar()
    assert quinto.espera_resultante == 30
    assert contador() == [(5, reloj.ahora + timedelta(seconds=30))]


def test_el_sexto_intento_dentro_de_la_espera_se_deniega_con_lo_que_falta(reloj):
    for _ in range(5):
        fallar()
    d = reservar()
    assert d == control.Denegado(30, "espera")
    reloj.avanzar(seconds=12)
    assert reservar() == control.Denegado(18, "espera")
    reloj.avanzar(seconds=17.5)
    assert reservar() == control.Denegado(1, "espera")                      # nunca 0: se redondea hacia arriba


def test_una_peticion_denegada_no_cambia_ningun_estado_ni_prolonga_la_espera(reloj):
    for _ in range(5):
        fallar()
    antes = (contador(), contar("intento_de_origen"))
    for _ in range(25):
        assert isinstance(reservar(), control.Denegado)
    assert (contador(), contar("intento_de_origen")) == antes


def test_la_progresion_completa_30s_1_2_4_8_16_32_min_y_1_hora(reloj):
    for _ in range(5):
        fallar()
    esperas = []
    for _ in range(9):
        d = reservar()
        assert isinstance(d, control.Denegado)
        esperas.append(d.espera_segundos)
        reloj.avanzar(seconds=d.espera_segundos)                               # se espera exactamente lo indicado
        siguiente = fallar()                                                   # y el intento siguiente se concede (y falla)
        assert siguiente.espera_resultante is not None
    assert esperas == [30, 60, 120, 240, 480, 960, 1920, 3600, 3600]


def test_pasada_la_espera_el_intento_se_concede_y_la_siguiente_espera_es_el_doble(reloj):
    for _ in range(5):
        fallar()
    reloj.avanzar(seconds=30)
    sexto = reservar()
    assert isinstance(sexto, control.Reserva) and sexto.espera_resultante == 60
    assert isinstance(reservar(), control.Denegado)


def test_un_acierto_reinicia_el_contador_de_esa_cuenta_y_devuelve_la_reserva_de_origen(reloj):
    for _ in range(4):
        fallar()
    r = fallar()
    control.liberar(get_engine(), r)
    assert contador() == [] and contar("intento_de_origen") == 4                  # el contador se reinicia; la reserva del acierto se devuelve
    for _ in range(5):                                                         # vuelven los cinco intentos libres
        assert isinstance(reservar(), control.Reserva)


def test_el_reinicio_tambien_levanta_una_espera_en_curso(reloj):
    for _ in range(5):
        r = fallar()
    control.liberar(get_engine(), r)
    assert isinstance(reservar(), control.Reserva)


# ======================================================= independencia entre claves (no se bloquea a terceros) ==========

def test_los_fallos_de_otro_origen_no_hacen_esperar_a_la_misma_cuenta(reloj):
    for _ in range(12):
        reservar(ID, "198.51.100.99")                                           # un atacante desde otro origen
    r = reservar(ID, ORIGEN)                                                    # la víctima, desde el suyo
    assert isinstance(r, control.Reserva) and r.espera_resultante is None
    assert contador() == [(1, None)]


def test_los_fallos_de_una_cuenta_no_hacen_esperar_a_otra_en_el_mismo_origen(reloj):
    for _ in range(8):
        reservar("otra.cuenta", ORIGEN)
    assert isinstance(reservar(ID, ORIGEN), control.Reserva)


def test_un_identificador_inexistente_se_cuenta_igual_que_uno_existente(reloj):
    """El control no consulta si la cuenta existe: la misma progresión para cualquier identificador."""
    for ident in ("existe.ana", "no.existe.nadie"):
        assert [fallar(ident).espera_resultante for _ in range(5)] == [None, None, None, None, 30]
        assert reservar(ident) == control.Denegado(30, "espera")


# ======================================================= olvido tras 24 horas ===========================================

def test_el_contador_se_olvida_tras_24_horas_sin_nuevos_intentos(reloj):
    for _ in range(5):
        fallar()
    assert contador()[0][0] == 5
    reloj.avanzar(hours=24, seconds=1)                                          # ya pasaron 24 h desde el último intento
    r = reservar()
    assert isinstance(r, control.Reserva) and r.espera_resultante is None
    assert contador() == [(1, None)]                                            # volvió a empezar de cero


def test_el_olvido_no_depende_de_la_limpieza_de_filas(reloj, monkeypatch):
    """La limpieza acotada puede no llegar a una fila (otra transacción limpiando, o más filas caducadas que el límite): el contador
    caducado se ignora igualmente al evaluar la clave."""
    for _ in range(5):
        fallar()
    reloj.avanzar(hours=24, seconds=1)
    monkeypatch.setattr(control, "_limpiar_caducados", lambda *a, **k: None)
    r = reservar()
    assert isinstance(r, control.Reserva) and r.espera_resultante is None and contador() == [(1, None)]


def test_el_olvido_tambien_se_aplica_a_la_persona_operadora_sin_depender_de_la_limpieza(reloj, monkeypatch):
    from app.db import get_provision_engine
    for _ in range(5):
        with get_provision_engine().begin() as c:
            assert isinstance(control.reservar_operador(c, "operadora.cli"), control.Reserva)
    reloj.avanzar(hours=24, seconds=1)
    monkeypatch.setattr(control, "_limpiar_caducados", lambda *a, **k: None)
    with get_provision_engine().begin() as c:
        r = control.reservar_operador(c, "operadora.cli")
    assert isinstance(r, control.Reserva) and r.espera_resultante is None
    assert filas("select intentos from control_de_intentos_operador") == [(1,)]


def test_las_24_horas_se_cuentan_desde_el_ultimo_intento_concedido_no_desde_los_denegados(reloj):
    for _ in range(5):
        fallar()
    reloj.avanzar(seconds=29)
    for _ in range(10):
        reservar()                                                              # denegados: no mueven el último intento
    reloj.avanzar(hours=24)
    assert isinstance(reservar(), control.Reserva) and contador()[0][0] == 1


def test_un_intento_poco_antes_de_las_24_horas_mantiene_el_contador(reloj):
    for _ in range(5):
        fallar()
    reloj.avanzar(hours=23)
    r = reservar()
    assert isinstance(r, control.Reserva) and r.espera_resultante == 60 and contador()[0][0] == 6


# ======================================================= límites por origen =============================================

def _intentos_de_origen(n, origen=ORIGEN, prefijo="cuenta"):
    """n intentos a identificadores distintos desde un mismo origen (así ningún contador de cuenta interviene)."""
    return [control.reservar(get_engine(), f"{prefijo}{i}", origen) for i in range(n)]


def test_el_limite_corto_son_30_intentos_en_5_minutos(reloj):
    assert all(isinstance(r, control.Reserva) for r in _intentos_de_origen(30))
    d = reservar("la.numero.31")
    assert d == control.Denegado(300, "limite_de_origen")
    reloj.avanzar(seconds=100)
    assert reservar("la.numero.31") == control.Denegado(200, "limite_de_origen")
    reloj.avanzar(seconds=200)
    assert isinstance(reservar("la.numero.31"), control.Reserva)                # los 30 salieron de la ventana


def test_el_limite_largo_son_200_intentos_en_una_hora(reloj):
    concedidos = 0
    for lote in range(6):                                                       # 6 lotes de 30 separados por 5 minutos: 180
        concedidos += sum(isinstance(r, control.Reserva) for r in _intentos_de_origen(30, prefijo=f"l{lote}-"))
        reloj.avanzar(minutes=5)
    assert concedidos == 180
    concedidos += sum(isinstance(r, control.Reserva) for r in _intentos_de_origen(30, prefijo="l6-"))   # el séptimo lote llega a 200
    assert concedidos == 200
    reloj.avanzar(minutes=5)
    d = reservar("el.201")
    assert isinstance(d, control.Denegado) and d.motivo == "limite_de_origen"
    assert 0 < d.espera_segundos <= 3600                                        # se libera cuando salen los más antiguos
    reloj.avanzar(seconds=d.espera_segundos)
    assert isinstance(reservar("el.201"), control.Reserva)


def test_los_limites_por_origen_son_configurables(monkeypatch, reloj):
    monkeypatch.setattr(get_settings(), "login_origin_short_attempts", 3)
    monkeypatch.setattr(get_settings(), "login_origin_short_window_seconds", 60)
    resultados = _intentos_de_origen(4)
    assert [type(r).__name__ for r in resultados] == ["Reserva", "Reserva", "Reserva", "Denegado"]
    assert resultados[3].espera_segundos == 60


def test_un_origen_no_afecta_a_otro(reloj):
    _intentos_de_origen(31)
    assert isinstance(reservar("quien.sea", "198.51.100.1"), control.Reserva)


def test_los_aciertos_no_cuentan_para_el_origen_una_red_compartida_no_se_penaliza(reloj):
    """Cada inicio correcto devuelve su reserva: 100 personas iniciando sesión desde la misma red no agotan el límite."""
    for i in range(100):
        r = control.reservar(get_engine(), f"persona{i}", ORIGEN)
        assert isinstance(r, control.Reserva)
        control.liberar(get_engine(), r)
    assert contar("intento_de_origen") == 0 and contar("control_de_intentos") == 0
    assert isinstance(reservar("otra"), control.Reserva)


def test_el_limite_de_origen_prevalece_y_da_la_misma_respuesta_exista_o_no_la_cuenta(reloj):
    _intentos_de_origen(30)
    assert reservar("existe") == reservar("no.existe") == control.Denegado(300, "limite_de_origen")


def test_si_la_cuenta_espera_mas_que_el_origen_se_informa_la_mayor(reloj, monkeypatch):
    monkeypatch.setattr(get_settings(), "login_origin_short_attempts", 5)
    monkeypatch.setattr(get_settings(), "login_origin_short_window_seconds", 10)
    for _ in range(5):
        fallar()
    assert reservar() == control.Denegado(30, "espera")                         # el origen pediría 10 s; la cuenta, 30 s


# ======================================================= nada es permanente y las tablas se acotan ======================

def test_todo_lo_que_se_escribe_caduca_y_se_limpia_sin_planificador(reloj):
    for i in range(8):
        control.reservar(get_engine(), f"vieja{i}", f"192.0.2.{i}")
    assert contar("control_de_intentos") == 8 and contar("intento_de_origen") == 8
    reloj.avanzar(hours=25)
    reservar("nueva", "198.51.100.5")                                            # cualquier intento posterior limpia lo caducado
    assert contar("control_de_intentos") == 1 and contar("intento_de_origen") == 1


def test_la_limpieza_esta_acotada_por_intento(reloj, monkeypatch):
    monkeypatch.setattr(control, "LIMITE_DE_LIMPIEZA", 3)
    for i in range(10):
        control.reservar(get_engine(), f"vieja{i}", f"192.0.2.{i}")
    reloj.avanzar(hours=25)
    reservar("nueva", "198.51.100.5")
    assert contar("control_de_intentos") == 10 - 3 + 1


# ======================================================= origen de la petición (DT-07) ==================================

@pytest.fixture()
def proxies(monkeypatch):
    def fijar(*redes):
        monkeypatch.setattr(get_settings(), "trusted_proxies", list(redes))
    return fijar


def test_sin_proxies_de_confianza_se_usa_la_direccion_de_la_conexion_y_se_ignora_la_cabecera():
    assert control.direccion_del_cliente("203.0.113.9", ["198.51.100.1"]) == "203.0.113.9"
    assert control.direccion_del_cliente("203.0.113.9", ["1.1.1.1, 2.2.2.2"]) == "203.0.113.9"


def test_la_cabecera_solo_se_acepta_de_un_proxy_expresamente_configurado(proxies):
    proxies("10.0.0.0/8")
    assert control.direccion_del_cliente("10.1.2.3", ["198.51.100.4"]) == "198.51.100.4"
    assert control.direccion_del_cliente("192.0.2.50", ["198.51.100.4"]) == "192.0.2.50"     # no es un proxy de confianza: se ignora


def test_lo_que_escribe_el_cliente_a_la_izquierda_no_se_acepta_si_hay_una_direccion_anterior_de_un_proxy_propio(proxies):
    proxies("10.0.0.0/8")
    # El cliente real es 198.51.100.4; escribió 1.2.3.4 al principio para suplantar a otro: el proxy lo añade a continuación.
    assert control.direccion_del_cliente("10.0.0.2", ["1.2.3.4, 198.51.100.4"]) == "198.51.100.4"
    assert control.direccion_del_cliente("10.0.0.2", ["1.2.3.4", "198.51.100.4, 10.0.0.9"]) == "198.51.100.4"


def test_varios_proxies_de_confianza_encadenados_se_saltan(proxies):
    proxies("10.0.0.0/8", "172.16.0.0/12")
    assert control.direccion_del_cliente("10.0.0.2", ["198.51.100.4, 172.16.0.5, 10.0.0.9"]) == "198.51.100.4"


def test_una_cabecera_mal_formada_no_se_interpreta_y_se_usa_el_proxy(proxies):
    proxies("10.0.0.0/8")
    for malo in ("basura", "999.1.1.1", "1.2.3.4, basura", ""):
        assert control.direccion_del_cliente("10.0.0.2", [malo]) == "10.0.0.2"


def test_si_todas_las_direcciones_son_de_confianza_se_usa_la_conexion(proxies):
    proxies("10.0.0.0/8")
    assert control.direccion_del_cliente("10.0.0.2", ["10.0.0.7, 10.0.0.9"]) == "10.0.0.2"


def test_ipv6_se_normaliza_y_una_ipv4_mapeada_es_la_misma_direccion(proxies):
    assert control.direccion_del_cliente("2001:DB8:0:0:0:0:0:1", []) == "2001:db8::1"
    assert control.direccion_del_cliente("::ffff:203.0.113.9", []) == "203.0.113.9"


def test_sin_direccion_de_conexion_se_usa_un_valor_fijo_y_un_socket_no_es_una_direccion():
    assert control.direccion_del_cliente(None, ["1.2.3.4"]) == "desconocido"
    assert control.direccion_del_cliente("/run/app.sock", []) == "/run/app.sock"
    assert len(control.direccion_del_cliente("x" * 500, [])) <= 64
