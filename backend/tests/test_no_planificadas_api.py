"""T5 — M2-06: registrar una actividad no planificada (PostgreSQL real, por HTTP).

Criterios: CA-43, CA-44, CA-53 a CA-58, CA-59, CA-60, CA-296 y las reglas D-01, D-02, D-03, D-04, T-04,
IR-13 (actividad y primer avance atómicos), IR-16 (sin planificación original inventada), RN-20, RN-45,
RN-69 y RN-112. Las pruebas destructivas corren solo sobre ``smartwork_test``.
"""

import threading
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.db import get_owner_engine
from app.modulos.bitacoras import servicio
from app.seguridad.sesiones import NOMBRE_COOKIE
from scripts.verificar_datos import estados_actuales_incoherentes
from tests.fabricas import (
    crear_equipo, crear_identidad, crear_persona, crear_pertenencia, escenario_basico, hoy,
)
from tests.utiles_http import API, iniciar_sesion, nuevo_cliente, sesion_iniciada
from tests.utiles_m2 import avanzar, con_clave, contar, filas, iso

ESTADOS = ["Pendiente", "En progreso", "Bloqueada", "Completada"]


def no_planificada(cliente, csrf, fecha=None, titulo="Reunión imprevista con soporte", estado="En progreso",
                   descripcion="Atendí un incidente urgente", motivo_bloqueo=None, clave="__auto__", **extra):
    """M2-06. Solo envía los campos que no son None (para probar campos ausentes)."""
    cuerpo = {"fecha_laboral": iso(0) if fecha is None else fecha, "titulo": titulo, "estado": estado, "descripcion": descripcion,
              "motivo_bloqueo": motivo_bloqueo, **extra}
    cuerpo = {k: v for k, v in cuerpo.items() if v is not None}
    return cliente.post(f"{API}/mi/actividades-no-planificadas", json=cuerpo, headers=con_clave(csrf, clave))


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c, desde=hoy() - timedelta(days=400))


@pytest.fixture()
def sesion(esc):
    return sesion_iniciada(esc)


def coherente() -> bool:
    with get_owner_engine().connect() as c:
        return estados_actuales_incoherentes(c) == []


# ============================== creación: actividad y primer avance =====================================

def test_crea_la_actividad_no_planificada_y_su_primer_avance(sesion, esc):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, iso(0), "Atender incidente", "En progreso", "Revisé los registros")
    assert r.status_code == 201
    d = r.json()
    assert set(d) == {"actividad", "avance", "bitacora_creada"} and d["bitacora_creada"] is True
    a, v = d["actividad"], d["avance"]
    assert a["titulo"] == "Atender incidente" and a["origen"] == "no_planificada"             # CA-53
    assert a["propietaria_id"] == str(esc.persona) and a["marca_error"] is None
    assert a["fecha_laboral_origen"] == iso(0) and a["estado_actual"] == "En progreso"
    assert v["actividad_id"] == a["id"] and v["fecha_laboral"] == iso(0)
    assert (v["estado"], v["descripcion"], v["motivo_bloqueo"], v["es_reactivacion"]) == (
        "En progreso", "Revisé los registros", None, False)
    assert (contar("actividad"), contar("avance"), contar("bitacora")) == (1, 1, 1)


@pytest.mark.parametrize("estado", ESTADOS)
def test_la_actividad_empieza_con_el_estado_de_su_primer_avance(sesion, estado):
    cliente, csrf = sesion
    motivo = "Falta el acceso" if estado == "Bloqueada" else None
    r = no_planificada(cliente, csrf, iso(0), estado=estado, motivo_bloqueo=motivo)
    assert r.status_code == 201                                                              # CA-44: cualquiera de los cuatro hoy
    assert r.json()["actividad"]["estado_actual"] == estado and r.json()["avance"]["estado"] == estado   # CA-54, RN-69
    assert filas("select estado_actual from actividad")[0].estado_actual == estado
    assert coherente()


def test_no_se_crea_ninguna_planificacion_original_ni_ficticia(sesion):
    cliente, csrf = sesion
    a = no_planificada(cliente, csrf).json()["actividad"]["id"]
    assert contar("planificacion") == 0                                                      # IR-16
    detalle = cliente.get(f"{API}/mi/actividades/{a}").json()
    assert detalle["planificacion_original"] is None and detalle["continuaciones_planificadas"] == []
    assert len(detalle["avances"]) == 1
    bitacora = cliente.get(f"{API}/mi/bitacoras/{iso(0)}").json()
    assert bitacora["planificaciones"] == []                                                 # nada previsto en la jornada
    assert [x["id"] for x in bitacora["actividades"]] == [a] and len(bitacora["avances"]) == 1


def test_se_distingue_de_las_planificadas_sin_ser_un_estado_adicional(sesion):
    cliente, csrf = sesion
    imprevista = no_planificada(cliente, csrf, titulo="Imprevista").json()["actividad"]["id"]
    planificada = cliente.post(f"{API}/mi/bitacoras/{iso(0)}/planificaciones", json={"titulo": "Prevista"},
                               headers=con_clave(csrf)).json()["actividad"]["id"]
    elementos = {e["id"]: e for e in cliente.get(f"{API}/mi/actividades").json()["elementos"]}
    assert (elementos[imprevista]["origen"], elementos[planificada]["origen"]) == ("no_planificada", "planificada")   # CA-53
    assert elementos[imprevista]["estado_actual"] in ESTADOS                                  # CA-57: es uno de los cuatro
    assert elementos[planificada]["estado_actual"] == "Pendiente"
    assert {f.origen for f in filas("select origen from actividad")} == {"planificada", "no_planificada"}


def test_la_actividad_no_planificada_aparece_en_la_consulta_y_el_listado(sesion):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, estado="Bloqueada", motivo_bloqueo="Falta el acceso")
    a = r.json()["actividad"]["id"]
    assert [e["id"] for e in cliente.get(f"{API}/mi/actividades", params={"estado": "Bloqueada"}).json()["elementos"]] == [a]
    avances = cliente.get(f"{API}/mi/actividades/{a}").json()["avances"]
    assert [(x["estado"], x["motivo_bloqueo"]) for x in avances] == [("Bloqueada", "Falta el acceso")]   # CA-56: el motivo consta


def test_los_avances_posteriores_continuan_la_secuencia_de_la_actividad_no_planificada(sesion):
    cliente, csrf = sesion
    a = no_planificada(cliente, csrf, iso(-1), estado="Pendiente", descripcion="Empezó ayer").json()["actividad"]["id"]
    assert avanzar(cliente, csrf, a, iso(0), "En progreso", "Seguí hoy").status_code == 201
    detalle = cliente.get(f"{API}/mi/actividades/{a}").json()
    assert [(x["fecha_laboral"], x["estado"]) for x in detalle["avances"]] == [(iso(-1), "Pendiente"), (iso(0), "En progreso")]
    assert detalle["estado_actual"] == "En progreso" and coherente()


def test_una_no_planificada_completada_no_recibe_avances_posteriores_sin_reactivarla(sesion):
    cliente, csrf = sesion
    a = no_planificada(cliente, csrf, iso(0), estado="Completada").json()["actividad"]["id"]
    r = avanzar(cliente, csrf, a, iso(0), "En progreso")
    assert r.status_code == 409 and r.json()["codigo"] == "ACTIVIDAD_COMPLETADA"             # el primer avance cuenta en la secuencia


# ============================== título, estado, descripción y motivo ====================================

@pytest.mark.parametrize("titulo", [None, "", "   ", "\n\t "])
def test_un_titulo_vacio_o_de_solo_espacios_no_se_permite(sesion, titulo):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, titulo=titulo)
    assert r.status_code == 422 and r.json()["codigo"] == "CAMPO_OBLIGATORIO"                # CA-296, RN-112
    assert r.json()["detalles"] == [{"campo": "titulo", "motivo": "obligatorio"}]
    assert (contar("actividad"), contar("avance"), contar("bitacora")) == (0, 0, 0)


@pytest.mark.parametrize("estado", ["Terminada", "pendiente", "", "COMPLETADA", "Planificada", "No planificada"])
def test_un_estado_distinto_de_los_cuatro_no_se_acepta(sesion, estado):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, estado=estado)
    assert r.status_code == 422 and r.json()["codigo"] == "ESTADO_INVALIDO"                  # CA-54; no hay quinto estado
    assert contar("actividad") == 0


def test_un_estado_ausente_no_se_acepta(sesion):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, estado=None)
    assert r.status_code == 422 and r.json()["codigo"] == "ESTADO_INVALIDO"


@pytest.mark.parametrize("motivo", [None, "", "   "])
def test_bloqueada_sin_motivo_no_se_permite(sesion, motivo):
    cliente, csrf = sesion
    cuerpo = {"fecha_laboral": iso(0), "titulo": "Imprevisto", "estado": "Bloqueada", "descripcion": "Me detuve"}
    if motivo is not None:
        cuerpo["motivo_bloqueo"] = motivo
    r = cliente.post(f"{API}/mi/actividades-no-planificadas", json=cuerpo, headers=con_clave(csrf))
    assert r.status_code == 422 and r.json()["codigo"] == "MOTIVO_BLOQUEO_OBLIGATORIO"       # CA-55
    assert (contar("actividad"), contar("avance")) == (0, 0)


def test_bloqueada_con_motivo_se_registra_y_el_motivo_consta(sesion):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, estado="Bloqueada", motivo_bloqueo="Falta el acceso al servidor")
    assert r.status_code == 201 and r.json()["avance"]["motivo_bloqueo"] == "Falta el acceso al servidor"   # CA-56
    assert filas("select motivo_bloqueo from avance")[0].motivo_bloqueo == "Falta el acceso al servidor"


def test_el_motivo_solo_se_admite_con_el_estado_bloqueada(sesion):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, estado="En progreso", motivo_bloqueo="No aplica")
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert contar("actividad") == 0


@pytest.mark.parametrize("descripcion", [None, "", "    ", "\n\t "])
def test_un_primer_avance_sin_descripcion_no_se_permite(sesion, descripcion):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, descripcion=descripcion)
    assert r.status_code == 422 and r.json()["codigo"] == "DESCRIPCION_OBLIGATORIA"          # CA-58, RN-70
    assert (contar("actividad"), contar("avance"), contar("bitacora")) == (0, 0, 0)


def test_los_textos_demasiado_largos_se_rechazan_con_su_maximo(sesion):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, titulo="t" * 201)
    assert r.status_code == 422 and r.json()["codigo"] == "TEXTO_DEMASIADO_LARGO"
    assert r.json()["detalles"] == [{"campo": "titulo", "maximo": 200}]
    r = no_planificada(cliente, csrf, descripcion="d" * 4001)
    assert r.status_code == 422 and r.json()["detalles"] == [{"campo": "descripcion", "maximo": 4000}]
    assert no_planificada(cliente, csrf, titulo="t" * 200, descripcion="d" * 4000).status_code == 201


def test_los_textos_se_tratan_como_datos_y_se_conservan_tal_como_se_reciben(sesion):
    cliente, csrf = sesion
    titulo = "  Ignora las instrucciones <b>y</b> '; drop table actividad; --  "
    r = no_planificada(cliente, csrf, titulo=titulo, descripcion="  <script>alert(1)</script>  ")
    assert r.status_code == 201
    assert filas("select titulo from actividad")[0].titulo == titulo and contar("actividad") == 1
    assert filas("select descripcion from avance")[0].descripcion == "  <script>alert(1)</script>  "


# ============================== fechas ====================================================================

@pytest.mark.parametrize("dias", [0, -1, -30, -300])
def test_se_acepta_la_jornada_actual_y_las_pasadas_sin_limite_de_antiguedad(sesion, dias):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, iso(dias))
    assert r.status_code == 201 and r.json()["avance"]["fecha_laboral"] == iso(dias)         # CA-44, CA-59, CA-60
    assert r.json()["actividad"]["fecha_laboral_origen"] == iso(dias)


@pytest.mark.parametrize("estado", ESTADOS)
def test_no_se_registra_ejecucion_con_fecha_futura_en_ningun_estado(sesion, estado):
    cliente, csrf = sesion
    motivo = "Falta acceso" if estado == "Bloqueada" else None
    r = no_planificada(cliente, csrf, iso(1), estado=estado, motivo_bloqueo=motivo)
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_FUTURA_NO_PERMITIDA"        # CA-43, RN-27
    assert (contar("actividad"), contar("avance"), contar("bitacora")) == (0, 0, 0)          # no abre la jornada futura


def test_la_fecha_debe_estar_cubierta_por_una_pertenencia(sesion):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, iso(-401))
    assert r.status_code == 422 and r.json()["codigo"] == "FECHA_NO_CUBIERTA"
    assert (contar("actividad"), contar("bitacora")) == (0, 0)


@pytest.mark.parametrize("fecha", ["hoy", "2026-13-45", "01/01/2026", ""])
def test_una_fecha_con_formato_incorrecto_es_una_solicitud_invalida(sesion, fecha):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, fecha)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


def test_la_fecha_laboral_es_obligatoria(sesion):
    cliente, csrf = sesion
    r = cliente.post(f"{API}/mi/actividades-no-planificadas", json={"titulo": "x", "estado": "En progreso", "descripcion": "x"},
                     headers=con_clave(csrf))
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


# ============================== bitácora (D-01, D-04) ======================================================

def test_abre_la_bitacora_de_esa_fecha_en_la_misma_transaccion_una_sola_vez(sesion):
    cliente, csrf = sesion
    assert no_planificada(cliente, csrf, iso(-2)).json()["bitacora_creada"] is True          # D-01
    assert no_planificada(cliente, csrf, iso(-2), titulo="Otra").json()["bitacora_creada"] is False
    assert contar("bitacora") == 1 and contar("actividad") == 2


def test_no_se_registra_en_una_jornada_cerrada(sesion, esc):
    cliente, csrf = sesion
    primera = no_planificada(cliente, csrf, iso(0)).json()["actividad"]["id"]
    with get_owner_engine().begin() as c:   # el cierre manual es T8: se prepara por SQL
        c.execute(text("update bitacora set estado = 'cerrada', cerrada_en = now()"))
    r = no_planificada(cliente, csrf, iso(0), titulo="Otra")
    assert r.status_code == 409 and r.json()["codigo"] == "BITACORA_CERRADA"                 # D-04
    assert (contar("actividad"), contar("avance")) == (1, 1) and primera


def test_una_jornada_cerrada_no_impide_registrar_en_otra_fecha(sesion):
    cliente, csrf = sesion
    no_planificada(cliente, csrf, iso(-1))
    with get_owner_engine().begin() as c:
        c.execute(text("update bitacora set estado = 'cerrada', cerrada_en = now()"))
    assert no_planificada(cliente, csrf, iso(0), titulo="Hoy").status_code == 201


# ============================== autorización y campos ===============================================

@pytest.mark.parametrize("extra", [
    {"origen": "planificada"}, {"propietaria_id": "otra"}, {"planificacion": {"descripcion": "x"}},
    {"estado_actual": "Completada"}, {"id": "x"}, {"es_reactivacion": True}, {"registrado_en": "2020-01-01T00:00:00Z"},
])
def test_el_cuerpo_no_admite_campos_desconocidos(sesion, extra):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, **extra)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert contar("actividad") == 0


def test_sin_sesion_no_se_registra_nada():
    r = nuevo_cliente().post(f"{API}/mi/actividades-no-planificadas", json={"fecha_laboral": iso(0)})
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"


def test_sin_token_csrf_o_desde_otro_origen_se_rechaza(sesion):
    cliente, csrf = sesion
    cuerpo = {"fecha_laboral": iso(0), "titulo": "x", "estado": "En progreso", "descripcion": "x"}
    sin_token = cliente.post(f"{API}/mi/actividades-no-planificadas", json=cuerpo,
                             headers={"Origin": "https://testserver", "Idempotency-Key": "k-1"})
    otro_origen = cliente.post(f"{API}/mi/actividades-no-planificadas", json=cuerpo,
                               headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf, "Idempotency-Key": "k-2"})
    assert sin_token.status_code == 400 and otro_origen.status_code == 400
    assert contar("actividad") == 0


def test_con_el_acceso_desactivado_no_se_registra_nada(sesion, esc):
    cliente, csrf = sesion
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": esc.persona})
    r = no_planificada(cliente, csrf)
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"
    assert contar("actividad") == 0


def test_la_actividad_es_de_quien_la_registra_y_no_de_otra_persona(sesion, esc):
    cliente, csrf = sesion
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        otra = crear_persona(c, "Otra persona")
        crear_pertenencia(c, otra, crear_equipo(c, org, "Otro equipo"), desde=hoy() - timedelta(days=50))
        crear_identidad(c, otra, "otra.persona", "contraseña-de-prueba-123")
    a = no_planificada(cliente, csrf).json()["actividad"]["id"]
    ajeno = nuevo_cliente()
    iniciar_sesion(ajeno, "otra.persona", "contraseña-de-prueba-123")
    assert ajeno.get(f"{API}/mi/actividades").json()["elementos"] == []
    assert ajeno.get(f"{API}/mi/actividades/{a}").status_code == 404                         # T-01
    assert filas("select propietaria_id from actividad")[0].propietaria_id == esc.persona


# ============================== auditoría (RN-45, D-02) =====================================================

def test_en_la_jornada_actual_no_se_audita(sesion):
    cliente, csrf = sesion
    no_planificada(cliente, csrf, iso(0))
    assert contar("auditoria") == 0


def test_en_una_jornada_pasada_deja_una_unica_entrada_con_todo_lo_creado(sesion, esc):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, iso(-4), "Imprevisto del lunes", "Bloqueada", "Me detuve", "Sin datos", clave="pasada-1")
    assert r.status_code == 201
    entradas = filas("select * from auditoria")
    assert len(entradas) == 1                                                                # una entrada por operación
    e = entradas[0]
    assert (e.tipo_autor, e.operacion, e.tipo_objeto) == ("persona", "modificacion_jornada_pasada", "actividad")
    assert e.autor_persona_id == esc.persona and e.propietaria_registro_id == esc.persona
    assert e.fecha_laboral_registro.isoformat() == iso(-4) and str(e.objeto_id) == r.json()["actividad"]["id"]
    assert e.valor_nuevo["bitacora_creada"] is True                                          # la creación implícita va en la misma entrada
    assert e.valor_nuevo["actividad"]["origen"] == "no_planificada" and e.valor_nuevo["actividad"]["estado_actual"] == "Bloqueada"
    assert e.valor_nuevo["avance"]["motivo_bloqueo"] == "Sin datos"
    no_planificada(cliente, csrf, iso(-4), "Imprevisto del lunes", "Bloqueada", "Me detuve", "Sin datos", clave="pasada-1")
    assert contar("auditoria") == 1 and contar("actividad") == 1                             # el reintento no duplica
    otra = no_planificada(cliente, csrf, iso(-4), "Otro imprevisto")                         # otra operación: otra entrada
    assert otra.json()["bitacora_creada"] is False and contar("auditoria") == 2


def test_una_peticion_rechazada_no_deja_auditoria(sesion):
    cliente, csrf = sesion
    no_planificada(cliente, csrf, iso(-4), descripcion="  ")
    no_planificada(cliente, csrf, iso(-4), estado="Bloqueada")
    assert contar("auditoria") == 0 and contar("bitacora") == 0


# ============================== idempotencia (T-04) =======================================================

def test_la_cabecera_idempotency_key_es_obligatoria(sesion):
    cliente, csrf = sesion
    r = no_planificada(cliente, csrf, clave=None)
    assert r.status_code == 400 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_OBLIGATORIA"
    assert contar("actividad") == 0


def test_repetir_la_misma_peticion_con_la_misma_clave_no_duplica_nada(sesion):
    cliente, csrf = sesion
    primera = no_planificada(cliente, csrf, clave="k-1")
    segunda = no_planificada(cliente, csrf, clave="k-1")
    assert primera.status_code == segunda.status_code == 201
    assert segunda.headers["idempotency-replayed"] == "true" and segunda.json() == primera.json()
    assert (contar("actividad"), contar("avance"), contar("bitacora")) == (1, 1, 1)


def test_reutilizar_la_clave_con_otra_peticion_se_rechaza(sesion):
    cliente, csrf = sesion
    no_planificada(cliente, csrf, titulo="Uno", clave="k-2")
    r = no_planificada(cliente, csrf, titulo="Dos", clave="k-2")
    assert r.status_code == 422 and r.json()["codigo"] == "CLAVE_IDEMPOTENCIA_REUTILIZADA"
    assert contar("actividad") == 1


def test_una_peticion_rechazada_no_consume_la_clave_y_se_puede_corregir(sesion):
    cliente, csrf = sesion
    assert no_planificada(cliente, csrf, descripcion="  ", clave="k-3").status_code == 422
    assert no_planificada(cliente, csrf, descripcion="Ahora sí", clave="k-3").status_code == 201
    assert contar("actividad") == 1


def test_dos_actividades_con_el_mismo_titulo_y_claves_distintas_son_dos_actividades(sesion):
    cliente, csrf = sesion
    a = no_planificada(cliente, csrf, titulo="Incidente").json()["actividad"]["id"]
    b = no_planificada(cliente, csrf, titulo="Incidente").json()["actividad"]["id"]
    assert a != b and contar("actividad") == 2 and contar("avance") == 2                     # intenciones distintas: no se fusionan


# ============================== atomicidad (IR-13, IR-24) ====================================================

def test_si_falla_el_primer_avance_no_queda_la_actividad_ni_la_bitacora_ni_la_clave(sesion, monkeypatch):
    cliente, csrf = sesion

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado al guardar el primer avance")

    monkeypatch.setattr(servicio.repositorio, "insertar_avance", falla)
    r = no_planificada(cliente, csrf, iso(0), clave="k-atomica")
    assert r.status_code == 500 and r.json()["codigo"] == "ERROR_INTERNO"
    assert "fallo simulado" not in r.text                                                    # sin detalles internos
    assert (contar("actividad"), contar("avance"), contar("bitacora"), contar("clave_idempotencia")) == (0, 0, 0, 0)
    monkeypatch.undo()
    assert no_planificada(cliente, csrf, iso(0), clave="k-atomica").status_code == 201       # la misma clave puede reintentarse
    assert (contar("actividad"), contar("avance")) == (1, 1)


def test_si_falla_la_auditoria_de_una_jornada_pasada_no_queda_nada(sesion, monkeypatch):
    cliente, csrf = sesion

    def falla(*args, **kwargs):
        raise RuntimeError("fallo simulado al auditar")

    monkeypatch.setattr(servicio, "registrar_operacion_de_persona", falla)
    r = no_planificada(cliente, csrf, iso(-3))
    assert r.status_code == 500
    assert (contar("actividad"), contar("avance"), contar("bitacora"), contar("auditoria"), contar("clave_idempotencia")) == (0, 0, 0, 0, 0)


def test_el_avance_nunca_queda_sin_su_actividad_ni_al_reves(sesion):
    cliente, csrf = sesion
    for i in range(5):
        no_planificada(cliente, csrf, iso(-i), titulo=f"Imprevisto {i}")
    assert filas("select count(*) n from actividad a where not exists (select 1 from avance v where v.actividad_id = a.id)")[0].n == 0
    assert filas("select count(*) n from avance v where not exists (select 1 from actividad a where a.id = v.actividad_id)")[0].n == 0
    assert coherente()


# ============================== concurrencia =================================================================

def _clientes_concurrentes(esc, n):
    base, _ = sesion_iniciada(esc)
    secreto = base.cookies.get(NOMBRE_COOKIE)
    csrf = base.get(f"{API}/sesion").json()["csrf_token"]
    return [nuevo_cliente({NOMBRE_COOKIE: secreto}) for _ in range(n)], csrf


def test_la_misma_peticion_simultanea_con_la_misma_clave_crea_una_sola_actividad(esc):
    clientes, csrf = _clientes_concurrentes(esc, 6)
    resultados, barrera = [], threading.Barrier(6)

    def intentar(i):
        barrera.wait()
        resultados.append(no_planificada(clientes[i], csrf, titulo="Incidente", clave="clave-concurrente"))

    hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(6)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert {r.status_code for r in resultados} <= {201, 409}
    assert [r.json()["codigo"] for r in resultados if r.status_code == 409] == \
        ["OPERACION_EN_CURSO"] * sum(r.status_code == 409 for r in resultados)
    assert sum(r.status_code == 201 and "idempotency-replayed" not in r.headers for r in resultados) == 1
    assert (contar("actividad"), contar("avance"), contar("bitacora")) == (1, 1, 1)


def test_registros_simultaneos_con_claves_distintas_en_una_fecha_nueva_dejan_una_bitacora(esc):
    clientes, csrf = _clientes_concurrentes(esc, 6)
    resultados, barrera = [], threading.Barrier(6)

    def intentar(i):
        barrera.wait()
        resultados.append(no_planificada(clientes[i], csrf, iso(-2), titulo=f"Imprevisto {i}"))

    hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(6)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert [r.status_code for r in resultados] == [201] * 6, [r.text for r in resultados if r.status_code != 201]
    assert (contar("bitacora"), contar("actividad"), contar("avance")) == (1, 6, 6)          # IR-01: una sola bitácora
    assert sum(r.json()["bitacora_creada"] for r in resultados) == 1
    assert contar("auditoria") == 6 and coherente()                                          # una entrada por operación
    assert len({r.json()["actividad"]["id"] for r in resultados}) == 6
