"""M1-T7 — intentos fallidos de la credencial de la persona operadora (CLI) y purga de los eventos técnicos de autenticación.

Decisiones del 2026-11-17: la MISMA curva de espera que las personas (cinco intentos libres; 30 s, 1, 2, 4, 8, 16, 32 min y 1 hora), un
contador SEPARADO del de las personas, sin deshabilitar nunca a la persona operadora, protección frente a credenciales incorrectas y a
identificadores inexistentes (misma respuesta), y sin credenciales en argumentos, salidas ni registros. Retención técnica de 30 días
con un procedimiento de purga seguro y comprobable (una orden de la CLI; no hay planificador). Las pruebas destructivas corren solo sobre
``smartwork_test``.
"""

import json
import os
import subprocess
import sys

import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine, get_owner_engine, get_provision_engine
from app.provision import operadores
from app.provision.cli import VARIABLE_CREDENCIAL, verificar_conexion_de_provision
from app.provision.errores import ErrorDeProvision
from app.seguridad import control_de_intentos as control
from tests.test_control_de_intentos import Reloj
from tests.test_provision_cli import CREDENCIAL, RAIZ, ejecutar, instalada, sin_secretos  # noqa: F401  (fixture ``instalada``)
from tests.utiles_m2 import contar, filas

MALA = "credencial-equivocada-123"


@pytest.fixture()
def reloj(monkeypatch):
    r = Reloj()
    monkeypatch.setattr(control, "_ahora", r)
    return r


def orden(instalada, credencial=CREDENCIAL, operador=None, nombre="Equipo X", **extra):
    return ejecutar(["crear-equipo", "--operador", operador or instalada["operador"], "--organizacion", str(instalada["org"]), "--nombre", nombre],
                    credencial=credencial, **extra)


def fallar(instalada, operador=None):
    codigo, salida, error = orden(instalada, MALA, operador)
    assert codigo == 2 and json.loads(error)["error"] == "OPERADOR_NO_AUTORIZADO" and salida == ""
    return error


def clave(instalada):
    return control.clave_de_operador(instalada["operador"])


# ===================================================== cinco intentos libres y esperas =====================================

def test_cinco_credenciales_incorrectas_no_esperan_y_la_sexta_orden_se_rechaza_por_espera_aunque_la_credencial_sea_buena(instalada, reloj):
    for _ in range(5):
        fallar(instalada)
    codigo, salida, error = orden(instalada, CREDENCIAL)
    r = json.loads(error)
    assert codigo == 4 and salida == "" and r["error"] == "DEMASIADOS_INTENTOS" and r["detalles"] == [{"espera_segundos": 30}]
    assert contar("equipo") == 0                                                       # la orden no se ejecutó
    sin_secretos(salida, error)


def test_la_espera_se_cuenta_atras_con_lo_que_falta(instalada, reloj):
    for _ in range(5):
        fallar(instalada)
    reloj.avanzar(seconds=12)
    assert json.loads(orden(instalada)[2])["detalles"] == [{"espera_segundos": 18}]


def test_pasada_la_espera_la_credencial_correcta_ejecuta_la_orden_y_reinicia_el_contador(instalada, reloj):
    for _ in range(5):
        fallar(instalada)
    reloj.avanzar(seconds=30)
    codigo, salida, error = orden(instalada)
    assert codigo == 0 and error == "" and json.loads(salida)["orden"] == "crear-equipo"
    assert contar("equipo") == 1 and contar("control_de_intentos_operador") == 0
    for _ in range(5):                                                                 # vuelven los cinco libres
        fallar(instalada, None)
    assert orden(instalada)[0] == 4


def test_la_progresion_completa_es_la_misma_curva_de_las_personas(instalada, reloj):
    for _ in range(5):
        fallar(instalada)
    vistas = []
    for _ in range(9):
        codigo, _, error = orden(instalada)
        assert codigo == 4
        espera = json.loads(error)["detalles"][0]["espera_segundos"]
        vistas.append(espera)
        reloj.avanzar(seconds=espera)
        fallar(instalada)
    assert vistas == [30, 60, 120, 240, 480, 960, 1920, 3600, 3600]


def test_el_contador_de_la_persona_operadora_se_olvida_a_las_24_horas(instalada, reloj):
    for _ in range(5):
        fallar(instalada)
    reloj.avanzar(hours=24, seconds=1)
    fallar(instalada)
    assert filas("select intentos from control_de_intentos_operador") == [(1,)]


def test_las_ordenes_rechazadas_por_espera_no_cambian_nada_ni_dejan_eventos(instalada, reloj):
    for _ in range(5):
        fallar(instalada)
    antes = (filas("select * from control_de_intentos_operador"), contar("evento_autenticacion"), contar("auditoria"))
    for _ in range(10):
        assert orden(instalada)[0] == 4
    assert (filas("select * from control_de_intentos_operador"), contar("evento_autenticacion"), contar("auditoria")) == antes


# ===================================================== nunca se deshabilita a la persona operadora ===========================

def test_nunca_se_deshabilita_a_la_persona_operadora_aunque_falle_cien_veces(instalada, reloj):
    for _ in range(100):
        codigo, _, error = orden(instalada, MALA)
        if codigo == 4:
            reloj.avanzar(seconds=json.loads(error)["detalles"][0]["espera_segundos"])
            codigo, _, error = orden(instalada, MALA)
        assert codigo == 2
    assert filas("select estado, revocado_en from operador") == [("activo", None)]
    reloj.avanzar(hours=2)
    assert orden(instalada)[0] == 0                                                    # y con la credencial buena vuelve a funcionar


def test_la_espera_maxima_es_de_una_hora_y_caduca_sola(instalada, reloj):
    for _ in range(40):
        codigo, _, error = orden(instalada, MALA)
        if codigo == 4:
            assert json.loads(error)["detalles"][0]["espera_segundos"] <= 3600
            reloj.avanzar(seconds=3600)
    reloj.avanzar(seconds=3600)
    assert orden(instalada)[0] == 0


# ===================================================== sin enumeración de personas operadoras ==============================

def test_un_identificador_desconocido_y_una_credencial_incorrecta_dan_exactamente_la_misma_respuesta(instalada, reloj):
    existente = [orden(instalada, MALA) for _ in range(5)] + [orden(instalada)]
    desconocido = [orden(instalada, MALA, operador="no.existe.nadie") for _ in range(5)] + [orden(instalada, operador="no.existe.nadie")]
    assert existente == desconocido
    assert {r[0] for r in existente[:5]} == {2} and existente[5][0] == 4


def test_una_persona_operadora_revocada_se_comporta_como_una_desconocida(instalada, reloj):
    with get_owner_engine().begin() as c:
        c.execute(text("update operador set estado = 'revocado', revocado_en = now()"))
    assert orden(instalada) == orden(instalada, operador="no.existe.nadie")
    assert filas("select intentos from control_de_intentos_operador order by intentos") == [(1,), (1,)]


def test_el_identificador_se_normaliza_igual_que_en_la_identificacion(instalada, reloj):
    for _ in range(5):
        orden(instalada, MALA, operador="  OPERADORA.CLI ")
    assert filas("select intentos from control_de_intentos_operador") == [(5,)]
    assert orden(instalada, operador="operadora.cli")[0] == 4


# ===================================================== contador separado y sin secretos ====================================

def test_el_contador_de_la_persona_operadora_no_es_el_de_las_personas(instalada, reloj):
    assert clave(instalada) != control.clave_de_cuenta(instalada["operador"], "127.0.0.1")
    # Los fallos de una persona con el mismo identificador no hacen esperar a la persona operadora...
    for _ in range(8):
        control.reservar(get_engine(), instalada["operador"], "127.0.0.1")
    assert orden(instalada)[0] == 0
    # ... y los fallos de la persona operadora no tocan el contador de las personas.
    for _ in range(6):
        orden(instalada, MALA)
    assert filas("select intentos from control_de_intentos") == [(5,)] and contar("intento_de_origen") == 5


def test_los_eventos_de_la_persona_operadora_no_llevan_secretos_ni_su_identificador(instalada, reloj):
    for _ in range(6):
        orden(instalada, MALA)
    reloj.avanzar(seconds=30)
    orden(instalada)
    eventos = filas("select tipo, ambito, persona_id, clave_cuenta, clave_origen, detalle from evento_autenticacion order by ocurrido_en, id")
    from collections import Counter
    assert Counter(e[0] for e in eventos) == {"inicio_fallido": 5, "espera_aplicada": 1, "inicio_correcto": 1}
    assert all(e[1] == "operador" and e[2] is None and e[3] == clave(instalada) and e[4] is None for e in eventos)
    assert [e[5] for e in eventos if e[0] == "espera_aplicada"] == [{"espera_segundos": 30}]
    with get_owner_engine().connect() as c:
        for tabla in ("evento_autenticacion", "control_de_intentos_operador"):          # ni la credencial ni el identificador de la persona operadora
            for fila in c.execute(text(f"select t::text from {tabla} t")).all():
                for secreto in (CREDENCIAL, MALA, instalada["operador"], "argon2"):
                    assert secreto not in fila[0], (tabla, secreto)
        for fila in c.execute(text("select t::text from auditoria t")).all():                # la auditoría funcional nombra a quien opera, nunca su credencial
            assert CREDENCIAL not in fila[0] and MALA not in fila[0] and "argon2" not in fila[0]


def test_la_credencial_nunca_va_en_los_argumentos_ni_en_la_salida_de_un_rechazo(instalada, reloj):
    argv = ["crear-equipo", "--operador", instalada["operador"], "--organizacion", str(instalada["org"]), "--nombre", "X"]
    assert MALA not in " ".join(argv) and CREDENCIAL not in " ".join(argv)
    for _ in range(6):
        codigo, salida, error = ejecutar(argv, credencial=MALA)
        assert MALA not in salida + error and CREDENCIAL not in salida + error


# ===================================================== la conexión y la orden ==============================================

@pytest.mark.parametrize("motor_nombre", ["aplicacion", "propietario"])
def test_con_otro_rol_se_rechaza_la_conexion_antes_de_contar_ningun_intento(instalada, reloj, motor_nombre):
    motor = get_engine() if motor_nombre == "aplicacion" else get_owner_engine()
    codigo, _, error = orden(instalada, MALA, motor_provision=motor)
    assert codigo == 3 and json.loads(error)["error"] == "CONEXION_NO_PERMITIDA"
    assert contar("control_de_intentos_operador") == 0 and contar("evento_autenticacion") == 0


def test_un_error_inesperado_al_reservar_no_ejecuta_la_orden(instalada, monkeypatch):
    def falla(*a, **k):
        raise RuntimeError("falló")
    monkeypatch.setattr(control, "reservar_operador", falla)
    codigo, salida, error = orden(instalada)
    assert codigo == 1 and json.loads(error) == {"error": "ERROR_INTERNO", "tipo": "RuntimeError"} and salida == "" and contar("equipo") == 0


def test_una_persona_operadora_revocada_entre_la_identificacion_y_la_orden_no_la_ejecuta(instalada, reloj, monkeypatch):
    original = operadores.autenticar

    def autenticar_y_revocar(motor, identificador, credencial, comprobar):
        operador = original(motor, identificador, credencial, comprobar)
        with get_owner_engine().begin() as c:
            c.execute(text("update operador set estado = 'revocado', revocado_en = now()"))
        return operador
    monkeypatch.setattr(operadores, "autenticar", autenticar_y_revocar)
    codigo, _, error = orden(instalada)
    assert codigo == 2 and json.loads(error)["error"] == "OPERADOR_NO_AUTORIZADO" and contar("equipo") == 0


def test_no_hay_ninguna_transaccion_abierta_mientras_se_calcula_el_hash_de_la_credencial(instalada, reloj, monkeypatch):
    capturas, original = [], operadores.verificar
    rol = get_settings().provision_db_role

    def observando(guardado, credencial):
        # ``pg_stat_activity.state`` está oculto a un rol sin privilegios: se cuentan los bloqueos ``virtualxid`` (transacciones abiertas).
        with get_owner_engine().connect() as c:
            capturas.append((c.execute(text("select count(*) from pg_locks l join pg_stat_activity a on a.pid = l.pid where a.usename = :r and l.locktype = 'virtualxid' and l.granted"),
                                       {"r": rol}).scalar_one(),
                             c.execute(text("select count(*) from pg_locks l join pg_stat_activity a on a.pid = l.pid where a.usename = :r and l.locktype = 'advisory' and l.granted"),
                                       {"r": rol}).scalar_one()))
        return original(guardado, credencial)
    monkeypatch.setattr(operadores, "verificar", observando)
    orden(instalada, MALA)
    orden(instalada)
    assert capturas == [(0, 0), (0, 0)]


def test_la_identificacion_directa_sigue_funcionando_para_los_casos_de_uso(instalada):
    """``identificar`` (sin control de intentos) se conserva para quien ya tiene una conexión abierta: no cambió su contrato."""
    with get_provision_engine().connect() as c:
        assert operadores.identificar(c, "OPERADORA.CLI ", CREDENCIAL).identificador == "operadora.cli"
        with pytest.raises(ErrorDeProvision):
            operadores.identificar(c, "operadora.cli", MALA)


# ===================================================== el proceso real ======================================================

def _proceso(argv, credencial):
    return subprocess.run([sys.executable, "-m", "scripts.provision", *argv], cwd=RAIZ, env={**os.environ, VARIABLE_CREDENCIAL: credencial},
                          capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL, timeout=120)


def test_como_proceso_real_la_sexta_credencial_incorrecta_termina_con_el_codigo_de_espera(instalada):
    argv = ["crear-equipo", "--operador", instalada["operador"], "--organizacion", str(instalada["org"]), "--nombre", "X"]
    resultados = [_proceso(argv, MALA) for _ in range(5)]
    assert [r.returncode for r in resultados] == [2] * 5
    sexto = _proceso(argv, CREDENCIAL)
    assert sexto.returncode == 4 and sexto.stdout == ""
    assert json.loads(sexto.stderr)["error"] == "DEMASIADOS_INTENTOS" and 1 <= json.loads(sexto.stderr)["detalles"][0]["espera_segundos"] <= 30
    assert CREDENCIAL not in sexto.stdout + sexto.stderr and MALA not in sexto.stdout + sexto.stderr and contar("equipo") == 0


# ===================================================== purga de eventos (retención técnica de 30 días) =====================

def _eventos(*dias):
    with get_owner_engine().begin() as c:
        for d in dias:
            c.execute(text("insert into evento_autenticacion (tipo, ambito, clave_cuenta, detalle, ocurrido_en) "
                           "values ('inicio_fallido', 'persona', :k, '{\"motivo\": \"x\"}', now() - make_interval(days => :d))"), {"k": "c" * 64, "d": d})


def de_personas() -> int:
    """Eventos de las personas (los sembrados): la propia identificación de la persona operadora deja un evento de ámbito ``operador``."""
    return filas("select count(*) from evento_autenticacion where ambito = 'persona'")[0][0]


def purgar(instalada, credencial=CREDENCIAL, **extra):
    return ejecutar(["purgar-eventos-autenticacion", "--operador", instalada["operador"]], credencial=credencial, **extra)


def test_la_purga_borra_solo_los_eventos_de_mas_de_30_dias(instalada):
    _eventos(31, 45, 90, 29, 10, 0)
    codigo, salida, error = purgar(instalada)
    r = json.loads(salida)
    assert codigo == 0 and error == "" and r["orden"] == "purgar-eventos-autenticacion" and r["eventos_purgados"] == 3 and r["retencion_dias"] == 30
    assert de_personas() == 3
    assert sorted(round(f[0]) for f in filas("select extract(day from now() - ocurrido_en) from evento_autenticacion where ambito = 'persona'")) == [0, 10, 29]


def test_la_purga_es_repetible_y_la_segunda_vez_no_borra_nada(instalada):
    _eventos(40, 41, 5)
    assert json.loads(purgar(instalada)[1])["eventos_purgados"] == 2
    assert json.loads(purgar(instalada)[1])["eventos_purgados"] == 0
    assert de_personas() == 1


def test_la_salida_de_la_purga_no_revela_el_contenido_de_ningun_evento(instalada):
    _eventos(40)
    codigo, salida, error = purgar(instalada)
    assert set(json.loads(salida)) == {"orden", "operador_id", "invocacion", "base", "eventos_purgados", "anteriores_a", "retencion_dias"}
    assert "c" * 64 not in salida and "motivo" not in salida and CREDENCIAL not in salida + error


def test_la_purga_exige_la_identificacion_de_la_persona_operadora_y_cuenta_sus_intentos(instalada, reloj):
    _eventos(40)
    codigo, salida, error = purgar(instalada, MALA)
    assert codigo == 2 and json.loads(error)["error"] == "OPERADOR_NO_AUTORIZADO" and contar("evento_autenticacion") == 1 + 1   # + el fallo de la operadora
    assert filas("select intentos from control_de_intentos_operador") == [(1,)]


def test_la_purga_respeta_una_retencion_mayor_configurada(instalada, monkeypatch):
    monkeypatch.setattr(get_settings(), "auth_event_retention_days", 60)
    _eventos(45, 61, 100)
    assert json.loads(purgar(instalada)[1])["eventos_purgados"] == 2 and de_personas() == 1


def test_aunque_el_reloj_falle_la_base_impide_borrar_eventos_de_menos_de_30_dias(instalada):
    """Defensa en profundidad: un reloj adelantado haría que el código intentara borrarlo todo; el disparador de la base lo rechaza."""
    from datetime import datetime, timedelta, timezone
    _eventos(40, 5)
    codigo, salida, error = purgar(instalada, reloj=lambda: datetime.now(timezone.utc) + timedelta(days=200))
    assert codigo == 1 and json.loads(error) == {"error": "ERROR_INTERNO", "tipo": "IntegrityError"} and salida == ""
    assert de_personas() == 2                                                            # ni siquiera lo viejo: la orden es atómica


def test_la_purga_no_toca_la_auditoria_los_contadores_ni_las_sesiones(instalada):
    _eventos(40)
    with get_owner_engine().begin() as c:
        c.execute(text("insert into control_de_intentos (clave, intentos, ultimo_intento_en) values (:k, 1, now())"), {"k": "d" * 64})
    antes = (contar("auditoria"), contar("control_de_intentos"), contar("sesion"), contar("operador"))
    assert purgar(instalada)[0] == 0
    assert (contar("auditoria"), contar("control_de_intentos"), contar("sesion"), contar("operador")) == antes


@pytest.mark.parametrize("motor_nombre", ["aplicacion", "propietario"])
def test_la_purga_se_niega_con_un_rol_distinto_del_de_provision(instalada, motor_nombre):
    _eventos(40)
    motor = get_engine() if motor_nombre == "aplicacion" else get_owner_engine()
    codigo, _, error = purgar(instalada, motor_provision=motor)
    assert codigo == 3 and json.loads(error)["error"] == "CONEXION_NO_PERMITIDA" and contar("evento_autenticacion") == 1


def test_no_existe_ninguna_ruta_http_de_purga_ni_de_consulta_de_eventos():
    from app.main import crear_app
    for ruta in crear_app().openapi()["paths"]:
        for palabra in ("purg", "evento", "intento"):
            assert palabra not in ruta, ruta


def test_la_orden_de_purga_no_acepta_credenciales_ni_fechas_como_argumentos():
    from app.provision import cli
    ayuda = cli._parser()._subparsers._group_actions[0].choices["purgar-eventos-autenticacion"].format_help()
    for palabra in ("--credencial", "--password", "--contrasena", "--hoy", "--fecha", "--dias", "--retencion"):
        assert palabra not in ayuda


def test_verificar_conexion_se_usa_antes_que_ninguna_otra_consulta(instalada):
    with get_owner_engine().connect() as c:
        with pytest.raises(ErrorDeProvision):
            verificar_conexion_de_provision(c)
