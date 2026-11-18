"""M5-T3 — interfaz interna de generación, validación de la salida y tratamiento de fallos, con un generador SIMULADO y determinista. Sin red, sin AWS, sin credenciales, sin HTTP y sin persistencia.

Se parte de informes REALES (M5-T1 y M5-T2, con PostgreSQL desechable) y se comprueba: generación individual y consolidada simuladas; separación de narrativa y métricas; rechazo de campos inesperados, de cifras
contradictorias o inventadas y de salidas malformadas; generador no disponible, tiempo agotado y errores inesperados sin filtrar nada; ausencia de identificadores y credenciales en lo que viajaría; informe sin
datos; instrucciones maliciosas dentro de las descripciones; y límites de contexto (con valores de PRUEBA locales: el producto no tiene ninguno todavía). Reutiliza el escenario de ``test_informe_consolidado``.
"""

import copy
import dataclasses
import json
import re
from pathlib import Path

import pytest
from sqlalchemy import text

from app.modulos.informes.generacion import (
    Clase, ErrorDeGeneracion, GeneradorDesactivado, LimitesDeContexto, SalidaDeGeneracion, construir_entrada, verificar_contexto,
)
from app.modulos.informes.generador_simulado import GeneradorSimulado
from app.modulos.informes.narrativa import generar_narrativa_consolidado, generar_narrativa_individual
from app.modulos.informes.validacion import validar_salida
from tests.test_informe_consolidado import CLAVE, consolidado, d, db, individual, mundo, mundo2, nombres  # noqa: F401  (fixtures y ayudas del escenario)
from tests.test_informe_individual import ORDEN_MALICIOSA

UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def fallo(funcion, *args) -> ErrorDeGeneracion:
    with pytest.raises(ErrorDeGeneracion) as e:
        funcion(*args)
    return e.value


def individual_de_ana(db, m):
    return individual(db, m, "ana", None)


# ------------------------------------------------------------------------------------------------------ 1 y 2: generación simulada

def test_la_generacion_individual_simulada_devuelve_la_narrativa_validada_con_el_nombre_real(db, mundo2):
    informe = individual_de_ana(db, mundo2)
    generador = GeneradorSimulado()
    r = generar_narrativa_individual(informe, generador)
    assert (r.clase, generador.llamadas, len(r.por_persona)) == (Clase.OK, 1, 1)
    n = r.por_persona[0]
    assert n.persona == informe.persona
    assert n.secciones[0].texto == "ana registró 4 avances en 3 jornadas, sobre 2 actividades."          # el alias se reconstruyó con el nombre real
    assert n.secciones[1].texto == f"ana tuvo bloqueos registrados el {d(-5).isoformat()}."
    assert all("Persona 1" not in s.texto for s in n.secciones)
    refs_validas = {h.ref for h in informe.hechos}
    assert all(set(s.refs) <= refs_validas for s in n.secciones) and n.secciones[1].refs == ("h2",)


def test_la_generacion_consolidada_simulada_hace_una_llamada_por_persona_sin_mezclar_contextos(db, mundo2):
    informe = consolidado(db, mundo2, "supt", None)
    generador = GeneradorSimulado()
    r = generar_narrativa_consolidado(informe, generador)
    assert (r.clase, generador.llamadas) == (Clase.OK, 5)
    assert [n.persona.nombre for n in r.por_persona] == nombres(informe) == ["ana", "beto", "gina", "pablo", "supt"]
    assert all(e["persona"] == {"alias": "Persona 1"} and e["tipo"] == "consolidado" for e in generador.recibido)       # cada llamada lleva UNA persona, con el mismo alias
    assert sum(len(e["hechos"]) for e in generador.recibido) == 13
    pablo = generador.recibido[3]
    assert {h["descripcion"] for h in pablo["hechos"]} == {"Avance interno del equipo T", "Bloqueo en el equipo T"}      # solo lo de Pablo, y solo lo de su equipo
    assert all("Avance de Beto" not in json.dumps(e) for i, e in enumerate(generador.recibido) if i != 1)               # el contexto de una persona no lleva el de otra
    assert "agregaciones_del_equipo" not in json.dumps(generador.recibido)                                              # la sección de equipo es determinista: no se envía


# ------------------------------------------------------------------------------------------------------ 3: separación de narrativa y métricas

def test_la_narrativa_y_las_metricas_estan_separadas_y_la_narrativa_no_puede_modificar_las_cifras(db, mundo2):
    informe = individual_de_ana(db, mundo2)
    antes = copy.deepcopy(informe)
    generador = GeneradorSimulado()
    r = generar_narrativa_individual(informe, generador)
    assert informe == antes                                                                         # el informe (hechos y métricas) queda intacto
    entrada = generador.recibido[0]
    assert entrada["metricas"] == dataclasses.asdict(informe.agregaciones) and "metricas" not in entrada["hechos"][0]      # las cifras van aparte de los hechos
    assert {f.name for f in dataclasses.fields(type(r.por_persona[0]))} == {"persona", "secciones", "uso"}                 # el resultado no tiene dónde llevar cifras
    with pytest.raises(dataclasses.FrozenInstanceError):
        informe.agregaciones.avances = 99                                                           # type: ignore[misc]
    # una narrativa que contradice una cifra NO corrige el informe: se rechaza (ver más abajo) y el informe sigue igual
    fallo(generar_narrativa_individual, informe, GeneradorSimulado("cifra_contradictoria"))
    assert informe == antes


# ------------------------------------------------------------------------------------------------------ 4 a 6: validación

@pytest.mark.parametrize("modo,motivo", [("campo_extra", "campo_desconocido"), ("campo_extra_en_seccion", "campo_desconocido"), ("campo_faltante", "campo_faltante"),
                                          ("no_es_un_objeto", "no_es_un_objeto"), ("secciones_no_es_lista", "secciones_invalidas"), ("tokens_booleanos", "uso_invalido")])
def test_una_salida_malformada_o_con_campos_inesperados_se_rechaza(db, mundo2, modo, motivo):
    e = fallo(generar_narrativa_individual, individual_de_ana(db, mundo2), GeneradorSimulado(modo))
    assert (e.clase, e.motivos) == (Clase.RESPUESTA_MALFORMADA, (motivo,))
    assert (e.codigo_publico, e.reintentable) == ("INFORME_NO_GENERADO", False)


@pytest.mark.parametrize("modo,motivo", [("cifra_contradictoria", "cifra_contradictoria"), ("cifra_inventada", "cifra_no_autorizada"), ("porcentaje", "porcentaje"),
                                          ("fecha_inventada", "fecha_no_autorizada"), ("alias_ajeno", "alias_no_autorizado"), ("referencia_inexistente", "referencia_inexistente"),
                                          ("enlace", "contenido_no_admitido"), ("identificador", "contenido_no_admitido")])
def test_una_salida_con_cifras_contradictorias_o_inventadas_o_con_datos_no_autorizados_se_rechaza(db, mundo2, modo, motivo):
    e = fallo(generar_narrativa_individual, individual_de_ana(db, mundo2), GeneradorSimulado(modo))
    assert (e.clase, motivo in e.motivos, e.codigo_publico) == (Clase.RECHAZADA_POR_VALIDACION, True, "INFORME_NO_GENERADO")


def test_el_validador_no_modifica_la_entrada_y_distingue_lo_correcto(db, mundo2):
    informe = individual_de_ana(db, mundo2)
    entrada = construir_entrada(informe.tipo, informe.desde, informe.hasta, informe.actividades, informe.hechos, informe.agregaciones)
    antes = copy.deepcopy(entrada)
    bruta = GeneradorSimulado()._correcta(entrada.a_diccionario())
    salida = validar_salida(bruta, entrada)
    assert isinstance(salida, SalidaDeGeneracion) and entrada == antes
    assert bruta["secciones"][0]["texto"].startswith("Persona 1 registró")                        # tampoco se modifica la salida bruta
    # una cifra que aparece en los propios registros (el «2» de un título) se admite al citarla; una que no, no
    bruta["secciones"][0]["texto"] += " Ver «Tarea de Beto 7»."
    with pytest.raises(ErrorDeGeneracion) as e:
        validar_salida(bruta, entrada)
    assert e.value.motivos == ("cifra_no_autorizada",)                                           # el 7 no es de ana: nada de otra persona entra por la narrativa


# ------------------------------------------------------------------------------------------------------ 7: fallos del generador

def test_un_generador_no_disponible_con_tiempo_agotado_o_roto_se_clasifica_sin_filtrar_nada(db, mundo2):
    informe = individual_de_ana(db, mundo2)
    for generador, clase, reintentable in ((GeneradorSimulado("no_disponible"), Clase.ERROR_TECNICO, True), (GeneradorSimulado("tiempo_agotado"), Clase.TIEMPO_AGOTADO, True),
                                           (GeneradorSimulado("error_inesperado"), Clase.ERROR_TECNICO, True), (GeneradorDesactivado(), Clase.ERROR_TECNICO, False)):      # sin generador configurado: no es transitorio (P-12)
        e = fallo(generar_narrativa_individual, informe, generador)
        assert (e.clase, e.reintentable, e.codigo_publico) == (clase, reintentable, "INFORME_NO_GENERADO")
        visible = " ".join([str(e), repr(e), *e.motivos])
        assert "interno" not in visible and "prompt" not in visible and "registros" not in visible and "Informe de Ana" not in visible    # ni el mensaje original ni el contenido
        assert e.__cause__ is None
        if isinstance(generador, GeneradorSimulado):
            assert generador.llamadas == 1                                                          # un solo intento: no hay reintentos ni colas


def test_si_falla_la_narrativa_de_una_persona_no_se_devuelve_un_informe_parcial(db, mundo2):
    class FallaEnLaTercera(GeneradorSimulado):
        def generar(self, entrada):
            if self.llamadas == 2:
                self.llamadas += 1
                raise ValueError("secreto")
            return super().generar(entrada)

    generador = FallaEnLaTercera()
    e = fallo(generar_narrativa_consolidado, consolidado(db, mundo2, "supt", None), generador)
    assert (e.clase, generador.llamadas) == (Clase.ERROR_TECNICO, 3)                                 # se detuvo en la tercera persona; no hay resultado alguno


# ------------------------------------------------------------------------------------------------------ 8: lo que viajaría

def test_lo_que_viajaria_al_generador_tiene_campos_cerrados_y_ningun_identificador_ni_credencial(db, mundo2):
    generadores = []
    for informe, funcion in ((individual_de_ana(db, mundo2), generar_narrativa_individual), (consolidado(db, mundo2, "supt", None), generar_narrativa_consolidado),
                             (consolidado(db, mundo2, "supu", None), generar_narrativa_consolidado)):
        g = GeneradorSimulado()
        funcion(informe, g)
        generadores.append(g)
    for g in generadores:
        for e in g.recibido:
            assert set(e) == {"version", "tipo", "idioma", "periodo", "persona", "actividades", "hechos", "metricas", "campos_no_confiables"}
            assert set(e["persona"]) == {"alias"} and e["persona"]["alias"] == "Persona 1"
            assert all(set(a) == {"ref", "forma", "texto", "planificada"} for a in e["actividades"])
            assert all(set(h) == {"ref", "fecha_laboral", "actividad_ref", "estado", "descripcion", "motivo_bloqueo"} for h in e["hechos"])
            assert e["campos_no_confiables"] == ["texto", "descripcion", "motivo_bloqueo"]
            texto = json.dumps(e, ensure_ascii=False)
            assert not UUID.search(texto)                                                            # ningún identificador de la base de datos
            for sensible in ("acceso-", "-privado", CLAVE, "argon2", "@", "Equipo T-reservado", "Equipo U-reservado", "Equipo W-reservado", "resumen reservado", "token", "password"):
                assert sensible not in texto, sensible
    # las referencias son opacas y no son identificadores
    assert {a["ref"] for e in generadores[0].recibido for a in e["actividades"]} == {"a1", "a2"}
    # lo protegido del equipo anterior no llega a un generador del equipo nuevo (CA-277)
    protegidos = ("Tarea secreta del equipo T", "Avance interno del equipo T", "Bloqueo en el equipo T", "motivo-reservado-del-equipo-T")
    assert not any(p in json.dumps(generadores[2].recibido, ensure_ascii=False) for p in protegidos)


# ------------------------------------------------------------------------------------------------------ 9: sin datos

def test_un_informe_sin_datos_no_invoca_al_generador(db, mundo2):
    for informe, funcion in ((individual(db, mundo2, "ana", None, -3, 2), generar_narrativa_individual), (consolidado(db, mundo2, "supt", None, 1, 10), generar_narrativa_consolidado)):
        assert informe.sin_datos
        generador = GeneradorSimulado("error_inesperado")                                            # si se invocase, fallaría
        r = funcion(informe, generador)
        assert (r.clase, r.por_persona, generador.llamadas) == (Clase.SIN_DATOS, (), 0)


# ------------------------------------------------------------------------------------------------------ 10: instrucciones maliciosas

def test_una_orden_escrita_en_una_descripcion_viaja_solo_como_dato_y_su_obediencia_se_rechaza_si_es_detectable(db, mundo2):
    informe = individual_de_ana(db, mundo2)
    assert any(h.descripcion == ORDEN_MALICIOSA for h in informe.hechos)
    generador = GeneradorSimulado()
    r = generar_narrativa_individual(informe, generador)
    enviado = json.dumps(generador.recibido[0], ensure_ascii=False)
    assert enviado.count(ORDEN_MALICIOSA) == 1                                                       # solo aparece como VALOR de un campo de datos (``descripcion``), nunca en otro sitio
    assert any(h["descripcion"] == ORDEN_MALICIOSA for h in generador.recibido[0]["hechos"]) and "descripcion" in generador.recibido[0]["campos_no_confiables"]
    assert "IGNORA" not in " ".join(s.texto for s in r.por_persona[0].secciones)                     # el generador simulado correcto no la sigue
    # un generador que la OBEDECE e inserta un enlace o cifras inventadas es rechazado
    e = fallo(generar_narrativa_individual, informe, GeneradorSimulado("obedece_orden_con_enlace"))
    assert (e.clase, {"contenido_no_admitido", "cifra_no_autorizada"} <= set(e.motivos)) == (Clase.RECHAZADA_POR_VALIDACION, True)
    # RIESGO RESIDUAL documentado: si obedece con prosa inocua (sin enlaces ni cifras), la validación determinista NO puede detectarlo. Solo la evaluación por muestras (D-M5-05) lo cubre
    r2 = generar_narrativa_individual(informe, GeneradorSimulado("obedece_orden_en_prosa"))
    assert r2.clase is Clase.OK and "todos los demás equipos" in r2.por_persona[0].secciones[0].texto


# ------------------------------------------------------------------------------------------------------ límites de contexto (valores de PRUEBA, no del producto)

def test_un_contexto_que_rebasa_un_limite_no_invoca_al_generador_y_se_distingue_de_un_fallo_tecnico(db, mundo2):
    informe = individual_de_ana(db, mundo2)                                                          # 4 hechos y un período de 111 días
    for limites in (LimitesDeContexto(max_hechos=3), LimitesDeContexto(max_dias=30)):
        generador = GeneradorSimulado()
        e = fallo(generar_narrativa_individual, informe, generador, limites)
        assert (e.clase, e.codigo_publico, e.reintentable, generador.llamadas) == (Clase.CONTEXTO_NO_ADMISIBLE, "INFORME_EXCEDE_LIMITES", False, 0)
    assert generar_narrativa_individual(informe, GeneradorSimulado(), LimitesDeContexto(max_hechos=4, max_dias=111)).clase is Clase.OK      # el límite exacto se admite
    assert generar_narrativa_individual(informe, GeneradorSimulado()).clase is Clase.OK                # sin límites (D-M5-06 abierta) no se rechaza nada por tamaño
    # en el consolidado se verifica a todas las personas ANTES de gastar una llamada (Beto tiene 5 hechos y Ana, que va antes, 4)
    generador = GeneradorSimulado()
    e = fallo(generar_narrativa_consolidado, consolidado(db, mundo2, "supt", None), generador, LimitesDeContexto(max_hechos=4))
    assert (e.clase, generador.llamadas) == (Clase.CONTEXTO_NO_ADMISIBLE, 0)
    entrada = construir_entrada(informe.tipo, informe.desde, informe.hasta, informe.actividades, informe.hechos, informe.agregaciones)
    verificar_contexto(entrada, LimitesDeContexto())                                                 # sin valores: no limita


# ------------------------------------------------------------------------------------------------------ solo dentro del proceso y sin persistencia

def test_el_paquete_de_informes_no_importa_ningun_cliente_de_red_ni_de_aws_y_no_persiste(db, mundo2):
    raiz = Path(__file__).resolve().parent.parent / "app" / "modulos" / "informes"
    prohibidos = re.compile(r"^\s*(import|from)\s+(boto3|botocore|httpx|requests|urllib|socket|aiohttp|anthropic|openai)\b", re.MULTILINE)
    assert [f.name for f in raiz.glob("*.py") if prohibidos.search(f.read_text(encoding="utf-8"))] == []
    tablas = ("bitacora", "actividad", "planificacion", "avance", "auditoria", "persona", "pertenencia", "equipo")
    antes = {t: db.execute(text(f"select count(*) from {t}")).scalar() for t in tablas}
    generar_narrativa_individual(individual_de_ana(db, mundo2), GeneradorSimulado())
    generar_narrativa_consolidado(consolidado(db, mundo2, "supt", None), GeneradorSimulado())
    db.rollback()
    assert {t: db.execute(text(f"select count(*) from {t}")).scalar() for t in tablas} == antes
