"""M5-T4 — rutas de informes: ``POST /api/v1/informes/individuales`` (M5-01) y ``POST /api/v1/informes/consolidados`` (M5-02).

Registrado en ``app/main.py`` (M5-T4). La respuesta de éxito es la proyección cerrada de ``presentacion.py``. Las preguntas del contrato que siguen abiertas (el texto de la declaración ``base``, P-6, y los límites de tokens, plazo y
concurrencia, P-8) no cambian la estructura de la respuesta.

Son operaciones de LECTURA con coste externo: no modifican datos, no llevan clave de idempotencia ni devuelven un identificador, y nada se guarda (RN-56). Al ser ``POST`` con la cookie de sesión, exigen el token
CSRF y el origen como cualquier escritura. Campos desconocidos: ``SOLICITUD_INVALIDA``.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.compartido.dependencias import Operador, operador_que_modifica
from app.compartido.fechas import parsear_fecha_laboral
from app.config import Settings, get_settings
from app.db import get_db
from app.modulos.informes import presentacion, servicio
from app.modulos.informes.generacion import GeneradorDeTexto, GeneradorDesactivado
from app.modulos.informes.generador_ollama import GeneradorOllama
from app.modulos.informes.generador_simulado import GeneradorSimulado

router = APIRouter(prefix="/informes", tags=["M5 Informes"])

SIN_CACHE = {"Cache-Control": "no-store"}


class InformeIndividualEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")          # un campo desconocido es SOLICITUD_INVALIDA

    desde: str
    hasta: str
    persona_id: str | None = None


class InformeConsolidadoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    desde: str
    hasta: str
    equipo_id: str | None = None


def obtener_generador(settings: Settings = Depends(get_settings)) -> GeneradorDeTexto:
    """El generador que corresponde a la configuración, SIN alternativas silenciosas entre proveedores: ``ollama`` (local, M5-T5) o ``simulado`` solo si se pidieron expresamente; en cualquier otro caso
    ``GeneradorDesactivado``, que no genera nada. Si Ollama falla, la solicitud falla: no se usa el simulado ni otro proveedor."""
    if settings.informe_generador == "ollama":
        return GeneradorOllama(settings.informe_ollama_url, settings.informe_ollama_modelo, settings.informe_ollama_timeout_segundos, settings.informe_ollama_num_ctx)
    if settings.informe_generador == "simulado":
        return GeneradorSimulado()
    return GeneradorDesactivado()


@router.post("/individuales", summary="M5-01 Generar un informe individual")
def generar_informe_individual(cuerpo: InformeIndividualEntrada, op: Operador = Depends(operador_que_modifica), db: Session = Depends(get_db),
                               settings: Settings = Depends(get_settings), generador: GeneradorDeTexto = Depends(obtener_generador)):
    desde, hasta = parsear_fecha_laboral(cuerpo.desde, "desde"), parsear_fecha_laboral(cuerpo.hasta, "hasta")
    persona = servicio.leer_identificador(cuerpo.persona_id, "persona_id")
    resultado = servicio.generar_informe_individual(db, op, persona, desde, hasta, servicio.ajustes_de(settings), generador)
    return JSONResponse(presentacion.a_respuesta_publica(resultado), headers=SIN_CACHE)


@router.post("/consolidados", summary="M5-02 Generar un informe consolidado")
def generar_informe_consolidado(cuerpo: InformeConsolidadoEntrada, op: Operador = Depends(operador_que_modifica), db: Session = Depends(get_db),
                                settings: Settings = Depends(get_settings), generador: GeneradorDeTexto = Depends(obtener_generador)):
    desde, hasta = parsear_fecha_laboral(cuerpo.desde, "desde"), parsear_fecha_laboral(cuerpo.hasta, "hasta")
    equipo = servicio.leer_identificador(cuerpo.equipo_id, "equipo_id")
    resultado = servicio.generar_informe_consolidado(db, op, equipo, desde, hasta, servicio.ajustes_de(settings), generador)
    return JSONResponse(presentacion.a_respuesta_publica(resultado), headers=SIN_CACHE)
