"""M1-T6 — la desactivación del acceso vista desde la API HTTP real (FastAPI + PostgreSQL) con la CLI de provisión real.

Criterios: CA-255 (ninguna operación autenticada desde la desactivación: ni las de sesiones ya emitidas ni los nuevos inicios), CA-256
(los registros y su visibilidad no cambian), CA-260 y CA-261 (el único supervisor se puede desactivar y nadie hereda su supervisión).
Se comprueban además las reglas existentes de CSRF y origen y que una carrera entre el inicio de sesión y la desactivación no deja
ninguna sesión válida. Las pruebas destructivas corren solo sobre ``smartwork_test``.
"""

import json
import threading
import time
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.db import get_engine, get_owner_engine, get_provision_engine
from app.provision.acceso import desactivar_acceso
from app.provision.operadores import identificar
from app.seguridad.contrasenas import calcular_hash
from tests.fabricas import hoy
from tests.test_provision_cli import ejecutar, instalada  # noqa: F401  (fixture ``instalada``: persona operadora y organización)
from tests.test_traslados import _esperar_bloqueo_consultivo
from tests.utiles_http import API, cabeceras, iniciar_sesion, nuevo_cliente
from tests.utiles_m2 import avanzar, con_clave, contar, filas, planificar_actividad

D0 = hoy()
CONTRASENA = "contraseña-de-prueba-123"
ORIGEN_AJENO = "https://otro-sitio.example"


def cli(*argv, esperado=0):
    codigo, salida, error = ejecutar(list(argv))
    assert codigo == esperado, (salida, error)
    return json.loads(salida if codigo == 0 else error)


@pytest.fixture()
def mundo(instalada):
    """Provisión oficial por la CLI: equipo T (supervisora ST; colaboradores P y Q) y equipo U (supervisor SU). Contraseña fijada por el propietario."""
    op = ["--operador", instalada["operador"]]
    equipos = {n: cli("crear-equipo", *op, "--organizacion", str(instalada["org"]), "--nombre", n)["equipo_id"] for n in ("T", "U")}
    personas = {}
    for clave, equipo, rol in (("ST", "T", "supervisor"), ("P", "T", "colaborador"), ("Q", "T", "colaborador"), ("SU", "U", "supervisor")):
        personas[clave] = cli("crear-persona", *op, "--nombre", f"Persona {clave}", "--identificador-acceso", f"{clave.lower()}.t6", "--equipo", equipos[equipo],
                              "--rol", rol, "--desde", D0.isoformat())["persona_id"]
    with get_owner_engine().begin() as c:   # solo la contraseña: el primer acceso (M1-03) no existe todavía
        c.execute(text("update identidad set hash_contrasena = :h"), {"h": calcular_hash(CONTRASENA)})
    return {"op": op, "operador": instalada["operador"], "equipos": equipos, "personas": personas}


def entrar(clave):
    cliente = nuevo_cliente()
    r = iniciar_sesion(cliente, f"{clave.lower()}.t6", CONTRASENA)
    assert r.status_code == 201, r.text
    return cliente, r.json()["csrf_token"]


def desactivar(mundo, clave, motivo="Fin de la relación laboral", esperado=0):
    return cli("desactivar-acceso", *mundo["op"], "--persona", mundo["personas"][clave], "--motivo", motivo, esperado=esperado)


def vigentes(mundo, clave) -> int:
    return filas("select count(*) from sesion s join identidad i on i.id = s.identidad_id where i.persona_id = :p and s.revocada_en is null",
                 p=uuid.UUID(mundo["personas"][clave]))[0][0]


# ===================================================== CA-255: sesiones ya emitidas ========================================

def test_ca255_las_sesiones_anteriores_a_la_desactivacion_dejan_de_servir_en_todas_las_operaciones(mundo):
    (c1, csrf1), (c2, csrf2) = entrar("P"), entrar("P")                     # dos sesiones de la misma persona
    assert c1.get(f"{API}/sesion").status_code == 200 and c2.get(f"{API}/sesion").status_code == 200
    antes = vigentes(mundo, "P")
    r = desactivar(mundo, "P")
    assert antes == 2 and r["sesiones_revocadas"] == 2 and vigentes(mundo, "P") == 0
    for cliente, csrf in ((c1, csrf1), (c2, csrf2)):
        assert cliente.get(f"{API}/sesion").status_code == 401
        assert cliente.get(f"{API}/mi/bitacoras/{D0.isoformat()}").status_code == 401
        assert cliente.post(f"{API}/mi/bitacoras", json={"fecha_laboral": D0.isoformat()}, headers=cabeceras(csrf)).status_code == 401
        assert cliente.post(f"{API}/sesion/cierre", headers=cabeceras(csrf)).status_code == 401
    assert contar("bitacora") == 0                                          # ni una sola escritura tras la desactivación


def test_ca255_aunque_la_sesion_siguiera_vigente_el_servidor_rechaza_toda_peticion_porque_el_acceso_esta_desactivado(mundo):
    """El rechazo no depende de que la revocación haya ocurrido: IR-37 se comprueba en cada petición (no solo al autenticar)."""
    cliente, csrf = entrar("P")
    desactivar(mundo, "P")
    with get_owner_engine().begin() as c:                                    # se «resucita» la sesión por SQL, solo para esta comprobación
        c.execute(text("update sesion set revocada_en = null"))
    assert vigentes(mundo, "P") == 1
    for respuesta in (cliente.get(f"{API}/sesion"), cliente.get(f"{API}/mi/bitacoras/{D0.isoformat()}"),
                      cliente.post(f"{API}/mi/bitacoras", json={"fecha_laboral": D0.isoformat()}, headers=cabeceras(csrf)),
                      cliente.get(f"{API}/mi/actividades")):
        assert respuesta.status_code == 403 and respuesta.json()["codigo"] == "ACCESO_DESACTIVADO", respuesta.text
    assert contar("bitacora") == 0


def test_ca255_un_nuevo_inicio_de_sesion_con_las_credenciales_correctas_se_rechaza_y_no_crea_ninguna_sesion(mundo):
    desactivar(mundo, "P")
    sesiones = contar("sesion")
    r = iniciar_sesion(nuevo_cliente(), "p.t6", CONTRASENA)
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"
    assert contar("sesion") == sesiones and vigentes(mundo, "P") == 0 and "set-cookie" not in r.headers


def test_las_credenciales_incorrectas_siguen_dando_el_mismo_error_uniforme_y_sin_enumerar(mundo):
    desactivar(mundo, "P")
    erroneas = [iniciar_sesion(nuevo_cliente(), "p.t6", "otra-contraseña-123"), iniciar_sesion(nuevo_cliente(), "inexistente.t6", CONTRASENA),
                iniciar_sesion(nuevo_cliente(), "q.t6", "otra-contraseña-123")]
    assert {(r.status_code, r.json()["codigo"]) for r in erroneas} == {(401, "CREDENCIALES_INVALIDAS")}             # la desactivación no se revela sin las credenciales


def test_las_reglas_de_origen_y_csrf_no_cambian(mundo):
    cliente, csrf = entrar("Q")
    desactivar(mundo, "P")
    assert iniciar_sesion(nuevo_cliente(), "q.t6", CONTRASENA, origen=ORIGEN_AJENO).status_code == 400                # origen no permitido
    assert cliente.post(f"{API}/mi/bitacoras", json={"fecha_laboral": D0.isoformat()}, headers={"Origin": "https://testserver"}).status_code == 400   # sin CSRF
    assert cliente.post(f"{API}/mi/bitacoras", json={"fecha_laboral": D0.isoformat()}, headers=cabeceras(csrf)).status_code == 201                    # y lo válido sigue válido


def test_las_demas_personas_no_se_ven_afectadas(mundo):
    q, csrf_q = entrar("Q")
    st, _ = entrar("ST")
    desactivar(mundo, "P")
    assert q.get(f"{API}/sesion").status_code == 200 and st.get(f"{API}/sesion").status_code == 200
    assert vigentes(mundo, "Q") == 1 and vigentes(mundo, "ST") == 1
    assert iniciar_sesion(nuevo_cliente(), "q.t6", CONTRASENA).status_code == 201


# ===================================================== CA-256: los registros no cambian ====================================

def test_ca256_los_registros_de_la_persona_desactivada_se_conservan_y_siguen_siendo_inaccesibles_para_los_demas_como_antes(mundo):
    p, csrf = entrar("P")
    q, _ = entrar("Q")
    actividad = planificar_actividad(p, csrf, D0.isoformat(), "Informe")
    assert avanzar(p, csrf, actividad, D0.isoformat(), "En progreso", "Primer borrador").status_code == 201
    antes = [filas(f"select x::text from {t} x order by x.id") for t in ("bitacora", "actividad", "planificacion", "avance")]
    ajena_antes = q.get(f"{API}/mi/actividades/{actividad}").status_code
    desactivar(mundo, "P")
    assert [filas(f"select x::text from {t} x order by x.id") for t in ("bitacora", "actividad", "planificacion", "avance")] == antes
    assert q.get(f"{API}/mi/actividades/{actividad}").status_code == ajena_antes == 404                              # M2 y M3 no cambian: sigue el 404 provisional hasta M4
    assert filas("select propietaria_id from actividad where id = :a", a=actividad) == [(uuid.UUID(mundo["personas"]["P"]),)]


# ===================================================== CA-260 y CA-261: el único supervisor ================================

def test_ca260_el_unico_supervisor_se_desactiva_con_advertencia_y_su_pertenencia_se_conserva(mundo):
    r = desactivar(mundo, "ST")
    assert [a["equipo"] for a in r["advertencias"]] == ["T"] and r["advertencias"][0]["colaboradores"] == 2
    assert filas("select rol, hasta_exclusivo from pertenencia where persona_id = :p", p=uuid.UUID(mundo["personas"]["ST"])) == [("supervisor", None)]
    st = nuevo_cliente()
    assert iniciar_sesion(st, "st.t6", CONTRASENA).status_code == 403                                                # la supervisora ya no entra


def test_ca261_los_colaboradores_del_equipo_pendiente_no_reciben_funciones_de_supervision(mundo):
    """Ningún colaborador ni otra supervisora accede a lo que solo veía la supervisión del equipo: la auditoría ajena sigue en 404 provisional."""
    p, csrf = entrar("P")
    q, _ = entrar("Q")
    su, _ = entrar("SU")
    actividad = planificar_actividad(p, csrf, D0.isoformat(), "Informe")
    desactivar(mundo, "ST")
    for cliente in (q, su):
        assert cliente.get(f"{API}/auditoria", params={"tipo_objeto": "actividad", "objeto_id": actividad}).status_code == 404
        assert cliente.get(f"{API}/mi/actividades/{actividad}").status_code == 404
    assert [f[0] for f in filas("select rol from pertenencia where persona_id in (:q, :p) order by rol",
                                q=uuid.UUID(mundo["personas"]["Q"]), p=uuid.UUID(mundo["personas"]["P"]))] == ["colaborador", "colaborador"]


# ===================================================== carreras entre el inicio de sesión y la desactivación ===============

def test_un_inicio_de_sesion_simultaneo_espera_a_la_desactivacion_y_se_rechaza_sin_dejar_sesiones(mundo, instalada):
    """Se detiene la desactivación antes de confirmar: el inicio de sesión queda esperando el bloqueo de la persona y, al confirmarse,
    ve el acceso desactivado. Sin ese bloqueo habría creado una sesión que la desactivación (ya calculada) no revocaría."""
    resultado = {}
    with get_provision_engine().connect() as conexion:
        operador = identificar(conexion, instalada["operador"], "credencial-cli-de-prueba-123")
        conexion.commit()
        desactivar_acceso(conexion, operador, persona_id=uuid.UUID(mundo["personas"]["P"]), motivo="Fin")      # sin confirmar todavía

        def iniciar():
            resultado["login"] = iniciar_sesion(nuevo_cliente(), "p.t6", CONTRASENA)

        hilo = threading.Thread(target=iniciar)
        hilo.start()
        assert _esperar_bloqueo_consultivo(), "el inicio de sesión debía esperar el bloqueo de la persona mientras la desactivación no confirma"
        conexion.commit()
    hilo.join(30)
    assert not hilo.is_alive()
    assert resultado["login"].status_code == 403 and resultado["login"].json()["codigo"] == "ACCESO_DESACTIVADO"
    assert vigentes(mundo, "P") == 0


@pytest.mark.parametrize("ronda", range(4))
def test_muchos_inicios_de_sesion_mientras_se_desactiva_no_dejan_ninguna_sesion_vigente(mundo, ronda):
    """Ocho hilos inician sesión sin parar mientras otro hilo desactiva el acceso: al final, ninguna sesión de la persona sigue vigente y
    ninguna petición con una de las sesiones obtenidas es aceptada."""
    obtenidas, errores, parar = [], [], threading.Event()

    def iniciar():
        while not parar.is_set():
            cliente = nuevo_cliente()
            r = iniciar_sesion(cliente, "p.t6", CONTRASENA)
            if r.status_code == 201:
                obtenidas.append(cliente)
            elif r.status_code not in (403, 429):        # 429: ocho inicios válidos simultáneos de una misma cuenta y origen pueden agotar los cinco libres (M1-T7)
                errores.append((r.status_code, r.text[:100]))

    hilos = [threading.Thread(target=iniciar) for _ in range(8)]
    for h in hilos:
        h.start()
    limite = time.time() + 60
    while len(obtenidas) < 3 and time.time() < limite:       # deja que haya sesiones en curso antes de desactivar
        time.sleep(0.01)
    desactivar(mundo, "P")
    parar.set()
    for h in hilos:
        h.join(60)
    assert errores == [] and vigentes(mundo, "P") == 0
    assert obtenidas and all(c.get(f"{API}/sesion").status_code in (401, 403) for c in obtenidas)


def test_las_peticiones_simultaneas_con_la_sesion_vigente_no_provocan_errores_de_servidor(mundo):
    cliente, csrf = entrar("P")
    codigos, parar = [], threading.Event()

    def pedir():
        while not parar.is_set():
            codigos.append(cliente.get(f"{API}/sesion").status_code)

    hilos = [threading.Thread(target=pedir) for _ in range(4)]
    for h in hilos:
        h.start()
    limite = time.time() + 30
    while len(codigos) < 5 and time.time() < limite:
        time.sleep(0.01)
    desactivar(mundo, "P")
    posteriores = len(codigos)
    time.sleep(0.3)                                  # los hilos siguen pidiendo después de la desactivación
    parar.set()
    for h in hilos:
        h.join(30)
    assert set(codigos) <= {200, 401, 403} and 200 in codigos                      # ninguna respuesta de servidor (5xx) ni inesperada
    # Como mucho una petición por hilo pudo empezar ANTES de la confirmación y terminar después (en curso); todo lo demás se rechaza.
    assert codigos[posteriores:].count(200) <= len(hilos) and all(c in (401, 403) for c in codigos[-5:])
    assert cliente.get(f"{API}/sesion").status_code in (401, 403)
