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
from starlette.routing import Match, Mount

logger = logging.getLogger("smartwork")

# Código -> (estado HTTP, mensaje fijo). Solo los códigos que usan las operaciones implementadas.
# OPERACION_NO_PERMITIDA (403): M4-03 y M4-04 la emiten a quien no es supervisor con acceso efectivo (RN-13) y, desde M4-T6, seis operaciones de M2 y M3 sobre un registro ajeno
# que le es VISIBLE según la política de visibilidad histórica (convenciones 3.1). Lo no visible o inexistente sigue siendo RECURSO_NO_DISPONIBLE (404), sin revelar si existe.
CATALOGO: dict[str, tuple[int, str]] = {
    "SOLICITUD_INVALIDA": (400, "La solicitud no es válida."),
    "CLAVE_IDEMPOTENCIA_OBLIGATORIA": (400, "Falta la cabecera Idempotency-Key."),
    "NO_IDENTIFICADA": (401, "No hay una persona identificada."),
    "CREDENCIALES_INVALIDAS": (401, "Las credenciales no son válidas."),
    "ACCESO_DESACTIVADO": (403, "Su acceso está desactivado."),
    "SIN_PERTENENCIA_VIGENTE": (403, "No tiene una pertenencia vigente."),
    "OPERACION_NO_PERMITIDA": (403, "La operación no está permitida para su rol."),
    "RECURSO_NO_DISPONIBLE": (404, "El recurso solicitado no está disponible"),
    "METODO_NO_PERMITIDO": (405, "El método HTTP no está permitido para este recurso."),
    "BITACORA_CERRADA": (409, "La bitácora está cerrada; hay que reabrirla antes de modificarla."),
    "BITACORA_NO_CERRADA": (409, "La bitácora no está cerrada."),
    "ACTIVIDAD_COMPLETADA": (409, "La actividad está Completada; hay que reactivarla antes de continuarla."),
    "ACTIVIDAD_NO_COMPLETADA": (409, "La actividad no está Completada, así que no hay nada que reactivar."),
    "SECUENCIA_INVALIDA": (409, "El resultado violaría la secuencia de avances de la actividad."),
    "ACTIVIDAD_MARCADA_POR_ERROR": (409, "La actividad está marcada como registrada por error."),
    "CONDICIONES_DE_CIERRE_NO_CUMPLIDAS": (409, "La jornada no cumple las condiciones de cierre."),
    "MARCA_NO_PROCEDE": (409, "La actividad tiene avances en jornadas posteriores a su creación y no puede marcarse."),
    "MARCA_INVALIDARIA_CIERRE": (409, "Marcar la actividad dejaría sin cumplir las condiciones de cierre de una jornada cerrada."),
    "MARCA_NO_VIGENTE": (409, "La actividad no tiene una marca de error vigente."),
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
    # Reservados para el canje de códigos (M1-T8.3 y T8.4; todavía no los emite ninguna ruta). Estados HTTP `[PROPUESTO]`. El mensaje es
    # fijo y único: no distingue un código desconocido, usado, caducado, invalidado o de un acceso desactivado, ni si el identificador existe.
    "CODIGO_NO_VALIDO": (400, "El código no es válido."),
    "CONTRASENA_NO_VALIDA": (422, "La contraseña no cumple la política."),
    "DEMASIADAS_SOLICITUDES": (429, "Demasiados intentos. Vuelva a intentarlo más tarde."),
    "ERROR_INTERNO": (500, "Se produjo un error interno."),
}


class AppError(Exception):
    """Error de negocio con código del catálogo."""

    def __init__(self, codigo: str, detalles: list[dict[str, object]] | None = None,
                 mensaje: str | None = None, cabeceras: dict[str, str] | None = None) -> None:
        if codigo not in CATALOGO:
            raise ValueError(f"Código de error fuera del catálogo: {codigo}")
        self.codigo = codigo
        self.estado = CATALOGO[codigo][0]
        self.mensaje = mensaje or CATALOGO[codigo][1]
        self.detalles = detalles or []
        self.cabeceras = cabeceras or {}
        super().__init__(codigo)

    @classmethod
    def demasiadas_solicitudes(cls, espera_segundos: int) -> "AppError":
        """429 con ``Retry-After`` (segundos enteros, RFC 9110) y la misma espera en los detalles. Mensaje y detalles fijos: no
        distinguen si el identificador existe ni cuántos intentos quedan."""
        return cls("DEMASIADAS_SOLICITUDES", [{"espera_segundos": espera_segundos}],
                   cabeceras={"Retry-After": str(espera_segundos), "Cache-Control": "no-store"})


def _respuesta(error: AppError, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=error.estado,
        content={"codigo": error.codigo, "mensaje": error.mensaje, "detalles": error.detalles},
        headers={**error.cabeceras, **(headers or {})} or None,
    )


_METODOS_HTTP = ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")


def metodos_de_la_api(scope: dict) -> list[str]:
    """Métodos que atendería de verdad alguna ruta de la API para la ruta de ``scope``, en orden alfabético (PA-30).

    Se pregunta al router, método a método, si hay una ruta de la API que coincida por completo, sin depender de cómo
    FastAPI organiza internamente sus rutas. El montaje del cliente web se ignora: coincide con cualquier ruta. Solo
    depende de la ruta, nunca del identificador del recurso ni de la sesión."""
    app = scope.get("app")
    if app is None:
        return []
    permitidos = []
    for metodo in _METODOS_HTTP:
        candidato = {**scope, "method": metodo, "root_path": scope.get("app_root_path", scope.get("root_path", ""))}
        for route in app.router.routes:
            if isinstance(route, Mount):
                continue
            if route.matches(candidato)[0] is Match.FULL:
                permitidos.append(metodo)
                break
    return permitidos


def _metodos_permitidos(request: Request, exc: StarletteHTTPException) -> str:
    """Valor de la cabecera ``Allow`` de un 405. Starlette solo informa de la primera ruta que coincide parcialmente y,
    con el cliente web montado, el 405 de una ruta de la API lo emitiría el servidor de ficheros estáticos
    (``Allow: GET, HEAD``): por eso se reúnen los métodos de todas las rutas de la API. Si ninguna ruta de la API atiende
    ningún método (por ejemplo, un fichero del cliente), se conserva la cabecera que haya puesto quien lanzó el error."""
    permitidos = metodos_de_la_api(request.scope)
    if permitidos:
        return ", ".join(permitidos)
    return (exc.headers or {}).get("Allow", "GET, HEAD")


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
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return _respuesta(AppError("RECURSO_NO_DISPONIBLE"))
        if exc.status_code == 405:
            # Método no admitido en una ruta que existe (PA-30): 405 con la cabecera Allow.
            return _respuesta(
                AppError("METODO_NO_PERMITIDO", [{"campo": "metodo", "motivo": "metodo_no_permitido"}]),
                headers={"Allow": _metodos_permitidos(request, exc)},
            )
        return _respuesta(AppError("SOLICITUD_INVALIDA"))

    @app.exception_handler(Exception)
    async def _interno(_: Request, exc: Exception) -> JSONResponse:
        correlacion = uuid.uuid4().hex
        logger.exception("Error interno (correlación %s)", correlacion)
        return _respuesta(
            AppError("ERROR_INTERNO", [{"correlacion": correlacion}]),
        )
