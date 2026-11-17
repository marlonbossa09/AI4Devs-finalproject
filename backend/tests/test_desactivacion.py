"""M1-T6 — desactivar el acceso de una persona (M1-08) con PostgreSQL real y el rol de PROVISIÓN (privilegios mínimos).

Criterios: CA-255, CA-256, CA-260 y CA-261; reglas IR-37, IR-38, RA-12, DM-09, DD-04, DD-05 y P6. Las pruebas destructivas corren solo
sobre ``smartwork_test``. Una orden = una transacción con el rol de provisión: si falla, se deshace por completo y no deja cambios,
sesiones revocadas ni auditoría. Se reutiliza el escenario de ``test_traslados`` (equipo T: supervisor ST y colaboradores C1 y C2;
equipo U: supervisor SU y colaborador CU; equipo W: solo su supervisor SW; equipo X: vacío).
"""

import json
import threading
import uuid
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.compartido import pertenencias
from app.compartido.visibilidad import EntradaDeAuditoria, Motivo, Registro, consultante_de, decidir_lectura, decidir_lectura_de_auditoria
from app.config import get_settings
from app.db import get_engine, get_owner_engine, get_provision_engine
from app.provision import acceso
from app.provision.acceso import ADVERTENCIA_EQUIPO_PENDIENTE, desactivar_acceso
from app.provision.errores import ErrorDeProvision
from app.provision.servicio import registrar_traslado
from tests.fabricas import hoy
from tests.test_traslados import (  # noqa: F401  (fixtures y asistentes compartidos)
    CREDENCIAL, HOY, _esperar_bloqueo_consultivo, cambio, dia, historial, mundo, operador, orden,
)
from tests.utiles_m2 import contar, filas

MOTIVO = "Fin de la relación laboral"


def desactivar(operador, mundo, persona, motivo=MOTIVO, **kw):
    return orden(desactivar_acceso, operador, persona_id=mundo.p[persona], motivo=motivo, **kw)


def foto():
    """Todo lo que la desactivación NO debe tocar: personas (menos el acceso), equipos, pertenencias, identidades y registros de M2 y M3."""
    return {
        "persona": filas("select id, nombre from persona order by id"),
        "equipo": filas("select * from equipo order by id"),
        "pertenencia": filas("select * from pertenencia order by id"),
        "identidad": filas("select * from identidad order by id"),
        "m2": [filas(f"select x::text from {t} x order by x.id") for t in ("bitacora", "actividad", "planificacion", "avance")],
        "auditoria": filas("select * from auditoria order by id"),
    }


def acceso_de(mundo, persona):
    return filas("select acceso_desactivado_en from persona where id = :p", p=mundo.p[persona])[0][0]


def sesion(mundo, persona, secreto, revocada=False):
    """Una sesión de la persona, creada por el propietario (lo que haría el inicio de sesión)."""
    with get_owner_engine().begin() as c:
        identidad = c.execute(text("select id from identidad where persona_id = :p"), {"p": mundo.p[persona]}).scalar_one()
        c.execute(text("insert into sesion (identidad_id, secreto_hash, caduca_absoluta_en, revocada_en) values (:i, :h, now() + interval '1 hour', "
                       "case when :r then now() - interval '1 hour' end)"), {"i": identidad, "h": secreto, "r": revocada})


def vigentes(mundo, persona) -> int:
    return filas("select count(*) from sesion s join identidad i on i.id = s.identidad_id where i.persona_id = :p and s.revocada_en is null", p=mundo.p[persona])[0][0]


def entrada():
    return filas("select tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id, propietaria_registro_id, motivo, valor_anterior, valor_nuevo "
                 "from auditoria where operacion = 'desactivacion_acceso' order by momento, id")


def rechaza(codigo, operador, mundo, persona="C1", motivo=MOTIVO, **kw) -> ErrorDeProvision:
    """La orden se rechaza con ese código y NO deja cambios: personas, pertenencias, sesiones, auditoría y acceso idénticos."""
    estado = lambda: (foto(), acceso_de(mundo, persona), filas("select id, revocada_en from sesion order by id"))   # noqa: E731
    antes = estado()
    with pytest.raises(ErrorDeProvision) as e:
        orden(desactivar_acceso, operador, persona_id=mundo.p[persona], motivo=motivo, **kw)
    assert e.value.codigo == codigo
    assert estado() == antes, "una orden rechazada no puede dejar cambios"
    return e.value


# ===================================================== desactivación válida ================================================

def test_desactivar_fija_la_hora_de_la_base_de_datos_y_conserva_todo_lo_demas(operador, mundo):
    antes = foto()
    r = desactivar(operador, mundo, "C1")
    assert acceso_de(mundo, "C1") == r.desactivado_en and r.persona_id == mundo.p["C1"]
    despues = foto()
    auditoria_antes, auditoria_despues = antes.pop("auditoria"), despues.pop("auditoria")
    assert despues == antes                                                         # personas (sin el acceso), equipos, pertenencias, identidades y M2 intactos
    por_id = {f[0]: f for f in auditoria_despues}
    assert all(por_id[f[0]] == f for f in auditoria_antes) and len(auditoria_despues) == len(auditoria_antes) + 1      # las entradas previas no cambian


def test_la_hora_la_pone_la_base_de_datos_no_la_orden(operador, mundo):
    """El reloj inyectable de la orden (D7) solo gobierna «hoy» de las advertencias: el instante del acceso es el de PostgreSQL."""
    reloj = lambda: datetime(2031, 1, 1, tzinfo=timezone.utc)      # noqa: E731
    r = desactivar(operador, mundo, "C1", reloj=reloj)
    assert r.desactivado_en.year != 2031 and filas("select acceso_desactivado_en <= now() from persona where id = :p", p=mundo.p["C1"]) == [(True,)]


def test_una_unica_entrada_de_auditoria_de_provision_con_el_motivo_sin_secretos(operador, mundo):
    antes = contar("auditoria")
    r = desactivar(operador, mundo, "C1", "  Fin del contrato  ")
    assert contar("auditoria") == antes + 1
    [(tipo_autor, referencia, operacion, tipo_objeto, objeto_id, propietaria, motivo, anterior, nuevo)] = entrada()
    assert (tipo_autor, operacion, tipo_objeto, objeto_id, propietaria) == ("provision", "desactivacion_acceso", "persona", mundo.p["C1"], mundo.p["C1"])
    assert referencia == f"operador:{operador.identificador}|invocacion:{r.invocacion}"
    assert motivo == "Fin del contrato"                                             # recortado
    assert anterior == {"acceso_desactivado_en": None}
    assert nuevo == {"acceso_desactivado_en": r.desactivado_en.isoformat(), "sesiones_revocadas": 0, "advertencias": []}
    texto = json.dumps(filas("select referencia_provision, valor_anterior, valor_nuevo from auditoria where operacion = 'desactivacion_acceso'"), default=str).lower()
    assert CREDENCIAL not in texto and "argon" not in texto and "identificador_acceso" not in texto and "hash" not in texto


# ===================================================== el motivo es obligatorio (P6) ======================================

@pytest.mark.parametrize("motivo", [None, "", "   ", "\t\n "])
def test_el_motivo_es_obligatorio_y_no_puede_estar_vacio(operador, mundo, motivo):
    e = rechaza("CAMPO_OBLIGATORIO", operador, mundo, motivo=motivo)
    assert e.detalles == [{"campo": "motivo", "motivo": "vacio"}] and acceso_de(mundo, "C1") is None


def test_el_motivo_tiene_un_maximo_configurable_y_el_limite_exacto_se_acepta(operador, mundo):
    maximo = get_settings().text_max_description
    rechaza("TEXTO_DEMASIADO_LARGO", operador, mundo, motivo="x" * (maximo + 1))
    desactivar(operador, mundo, "C1", "x" * maximo)
    assert len(entrada()[0][6]) == maximo


# ===================================================== persona inexistente y solicitud repetida ============================

def test_una_persona_inexistente_se_rechaza_sin_cambios(operador, mundo):
    antes = foto()
    with pytest.raises(ErrorDeProvision) as e:
        orden(desactivar_acceso, operador, persona_id=uuid.uuid4(), motivo=MOTIVO)
    assert e.value.codigo == "RECURSO_NO_DISPONIBLE" and e.value.detalles == [{"campo": "persona"}] and foto() == antes


def test_una_solicitud_repetida_se_rechaza_de_forma_explicita_sin_nuevos_cambios_ni_entrada(operador, mundo):
    primera = desactivar(operador, mundo, "C1")
    sesion(mundo, "C1", "tras-la-primera")                 # (preparado por el propietario; la segunda orden no debe tocarla)
    antes = (foto(), filas("select id, revocada_en from sesion order by id"))
    rechaza("ACCESO_YA_DESACTIVADO", operador, mundo, "C1", motivo="Otro motivo")
    assert acceso_de(mundo, "C1") == primera.desactivado_en and len(entrada()) == 1                  # ni la hora ni la auditoría cambian
    assert (foto(), filas("select id, revocada_en from sesion order by id")) == antes
    assert vigentes(mundo, "C1") == 1                                                               # la segunda orden no revocó nada


def test_un_acceso_ya_desactivado_por_otro_medio_tambien_se_rechaza(operador, mundo):
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() - interval '5 days' where id = :p"), {"p": mundo.p["C2"]})
    rechaza("ACCESO_YA_DESACTIVADO", operador, mundo, "C2")


# ===================================================== sesiones ===========================================================

@pytest.fixture()
def con_sesiones(operador, mundo):
    """Cada persona de T y la supervisora con identidad y sesiones: C1 dos vigentes y una ya revocada; C2 una vigente."""
    with get_owner_engine().begin() as c:
        c.execute(text("update identidad set hash_contrasena = 'no-se-usa-en-estas-pruebas' where hash_contrasena is null"))
    for persona, secreto, revocada in (("C1", "c1-a", False), ("C1", "c1-b", False), ("C1", "c1-vieja", True), ("C2", "c2-a", False), ("ST", "st-a", False)):
        sesion(mundo, persona, secreto, revocada)
    return mundo


def test_se_revocan_todas_las_sesiones_vigentes_de_la_persona_y_solo_las_suyas(operador, con_sesiones):
    m = con_sesiones
    vieja = filas("select revocada_en from sesion where secreto_hash = 'c1-vieja'")[0][0]
    r = desactivar(operador, m, "C1")
    assert r.sesiones_revocadas == 2 and vigentes(m, "C1") == 0
    assert filas("select revocada_en from sesion where secreto_hash = 'c1-vieja'")[0][0] == vieja                      # la ya revocada no se reescribe
    assert vigentes(m, "C2") == 1 and vigentes(m, "ST") == 1                                                          # las demás personas no se tocan
    assert entrada()[0][8]["sesiones_revocadas"] == 2


def test_la_revocacion_ocurre_en_el_mismo_instante_de_la_transaccion_que_la_desactivacion(operador, con_sesiones):
    m = con_sesiones
    r = desactivar(operador, m, "C1")
    assert {f[0] for f in filas("select s.revocada_en from sesion s join identidad i on i.id = s.identidad_id where i.persona_id = :p and s.secreto_hash in ('c1-a', 'c1-b')",
                                p=m.p["C1"])} == {r.desactivado_en}


def test_si_la_orden_falla_a_mitad_no_se_desactiva_nada_ni_se_revoca_ninguna_sesion(operador, con_sesiones, monkeypatch):
    m = con_sesiones
    antes = (foto(), filas("select id, revocada_en from sesion order by id"))

    def falla(*a, **k):
        raise RuntimeError("fallo simulado")
    monkeypatch.setattr(acceso, "_auditar", falla)
    with pytest.raises(RuntimeError):
        desactivar(operador, m, "C1")
    assert acceso_de(m, "C1") is None and vigentes(m, "C1") == 2                           # nada se desactivó y las sesiones siguen vigentes
    assert (foto(), filas("select id, revocada_en from sesion order by id")) == antes


# ===================================================== DM-09: equipos pendientes de supervisión efectiva ===================

def test_desactivar_al_unico_supervisor_de_un_equipo_con_colaboradores_no_se_bloquea_y_advierte(operador, mundo):
    antes = foto()
    r = desactivar(operador, mundo, "ST")
    assert acceso_de(mundo, "ST") == r.desactivado_en                                      # la desactivación se aplica (DD-04)
    [a] = r.advertencias
    assert (a.equipo_id, a.equipo, a.colaboradores, a.supervisor_id, a.supervisor_hasta_exclusivo) == (mundo.eq["T"], "T", 2, mundo.p["ST"], None)
    assert a.como_dict() == {"codigo": ADVERTENCIA_EQUIPO_PENDIENTE, "equipo_id": str(mundo.eq["T"]), "equipo": "T", "colaboradores": 2,
                             "supervisor_id": str(mundo.p["ST"]), "supervisor_hasta_exclusivo": None}
    antes.pop("auditoria")
    despues = foto()
    despues.pop("auditoria")
    assert despues == antes                                                                 # no se modifica ninguna pertenencia ni se asigna a nadie


def test_la_advertencia_queda_en_la_auditoria_y_la_pertenencia_historica_se_conserva(operador, mundo):
    r = desactivar(operador, mundo, "ST")
    nuevo = entrada()[0][8]
    assert nuevo["advertencias"] == [r.advertencias[0].como_dict()]
    assert historial(mundo, "ST") == [("T", "supervisor", HOY, None)]                       # la pertenencia (histórica y vigente) es la misma


def test_no_se_asigna_ningun_supervisor_sustituto_ni_se_crea_estado_nuevo(operador, mundo):
    desactivar(operador, mundo, "ST")
    supervisores = filas("select persona_id from pertenencia where equipo_id = :e and rol = 'supervisor' and hasta_exclusivo is null", e=mundo.eq["T"])
    assert supervisores == [(mundo.p["ST"],)]                                               # sigue siendo la misma persona, ahora sin acceso efectivo
    assert {f[0] for f in filas("select column_name from information_schema.columns where table_name = 'equipo'")} == {"id", "organizacion_id", "nombre"}


def test_un_supervisor_con_un_relevo_ya_programado_se_advierte_hoy_e_informa_hasta_cuando(operador, mundo):
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "ST", "X", "supervisor", dia(5)), cambio(mundo, "C1", "T", "supervisor", dia(5))])
    r = desactivar(operador, mundo, "ST")
    assert [a.supervisor_hasta_exclusivo for a in r.advertencias] == [dia(5)]               # hoy está pendiente; desde el día 5 hay otro supervisor asignado


@pytest.mark.parametrize("persona", ["C1", "CU", "SW"])
def test_no_hay_advertencia_si_la_persona_no_es_el_supervisor_de_un_equipo_con_colaboradores(operador, mundo, persona):
    """Un colaborador no deja a nadie sin supervisión; SW supervisa un equipo sin colaboradores (en provisión, IR-32)."""
    assert desactivar(operador, mundo, persona).advertencias == ()
    assert entrada()[0][8]["advertencias"] == []


def test_otro_equipo_se_advierte_por_separado(operador, mundo):
    r = desactivar(operador, mundo, "SU")
    assert [(a.equipo, a.colaboradores) for a in r.advertencias] == [("U", 1)]


def test_la_condicion_se_calcula_a_partir_de_las_reglas_de_supervision_efectiva_solo_para_lo_afectado_por_esta_orden(operador, mundo):
    """Tras desactivar a ST (T queda pendiente), desactivar a un colaborador de T no vuelve a advertir de T."""
    assert len(desactivar(operador, mundo, "ST").advertencias) == 1
    assert desactivar(operador, mundo, "C1").advertencias == ()


def test_un_supervisor_programado_solo_para_el_futuro_no_deja_hoy_a_ningun_equipo_pendiente(operador, mundo):
    """DM-09 se define en la fecha ACTUAL: quien será supervisor mañana no es hoy el supervisor asignado (límite documentado)."""
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "ST", "X", "supervisor", dia(5)), cambio(mundo, "C1", "T", "supervisor", dia(5))])
    assert desactivar(operador, mundo, "C1").advertencias == ()                             # C1 es hoy colaborador, supervisor desde el día 5


def test_el_reloj_inyectable_mueve_la_fecha_actual_de_la_advertencia(operador, mundo):
    """Con «hoy» el día 6, el supervisor asignado de T es C1 (relevo del día 5): desactivar a ST ya no deja a T pendiente."""
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "ST", "X", "supervisor", dia(5)), cambio(mundo, "C1", "T", "supervisor", dia(5))])
    reloj = lambda: datetime.combine(dia(6), time(12), tzinfo=ZoneInfo("America/Bogota")).astimezone(timezone.utc)      # noqa: E731
    assert desactivar(operador, mundo, "ST", reloj=reloj).advertencias == ()
    assert [a.equipo for a in desactivar(operador, mundo, "C1", reloj=reloj).advertencias] == ["T"]


# ===================================================== RA-12, CA-261, CA-256, CA-260 ======================================

def test_ca261_un_equipo_pendiente_no_concede_permisos_de_supervision_a_nadie(operador, mundo):
    with get_owner_engine().begin() as c:
        c.execute(text("insert into bitacora (persona_id, fecha_laboral, resumen) values (:p, :f, 'x')"), {"p": mundo.p["C2"], "f": HOY})
    persona = lambda c: mundo.p[c]   # noqa: E731
    entrada_de_c2 = EntradaDeAuditoria(persona("C2"), HOY, "persona")
    with Session(get_engine()) as db:
        assert consultante_de(db, persona("ST"), hoy=HOY).supervisa(mundo.eq["T"])                                    # antes: ST supervisa T
        assert decidir_lectura_de_auditoria(db, consultante_de(db, persona("ST"), hoy=HOY), entrada_de_c2).visible
    desactivar(operador, mundo, "ST")
    with Session(get_engine()) as db:
        for quien in ("ST", "C1", "C2", "SU", "CU", "SW"):                                                             # después: NADIE supervisa T
            assert not consultante_de(db, persona(quien), hoy=HOY).supervisa(mundo.eq["T"]), quien
        assert decidir_lectura_de_auditoria(db, consultante_de(db, persona("ST"), hoy=HOY), entrada_de_c2).motivo == Motivo.ACCESO_DESACTIVADO
        for colaborador in ("C1", "CU"):                                                                               # los colaboradores solo tienen lectura entre pares, nunca la auditoría ajena
            decision = decidir_lectura_de_auditoria(db, consultante_de(db, persona(colaborador), hoy=HOY), entrada_de_c2)
            assert not decision.visible and decision.motivo in (Motivo.NO_ES_SUPERVISION, Motivo.OTRO_EQUIPO)
    assert historial(mundo, "C1") == [("T", "colaborador", HOY, None)]                                                 # y nadie cambió de rol ni de equipo


def test_ca256_los_registros_y_su_visibilidad_no_cambian_con_la_desactivacion(operador, mundo):
    """El contenido, el equipo histórico y la visibilidad de lo registrado por la persona desactivada son los mismos."""
    with get_owner_engine().begin() as c:
        c.execute(text("insert into bitacora (persona_id, fecha_laboral, resumen) values (:p, :f, 'Trabajo de C1')"), {"p": mundo.p["C1"], "f": HOY})
    persona = lambda c: mundo.p[c]   # noqa: E731

    def matriz():
        with Session(get_engine()) as db:
            leer = lambda quien: decidir_lectura(db, consultante_de(db, persona(quien), hoy=HOY), Registro(persona("C1"), HOY))   # noqa: E731
            return {q: (leer(q).visible, leer(q).motivo) for q in ("C2", "ST", "CU", "SU")}, pertenencias.equipo_en_fecha(db, persona("C1"), HOY)

    visibles_antes, equipo_antes = matriz()
    registros = filas("select b::text from bitacora b")
    desactivar(operador, mundo, "C1")
    visibles_despues, equipo_despues = matriz()
    assert (visibles_despues, equipo_despues) == (visibles_antes, equipo_antes)
    assert filas("select b::text from bitacora b") == registros
    assert visibles_despues["C2"] == (True, Motivo.EQUIPO_HISTORICO) and visibles_despues["CU"][0] is False
    with Session(get_engine()) as db:   # la propia persona desactivada ya no opera ni consulta (IR-37)
        assert decidir_lectura(db, consultante_de(db, persona("C1"), hoy=HOY), Registro(persona("C1"), HOY)).motivo == Motivo.ACCESO_DESACTIVADO


def test_ca260_la_persona_conserva_su_pertenencia_historica_y_sigue_siendo_una_persona_del_equipo(operador, mundo):
    antes = filas("select * from pertenencia where persona_id = :p", p=mundo.p["ST"])
    desactivar(operador, mundo, "ST")
    assert filas("select * from pertenencia where persona_id = :p", p=mundo.p["ST"]) == antes
    with Session(get_engine()) as db:
        assert pertenencias.equipo_en_fecha(db, mundo.p["ST"], HOY) == mundo.eq["T"]


def test_una_transaccion_iniciada_antes_de_la_desactivacion_la_ve_en_cuanto_se_confirma(operador, mundo):
    """IR-37 «desde ese momento»: la comprobación del acceso usa el instante real, no el inicio de la transacción. Un inicio de sesión
    que empezó antes (verificando la contraseña, con Argon2) y espera su turno debe ver la desactivación ya confirmada."""
    from app.compartido.politica_acceso import contexto_de_operacion
    from app.errores import AppError
    with Session(get_engine()) as db:
        db.execute(text("select 1"))                                   # la transacción empieza AQUÍ, antes de la desactivación
        desactivar(operador, mundo, "C1")                              # otra transacción la desactiva y la confirma después
        with pytest.raises(AppError) as e:
            contexto_de_operacion(db, mundo.p["C1"])                   # con now() (inicio de la transacción) esto NO la vería
        assert e.value.codigo == "ACCESO_DESACTIVADO"


# ===================================================== autorización =======================================================

def test_la_aplicacion_no_puede_ejecutar_la_orden_aunque_se_llame_al_caso_de_uso(operador, con_sesiones):
    m = con_sesiones
    antes = (foto(), filas("select id, revocada_en from sesion order by id"))
    with pytest.raises(DBAPIError) as e, get_engine().begin() as c:
        desactivar_acceso(c, operador, persona_id=m.p["C1"], motivo=MOTIVO)
    assert e.value.orig.sqlstate == "42501" and (foto(), filas("select id, revocada_en from sesion order by id")) == antes
    assert acceso_de(m, "C1") is None and vigentes(m, "C1") == 2


# ===================================================== concurrencia =======================================================

def test_dos_desactivaciones_simultaneas_de_la_misma_persona_dejan_una_efectiva_y_una_sola_entrada(operador, con_sesiones):
    m = con_sesiones
    resultados = []

    def ejecutar():
        try:
            orden(desactivar_acceso, operador, persona_id=m.p["C1"], motivo=MOTIVO)
            resultados.append("aceptada")
        except ErrorDeProvision as e:
            resultados.append(e.codigo)

    hilos = [threading.Thread(target=ejecutar) for _ in range(6)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(60)
    assert sorted(resultados) == ["ACCESO_YA_DESACTIVADO"] * 5 + ["aceptada"]
    assert len(entrada()) == 1 and vigentes(m, "C1") == 0


def test_una_desactivacion_sin_confirmar_hace_esperar_a_un_traslado_de_la_misma_persona_y_no_se_estorban(operador, mundo):
    """Desactivar y trasladar a la misma persona comparten bloqueos en el mismo orden: no hay bloqueo mutuo y ambas se completan."""
    resultado = {}
    conexion = get_provision_engine().connect()
    try:
        desactivar_acceso(conexion, operador, persona_id=mundo.p["C1"], motivo=MOTIVO)             # sin confirmar

        def trasladar():
            try:
                orden(registrar_traslado, operador, cambios=[cambio(mundo, "C1", "U", "colaborador", dia(3))])
                resultado["traslado"] = "aceptada"
            except ErrorDeProvision as e:
                resultado["traslado"] = e.codigo

        hilo = threading.Thread(target=trasladar)
        hilo.start()
        assert _esperar_bloqueo_consultivo(), "el traslado debía esperar el bloqueo de la persona"
        conexion.commit()
    finally:
        conexion.close()
    hilo.join(30)
    assert resultado == {"traslado": "aceptada"}                                                   # una persona sin acceso puede trasladarse (DD-04)
    assert historial(mundo, "C1")[-1] == ("U", "colaborador", dia(3), None) and acceso_de(mundo, "C1") is not None


def test_las_ordenes_sobre_personas_distintas_no_se_estorban(operador, mundo):
    resultados = []

    def ejecutar(persona):
        try:
            desactivar(operador, mundo, persona)
            resultados.append("aceptada")
        except ErrorDeProvision as e:
            resultados.append(e.codigo)

    hilos = [threading.Thread(target=ejecutar, args=(p,)) for p in ("C1", "C2", "ST", "SU", "CU", "SW")]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(60)
    assert resultados == ["aceptada"] * 6 and contar("auditoria") >= 6
    assert len(entrada()) == 6
