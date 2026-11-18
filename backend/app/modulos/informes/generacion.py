"""M5-T3 — contrato INTERNO entre el backend y el generador de narrativa (``docs/api/m5-integracion-ia.md``, `[PROPUESTO]`). Es la frontera que M5-T5 rellenará con la integración de AWS: el dominio de
informes solo conoce esta interfaz, nunca un proveedor. Este módulo NO llama a ningún servicio, no tiene transporte, no persiste nada y no define ningún valor numérico de límites.

Capas (separadas a propósito):

1. DATOS SELECCIONADOS Y AUTORIZADOS: ``InformeBase`` y ``ConsolidadoBase`` (M5-T1 y M5-T2). Aquí solo se LEEN.
2. MÉTRICAS DETERMINISTAS: ``Agregaciones``. Entran en el contexto como HECHOS DADOS (``metricas``); el generador no las calcula y no puede modificarlas.
3. CONTEXTO MÍNIMO DE GENERACIÓN: ``EntradaDeGeneracion``, de campos CERRADOS, de UNA persona (D-M5-03: una narrativa por persona), con la persona seudonimizada.
4. NARRATIVA PROPUESTA: lo que devuelve el generador, que es DATO NO CONFIABLE hasta que ``validacion.validar_salida`` lo acepta.
5. VALIDACIÓN: determinista, en ``validacion.py``. Un fallo es un ``ErrorDeGeneracion`` con una clase y motivos de un vocabulario fijo, nunca con texto del prompt, de los registros ni de la respuesta.

SEUDONIMIZACIÓN (ADR-003, sección 6). La persona se sustituye por el alias «Persona 1» (cada llamada lleva una sola persona, así que el alias es siempre el mismo y no hay tabla compartida entre personas).
Quien llama conserva el alias y el nombre real EN MEMORIA y reconstruye el nombre después de validar (``narrativa.py``). Nunca viajan: el nombre, ``persona.id``, el identificador de las actividades, correos,
identificadores de acceso, credenciales, tokens ni el nombre del equipo. Las referencias de hechos y actividades son opacas por informe (``h1``, ``a1``…).

TEXTO NO CONFIABLE (RN-31, RNF-12). Las descripciones, los motivos de bloqueo y los títulos viajan como VALORES de campos de datos; ``campos_no_confiables`` los lista para que el adaptador los entregue
delimitados y nunca concatenados a las instrucciones. Este módulo no interpreta ni ejecuta ningún texto libre.
"""

from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol

from app.modulos.informes.agregaciones import Agregaciones
from app.modulos.informes.estructura import ActividadDelInforme, Hecho

VERSION_DEL_CONTRATO = "1"
IDIOMA = "es"
PREFIJO_DEL_ALIAS = "Persona"
CAMPOS_NO_CONFIABLES = ("texto", "descripcion", "motivo_bloqueo")


# ----------------------------------------------------------------------------------------------------------------------
# Entrada: contexto mínimo de generación (campos cerrados)
# ----------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class ActividadParaGenerar:
    ref: str
    forma: str
    texto: str                         # NO CONFIABLE: el título, o la referencia neutral
    planificada: bool | None


@dataclass(frozen=True)
class HechoParaGenerar:
    ref: str
    fecha_laboral: date
    actividad_ref: str
    estado: str
    descripcion: str                   # NO CONFIABLE
    motivo_bloqueo: str | None         # NO CONFIABLE


@dataclass(frozen=True)
class EntradaDeGeneracion:
    """Todo lo que el generador recibe. ``hechos`` (registros) y ``metricas`` (cifras deterministas) van SEPARADOS. Sin identificadores de la base de datos, sin nombre real y sin datos de acceso."""

    version: str
    tipo: str                          # ``individual`` o ``consolidado`` (el informe del que forma parte esta persona)
    idioma: str
    desde: date
    hasta: date
    alias: str
    actividades: tuple[ActividadParaGenerar, ...]
    hechos: tuple[HechoParaGenerar, ...]
    metricas: dict

    def a_diccionario(self) -> dict:
        """La forma que viaja: JSON puro, con la lista cerrada de campos del contrato. Es lo ÚNICO que un adaptador ve."""
        return {
            "version": self.version, "tipo": self.tipo, "idioma": self.idioma,
            "periodo": {"desde": self.desde.isoformat(), "hasta": self.hasta.isoformat()},
            "persona": {"alias": self.alias},
            "actividades": [{"ref": a.ref, "forma": a.forma, "texto": a.texto, "planificada": a.planificada} for a in self.actividades],
            "hechos": [{"ref": h.ref, "fecha_laboral": h.fecha_laboral.isoformat(), "actividad_ref": h.actividad_ref, "estado": h.estado,
                        "descripcion": h.descripcion, "motivo_bloqueo": h.motivo_bloqueo} for h in self.hechos],
            "metricas": self.metricas,
            "campos_no_confiables": list(CAMPOS_NO_CONFIABLES),
        }


def construir_entrada(tipo: str, desde: date, hasta: date, actividades: tuple[ActividadDelInforme, ...], hechos: tuple[Hecho, ...],
                      agregaciones: Agregaciones, numero_de_alias: int = 1) -> EntradaDeGeneracion:
    """Construye la entrada con una función de LISTA CERRADA (nunca serializando las estructuras del informe): copia solo los campos permitidos y descarta ``Persona``, ``id`` de actividad y todo lo demás."""
    return EntradaDeGeneracion(
        version=VERSION_DEL_CONTRATO, tipo=tipo, idioma=IDIOMA, desde=desde, hasta=hasta, alias=f"{PREFIJO_DEL_ALIAS} {numero_de_alias}",
        actividades=tuple(ActividadParaGenerar(a.ref, a.forma, a.texto, a.planificada) for a in actividades),
        hechos=tuple(HechoParaGenerar(h.ref, h.fecha_laboral, h.actividad_ref, h.estado, h.descripcion, h.motivo_bloqueo) for h in hechos),
        metricas=asdict(agregaciones))


# ----------------------------------------------------------------------------------------------------------------------
# Salida validada
# ----------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class SeccionDeNarrativa:
    texto: str
    refs: tuple[str, ...]              # referencias de los hechos que respaldan la sección (internas: no se muestran, PP-11 no está aprobada)


@dataclass(frozen=True)
class UsoDeTokens:
    entrada: int
    salida: int


@dataclass(frozen=True)
class SalidaDeGeneracion:
    """La narrativa ya VALIDADA. No contiene ninguna cifra propia: las cifras del informe son las de ``Agregaciones``, que este objeto no puede reemplazar ni modificar."""

    secciones: tuple[SeccionDeNarrativa, ...]
    uso: UsoDeTokens


# ----------------------------------------------------------------------------------------------------------------------
# Clasificación de resultados y de fallos
# ----------------------------------------------------------------------------------------------------------------------

class Clase(StrEnum):
    OK = "ok"
    SIN_DATOS = "sin_datos"                                        # no es un fallo: no hay registros autorizados y el generador no se invoca
    ERROR_TECNICO = "error_tecnico"                                # el generador no está disponible o falla
    RESPUESTA_MALFORMADA = "respuesta_malformada"                  # no cumple el esquema cerrado (estructura, tipos, campos desconocidos o ausentes)
    RECHAZADA_POR_VALIDACION = "rechazada_por_validacion"          # cumple el esquema, pero no supera una comprobación determinista de contenido
    TIEMPO_AGOTADO = "tiempo_agotado"
    CONTEXTO_NO_ADMISIBLE = "contexto_no_admisible"                # rebasa un límite configurado (D-M5-06: sin valores todavía)


class ErrorDeGeneracion(Exception):
    """Fallo de la generación. Lleva SOLO la clase y motivos de un vocabulario fijo: nunca el prompt, los registros, la respuesta del generador ni el mensaje de la excepción original."""

    def __init__(self, clase: Clase, motivos: tuple[str, ...] = ()) -> None:
        self.clase = clase
        self.motivos = tuple(motivos)
        super().__init__(clase.value)

    @property
    def codigo_publico(self) -> str:
        """Cómo lo verá el cliente (M5-T4): un límite rebasado es ``INFORME_EXCEDE_LIMITES``; todo lo demás, ``INFORME_NO_GENERADO`` (RN-58). Sin contenido parcial en ningún caso."""
        return "INFORME_EXCEDE_LIMITES" if self.clase is Clase.CONTEXTO_NO_ADMISIBLE else "INFORME_NO_GENERADO"

    @property
    def reintentable(self) -> bool:
        """Si tiene sentido decirle al cliente que puede volver a intentarlo (P-12): solo los fallos técnicos TRANSITORIOS (el generador no responde o agota su plazo). Una integración desactivada o sin generador
        configurado es un estado de configuración, no un fallo transitorio, y una respuesta mal formada o rechazada por la validación no mejora por repetirla."""
        return self.clase in (Clase.ERROR_TECNICO, Clase.TIEMPO_AGOTADO) and not set(self.motivos) & {"integracion_desactivada", "generador_no_configurado"}


# ----------------------------------------------------------------------------------------------------------------------
# La interfaz que sustituirá la integración de M5-T5
# ----------------------------------------------------------------------------------------------------------------------

class ErrorDelGenerador(Exception):
    """Base de los fallos que un adaptador declara. Su mensaje NUNCA se propaga."""


class GeneradorNoDisponible(ErrorDelGenerador):
    pass


class GeneradorNoConfigurado(ErrorDelGenerador):
    """No hay ningún generador configurado (no es un fallo transitorio)."""


class TiempoAgotado(ErrorDelGenerador):
    pass


class GeneradorDeTexto(Protocol):
    """Quien implemente esto (el simulado, ``GeneradorDesactivado`` y, en M5-T5, el adaptador de Lambda) recibe la entrada y devuelve la salida BRUTA, que el dominio trata como no confiable y valida.
    El adaptador es responsable de su plazo; el dominio no aplica reintentos ni colas (D-M5-06 abierta)."""

    def generar(self, entrada: EntradaDeGeneracion) -> object: ...


class GeneradorDesactivado:
    """Adaptador ``ninguno``: la integración no está habilitada. Es lo que usará el sistema mientras ``INFORME_HABILITADO`` esté desactivado (propuesta, D-M5-08)."""

    def generar(self, entrada: EntradaDeGeneracion) -> object:
        raise GeneradorNoConfigurado("integración desactivada")


# ----------------------------------------------------------------------------------------------------------------------
# Límites de contexto: sin valores (D-M5-06 abierta)
# ----------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class LimitesDeContexto:
    """Todos ``None`` = sin límite. NO hay ningún valor por defecto del producto: D-M5-06 está abierta. Existe para que el comportamiento «contexto no admisible» sea comprobable y para que M5-T4 lo cargue
    de la configuración cuando se aprueben los valores. Los límites de tokens, plazo, reintentos y concurrencia se aplican en el adaptador (M5-T5), no aquí."""

    max_dias: int | None = None
    max_hechos: int | None = None


SIN_LIMITES = LimitesDeContexto()


def verificar_contexto(entrada: EntradaDeGeneracion, limites: LimitesDeContexto) -> None:
    dias = (entrada.hasta - entrada.desde).days + 1
    if limites.max_dias is not None and dias > limites.max_dias:
        raise ErrorDeGeneracion(Clase.CONTEXTO_NO_ADMISIBLE, ("periodo_excede_el_limite",))
    if limites.max_hechos is not None and len(entrada.hechos) > limites.max_hechos:
        raise ErrorDeGeneracion(Clase.CONTEXTO_NO_ADMISIBLE, ("hechos_exceden_el_limite",))
