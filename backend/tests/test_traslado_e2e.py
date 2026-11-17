"""M1-T5 — recorrido de extremo a extremo de un TRASLADO OFICIAL (M1-05): CA-212, CA-213 y CA-214, con las operaciones de M2 y M3.

Qué es real: PostgreSQL, la CLI de provisión (``crear-equipo``, ``crear-persona``, ``registrar-traslado``, ``cancelar-operacion-programada``,
con el rol de provisión y una persona operadora), la API HTTP de M2 y M3 con sesiones reales y la política de visibilidad de M1-T1.
Las pertenencias NO se tocan nunca por SQL: el traslado se registra con la orden oficial, con fecha efectiva futura.

El tiempo (el único mecanismo de prueba, aislado y justificado): las operaciones de M2 y M3 toman «hoy» de UNA sola función de
producción, ``politica_acceso.fecha_actual_en`` (zona horaria de la organización). Para vivir el día en que el traslado ya es efectivo,
la prueba sustituye esa función con ``monkeypatch`` (solo dentro del proceso de la prueba, y se restaura sola). No se cambia el reloj
del sistema ni se toca el de PostgreSQL (que sigue protegiendo la edición de pertenencias efectivas), las sesiones y la idempotencia
siguen usando el reloj real y ningún código de producción cambia. Lo único preparado fuera de las órdenes de provisión es la
contraseña de las personas de prueba (el primer acceso, M1-03, no existe todavía).

Qué NO prueba: visibilidad entre personas por HTTP (M4: los registros ajenos responden 404 provisional) ni la clase «planificación
conservada» (DM-08) en las vistas de M2. La política de visibilidad se comprueba a nivel de dominio. Las pruebas destructivas
corren solo sobre ``smartwork_test``.
"""

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.compartido import pertenencias, politica_acceso
from app.compartido.visibilidad import Registro, consultante_de, decidir_lectura
from app.db import get_engine, get_owner_engine
from app.seguridad.contrasenas import calcular_hash
from scripts.verificar_datos import estados_actuales_incoherentes as _incoherentes
from tests.fabricas import hoy
from tests.test_provision_cli import ejecutar, instalada  # noqa: F401  (fixture ``instalada``: persona operadora y organización)
from tests.utiles_http import API, cabeceras, iniciar_sesion, nuevo_cliente
from tests.utiles_m2 import avanzar, con_clave, contar, filas, planificar_actividad

D0 = hoy()                                   # hoy (real) en la zona de la organización
F = D0 + timedelta(days=2)                   # fecha efectiva del traslado: posterior a hoy, como exige IR-30
CONTRASENA = "contraseña-de-prueba-123"
TABLAS_M2 = ("bitacora", "actividad", "planificacion", "avance")


def iso(fecha) -> str:
    return fecha.isoformat()


@dataclass
class Sesion:
    cliente: object
    csrf: str


@dataclass
class Mundo:
    equipos: dict
    personas: dict
    reloj: dict
    sesiones: dict = field(default_factory=dict)
    actividad: str = ""
    avances: list = field(default_factory=list)

    def entrar(self, clave: str) -> Sesion:
        cliente = nuevo_cliente()
        r = iniciar_sesion(cliente, f"{clave.lower()}.t5", CONTRASENA)
        assert r.status_code == 201, r.text
        self.sesiones[clave] = Sesion(cliente, r.json()["csrf_token"])
        return self.sesiones[clave]

    def hoy_es(self, fecha):
        self.reloj["hoy"] = fecha


def cli(*argv):
    codigo, salida, error = ejecutar(list(argv))
    assert codigo == 0, error
    return json.loads(salida)


def estados_actuales_incoherentes():
    with get_owner_engine().connect() as c:
        return _incoherentes(c)


def snapshot_m2():
    return {t: filas(f"select x::text from {t} x order by x.id") for t in TABLAS_M2}


def snapshot_pertenencias():
    return filas("select id, persona_id, equipo_id, rol, desde, hasta_exclusivo from pertenencia order by id")


@pytest.fixture()
def mundo(instalada, monkeypatch):
    """Provisión oficial por la CLI: equipo T (supervisora ST; P y Q) y equipo U (supervisor SU; R). El reloj de la aplicación marca hoy."""
    reloj = {"hoy": D0}
    monkeypatch.setattr(politica_acceso, "fecha_actual_en", lambda zona: reloj["hoy"])
    op = ["--operador", instalada["operador"]]
    equipos = {n: cli("crear-equipo", *op, "--organizacion", str(instalada["org"]), "--nombre", n)["equipo_id"] for n in ("T", "U")}
    personas = {}
    for clave, equipo, rol in (("ST", "T", "supervisor"), ("P", "T", "colaborador"), ("Q", "T", "colaborador"), ("SU", "U", "supervisor"), ("R", "U", "colaborador")):
        personas[clave] = cli("crear-persona", *op, "--nombre", f"Persona {clave}", "--identificador-acceso", f"{clave.lower()}.t5",
                              "--equipo", equipos[equipo], "--rol", rol, "--desde", iso(D0))["persona_id"]
    with get_owner_engine().begin() as c:   # solo la contraseña: el primer acceso (M1-03) no existe todavía; ninguna pertenencia se toca
        c.execute(text("update identidad set hash_contrasena = :h"), {"h": calcular_hash(CONTRASENA)})
    m = Mundo(equipos, personas, reloj)
    m.operador = instalada["operador"]
    return m


def trabajo_en_t(m: Mundo, cerrar: bool = True) -> Mundo:
    """Fase 1 (hoy = D0, P en T): P abre su bitácora, planifica una actividad, registra DOS avances, planifica una continuación para el
    día F (todavía en T, la pertenencia programada cubre esa fecha), guarda su resumen y, si ``cerrar``, cierra la jornada (M3-01).
    Una jornada cerrada no admite más avances (``BITACORA_CERRADA``): las pruebas que siguen registrando en D0 no la cierran."""
    p = m.entrar("P")
    m.actividad = planificar_actividad(p.cliente, p.csrf, iso(D0), "Informe trimestral")
    for estado, descripcion, motivo in (("En progreso", "Primer borrador", None), ("Bloqueada", "Espero las cifras", "Faltan cifras del área")):
        r = avanzar(p.cliente, p.csrf, m.actividad, iso(D0), estado, descripcion, motivo)
        assert r.status_code == 201, r.text
        m.avances.append(r.json()["avance"]["id"])
    r = p.cliente.post(f"{API}/mi/actividades/{m.actividad}/continuaciones-planificadas", headers=con_clave(p.csrf),
                       json={"fecha_laboral": iso(F), "descripcion": "Seguir con el equipo nuevo"})
    assert r.status_code == 201, r.text
    assert p.cliente.put(f"{API}/mi/bitacoras/{iso(D0)}/resumen", json={"resumen": "Avancé con el informe"}, headers=cabeceras(p.csrf)).status_code == 200
    if cerrar:
        assert p.cliente.post(f"{API}/mi/bitacoras/{iso(D0)}/cierre", headers=con_clave(p.csrf)).status_code == 200
    return m


def trasladar(m: Mundo, fecha=F):
    return cli("registrar-traslado", "--operador", m.operador, "--cambio", f"{m.personas['P']}:{m.equipos['U']}:colaborador:{iso(fecha)}")


@pytest.fixture()
def tras_el_traslado(mundo):
    """Hasta aquí: trabajo en T, traslado OFICIAL a U con efecto en F y reloj de la aplicación en F (el traslado ya es efectivo)."""
    trabajo_en_t(mundo)
    mundo.antes = {"m2": snapshot_m2(), "pertenencias": snapshot_pertenencias()}
    trasladar(mundo)
    mundo.despues_del_traslado = snapshot_pertenencias()
    mundo.hoy_es(F)
    return mundo


def actividad_de(m: Mundo, sesion: Sesion):
    r = sesion.cliente.get(f"{API}/mi/actividades/{m.actividad}")
    assert r.status_code == 200, r.text
    return r.json()


# ===================================================== el traslado y el estado previo ======================================

def test_el_traslado_oficial_cierra_la_pertenencia_en_t_y_abre_la_de_u_sin_tocar_los_registros_de_m2(mundo):
    trabajo_en_t(mundo)
    antes_m2 = snapshot_m2()
    r = trasladar(mundo)
    assert r["cambios"][0]["tipo"] == "traslado" and r["historiales"][0]["pertenencias"][-1]["desde"] == iso(F)
    assert filas("select e.nombre, p.desde, p.hasta_exclusivo from pertenencia p join equipo e on e.id = p.equipo_id where p.persona_id = :p order by p.desde",
                 p=uuid.UUID(mundo.personas["P"])) == [("T", D0, F), ("U", F, None)]
    assert snapshot_m2() == antes_m2                                                  # la provisión no escribe en M2 ni en M3


def test_antes_de_la_fecha_efectiva_la_persona_sigue_en_t_aunque_el_traslado_ya_este_registrado(mundo):
    p = trabajo_en_t(mundo, cerrar=False).sesiones["P"]
    trasladar(mundo)
    with Session(get_engine()) as db:
        assert pertenencias.equipo_en_fecha(db, uuid.UUID(mundo.personas["P"]), D0) == uuid.UUID(mundo.equipos["T"])
        assert pertenencias.equipo_en_fecha(db, uuid.UUID(mundo.personas["P"]), F) == uuid.UUID(mundo.equipos["U"])
    r = avanzar(p.cliente, p.csrf, mundo.actividad, iso(D0), "En progreso", "Sigo hoy en T")          # hoy (D0): la jornada de hoy es de T (CA-249)
    assert r.status_code == 201, r.text


# ===================================================== CA-212 ==============================================================

def test_ca212_la_actividad_iniciada_en_t_sigue_siendo_la_misma_y_de_su_propietaria_tras_pasar_a_u(tras_el_traslado):
    m = tras_el_traslado
    p = m.sesiones["P"]
    with Session(get_engine()) as db:
        assert pertenencias.pertenencia_en_fecha(db, uuid.UUID(m.personas["P"]), F).equipo_id == uuid.UUID(m.equipos["U"])      # ya está en U
    vista = actividad_de(m, p)
    assert vista["actividad"]["id"] == m.actividad and vista["estado_actual"] == "Bloqueada"
    fila = filas("select propietaria_id, origen, bitacora_origen_id from actividad where id = :a", a=m.actividad)[0]
    assert fila.propietaria_id == uuid.UUID(m.personas["P"]) and fila.origen == "planificada"
    assert filas("select fecha_laboral from bitacora where id = :b", b=fila.bitacora_origen_id) == [(D0,)]               # origen: la jornada de T
    assert contar("actividad") == 1
    assert snapshot_m2() == m.antes["m2"]                                              # el traslado no reescribió ningún registro


def test_ca212_el_equipo_historico_de_la_actividad_sigue_siendo_t_y_el_actual_de_su_propietaria_es_u(tras_el_traslado):
    m = tras_el_traslado
    with Session(get_engine()) as db:
        origen = filas("select b.fecha_laboral from actividad a join bitacora b on b.id = a.bitacora_origen_id where a.id = :a", a=m.actividad)[0][0]
        assert pertenencias.equipo_en_fecha(db, uuid.UUID(m.personas["P"]), origen) == uuid.UUID(m.equipos["T"])
        assert pertenencias.equipo_en_fecha(db, uuid.UUID(m.personas["P"]), F) == uuid.UUID(m.equipos["U"])


# ===================================================== CA-213 ==============================================================

def test_ca213_un_avance_registrado_en_u_no_crea_otra_actividad(tras_el_traslado):
    m = tras_el_traslado
    p = m.sesiones["P"]
    n_actividades, n_planificaciones = contar("actividad"), contar("planificacion")
    r = avanzar(p.cliente, p.csrf, m.actividad, iso(F), "En progreso", "Retomo el informe en el equipo nuevo")
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["actividad"]["id"] == m.actividad and cuerpo["avance"]["fecha_laboral"] == iso(F)
    assert contar("actividad") == n_actividades == 1 and contar("planificacion") == n_planificaciones      # misma actividad, nada nuevo que planificar
    nuevo = filas("select a.actividad_id, b.fecha_laboral, b.persona_id from avance a join bitacora b on b.id = a.bitacora_id where a.id = :i", i=cuerpo["avance"]["id"])[0]
    assert (nuevo.actividad_id, nuevo.fecha_laboral, nuevo.persona_id) == (uuid.UUID(m.actividad), F, uuid.UUID(m.personas["P"]))
    with Session(get_engine()) as db:   # el avance pertenece a una jornada que, por su fecha, es del equipo U
        assert pertenencias.equipo_en_fecha(db, uuid.UUID(m.personas["P"]), nuevo.fecha_laboral) == uuid.UUID(m.equipos["U"])


def test_ca213_el_avance_en_u_se_valida_con_las_mismas_reglas_de_la_actividad(tras_el_traslado):
    """Es la MISMA actividad con sus reglas: estado válido, motivo de bloqueo, fecha no futura y secuencia (M2-05)."""
    m = tras_el_traslado
    p = m.sesiones["P"]
    assert avanzar(p.cliente, p.csrf, m.actividad, iso(F), "Bloqueada", "Sin motivo").status_code == 422                      # Bloqueada exige motivo
    assert avanzar(p.cliente, p.csrf, m.actividad, iso(F + timedelta(days=1)), "En progreso", "Mañana").status_code == 422      # fecha futura
    assert contar("avance") == 2                                                                                           # los rechazos no dejan nada


# ===================================================== CA-214 ==============================================================

def test_ca214_la_propietaria_ve_en_u_todos_los_avances_de_la_actividad_los_de_t_y_los_de_u(tras_el_traslado):
    m = tras_el_traslado
    p = m.sesiones["P"]
    assert avanzar(p.cliente, p.csrf, m.actividad, iso(F), "En progreso", "Retomo en U").status_code == 201
    assert avanzar(p.cliente, p.csrf, m.actividad, iso(F), "Completada", "Entregado desde U").status_code == 201
    vista = actividad_de(m, p)
    secuencia = [(a["fecha_laboral"], a["estado"], a["descripcion"]) for a in vista["avances"]]
    assert secuencia == [(iso(D0), "En progreso", "Primer borrador"), (iso(D0), "Bloqueada", "Espero las cifras"),
                         (iso(F), "En progreso", "Retomo en U"), (iso(F), "Completada", "Entregado desde U")]
    assert vista["estado_actual"] == "Completada"
    assert [c["fecha_laboral"] for c in vista["continuaciones_planificadas"]] == [iso(F)]                    # la continuación planificada desde T sigue ahí
    assert estados_actuales_incoherentes() == []                                                              # el estado actual derivado coincide


def test_ca214_la_actividad_aparece_una_sola_vez_en_el_listado_con_su_estado_actual(tras_el_traslado):
    m = tras_el_traslado
    p = m.sesiones["P"]
    assert avanzar(p.cliente, p.csrf, m.actividad, iso(F), "En progreso", "Retomo en U").status_code == 201
    r = p.cliente.get(f"{API}/mi/actividades")
    assert r.status_code == 200
    elementos = [e for e in r.json()["elementos"] if e["id"] == m.actividad]
    assert len(elementos) == 1 and elementos[0]["estado_actual"] == "En progreso"


# ===================================================== FECHA_NO_CUBIERTA y restricciones de pertenencia ====================

def test_una_fecha_anterior_a_la_primera_pertenencia_no_esta_cubierta_ni_antes_ni_despues_del_traslado(tras_el_traslado):
    m = tras_el_traslado
    p = m.sesiones["P"]
    r = avanzar(p.cliente, p.csrf, m.actividad, iso(D0 - timedelta(days=1)), "En progreso", "Antes de empezar")
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_NO_CUBIERTA"
    r = p.cliente.post(f"{API}/mi/bitacoras/{iso(D0 - timedelta(days=1))}/planificaciones", json={"titulo": "Antes"}, headers=con_clave(p.csrf))
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_NO_CUBIERTA"
    with Session(get_engine()) as db:
        assert pertenencias.pertenencia_en_fecha(db, uuid.UUID(m.personas["P"]), D0 - timedelta(days=1)) is None


def test_no_hay_ni_huecos_ni_solapes_las_dos_pertenencias_cubren_cada_fecha_desde_el_inicio(tras_el_traslado):
    """La frontera es exacta: el último día de T es F-1 y el primero de U es F, y las dos fechas admiten registros."""
    m = tras_el_traslado
    p = m.sesiones["P"]
    assert avanzar(p.cliente, p.csrf, m.actividad, iso(F), "En progreso", "Primer día en U").status_code == 201
    with Session(get_engine()) as db:
        persona = uuid.UUID(m.personas["P"])
        assert pertenencias.equipo_en_fecha(db, persona, F - timedelta(days=1)) == uuid.UUID(m.equipos["T"])
        assert pertenencias.equipo_en_fecha(db, persona, F) == uuid.UUID(m.equipos["U"])
    # un avance retroactivo de la jornada intermedia (de T) hecho desde U se acepta: esa fecha está cubierta por la pertenencia de T
    r = avanzar(p.cliente, p.csrf, m.actividad, iso(F - timedelta(days=1)), "En progreso", "Aclaración retroactiva de un día de T")
    assert r.status_code == 201, r.text
    assert filas("select b.fecha_laboral from avance a join bitacora b on b.id = a.bitacora_id where a.id = :i", i=r.json()["avance"]["id"]) == [(F - timedelta(days=1),)]


def test_el_traslado_cancelado_antes_de_su_fecha_efectiva_deja_a_la_persona_trabajando_en_t_en_esa_fecha(mundo):
    """CA-244 con M2: se cancela el traslado (M1-07) y, llegado F, la persona sigue en T con la misma actividad."""
    trabajo_en_t(mundo)
    trasladar(mundo)
    r = cli("cancelar-operacion-programada", "--operador", mundo.operador, "--cancelar", f"{mundo.personas['P']}:traslado:{iso(F)}")
    assert r["operacion"] == "cancelacion_operacion"
    mundo.hoy_es(F)
    p = mundo.sesiones["P"]
    assert avanzar(p.cliente, p.csrf, mundo.actividad, iso(F), "En progreso", "Sigo en T").status_code == 201
    with Session(get_engine()) as db:
        assert pertenencias.equipo_en_fecha(db, uuid.UUID(mundo.personas["P"]), F) == uuid.UUID(mundo.equipos["T"])
    assert contar("actividad") == 1


def test_un_traslado_rechazado_no_cambia_nada_y_la_persona_sigue_operando(mundo):
    trabajo_en_t(mundo, cerrar=False)
    antes = (snapshot_pertenencias(), snapshot_m2(), contar("auditoria"))
    codigo, _, error = ejecutar(["registrar-traslado", "--operador", mundo.operador, "--cambio", f"{mundo.personas['P']}:{mundo.equipos['U']}:colaborador:{iso(D0)}"])
    assert codigo == 2 and json.loads(error)["error"] == "FECHA_EFECTIVA_INVALIDA"                  # hoy no es futuro
    assert (snapshot_pertenencias(), snapshot_m2(), contar("auditoria")) == antes
    p = mundo.sesiones["P"]
    assert avanzar(p.cliente, p.csrf, mundo.actividad, iso(D0), "En progreso", "Sigo").status_code == 201


# ===================================================== autorización antes y después =======================================

@pytest.mark.parametrize("quien", ["Q", "R", "ST", "SU"])
def test_ninguna_otra_persona_accede_a_la_actividad_ni_antes_ni_despues_del_traslado(mundo, quien):
    """404 provisional de M2 y M3 hasta M4 (T-01): ni el equipo de origen, ni el de destino, ni sus supervisoras la consultan o la modifican."""
    trabajo_en_t(mundo)
    ajena = mundo.entrar(quien)

    def comprobar():
        assert ajena.cliente.get(f"{API}/mi/actividades/{mundo.actividad}").status_code == 404
        assert avanzar(ajena.cliente, ajena.csrf, mundo.actividad, iso(mundo.reloj["hoy"]), "En progreso", "Intruso").status_code == 404
        assert ajena.cliente.get(f"{API}/auditoria", params={"tipo_objeto": "actividad", "objeto_id": mundo.actividad}).status_code == 404

    comprobar()                                                  # antes del traslado
    trasladar(mundo)
    mundo.hoy_es(F)
    comprobar()                                                  # después de que el traslado es efectivo
    assert contar("avance") == 2


def test_la_propietaria_conserva_el_acceso_completo_a_lo_suyo_antes_y_despues(tras_el_traslado):
    m = tras_el_traslado
    p = m.sesiones["P"]
    assert p.cliente.get(f"{API}/mi/actividades/{m.actividad}").status_code == 200
    assert p.cliente.get(f"{API}/mi/bitacoras/{iso(D0)}").status_code == 200            # la jornada de T, ya cerrada
    sesion = p.cliente.get(f"{API}/sesion").json()
    assert sesion["fecha_actual"] == iso(F) and sesion["rol_vigente"] == "colaborador"


def test_la_politica_de_visibilidad_de_m1_t1_decide_por_el_equipo_de_cada_fecha_antes_y_despues_del_traslado(tras_el_traslado):
    """Nivel de DOMINIO (no hay endpoint hasta M4): quién puede leer las jornadas de P según el equipo en cada fecha."""
    m = tras_el_traslado
    p = m.sesiones["P"]
    assert avanzar(p.cliente, p.csrf, m.actividad, iso(F), "En progreso", "Retomo en U").status_code == 201
    persona = lambda c: uuid.UUID(m.personas[c])    # noqa: E731
    with Session(get_engine()) as db:
        def lee(quien, fecha, hoy_):
            return decidir_lectura(db, consultante_de(db, persona(quien), hoy=hoy_), Registro(persona("P"), fecha)).visible
        for hoy_ in (D0, F):                                                         # antes (D0) y después (F) del traslado
            assert lee("Q", D0, hoy_) and lee("ST", D0, hoy_)                         # la jornada de T sigue siendo del equipo T
            assert not lee("R", D0, hoy_) and not lee("SU", D0, hoy_)                 # y no del equipo U
        assert lee("R", F, F) and lee("SU", F, F) and not lee("Q", F, F) and not lee("ST", F, F)   # la jornada de F es del equipo U
        assert lee("P", D0, F) and lee("P", F, F)                                    # la propietaria lee todo lo suyo


def test_una_persona_finalizada_no_consulta_sus_registros_tras_la_fecha_efectiva_pero_estos_y_su_propiedad_se_conservan(mundo):
    """IR-38 (decisión 8 de M1-T4): sin pertenencia vigente no se consulta nada, ni lo propio; nada se elimina ni cambia de propietaria."""
    trabajo_en_t(mundo)
    p = mundo.sesiones["P"]
    cli("finalizar-pertenencia", "--operador", mundo.operador, "--finalizar", f"{mundo.personas['P']}:{iso(F)}")
    antes = snapshot_m2()
    mundo.hoy_es(F - timedelta(days=1))                                               # el último día de pertenencia: todavía opera y consulta
    assert p.cliente.get(f"{API}/mi/actividades/{mundo.actividad}").status_code == 200
    mundo.hoy_es(F)                                                                    # desde la fecha efectiva ya no tiene pertenencia vigente
    for respuesta in (p.cliente.get(f"{API}/mi/actividades/{mundo.actividad}"), p.cliente.get(f"{API}/mi/bitacoras/{iso(D0)}"),
                      avanzar(p.cliente, p.csrf, mundo.actividad, iso(F), "En progreso", "Ya no")):
        assert respuesta.status_code == 403 and respuesta.json()["codigo"] == "SIN_PERTENENCIA_VIGENTE"
    assert snapshot_m2() == antes                                                      # ningún registro se eliminó ni cambió
    assert filas("select propietaria_id from actividad where id = :a", a=mundo.actividad) == [(uuid.UUID(mundo.personas["P"]),)]
    assert filas("select hasta_exclusivo from pertenencia where persona_id = :p", p=uuid.UUID(mundo.personas["P"])) == [(F,)]


# ===================================================== M3 tras el traslado ================================================

def test_las_operaciones_de_m3_tras_el_traslado_son_de_la_propietaria_y_quedan_auditadas_con_sus_fechas_laborales(tras_el_traslado):
    """Reabrir la jornada de T (cerrada antes del traslado), corregir un avance de T y cerrar una jornada de U, todo desde U."""
    m = tras_el_traslado
    p = m.sesiones["P"]
    persona = uuid.UUID(m.personas["P"])
    bitacora_t = filas("select id from bitacora where persona_id = :p and fecha_laboral = :f", p=persona, f=D0)[0][0]
    assert p.cliente.post(f"{API}/mi/bitacoras/{iso(D0)}/reapertura", json={"motivo": "Corregir un avance de la jornada en T"}, headers=con_clave(p.csrf)).status_code == 200
    r = p.cliente.patch(f"{API}/mi/avances/{m.avances[0]}", json={"descripcion": "Primer borrador (corregido desde U)"}, headers=con_clave(p.csrf))
    assert r.status_code == 200, r.text
    nuevo = planificar_actividad(p.cliente, p.csrf, iso(F), "Trabajo en U")
    assert p.cliente.put(f"{API}/mi/bitacoras/{iso(F)}/resumen", json={"resumen": "Primer día en U"}, headers=cabeceras(p.csrf)).status_code == 200
    assert p.cliente.post(f"{API}/mi/bitacoras/{iso(F)}/cierre", headers=con_clave(p.csrf)).status_code == 200

    historial = p.cliente.get(f"{API}/auditoria", params={"tipo_objeto": "bitacora", "objeto_id": str(bitacora_t)}).json()["elementos"]
    assert [e["operacion"] for e in historial] == ["cierre", "reapertura"]                  # el cierre hecho en T y la reapertura hecha desde U
    assert {e["autor_persona_id"] for e in historial} == {m.personas["P"]} and {e["tipo_autor"] for e in historial} == {"persona"}
    assert {e["fecha_laboral_registro"] for e in historial} == {iso(D0)}                    # la fecha laboral NO es la del día real de la operación
    assert historial[0]["momento"] < historial[1]["momento"]
    correcciones = p.cliente.get(f"{API}/auditoria", params={"tipo_objeto": "avance", "objeto_id": m.avances[0]}).json()["elementos"]
    assert [e["operacion"] for e in correcciones] == ["correccion"] and correcciones[0]["fecha_laboral_registro"] == iso(D0)
    assert correcciones[0]["valor_anterior"]["avance"] == {"descripcion": "Primer borrador"}
    assert correcciones[0]["valor_nuevo"]["avance"] == {"descripcion": "Primer borrador (corregido desde U)"}
    # el avance corregido conserva su fecha laboral, su momento y su orden; el estado actual no cambia
    fila = filas("select b.fecha_laboral, a.estado, a.descripcion from avance a join bitacora b on b.id = a.bitacora_id where a.id = :i", i=m.avances[0])[0]
    assert (fila.fecha_laboral, fila.estado) == (D0, "En progreso") and fila.descripcion.endswith("(corregido desde U)")
    assert actividad_de(m, p)["estado_actual"] == "Bloqueada"
    assert estados_actuales_incoherentes() == [] and nuevo


def test_las_entradas_de_provision_del_traslado_existen_pero_ninguna_persona_las_consulta_por_la_api(tras_el_traslado):
    m = tras_el_traslado
    p = m.sesiones["P"]
    entrada = filas("select tipo_autor, referencia_provision, operacion, propietaria_registro_id from auditoria where operacion = 'cambio_pertenencia'")
    assert len(entrada) == 1 and entrada[0][0] == "provision" and entrada[0][1].startswith(f"operador:{m.operador}|") and entrada[0][3] is None
    persona = uuid.UUID(m.personas["P"])
    bitacora_t = filas("select id from bitacora where persona_id = :p and fecha_laboral = :f", p=persona, f=D0)[0][0]
    for tipo, objeto in (("bitacora", str(bitacora_t)), ("actividad", m.actividad), ("avance", m.avances[0])):
        elementos = p.cliente.get(f"{API}/auditoria", params={"tipo_objeto": tipo, "objeto_id": objeto}).json()["elementos"]
        assert all(e["tipo_autor"] == "persona" for e in elementos)                       # D-11: la provisión no se muestra


# ===================================================== no se reescribe nada =================================================

def test_nada_historico_se_reescribe_las_pertenencias_efectivas_y_los_registros_de_t_quedan_intactos(tras_el_traslado):
    """Tras TODO el trabajo en U (avances, retroactivo, cierre), las dos pertenencias y los registros de la jornada de T no cambian."""
    m = tras_el_traslado
    p = m.sesiones["P"]
    assert avanzar(p.cliente, p.csrf, m.actividad, iso(F), "En progreso", "Retomo en U").status_code == 201
    assert avanzar(p.cliente, p.csrf, m.actividad, iso(F), "Completada", "Terminado").status_code == 201
    assert snapshot_pertenencias() == m.despues_del_traslado                              # ni una pertenencia reescrita por la actividad de M2
    for tabla in ("avance", "planificacion"):                                             # los registros de T siguen idénticos, solo se añade lo nuevo
        antes = set(map(tuple, m.antes["m2"][tabla]))
        assert antes <= set(map(tuple, filas(f"select x::text from {tabla} x order by x.id")))
    bitacora_t = filas("select b::text from bitacora b where fecha_laboral = :f and persona_id = :p", f=D0, p=uuid.UUID(m.personas["P"]))
    assert tuple(bitacora_t[0]) in set(map(tuple, m.antes["m2"]["bitacora"]))
    auditoria_previa = filas("select id from auditoria where operacion in ('cierre') order by id")
    assert len(auditoria_previa) == 1


# ===================================================== concurrencia y atomicidad ==========================================

def test_un_avance_y_un_traslado_simultaneos_se_completan_los_dos_y_el_resultado_es_consistente(mundo):
    """El avance (hoy, jornada de T) y la orden de traslado (fecha efectiva futura) no se estorban: se aceptan ambos."""
    trabajo_en_t(mundo, cerrar=False)
    p = mundo.sesiones["P"]
    resultados = {}

    def avance():
        resultados["avance"] = avanzar(p.cliente, p.csrf, mundo.actividad, iso(D0), "En progreso", "Mientras se traslada").status_code

    def traslado():
        try:
            resultados["traslado"] = trasladar(mundo)["cambios"][0]["tipo"]
        except AssertionError as e:   # un fallo de la CLI se vería aquí
            resultados["traslado"] = str(e)

    hilos = [threading.Thread(target=avance), threading.Thread(target=traslado)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(60)
    assert resultados == {"avance": 201, "traslado": "traslado"}
    assert contar("avance") == 3 and contar("actividad") == 1
    assert filas("select count(*) from pertenencia where persona_id = :p", p=uuid.UUID(mundo.personas["P"])) == [(2,)]
    mundo.hoy_es(F)
    assert avanzar(p.cliente, p.csrf, mundo.actividad, iso(F), "En progreso", "Ya en U").status_code == 201
    assert estados_actuales_incoherentes() == []
