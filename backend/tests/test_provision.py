"""M1-T2 — provisión inicial: crear equipo (M1-02a) y crear persona con su pertenencia inicial (M1-02b).

Casos de uso con PostgreSQL real, ejecutados con el rol de PROVISIÓN (privilegios mínimos), sin CLI ni HTTP.
Criterios: CA-06 a CA-10, CA-22, CA-26, CA-250 a CA-253, CA-251; IR-02, IR-03, IR-28, IR-32, RN-106; P6. Las pruebas
destructivas corren solo sobre ``smartwork_test``.
"""

import json
import threading
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.config import get_settings
from app.db import get_owner_engine, get_provision_engine
from app.provision import operadores, servicio
from app.provision.errores import ErrorDeProvision
from app.provision.operadores import Operador, crear_primer_operador, identificar
from app.provision.servicio import crear_equipo, crear_persona
from tests.fabricas import crear_equipo as fab_equipo, crear_organizacion, crear_persona as fab_persona, crear_pertenencia, hoy
from tests.utiles_http import API, iniciar_sesion, nuevo_cliente
from tests.utiles_m2 import contar, filas

CREDENCIAL = "credencial-de-prueba-123"
HOY = hoy()


@pytest.fixture()
def operador() -> Operador:
    with get_owner_engine().begin() as c:
        return crear_primer_operador(c, "Operadora.Uno", CREDENCIAL, uuid.uuid4())


@pytest.fixture()
def org():
    with get_owner_engine().begin() as c:
        return crear_organizacion(c)


def orden(funcion, operador, **kw):
    """Una orden = una transacción con el rol de provisión: si falla, se deshace por completo."""
    with get_provision_engine().begin() as c:
        return funcion(c, operador, **kw)


def equipo(operador, org, nombre="Equipo A"):
    return orden(crear_equipo, operador, organizacion_id=org, nombre=nombre)


def persona(operador, eq, rol="colaborador", desde=HOY, nombre="Ana Pérez", ident="ana.perez", **kw):
    return orden(crear_persona, operador, nombre=nombre, identificador_acceso=ident, equipo_id=eq.equipo_id if hasattr(eq, "equipo_id") else eq,
                 rol=rol, desde=desde, **kw)


def rechaza(codigo, funcion, operador, **kw):
    with pytest.raises(ErrorDeProvision) as e:
        orden(funcion, operador, **kw)
    assert e.value.codigo == codigo
    return e.value


def auditoria():
    return filas("select tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id, propietaria_registro_id, valor_nuevo "
                 "from auditoria order by momento, id")


# ===================================================== M1-02a: crear un equipo ============================================

def test_un_equipo_se_crea_en_una_organizacion_existente_y_nace_sin_supervisor(operador, org):
    e = equipo(operador, org, "Contabilidad")
    assert filas("select nombre, organizacion_id from equipo") == [("Contabilidad", org)]
    assert filas("select count(*) from pertenencia") == [(0,)]                    # CA-250: puede carecer de supervisor
    assert e.nombre == "Contabilidad" and e.organizacion_id == org


def test_crear_un_equipo_deja_una_unica_entrada_de_provision_con_la_persona_operadora(operador, org):
    e = equipo(operador, org, "Contabilidad")
    entradas = [a for a in auditoria() if a[3] == "equipo"]
    assert len(entradas) == 1
    tipo_autor, referencia, operacion, tipo_objeto, objeto_id, propietaria, nuevo = entradas[0]
    assert (tipo_autor, operacion, objeto_id, propietaria) == ("provision", "alta", e.equipo_id, None)   # CA-251
    assert referencia.startswith(f"operador:{operador.identificador}|invocacion:")
    assert nuevo == {"equipo": str(e.equipo_id), "organizacion": str(org), "nombre": "Contabilidad"}


def test_la_organizacion_debe_existir(operador):
    e = rechaza("RECURSO_NO_DISPONIBLE", crear_equipo, operador, organizacion_id=uuid.uuid4(), nombre="X")
    assert e.detalles == [{"campo": "organizacion"}]
    assert contar("equipo") == 0 and contar("auditoria") == 1                     # solo la alta de la persona operadora


@pytest.mark.parametrize("nombre", ["", "   ", "\t\n", None])
def test_el_nombre_del_equipo_es_obligatorio(operador, org, nombre):
    rechaza("CAMPO_OBLIGATORIO", crear_equipo, operador, organizacion_id=org, nombre=nombre)
    assert contar("equipo") == 0


def test_el_nombre_del_equipo_tiene_un_maximo_configurable(operador, org):
    maximo = get_settings().text_max_title
    equipo(operador, org, "x" * maximo)
    rechaza("TEXTO_DEMASIADO_LARGO", crear_equipo, operador, organizacion_id=org, nombre="y" * (maximo + 1))
    assert contar("equipo") == 1


@pytest.mark.parametrize("repetido", ["contabilidad", "CONTABILIDAD", "Contabilidad", "  Contabilidad  ", "\tcontabilidad\n", "cOnTaBiLiDaD "])
def test_el_nombre_es_unico_por_organizacion_sin_distinguir_mayusculas_ni_espacios_exteriores(operador, org, repetido):
    equipo(operador, org, "Contabilidad")
    rechaza("NOMBRE_DE_EQUIPO_DUPLICADO", crear_equipo, operador, organizacion_id=org, nombre=repetido)
    assert contar("equipo") == 1 and len([a for a in auditoria() if a[3] == "equipo"]) == 1


def test_el_nombre_con_acentos_se_compara_sin_distinguir_mayusculas(operador, org):
    equipo(operador, org, "Ánimo Ñandú")
    rechaza("NOMBRE_DE_EQUIPO_DUPLICADO", crear_equipo, operador, organizacion_id=org, nombre="ÁNIMO ÑANDÚ")
    rechaza("NOMBRE_DE_EQUIPO_DUPLICADO", crear_equipo, operador, organizacion_id=org, nombre="ánimo ñandú")


@pytest.mark.parametrize("distinto", ["Animo Ñandú", "Ánimo Nandú", "Ánimo  Ñandú", "ÁnimoÑandú"])
def test_no_se_quitan_acentos_ni_espacios_interiores_al_comparar(operador, org, distinto):
    equipo(operador, org, "Ánimo Ñandú")
    equipo(operador, org, distinto)                       # es OTRO nombre: se acepta
    assert contar("equipo") == 2


def test_el_nombre_guardado_conserva_su_forma_salvo_los_espacios_exteriores(operador, org):
    e = equipo(operador, org, "  Soporte  Técnico  ")
    assert e.nombre == "Soporte  Técnico" and filas("select nombre from equipo") == [("Soporte  Técnico",)]


def test_el_mismo_nombre_se_admite_en_otra_organizacion(operador, org):
    with get_owner_engine().begin() as c:
        otra = crear_organizacion(c)
    equipo(operador, org, "Contabilidad")
    equipo(operador, otra, "contabilidad")
    assert contar("equipo") == 2


# ===================================================== M1-02b: crear una persona ==========================================

def test_el_primer_integrante_de_un_equipo_es_su_supervisor_y_un_colaborador_se_une_despues(operador, org):
    e = equipo(operador, org)
    s = persona(operador, e, "supervisor", nombre="Sofía Supervisora", ident="sofia")
    c = persona(operador, e, "colaborador", nombre="Carlos Colaborador", ident="carlos")
    assert [f[:2] for f in filas("select rol, hasta_exclusivo from pertenencia order by rol")] == [("colaborador", None), ("supervisor", None)]
    assert s.rol == "supervisor" and c.rol == "colaborador" and c.sin_contrasena


def test_la_persona_se_crea_con_identidad_sin_contrasena_y_pertenencia_desde_la_fecha_indicada(operador, org):
    e = equipo(operador, org)
    persona(operador, e, "supervisor", desde=HOY + timedelta(days=3), nombre="Sofía", ident="Sofia.Sup")
    assert filas("select nombre from persona") == [("Sofía",)]
    assert filas("select identificador_acceso, hash_contrasena from identidad") == [("sofia.sup", None)]   # normalizado, sin contraseña
    assert filas("select rol, desde, hasta_exclusivo, equipo_id from pertenencia") == [("supervisor", HOY + timedelta(days=3), None, e.equipo_id)]


def test_crear_una_persona_deja_una_unica_entrada_de_provision_sin_credenciales_ni_identificadores(operador, org):
    e = equipo(operador, org)
    p = persona(operador, e, "supervisor", ident="sofia.secreta")
    entradas = [a for a in auditoria() if a[3] == "persona"]
    assert len(entradas) == 1
    tipo_autor, referencia, operacion, _, objeto_id, propietaria, nuevo = entradas[0]
    assert (tipo_autor, operacion, objeto_id, propietaria) == ("provision", "alta", p.persona_id, p.persona_id)
    assert referencia.startswith(f"operador:{operador.identificador}|invocacion:")
    assert nuevo == {"persona": str(p.persona_id), "equipo": str(e.equipo_id), "rol": "supervisor", "desde": HOY.isoformat()}
    texto = json.dumps([list(map(str, a)) for a in auditoria()])
    assert "sofia.secreta" not in texto and CREDENCIAL not in texto and "argon2" not in texto   # CA-251


def test_un_colaborador_exige_que_el_equipo_tenga_supervisor_desde_esa_fecha(operador, org):
    e = equipo(operador, org)
    err = rechaza("PERTENENCIA_INVALIDA", crear_persona, operador, nombre="Carlos", identificador_acceso="carlos",
                  equipo_id=e.equipo_id, rol="colaborador", desde=HOY)
    assert err.detalles == [{"campo": "rol", "motivo": "el_equipo_no_tiene_supervisor_desde_esa_fecha"}]   # IR-32
    assert contar("persona") == 0 and contar("identidad") == 0 and contar("pertenencia") == 0


def test_un_segundo_supervisor_no_se_asigna_a_un_equipo_que_ya_tiene_supervisor(operador, org):
    e = equipo(operador, org)
    persona(operador, e, "supervisor", ident="sofia")
    err = rechaza("PERTENENCIA_INVALIDA", crear_persona, operador, nombre="Otro", identificador_acceso="otro",
                  equipo_id=e.equipo_id, rol="supervisor", desde=HOY)
    assert err.detalles == [{"campo": "rol", "motivo": "el_equipo_ya_tiene_supervisor"}]                  # CA-08
    assert contar("persona") == 1 and filas("select count(*) from pertenencia where rol = 'supervisor'") == [(1,)]


def test_un_supervisor_solo_supervisa_un_equipo_y_cada_persona_tiene_un_unico_equipo(operador, org):
    e1, e2 = equipo(operador, org, "A"), equipo(operador, org, "B")
    persona(operador, e1, "supervisor", ident="s1")
    persona(operador, e2, "supervisor", ident="s2")
    # una persona nueva solo entra en el equipo que se indica: no existe la operación de añadir a otro (CA-07, CA-10)
    assert filas("select count(distinct persona_id), count(*) from pertenencia") == [(2, 2)]


def test_un_supervisor_nuevo_puede_empezar_cuando_termina_el_anterior_y_el_equipo_sigue_cubierto(operador, org):
    e = equipo(operador, org)
    fin = HOY + timedelta(days=10)
    with get_owner_engine().begin() as c:   # el supervisor actual termina en `fin` (lo hará M1-T4; aquí se prepara por SQL)
        s0 = fab_persona(c, "S0")
        crear_pertenencia(c, s0, e.equipo_id, "supervisor", desde=HOY - timedelta(days=5), hasta=fin)
    rechaza("PERTENENCIA_INVALIDA", crear_persona, operador, nombre="S1", identificador_acceso="s1", equipo_id=e.equipo_id,
            rol="supervisor", desde=fin - timedelta(days=1))                      # solapa un día con el anterior (IR-03)
    persona(operador, e, "supervisor", desde=fin, ident="s1")                     # contiguo: se acepta
    persona(operador, e, "colaborador", desde=HOY, ident="c1")                    # cubierto sin huecos hasta el infinito (IR-32)


def test_un_colaborador_no_se_asigna_si_la_supervision_tiene_un_hueco_o_termina(operador, org):
    e = equipo(operador, org)
    with get_owner_engine().begin() as c:
        s0 = fab_persona(c, "S0")
        crear_pertenencia(c, s0, e.equipo_id, "supervisor", desde=HOY - timedelta(days=5), hasta=HOY + timedelta(days=10))
    rechaza("PERTENENCIA_INVALIDA", crear_persona, operador, nombre="C", identificador_acceso="c", equipo_id=e.equipo_id,
            rol="colaborador", desde=HOY)           # el supervisor termina: tras su fin el equipo tendría un colaborador sin supervisor
    assert contar("persona") == 1


def test_un_colaborador_que_empieza_antes_de_que_llegue_el_supervisor_se_rechaza(operador, org):
    e = equipo(operador, org)
    persona(operador, e, "supervisor", desde=HOY + timedelta(days=10), ident="s")
    rechaza("PERTENENCIA_INVALIDA", crear_persona, operador, nombre="C", identificador_acceso="c", equipo_id=e.equipo_id,
            rol="colaborador", desde=HOY)
    persona(operador, e, "colaborador", desde=HOY + timedelta(days=10), ident="c")    # desde que llega el supervisor, sí


def test_el_rol_debe_ser_colaborador_o_supervisor(operador, org):
    e = equipo(operador, org)
    err = rechaza("PERTENENCIA_INVALIDA", crear_persona, operador, nombre="X", identificador_acceso="x", equipo_id=e.equipo_id,
                  rol="administrador", desde=HOY)
    assert err.detalles == [{"campo": "rol", "motivo": "rol_no_valido"}]            # no existe un tercer rol funcional (RN-33)


def test_el_equipo_debe_existir(operador):
    rechaza("RECURSO_NO_DISPONIBLE", crear_persona, operador, nombre="X", identificador_acceso="x", equipo_id=uuid.uuid4(),
            rol="supervisor", desde=HOY)
    assert contar("persona") == 0


@pytest.mark.parametrize("campo,valor", [("nombre", ""), ("nombre", "   "), ("identificador_acceso", ""), ("identificador_acceso", "  \t ")])
def test_el_nombre_y_el_identificador_de_la_persona_son_obligatorios(operador, org, campo, valor):
    e = equipo(operador, org)
    kw = {"nombre": "Ana", "identificador_acceso": "ana", **{campo: valor}}
    rechaza("CAMPO_OBLIGATORIO", crear_persona, operador, equipo_id=e.equipo_id, rol="supervisor", desde=HOY, **kw)
    assert contar("persona") == 0


def test_los_textos_de_la_persona_tienen_un_maximo_configurable(operador, org):
    e = equipo(operador, org)
    s = get_settings()
    rechaza("TEXTO_DEMASIADO_LARGO", crear_persona, operador, nombre="n" * (s.text_max_title + 1), identificador_acceso="a",
            equipo_id=e.equipo_id, rol="supervisor", desde=HOY)
    rechaza("TEXTO_DEMASIADO_LARGO", crear_persona, operador, nombre="Ana", identificador_acceso="a" * (s.login_identifier_max_length + 1),
            equipo_id=e.equipo_id, rol="supervisor", desde=HOY)
    assert contar("persona") == 0


@pytest.mark.parametrize("repetido", ["ana", "ANA", "  Ana  ", "ａｎａ"])
def test_el_identificador_de_acceso_es_unico_una_vez_normalizado(operador, org, repetido):
    e = equipo(operador, org)
    persona(operador, e, "supervisor", ident="ana")
    rechaza("IDENTIFICADOR_DUPLICADO", crear_persona, operador, nombre="Otra", identificador_acceso=repetido,
            equipo_id=e.equipo_id, rol="colaborador", desde=HOY)
    assert contar("persona") == 1 and contar("identidad") == 1 and contar("pertenencia") == 1


# ===================================================== fechas (CA-252, CA-253, RN-106) y reloj inyectable =================

def test_la_fecha_de_inicio_igual_o_posterior_a_la_fecha_actual_se_acepta_y_la_anterior_se_rechaza(operador, org):
    e = equipo(operador, org)
    persona(operador, e, "supervisor", desde=HOY, ident="hoy")                                  # CA-252: igual a hoy
    persona(operador, e, "colaborador", desde=HOY + timedelta(days=30), ident="futuro")         # posterior
    rechaza("FECHA_EFECTIVA_INVALIDA", crear_persona, operador, nombre="Ayer", identificador_acceso="ayer",
            equipo_id=e.equipo_id, rol="colaborador", desde=HOY - timedelta(days=1))            # CA-253: no hay altas históricas
    assert contar("persona") == 2


def _reloj(instante: datetime):
    return lambda: instante


def test_la_fecha_actual_se_mide_en_la_zona_de_la_organizacion_con_un_reloj_inyectable(operador, org):
    """Organización en America/Bogota (UTC-5): a las 04:59:59 UTC todavía es el día anterior; a las 05:00:00 UTC ya es hoy."""
    e = equipo(operador, org)
    antes = _reloj(datetime(2026, 6, 15, 4, 59, 59, tzinfo=timezone.utc))     # en Bogotá: 2026-06-14 23:59:59
    despues = _reloj(datetime(2026, 6, 15, 5, 0, 0, tzinfo=timezone.utc))     # en Bogotá: 2026-06-15 00:00:00
    persona(operador, e, "supervisor", desde=date(2026, 6, 14), ident="s", reloj=antes)           # el día 14 es «hoy»: se acepta
    rechaza("FECHA_EFECTIVA_INVALIDA", crear_persona, operador, nombre="C", identificador_acceso="c", equipo_id=e.equipo_id,
            rol="colaborador", desde=date(2026, 6, 13), reloj=antes)                              # el 13 ya es pasado
    rechaza("FECHA_EFECTIVA_INVALIDA", crear_persona, operador, nombre="C", identificador_acceso="c", equipo_id=e.equipo_id,
            rol="colaborador", desde=date(2026, 6, 14), reloj=despues)                            # con el reloj siguiente, el 14 es pasado
    persona(operador, e, "colaborador", desde=date(2026, 6, 15), ident="c", reloj=despues)


# ===================================================== atomicidad y rollback ==============================================

def _recuentos():
    return {t: contar(t) for t in ("persona", "identidad", "pertenencia", "equipo", "auditoria", "operador")}


def test_una_orden_rechazada_no_deja_altas_parciales_ni_entradas(operador, org):
    e = equipo(operador, org)
    persona(operador, e, "supervisor", ident="s")
    antes = _recuentos()
    for kw in ({"identificador_acceso": "s"},                                 # identificador duplicado
               {"identificador_acceso": "nuevo", "rol": "supervisor"},        # segundo supervisor
               {"identificador_acceso": "nuevo", "desde": HOY - timedelta(days=1)}):   # fecha pasada
        base = {"nombre": "Nueva", "identificador_acceso": "nuevo", "equipo_id": e.equipo_id, "rol": "colaborador", "desde": HOY, **kw}
        with pytest.raises(ErrorDeProvision):
            orden(crear_persona, operador, **base)
        assert _recuentos() == antes


def test_si_falla_el_ultimo_paso_no_queda_ni_la_persona_ni_la_identidad_ni_la_pertenencia(operador, org, monkeypatch):
    e = equipo(operador, org)
    antes = _recuentos()

    def falla(*a, **k):
        raise RuntimeError("fallo simulado al auditar")

    monkeypatch.setattr(servicio, "_auditar", falla)
    with pytest.raises(RuntimeError):
        persona(operador, e, "supervisor", ident="s")
    assert _recuentos() == antes                                              # todo o nada


def test_si_falla_la_auditoria_de_un_equipo_no_queda_el_equipo(operador, org, monkeypatch):
    antes = _recuentos()
    monkeypatch.setattr(servicio, "_auditar", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fallo simulado")))
    with pytest.raises(RuntimeError):
        equipo(operador, org, "Nuevo")
    assert _recuentos() == antes


def test_la_base_rechaza_una_pertenencia_que_el_servicio_no_comprobara(operador, org):
    """Defensa en profundidad: aunque se saltara la validación del servicio, la base impide dos supervisores a la vez."""
    e = equipo(operador, org)
    persona(operador, e, "supervisor", ident="s")
    with get_owner_engine().begin() as c:
        otra = fab_persona(c, "Otra")
    with pytest.raises(Exception) as error:
        with get_owner_engine().begin() as c:
            crear_pertenencia(c, otra, e.equipo_id, "supervisor", desde=HOY)
    assert "pertenencia_un_supervisor_por_equipo_y_fecha" in str(error.value)


# ===================================================== concurrencia =======================================================

def _simultaneas(trabajos):
    resultados, barrera = [None] * len(trabajos), threading.Barrier(len(trabajos))

    def correr(i, trabajo):
        barrera.wait()
        try:
            trabajo()
            resultados[i] = "ok"
        except ErrorDeProvision as e:
            resultados[i] = e.codigo
        except Exception as e:  # noqa: BLE001
            resultados[i] = f"INESPERADO:{type(e).__name__}"

    hilos = [threading.Thread(target=correr, args=(i, t)) for i, t in enumerate(trabajos)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    return resultados


def test_altas_simultaneas_del_mismo_nombre_de_equipo_con_distinta_forma_dejan_un_solo_equipo(operador, org):
    nombres = ["Ventas", "VENTAS", " ventas ", "vEnTaS", "Ventas\t", "ventas", "VENTAS ", " Ventas"]
    res = _simultaneas([lambda n=n: equipo(operador, org, n) for n in nombres])
    assert res.count("ok") == 1 and res.count("NOMBRE_DE_EQUIPO_DUPLICADO") == len(nombres) - 1, res
    assert contar("equipo") == 1 and len([a for a in auditoria() if a[3] == "equipo"]) == 1


def test_altas_simultaneas_con_el_mismo_identificador_dejan_una_sola_persona(operador, org):
    e = equipo(operador, org)
    persona(operador, e, "supervisor", ident="sup")
    res = _simultaneas([lambda k=k: persona(operador, e, "colaborador", ident="Mismo.Id" if k % 2 else "mismo.id", nombre=f"P{k}")
                        for k in range(6)])
    assert res.count("ok") == 1 and res.count("IDENTIFICADOR_DUPLICADO") == 5, res
    assert contar("persona") == 2 and contar("identidad") == 2 and contar("pertenencia") == 2


def test_supervisores_simultaneos_del_mismo_equipo_dejan_uno_solo(operador, org):
    e = equipo(operador, org)
    res = _simultaneas([lambda k=k: persona(operador, e, "supervisor", ident=f"s{k}", nombre=f"S{k}") for k in range(6)])
    assert res.count("ok") == 1 and res.count("PERTENENCIA_INVALIDA") == 5, res
    assert filas("select count(*) from pertenencia where rol = 'supervisor'") == [(1,)] and contar("persona") == 1


def test_un_colaborador_y_un_supervisor_simultaneos_en_un_equipo_sin_supervisor_no_dejan_un_equipo_incoherente(operador, org):
    e = equipo(operador, org)
    res = _simultaneas([lambda: persona(operador, e, "colaborador", ident="c", nombre="C"),
                        lambda: persona(operador, e, "supervisor", ident="s", nombre="S")])
    # El colaborador solo prospera si el supervisor ya estaba; nunca queda un colaborador sin supervisor.
    sup = filas("select count(*) from pertenencia where rol = 'supervisor'")[0][0]
    col = filas("select count(*) from pertenencia where rol = 'colaborador'")[0][0]
    assert sup == 1 and col in (0, 1), (res, sup, col)
    assert "INESPERADO" not in " ".join(res)


# ===================================================== personas operadoras ================================================

def test_la_primera_persona_operadora_se_crea_con_hash_normalizada_y_auditoria_sin_credencial(operador):
    fila = filas("select identificador, hash_credencial, estado, concedido_por from operador")[0]
    assert fila[0] == "operadora.uno" and fila[1].startswith("$argon2id$") and CREDENCIAL not in fila[1]
    assert fila[2:] == ("activo", None)
    entradas = auditoria()
    assert len(entradas) == 1 and entradas[0][:4] == ("provision", f"instalacion|invocacion:{entradas[0][1].split(':')[1]}", "alta", "operador")
    assert CREDENCIAL not in json.dumps([list(map(str, a)) for a in entradas])


def test_no_se_crea_una_segunda_persona_operadora_por_el_procedimiento_de_instalacion(operador):
    with pytest.raises(ErrorDeProvision) as e, get_owner_engine().begin() as c:
        crear_primer_operador(c, "otra.operadora", CREDENCIAL, uuid.uuid4())
    assert e.value.codigo == "INSTALACION_YA_REALIZADA" and contar("operador") == 1


@pytest.mark.parametrize("credencial", ["", "corta", "x" * 9])
def test_una_credencial_demasiado_corta_se_rechaza(credencial):
    with pytest.raises(ErrorDeProvision) as e, get_owner_engine().begin() as c:
        crear_primer_operador(c, "operadora", credencial, uuid.uuid4())
    assert e.value.codigo == "CREDENCIAL_NO_VALIDA" and contar("operador") == 0 and contar("auditoria") == 0


def test_la_credencial_tiene_un_maximo(operador):
    with pytest.raises(ErrorDeProvision) as e, get_owner_engine().begin() as c:
        operadores.validar_credencial("x" * (get_settings().login_password_max_length + 1))
    assert e.value.codigo == "CREDENCIAL_NO_VALIDA"


def test_identificar_a_la_persona_operadora(operador):
    with get_provision_engine().begin() as c:
        assert identificar(c, "OPERADORA.UNO ", CREDENCIAL) == operador


def test_credencial_incorrecta_identificador_desconocido_y_operadora_revocada_dan_el_mismo_error(operador):
    with get_owner_engine().begin() as c:
        c.execute(text("insert into operador (identificador, hash_credencial, estado, revocado_en) values "
                       "('revocada', (select hash_credencial from operador limit 1), 'revocado', now())"))
    errores = []
    for ident, cred in (("operadora.uno", "otra-credencial-123"), ("no.existe", CREDENCIAL), ("revocada", CREDENCIAL), ("", ""), (None, None)):
        with pytest.raises(ErrorDeProvision) as e, get_provision_engine().begin() as c:
            identificar(c, ident, cred)
        errores.append(e.value.como_dict())
    assert all(x == errores[0] for x in errores) and errores[0]["error"] == "OPERADOR_NO_AUTORIZADO"


def test_una_persona_creada_no_puede_iniciar_sesion_hasta_el_primer_acceso(operador, org):
    """No se emite ningún código ni se fija contraseña (M1-03a/b no existen): la persona aún no puede entrar."""
    e = equipo(operador, org)
    persona(operador, e, "supervisor", ident="sofia")
    r = iniciar_sesion(nuevo_cliente(), "sofia", "cualquier-contraseña-123")
    assert r.status_code == 401 and r.json()["codigo"] == "CREDENCIALES_INVALIDAS"
    assert filas("select count(*) from sesion") == [(0,)]


def test_las_personas_creadas_por_provision_se_pueden_usar_despues_con_la_politica_de_acceso(operador, org):
    """La persona creada con inicio hoy tiene una pertenencia vigente: la política de acceso la reconoce (IR-38)."""
    from app.compartido.pertenencias import equipo_en_fecha
    from app.db import new_session
    e = equipo(operador, org)
    p = persona(operador, e, "supervisor", ident="sofia")
    with new_session() as db:
        assert equipo_en_fecha(db, p.persona_id, HOY) == e.equipo_id
