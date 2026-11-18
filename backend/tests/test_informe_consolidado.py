"""M5-T2 — núcleo determinista del informe consolidado (servicio interno, sin HTTP, sin IA, sin narrativa) con PostgreSQL real.

Pruebas focalizadas (metodología ligera): supervisor autorizado; colaborador, ex supervisor, supervisor desactivado y sin pertenencia rechazados (CA-169); equipo ajeno o inexistente (CA-170);
personas y avances autorizados por pertenencia histórica; traslados entre equipos (CA-228, CA-229, CA-277); exclusión de lo protegido y del estado al corte derivado de otro equipo (CA-235);
marcadas por error y planificaciones conservadas; coherencia con el informe individual cuando las poblaciones coinciden (y su diferencia declarada para la supervisora que estuvo en otro
equipo); sin datos; estructura de campos cerrados sin rankings, puntuaciones ni datos de acceso; y solo lectura. Reutiliza el escenario de ``test_informe_individual`` y lo amplía.
Destructivas solo sobre ``smartwork_test``. Datos siempre ficticios.
"""

import dataclasses
import json
import re
import uuid

import pytest
from sqlalchemy import text

from app.compartido.visibilidad import consultante_de
from app.db import get_owner_engine
from app.errores import AppError
from app.modulos.informes.consolidado import clave_alfabetica, preparar_informe_consolidado
from app.modulos.informes.individual import preparar_informe_individual
from tests.fabricas import crear_equipo, crear_identidad, crear_persona, crear_pertenencia
from tests.test_informe_individual import CLAVE, H, _actividad, _avance, _bitacora, d, db, mundo  # noqa: F401  (fixtures y ayudas del escenario de M5-T1)


@pytest.fixture()
def mundo2(mundo):
    """El escenario de M5-T1 más: Beto con cinco avances (más que Ana, para que el orden alfabético no coincida con el de cantidad), una ex supervisora (``exsup``, de W, que ahora es colaboradora de T),
    y el equipo W con su supervisora (``supw``, que antes estuvo en U con un avance) y una colaboradora (``wila``)."""
    m = dict(mundo)
    with get_owner_engine().begin() as c:
        for n in range(8, 3, -1):
            b = _bitacora(c, m["beto"], d(-n))
            _avance(c, _actividad(c, m["beto"], b, f"Tarea de Beto {n}"), b, "En progreso", f"Avance de Beto {n}")
        t = c.execute(text("select equipo_id from pertenencia where persona_id = :p and hasta_exclusivo is null"), {"p": m["supt"]}).scalar_one()
        u = c.execute(text("select equipo_id from pertenencia where persona_id = :p and hasta_exclusivo is null"), {"p": m["supu"]}).scalar_one()
        org = c.execute(text("select organizacion_id from equipo where id = :e"), {"e": t}).scalar_one()
        w = crear_equipo(c, org, "Equipo W-reservado")
        exsup = crear_persona(c, "exsup")                                                  # supervisora de W hasta que lo releva supw; hoy colaboradora de T
        crear_pertenencia(c, exsup, w, "supervisor", desde=d(-90), hasta=d(-40))
        crear_pertenencia(c, exsup, t, "colaborador", desde=d(-40))
        crear_identidad(c, exsup, "acceso-exsup-privado", CLAVE)
        supw = crear_persona(c, "supw")
        crear_pertenencia(c, supw, u, "colaborador", desde=d(-90), hasta=d(-40))
        crear_pertenencia(c, supw, w, "supervisor", desde=d(-40))
        crear_identidad(c, supw, "acceso-supw-privado", CLAVE)
        wila = crear_persona(c, "wila")
        crear_pertenencia(c, wila, w, "colaborador", desde=d(-90))
        crear_identidad(c, wila, "acceso-wila-privado", CLAVE)
        for persona, dias, titulo in ((supw, 50, "Trabajo previo en U"), (supw, 2, "Trabajo en W"), (wila, 2, "Trabajo de Wila")):
            b = _bitacora(c, persona, d(-dias))
            _avance(c, _actividad(c, persona, b, titulo), b, "En progreso", f"Avance: {titulo}")
        m.update(exsup=exsup, supw=supw, wila=wila, equipo_t=t, equipo_u=u, equipo_w=w)
    return m


def consolidado(db, m, quien, equipo, desde=-100, hasta=10):
    return preparar_informe_consolidado(db, consultante_de(db, m[quien], hoy=H), None if equipo is None else m[equipo] if isinstance(equipo, str) else equipo, d(desde), d(hasta))


def individual(db, m, quien, persona, desde=-100, hasta=10):
    return preparar_informe_individual(db, consultante_de(db, m[quien], hoy=H), None if persona is None else m[persona], d(desde), d(hasta))


def error(db, m, quien, equipo=None, desde=-100, hasta=10):
    with pytest.raises(AppError) as e:
        consolidado(db, m, quien, equipo, desde, hasta)
    return e.value


def nombres(r):
    return [p.persona.nombre for p in r.personas]


def sin_refs(p):
    """Lo que dice un bloque, sin las referencias opacas (las del consolidado son únicas en todo el informe y las del individual empiezan en 1)."""
    return [(h.fecha_laboral, h.estado, h.descripcion, h.motivo_bloqueo) for h in p.hechos], [(a.forma, a.texto, a.planificada) for a in p.actividades]


def todo_el_texto(r) -> str:
    return json.dumps(dataclasses.asdict(r), default=str, ensure_ascii=False)


# ------------------------------------------------------------------------------------------------------ supervisor autorizado

def test_el_supervisor_obtiene_el_consolidado_con_las_personas_en_orden_alfabetico_y_no_por_cantidad(db, mundo2):
    r = consolidado(db, mundo2, "supt", None)
    assert (r.tipo, r.sin_datos) == ("consolidado", False)
    # solo las personas con avances autorizados del equipo, por nombre. Beto tiene más avances que Ana: si se ordenase por cantidad iría primero
    assert nombres(r) == ["ana", "beto", "gina", "pablo", "supt"]
    cantidad = {p.persona.nombre: p.agregaciones.avances for p in r.personas}
    assert cantidad == {"ana": 4, "beto": 5, "gina": 1, "pablo": 2, "supt": 1}
    assert nombres(r) != sorted(cantidad, key=lambda n: -cantidad[n])
    assert consolidado(db, mundo2, "supt", mundo2["equipo_t"]) == r                       # el equipo explícito es el que supervisa: lo mismo
    # referencias opacas únicas en TODO el informe, también entre personas
    refs_h = [h.ref for p in r.personas for h in p.hechos]
    refs_a = [a.ref for p in r.personas for a in p.actividades]
    assert len(set(refs_h)) == len(refs_h) == 13 and len(set(refs_a)) == len(refs_a)
    # la sección de equipo es la misma definición aplicada al conjunto: sumas, salvo las jornadas (fechas distintas del conjunto)
    e, ps = r.agregaciones_del_equipo, [p.agregaciones for p in r.personas]
    assert e.avances == sum(a.avances for a in ps) == 13
    assert e.actividades_con_registros == sum(a.actividades_con_registros for a in ps)
    assert e.jornadas_con_registros == len({h.fecha_laboral for p in r.personas for h in p.hechos}) < sum(a.jornadas_con_registros for a in ps)
    assert dataclasses.astuple(e.actividades_por_estado_al_corte) == tuple(map(sum, zip(*(dataclasses.astuple(a.actividades_por_estado_al_corte) for a in ps))))
    assert consolidado(db, mundo2, "supt", None) == r                                       # determinista


# ------------------------------------------------------------------------------------------------------ rechazos

def test_solo_el_supervisor_vigente_con_acceso_efectivo_genera_el_consolidado(db, mundo2):
    assert error(db, mundo2, "ana").codigo == "OPERACION_NO_PERMITIDA"                      # colaborador (CA-169)
    assert error(db, mundo2, "ana", mundo2["equipo_u"]).codigo == "OPERACION_NO_PERMITIDA"  # el rol se decide antes que el equipo: no revela nada
    assert error(db, mundo2, "exsup").codigo == "OPERACION_NO_PERMITIDA"                    # fue supervisora y ya no lo es: sin rol vigente
    with get_owner_engine().begin() as c:
        c.execute(text("update persona set acceso_desactivado_en = now() - interval '1 day' where id = :p"), {"p": mundo2["supu"]})
    assert error(db, mundo2, "supu").codigo == "ACCESO_DESACTIVADO"                         # un supervisor desactivado no supervisa (RA-12)
    assert error(db, mundo2, "zeta").codigo == "ACCESO_DESACTIVADO"
    assert error(db, mundo2, "gina").codigo == "SIN_PERTENENCIA_VIGENTE"                    # sin pertenencia vigente
    with pytest.raises(AppError) as e:                                                      # el formato se evalúa antes que el rol y no depende de nadie
        consolidado(db, mundo2, "ana", None, 5, -5)
    assert (e.value.codigo, e.value.detalles) == ("SOLICITUD_INVALIDA", [{"campo": "desde", "motivo": "posterior_a_hasta"}])


def test_un_equipo_ajeno_o_inexistente_es_el_mismo_404(db, mundo2):
    uniforme = AppError("RECURSO_NO_DISPONIBLE")
    for equipo in (mundo2["equipo_u"], mundo2["equipo_w"], uuid.uuid4()):                  # otro equipo de la organización, otro del mismo mundo e inexistente (CA-170)
        e = error(db, mundo2, "supt", equipo)
        assert (e.codigo, e.estado, e.mensaje, e.detalles) == (uniforme.codigo, uniforme.estado, uniforme.mensaje, uniforme.detalles)


# ------------------------------------------------------------------------------------------------------ traslados y datos protegidos

def test_una_persona_trasladada_solo_aporta_a_cada_equipo_lo_de_sus_fechas(db, mundo2):
    t, u = consolidado(db, mundo2, "supt", None), consolidado(db, mundo2, "supu", None)
    pablo_t = next(p for p in t.personas if p.persona.nombre == "pablo")
    pablo_u = next(p for p in u.personas if p.persona.nombre == "pablo")
    assert [h.fecha_laboral for h in pablo_t.hechos] == [d(-30), d(-30)]                    # CA-229: nada posterior al traslado
    assert [h.fecha_laboral for h in pablo_u.hechos] == [d(-3), d(-3)]                      # CA-228: nada anterior al traslado
    assert nombres(u) == ["celia", "pablo", "supw"]                                         # supw, hoy supervisora de W, trabajó en U hasta d(-40): ese avance es de U
    assert [b.motivo for b in pablo_t.bloqueos] == ["motivo-reservado-del-equipo-T"] and pablo_u.bloqueos == ()
    texto_u = todo_el_texto(u)
    for protegido in ("Tarea secreta del equipo T", "Avance interno del equipo T", "Bloqueo en el equipo T", "motivo-reservado-del-equipo-T", "resumen reservado del equipo T", "Equipo T-reservado"):
        assert protegido not in texto_u                                                     # CA-277
    assert [(a.forma, a.texto, a.planificada) for a in pablo_u.actividades] == [("neutral", "Actividad en continuidad", None), ("completa", "Tarea nueva en U", False)]
    texto_t = todo_el_texto(t)
    for ajeno in ("Continúa en el equipo U", "Tarea nueva en U", "Arranca en U", "Equipo U-reservado"):
        assert ajeno not in texto_t


def test_el_estado_al_corte_que_determina_un_avance_de_otro_equipo_no_se_muestra_ni_se_sustituye(db, mundo2):
    cortes = lambda p: dataclasses.astuple(p.agregaciones.actividades_por_estado_al_corte)  # (pendiente, en progreso, bloqueada, completada, no disponible)  # noqa: E731
    t, u = consolidado(db, mundo2, "supt", None), consolidado(db, mundo2, "supu", None)
    # equipo T con el corte en d(10): el último avance de la actividad de Pablo es de U (protegido): no disponible, y NO el Bloqueada anterior de T (CA-235)
    assert cortes(next(p for p in t.personas if p.persona.nombre == "pablo")) == (0, 0, 0, 0, 1)
    assert t.agregaciones_del_equipo.actividades_por_estado_al_corte.estado_no_disponible == 1
    # equipo U: el último avance es suyo y se muestra; sin revelar el Bloqueada de T
    assert cortes(next(p for p in u.personas if p.persona.nombre == "pablo")) == (1, 1, 0, 0, 0)
    assert "Bloqueada" not in todo_el_texto(u)
    # con el corte anterior al traslado, T sí muestra su último avance
    assert cortes(next(p for p in consolidado(db, mundo2, "supt", None, -40, -20).personas if p.persona.nombre == "pablo")) == (0, 0, 1, 0, 0)
    for r in (t, u):
        for p in r.personas:
            assert sum(cortes(p)) == p.agregaciones.actividades_con_registros


def test_las_marcadas_por_error_y_las_planificaciones_conservadas_no_cuentan(db, mundo2):
    r = consolidado(db, mundo2, "supt", None)
    texto = todo_el_texto(r)
    assert "Tarea registrada por error" not in texto and "avance de la tarea errónea" not in texto      # marcada por error de Ana
    assert "Plan conservado de Gina" not in texto and "Plan futuro de Ana" not in texto                # planificaciones: no son registros
    assert next(p for p in r.personas if p.persona.nombre == "ana").agregaciones.avances == 4
    assert next(p for p in r.personas if p.persona.nombre == "gina").agregaciones.avances == 1


# ------------------------------------------------------------------------------------------------------ coherencia con el informe individual

def test_las_agregaciones_por_persona_coinciden_con_las_del_informe_individual_cuando_las_poblaciones_coinciden(db, mundo2):
    for quien, equipo_propio in (("supt", None), ("supu", None), ("supw", None)):
        r = consolidado(db, mundo2, quien, equipo_propio)
        for p in r.personas:
            nombre = p.persona.nombre
            if nombre == "supw":
                continue                                                                    # la diferencia declarada, comprobada abajo
            i = individual(db, mundo2, quien, nombre)
            assert (p.agregaciones, sin_refs(p)) == (i.agregaciones, sin_refs(i)), (quien, nombre)


def test_la_supervisora_que_estuvo_en_otro_equipo_cuenta_distinto_en_su_informe_propio_y_en_el_del_equipo(db, mundo2):
    propio = individual(db, mundo2, "supw", None)                                           # la propietaria obtiene todo lo suyo, de ambos equipos (CA-227)
    del_equipo = next(p for p in consolidado(db, mundo2, "supw", None).personas if p.persona.nombre == "supw")
    assert propio.agregaciones.avances == 2 and del_equipo.agregaciones.avances == 1
    assert [a.texto for a in del_equipo.actividades] == ["Trabajo en W"] and "Trabajo previo en U" not in todo_el_texto(consolidado(db, mundo2, "supw", None))
    assert nombres(consolidado(db, mundo2, "supw", None)) == ["supw", "wila"]


# ------------------------------------------------------------------------------------------------------ sin datos, privacidad y solo lectura

def test_sin_avances_autorizados_el_consolidado_dice_que_no_hay_datos(db, mundo2):
    r = consolidado(db, mundo2, "supt", None, 1, 10)                                        # solo hay planificaciones (futuras y conservadas)
    assert (r.sin_datos, r.personas, r.agregaciones_del_equipo) == (True, (), None)


CLAVES_CERRADAS = {"tipo", "desde", "hasta", "sin_datos", "personas", "persona", "id", "nombre", "actividades", "ref", "forma", "texto", "planificada", "hechos", "fecha_laboral",
                   "actividad_ref", "estado", "descripcion", "motivo_bloqueo", "bloqueos", "hecho_ref", "motivo", "agregaciones", "avances", "jornadas_con_registros",
                   "actividades_con_registros", "actividades_por_origen", "planificadas", "no_planificadas", "origen_no_disponible", "actividades_con_bloqueo",
                   "actividades_por_estado_al_corte", "pendiente", "en_progreso", "bloqueada", "completada", "estado_no_disponible", "agregaciones_del_equipo"}


def _claves(valor, acumulado):
    if isinstance(valor, dict):
        for k, v in valor.items():
            acumulado.add(k)
            _claves(v, acumulado)
    elif isinstance(valor, (list, tuple)):
        for v in valor:
            _claves(v, acumulado)
    return acumulado


def test_la_estructura_tiene_campos_cerrados_sin_rankings_puntuaciones_ni_datos_de_acceso(db, mundo2):
    for quien in ("supt", "supu", "supw"):
        r = consolidado(db, mundo2, quien, None)
        claves = _claves(dataclasses.asdict(r), set())
        assert claves <= CLAVES_CERRADAS, claves - CLAVES_CERRADAS
        assert not [c for c in claves if re.search(r"rank|puntu|score|porcentaje|valoraci|rendimiento|orden|posicion", c)]
        assert {f.name for f in dataclasses.fields(type(r.personas[0].persona))} == {"id", "nombre"}                      # de cada persona, solo su identificador y su nombre
        texto = todo_el_texto(r)
        for sensible in ("acceso-", "-privado", CLAVE, "argon2", "Equipo T-reservado", "Equipo U-reservado", "Equipo W-reservado", "resumen reservado", "hash", "@"):
            assert sensible not in texto, (quien, sensible)


def test_el_consolidado_es_de_solo_lectura(db, mundo2):
    tablas = ("bitacora", "actividad", "planificacion", "avance", "auditoria", "persona", "pertenencia", "equipo")
    antes = {t: db.execute(text(f"select count(*) from {t}")).scalar() for t in tablas}
    consolidado(db, mundo2, "supt", None)
    consolidado(db, mundo2, "supu", None)
    db.rollback()
    assert {t: db.execute(text(f"select count(*) from {t}")).scalar() for t in tablas} == antes


# ------------------------------------------------------------------------------------------------------ orden alfabético (C-3)

def test_el_criterio_de_comparacion_ignora_mayusculas_y_acentos_y_pone_la_enie_tras_la_n():
    nombres_ = ["Zoe", "Álvaro", "alba", "Ñandú", "Nora", "Óscar", "Ana", "ana"]
    ordenados = sorted(nombres_, key=lambda n: (clave_alfabetica(n), n))
    assert [n for n in ordenados if n not in ("Ana", "ana")] == ["alba", "Álvaro", "Nora", "Ñandú", "Óscar", "Zoe"]
    assert {ordenados[2], ordenados[3]} == {"Ana", "ana"} and clave_alfabetica("Ana") == clave_alfabetica("ana")      # mayúsculas: comparan igual, y «Álvaro» va antes de «Ana»
    assert clave_alfabetica("José") == clave_alfabetica("jose") == "jose"                      # acentos: comparan igual
    assert clave_alfabetica("Muñoz") > clave_alfabetica("Munzo") and clave_alfabetica("Muñoz") < clave_alfabetica("Muoz")     # ñ: después de toda «n», antes de la «o»
    assert clave_alfabetica("ña") == clave_alfabetica("ña")                              # la forma descompuesta de la ñ se trata igual


def test_el_orden_alfabetico_del_consolidado_es_estable_y_no_altera_los_nombres_mostrados(db, mundo):
    with get_owner_engine().begin() as c:
        org = c.execute(text("select organizacion_id from equipo limit 1")).scalar_one()
        equipo = crear_equipo(c, org, "Equipo de nombres")
        sup = crear_persona(c, "Supervisor de nombres")
        crear_pertenencia(c, sup, equipo, "supervisor", desde=d(-90))
        crear_identidad(c, sup, "acceso-nombres-privado", CLAVE)
        ids = {}
        for nombre in ("Zoe", "Álvaro", "alba", "Ñandú", "Nora", "Óscar", "José", "Jose"):
            p = ids[nombre] = crear_persona(c, nombre)
            crear_pertenencia(c, p, equipo, "colaborador", desde=d(-90))
            b = _bitacora(c, p, d(-2))
            _avance(c, _actividad(c, p, b, f"Tarea de {nombre}"), b, "En progreso", "Avance")
    m = {"sup": sup}
    r = preparar_informe_consolidado(db, consultante_de(db, sup, hoy=H), None, d(-5), d(0))
    mostrados = nombres(r)
    assert set(mostrados) == set(ids)                                                         # los nombres se muestran tal cual (con sus acentos y mayúsculas)
    sin_empate = [n for n in mostrados if n not in ("José", "Jose")]
    assert sin_empate == ["alba", "Álvaro", "Nora", "Ñandú", "Óscar", "Zoe"]
    jose = [p.persona.id for p in r.personas if p.persona.nombre in ("José", "Jose")]
    assert jose == sorted(jose) and mostrados.index("José") + mostrados.index("Jose") == 2 * mostrados.index("Jose") + (1 if mostrados.index("José") > mostrados.index("Jose") else -1)   # contiguos
    assert nombres(preparar_informe_consolidado(db, consultante_de(db, sup, hoy=H), None, d(-5), d(0))) == mostrados     # estable entre ejecuciones
