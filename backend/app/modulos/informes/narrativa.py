"""M5-T3 — orquestación de la narrativa de un informe individual o consolidado a través de la interfaz ``GeneradorDeTexto``. Servicio INTERNO: sin ruta, sin transporte, sin AWS, sin persistencia, sin reintentos ni
colas (D-M5-06 abierta) y sin ningún dato fuera del proceso salvo la entrada de lista cerrada que recibe el generador.

FLUJO (D-M5-03, aprobada en principio: una narrativa por persona y sección de equipo determinista):

1. ``sin_datos``: no se construye entrada ni se invoca al generador; resultado ``Clase.SIN_DATOS`` sin narrativa (RN-57).
2. Por cada persona se construye la entrada (alias «Persona 1», lista cerrada de campos) y se verifica el contexto contra los límites. En el consolidado TODAS las entradas se construyen y verifican ANTES de
   invocar al generador, para no gastar una llamada si alguna persona no es admisible.
3. Se invoca al generador UNA vez por persona. Cualquier fallo se clasifica (``Clase``) sin propagar su mensaje.
4. La salida bruta se valida (``validacion.validar_salida``): es dato no confiable hasta entonces.
5. Solo si TODAS las personas pasan, se reconstruye el nombre real en memoria y se devuelve el resultado. Si una falla, el informe completo falla: NO hay contenido parcial (RN-58, CA-175).

Las métricas del informe (``Agregaciones``) y los hechos NO se tocan: el resultado solo lleva narrativa y los objetos del informe son inmutables. La narrativa no puede reemplazar ni corregir una cifra, y no se
modifican los hechos para que coincidan con una narrativa incorrecta: una narrativa incorrecta se rechaza.
"""

from dataclasses import dataclass

from app.modulos.informes.consolidado import ConsolidadoBase
from app.modulos.informes.estructura import ActividadDelInforme, Hecho, Persona
from app.modulos.informes.generacion import (
    SIN_LIMITES, Clase, EntradaDeGeneracion, ErrorDeGeneracion, ErrorDelGenerador, GeneradorDeTexto, LimitesDeContexto, SalidaDeGeneracion, SeccionDeNarrativa,
    ContextoNoAdmitido, GeneradorNoConfigurado, TiempoAgotado, UsoDeTokens, construir_entrada, verificar_contexto,
)
from app.modulos.informes.agregaciones import Agregaciones
from app.modulos.informes.individual import InformeBase
from app.modulos.informes.validacion import validar_salida


@dataclass(frozen=True)
class NarrativaDePersona:
    """La narrativa VALIDADA de una persona, con su nombre real ya reconstruido. ``refs`` son internas (PP-11 no aprobada): no se muestran."""

    persona: Persona
    secciones: tuple[SeccionDeNarrativa, ...]
    uso: UsoDeTokens


@dataclass(frozen=True)
class NarrativaGenerada:
    """``clase`` es ``OK`` (``por_persona`` tiene una entrada por persona) o ``SIN_DATOS`` (``por_persona`` vacío). Los fallos no se devuelven: se lanzan como ``ErrorDeGeneracion``."""

    clase: Clase
    por_persona: tuple[NarrativaDePersona, ...]


def _invocar(generador: GeneradorDeTexto, entrada: EntradaDeGeneracion) -> object:
    try:
        return generador.generar(entrada)
    except TiempoAgotado:
        raise ErrorDeGeneracion(Clase.TIEMPO_AGOTADO, ("tiempo_agotado",)) from None
    except ContextoNoAdmitido:
        raise ErrorDeGeneracion(Clase.CONTEXTO_NO_ADMISIBLE, ("contexto_no_admitido",)) from None
    except GeneradorNoConfigurado:
        raise ErrorDeGeneracion(Clase.ERROR_TECNICO, ("generador_no_configurado",)) from None
    except ErrorDelGenerador:
        raise ErrorDeGeneracion(Clase.ERROR_TECNICO, ("generador_no_disponible",)) from None
    except Exception:                                              # cualquier otro fallo del adaptador: se clasifica y se descarta su mensaje (puede contener datos o el prompt)
        raise ErrorDeGeneracion(Clase.ERROR_TECNICO, ("excepcion_inesperada",)) from None


def _con_el_nombre_real(salida: SalidaDeGeneracion, persona: Persona, alias: str) -> NarrativaDePersona:
    """Reconstrucción local (ADR-003, sección 6): el alias se sustituye por el nombre real, solo en memoria y solo DESPUÉS de validar."""
    return NarrativaDePersona(persona, tuple(SeccionDeNarrativa(s.texto.replace(alias, persona.nombre), s.refs) for s in salida.secciones), salida.uso)


def _narrar(generador: GeneradorDeTexto, bloques: list[tuple[Persona, EntradaDeGeneracion]]) -> NarrativaGenerada:
    salidas = []
    for persona, entrada in bloques:
        salidas.append(_con_el_nombre_real(validar_salida(_invocar(generador, entrada), entrada), persona, entrada.alias))
    return NarrativaGenerada(Clase.OK, tuple(salidas))


def generar_narrativa_individual(informe: InformeBase, generador: GeneradorDeTexto, limites: LimitesDeContexto = SIN_LIMITES) -> NarrativaGenerada:
    """Narrativa de un informe individual. Un solo intento. Ver el docstring del módulo."""
    if informe.sin_datos:
        return NarrativaGenerada(Clase.SIN_DATOS, ())
    entrada = construir_entrada(informe.tipo, informe.desde, informe.hasta, informe.actividades, informe.hechos, informe.agregaciones)
    verificar_contexto(entrada, limites)
    return _narrar(generador, [(informe.persona, entrada)])


def generar_narrativa_consolidado(consolidado: ConsolidadoBase, generador: GeneradorDeTexto, limites: LimitesDeContexto = SIN_LIMITES) -> NarrativaGenerada:
    """Narrativa por persona de un informe consolidado. La sección de equipo (``agregaciones_del_equipo``) es determinista y NO se envía al generador (D-M5-03). Un solo intento por persona; si una falla, el informe
    completo falla."""
    if consolidado.sin_datos:
        return NarrativaGenerada(Clase.SIN_DATOS, ())
    bloques = [(p.persona, construir_entrada(consolidado.tipo, consolidado.desde, consolidado.hasta, p.actividades, p.hechos, p.agregaciones)) for p in consolidado.personas]
    for _, entrada in bloques:
        verificar_contexto(entrada, limites)                         # antes de gastar ninguna llamada
    return _narrar(generador, bloques)
