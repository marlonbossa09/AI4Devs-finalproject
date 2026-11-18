"""M5-T4 — canalización de un informe: autorización, límites, selección autorizada, interruptor de habilitación, generación de la narrativa con la interfaz de M5-T3 y traducción de los fallos a errores
contractuales. Es lo que invoca la ruta; no hay persistencia, ni transporte, ni AWS.

ORDEN (convenciones 3.2; la autorización, siempre ANTES de leer datos de registros):

1. Puede operar (la dependencia de sesión de la ruta) y formato de la solicitud (fechas y identificadores).
2. Autorización sobre la persona o el equipo (``autorizar_informe_*``: política única de M1, D-M5-09): 403 ``OPERACION_NO_PERMITIDA`` o 404 uniforme ``RECURSO_NO_DISPONIBLE``.
3. Límite de amplitud del período (``INFORME_MAX_RANGE_DAYS``, 31, ambos extremos incluidos): ``INFORME_EXCEDE_LIMITES``. Va DESPUÉS de autorizar para que ningún límite revele lo que la autorización oculta.
4. Selección de los avances autorizados, filtrada en SQL antes de agrupar y con un tope de lectura: más de ``INFORME_MAX_HECHOS`` (400, TOTAL de la solicitud: en el consolidado, todas las personas juntas)
   es ``INFORME_EXCEDE_LIMITES``. Nunca se trunca nada.
5. Sin avances autorizados: ``sin_datos``. El generador NO se invoca (RN-57) y no hace falta que esté habilitado; la respuesta sigue llevando ``base`` y no tiene narrativa.
6. Con avances: si ``INFORME_HABILITADO`` es falso (por defecto), ``INFORME_NO_GENERADO`` y NINGÚN generador se ejecuta. Si está habilitado, narrativa con la interfaz de M5-T3 (un solo intento: los reintentos son 0).
7. Cualquier fallo del generador o de la validación es ``INFORME_NO_GENERADO`` (503) sin contenido parcial, sin el contenido rechazado y con solo la indicación de si puede reintentarse.

EL RESULTADO INTERNO NO ES LA RESPUESTA. ``ResultadoDeInforme`` es interno: reúne el informe determinista (hechos y cifras, sin tocar) y la narrativa validada (aparte). Lo que sale al cliente lo construye ``presentacion.py`` con
proyecciones cerradas (borradores de contrato M5-01 y M5-02 0.2).

REGISTRO. Una línea técnica por generación con el tipo, el resultado, el número de hechos y la duración. Nunca nombres, identificadores de personas, textos de los registros, prompts ni narrativa.
"""

import logging
import time
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador
from app.compartido.visibilidad import consultante_de
from app.config import Settings
from app.errores import AppError
from app.modulos.informes import consolidado as modulo_consolidado, individual as modulo_individual, narrativa
from app.modulos.informes.consolidado import ConsolidadoBase
from app.modulos.informes.estructura import detalle_de_reintento
from app.modulos.informes.generacion import Clase, ErrorDeGeneracion, GeneradorDeTexto
from app.modulos.informes.individual import InformeBase
from app.modulos.informes.narrativa import NarrativaGenerada

logger = logging.getLogger("smartwork.informes")


@dataclass(frozen=True)
class AjustesDeInformes:
    """Los parámetros de D-M5-06 CONFIRMADOS que aplica este ticket. Los abiertos (tokens, plazo, concurrencia) no existen todavía."""

    habilitado: bool
    max_dias: int
    max_hechos: int


def ajustes_de(settings: Settings) -> AjustesDeInformes:
    return AjustesDeInformes(settings.informe_habilitado, settings.informe_max_range_days, settings.informe_max_hechos)


@dataclass(frozen=True)
class ResultadoDeInforme:
    """INTERNO. El informe determinista (``InformeBase`` o ``ConsolidadoBase``: hechos y cifras) y la narrativa validada, SEPARADOS: la narrativa no puede modificar ni sustituir ninguna cifra."""

    informe: InformeBase | ConsolidadoBase
    narrativa: NarrativaGenerada


# ----------------------------------------------------------------------------------------------------------------------
# Formato de la solicitud (paso 1)
# ----------------------------------------------------------------------------------------------------------------------

def leer_identificador(valor: str | None, campo: str) -> UUID | None:
    if valor is None:
        return None
    try:
        return UUID(valor)
    except ValueError:
        raise AppError("SOLICITUD_INVALIDA", [{"campo": campo, "motivo": "identificador_no_valido"}]) from None


# ----------------------------------------------------------------------------------------------------------------------
# Límites y fallos
# ----------------------------------------------------------------------------------------------------------------------

def _exigir_rango(desde: date, hasta: date, maximo_dias: int) -> None:
    if (hasta - desde).days + 1 > maximo_dias:
        raise AppError("INFORME_EXCEDE_LIMITES", [{"campo": "hasta", "motivo": "rango_excede_el_maximo", "maximo_dias": maximo_dias}, detalle_de_reintento(False)])


def _a_error_de_aplicacion(error: ErrorDeGeneracion) -> AppError:
    """Sin el contenido rechazado, sin el mensaje del generador y sin prompts: la clase decide el código y el único dato adicional es si puede reintentarse (convenciones 4; P-12, confirmada)."""
    if error.clase is Clase.CONTEXTO_NO_ADMISIBLE:
        return AppError("INFORME_EXCEDE_LIMITES", [{"campo": "informe", "motivo": "contexto_excede_el_limite"}, detalle_de_reintento(False)])
    return AppError("INFORME_NO_GENERADO", [detalle_de_reintento(error.reintentable)])


def _narrar(tipo: str, hechos: int, sin_datos: bool, ajustes: AjustesDeInformes, producir, inicio: float) -> NarrativaGenerada:
    """Pasos 5 a 7. ``producir`` es la llamada a la interfaz de M5-T3; no se ejecuta con la integración desactivada ni cuando no hay datos."""
    if sin_datos:
        resultado = NarrativaGenerada(Clase.SIN_DATOS, ())            # RN-57: no se invoca al generador
    elif not ajustes.habilitado:
        _registrar(tipo, "integracion_desactivada", hechos, inicio)
        raise _a_error_de_aplicacion(ErrorDeGeneracion(Clase.ERROR_TECNICO, ("integracion_desactivada",)))
    else:
        try:
            resultado = producir()
        except ErrorDeGeneracion as error:
            _registrar(tipo, f"{error.clase.value}:{','.join(error.motivos)}", hechos, inicio)
            raise _a_error_de_aplicacion(error) from None
    _registrar(tipo, resultado.clase.value, hechos, inicio)
    return resultado


def _registrar(tipo: str, resultado: str, hechos: int, inicio: float) -> None:
    logger.info("informe tipo=%s resultado=%s hechos=%d ms=%d", tipo, resultado, hechos, round((time.monotonic() - inicio) * 1000))


# ----------------------------------------------------------------------------------------------------------------------
# Las dos canalizaciones
# ----------------------------------------------------------------------------------------------------------------------

def generar_informe_individual(db: Session, op: Operador, persona_id: UUID | None, desde: date, hasta: date, ajustes: AjustesDeInformes, generador: GeneradorDeTexto) -> ResultadoDeInforme:
    inicio = time.monotonic()
    consultante = consultante_de(db, op.persona_id, hoy=op.contexto.fecha_actual)
    objetivo = modulo_individual.autorizar_informe_individual(db, consultante, persona_id, desde, hasta)
    _exigir_rango(desde, hasta, ajustes.max_dias)
    informe = modulo_individual.construir_informe_individual(db, consultante, objetivo, desde, hasta, ajustes.max_hechos)
    resultado = _narrar("individual", len(informe.hechos), informe.sin_datos, ajustes, lambda: narrativa.generar_narrativa_individual(informe, generador), inicio)
    return ResultadoDeInforme(informe, resultado)


def generar_informe_consolidado(db: Session, op: Operador, equipo_id: UUID | None, desde: date, hasta: date, ajustes: AjustesDeInformes, generador: GeneradorDeTexto) -> ResultadoDeInforme:
    inicio = time.monotonic()
    consultante = consultante_de(db, op.persona_id, hoy=op.contexto.fecha_actual)
    modulo_consolidado.autorizar_informe_consolidado(db, consultante, equipo_id, desde, hasta)
    _exigir_rango(desde, hasta, ajustes.max_dias)
    informe = modulo_consolidado.construir_informe_consolidado(db, consultante, desde, hasta, ajustes.max_hechos)
    hechos = sum(len(p.hechos) for p in informe.personas)
    resultado = _narrar("consolidado", hechos, informe.sin_datos, ajustes, lambda: narrativa.generar_narrativa_consolidado(informe, generador), inicio)
    return ResultadoDeInforme(informe, resultado)
