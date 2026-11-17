"""M1-T5 — el enlace histórico entre una cancelación o sustitución y la operación ORIGINAL que retira (decisión 6 de M1-T4).

La entrada de cancelación conserva los identificadores de las pertenencias retiradas. La operación original es la ÚNICA entrada de
auditoría que las creó: su ``valor_nuevo`` las lista como nuevas (``cambios[].pertenencia_nueva``, ``pertenencias_nuevas``) o, para una
alta de M1-02b, es la entrada de alta de esa persona. Estas pruebas demuestran la unicidad de ese enlace en todos los orígenes posibles de un
intervalo programado y dejan constancia del ÚNICO caso que los datos por sí solos no desambiguan: el fin de una finalización que se
registra, se cancela y se vuelve a registrar con la misma fecha. Las pruebas destructivas corren solo sobre ``smartwork_test``.
"""

import uuid

from app.provision.programacion import CancelacionSolicitada, FinalizacionSolicitada, cancelar_operacion_programada, finalizar_pertenencia
from app.provision.servicio import crear_persona, registrar_traslado
from tests.test_programacion import canc, cancelar, entradas, finalizar, fin
from tests.test_traslados import HOY, cambio, dia, mundo, operador, orden  # noqa: F401  (fixtures y asistentes compartidos)
from tests.utiles_m2 import filas


def creadoras(intervalo_id) -> list:
    """Entradas de auditoría que CREARON ese intervalo (lo listan como nuevo)."""
    return filas(
        "select id, operacion from auditoria where "
        "(valor_nuevo -> 'cambios') @> jsonb_build_array(jsonb_build_object('pertenencia_nueva', jsonb_build_object('id', cast(:i as text)))) "
        "or (valor_nuevo -> 'pertenencias_nuevas') @> jsonb_build_array(jsonb_build_object('id', cast(:i as text))) order by momento, id", i=str(intervalo_id))


def retirados_por(operacion: str) -> list[str]:
    return [r["id"] for (_, _, _, _, _, _, anterior, _) in entradas(operacion) for r in anterior["pertenencias_retiradas"]]


def test_un_traslado_cancelado_se_enlaza_con_exactamente_una_entrada_original(operador, mundo):
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "C1", "U", "colaborador", dia(3))])
    cancelar(operador, canc(mundo, "C1", "traslado", dia(3)))
    [retirada] = retirados_por("cancelacion_operacion")
    assert [op for _, op in creadoras(retirada)] == ["cambio_pertenencia"]


def test_una_sustitucion_cancelada_se_enlaza_con_la_entrada_de_la_sustitucion_y_no_con_la_del_traslado_inicial(operador, mundo):
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "C1", "U", "colaborador", dia(3))])
    cancelar(operador, canc(mundo, "C1", "traslado", dia(3)), cambios=[cambio(mundo, "C1", "W", "colaborador", dia(5))])      # sustituir
    cancelar(operador, canc(mundo, "C1", "traslado", dia(5)))                                                               # y cancelar la sustituta
    inicial, sustituta = retirados_por("sustitucion_operacion")[0], retirados_por("cancelacion_operacion")[0]
    assert [op for _, op in creadoras(inicial)] == ["cambio_pertenencia"]
    assert [op for _, op in creadoras(sustituta)] == ["sustitucion_operacion"]
    assert creadoras(inicial)[0][0] != creadoras(sustituta)[0][0]


def test_un_relevo_registrado_con_una_finalizacion_y_cancelado_se_enlaza_con_la_entrada_de_la_finalizacion(operador, mundo):
    finalizar(operador, fin(mundo, "ST", dia(4)), cambios=[cambio(mundo, "C1", "T", "supervisor", dia(4))])
    cancelar(operador, canc(mundo, "ST", "finalizacion", dia(4)), canc(mundo, "C1", "cambio_de_rol", dia(4)))
    for retirada in retirados_por("cancelacion_operacion"):
        assert [op for _, op in creadoras(retirada)] == ["finalizacion_pertenencia"]


def test_un_alta_cancelada_se_enlaza_con_la_unica_entrada_de_alta_de_esa_persona(operador, mundo):
    """La entrada de alta de M1-02b no lista el identificador de la pertenencia: el enlace es la persona (objeto de la entrada) y la fecha de inicio."""
    n = orden(crear_persona, operador, nombre="Futura", identificador_acceso="futura", equipo_id=mundo.eq["U"], rol="colaborador", desde=dia(10))
    cancelar(operador, CancelacionSolicitada(n.persona_id, "alta", dia(10)))
    [retirada] = [r for (_, _, _, _, _, _, anterior, _) in entradas("cancelacion_operacion") for r in anterior["pertenencias_retiradas"]]
    altas = filas("select valor_nuevo from auditoria where operacion = 'alta' and tipo_objeto = 'persona' and objeto_id = :p", p=uuid.UUID(retirada["persona"]))
    assert len(altas) == 1 and altas[0][0]["desde"] == retirada["desde"] == dia(10).isoformat() and altas[0][0]["equipo"] == retirada["equipo"]
    assert creadoras(retirada["id"]) == []                                              # ninguna otra entrada creó ese intervalo


def test_cada_pertenencia_programada_la_crea_una_sola_entrada_en_todos_los_origenes(operador, mundo):
    """Propiedad sobre todas las entradas que crean pertenencias: ningún identificador aparece como creado por dos entradas."""
    orden(registrar_traslado, operador, cambios=[cambio(mundo, "C1", "U", "colaborador", dia(3))])
    cancelar(operador, canc(mundo, "C1", "traslado", dia(3)), cambios=[cambio(mundo, "C1", "W", "colaborador", dia(5))])
    finalizar(operador, fin(mundo, "ST", dia(8)), cambios=[cambio(mundo, "C2", "T", "supervisor", dia(8))])
    creadas = [i for (_, _, _, _, _, _, _, nuevo) in (e for op in ("cambio_pertenencia", "sustitucion_operacion", "finalizacion_pertenencia") for e in entradas(op))
               for i in ([c["pertenencia_nueva"]["id"] for c in nuevo.get("cambios", [])] + [p["id"] for p in nuevo.get("pertenencias_nuevas", [])])]
    assert len(creadas) == len(set(creadas)) == 3                                       # C1 a W, y los dos de ese relevo con finalización: cada uno, una sola vez


# ----- el único caso ambiguo --------------------------------------------------------------------------------------------

def fijaron_el_fin(intervalo_id, fecha) -> list:
    """Entradas que fijaron el fin ``fecha`` en ese intervalo (por cierre en un traslado o en una finalización)."""
    return filas(
        "select id, operacion from auditoria where "
        "(valor_nuevo -> 'cambios') @> jsonb_build_array(jsonb_build_object('pertenencia_cerrada', jsonb_build_object('id', cast(:i as text), 'hasta_exclusivo', cast(:f as text)))) "
        "or (valor_nuevo -> 'fines_nuevos') @> jsonb_build_array(jsonb_build_object('id', cast(:i as text), 'hasta_exclusivo', cast(:f as text))) order by momento, id",
        i=str(intervalo_id), f=fecha.isoformat())


def test_una_finalizacion_repetida_con_la_misma_fecha_no_se_desambigua_solo_con_los_datos_sino_por_el_orden(operador, mundo):
    """CASO AMBIGUO DOCUMENTADO: se finaliza el día 4, se cancela y se vuelve a finalizar el día 4. Dos entradas fijaron el mismo fin en el
    mismo intervalo; la original de la última cancelación es la más reciente anterior a ella. Con una finalización de otra fecha no hay duda."""
    finalizar(operador, fin(mundo, "C2", dia(4)))
    cancelar(operador, canc(mundo, "C2", "finalizacion", dia(4)))
    finalizar(operador, fin(mundo, "C2", dia(4)))
    cancelar(operador, canc(mundo, "C2", "finalizacion", dia(4)))
    intervalo = filas("select id from pertenencia where persona_id = :p", p=mundo.p["C2"])[0][0]
    candidatas = fijaron_el_fin(intervalo, dia(4))
    assert len(candidatas) == 2 and {op for _, op in candidatas} == {"finalizacion_pertenencia"}      # ambiguo por los datos
    ordenadas = [e[0] for e in filas("select id from auditoria where operacion in ('finalizacion_pertenencia', 'cancelacion_operacion') order by momento, id")]
    ultima_cancelacion = ordenadas[-1]
    anteriores = [i for i in ordenadas if i != ultima_cancelacion and i in {c[0] for c in candidatas}]
    assert anteriores[-1] == candidatas[-1][0]                                          # por orden temporal: la original es la última anterior


def test_con_fechas_distintas_el_fin_se_enlaza_sin_ambiguedad(operador, mundo):
    finalizar(operador, fin(mundo, "C2", dia(4)))
    cancelar(operador, canc(mundo, "C2", "finalizacion", dia(4)))
    finalizar(operador, fin(mundo, "C2", dia(6)))
    intervalo = filas("select id from pertenencia where persona_id = :p", p=mundo.p["C2"])[0][0]
    assert len(fijaron_el_fin(intervalo, dia(4))) == 1 and len(fijaron_el_fin(intervalo, dia(6))) == 1
