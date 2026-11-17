"""M1-T7 — el inicio de sesión con control de intentos, visto desde la API HTTP real (FastAPI + PostgreSQL).

Cubre: cinco intentos libres, esperas progresivas y 429 ``DEMASIADAS_SOLICITUDES`` con ``Retry-After``; credenciales correctas durante la
espera; respuestas uniformes para identificadores existentes e inexistentes; reinicio tras un acierto; olvido a las 24 horas; límites por
origen; proxy de confianza y cabeceras falsificadas; eventos técnicos (A11) y ausencia de secretos; CSRF, origen, cookies y sesiones sin
cambios; y que no hay transacción ni bloqueo abiertos mientras se calcula Argon2. El tiempo se controla sustituyendo ``control._ahora``.
"""

import logging
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine, get_owner_engine
from app.main import crear_app
from app.seguridad import control_de_intentos as control
from app.seguridad.sesiones import NOMBRE_COOKIE
from tests.fabricas import crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, escenario_basico, hoy
from tests.test_control_de_intentos import Reloj
from tests.utiles_http import API, ORIGEN, cabeceras, iniciar_sesion
from tests.utiles_m2 import contar, filas

MALA = "contraseña-incorrecta-123"
IP_A, IP_B = "203.0.113.5", "203.0.113.6"


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c)


@pytest.fixture()
def reloj(monkeypatch):
    r = Reloj()
    monkeypatch.setattr(control, "_ahora", r)
    return r


def cliente_en(host: str = IP_A) -> TestClient:
    return TestClient(crear_app(), base_url=ORIGEN, client=(host, 50000), raise_server_exceptions=False)


def intentar(cliente, identificador, contrasena=MALA):
    return iniciar_sesion(cliente, identificador, contrasena)


def huella(r):
    """Lo observable de una respuesta, sin lo que cambia por naturaleza (fecha)."""
    return (r.status_code, r.json(), r.headers.get("retry-after"), r.headers.get("content-type"), r.headers.get("cache-control"),
            "set-cookie" in r.headers)


def eventos(tipo=None):
    consulta = "select tipo, ambito, persona_id, sesion_id, clave_cuenta, clave_origen, detalle from evento_autenticacion"
    return filas(consulta + (" where tipo = :t" if tipo else "") + " order by ocurrido_en, id", **({"t": tipo} if tipo else {}))


def fallar_cinco(cliente, identificador):
    for _ in range(5):
        assert intentar(cliente, identificador).status_code == 401


# ===================================================== cinco intentos libres y 429 =========================================

def test_los_cinco_primeros_fallos_son_401_uniformes_y_el_sexto_intento_es_429_con_retry_after(esc, reloj):
    c = cliente_en()
    for _ in range(5):
        r = intentar(c, esc.identificador)
        assert r.status_code == 401 and r.json()["codigo"] == "CREDENCIALES_INVALIDAS" and "retry-after" not in r.headers
    r = intentar(c, esc.identificador)
    assert r.status_code == 429
    assert r.json() == {"codigo": "DEMASIADAS_SOLICITUDES", "mensaje": "Demasiados intentos. Vuelva a intentarlo más tarde.",
                        "detalles": [{"espera_segundos": 30}]}
    assert r.headers["retry-after"] == "30" and r.headers["cache-control"] == "no-store" and "set-cookie" not in r.headers


def test_retry_after_es_coherente_con_el_tiempo_que_falta(esc, reloj):
    c = cliente_en()
    fallar_cinco(c, esc.identificador)
    assert intentar(c, esc.identificador).headers["retry-after"] == "30"
    reloj.avanzar(seconds=10)
    r = intentar(c, esc.identificador)
    assert r.headers["retry-after"] == "20" and r.json()["detalles"] == [{"espera_segundos": 20}]
    reloj.avanzar(seconds=19.5)
    assert intentar(c, esc.identificador).headers["retry-after"] == "1"


def test_con_credenciales_correctas_durante_la_espera_tambien_es_429_y_no_hay_sesion(esc, reloj):
    c = cliente_en()
    fallar_cinco(c, esc.identificador)
    r = intentar(c, esc.identificador, esc.contrasena)                       # la contraseña buena, pero dentro de la espera
    assert r.status_code == 429 and NOMBRE_COOKIE not in r.headers.get("set-cookie", "")
    assert contar("sesion") == 0 and eventos("inicio_correcto") == []


def test_pasada_la_espera_la_contrasena_correcta_inicia_sesion_y_reinicia_el_contador(esc, reloj):
    c = cliente_en()
    fallar_cinco(c, esc.identificador)
    reloj.avanzar(seconds=30)
    r = intentar(c, esc.identificador, esc.contrasena)
    assert r.status_code == 201 and r.cookies.get(NOMBRE_COOKIE)
    assert contar("control_de_intentos") == 0                                 # contador de la cuenta reiniciado
    assert contar("intento_de_origen") == 5                                   # el acierto devolvió su reserva; los 5 fallos siguen contando
    for _ in range(5):                                                        # vuelven los cinco intentos libres
        assert intentar(c, esc.identificador).status_code == 401
    assert intentar(c, esc.identificador).status_code == 429


def test_un_fallo_tras_la_espera_dobla_la_siguiente(esc, reloj):
    c = cliente_en()
    fallar_cinco(c, esc.identificador)
    reloj.avanzar(seconds=30)
    assert intentar(c, esc.identificador).status_code == 401
    r = intentar(c, esc.identificador)
    assert r.status_code == 429 and r.headers["retry-after"] == "60"


def test_la_progresion_http_30s_1_2_4_8_16_32_min_y_1_hora(esc, reloj):
    c = cliente_en()
    fallar_cinco(c, esc.identificador)
    vistas = []
    for _ in range(9):
        r = intentar(c, esc.identificador)
        assert r.status_code == 429
        espera = int(r.headers["retry-after"])
        vistas.append(espera)
        reloj.avanzar(seconds=espera)
        assert intentar(c, esc.identificador).status_code == 401
    assert vistas == [30, 60, 120, 240, 480, 960, 1920, 3600, 3600]


def test_las_peticiones_denegadas_no_prolongan_la_espera_ni_dejan_eventos(esc, reloj):
    c = cliente_en()
    fallar_cinco(c, esc.identificador)
    antes = (contar("evento_autenticacion"), contar("intento_de_origen"), filas("select intentos, permitido_desde from control_de_intentos"))
    for _ in range(20):
        assert intentar(c, esc.identificador).status_code == 429
    assert (contar("evento_autenticacion"), contar("intento_de_origen"), filas("select intentos, permitido_desde from control_de_intentos")) == antes


def test_el_contador_se_olvida_a_las_24_horas_sin_nuevos_intentos(esc, reloj):
    c = cliente_en()
    fallar_cinco(c, esc.identificador)
    assert intentar(c, esc.identificador).status_code == 429
    reloj.avanzar(hours=24, seconds=1)
    assert intentar(c, esc.identificador).status_code == 401                  # ni siquiera la espera de 30 s: empieza de cero
    assert filas("select intentos from control_de_intentos") == [(1,)]


# ===================================================== respuestas uniformes (sin enumeración) =============================

def test_el_mismo_recorrido_es_indistinguible_para_cuentas_existentes_e_inexistentes(esc, reloj):
    with get_owner_engine().begin() as c:
        crear_identidad(c, crear_persona(c, "Sin primer acceso"), "pendiente", None)
    recorridos = []
    for host, ident in (("10.1.0.1", esc.identificador), ("10.1.0.2", "no.existe.nadie"), ("10.1.0.3", "pendiente")):
        c = cliente_en(host)
        pasos = []
        for _ in range(5):
            pasos.append(huella(intentar(c, ident)))
        for espera in (30, 60, 120, 240):
            pasos.append(huella(intentar(c, ident)))                          # 429
            pasos.append(huella(intentar(c, ident, "contraseña-que-sea-1234")))
            reloj.avanzar(seconds=espera)
            pasos.append(huella(intentar(c, ident)))                          # 401 de nuevo
        recorridos.append(pasos)
    assert recorridos[0] == recorridos[1] == recorridos[2]
    assert {p[0] for p in recorridos[0]} == {401, 429}


def test_un_identificador_inventado_no_deja_su_texto_en_ninguna_tabla(esc, reloj):
    inventado = "identificador.inventado.por.un.atacante"
    for _ in range(6):
        intentar(cliente_en(), inventado)
    for tabla in ("control_de_intentos", "intento_de_origen", "evento_autenticacion"):
        assert all(inventado not in f[0] for f in filas(f"select t::text from {tabla} t"))


def test_las_variantes_de_un_mismo_identificador_comparten_el_contador(esc, reloj):
    """El identificador se normaliza (mayúsculas, espacios y Unicode) ANTES de calcular la clave: cambiar la forma no da intentos nuevos."""
    c = cliente_en()
    for variante in ("ANA.PRUEBA", " ana.prueba ", "Ana.Prueba", "ＡＮＡ.prueba", "ana.prueba"):          # la cuarta usa letras de ancho completo (NFKC)
        assert intentar(c, variante).status_code == 401
    assert intentar(c, "ana.PRUEBA").status_code == 429
    assert filas("select intentos from control_de_intentos") == [(5,)]


# ===================================================== independencia entre orígenes y cuentas ==============================

def test_los_fallos_desde_un_origen_no_hacen_esperar_a_la_misma_cuenta_desde_otro(esc, reloj):
    atacante, victima = cliente_en(IP_A), cliente_en(IP_B)
    fallar_cinco(atacante, esc.identificador)
    assert intentar(atacante, esc.identificador).status_code == 429
    assert intentar(victima, esc.identificador, esc.contrasena).status_code == 201     # la víctima, desde otro origen, entra sin esperar


def test_los_fallos_en_una_cuenta_no_hacen_esperar_a_otra_en_el_mismo_origen(esc, reloj):
    c = cliente_en()
    fallar_cinco(c, "otra.cuenta")
    assert intentar(c, "otra.cuenta").status_code == 429
    assert intentar(c, esc.identificador, esc.contrasena).status_code == 201


# ===================================================== límites por origen ==================================================

def test_el_limite_por_origen_son_30_intentos_fallidos_en_5_minutos(esc, reloj):
    c = cliente_en()
    for i in range(30):
        assert intentar(c, f"cuenta.{i}").status_code == 401
    r = intentar(c, esc.identificador, esc.contrasena)                                   # incluso con la contraseña buena
    assert r.status_code == 429 and r.headers["retry-after"] == "300"
    reloj.avanzar(seconds=300)
    assert intentar(c, esc.identificador, esc.contrasena).status_code == 201


def test_el_limite_por_origen_es_el_mismo_para_cuentas_que_existen_y_que_no(esc, reloj):
    c = cliente_en()
    for i in range(30):
        intentar(c, f"cuenta.{i}")
    assert huella(intentar(c, esc.identificador)) == huella(intentar(c, "no.existe"))


def test_otro_origen_no_sufre_el_limite_de_una_red_saturada(esc, reloj):
    for i in range(30):
        intentar(cliente_en(IP_A), f"cuenta.{i}")
    assert intentar(cliente_en(IP_A), "x").status_code == 429
    assert intentar(cliente_en(IP_B), esc.identificador, esc.contrasena).status_code == 201


def test_una_red_compartida_no_se_penaliza_por_sus_inicios_correctos(esc, reloj):
    """40 inicios de sesión correctos desde la misma red (más que el límite de 30): ninguno cuenta como intento fallido."""
    c = cliente_en()
    for _ in range(40):
        assert intentar(c, esc.identificador, esc.contrasena).status_code == 201
    assert contar("intento_de_origen") == 0 and contar("control_de_intentos") == 0


def test_el_limite_largo_se_aplica_y_se_levanta_solo(esc, reloj):
    c = cliente_en()
    for lote in range(6):
        for i in range(30):
            assert intentar(c, f"l{lote}.{i}").status_code == 401
        reloj.avanzar(minutes=5)
    for i in range(20):
        assert intentar(c, f"l6.{i}").status_code == 401
    r = intentar(c, esc.identificador, esc.contrasena)                                   # 200 en la última hora
    assert r.status_code == 429
    reloj.avanzar(seconds=int(r.headers["retry-after"]))
    assert intentar(c, esc.identificador, esc.contrasena).status_code == 201


# ===================================================== proxy de confianza y cabeceras falsificadas =========================

def test_sin_proxy_de_confianza_una_cabecera_falsificada_se_ignora_y_no_se_puede_atacar_a_otro_origen(esc, reloj):
    atacante = cliente_en(IP_A)
    for _ in range(8):
        r = atacante.post(f"{API}/sesion", json={"identificador_acceso": esc.identificador, "contrasena": MALA},
                          headers={"Origin": ORIGEN, "X-Forwarded-For": IP_B})            # se hace pasar por la víctima
        assert r.status_code in (401, 429)
    assert intentar(cliente_en(IP_B), esc.identificador, esc.contrasena).status_code == 201   # la víctima real no esperó
    # Lo único que consta a nombre del origen de la víctima es su propio inicio correcto: ningún fallo se le atribuyó.
    assert filas("select tipo from evento_autenticacion where clave_origen = :k", k=control.clave_de_origen(IP_B)) == [("inicio_correcto",)]


def test_el_atacante_no_se_libra_del_limite_cambiando_la_cabecera(esc, reloj):
    atacante = cliente_en(IP_A)
    estados = []
    for i in range(7):
        r = atacante.post(f"{API}/sesion", json={"identificador_acceso": esc.identificador, "contrasena": MALA},
                          headers={"Origin": ORIGEN, "X-Forwarded-For": f"198.51.100.{i}"})
        estados.append(r.status_code)
    assert estados == [401] * 5 + [429] * 2


def test_con_un_proxy_de_confianza_se_usa_el_cliente_real_de_la_cabecera(esc, reloj, monkeypatch):
    monkeypatch.setattr(get_settings(), "trusted_proxies", ["10.0.0.0/8"])
    balanceador = cliente_en("10.0.0.2")

    def desde(ip_cliente, contrasena=MALA):
        return balanceador.post(f"{API}/sesion", json={"identificador_acceso": esc.identificador, "contrasena": contrasena},
                                headers={"Origin": ORIGEN, "X-Forwarded-For": f"1.2.3.4, {ip_cliente}"})   # 1.2.3.4: lo que escribió el cliente
    for _ in range(5):
        assert desde("198.51.100.4").status_code == 401
    assert desde("198.51.100.4").status_code == 429
    assert desde("198.51.100.5", esc.contrasena).status_code == 201                      # otro cliente tras el mismo balanceador
    assert filas("select count(*) from evento_autenticacion where clave_origen = :k", k=control.clave_de_origen("198.51.100.4"))[0][0] == 6
    assert filas("select count(*) from evento_autenticacion where clave_origen = :k", k=control.clave_de_origen("10.0.0.2")) == [(0,)]


def test_con_un_proxy_de_confianza_pero_una_conexion_ajena_la_cabecera_se_ignora(esc, reloj, monkeypatch):
    monkeypatch.setattr(get_settings(), "trusted_proxies", ["10.0.0.0/8"])
    c = cliente_en(IP_A)                                                                # no es el balanceador
    for _ in range(5):
        c.post(f"{API}/sesion", json={"identificador_acceso": esc.identificador, "contrasena": MALA},
               headers={"Origin": ORIGEN, "X-Forwarded-For": "198.51.100.4"})
    assert filas("select count(*) from evento_autenticacion where clave_origen = :k", k=control.clave_de_origen("198.51.100.4")) == [(0,)]
    assert filas("select count(*) from evento_autenticacion where clave_origen = :k", k=control.clave_de_origen(IP_A))[0][0] >= 5


# ===================================================== CSRF, origen, cookies y sesiones sin cambios =======================

@pytest.mark.parametrize("origen", ["https://evil.example", "null", None])
def test_una_peticion_con_origen_invalido_se_rechaza_antes_de_contar_nada(esc, reloj, origen):
    c = cliente_en()
    for _ in range(10):
        r = iniciar_sesion(c, esc.identificador, MALA, origen=origen)
        assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert (contar("control_de_intentos"), contar("intento_de_origen"), contar("evento_autenticacion")) == (0, 0, 0)


def test_una_solicitud_mal_formada_no_cuenta_como_intento(esc, reloj):
    c = cliente_en()
    r = c.post(f"{API}/sesion", headers={"Origin": ORIGEN}, json={"identificador_acceso": "a", "contrasena": "b", "rol": "supervisor"})
    assert r.status_code == 400 and contar("control_de_intentos") == 0


def test_el_inicio_correcto_conserva_la_cookie_el_csrf_y_el_cierre(esc, reloj):
    c = cliente_en()
    r = intentar(c, esc.identificador, esc.contrasena)
    assert r.status_code == 201 and set(r.json()) == {"persona", "rol_vigente", "csrf_token"}
    cookie = next(v for v in r.headers.get_list("set-cookie") if v.startswith(f"{NOMBRE_COOKIE}=")).lower()
    assert "secure" in cookie and "httponly" in cookie and "samesite=strict" in cookie and "path=/" in cookie and "domain" not in cookie
    assert c.post(f"{API}/sesion/cierre", headers={"Origin": ORIGEN}).status_code == 400            # sin CSRF
    assert c.post(f"{API}/sesion/cierre", headers=cabeceras(r.json()["csrf_token"])).status_code == 204
    assert c.get(f"{API}/sesion").status_code == 401                                                # revocada en el servidor


def test_la_sesion_dura_lo_configurado_y_los_valores_por_defecto_son_24_horas_y_1_hora(esc, reloj):
    r = intentar(cliente_en(), esc.identificador, esc.contrasena)
    assert r.status_code == 201
    absoluta = filas("select caduca_absoluta_en - creada_en from sesion")[0][0]
    assert abs(absoluta - timedelta(minutes=get_settings().session_absolute_minutes)) < timedelta(seconds=5)


def test_en_desarrollo_un_cliente_de_otro_origen_puede_leer_retry_after(esc, reloj, monkeypatch):
    """El cliente Flutter de desarrollo corre en otro origen (CORS): sin ``Access-Control-Expose-Headers`` el navegador no le deja leer la cabecera."""
    monkeypatch.setattr(get_settings(), "app_env", "development")
    monkeypatch.setattr(get_settings(), "cors_allowed_origins", ["http://localhost:8080"])
    c = TestClient(crear_app(), base_url=ORIGEN, client=(IP_A, 50000), raise_server_exceptions=False)
    for _ in range(5):
        c.post(f"{API}/sesion", headers={"Origin": "http://localhost:8080"}, json={"identificador_acceso": esc.identificador, "contrasena": MALA})
    r = c.post(f"{API}/sesion", headers={"Origin": "http://localhost:8080"}, json={"identificador_acceso": esc.identificador, "contrasena": MALA})
    assert r.status_code == 429 and r.headers["retry-after"] == "30"
    assert "retry-after" in r.headers["access-control-expose-headers"].lower()


# ===================================================== eventos técnicos (A11) y ausencia de secretos ========================

def test_los_fallos_dejan_eventos_sin_persona_y_la_espera_se_registra_una_vez(esc, reloj):
    c = cliente_en()
    fallar_cinco(c, esc.identificador)
    for _ in range(10):
        intentar(c, esc.identificador)                                                              # 429: sin eventos nuevos
    fallidos, esperas = eventos("inicio_fallido"), eventos("espera_aplicada")
    assert len(fallidos) == 5 and len(esperas) == 1 and len(eventos()) == 6
    assert all(f[1] == "persona" and f[2] is None and f[3] is None for f in fallidos)           # sin persona: es un intento no autenticado
    assert esperas[0].detalle == {"espera_segundos": 30}
    assert {f.clave_cuenta for f in fallidos} == {control.clave_de_cuenta(esc.identificador, IP_A)}
    assert {f.clave_origen for f in fallidos} == {control.clave_de_origen(IP_A)}


def test_el_inicio_correcto_deja_un_evento_con_la_persona_y_la_sesion(esc, reloj):
    assert intentar(cliente_en(), esc.identificador, esc.contrasena).status_code == 201
    (ev,) = eventos("inicio_correcto")
    sesion_id = filas("select id from sesion")[0][0]
    assert ev.persona_id == esc.persona and ev.sesion_id == sesion_id and ev.ambito == "persona"


def test_el_cierre_de_sesion_deja_un_evento(esc, reloj):
    c = cliente_en()
    csrf = intentar(c, esc.identificador, esc.contrasena).json()["csrf_token"]
    assert c.post(f"{API}/sesion/cierre", headers=cabeceras(csrf)).status_code == 204
    (ev,) = eventos("cierre_sesion")
    assert ev.persona_id == esc.persona and ev.sesion_id == filas("select id from sesion")[0][0]


def test_un_acceso_desactivado_deja_el_evento_y_no_crea_sesion(esc, reloj):
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() - interval '1 minute'"))
    r = intentar(cliente_en(), esc.identificador, esc.contrasena)
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO" and contar("sesion") == 0
    (ev,) = eventos("acceso_desactivado_en_inicio")
    assert ev.persona_id == esc.persona and eventos("inicio_correcto") == []
    # Contraseña válida pero SIN poder operar: no es una autenticación completa, el intento sigue contando (decisión del 2026-11-17).
    assert filas("select intentos from control_de_intentos") == [(1,)] and contar("intento_de_origen") == 1


# ===================================================== interpretación 5: solo una autenticación COMPLETA reinicia el contador ===========

def _desactivar(valor="now() - interval '1 minute'"):
    with get_owner_engine().begin() as c:
        c.execute(text(f"update persona set acceso_desactivado_en = {valor}"))


def _sin_pertenencia():
    with get_owner_engine().begin() as c:
        c.execute(text("update pertenencia set hasta_exclusivo = current_date - 1"))


@pytest.mark.parametrize("motivo", ["desactivado", "sin_pertenencia"])
def test_una_contrasena_valida_sin_poder_operar_no_reinicia_el_contador_ni_devuelve_la_reserva_de_origen(esc, reloj, motivo):
    c = cliente_en()
    for _ in range(3):
        assert intentar(c, esc.identificador).status_code == 401
    _desactivar() if motivo == "desactivado" else _sin_pertenencia()
    r = intentar(c, esc.identificador, esc.contrasena)
    assert r.status_code == 403 and r.json()["codigo"] == ("ACCESO_DESACTIVADO" if motivo == "desactivado" else "SIN_PERTENENCIA_VIGENTE")
    assert filas("select intentos from control_de_intentos") == [(4,)]                  # contó como un intento más: no se reinició
    assert contar("intento_de_origen") == 4                                              # y la reserva de origen NO se devolvió
    assert contar("sesion") == 0


@pytest.mark.parametrize("motivo", ["desactivado", "sin_pertenencia"])
def test_no_se_pueden_sondear_sin_limite_contrasenas_de_una_cuenta_que_no_puede_operar(esc, reloj, motivo):
    """Con el acceso desactivado (o sin pertenencia) las contraseñas correctas dan 403 y gastan los cinco intentos libres: el sexto, 429."""
    _desactivar() if motivo == "desactivado" else _sin_pertenencia()
    c = cliente_en()
    assert [intentar(c, esc.identificador, esc.contrasena).status_code for _ in range(5)] == [403] * 5
    r = intentar(c, esc.identificador, esc.contrasena)
    assert r.status_code == 429 and r.headers["retry-after"] == "30"
    assert intentar(c, esc.identificador, MALA).status_code == 429
    assert contar("sesion") == 0


def test_la_respuesta_con_el_acceso_desactivado_no_cambia_y_sigue_siendo_distinta_solo_de_las_credenciales_validas(esc, reloj):
    _desactivar()
    c = cliente_en()
    assert intentar(c, esc.identificador, MALA).status_code == 401
    assert intentar(c, esc.identificador, esc.contrasena).json()["codigo"] == "ACCESO_DESACTIVADO"       # comportamiento existente (CA-29, CA-255)


def test_cuando_se_vuelve_a_habilitar_el_acceso_la_siguiente_autenticacion_completa_si_reinicia(esc, reloj):
    c = cliente_en()
    _desactivar()
    for _ in range(5):
        intentar(c, esc.identificador, esc.contrasena)
    assert intentar(c, esc.identificador, esc.contrasena).status_code == 429
    with get_owner_engine().begin() as con:
        con.execute(text("update persona set acceso_desactivado_en = null"))
    reloj.avanzar(seconds=30)
    assert intentar(c, esc.identificador, esc.contrasena).status_code == 201
    assert contar("control_de_intentos") == 0 and contar("intento_de_origen") == 5       # reinicio y reserva devuelta SOLO con la sesión creada


def test_el_reinicio_va_en_la_misma_transaccion_que_la_sesion(esc, reloj, monkeypatch):
    """Si no llega a crearse la sesión (error al insertarla), el contador NO se reinicia: no hay autenticación completa."""
    from app.modulos.acceso import router
    monkeypatch.setattr(router, "hash_secreto", lambda *a: (_ for _ in ()).throw(RuntimeError("falla")))
    r = intentar(cliente_en(), esc.identificador, esc.contrasena)
    assert r.status_code == 500 and contar("sesion") == 0
    assert filas("select intentos from control_de_intentos") == [(1,)] and contar("intento_de_origen") == 1


def test_un_inicio_correcto_completo_sigue_reiniciando_el_contador_y_la_reserva(esc, reloj):
    c = cliente_en()
    for _ in range(3):
        intentar(c, esc.identificador)
    assert intentar(c, esc.identificador, esc.contrasena).status_code == 201
    assert contar("control_de_intentos") == 0 and contar("intento_de_origen") == 3


def test_sin_pertenencia_vigente_el_inicio_se_rechaza_con_su_evento(reloj):
    with get_owner_engine().begin() as c:
        p = crear_persona(c)
        crear_pertenencia(c, p, crear_equipo(c, crear_organizacion(c)), desde=hoy() - timedelta(days=30), hasta=hoy() - timedelta(days=1))
        crear_identidad(c, p, "sin.pertenencia", "contraseña-de-prueba-123")
    r = intentar(cliente_en(), "sin.pertenencia", "contraseña-de-prueba-123")
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERTENENCIA_VIGENTE" and contar("sesion") == 0
    (ev,) = eventos("inicio_fallido")
    assert ev.persona_id == p and ev.detalle == {"motivo": "sin_pertenencia_vigente"}


def test_ninguna_tabla_de_control_ni_la_salida_contiene_secretos(esc, reloj, caplog):
    c = cliente_en()
    with caplog.at_level(logging.DEBUG):
        fallar_cinco(c, esc.identificador)
        intentar(c, esc.identificador)
        reloj.avanzar(seconds=30)
        r = intentar(c, esc.identificador, esc.contrasena)
        csrf, cookie = r.json()["csrf_token"], r.cookies.get(NOMBRE_COOKIE)
        c.post(f"{API}/sesion/cierre", headers=cabeceras(csrf))
    secretos = [esc.identificador, esc.contrasena, MALA, csrf, cookie, IP_A, "argon2"]
    with get_owner_engine().connect() as con:
        for tabla in ("control_de_intentos", "intento_de_origen", "evento_autenticacion", "control_de_intentos_operador"):
            for fila in con.execute(text(f"select t::text from {tabla} t")).all():
                for s in secretos:
                    assert s not in fila[0], (tabla, s)
    for s in secretos[:5]:
        assert s not in caplog.text


# ===================================================== fallo cerrado y cero transacciones abiertas durante Argon2 ============

def test_sin_el_secreto_la_aplicacion_no_arranca(monkeypatch):
    monkeypatch.setattr(get_settings(), "auth_pepper", None)
    with pytest.raises(control.ProteccionNoConfigurada):
        crear_app()


def test_si_la_base_de_control_falla_el_inicio_de_sesion_no_se_concede(esc, reloj, monkeypatch):
    def falla(*a, **k):
        raise RuntimeError("base caída")
    monkeypatch.setattr(control, "reservar", falla)
    r = intentar(cliente_en(), esc.identificador, esc.contrasena)
    assert r.status_code == 500 and contar("sesion") == 0


def test_mientras_se_calcula_argon2_no_hay_transaccion_ni_bloqueo_abiertos(esc, reloj, monkeypatch):
    from app.modulos.acceso import router
    original, capturas = router.verificar, []
    rol = get_settings().app_db_role

    def observando(hash_guardado, contrasena):
        # OJO: ``pg_stat_activity.state`` está oculto a un rol sin privilegios (siempre nulo): se usa ``pg_locks``, visible para todos. Un
        # bloqueo ``virtualxid`` concedido identifica una transacción abierta de esa sesión.
        with get_owner_engine().connect() as c:
            en_transaccion = c.execute(text("select count(*) from pg_locks l join pg_stat_activity a on a.pid = l.pid "
                                            "where a.usename = :r and l.locktype = 'virtualxid' and l.granted"), {"r": rol}).scalar_one()
            bloqueos = c.execute(text("select count(*) from pg_locks l join pg_stat_activity a on a.pid = l.pid "
                                      "where a.usename = :r and l.locktype = 'advisory' and l.granted"), {"r": rol}).scalar_one()
        capturas.append((en_transaccion, bloqueos))
        return original(hash_guardado, contrasena)
    monkeypatch.setattr(router, "verificar", observando)
    assert intentar(cliente_en(), esc.identificador, MALA).status_code == 401
    assert intentar(cliente_en(), esc.identificador, esc.contrasena).status_code == 201
    assert capturas == [(0, 0), (0, 0)]
    # La comprobación no es vacua: con una transacción abierta de la aplicación SÍ se ve.
    with get_engine().connect() as abierta:
        abierta.execute(text("select 1"))
        with get_owner_engine().connect() as c:
            assert c.execute(text("select count(*) from pg_locks l join pg_stat_activity a on a.pid = l.pid "
                                  "where a.usename = :r and l.locktype = 'virtualxid' and l.granted"), {"r": rol}).scalar_one() == 1
