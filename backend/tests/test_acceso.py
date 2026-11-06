"""Bloque 4: inicio, consulta y cierre de sesión (M1-01a/b/c; HU-1.1; ADR-002).

Cubre CA-01, CA-03, CA-04, CA-05, CA-29, CA-255 y CA-259 con cookies, CSRF, origen y sesiones
reales sobre PostgreSQL.
"""

import hashlib
import logging
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.db import get_owner_engine
from app.seguridad.contrasenas import calcular_hash, necesita_recalculo, verificar
from app.seguridad.identificadores import normalizar_identificador
from app.seguridad.sesiones import NOMBRE_COOKIE, generar_secreto, hash_secreto, token_csrf
from tests.fabricas import (
    crear_equipo, crear_identidad, crear_organizacion, crear_persona, crear_pertenencia, escenario_basico, hoy,
)
from tests.utiles_http import API, ORIGEN, cabeceras, iniciar_sesion, nuevo_cliente, sesion_iniciada


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c)


# --- M1-01a: iniciar sesión ---------------------------------------------------------------------

def test_el_inicio_de_sesion_devuelve_persona_rol_y_csrf_y_la_cookie_solo_en_la_cabecera(esc):
    cliente = nuevo_cliente()
    r = iniciar_sesion(cliente, esc.identificador, esc.contrasena)
    assert r.status_code == 201
    cuerpo = r.json()
    assert set(cuerpo) == {"persona", "rol_vigente", "csrf_token"}
    assert cuerpo["rol_vigente"] == "colaborador" and cuerpo["persona"]["nombre"] == "Ana de prueba"
    cookie = r.cookies.get(NOMBRE_COOKIE)
    assert cookie and cookie not in r.text  # el secreto nunca va en el cuerpo
    assert esc.contrasena not in r.text
    assert r.headers["cache-control"] == "no-store"


def test_la_cookie_tiene_los_atributos_de_seguridad_de_adr_002(esc):
    r = iniciar_sesion(nuevo_cliente(), esc.identificador, esc.contrasena)
    cabecera = next(v for v in r.headers.get_list("set-cookie") if v.startswith(f"{NOMBRE_COOKIE}="))
    minusculas = cabecera.lower()
    assert "secure" in minusculas and "httponly" in minusculas and "samesite=strict" in minusculas
    assert "path=/" in minusculas
    assert "domain" not in minusculas  # requisito del prefijo __Host-


def test_en_la_base_de_datos_solo_se_guarda_el_hash_del_secreto(esc):
    r = iniciar_sesion(nuevo_cliente(), esc.identificador, esc.contrasena)
    secreto = r.cookies.get(NOMBRE_COOKIE)
    with get_owner_engine().connect() as c:
        guardado = c.execute(text("select secreto_hash from sesion")).scalar_one()
        assert guardado == hashlib.sha256(secreto.encode()).hexdigest() and guardado != secreto
        assert c.execute(text("select count(*) from sesion s where s::text like :s"),
                         {"s": f"%{secreto}%"}).scalar_one() == 0


def test_cada_inicio_de_sesion_genera_un_secreto_nuevo(esc):
    c1, c2 = nuevo_cliente(), nuevo_cliente()
    s1 = iniciar_sesion(c1, esc.identificador, esc.contrasena).cookies.get(NOMBRE_COOKIE)
    s2 = iniciar_sesion(c2, esc.identificador, esc.contrasena).cookies.get(NOMBRE_COOKIE)
    assert s1 != s2
    with get_owner_engine().connect() as c:
        assert c.execute(text("select count(distinct secreto_hash) from sesion")).scalar_one() == 2


def test_identificador_inexistente_y_contrasena_incorrecta_producen_la_misma_respuesta(esc):
    with get_owner_engine().begin() as c:
        crear_identidad(c, crear_persona(c, "Sin primer acceso"), "pendiente", None)
    r_inexistente = iniciar_sesion(nuevo_cliente(), "nadie", "cualquier-contraseña-123")
    r_incorrecta = iniciar_sesion(nuevo_cliente(), esc.identificador, "contraseña-incorrecta-123")
    r_sin_primer_acceso = iniciar_sesion(nuevo_cliente(), "pendiente", "cualquier-contraseña-123")
    for r in (r_inexistente, r_incorrecta, r_sin_primer_acceso):
        assert r.status_code == 401
        assert r.json() == r_inexistente.json()
        assert r.json()["codigo"] == "CREDENCIALES_INVALIDAS"
        assert NOMBRE_COOKIE not in r.headers.get("set-cookie", "")


def test_el_identificador_no_distingue_mayusculas(esc):
    assert iniciar_sesion(nuevo_cliente(), esc.identificador.upper(), esc.contrasena).status_code == 201


def test_ninguna_respuesta_ni_registro_contiene_la_contrasena(esc, caplog):
    secreta = "contraseña-secreta-única-98765"
    with caplog.at_level(logging.DEBUG):
        r1 = iniciar_sesion(nuevo_cliente(), esc.identificador, secreta)
        r2 = iniciar_sesion(nuevo_cliente(), esc.identificador, esc.contrasena)
    assert secreta not in r1.text and esc.contrasena not in r2.text
    assert secreta not in caplog.text and esc.contrasena not in caplog.text


def test_con_el_acceso_desactivado_no_se_crea_sesion(esc):
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() - interval '1 minute'"))
    r = iniciar_sesion(nuevo_cliente(), esc.identificador, esc.contrasena)
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"
    with get_owner_engine().connect() as c:
        assert c.execute(text("select count(*) from sesion")).scalar_one() == 0


@pytest.mark.parametrize("desde,hasta", [
    (-30, -1),   # la pertenencia ya terminó
    (5, None),   # todavía no empieza
])
def test_sin_pertenencia_vigente_no_se_crea_sesion(desde, hasta):
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c)
        p = crear_persona(c)
        crear_pertenencia(c, p, crear_equipo(c, org), desde=hoy() + timedelta(days=desde),
                          hasta=None if hasta is None else hoy() + timedelta(days=hasta))
        crear_identidad(c, p, "sin.pertenencia", "contraseña-de-prueba-123")
    r = iniciar_sesion(nuevo_cliente(), "sin.pertenencia", "contraseña-de-prueba-123")
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERTENENCIA_VIGENTE"
    with get_owner_engine().connect() as c:
        assert c.execute(text("select count(*) from sesion")).scalar_one() == 0


def test_campos_desconocidos_y_longitudes_excesivas_se_rechazan(esc):
    cliente = nuevo_cliente()
    r = cliente.post(f"{API}/sesion", headers={"Origin": ORIGEN},
                     json={"identificador_acceso": "a", "contrasena": "b", "rol": "supervisor"})
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    r = cliente.post(f"{API}/sesion", headers={"Origin": ORIGEN},
                     json={"identificador_acceso": "a", "contrasena": "x" * 5000})
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


@pytest.mark.parametrize("origen", ["https://evil.example", "null", None])
def test_el_inicio_de_sesion_desde_otro_origen_o_sin_origen_se_rechaza(esc, origen):
    r = iniciar_sesion(nuevo_cliente(), esc.identificador, esc.contrasena, origen=origen)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    with get_owner_engine().connect() as c:
        assert c.execute(text("select count(*) from sesion")).scalar_one() == 0


def test_el_origen_tambien_puede_venir_en_el_referer(esc):
    r = nuevo_cliente().post(f"{API}/sesion", headers={"Referer": f"{ORIGEN}/pantalla"},
                             json={"identificador_acceso": esc.identificador, "contrasena": esc.contrasena})
    assert r.status_code == 201


# --- M1-01c: consultar mi sesión -----------------------------------------------------------------

def test_sin_sesion_no_se_muestra_ningun_dato(esc):
    r = nuevo_cliente().get(f"{API}/sesion")
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"          # CA-01
    assert "Ana" not in r.text


def test_consultar_la_sesion_devuelve_identidad_rol_fecha_actual_y_csrf(esc):
    cliente, csrf = sesion_iniciada(esc)
    r = cliente.get(f"{API}/sesion")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["persona"]["nombre"] == "Ana de prueba" and cuerpo["rol_vigente"] == "colaborador"
    assert cuerpo["fecha_actual"] == hoy().isoformat()
    assert cuerpo["csrf_token"] == csrf
    assert r.headers["cache-control"] == "no-store"


def test_el_rol_vigente_distingue_colaborador_y_supervisor():
    with get_owner_engine().begin() as c:
        org = crear_organizacion(c)
        equipo = crear_equipo(c, org)
        s, k = crear_persona(c, "Sara"), crear_persona(c, "Kevin")
        crear_pertenencia(c, s, equipo, "supervisor")
        crear_pertenencia(c, k, equipo, "colaborador")
        crear_identidad(c, s, "sara", "contraseña-de-prueba-123")
        crear_identidad(c, k, "kevin", "contraseña-de-prueba-123")
    roles = {}
    for ident in ("sara", "kevin"):
        cliente = nuevo_cliente()
        iniciar_sesion(cliente, ident, "contraseña-de-prueba-123")
        roles[ident] = cliente.get(f"{API}/sesion").json()["rol_vigente"]
    assert roles == {"sara": "supervisor", "kevin": "colaborador"}                    # CA-03, CA-04


def test_tras_desactivar_el_acceso_la_siguiente_peticion_con_la_sesion_previa_se_rechaza(esc):
    cliente, _ = sesion_iniciada(esc)
    assert cliente.get(f"{API}/sesion").status_code == 200
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now()"))
    r = cliente.get(f"{API}/sesion")
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"       # CA-29, CA-255


def test_al_terminar_la_pertenencia_la_sesion_previa_deja_de_operar(esc):
    cliente, _ = sesion_iniciada(esc)
    with get_owner_engine().begin() as c:
        c.execute(text("update pertenencia set hasta_exclusivo = :h"), {"h": hoy()})
    r = cliente.get(f"{API}/sesion")
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERTENENCIA_VIGENTE"  # CA-259


@pytest.mark.parametrize("cambio", [
    "update sesion set revocada_en = now()",
    "update sesion set caduca_absoluta_en = now() - interval '1 second'",
    "update sesion set ultimo_uso_en = now() - interval '31 minutes'",
])
def test_una_sesion_revocada_caducada_o_inactiva_no_identifica(esc, cambio):
    cliente, _ = sesion_iniciada(esc)
    with get_owner_engine().begin() as c:
        c.execute(text(cambio))
    r = cliente.get(f"{API}/sesion")
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"


def test_el_ultimo_uso_se_actualiza_con_frecuencia_limitada(esc):
    cliente, _ = sesion_iniciada(esc)
    with get_owner_engine().begin() as c:
        c.execute(text("update sesion set ultimo_uso_en = now() - interval '10 seconds'"))
    cliente.get(f"{API}/sesion")
    with get_owner_engine().connect() as c:
        reciente = c.execute(text("select now() - ultimo_uso_en > interval '5 seconds' from sesion")).scalar_one()
    assert reciente  # dentro de la ventana de 60 s no se vuelve a escribir
    with get_owner_engine().begin() as c:
        c.execute(text("update sesion set ultimo_uso_en = now() - interval '5 minutes'"))
    cliente.get(f"{API}/sesion")
    with get_owner_engine().connect() as c:
        assert c.execute(text("select now() - ultimo_uso_en < interval '5 seconds' from sesion")).scalar_one()


# --- M1-01b: cerrar sesión -----------------------------------------------------------------------

def test_cerrar_la_sesion_la_revoca_en_el_servidor_aunque_se_conserve_la_cookie(esc):
    cliente, csrf = sesion_iniciada(esc)
    secreto = cliente.cookies.get(NOMBRE_COOKIE)
    r = cliente.post(f"{API}/sesion/cierre", headers=cabeceras(csrf))
    assert r.status_code == 204
    assert any("max-age=0" in v.lower() or "expires=" in v.lower() for v in r.headers.get_list("set-cookie"))
    con_cookie_vieja = nuevo_cliente({NOMBRE_COOKIE: secreto})
    assert con_cookie_vieja.get(f"{API}/sesion").status_code == 401                  # revocada en el servidor
    with get_owner_engine().connect() as c:
        assert c.execute(text("select revocada_en is not null from sesion")).scalar_one()


def test_cerrar_la_sesion_sin_sesion_no_esta_permitido(esc):
    r = nuevo_cliente().post(f"{API}/sesion/cierre", headers=cabeceras("x"))
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"


# --- CSRF y origen en operaciones que modifican --------------------------------------------------

@pytest.mark.parametrize("encabezados,motivo", [
    ({"Origin": ORIGEN}, "csrf_invalido"),                                       # sin token
    ({"Origin": ORIGEN, "X-CSRF-Token": "token-falso"}, "csrf_invalido"),
    ({"Origin": "https://evil.example", "X-CSRF-Token": "{csrf}"}, "origen_no_permitido"),
    ({"X-CSRF-Token": "{csrf}"}, "origen_no_permitido"),                          # sin origen ni referer
])
def test_una_peticion_que_modifica_sin_csrf_o_desde_otro_origen_se_rechaza_y_no_cambia_nada(esc, encabezados, motivo):
    cliente, csrf = sesion_iniciada(esc)
    encabezados = {k: v.replace("{csrf}", csrf) for k, v in encabezados.items()}
    r = cliente.post(f"{API}/sesion/cierre", headers=encabezados)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert r.json()["detalles"][0]["motivo"] == motivo
    assert cliente.get(f"{API}/sesion").status_code == 200  # la sesión sigue viva


def test_el_token_csrf_de_otra_sesion_no_sirve(esc):
    cliente, _ = sesion_iniciada(esc)
    _, csrf_otra = sesion_iniciada(esc)
    r = cliente.post(f"{API}/sesion/cierre", headers=cabeceras(csrf_otra))
    assert r.status_code == 400


# --- Utilidades de seguridad ---------------------------------------------------------------------

def test_las_contrasenas_se_guardan_con_argon2id_y_se_verifican():
    h = calcular_hash("una-contraseña-larga-de-prueba")
    assert h.startswith("$argon2id$") and "m=19456,t=2,p=1" in h
    assert verificar(h, "una-contraseña-larga-de-prueba") and not verificar(h, "otra")
    assert not verificar("no-es-un-hash", "x")
    assert not necesita_recalculo(h)


def test_el_token_csrf_deriva_del_secreto_sin_revelarlo():
    s = generar_secreto()
    assert len(s) >= 43 and token_csrf(s) == token_csrf(s) and token_csrf(s) != token_csrf(generar_secreto())
    assert s not in token_csrf(s) and hash_secreto(s) != s


def test_el_identificador_se_normaliza():
    assert normalizar_identificador("  ANA.Prueba ") == "ana.prueba"
