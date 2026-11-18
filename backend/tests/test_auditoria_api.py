"""T13 — M3-07: consultar la auditoría de un registro (PostgreSQL real, por HTTP).

Criterios: CA-65, CA-104, CA-106, CA-108, CA-109, CA-110, CA-112, CA-114, CA-120, CA-266, CA-267, CA-285, CA-286;
RN-49 a RN-52, RN-103, RN-110; D-10, D-11, T-01. Solo la persona propietaria consulta (el acceso del supervisor y la
visibilidad histórica son de M4). Es una lectura: no escribe nada ni genera entradas. Las pruebas destructivas corren
solo sobre ``smartwork_test``.
"""

import base64
import json
import threading
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db import get_owner_engine
from app.seguridad.sesiones import NOMBRE_COOKIE
from tests.fabricas import (
    crear_equipo, crear_identidad, crear_persona, crear_pertenencia, escenario_basico, hoy,
)
from tests.utiles_http import API, iniciar_sesion, nuevo_cliente, sesion_iniciada
from tests.utiles_m2 import avanzar, con_clave, contar, filas, iso, planificar_actividad

CAMPOS = {"id", "momento", "tipo_autor", "autor_persona_id", "operacion", "tipo_objeto", "objeto_id",
          "propietaria_registro_id", "fecha_laboral_registro", "motivo", "valor_anterior", "valor_nuevo"}


def consultar(cliente, tipo, objeto, **parametros):
    return cliente.get(f"{API}/auditoria", params={"tipo_objeto": tipo, "objeto_id": objeto, **parametros})


def entradas_de(cliente, tipo, objeto, **parametros):
    r = consultar(cliente, tipo, objeto, **parametros)
    assert r.status_code == 200, r.text
    return r.json()["elementos"]


def operaciones_de(cliente, tipo, objeto, **parametros):
    return [e["operacion"] for e in entradas_de(cliente, tipo, objeto, **parametros)]


def crear_avance(cliente, csrf, actividad, fecha, estado="En progreso", descripcion="Avancé", motivo=None):
    r = avanzar(cliente, csrf, actividad, fecha, estado, descripcion, motivo)
    assert r.status_code == 201, r.text
    return r.json()["avance"]["id"]


def corregir(cliente, csrf, avance, **campos):
    return cliente.patch(f"{API}/mi/avances/{avance}", json=campos, headers=con_clave(csrf))


def reactivar(cliente, csrf, actividad, fecha, estado="En progreso", descripcion="Retomo"):
    r = cliente.post(f"{API}/mi/actividades/{actividad}/reactivacion", headers=con_clave(csrf),
                     json={"fecha_laboral": fecha, "estado": estado, "descripcion": descripcion})
    assert r.status_code == 201, r.text
    return r.json()["avance"]["id"]


def cerrar(cliente, csrf, fecha, resumen="Resumen de la jornada"):
    cliente.put(f"{API}/mi/bitacoras/{fecha}/resumen", json={"resumen": resumen}, headers=con_clave(csrf, None))
    return cliente.post(f"{API}/mi/bitacoras/{fecha}/cierre", headers=con_clave(csrf))


def reabrir(cliente, csrf, fecha, motivo="Corregir el resumen"):
    return cliente.post(f"{API}/mi/bitacoras/{fecha}/reapertura", json={"motivo": motivo}, headers=con_clave(csrf))


def marcar(cliente, csrf, actividad, motivo="Duplicada"):
    return cliente.post(f"{API}/mi/actividades/{actividad}/marca-error", json={"motivo": motivo}, headers=con_clave(csrf))


def revertir(cliente, csrf, actividad):
    return cliente.post(f"{API}/mi/actividades/{actividad}/marca-error/reversion", headers=con_clave(csrf))


def bitacora_de(fecha) -> str:
    return str(filas("select id from bitacora where fecha_laboral = :f", f=hoy() + timedelta(days=fecha))[0].id)


@pytest.fixture()
def esc():
    with get_owner_engine().begin() as c:
        return escenario_basico(c, desde=hoy() - timedelta(days=400))


@pytest.fixture()
def sesion(esc):
    return sesion_iniciada(esc)


def _otra_persona(identificador="otra.persona"):
    with get_owner_engine().begin() as c:
        org = c.execute(text("select id from organizacion")).scalar_one()
        otra = crear_persona(c, "Otra persona")
        crear_pertenencia(c, otra, crear_equipo(c, org, "Otro equipo"), desde=hoy() - timedelta(days=100))
        crear_identidad(c, otra, identificador, "contraseña-de-prueba-123")
    cliente = nuevo_cliente()
    return cliente, iniciar_sesion(cliente, identificador, "contraseña-de-prueba-123").json()["csrf_token"]


# ============================== la bitácora: cierre, reapertura y correcciones (CA-109, CA-110, CA-266) ==========

def test_los_ciclos_de_cierre_y_reapertura_se_reconstruyen_en_orden(sesion):
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(-3))
    assert cerrar(cliente, csrf, iso(-3)).status_code == 200
    assert reabrir(cliente, csrf, iso(-3), "Faltaba una cifra").status_code == 200
    assert cerrar(cliente, csrf, iso(-3), "Resumen corregido").status_code == 200
    e = entradas_de(cliente, "bitacora", bitacora_de(-3))
    ops = [x["operacion"] for x in e]
    assert [o for o in ops if o in ("cierre", "reapertura")] == ["cierre", "reapertura", "cierre"]          # CA-266
    reap = next(x for x in e if x["operacion"] == "reapertura")
    assert reap["motivo"] == "Faltaba una cifra"                                                              # CA-109
    assert reap["valor_anterior"]["estado"] == "cerrada" and reap["valor_nuevo"] == {"estado": "abierta", "cerrada_en": None}
    cierre = next(x for x in e if x["operacion"] == "cierre")
    assert cierre["valor_anterior"] == {"estado": "abierta", "cerrada_en": None} and cierre["valor_nuevo"]["estado"] == "cerrada"
    assert cierre["valor_nuevo"]["cerrada_en"].endswith("Z")


def test_la_correccion_del_resumen_tras_reabrir_consta_con_el_resumen_anterior_y_el_nuevo(sesion):
    """En la jornada de hoy, reabierta, el cambio es una corrección; en una pasada es una modificación de jornada pasada."""
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(0))
    cerrar(cliente, csrf, iso(0), "Primer resumen")
    reabrir(cliente, csrf, iso(0))
    cliente.put(f"{API}/mi/bitacoras/{iso(0)}/resumen", json={"resumen": "Segundo resumen"}, headers=con_clave(csrf, None))
    corr = [x for x in entradas_de(cliente, "bitacora", bitacora_de(0)) if x["operacion"] == "correccion"]
    assert len(corr) == 1
    assert corr[0]["valor_anterior"]["resumen"] == "Primer resumen" and corr[0]["valor_nuevo"]["resumen"] == "Segundo resumen"
    assert corr[0]["fecha_laboral_registro"] == iso(0)                                                        # CA-65, CA-106


def test_guardar_el_resumen_de_una_jornada_pasada_se_audita_como_modificacion_de_jornada_pasada(sesion):
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(-3))
    cliente.put(f"{API}/mi/bitacoras/{iso(-3)}/resumen", json={"resumen": "Hecho"}, headers=con_clave(csrf, None))
    ops = operaciones_de(cliente, "bitacora", bitacora_de(-3))
    assert "modificacion_jornada_pasada" in ops


# ============================== la actividad: marca y reversión (CA-120) =======================================

def test_la_marca_y_su_reversion_constan_con_motivo_y_valores(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    marcar(cliente, csrf, a, "Se creó dos veces")
    revertir(cliente, csrf, a)
    e = entradas_de(cliente, "actividad", a)
    assert [x["operacion"] for x in e] == ["marca_error", "reversion_marca"]
    m, r = e
    assert m["motivo"] == "Se creó dos veces" and m["valor_anterior"]["marca_error"] is None
    assert m["valor_nuevo"]["marca_error"]["motivo"] == "Se creó dos veces"
    assert r["motivo"] is None and r["valor_anterior"]["marca_error"]["motivo"] == "Se creó dos veces" and r["valor_nuevo"]["marca_error"] is None


def test_una_actividad_marcada_sigue_siendo_consultable_en_la_auditoria(sesion):
    """CA-120."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    marcar(cliente, csrf, a)
    assert operaciones_de(cliente, "actividad", a) == ["marca_error"]


def test_una_actividad_creada_en_una_jornada_pasada_deja_su_entrada(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-4))
    e = entradas_de(cliente, "actividad", a)
    assert [x["operacion"] for x in e] == ["modificacion_jornada_pasada"] and e[0]["fecha_laboral_registro"] == iso(-4)


# ============================== el avance: reactivación y corrección (CA-104, CA-106, CA-108) ===================

def test_la_reactivacion_y_las_correcciones_de_un_avance_se_reconstruyen(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-6))
    crear_avance(cliente, csrf, a, iso(-5), "Completada", "Terminé")
    reac = reactivar(cliente, csrf, a, iso(-4), "En progreso", "Retomo")
    assert corregir(cliente, csrf, reac, descripcion="Retomo, con más detalle").status_code == 200
    assert corregir(cliente, csrf, reac, estado="Bloqueada", motivo_bloqueo="Falta el acceso").status_code == 200
    e = entradas_de(cliente, "avance", reac)
    assert [x["operacion"] for x in e] == ["reactivacion", "correccion", "correccion"]
    assert e[0]["fecha_laboral_registro"] == iso(-4) and e[0]["valor_nuevo"]["avance"]["es_reactivacion"] is True
    assert e[1]["valor_anterior"]["avance"] == {"descripcion": "Retomo"} and e[1]["valor_nuevo"]["avance"] == {"descripcion": "Retomo, con más detalle"}
    assert e[2]["valor_anterior"]["avance"] == {"estado": "En progreso", "motivo_bloqueo": None}               # CA-104, CA-108
    assert e[2]["valor_nuevo"]["avance"] == {"estado": "Bloqueada", "motivo_bloqueo": "Falta el acceso"}
    assert e[2]["valor_anterior"]["estado_actual"] == "En progreso" and e[2]["valor_nuevo"]["estado_actual"] == "Bloqueada"


def test_una_operacion_que_modifica_varios_campos_es_una_sola_entrada(sesion):
    """CA-267."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-4))
    v = crear_avance(cliente, csrf, a, iso(-3), "En progreso", "Texto")
    corregir(cliente, csrf, v, estado="Bloqueada", descripcion="Otro texto", motivo_bloqueo="Sin acceso")
    e = [x for x in entradas_de(cliente, "avance", v) if x["operacion"] == "correccion"]
    assert len(e) == 1 and set(e[0]["valor_nuevo"]["avance"]) == {"estado", "descripcion", "motivo_bloqueo"}


def test_un_avance_registrado_en_una_jornada_pasada_consta_como_modificacion(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-4))
    v = crear_avance(cliente, csrf, a, iso(-3))
    e = entradas_de(cliente, "avance", v)
    assert [x["operacion"] for x in e] == ["modificacion_jornada_pasada"] and e[0]["fecha_laboral_registro"] == iso(-3)


def test_cada_entrada_tiene_los_campos_del_contrato_y_el_autor_es_la_propietaria(sesion, esc):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-4))
    v = crear_avance(cliente, csrf, a, iso(-3))
    corregir(cliente, csrf, v, descripcion="Nuevo")
    for e in entradas_de(cliente, "avance", v):
        assert set(e) == CAMPOS
        assert e["tipo_autor"] == "persona" and e["autor_persona_id"] == str(esc.persona)
        assert e["propietaria_registro_id"] == str(esc.persona) and e["tipo_objeto"] == "avance" and e["objeto_id"] == v
        assert e["momento"].endswith("Z") and uuid.UUID(e["id"])


def test_una_planificacion_propia_se_puede_consultar_y_no_tiene_entradas(sesion):
    """No hay edición de planificaciones (IR-16): su auditoría existe como consulta y está vacía."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(-4))
    plan = str(filas("select id from planificacion where actividad_id = :a", a=a)[0].id)
    r = consultar(cliente, "planificacion", plan)
    assert r.status_code == 200 and r.json() == {"elementos": [], "siguiente": None}


def test_un_registro_sin_operaciones_auditadas_devuelve_una_lista_vacia(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))                 # hoy: crear no se audita
    assert consultar(cliente, "actividad", a).json() == {"elementos": [], "siguiente": None}


# ============================== lo que no produjo cambios no aparece ===========================================

def test_las_operaciones_rechazadas_o_sin_cambios_no_dejan_entrada(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    v = crear_avance(cliente, csrf, a, iso(0), "En progreso", "Texto")
    assert corregir(cliente, csrf, v, descripcion="Texto").status_code == 200                    # sin cambios
    assert corregir(cliente, csrf, v, estado="Pausada").status_code == 422                        # rechazada
    assert corregir(cliente, csrf, v, estado="Completada").status_code == 200
    assert corregir(cliente, csrf, v, estado="En progreso").status_code == 200
    assert reabrir(cliente, csrf, iso(0)).status_code == 409                                      # no estaba cerrada
    assert cerrar(cliente, csrf, iso(0), "").status_code == 409                                   # condiciones sin cumplir
    assert marcar(cliente, csrf, a, "x").status_code == 200 and marcar(cliente, csrf, a, "y").status_code == 409
    assert revertir(cliente, csrf, a).status_code == 200 and revertir(cliente, csrf, a).status_code == 409
    assert operaciones_de(cliente, "avance", v) == ["correccion", "correccion"]
    assert operaciones_de(cliente, "actividad", a) == ["marca_error", "reversion_marca"]
    assert operaciones_de(cliente, "bitacora", bitacora_de(0)) == []


# ============================== autorización: ajeno e inexistente son indistinguibles (CA-286, T-01) ===========

def _registros(cliente, csrf):
    a = planificar_actividad(cliente, csrf, iso(-4))
    v = crear_avance(cliente, csrf, a, iso(-3))
    plan = str(filas("select id from planificacion where actividad_id = :a", a=a)[0].id)
    return {"bitacora": bitacora_de(-4), "actividad": a, "avance": v, "planificacion": plan}


def test_la_auditoria_de_un_registro_ajeno_y_de_uno_inexistente_es_indistinguible(sesion):
    cliente, csrf = sesion
    ajeno, _ = _otra_persona()
    for tipo, objeto in _registros(cliente, csrf).items():
        r = consultar(ajeno, tipo, objeto)
        assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE", tipo                 # CA-112
        inexistente = consultar(ajeno, tipo, str(uuid.uuid4()))
        assert (inexistente.status_code, inexistente.json()) == (r.status_code, r.json()), tipo


def test_un_tipo_que_no_corresponde_al_registro_responde_igual_que_uno_inexistente(sesion):
    cliente, csrf = sesion
    registros = _registros(cliente, csrf)
    r = consultar(cliente, "actividad", registros["avance"])
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE"
    assert consultar(cliente, "avance", registros["bitacora"]).status_code == 404


def test_un_supervisor_del_mismo_equipo_consulta_la_auditoria_de_su_equipo(esc):
    """Actualizada a propósito en M4-T6 (antes afirmaba el 404 provisional): la supervisora vigente del equipo del registro por su fecha laboral consulta la misma auditoría que la
    propietaria (RA-10, CA-111)."""
    cliente, csrf = sesion_iniciada(esc)
    registros = _registros(cliente, csrf)
    with get_owner_engine().begin() as c:
        sup = crear_persona(c, "Sara supervisora")
        crear_pertenencia(c, sup, esc.equipo, "supervisor", desde=hoy() - timedelta(days=50))
        crear_identidad(c, sup, "sara.sup", "contraseña-de-prueba-123")
    s = nuevo_cliente()
    iniciar_sesion(s, "sara.sup", "contraseña-de-prueba-123")
    for tipo, objeto in registros.items():
        r = consultar(s, tipo, objeto)
        assert r.status_code == 200 and r.json() == consultar(cliente, tipo, objeto).json(), tipo


def test_una_persona_solo_ve_sus_propias_entradas(sesion):
    cliente, csrf = sesion
    ajeno, csrf_ajeno = _otra_persona()
    a = planificar_actividad(cliente, csrf, iso(0))
    marcar(cliente, csrf, a)
    b = planificar_actividad(ajeno, csrf_ajeno, iso(0), "De otra persona")
    marcar(ajeno, csrf_ajeno, b, "Motivo ajeno")
    assert [x["motivo"] for x in entradas_de(cliente, "actividad", a)] == ["Duplicada"]
    assert [x["motivo"] for x in entradas_de(ajeno, "actividad", b)] == ["Motivo ajeno"]
    assert consultar(cliente, "actividad", b).status_code == 404 and consultar(ajeno, "actividad", a).status_code == 404


def test_la_autorizacion_se_aplica_antes_de_leer_las_entradas(sesion):
    """Un registro ajeno con muchas entradas no filtra nada: ni cuántas ni su existencia."""
    cliente, csrf = sesion
    ajeno, _ = _otra_persona()
    a = planificar_actividad(cliente, csrf, iso(0))
    marcar(cliente, csrf, a)
    revertir(cliente, csrf, a)
    r = consultar(ajeno, "actividad", a, limite=1)
    assert r.status_code == 404 and "elementos" not in r.json() and "siguiente" not in r.json()


def test_sin_sesion_no_se_consulta(sesion):
    cliente, csrf = sesion
    registros = _registros(cliente, csrf)
    anonimo = nuevo_cliente()
    r = consultar(anonimo, "actividad", registros["actividad"])
    assert r.status_code == 401 and r.json()["codigo"] == "NO_IDENTIFICADA"
    r = anonimo.get(f"{API}/auditoria")
    assert r.status_code == 401


def test_con_el_acceso_desactivado_no_se_consulta(sesion, esc):
    cliente, csrf = sesion
    registros = _registros(cliente, csrf)
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": esc.persona})
    r = consultar(cliente, "actividad", registros["actividad"])
    assert r.status_code in (401, 403) and "elementos" not in r.json()


# ============================== validación de los parámetros (se evalúa antes que el registro) ==================

def test_no_existe_consulta_sin_objeto_ni_listado_global(sesion):
    cliente, csrf = sesion
    for params in ({}, {"tipo_objeto": "actividad"}, {"objeto_id": str(uuid.uuid4())}, {"operacion": "cierre"}):
        r = cliente.get(f"{API}/auditoria", params=params)
        assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA", params
    assert cliente.get(f"{API}/auditoria").json()["detalles"][0]["motivo"] == "obligatorio"


@pytest.mark.parametrize("tipo", ["persona", "pertenencia", "Actividad", "bitácora", "", "todas", "actividad,avance"])
def test_un_tipo_de_registro_no_valido_se_rechaza(sesion, tipo):
    cliente, csrf = sesion
    r = cliente.get(f"{API}/auditoria", params={"tipo_objeto": tipo, "objeto_id": str(uuid.uuid4())})
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"


@pytest.mark.parametrize("objeto", ["no-es-un-uuid", "123", "'; drop table auditoria; --"])
def test_un_identificador_mal_formado_es_una_solicitud_invalida(sesion, objeto):
    cliente, csrf = sesion
    r = cliente.get(f"{API}/auditoria", params={"tipo_objeto": "actividad", "objeto_id": objeto})
    assert r.status_code == 400 and r.json()["detalles"][0]["campo"] == "objeto_id"


@pytest.mark.parametrize("extra", [{"persona_id": "x"}, {"desde": "2026-01-01"}, {"autor": "x"}, {"q": "texto"}])
def test_un_parametro_que_el_producto_no_contempla_se_rechaza(sesion, extra):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    r = consultar(cliente, "actividad", a, **extra)
    assert r.status_code == 400 and r.json()["detalles"][0]["motivo"] == "parametro_no_soportado"


def test_un_parametro_repetido_se_rechaza(sesion):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    r = cliente.get(f"{API}/auditoria?tipo_objeto=actividad&objeto_id={a}&operacion=cierre&operacion=reapertura")
    assert r.status_code == 400 and r.json()["detalles"][0]["motivo"] == "parametro_repetido"


@pytest.mark.parametrize("operacion", ["alta", "cambio_pertenencia", "desactivacion_acceso", "CIERRE", "x", ""])
def test_solo_las_operaciones_de_dominio_son_un_filtro_valido(sesion, operacion):
    """Las de provisión administrativa permanecen aparte (D-11): no son un filtro de esta consulta."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    r = cliente.get(f"{API}/auditoria", params={"tipo_objeto": "actividad", "objeto_id": a, "operacion": operacion})
    assert r.status_code == 400 and r.json()["detalles"][0]["campo"] == "operacion"


@pytest.mark.parametrize("limite", ["0", "-1", "x", "1.5", "", "101", "99999999999"])
def test_un_limite_invalido_o_superior_al_maximo_se_rechaza_con_el_maximo(sesion, limite):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    r = consultar(cliente, "actividad", a, limite=limite)
    assert r.status_code == 400 and r.json()["codigo"] == "SOLICITUD_INVALIDA"
    assert r.json()["detalles"][0] == {"campo": "limite", "maximo": get_settings().pagination_max_limit}


def _cursor(contenido) -> str:
    return base64.urlsafe_b64encode(json.dumps(contenido).encode()).decode().rstrip("=")


@pytest.mark.parametrize("cursor", [
    "abc", "????", "e30", _cursor({}), _cursor({"m": "2026-01-01T00:00:00", "i": str(uuid.uuid4())}),      # sin zona horaria
    _cursor({"m": "no-es-un-instante", "i": str(uuid.uuid4())}), _cursor({"m": "2026-01-01T00:00:00Z", "i": "no"}),
    _cursor([1, 2]),
])
def test_un_cursor_invalido_se_rechaza(sesion, cursor):
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    r = consultar(cliente, "actividad", a, continuar_desde=cursor)
    assert r.status_code == 400 and r.json()["detalles"][0] == {"campo": "continuar_desde", "motivo": "cursor_invalido"}


def test_el_formato_se_evalua_antes_que_la_visibilidad(sesion):
    """Una petición con un límite inválido sobre un registro ajeno es un error de formato, no un 404 (convenciones 3.2)."""
    cliente, csrf = sesion
    ajeno, _ = _otra_persona()
    a = planificar_actividad(cliente, csrf, iso(0))
    assert consultar(ajeno, "actividad", a, limite="0").status_code == 400
    assert consultar(ajeno, "actividad", a).status_code == 404


# ============================== paginación y orden estable (D-10) ==============================================

def _con_cinco_entradas(cliente, csrf):
    a = planificar_actividad(cliente, csrf, iso(-4))
    v = crear_avance(cliente, csrf, a, iso(-3), "En progreso", "Cero")
    for i in range(1, 5):
        assert corregir(cliente, csrf, v, descripcion=f"Versión {i}").status_code == 200
    return v                                                  # 1 modificación de jornada pasada + 4 correcciones


def test_la_paginacion_no_repite_ni_omite_y_termina_con_siguiente_nulo(sesion):
    cliente, csrf = sesion
    v = _con_cinco_entradas(cliente, csrf)
    completo = entradas_de(cliente, "avance", v)
    assert len(completo) == 5
    vistos, cursor, paginas = [], None, 0
    while True:
        r = consultar(cliente, "avance", v, limite=2, **({"continuar_desde": cursor} if cursor else {}))
        assert r.status_code == 200
        cuerpo = r.json()
        assert set(cuerpo) == {"elementos", "siguiente"} and len(cuerpo["elementos"]) <= 2
        vistos += [e["id"] for e in cuerpo["elementos"]]
        paginas += 1
        cursor = cuerpo["siguiente"]
        if cursor is None:
            break
    assert paginas == 3 and vistos == [e["id"] for e in completo] and len(set(vistos)) == 5


def test_sin_mas_elementos_no_hay_siguiente_y_con_mas_si(sesion):
    cliente, csrf = sesion
    v = _con_cinco_entradas(cliente, csrf)
    assert consultar(cliente, "avance", v, limite=5).json()["siguiente"] is None
    assert consultar(cliente, "avance", v, limite=4).json()["siguiente"] is not None
    assert consultar(cliente, "avance", v).json()["siguiente"] is None          # el valor por defecto cubre las cinco


def test_el_orden_es_cronologico_y_estable_entre_consultas(sesion):
    cliente, csrf = sesion
    v = _con_cinco_entradas(cliente, csrf)
    primera = entradas_de(cliente, "avance", v)
    assert [e["momento"] for e in primera] == sorted(e["momento"] for e in primera)
    assert [e["valor_nuevo"]["avance"]["descripcion"] for e in primera[1:]] == [f"Versión {i}" for i in range(1, 5)]
    assert entradas_de(cliente, "avance", v) == primera == entradas_de(cliente, "avance", v)


def test_un_cursor_sigue_siendo_valido_si_se_anaden_entradas_despues(sesion):
    """La auditoría solo se anexa: una entrada nueva aparece al final y no desplaza lo ya paginado."""
    cliente, csrf = sesion
    v = _con_cinco_entradas(cliente, csrf)
    primera = consultar(cliente, "avance", v, limite=3).json()
    corregir(cliente, csrf, v, descripcion="Versión 5")
    resto = entradas_de(cliente, "avance", v, limite=10, continuar_desde=primera["siguiente"])
    assert [e["valor_nuevo"]["avance"]["descripcion"] for e in resto] == ["Versión 3", "Versión 4", "Versión 5"]


def test_el_cursor_de_un_registro_no_da_acceso_a_otro(sesion):
    cliente, csrf = sesion
    v = _con_cinco_entradas(cliente, csrf)
    otro = planificar_actividad(cliente, csrf, iso(-5), "Otra")
    cursor = consultar(cliente, "avance", v, limite=1).json()["siguiente"]
    assert entradas_de(cliente, "actividad", otro, continuar_desde=cursor) == [
        e for e in entradas_de(cliente, "actividad", otro)]                      # el cursor solo posiciona; nunca cambia el objeto


def test_el_filtro_por_operacion_se_combina_con_la_paginacion(sesion):
    cliente, csrf = sesion
    v = _con_cinco_entradas(cliente, csrf)
    assert operaciones_de(cliente, "avance", v, operacion="modificacion_jornada_pasada") == ["modificacion_jornada_pasada"]
    primera = consultar(cliente, "avance", v, operacion="correccion", limite=3).json()
    segunda = consultar(cliente, "avance", v, operacion="correccion", limite=3, continuar_desde=primera["siguiente"]).json()
    assert [e["operacion"] for e in primera["elementos"] + segunda["elementos"]] == ["correccion"] * 4
    assert segunda["siguiente"] is None and operaciones_de(cliente, "avance", v, operacion="cierre") == []


def test_el_orden_refleja_el_orden_en_que_se_aplicaron_las_correcciones_simultaneas(esc):
    """El momento usa el reloj real, no el inicio de la transacción: la cadena de valores anteriores y nuevos se lee en
    orden cronológico aunque las peticiones esperaran el bloqueo de la actividad."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-5))
    v = crear_avance(cliente, csrf0, a, iso(-4), "En progreso", "Lunes")
    base = cliente.get(f"{API}/sesion")
    secreto, csrf = cliente.cookies.get(NOMBRE_COOKIE), base.json()["csrf_token"]
    clientes = [nuevo_cliente({NOMBRE_COOKIE: secreto}) for _ in range(6)]
    barrera = threading.Barrier(6)

    def hilo(i):
        barrera.wait()
        clientes[i].patch(f"{API}/mi/avances/{v}", json={"descripcion": f"Versión {i}"}, headers=con_clave(csrf))

    hs = [threading.Thread(target=hilo, args=(i,)) for i in range(6)]
    [h.start() for h in hs]
    [h.join() for h in hs]
    e = [x for x in entradas_de(cliente, "avance", v) if x["operacion"] == "correccion"]
    assert len(e) == 6
    anterior = "Lunes"
    for x in e:                                                       # cada entrada parte de donde dejó la anterior
        assert x["valor_anterior"]["avance"]["descripcion"] == anterior
        anterior = x["valor_nuevo"]["avance"]["descripcion"]
    assert anterior == filas("select descripcion from avance where id = :v", v=v)[0].descripcion


# ============================== provisión, solo lectura y métodos ==============================================

def test_las_entradas_de_provision_administrativa_no_aparecen(sesion, esc):
    """CA-285 y D-11."""
    cliente, csrf = sesion
    planificar_actividad(cliente, csrf, iso(-3))
    b = bitacora_de(-3)
    cerrar(cliente, csrf, iso(-3))
    with get_owner_engine().begin() as c:
        c.execute(text("insert into auditoria (tipo_autor, referencia_provision, operacion, tipo_objeto, objeto_id, "
                       "propietaria_registro_id, fecha_laboral_registro, valor_nuevo) "
                       "values ('provision', 'procedimiento-1', 'alta', 'bitacora', :b, :p, :f, '{}')"),
                  {"b": b, "p": esc.persona, "f": hoy() - timedelta(days=3)})
    assert filas("select count(*) as n from auditoria where tipo_autor = 'provision'")[0].n == 1
    e = entradas_de(cliente, "bitacora", b)
    assert all(x["tipo_autor"] == "persona" for x in e) and "alta" not in [x["operacion"] for x in e]


def test_consultar_no_escribe_nada_ni_genera_entradas(sesion):
    cliente, csrf = sesion
    v = _con_cinco_entradas(cliente, csrf)
    antes = (contar("auditoria"), contar("avance"), contar("actividad"), contar("bitacora"), contar("clave_idempotencia"))
    for _ in range(3):
        r = consultar(cliente, "avance", v, limite=2)
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    consultar(cliente, "avance", str(uuid.uuid4()))
    cliente.get(f"{API}/auditoria")
    assert (contar("auditoria"), contar("avance"), contar("actividad"), contar("bitacora"), contar("clave_idempotencia")) == antes


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_la_auditoria_no_admite_ninguna_otra_operacion(sesion, metodo):
    """Es solo lectura: cualquier otro método se rechaza con 405 y Allow: GET (PA-30) y no cambia nada."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    antes = contar("auditoria")
    r = getattr(cliente, metodo)(f"{API}/auditoria", headers=con_clave(csrf), params={"tipo_objeto": "actividad", "objeto_id": a})
    assert r.status_code == 405 and r.headers["Allow"] == "GET" and r.json()["codigo"] == "METODO_NO_PERMITIDO"
    assert contar("auditoria") == antes


def test_no_hay_un_listado_global_por_ninguna_ruta_conocida(sesion):
    cliente, csrf = sesion
    for ruta in ("/auditoria/todas", "/auditoria/global", "/mi/auditoria", "/auditoria/entradas"):
        assert cliente.get(f"{API}{ruta}").status_code in (404, 405, 400)
        assert "elementos" not in cliente.get(f"{API}{ruta}").json()


def test_el_momento_de_la_entrada_es_el_de_la_operacion_y_no_se_reescribe(sesion):
    """CA-114: las entradas ya existentes no cambian al seguir operando."""
    cliente, csrf = sesion
    a = planificar_actividad(cliente, csrf, iso(0))
    marcar(cliente, csrf, a)
    primera = entradas_de(cliente, "actividad", a)[0]
    revertir(cliente, csrf, a)
    assert entradas_de(cliente, "actividad", a)[0] == primera


def test_el_momento_de_la_entrada_es_el_de_cuando_se_aplico_el_cambio_y_no_el_del_inicio_de_la_peticion(esc):
    """Determinista: otra transacción tiene la actividad bloqueada; la corrección espera. Su entrada queda con un momento
    posterior a ese bloqueo (reloj real), no con el instante en que empezó la petición. Así el orden cronológico de la
    consulta es el orden en que se aplicaron los cambios."""
    cliente, csrf0 = sesion_iniciada(esc)
    a = planificar_actividad(cliente, csrf0, iso(-5))
    v = crear_avance(cliente, csrf0, a, iso(-4), "En progreso", "Lunes")
    secreto = cliente.cookies.get(NOMBRE_COOKIE)
    csrf = cliente.get(f"{API}/sesion").json()["csrf_token"]
    otro = nuevo_cliente({NOMBRE_COOKIE: secreto})
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(
        otro.patch(f"{API}/mi/avances/{v}", json={"descripcion": "Nueva"}, headers=con_clave(csrf))))
    with get_owner_engine().begin() as c:
        c.execute(text("select 1 from actividad where id = :a for update"), {"a": a})
        antes = c.execute(text("select clock_timestamp()")).scalar_one()
        hilo.start()
        hilo.join(timeout=1.5)
        assert hilo.is_alive() and not resultado, "la corrección debía esperar al bloqueo de la actividad"
    hilo.join(timeout=15)
    assert resultado[0].status_code == 200
    momento = filas("select momento from auditoria where objeto_id = :v and operacion = 'correccion'", v=v)[0].momento
    assert momento > antes + timedelta(seconds=1)


def test_una_entrada_incoherente_de_la_base_no_se_devuelve_aunque_comparta_el_identificador(sesion, esc):
    """Defensa en profundidad: la consulta filtra también por el tipo de registro y por la propietaria de la entrada, no
    solo por el identificador del objeto, así que una fila que no coincide (de otra persona, o de otro tipo con el mismo
    identificador) nunca se devuelve."""
    cliente, csrf = sesion
    ajeno, _ = _otra_persona()
    a = planificar_actividad(cliente, csrf, iso(0))
    marcar(cliente, csrf, a)
    otra_persona = filas("select id from persona where nombre = 'Otra persona'")[0].id
    with get_owner_engine().begin() as c:
        for tipo, propietaria in (("actividad", otra_persona), ("avance", esc.persona)):
            c.execute(text("insert into auditoria (tipo_autor, autor_persona_id, operacion, tipo_objeto, objeto_id, "
                           "propietaria_registro_id, motivo) values ('persona', :p, 'correccion', :t, :o, :d, 'No debe verse')"),
                      {"p": otra_persona if propietaria == otra_persona else esc.persona, "t": tipo, "o": a, "d": propietaria})
    e = entradas_de(cliente, "actividad", a)
    assert [x["operacion"] for x in e] == ["marca_error"] and all(x["motivo"] != "No debe verse" for x in e)
