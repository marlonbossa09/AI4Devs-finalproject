"""M5-T5 — prueba con un OLLAMA REAL, local, con datos FICTICIOS y un modelo ya instalado. Solo corre si se pide expresamente con ``SMARTWORK_PRUEBA_OLLAMA_MODELO`` (el nombre de un modelo instalado); opcionalmente
``SMARTWORK_PRUEBA_OLLAMA_URL`` (por defecto ``http://127.0.0.1:11434``, y solo se admiten destinos locales). Sin esa variable se omite: la suite no depende de Ollama.

Un modelo local pequeño puede incumplir las reglas del validador: eso NO es un fallo del adaptador sino el comportamiento previsto (falla cerrado, sin contenido parcial). La prueba exige solo los invariantes: o se obtiene una
narrativa que supera TODAS las validaciones, o un ``ErrorDeGeneracion`` controlado con una clase y motivos fijos; nunca otra excepción, nunca contenido sin validar y nunca una cifra distinta de las deterministas.
Con ``-s`` imprime el resultado de cada intento (datos ficticios).
"""

import os
import time

import pytest

from app.modulos.informes.generacion import Clase, ErrorDeGeneracion
from app.modulos.informes.generador_ollama import GeneradorOllama
from app.modulos.informes.narrativa import generar_narrativa_consolidado, generar_narrativa_individual
from tests.test_informe_consolidado import consolidado, db, individual, mundo, mundo2  # noqa: F401  (escenario de M5-T1 y M5-T2)

MODELO = os.environ.get("SMARTWORK_PRUEBA_OLLAMA_MODELO")
URL = os.environ.get("SMARTWORK_PRUEBA_OLLAMA_URL", "http://127.0.0.1:11434")
pytestmark = pytest.mark.skipif(not MODELO, reason="Defina SMARTWORK_PRUEBA_OLLAMA_MODELO para probar con un Ollama local real")


def intentar(informe, generador, funcion):
    inicio = time.monotonic()
    try:
        resultado, error = funcion(informe, generador), None
    except ErrorDeGeneracion as e:
        resultado, error = None, e
    return resultado, error, time.monotonic() - inicio


@pytest.mark.parametrize("intento", [1, 2, 3])
def test_informe_individual_con_ollama_real(db, mundo2, intento):
    informe = individual(db, mundo2, "ana", None, -10, 0)
    resultado, error, segundos = intentar(informe, GeneradorOllama(URL, MODELO, 240, 8192), generar_narrativa_individual)
    if error is not None:
        print(f"\n[individual #{intento}] {segundos:.1f}s -> {error.clase.value} {error.motivos}")
        assert error.clase in (Clase.RESPUESTA_MALFORMADA, Clase.RECHAZADA_POR_VALIDACION, Clase.TIEMPO_AGOTADO, Clase.ERROR_TECNICO)
        return
    n = resultado.por_persona[0]
    print(f"\n[individual #{intento}] {segundos:.1f}s -> OK, {len(n.secciones)} secciones, tokens {n.uso.entrada}/{n.uso.salida}")
    for s in n.secciones:
        print("   -", s.texto, s.refs)
    assert resultado.clase is Clase.OK and n.persona.nombre == "ana" and n.secciones
    assert informe.agregaciones.avances == 4                                              # las cifras deterministas no se tocan


def test_consolidado_con_ollama_real(db, mundo2):
    informe = consolidado(db, mundo2, "supt", None, -30, 0)
    resultado, error, segundos = intentar(informe, GeneradorOllama(URL, MODELO, 240, 8192), generar_narrativa_consolidado)
    if error is not None:
        print(f"\n[consolidado] {segundos:.1f}s -> {error.clase.value} {error.motivos} (una persona que falla hace fallar todo el informe)")
        assert error.clase in (Clase.RESPUESTA_MALFORMADA, Clase.RECHAZADA_POR_VALIDACION, Clase.TIEMPO_AGOTADO, Clase.ERROR_TECNICO)
        return
    print(f"\n[consolidado] {segundos:.1f}s -> OK, {len(resultado.por_persona)} personas")
    assert [p.persona.nombre for p in resultado.por_persona] == ["ana", "beto", "gina", "pablo", "supt"] and all(p.secciones for p in resultado.por_persona)


def test_modelo_no_instalado_y_servidor_caido_con_ollama_real(db, mundo2):
    informe = individual(db, mundo2, "ana", None, -10, 0)
    _, e, _ = intentar(informe, GeneradorOllama(URL, "modelo-que-no-existe:0b", 60, 8192), generar_narrativa_individual)
    assert (e.clase, e.motivos, e.reintentable) == (Clase.ERROR_TECNICO, ("generador_no_configurado",), False)              # 404 real de Ollama
    _, e, _ = intentar(informe, GeneradorOllama("http://127.0.0.1:9", MODELO, 4, 8192), generar_narrativa_individual)
    assert e.clase in (Clase.ERROR_TECNICO, Clase.TIEMPO_AGOTADO) and e.reintentable
