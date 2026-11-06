"""Creación de cuentas locales: idempotente, sin duplicados, sin tercer rol y sin contraseñas en claro.

Las pruebas usan correos de ejemplo y una contraseña aleatoria generada en cada ejecución: ninguna
contraseña real está escrita en un archivo.
"""

import json
import secrets
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db import get_owner_engine
from app.seguridad.contrasenas import verificar
from scripts import crear_cuentas as cc
from scripts.crear_cuentas import CreacionRechazada, crear_cuentas, main
from scripts.seed_dev import sembrar
from tests.aislamiento import BASE_DE_PRUEBAS
from tests.fabricas import hoy
from tests.utiles_http import API, cabeceras, iniciar_sesion, nuevo_cliente

CLAVE = secrets.token_urlsafe(20)  # aleatoria por ejecución; nunca un valor fijo
ADMIN = "admin.prueba@example.test"
COLAB = "colab.prueba@example.test"


def puerto() -> int:
    return make_url(get_settings().migrations_database_url).port


def especificacion(**cambios) -> dict:
    spec = {
        "organizacion": "Organización de prueba",
        "zona_horaria": "America/Bogota",
        "equipo": "Equipo de prueba",
        "cuentas": [
            {"nombre": "Admin Prueba", "usuario": ADMIN, "rol": "supervisor"},
            {"nombre": "Persona Colaboradora", "usuario": COLAB, "rol": "colaborador"},
        ],
    }
    spec.update(cambios)
    return spec


def crear(spec=None, clave=CLAVE, **kw):
    return crear_cuentas(get_owner_engine(), spec or especificacion(), clave, base=BASE_DE_PRUEBAS,
                         puerto=puerto(), **kw)


def contar(tabla: str) -> int:
    with get_owner_engine().connect() as c:
        return c.execute(text(f"select count(*) from {tabla}")).scalar_one()


def todo() -> dict:
    return {t: contar(t) for t in ("organizacion", "equipo", "persona", "identidad", "pertenencia", "auditoria")}


# --- Creación y modelo ---------------------------------------------------------------------------

def test_crea_la_organizacion_el_equipo_y_las_dos_cuentas_en_el_mismo_equipo():
    resultados = crear()
    assert [(r.nombre, r.rol, r.accion) for r in resultados] == [
        ("Admin Prueba", "supervisor", "creada"), ("Persona Colaboradora", "colaborador", "creada")]
    assert todo() == {"organizacion": 1, "equipo": 1, "persona": 2, "identidad": 2, "pertenencia": 2, "auditoria": 2}
    with get_owner_engine().connect() as c:
        filas = c.execute(text("select p.nombre, pe.rol, pe.equipo_id, pe.desde, pe.hasta_exclusivo "
                               "from pertenencia pe join persona p on p.id = pe.persona_id order by 1")).all()
    assert len({f.equipo_id for f in filas}) == 1                                 # el mismo equipo
    assert {f.rol for f in filas} == {"supervisor", "colaborador"}               # solo roles funcionales
    assert all(f.desde == hoy() and f.hasta_exclusivo is None for f in filas)    # IR-30: desde la fecha actual


def test_no_existe_ningun_rol_de_administrador():
    for rol in ("admin", "administrador", "ADMIN"):
        spec = especificacion()
        spec["cuentas"][0]["rol"] = rol
        with pytest.raises(CreacionRechazada):
            crear(spec)
    assert sum(todo().values()) == 0
    crear()
    with get_owner_engine().connect() as c:
        assert {r[0] for r in c.execute(text("select distinct rol from pertenencia"))} <= {"colaborador", "supervisor"}


def test_las_contrasenas_usan_argon2id_y_no_aparecen_en_ninguna_tabla():
    crear()
    with get_owner_engine().connect() as c:
        hashes = [r[0] for r in c.execute(text("select hash_contrasena from identidad"))]
        assert len(hashes) == 2 and len(set(hashes)) == 2                         # sal distinta en cada cuenta
        assert all(h.startswith("$argon2id$") and verificar(h, CLAVE) for h in hashes)
        for tabla in [r[0] for r in c.execute(text(
                "select tablename from pg_tables where schemaname='public' and tablename <> 'alembic_version'"))]:
            n = c.execute(text(f"select count(*) from {tabla} x where x::text like :p"), {"p": f"%{CLAVE}%"}).scalar_one()
            assert n == 0, f"la contraseña aparece en claro en {tabla}"


def test_el_usuario_se_guarda_normalizado():
    spec = especificacion()
    spec["cuentas"][1]["usuario"] = "  Colab.Prueba@Example.Test "
    crear(spec)
    with get_owner_engine().connect() as c:
        assert c.execute(text("select count(*) from identidad where identificador_acceso = :i"), {"i": COLAB}).scalar_one() == 1


# --- Idempotencia y duplicados -------------------------------------------------------------------

def test_es_idempotente_y_no_modifica_lo_existente():
    crear()
    antes = todo()
    with get_owner_engine().connect() as c:
        hashes_antes = sorted(r[0] for r in c.execute(text("select hash_contrasena from identidad")))
    otra_clave = secrets.token_urlsafe(20)
    resultados = crear(clave=otra_clave)                                          # otra contraseña: no debe aplicarse
    assert {r.accion for r in resultados} == {"ya existía"}
    assert todo() == antes
    with get_owner_engine().connect() as c:
        assert sorted(r[0] for r in c.execute(text("select hash_contrasena from identidad"))) == hashes_antes


def test_una_cuenta_nueva_se_anade_sin_tocar_las_existentes():
    crear()
    spec = especificacion()
    spec["cuentas"].append({"nombre": "Tercera Persona", "usuario": "tercera@example.test", "rol": "colaborador"})
    resultados = crear(spec)
    assert [r.accion for r in resultados] == ["ya existía", "ya existía", "creada"]
    assert todo()["persona"] == 3 and todo()["pertenencia"] == 3


def test_no_duplica_aunque_el_usuario_cambie_de_mayusculas():
    crear()
    spec = especificacion()
    spec["cuentas"][0]["usuario"] = ADMIN.upper()
    assert crear(spec)[0].accion == "ya existía"
    assert todo()["identidad"] == 2


def test_rechaza_un_nombre_que_ya_pertenece_a_otra_identidad():
    crear()
    spec = especificacion()
    spec["cuentas"].append({"nombre": "admin prueba", "usuario": "otro@example.test", "rol": "colaborador"})
    antes = todo()
    with pytest.raises(CreacionRechazada, match="no se duplica"):
        crear(spec)
    assert todo() == antes                                                        # todo o nada


def test_reutiliza_la_organizacion_y_no_toca_a_las_personas_existentes():
    sembrar(get_owner_engine())                                                   # "Organización Demo" y 3 personas
    antes = todo()
    spec = especificacion(organizacion="Organización Demo")
    crear(spec)
    despues = todo()
    assert despues["organizacion"] == antes["organizacion"] == 1                  # la reutiliza
    assert despues["persona"] == antes["persona"] + 2 and despues["equipo"] == antes["equipo"] + 1
    with get_owner_engine().connect() as c:
        assert c.execute(text("select count(*) from persona where nombre like '%(demo)'")).scalar_one() == 3
        assert c.execute(text("select count(*) from pertenencia where rol='supervisor'")).scalar_one() == 2  # uno por equipo


# --- Reglas del modelo ---------------------------------------------------------------------------

def test_un_equipo_no_admite_dos_supervisores_ni_en_la_especificacion_ni_en_ejecuciones_distintas():
    spec = especificacion()
    spec["cuentas"].append({"nombre": "Otro Supervisor", "usuario": "sup2@example.test", "rol": "supervisor"})
    with pytest.raises(CreacionRechazada, match="como máximo un supervisor"):
        crear(spec)
    crear()
    otra = especificacion(cuentas=[{"nombre": "Otro Supervisor", "usuario": "sup2@example.test", "rol": "supervisor"}])
    antes = todo()
    with pytest.raises(CreacionRechazada, match="rechazó la operación"):
        crear(otra)
    assert todo() == antes


def test_colaboradores_sin_supervisor_en_el_equipo_se_rechazan():
    spec = especificacion(cuentas=[{"nombre": "Solo Colaborador", "usuario": "solo@example.test", "rol": "colaborador"}])
    with pytest.raises(CreacionRechazada, match="sin supervisor"):
        crear(spec)
    assert sum(todo().values()) == 0                                              # todo o nada: ni siquiera el equipo


def test_la_auditoria_de_provision_no_contiene_credenciales_ni_identificadores_de_acceso():
    crear()
    with get_owner_engine().connect() as c:
        filas = c.execute(text("select tipo_autor, autor_persona_id, referencia_provision, operacion, "
                               "valor_nuevo::text as nuevo from auditoria")).all()
    assert len(filas) == 2
    for f in filas:
        assert (f.tipo_autor, f.autor_persona_id, f.operacion) == ("provision", None, "alta")
        assert f.referencia_provision == "scripts.crear_cuentas"
        for prohibido in (CLAVE, "argon2", "example.test", "@"):
            assert prohibido not in f.nuevo


# --- Destino, simulación, especificación y contraseña --------------------------------------------

def test_comprueba_con_el_servidor_la_base_y_el_puerto_exactos():
    for base, p in (("smartwork_app", puerto()), (BASE_DE_PRUEBAS, 5433), ("otra_base", 1)):
        with pytest.raises(CreacionRechazada):
            crear_cuentas(get_owner_engine(), especificacion(), CLAVE, base=base, puerto=p)
    assert sum(todo().values()) == 0


class _ConexionQueResponde:
    """Simula lo que el SERVIDOR dice de sí mismo, distinto de lo que dice la configuración."""

    def __init__(self, base, puerto, superusuario=False):
        self._fila = (base, puerto, superusuario)

    def execute(self, *_a, **_k):
        class _R:
            def one(_s):
                return self._fila
        return _R()


def test_si_el_servidor_contradice_a_la_configuracion_se_rechaza():
    """La configuración apunta a smartwork_test, pero el servidor responde ser otra base u otro puerto."""
    ok = _ConexionQueResponde(BASE_DE_PRUEBAS, puerto())
    cc.comprobar_destino(ok, base=BASE_DE_PRUEBAS, puerto=puerto())          # coherente: se acepta
    for falsa in (_ConexionQueResponde("smartwork_app", puerto()), _ConexionQueResponde(BASE_DE_PRUEBAS, 5433)):
        with pytest.raises(CreacionRechazada, match="servidor confirma"):
            cc.comprobar_destino(falsa, base=BASE_DE_PRUEBAS, puerto=puerto())


def test_un_rol_administrador_se_rechaza_aunque_la_base_coincida():
    with pytest.raises(CreacionRechazada, match="no debe ser administrador"):
        cc.comprobar_destino(_ConexionQueResponde(BASE_DE_PRUEBAS, puerto(), superusuario=True),
                             base=BASE_DE_PRUEBAS, puerto=puerto())


def test_solo_opera_contra_un_servidor_local(monkeypatch):
    remoto = make_url(get_settings().migrations_database_url).set(host="db.ejemplo.com")
    monkeypatch.setattr(get_settings(), "migrations_database_url", remoto.render_as_string(hide_password=False))
    with pytest.raises(CreacionRechazada, match="local"):
        crear()


def test_simular_valida_todo_y_no_deja_nada():
    resultados = crear(simular=True)
    assert {r.accion for r in resultados} == {"creada"}
    assert sum(todo().values()) == 0


def test_la_especificacion_no_puede_contener_contrasenas(tmp_path):
    for clave in ("password", "contrasena", "Clave", "secret"):
        ruta = tmp_path / "cuentas.json"
        spec = especificacion()
        spec["cuentas"][0][clave] = "lo-que-sea"
        ruta.write_text(json.dumps(spec), encoding="utf-8")
        with pytest.raises(CreacionRechazada, match="contraseñas"):
            cc.cargar_especificacion(ruta)


def test_cargar_especificacion_valida_la_estructura(tmp_path):
    with pytest.raises(CreacionRechazada, match="No existe"):
        cc.cargar_especificacion(tmp_path / "no-existe.json")
    mala = tmp_path / "mala.json"
    mala.write_text("{no es json", encoding="utf-8")
    with pytest.raises(CreacionRechazada, match="JSON"):
        cc.cargar_especificacion(mala)
    buena = tmp_path / "buena.json"
    buena.write_text(json.dumps(especificacion()), encoding="utf-8")
    assert len(cc.cargar_especificacion(buena)["cuentas"]) == 2


def test_la_contrasena_se_lee_de_un_archivo_del_entorno_o_de_una_peticion_sin_eco(tmp_path):
    archivo = tmp_path / "contrasena"
    archivo.write_text(CLAVE + "\n", encoding="utf-8")
    assert cc.leer_contrasena(archivo, entorno={}) == CLAVE                        # el salto de línea final no cuenta
    assert cc.leer_contrasena(None, entorno={cc.VARIABLE_CONTRASENA: CLAVE}) == CLAVE
    assert cc.leer_contrasena(None, entorno={}, interactivo=True, pedir=lambda _: CLAVE) == CLAVE
    with pytest.raises(CreacionRechazada, match="Falta la contraseña"):
        cc.leer_contrasena(None, entorno={}, interactivo=False)


def test_el_minimo_de_la_politica_es_de_10_caracteres_y_viene_de_la_configuracion():
    assert get_settings().password_min_length == 10
    assert cc.leer_contrasena(None, entorno={cc.VARIABLE_CONTRASENA: "a" * 10}) == "a" * 10   # el límite exacto se acepta
    for valor in ("corta", "a" * 9):
        with pytest.raises(CreacionRechazada, match="al menos 10"):
            cc.leer_contrasena(None, entorno={cc.VARIABLE_CONTRASENA: valor})


def test_el_minimo_es_un_parametro_y_no_un_valor_fijo_del_codigo(monkeypatch):
    monkeypatch.setattr(get_settings(), "password_min_length", 12)
    with pytest.raises(CreacionRechazada, match="al menos 12"):
        cc.leer_contrasena(None, entorno={cc.VARIABLE_CONTRASENA: "a" * 11})
    assert cc.leer_contrasena(None, entorno={cc.VARIABLE_CONTRASENA: "a" * 12}) == "a" * 12


def test_ya_no_existe_ninguna_excepcion_de_contrasena_corta(tmp_path):
    assert not hasattr(cc, "LONGITUD_MINIMA_EXCEPCION") and not hasattr(cc, "LONGITUD_MINIMA")
    with pytest.raises(TypeError):
        cc.leer_contrasena(None, entorno={cc.VARIABLE_CONTRASENA: "a" * 10}, permitir_corta=True)  # type: ignore[call-arg]
    ruta = tmp_path / "cuentas.json"
    ruta.write_text(json.dumps(especificacion()), encoding="utf-8")
    with pytest.raises(SystemExit) as salida:                                      # el indicador ya no existe
        main(["--base", BASE_DE_PRUEBAS, "--puerto", str(puerto()), "--cuentas", str(ruta), "--permitir-contrasena-corta"])
    assert salida.value.code == 2


def test_la_linea_de_ordenes_crea_con_una_contrasena_de_10_caracteres_sin_ningun_indicador(tmp_path, capsys):
    valor = secrets.token_urlsafe(8)[:10]                                         # 10 caracteres, aleatoria
    archivo = tmp_path / "contrasena"
    archivo.write_text(valor, encoding="utf-8")
    ruta = tmp_path / "cuentas.json"
    ruta.write_text(json.dumps(especificacion()), encoding="utf-8")
    base = ["--base", BASE_DE_PRUEBAS, "--puerto", str(puerto()), "--cuentas", str(ruta)]
    assert main([*base, "--archivo-contrasena", str(archivo)]) == 0
    salida = capsys.readouterr().out
    assert valor not in salida and "Aviso" not in salida
    assert todo()["identidad"] == 2
    assert iniciar_sesion(nuevo_cliente(), ADMIN, valor).status_code == 201
    corta = tmp_path / "corta"
    corta.write_text(valor[:9], encoding="utf-8")                                 # 9 caracteres: rechazada
    assert main([*base, "--archivo-contrasena", str(corta)]) == 1
    assert "al menos 10" in capsys.readouterr().err


def test_rechaza_una_contrasena_demasiado_larga():
    with pytest.raises(CreacionRechazada, match="máximo"):
        cc.leer_contrasena(None, entorno={cc.VARIABLE_CONTRASENA: "a" * (get_settings().login_password_max_length + 1)})


def test_la_linea_de_ordenes_simula_y_rechaza_el_destino_equivocado(tmp_path, capsys):
    ruta = tmp_path / "cuentas.json"
    ruta.write_text(json.dumps(especificacion()), encoding="utf-8")
    base = ["--base", BASE_DE_PRUEBAS, "--puerto", str(puerto()), "--cuentas", str(ruta)]
    assert main([*base, "--simular"]) == 0
    salida = capsys.readouterr().out
    assert "Destino confirmado por el servidor" in salida and "simulación" in salida
    assert CLAVE not in salida and "example.test" not in salida
    assert sum(todo().values()) == 0
    assert main(["--base", "smartwork_app", "--puerto", str(puerto()), "--cuentas", str(ruta), "--simular"]) == 1
    assert "rechazada" in capsys.readouterr().err


# --- Las cuentas creadas funcionan de verdad ------------------------------------------------------

def test_ambas_cuentas_inician_sesion_con_su_rol_y_cada_una_ve_solo_lo_suyo():
    crear()
    admin, colab = nuevo_cliente(), nuevo_cliente()
    r_admin = iniciar_sesion(admin, ADMIN, CLAVE)
    r_colab = iniciar_sesion(colab, COLAB, CLAVE)
    assert r_admin.status_code == 201 and r_colab.status_code == 201
    assert admin.get(f"{API}/sesion").json()["rol_vigente"] == "supervisor"
    assert colab.get(f"{API}/sesion").json()["rol_vigente"] == "colaborador"
    assert admin.get(f"{API}/sesion").json()["persona"]["nombre"] == "Admin Prueba"
    fecha = hoy().isoformat()

    # La persona colaboradora registra y consulta su bitácora
    csrf = r_colab.json()["csrf_token"]
    abierta = colab.post(f"{API}/mi/bitacoras", json={"fecha_laboral": fecha}, headers=cabeceras(csrf))
    assert abierta.status_code == 201
    plan = colab.post(f"{API}/mi/bitacoras/{fecha}/planificaciones", json={"titulo": "Revisar entregables"},
                      headers=cabeceras(csrf, **{"Idempotency-Key": secrets.token_hex(8)}))
    assert plan.status_code == 201
    propia = colab.get(f"{API}/mi/bitacoras/{fecha}").json()
    assert [a["titulo"] for a in propia["actividades"]] == ["Revisar entregables"]

    # Las restricciones siguen: el supervisor no ve la bitácora de la colaboradora (RN-23; M4 no existe todavía)
    ajena = admin.get(f"{API}/mi/bitacoras/{fecha}")
    assert ajena.status_code == 404 and ajena.json()["codigo"] == "RECURSO_NO_DISPONIBLE"
    # ... y viceversa
    csrf_admin = r_admin.json()["csrf_token"]
    admin.post(f"{API}/mi/bitacoras", json={"fecha_laboral": fecha}, headers=cabeceras(csrf_admin))
    assert colab.get(f"{API}/mi/bitacoras/{fecha}").json()["bitacora"]["persona_id"] != \
        admin.get(f"{API}/mi/bitacoras/{fecha}").json()["bitacora"]["persona_id"]
    # Sin sesión no hay nada
    assert nuevo_cliente().get(f"{API}/mi/bitacoras/{fecha}").status_code == 401


def test_no_hay_privilegios_administrativos_globales():
    crear()
    admin = nuevo_cliente()
    iniciar_sesion(admin, ADMIN, CLAVE)
    cuerpo = admin.get(f"{API}/sesion").json()
    assert cuerpo["rol_vigente"] in ("colaborador", "supervisor")
    assert set(cuerpo) == {"persona", "rol_vigente", "fecha_actual", "csrf_token"}   # nada de permisos extra
    # Las rutas de administración no existen
    for ruta in ("/admin", "/api/v1/admin", "/api/v1/usuarios", "/api/v1/equipos"):
        assert admin.get(ruta).status_code == 404
