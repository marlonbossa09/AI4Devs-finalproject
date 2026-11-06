"""Estructura de error común y catálogo (docs/api/convenciones.md, sección 4).

Estructura: ``codigo`` (estable), ``mensaje`` (para personas) y ``detalles`` (lista opcional de
pares campo y motivo). Los errores del servidor no incluyen detalles internos y llevan un
identificador de correlación.
"""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("smartwork")

# Código -> (estado HTTP, mensaje fijo). Solo los códigos que usan las operaciones implementadas.
# OPERACION_NO_PERMITIDA (403) no se emite todavía: mientras no exista la visibilidad histórica
# del equipo (BE-02, M4), una actividad o bitácora ajena se responde siempre con
# RECURSO_NO_DISPONIBLE (404), sin revelar si existe. Es una diferencia provisional respecto a los
# contratos de M2 y M3, que distinguen 403 (recurso visible) de 404 (no visible).
CATALOGO: dict[str, tuple[int, str]] = {
    "SOLICITUD_INVALIDA": (400, "La solicitud no es válida."),
    "CLAVE_IDEMPOTENCIA_OBLIGATORIA": (400, "Falta la cabecera Idempotency-Key."),
    "NO_IDENTIFICADA": (401, "No hay una persona identificada."),
    "CREDENCIALES_INVALIDAS": (401, "Las credenciales no son válidas."),
    "ACCESO_DESACTIVADO": (403, "Su acceso está desactivado."),
    "SIN_PERTENENCIA_VIGENTE": (403, "No tiene una pertenencia vigente."),
    "RECURSO_NO_DISPONIBLE": (404, "El recurso solicitado no está disponible"),
    "BITACORA_CERRADA": (409, "La bitácora está cerrada; hay que reabrirla antes de modificarla."),
    "BITACORA_NO_CERRADA": (409, "La bitácora no está cerrada."),
    "ACTIVIDAD_COMPLETADA": (409, "La actividad está Completada; hay que reactivarla antes de continuarla."),
    "ACTIVIDAD_MARCADA_POR_ERROR": (409, "La actividad está marcada como registrada por error."),
    "CONDICIONES_DE_CIERRE_NO_CUMPLIDAS": (409, "La jornada no cumple las condiciones de cierre."),
    "OPERACION_EN_CURSO": (409, "Otra petición con la misma clave sigue en curso."),
    "FECHA_NO_CUBIERTA": (422, "La fecha laboral no está cubierta por una pertenencia."),
    "FECHA_FUTURA_NO_PERMITIDA": (422, "No se puede registrar ejecución ni cerrar una jornada de fecha futura."),
    "FECHA_NO_FUTURA": (422, "La continuación planificada exige una fecha posterior a la actual."),
    "ESTADO_INVALIDO": (422, "El estado no es uno de los cuatro permitidos."),
    "DESCRIPCION_OBLIGATORIA": (422, "La descripción es obligatoria."),
    "MOTIVO_BLOQUEO_OBLIGATORIO": (422, "Una actividad Bloqueada exige indicar el motivo."),
    "MOTIVO_OBLIGATORIO": (422, "Falta el motivo."),
    "CAMPO_OBLIGATORIO": (422, "Falta un campo obligatorio."),
    "TEXTO_DEMASIADO_LARGO": (422, "El texto supera el máximo permitido."),
    "CLAVE_IDEMPOTENCIA_REUTILIZADA": (422, "La clave ya se usó con otra petición distinta."),
    "ERROR_INTERNO": (500, "Se produjo un error interno."),
}


class AppError(Exception):
    """Error de negocio con código del catálogo."""

    def __init__(self, codigo: str, detalles: list[dict[str, object]] | None = None,
                 mensaje: str | None = None) -> None:
        if codigo not in CATALOGO:
            raise ValueError(f"Código de error fuera del catálogo: {codigo}")
        self.codigo = codigo
        self.estado = CATALOGO[codigo][0]
        self.mensaje = mensaje or CATALOGO[codigo][1]
        self.detalles = detalles or []
        super().__init__(codigo)


def _respuesta(error: AppError, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=error.estado,
        content={"codigo": error.codigo, "mensaje": error.mensaje, "detalles": error.detalles},
        headers=headers,
    )


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return _respuesta(exc)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Formato, tipos y campos desconocidos: petición mal formada (400). Sin eco de valores.
        detalles = [
            {"campo": ".".join(str(p) for p in e["loc"] if p != "body"), "motivo": e["type"]}
            for e in exc.errors()
        ]
        return _respuesta(AppError("SOLICITUD_INVALIDA", detalles))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return _respuesta(AppError("RECURSO_NO_DISPONIBLE"))
        return _respuesta(AppError("SOLICITUD_INVALIDA"))

    @app.exception_handler(Exception)
    async def _interno(_: Request, exc: Exception) -> JSONResponse:
        correlacion = uuid.uuid4().hex
        logger.exception("Error interno (correlación %s)", correlacion)
        return _respuesta(
            AppError("ERROR_INTERNO", [{"correlacion": correlacion}]),
        )
