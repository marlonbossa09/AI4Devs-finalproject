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
CATALOGO: dict[str, tuple[int, str]] = {
    "SOLICITUD_INVALIDA": (400, "La solicitud no es válida."),
    "CLAVE_IDEMPOTENCIA_OBLIGATORIA": (400, "Falta la cabecera Idempotency-Key."),
    "NO_IDENTIFICADA": (401, "No hay una persona identificada."),
    "CREDENCIALES_INVALIDAS": (401, "Las credenciales no son válidas."),
    "ACCESO_DESACTIVADO": (403, "Su acceso está desactivado."),
    "SIN_PERTENENCIA_VIGENTE": (403, "No tiene una pertenencia vigente."),
    "RECURSO_NO_DISPONIBLE": (404, "El recurso solicitado no está disponible"),
    "BITACORA_CERRADA": (409, "La bitácora está cerrada; hay que reabrirla antes de modificarla."),
    "OPERACION_EN_CURSO": (409, "Otra petición con la misma clave sigue en curso."),
    "FECHA_NO_CUBIERTA": (422, "La fecha laboral no está cubierta por una pertenencia."),
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
