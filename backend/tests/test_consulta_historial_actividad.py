"""M4-T5 — M4-04, historial de una actividad del equipo (``GET /api/v1/equipo/actividades/{actividad_id}``) con FastAPI y PostgreSQL reales y traslados reales.

Reutiliza el mundo de M4-T4 (equipos S, T y U; Pablo de S a T y a U; Luis de U a T). Se prueba: supervisor autorizado y secuencia correcta (CA-148), colaborador rechazado, recurso
inexistente o invisible indistinguible, actividad heredada con avances visibles (CA-223, CA-273, CA-275, CA-215), heredada sin registros del equipo como referencia mínima (CA-233, CA-292,
D-09), lo protegido ausente en TODO el JSON, marcada por error de otro equipo (RA-08, CA-268), solo lectura (CA-149, CA-150), sin clasificaciones (CA-151), la equivalencia entre la
política en Python y los predicados SQL y que lo protegido no cambia la respuesta. Destructivas solo sobre ``smartwork_test``.
"""

import json
from datetime import datetime, timezone

from sqlalchemy import text

from app.compartido import visibilidad
from app.db import get_owner_engine, new_session
from app.modulos.consulta import repositorio
from tests.test_consulta_bitacora import API, H, _actividad, _avance, _bitacora, _marcar, _plan, d, entrar
from tests.test_consulta_supervision_herencia import NEUTRAL, REFERENCIA, completo, herencia  # noqa: F401

NO_EXISTE = "00000000-0000-4000-8000-0000000000aa"
CLAVES_DE_AVANCE = {"fecha_laboral", "estado", "descripcion", "motivo_bloqueo"}                      # lista cerrada del contrato: sin id, registrado_en, modificado_en ni es_reactivacion
CLAVES_DE_PLANIFICACION = {"fecha_laboral", "tipo", "descripcion"}
# Lo que pertenece al equipo U o S y NUNCA debe verlo el supervisor de T al abrir una actividad heredada (y viceversa para los de T)
PROTEGIDO_DE_U = ("Heredada sin registros de T", "Heredada con avance de T", "Heredada con planificación de T", "descripción protegida de U", "plan original protegido de U",
                  "resumen reservado de U", "motivo protegido de U", "terminada en U", "Equipo U", "Equipo S")
PROTEGIDO_DE_T = ("Tarea de Pablo", "arranque en T", "bloqueo en T", "motivo reservado de T", "plan original protegido de T", "resumen reservado de T", "Equipo T", "Equipo S")


def historial(cliente, actividad):
    return cliente.get(f"{API}/equipo/actividades/{actividad}")


def claves(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from claves(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from claves(v)


# ------------------------------------------------------------------------------------------------------ el equipo propio y la secuencia

def test_el_supervisor_ve_los_avances_autorizados_con_su_fecha_y_estado_historico_en_el_orden_de_la_secuencia(herencia):
    with get_owner_engine().begin() as c:                                        # un avance RETROACTIVO registrado después: la fecha laboral manda, no el momento de registro (CA-74)
        _avance(c, herencia["P1"], _bitacora(c, herencia["pablo"], d(-20)), "En progreso", "retroactivo en T")
    r = historial(entrar("supt"), herencia["P1"])
    c = r.json()
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store" and set(c) == {"tipo", "actividad", "avances", "planificaciones"}      # Pablo ya no es de T: sin estado actual
    assert c["tipo"] == "actividad" and c["actividad"]["forma"] == "completa" and c["actividad"]["titulo"] == "Tarea de Pablo" and "estado_actual" not in c["actividad"]
    assert [(a["fecha_laboral"], a["estado"], a["descripcion"], a["motivo_bloqueo"]) for a in c["avances"]] == [                                                # CA-148
        (d(-30).isoformat(), "En progreso", "arranque en T", None), (d(-20).isoformat(), "En progreso", "retroactivo en T", None),
        (d(-12).isoformat(), "Bloqueada", "bloqueo en T", "motivo reservado de T")]                                                                    # el motivo es de T: es suyo
    assert all(set(a) == CLAVES_DE_AVANCE for a in c["avances"]) and all(set(p) == CLAVES_DE_PLANIFICACION for p in c["planificaciones"])
    assert [(p["tipo"], p["fecha_laboral"]) for p in c["planificaciones"]] == [("original", d(-30).isoformat())]
    assert "continúa en U" not in completo(c)                                                                                                          # el avance de U no es suyo
    a1 = historial(entrar("supt"), herencia["A1"]).json()
    assert a1["estado_actual"] == "En progreso" and a1["actividad"]["forma"] == "completa" and len(a1["avances"]) == 1                                  # la propietaria es de T hoy


def test_una_marcada_por_error_con_el_origen_autorizado_se_muestra_con_su_marca_y_sin_el_origen_autorizado_no_existe(herencia):
    with get_owner_engine().begin() as c:
        b = _bitacora(c, herencia["ana"], d(-7))
        a = _actividad(c, herencia["ana"], b, "Registrada por error de Ana", estado="Pendiente"); _plan(c, a, b); _marcar(c, a, herencia["ana"])
    c = historial(entrar("supt"), a).json()
    assert c["actividad"]["titulo"] == "Registrada por error de Ana" and c["actividad"]["marca_error"]["motivo"] == "motivo de la marca"                        # RA-04: quien está autorizado la ve
    r = historial(entrar("supu"), a)                                                                                                                     # el supervisor de otro equipo: no existe
    assert r.status_code == 404 and r.json()["codigo"] == "RECURSO_NO_DISPONIBLE" and "Registrada por error" not in r.text and "motivo de la marca" not in r.text


# ------------------------------------------------------------------------------------------------------ permisos y recurso no disponible

def test_el_colaborador_recibe_403_exista_o_no_la_actividad_y_el_formato_se_valida_antes_que_el_permiso(herencia):
    ana = entrar("ana")
    r1, r2 = historial(ana, herencia["A1"]), historial(ana, NO_EXISTE)
    assert r1.status_code == r2.status_code == 403 and r1.json() == r2.json() and r1.json()["codigo"] == "OPERACION_NO_PERMITIDA"                       # no es un oráculo de existencia
    assert historial(ana, "no-es-un-uuid").status_code == 400 and historial(entrar("supt"), "no-es-un-uuid").json()["detalles"][0]["campo"] == "actividad_id"
    from tests.utiles_http import nuevo_cliente
    assert historial(nuevo_cliente(), herencia["A1"]).status_code == 401


def test_un_supervisor_con_el_acceso_desactivado_no_consulta_y_nadie_hereda_su_permiso(herencia):
    supt, ana = entrar("supt"), entrar("ana")
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() where id = :p"), {"p": herencia["supt"]})
    r = historial(supt, herencia["A1"])
    assert r.status_code == 403 and r.json()["codigo"] == "ACCESO_DESACTIVADO"
    assert historial(ana, herencia["A1"]).json()["codigo"] == "OPERACION_NO_PERMITIDA"


def test_lo_inexistente_lo_de_otro_equipo_lo_oculto_y_lo_que_no_admite_referencia_responden_lo_mismo(herencia):
    supt = entrar("supt")
    respuestas = {nombre: historial(supt, actividad) for nombre, actividad in (
        ("inexistente", NO_EXISTE), ("de otro equipo", herencia["C1"]), ("marcada por error en otro equipo", herencia["H5"]),
        ("heredada completada sin registros", herencia["H4"]), ("heredada de quien ya no es del equipo", herencia["P2"]))}
    assert {r.status_code for r in respuestas.values()} == {404}
    assert len({json.dumps(r.json(), sort_keys=True) for r in respuestas.values()}) == 1                                                                 # T-01: mismo cuerpo
    assert respuestas["inexistente"].json()["codigo"] == "RECURSO_NO_DISPONIBLE"
    for protegido in ("Tarea de Celia", "Heredada marcada por error", "motivo de la marca", "Heredada completada antes", "Tarea heredada de S"):
        assert protegido not in respuestas["inexistente"].text


# ------------------------------------------------------------------------------------------------------ actividad heredada

def test_la_actividad_heredada_con_avances_del_equipo_nuevo_se_muestra_neutral_con_solo_esos_avances(herencia):
    with get_owner_engine().begin() as c:                                        # el avance protegido de U lleva un motivo de bloqueo
        c.execute(text("update avance set estado = 'Bloqueada', motivo_bloqueo = 'motivo protegido de U' where actividad_id = :h and descripcion = 'descripción protegida de U'"),
                  {"h": herencia["H2"]})
    r = historial(entrar("supt"), herencia["H2"])
    c = r.json()
    assert r.status_code == 200 and c["tipo"] == "actividad" and set(c["actividad"]) == NEUTRAL and c["actividad"]["referencia_neutral"] == "Actividad en continuidad"   # CA-275
    assert [(a["fecha_laboral"], a["estado"], a["descripcion"], a["motivo_bloqueo"]) for a in c["avances"]] == [
        (d(-5).isoformat(), "Bloqueada", "bloqueo de Luis en T", "motivo de Luis en T")]                                                                # CA-223: el de T, con su detalle
    assert c["planificaciones"] == [] and c["estado_actual"] == "Bloqueada"                                                                              # el plan original es de U
    texto = completo(c)
    assert not any(p in texto for p in PROTEGIDO_DE_U), [p for p in PROTEGIDO_DE_U if p in texto]                                                        # CA-273, CA-215


def test_el_supervisor_del_equipo_nuevo_no_obtiene_titulo_descripciones_ni_motivos_del_equipo_anterior(herencia):
    r = historial(entrar("supu"), herencia["P1"])
    c = r.json()
    assert c["tipo"] == "actividad" and set(c["actividad"]) == NEUTRAL and [a["descripcion"] for a in c["avances"]] == ["continúa en U"]                 # CA-275, CA-215
    assert c["planificaciones"] == [] and c["estado_actual"] == "En progreso"
    assert not any(p in completo(c) for p in PROTEGIDO_DE_T), [p for p in PROTEGIDO_DE_T if p in completo(c)]


def test_el_equipo_anterior_conserva_su_historial_autorizado_sin_estado_actual_ni_lo_posterior(herencia):
    supu = entrar("supu")
    h1, h2 = historial(supu, herencia["H1"]).json(), historial(supu, herencia["H2"]).json()
    assert h1["actividad"]["titulo"] == "Heredada sin registros de T" and [a["descripcion"] for a in h1["avances"]] == ["descripción protegida de U"]    # su origen es de U
    assert [p["descripcion"] for p in h1["planificaciones"]] == ["plan original protegido de U"] and "estado_actual" not in h1                           # Luis es hoy de T
    assert [a["descripcion"] for a in h2["avances"]] == ["descripción protegida de U"] and "bloqueo de Luis en T" not in completo(h2) and "motivo de Luis en T" not in completo(h2)


def test_la_heredada_sin_registros_del_equipo_es_solo_la_referencia_minima_y_pasa_a_neutral_cuando_el_equipo_registra(herencia):
    supt = entrar("supt")
    r = historial(supt, herencia["H1"])
    c = r.json()
    assert r.status_code == 200 and set(c) == REFERENCIA and c["tipo"] == "referencia_minima" and c["iniciada_en_otro_equipo"] is True                   # CA-233, CA-292, D-09
    assert set(c["actividad"]) == NEUTRAL and c["propietaria_id"] == str(herencia["luis"]) and c["estado_actual"] == "En progreso"
    assert not any(p in completo(c) for p in PROTEGIDO_DE_U + ("avances", "planificaciones", "titulo", "estado_al_corte", "motivo", "descripcion"))
    pu = historial(entrar("supu"), herencia["P2"]).json()                                                                                                  # Pablo es de U y la actividad es de S
    assert set(pu) == REFERENCIA and pu["estado_actual"] == "En progreso" and "Tarea heredada de S" not in completo(pu) and "avance en S" not in completo(pu)
    with get_owner_engine().begin() as c2:                                                                                                                 # Luis registra en T un avance sobre la heredada
        _avance(c2, herencia["H1"], _bitacora(c2, herencia["luis"], d(-1)), "Bloqueada", "bloqueo propio de T", "motivo propio de T")
    n = historial(supt, herencia["H1"]).json()
    assert n["tipo"] == "actividad" and set(n["actividad"]) == NEUTRAL and [a["descripcion"] for a in n["avances"]] == ["bloqueo propio de T"]
    assert "descripción protegida de U" not in completo(n)


# ------------------------------------------------------------------------------------------------------ lectura pura, sin clasificaciones y sin filtraciones

def test_la_ruta_es_de_solo_lectura_y_leer_no_cambia_nada(herencia):
    supt = entrar("supt")
    contar = text("select (select count(*) from actividad) || '/' || (select count(*) from avance) || '/' || (select count(*) from planificacion) || '/' || (select count(*) from auditoria)")
    with get_owner_engine().connect() as c:
        antes = c.execute(contar).scalar_one()
    for a in (herencia["A1"], herencia["P1"], herencia["H1"], herencia["H2"]):
        assert historial(supt, a).status_code == 200
    for metodo in ("post", "put", "patch", "delete"):
        r = getattr(supt, metodo)(f"{API}/equipo/actividades/{herencia['A1']}", headers={"Origin": "https://testserver"})
        assert r.status_code == 405 and r.headers["allow"] == "GET", metodo                                                                             # CA-149, CA-150
    with get_owner_engine().connect() as c:
        assert c.execute(contar).scalar_one() == antes


def test_ninguna_respuesta_contiene_clasificaciones_ni_campos_fuera_de_la_lista_cerrada(herencia):
    supt, supu = entrar("supt"), entrar("supu")
    casos = [historial(supt, herencia[k]).json() for k in ("A1", "P1", "H1", "H2")] + [historial(supu, herencia[k]).json() for k in ("P1", "P2", "H1")]
    prohibidas = {"ranking", "puntuacion", "puntaje", "clasificacion", "score", "equipo_id", "equipo", "equipo_anterior", "bitacora_id", "bitacora_origen_id", "total_avances", "numero_de_avances"}
    for c in casos:
        assert not (set(claves(c)) & prohibidas), c["tipo"]                                                                                              # CA-151
        assert set(c) in ({"tipo", "actividad", "avances", "planificaciones"}, {"tipo", "actividad", "avances", "planificaciones", "estado_actual"}, REFERENCIA)
        if c["tipo"] == "actividad":
            assert all(set(a) == CLAVES_DE_AVANCE for a in c["avances"]) and all(set(p) == CLAVES_DE_PLANIFICACION for p in c["planificaciones"])
            assert set(c["actividad"]) in (NEUTRAL, {"forma", "id", "propietaria_id", "titulo", "origen", "marca_error", "fecha_laboral_origen", "creada_en"})


def test_lo_protegido_de_otros_equipos_no_cambia_la_respuesta(herencia):
    supt, supu = entrar("supt"), entrar("supu")
    pedidos = [(supt, herencia[k]) for k in ("H1", "H2", "H3", "P1")] + [(supu, herencia[k]) for k in ("P1", "P2")]
    antes = [historial(cl, a).json() for cl, a in pedidos]
    with get_owner_engine().begin() as c:                                        # cambia lo que NO pueden ver: avances, planes y bitácoras del otro equipo
        c.execute(text("update avance set estado = 'Bloqueada', descripcion = 'otra cosa protegida', motivo_bloqueo = 'otro motivo protegido' "
                       "where descripcion in ('descripción protegida de U', 'arranque en T', 'avance en S')"))
        c.execute(text("update planificacion set descripcion = 'otro plan protegido' where descripcion in ('plan original protegido de U', 'plan original protegido de T')"))
        c.execute(text("update bitacora set resumen = 'otro resumen protegido' where resumen like 'resumen reservado%'"))
    despues = [historial(cl, a).json() for cl, a in pedidos]
    for cambiado, original, (cl, a) in zip(despues, antes, pedidos):
        if original["tipo"] == "referencia_minima" or original["actividad"]["forma"] == "neutral":                                                         # lo protegido no entra en esas formas
            assert cambiado == original, a


# ------------------------------------------------------------------------------------------------------ la política compartida

def test_los_registros_autorizados_que_calcula_sql_coinciden_con_la_politica_en_python(herencia):
    db = new_session()
    try:
        ahora = datetime.now(timezone.utc)
        with get_owner_engine().connect() as c:
            avances = c.execute(text("select av.id, av.actividad_id as a, b.fecha_laboral as f from avance av join bitacora b on b.id = av.bitacora_id")).all()
            planes = c.execute(text("select pl.id, pl.actividad_id as a, b.fecha_laboral as f from planificacion pl join bitacora b on b.id = pl.bitacora_id")).all()
            origen = {r.id: (r.propietaria_id, r.fecha) for r in c.execute(text("select a.id, a.propietaria_id, b.fecha_laboral as fecha from actividad a join bitacora b on b.id = a.bitacora_origen_id")).all()}
        for quien in ("supt", "supu"):
            consultante = visibilidad.consultante_de(db, herencia[quien], hoy=H, ahora=ahora)
            for actividad, (propietaria, fecha_origen) in origen.items():
                esperados_av = {v.id for v in avances if v.a == actividad and visibilidad.pertenece_al_equipo_en(db, consultante, propietaria, v.f)}
                esperados_pl = {p.id for p in planes if p.a == actividad and visibilidad.pertenece_al_equipo_en(db, consultante, propietaria, p.f)}
                assert {v.id for v in repositorio.avances_autorizados_de_la_actividad(db, consultante, actividad)} == esperados_av, (quien, actividad)
                assert {p.id for p in repositorio.planificaciones_autorizadas_de_la_actividad(db, consultante, actividad)} == esperados_pl, (quien, actividad)
                fila = repositorio.actividad_con_hechos_de_autorizacion(db, consultante, actividad)
                python = visibilidad.pertenece_al_equipo_en(db, consultante, propietaria, fecha_origen)
                assert fila.origen_autorizado == python and (fila.titulo is not None) == python and (fila.creada_en is not None) == python, (quien, actividad)
                assert (fila.motivo_error is None or python) and (fila.fecha_laboral_origen is not None) == python
        assert repositorio.actividad_con_hechos_de_autorizacion(db, consultante, NO_EXISTE) is None
    finally:
        db.close()
