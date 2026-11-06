"""Punto de entrada de la API de SMARTWORK (monolito modular, prefijo /api/v1)."""

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.errores import registrar_manejadores
from app.modulos.acceso.router import router as router_acceso
from app.modulos.bitacoras.router import router as router_bitacoras
from app.salud import router as router_salud

API_PREFIX = "/api/v1"


def crear_app() -> FastAPI:
    settings = get_settings()
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
            allow_methods=["GET", "POST", "PUT"],
            allow_headers=["Content-Type", "Idempotency-Key", "X-CSRF-Token"],
        )

    api = APIRouter(prefix=API_PREFIX)
    # Los routers de cada módulo se registran aquí, a medida que se implementan.
    api.include_router(router_acceso)
    api.include_router(router_bitacoras)
    app.include_router(api)
    # Salud y disponibilidad: en la raíz, sin /api/v1 y sin autenticación; antes del cliente web.
    app.include_router(router_salud)

    # El cliente compilado se sirve DESPUÉS de las rutas de la API, que tienen prioridad.
    if settings.web_client_dir and Path(settings.web_client_dir).is_dir():
        app.mount("/", StaticFiles(directory=settings.web_client_dir, html=True), name="cliente")
    return app


app = crear_app()
