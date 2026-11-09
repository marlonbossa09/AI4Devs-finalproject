"""T6 — M2-02: guardar el resumen libre de mi bitácora (PostgreSQL real, por HTTP).

Criterios: CA-34, CA-36, CA-62, CA-65, CA-105, CA-107, CA-281, CA-284, CA-293 y las reglas D-01, D-02,
D-03 y D-04, RN-18, RN-45, RN-49, RN-108 e IR-35. El contrato M2-02 no exige ``Idempotency-Key``: es un
reemplazo, naturalmente idempotente. Las pruebas destructivas corren solo sobre ``smartwork_test``.
"""

import threading
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db import get_owner_engine
from app.modulos.bitacoras import servicio
from app.seguridad.sesiones import NOMBRE_COOKIE
from tests.fabricas import (
    crear_equipo, crear_identidad, crear_persona, crear_pertenencia, escenario_basico, hoy,
)
from tests.utiles_http import API, cabeceras, iniciar_sesion, nuevo_cliente, sesion_iniciada
from tests.utiles_m2 import contar, filas, iso, planificar_actividad


def guardar(cliente, csrf, fecha=None, resumen="Hoy avancé con el informe", **extra):
    """M2-02. ``resumen=None`` omite el campo."""
    cuerpo = {} if resumen is None else {"resumen": resumen}
    return cliente.put(f"{API}/mi/bitacoras/{iso(0) if fecha is None else fecha}/resumen",
                       json={**cuerpo, **extra}, headers=cabeceras(csrf))


def consultar(cliente, fecha):
    return cliente.get(f"{API}/mi/bitacoras/{fecha}")


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c, desde=hoy() - timedelta(days=400))


@pytest.fixture()
def sesion(esc):
    return sesion_iniciada(esc)


def auditoria():
    return filas("select * from auditoria order by momento, id")


def marcar_reabierta(esc, fecha):
    """La reapertura (M3-02) es T8: se prepara dejando su entrada de auditoría, que es lo que ella deja."""
    with get_owner_engine().begin() as c:
        b = c.execute(text("select id from bitacora where persona_id = :p and fecha_laboral = :f"),
                      {"p": esc.persona, "f": fecha}).scalar_one()
        c.execute(text("insert into auditoria (tipo_autor, autor_persona_id, operacion, tipo_objeto, objeto_id, "
                       "propietaria_registro_id, fecha_laboral_registro, motivo, valor_anterior, valor_nuevo) "
                       "values ('persona', :p, 'reapertura', 'bitacora', :b, :p, :f, 'corregir', "
                       "cast('{\"estado\": \"cerrada\"}' as jsonb), cast('{\"estado\": \"abierta\"}' as jsonb))"),
                  {"p": esc.persona, "b": b, "f": fecha})


# ============================== guardar y actualizar ======================================================

def test_guarda_el_resumen_de_una_bitacora_existente_y_la_consulta_lo_devuelve(sesion):
    cliente, csrf = sesion
    assert cliente.post(f"{API}/mi/bitacoras", json={"fecha_laboral": iso(0)}, headers=cabeceras(csrf)).status_code == 201
    r = guardar(cliente, csrf, iso(0), "Preparé el informe y revisé las cifras")
    assert r.status_code == 200
    cuerpo = r.json()
    assert set(cuerpo) == {"bitacora", "bitacora_creada"} and cuerpo["bitacora_creada"] is False
    assert cuerpo["bitacora"]["resumen"] == "Preparé el informe y revisé las cifras"           # CA-34
    assert cuerpo["bitacora"]["estado"] == "abierta" and cuerpo["bitacora"]["fecha_laboral"] == iso(0)
    assert consultar(cliente, iso(0)).json()["bitacora"]["resumen"] == "Preparé el informe y revisé las cifras"
    assert filas("select resumen from bitacora")[0].resumen == "Preparé el informe y revisé las cifras"   # persistido


def test_actualizar_reemplaza_el_resumen_anterior(sesion):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(0), "Primera versión")
    r = guardar(cliente, csrf, iso(0), "Segunda versión")
    assert r.status_code == 200 and r.json()["bitacora"]["resumen"] == "Segunda versión"
    assert filas("select resumen from bitacora")[0].resumen == "Segunda versión" and contar("bitacora") == 1


def test_repetir_el_mismo_guardado_deja_lo_mismo_sin_clave_de_idempotencia(sesion):
    cliente, csrf = sesion
    primera = guardar(cliente, csrf, iso(0), "Igual")
    segunda = guardar(cliente, csrf, iso(0), "Igual")
    assert primera.status_code == segunda.status_code == 200                                 # no exige Idempotency-Key
    assert segunda.json()["bitacora"]["resumen"] == "Igual" and segunda.json()["bitacora_creada"] is False
    assert contar("bitacora") == 1 and contar("clave_idempotencia") == 0                     # no usa claves


def test_el_resumen_no_toca_las_actividades_ni_sus_avances(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    antes = (contar("actividad"), contar("avance"), contar("planificacion"), filas("select estado_actual from actividad")[0].estado_actual)
    guardar(cliente, csrf, iso(0), "Resumen de la jornada")
    assert antes == (contar("actividad"), contar("avance"), contar("planificacion"), filas("select estado_actual from actividad")[0].estado_actual)
    assert [x["id"] for x in consultar(cliente, iso(0)).json()["actividades"]] == [a]


# ============================== apertura implícita (D-01) ================================================

@pytest.mark.parametrize("dias", [0, -1, -300, 3])
def test_si_la_bitacora_no_existe_se_crea_en_la_misma_transaccion(sesion, dias):
    cliente, csrf = sesion
    r = guardar(cliente, csrf, iso(dias), "Contenido de la jornada")
    assert r.status_code == 200 and r.json()["bitacora_creada"] is True                       # CA-281
    assert r.json()["bitacora"]["fecha_laboral"] == iso(dias) and r.json()["bitacora"]["resumen"] == "Contenido de la jornada"
    assert contar("bitacora") == 1
    assert guardar(cliente, csrf, iso(dias), "Otro").json()["bitacora_creada"] is False
    assert contar("bitacora") == 1


def test_la_fecha_debe_estar_cubierta_por_una_pertenencia(sesion):
    cliente, csrf = sesion
    r = guardar(cliente, csrf, iso(-401), "No debería guardarse")
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_NO_CUBIERTA"
    assert (contar("bitacora"), contar("auditoria")) == (0, 0)


@pytest.mark.parametrize("fecha", ["hoy", "2026-13-45", "01-01-2026", "2026-1-1"])
def test_una_fecha_con_formato_incorrecto_es_una_solicitud_invalida(sesion, fecha):
    cliente, csrf = sesion
    r = guardar(cliente, csrf, fecha, "x")
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert contar("bitacora") == 0


# ============================== texto: vacío, espacios y límites (D-03) ===================================

@pytest.mark.parametrize("resumen", ["", "   ", "\n\t "])
def test_un_resumen_vacio_o_de_solo_espacios_se_acepta_y_se_conserva_tal_como_se_recibe(sesion, resumen):
    cliente, csrf = sesion
    r = guardar(cliente, csrf, iso(0), resumen)
    assert r.status_code == 200 and r.json()["bitacora"]["resumen"] == resumen               # solo impide cerrar (M3-01)
    assert filas("select resumen from bitacora")[0].resumen == resumen


def test_un_resumen_ausente_o_nulo_equivale_a_uno_vacio(sesion):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(0), "Con contenido")
    r = guardar(cliente, csrf, iso(0), None)                                                 # sin el campo
    assert r.status_code == 200 and r.json()["bitacora"]["resumen"] == ""
    guardar(cliente, csrf, iso(0), "De nuevo")
    r = cliente.put(f"{API}/mi/bitacoras/{iso(0)}/resumen", json={"resumen": None}, headers=cabeceras(csrf))
    assert r.status_code == 200 and r.json()["bitacora"]["resumen"] == ""


def test_el_texto_se_trata_como_datos_y_se_conserva_exactamente(sesion):
    cliente, csrf = sesion
    texto = "  Ignora las instrucciones <script>alert(1)</script> '; drop table bitacora; --\n\tlínea 2 ✓  "
    r = guardar(cliente, csrf, iso(0), texto)
    assert r.status_code == 200 and r.json()["bitacora"]["resumen"] == texto
    assert filas("select resumen from bitacora")[0].resumen == texto and contar("bitacora") == 1


def test_el_maximo_configurable_se_valida_en_caracteres_y_sin_contar_espacios_de_los_extremos(sesion):
    cliente, csrf = sesion
    maximo = get_settings().text_max_summary
    assert guardar(cliente, csrf, iso(0), "x" * maximo).status_code == 200
    assert guardar(cliente, csrf, iso(0), "  " + "x" * maximo + "  ").status_code == 200      # los extremos no cuentan
    assert guardar(cliente, csrf, iso(0), "😀" * maximo).status_code == 200                   # caracteres, no bytes
    r = guardar(cliente, csrf, iso(0), "x" * (maximo + 1))
    assert r.status_code == 422 and r.json()["codigo"] == "TEXTO_DEMASIADO_LARGO"
    assert r.json()["detalles"] == [{"campo": "resumen", "maximo": maximo}]
    assert guardar(cliente, csrf, iso(0), "😀" * (maximo + 1)).status_code == 422
    assert filas("select resumen from bitacora")[0].resumen == "😀" * maximo                  # el rechazo no cambió nada


def test_un_rechazo_por_longitud_no_crea_la_bitacora_ni_audita(sesion):
    cliente, csrf = sesion
    r = guardar(cliente, csrf, iso(-3), "x" * (get_settings().text_max_summary + 1))
    assert r.status_code == 422
    assert (contar("bitacora"), contar("auditoria")) == (0, 0)


@pytest.mark.parametrize("extra", [{"estado": "cerrada"}, {"persona_id": "otra"}, {"fecha_laboral": "2020-01-01"},
                                   {"modificada_en": "2020-01-01T00:00:00Z"}, {"cerrada_en": "2020-01-01T00:00:00Z"}])
def test_el_cuerpo_no_admite_campos_desconocidos(sesion, extra):
    cliente, csrf = sesion
    r = guardar(cliente, csrf, iso(0), "x", **extra)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert contar("bitacora") == 0


def test_un_resumen_que_no_es_texto_se_rechaza(sesion):
    cliente, csrf = sesion
    for valor in (123, True, ["a"], {"a": 1}):
        r = cliente.put(f"{API}/mi/bitacoras/{iso(0)}/resumen", json={"resumen": valor}, headers=cabeceras(csrf))
        assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA", valor


# ============================== modificada_en (RN-18, CA-62, CA-65) ======================================

def test_modificada_en_se_renueva_en_cada_guardado_y_las_otras_dos_fechas_no_cambian(sesion):
    cliente, csrf = sesion
    primera = guardar(cliente, csrf, iso(0), "Uno").json()["bitacora"]
    segunda = guardar(cliente, csrf, iso(0), "Dos").json()["bitacora"]
    igual = guardar(cliente, csrf, iso(0), "Dos").json()["bitacora"]                         # mismo texto: también se renueva
    vacia = guardar(cliente, csrf, iso(0), "").json()["bitacora"]                            # vacío: también
    momentos = [b["modificada_en"] for b in (primera, segunda, igual, vacia)]
    assert momentos == sorted(momentos) and len(set(momentos)) == 4                          # RN-18: siempre, y hacia delante
    assert {b["creada_en"] for b in (primera, segunda, igual, vacia)} == {primera["creada_en"]}
    assert {b["fecha_laboral"] for b in (primera, segunda)} == {iso(0)}                      # CA-62: tres fechas por separado


def test_la_consulta_muestra_las_tres_fechas_tras_una_correccion_en_una_jornada_pasada(sesion):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(-5), "Original")
    guardar(cliente, csrf, iso(-5), "Corregido")
    b = consultar(cliente, iso(-5)).json()["bitacora"]
    assert b["fecha_laboral"] == iso(-5) and b["clase_jornada"] == "pasada"
    assert b["creada_en"] < b["modificada_en"] and b["creada_en"][:10] != b["fecha_laboral"]   # CA-65
    assert len(auditoria()) == 2                                                             # y el cambio consta en la auditoría


# ============================== jornada cerrada (RN-108, D-04) ===========================================

def _cerrar_por_sql():
    """El cierre manual es T8: se prepara por SQL."""
    with get_owner_engine().begin() as c:
        c.execute(text("update bitacora set estado = 'cerrada', cerrada_en = now()"))


@pytest.mark.parametrize("dias", [0, -4])
def test_una_jornada_cerrada_no_admite_cambios_hasta_reabrirla(sesion, dias):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(dias), "Antes de cerrar")
    _cerrar_por_sql()
    antes = filas("select resumen, modificada_en, estado from bitacora")[0]
    n_audit = contar("auditoria")
    r = guardar(cliente, csrf, iso(dias), "Intento de cambio")
    assert r.status_code == 409 and r.json()["codigo"] == "BITACORA_CERRADA"                 # CA-284
    for texto in ("", "Antes de cerrar"):                                                    # ni vaciar ni repetir
        assert guardar(cliente, csrf, iso(dias), texto).status_code == 409
    despues = filas("select resumen, modificada_en, estado from bitacora")[0]
    assert tuple(despues) == tuple(antes) and contar("auditoria") == n_audit                 # nada cambió


def test_una_jornada_cerrada_no_impide_guardar_el_resumen_de_otra_fecha(sesion):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(-1), "Ayer")
    _cerrar_por_sql()
    assert guardar(cliente, csrf, iso(0), "Hoy").status_code == 200


# ============================== autorización y acceso =====================================================

def test_sin_sesion_no_se_guarda_nada(sesion):
    r = nuevo_cliente().put(f"{API}/mi/bitacoras/{iso(0)}/resumen", json={"resumen": "x"})
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"
    assert contar("bitacora") == 0


def test_sin_token_csrf_o_desde_otro_origen_se_rechaza(sesion):
    cliente, csrf = sesion
    sin_token = cliente.put(f"{API}/mi/bitacoras/{iso(0)}/resumen", json={"resumen": "x"},
                            headers={"Origin": "https://testserver"})
    otro_origen = cliente.put(f"{API}/mi/bitacoras/{iso(0)}/resumen", json={"resumen": "x"},
                              headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf})
    assert sin_token.status_code == 400 and otro_origen.status_code == 400
    assert contar("bitacora") == 0


def test_con_el_acceso_desactivado_no_se_guarda_nada(sesion, esc):
    cliente, csrf = sesion
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": esc.persona})
    r = guardar(cliente, csrf, iso(0), "x")
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"
    assert contar("bitacora") == 0


def test_sin_pertenencia_vigente_no_se_guarda_nada(sesion, esc):
    cliente, csrf = sesion
    with get_owner_engine().begin() as c:
        c.execute(text("update pertenencia set hasta_exclusivo = :h where persona_id = :p"),
                  {"h": hoy() - timedelta(days=1), "p": esc.persona})
    r = guardar(cliente, csrf, iso(-3), "x")
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERTENENCIA_VIGENTE"
    assert contar("bitacora") == 0


def test_solo_se_guarda_en_la_bitacora_propia_y_nunca_en_la_de_otra_persona(sesion, esc):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(-2), "Mi resumen")
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        otra = crear_persona(c, "Otra persona")
        crear_pertenencia(c, otra, crear_equipo(c, org, "Otro equipo"), desde=hoy() - timedelta(days=50))
        crear_identidad(c, otra, "otra.persona", "contraseña-de-prueba-123")
    ajeno = nuevo_cliente()
    r = iniciar_sesion(ajeno, "otra.persona", "contraseña-de-prueba-123")
    resp = guardar(ajeno, r.json()["csrf_token"], iso(-2), "Resumen de la otra persona")
    assert resp.status_code == 200 and resp.json()["bitacora"]["persona_id"] != str(esc.persona)   # CA-36, CA-107
    assert consultar(cliente, iso(-2)).json()["bitacora"]["resumen"] == "Mi resumen"           # la mía no cambió
    assert contar("bitacora") == 2


# ============================== auditoría (RN-45, RN-49, IR-35) =========================================

def test_en_la_jornada_actual_o_futura_no_se_audita(sesion):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(0), "Uno")
    guardar(cliente, csrf, iso(0), "Dos")
    guardar(cliente, csrf, iso(4), "Futura")
    assert contar("auditoria") == 0


def test_una_modificacion_en_una_jornada_pasada_deja_una_unica_entrada_con_el_resumen_anterior_y_el_nuevo(sesion, esc):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(-4), "Versión original")                                      # primera escritura (crea la bitácora)
    assert len(auditoria()) == 1
    r = guardar(cliente, csrf, iso(-4), "Versión corregida")
    assert r.status_code == 200
    entradas = auditoria()
    assert len(entradas) == 2                                                                # una entrada por operación
    e = entradas[-1]
    assert (e.tipo_autor, e.operacion, e.tipo_objeto) == ("persona", "modificacion_jornada_pasada", "bitacora")
    assert e.autor_persona_id == esc.persona and e.propietaria_registro_id == esc.persona   # CA-105
    assert e.fecha_laboral_registro.isoformat() == iso(-4) and str(e.objeto_id) == r.json()["bitacora"]["id"]
    assert e.valor_anterior["resumen"] == "Versión original" and e.valor_nuevo["resumen"] == "Versión corregida"
    assert e.valor_nuevo["bitacora_creada"] is False


def test_la_primera_escritura_efectiva_en_una_jornada_pasada_se_audita_con_la_creacion_implicita(sesion, esc):
    cliente, csrf = sesion
    r = guardar(cliente, csrf, iso(-6), "Primer contenido de una jornada pasada")
    entradas = auditoria()
    assert len(entradas) == 1                                                                # CA-293: una sola entrada
    e = entradas[0]
    assert e.operacion == "modificacion_jornada_pasada" and e.tipo_objeto == "bitacora"
    assert e.valor_anterior == {"resumen": "", "bitacora_existia": False}
    assert e.valor_nuevo["bitacora_creada"] is True and e.valor_nuevo["resumen"] == "Primer contenido de una jornada pasada"
    assert str(e.objeto_id) == r.json()["bitacora"]["id"]                                    # la creación va en la misma entrada


def test_guardar_un_resumen_vacio_donde_no_habia_contenido_no_es_una_escritura_efectiva(sesion):
    cliente, csrf = sesion
    r = guardar(cliente, csrf, iso(-6), "")                                                  # crea la bitácora vacía
    assert r.status_code == 200 and r.json()["bitacora_creada"] is True
    assert guardar(cliente, csrf, iso(-6), "   ").status_code == 200                         # vacío sobre vacío
    assert contar("bitacora") == 1 and contar("auditoria") == 0                              # D-02


def test_vaciar_un_resumen_que_tenia_contenido_si_se_audita_porque_cambia_el_registro(sesion):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(-6), "Contenido que luego se borra")
    guardar(cliente, csrf, iso(-6), "")
    e = auditoria()[-1]
    assert e.valor_anterior["resumen"] == "Contenido que luego se borra" and e.valor_nuevo["resumen"] == ""
    assert len(auditoria()) == 2                                                             # nunca se borra sin dejar rastro


def test_una_bitacora_reabierta_audita_las_correcciones_aunque_sea_de_hoy(sesion, esc):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(0), "Antes del cierre")
    marcar_reabierta(esc, iso(0))                                                            # abierta de nuevo, con su reapertura
    n = contar("auditoria")
    r = guardar(cliente, csrf, iso(0), "Corregido tras reabrir")
    assert r.status_code == 200 and contar("auditoria") == n + 1
    e = auditoria()[-1]
    assert (e.operacion, e.tipo_objeto) == ("correccion", "bitacora")                        # RN-49
    assert e.valor_anterior["resumen"] == "Antes del cierre" and e.valor_nuevo["resumen"] == "Corregido tras reabrir"
    assert e.fecha_laboral_registro.isoformat() == iso(0)


def test_una_peticion_rechazada_no_deja_auditoria_ni_cambios(sesion):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(-2), "Estable")
    n, antes = contar("auditoria"), filas("select resumen, modificada_en from bitacora")[0]
    assert guardar(cliente, csrf, iso(-2), "x" * 9000).status_code == 422
    _cerrar_por_sql()
    assert guardar(cliente, csrf, iso(-2), "Nuevo").status_code == 409
    assert contar("auditoria") == n and tuple(filas("select resumen, modificada_en from bitacora")[0]) == tuple(antes)


# ============================== atomicidad y concurrencia ================================================

def test_si_falla_la_auditoria_no_queda_ni_el_cambio_ni_la_bitacora_creada(sesion, monkeypatch):
    cliente, csrf = sesion

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado al auditar")

    monkeypatch.setattr(servicio, "registrar_operacion_de_persona", falla)
    r = guardar(cliente, csrf, iso(-3), "Contenido")
    assert r.status_code == 500 and r.json()["codigo"] == "ERROR_INTERNO" and "fallo simulado" not in r.text
    assert (contar("bitacora"), contar("auditoria")) == (0, 0)                               # la creación implícita se deshizo


def test_si_falla_la_auditoria_el_resumen_existente_y_su_fecha_de_modificacion_no_cambian(sesion, monkeypatch):
    cliente, csrf = sesion
    guardar(cliente, csrf, iso(-3), "Original")
    antes = tuple(filas("select resumen, modificada_en from bitacora")[0])

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado al auditar")

    monkeypatch.setattr(servicio, "registrar_operacion_de_persona", falla)
    assert guardar(cliente, csrf, iso(-3), "Corrección que no debe quedar").status_code == 500
    assert tuple(filas("select resumen, modificada_en from bitacora")[0]) == antes


def _clientes_concurrentes(esc, n):
    base, _ = sesion_iniciada(esc)
    secreto = base.cookies.get(NOMBRE_COOKIE)
    csrf = base.get(f"{API}/sesion").json()["csrf_token"]
    return [nuevo_cliente({NOMBRE_COOKIE: secreto}) for _ in range(n)], csrf


@pytest.mark.parametrize("dias", [-3, 0])
def test_guardados_simultaneos_en_una_fecha_nueva_dejan_una_bitacora_y_un_resultado_coherente(esc, dias):
    n = 8
    clientes, csrf = _clientes_concurrentes(esc, n)
    resultados, barrera = [], threading.Barrier(n)

    def intentar(i):
        barrera.wait()
        resultados.append(guardar(clientes[i], csrf, iso(dias), f"Texto {i}"))

    hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(n)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert [r.status_code for r in resultados] == [200] * n, [r.text for r in resultados if r.status_code != 200]
    assert contar("bitacora") == 1                                                           # IR-01
    assert sum(r.json()["bitacora_creada"] for r in resultados) == 1
    final = filas("select resumen from bitacora")[0].resumen
    assert final in {f"Texto {i}" for i in range(n)}                                         # un resultado completo, no mezclado
    if dias < 0:   # jornada pasada: una entrada por escritura, encadenadas sin pérdidas
        entradas = auditoria()
        assert len(entradas) == n
        anteriores = sorted(e.valor_anterior["resumen"] for e in entradas)
        nuevos = sorted(e.valor_nuevo["resumen"] for e in entradas)
        # Serializadas: cada texto reemplaza exactamente a otro, empezando por el vacío y acabando en el final
        assert sorted(anteriores + [final]) == sorted(nuevos + [""])
        assert sum(e.valor_nuevo["bitacora_creada"] for e in entradas) == 1
    else:
        assert contar("auditoria") == 0


def test_guardados_simultaneos_sobre_una_bitacora_existente_no_pierden_el_encadenamiento(esc):
    cliente, csrf = sesion_iniciada(esc)
    guardar(cliente, csrf, iso(-2), "Inicio")
    n = 6
    clientes, csrf = _clientes_concurrentes(esc, n)
    barrera, resultados = threading.Barrier(n), []

    def intentar(i):
        barrera.wait()
        resultados.append(guardar(clientes[i], csrf, iso(-2), f"Versión {i}"))

    hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(n)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert [r.status_code for r in resultados] == [200] * n
    entradas = auditoria()[1:]                                                               # sin la primera, de la creación
    final = filas("select resumen from bitacora")[0].resumen
    anteriores = sorted(e.valor_anterior["resumen"] for e in entradas)
    nuevos = sorted(e.valor_nuevo["resumen"] for e in entradas)
    assert sorted(anteriores + [final]) == sorted(nuevos + ["Inicio"])                        # el anterior auditado es el realmente reemplazado
    momentos = sorted(r.json()["bitacora"]["modificada_en"] for r in resultados)
    assert len(set(momentos)) == n                                                           # cada guardado, su propio momento


def test_un_guardado_espera_al_que_tiene_bloqueada_la_bitacora_y_audita_el_valor_realmente_reemplazado(esc):
    """Prueba determinista de la serialización: otra transacción tiene la bitácora bloqueada, el
    guardado debe ESPERAR y, al liberarse, auditar como anterior el valor que esa otra dejó."""
    cliente, csrf = sesion_iniciada(esc)
    guardar(cliente, csrf, iso(-2), "Original")
    clientes, csrf = _clientes_concurrentes(esc, 1)
    resultado = []

    def registrar():
        resultado.append(guardar(clientes[0], csrf, iso(-2), "Mi versión"))

    with get_owner_engine().begin() as c:
        c.execute(text("select 1 from bitacora where fecha_laboral = :f for update"), {"f": hoy() - timedelta(days=2)})
        hilo = threading.Thread(target=registrar)
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "el guardado debía esperar al bloqueo de la bitácora"
        momento_de_la_otra = c.execute(
            text("update bitacora set resumen = 'Cambio de otra transacción', modificada_en = clock_timestamp() "
                 "where fecha_laboral = :f returning modificada_en"),
            {"f": hoy() - timedelta(days=2)},
        ).scalar_one()
    hilo.join(timeout=10)
    assert resultado and resultado[0].status_code == 200
    e = auditoria()[-1]
    assert e.valor_anterior["resumen"] == "Cambio de otra transacción" and e.valor_nuevo["resumen"] == "Mi versión"
    # La petición empezó ANTES que el cambio de la otra transacción pero se aplicó DESPUÉS: su fecha de
    # modificación debe ser posterior (reloj real, no el inicio de su transacción).
    momento_mio = datetime.fromisoformat(resultado[0].json()["bitacora"]["modificada_en"].replace("Z", "+00:00"))
    assert momento_mio > momento_de_la_otra
