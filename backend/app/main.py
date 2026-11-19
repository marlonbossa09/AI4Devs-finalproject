"""Punto de entrada de la API de SMARTWORK (monolito modular, prefijo /api/v1)."""

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from app.config import get_settings
from app.errores import metodos_de_la_api, registrar_manejadores
from app.modulos.acceso.primer_acceso import router as router_primer_acceso
from app.modulos.acceso.router import router as router_acceso
from app.modulos.auditoria.router import router as router_auditoria
from app.modulos.bitacoras.router import router as router_bitacoras
from app.modulos.consulta.router import router as router_consulta
from app.modulos.gestion.router import router as router_gestion
from app.modulos.informes.router import router as router_informes
from app.salud import router as router_salud
from app.seguridad.codigos import comprobar_configuracion as comprobar_secreto_de_codigos
from app.seguridad.contrasenas_comprometidas import comprobar_configuracion as comprobar_listado_de_contrasenas
from app.seguridad.control_de_intentos import comprobar_configuracion

API_PREFIX = "/api/v1"


class ClienteWeb(StaticFiles):
    """Sirve el cliente compilado sin tapar a la API.

    El montaje en la raíz recibe todo lo que ninguna ruta de la API atiende. Si la ruta pedida existe en la API pero con
    otro método (por ejemplo, un GET a una ruta solo de escritura), hay que responder 405 y no buscar un fichero con ese
    nombre, que daría un 404 engañoso (PA-30). Una ruta de la API que no existe es siempre el 404 uniforme."""

    async def get_response(self, path, scope):
        if metodos_de_la_api(scope):
            raise HTTPException(status_code=405)
        ruta = scope.get("path", "")
        if ruta == API_PREFIX or ruta.startswith(API_PREFIX + "/"):
            raise HTTPException(status_code=404)  # una ruta de la API que no existe nunca es un fichero del cliente
        return await super().get_response(path, scope)


def crear_app() -> FastAPI:
    settings = get_settings()
    # Falla al arrancar (no en la primera petición) si falta AUTH_PEPPER: sin él no hay control de intentos (M1-T7).
    comprobar_configuracion()
    comprobar_listado_de_contrasenas()  # un listado configurado e inválido (procedencia, huella) impide arrancar; sin listado, avisa y queda inactivo
    comprobar_secreto_de_codigos()      # CODE_PEPPER es obligatorio para emitir y canjear códigos (M1-T8.3): sin él la API no arranca
    # La documentación interactiva solo existe en desarrollo.
    es_desarrollo = settings.app_env == "development"
    app = FastAPI(
        title="SMARTWORK API",
        version="0.1.0",
        docs_url="/docs" if es_desarrollo else None,
        redoc_url=None,
        openapi_url="/openapi.json" if es_desarrollo else None,
    )
    registrar_manejadores(app)

    # CORS solo en desarrollo y solo para los orígenes configurados. En la demostración el
    # cliente se sirve desde el mismo origen que la API y no hace falta.
    if es_desarrollo and settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "PATCH", "POST", "PUT"],
            allow_headers=["Content-Type", "Idempotency-Key", "X-CSRF-Token"],
            # El cliente (otro origen en desarrollo) necesita leer Retry-After de la respuesta 429 (M1-T7).
            expose_headers=["Retry-After"],
        )

    api = APIRouter(prefix=API_PREFIX)
    # Los routers de cada módulo se registran aquí, a medida que se implementan.
    api.include_router(router_acceso)
    api.include_router(router_primer_acceso)
    api.include_router(router_bitacoras)
    api.include_router(router_auditoria)
    api.include_router(router_consulta)
    api.include_router(router_gestion)
    api.include_router(router_informes)
    app.include_router(api)
    # Salud y disponibilidad: en la raíz, sin /api/v1 y sin autenticación; antes del cliente web.
    app.include_router(router_salud)

    # El cliente compilado se sirve DESPUÉS de las rutas de la API, que tienen prioridad.
    if settings.web_client_dir and Path(settings.web_client_dir).is_dir():
        app.mount("/", ClienteWeb(directory=settings.web_client_dir, html=True), name="cliente")
    return app


app = crear_app()
