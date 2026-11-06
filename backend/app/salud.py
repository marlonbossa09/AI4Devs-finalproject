"""Comprobaciones de salud y disponibilidad (``/health`` y ``/health/ready``).

Independientes de las funcionalidades de negocio: sin autenticación, sin prefijo ``/api/v1`` y
sin tocar tablas del dominio. Pensadas para balanceadores y orquestadores (por ejemplo AWS ECS):

- ``GET /health`` es la comprobación de VIVACIDAD: responde 200 si el proceso de FastAPI atiende
  peticiones. No usa la base de datos, así que un fallo de PostgreSQL no hace que el
  orquestador reinicie un contenedor que no tiene la culpa.
- ``GET /health/ready`` es la de DISPONIBILIDAD: ejecuta una consulta ligera (``SELECT 1``) y
  responde 200 si PostgreSQL contesta, o 503 si no. La espera máxima la acota
  ``DB_CONNECT_TIMEOUT_SECONDS``.

Las respuestas son JSON mínimo y nunca incluyen credenciales, cadenas de conexión, nombres de
servidor, datos de personas ni mensajes de error de la base de datos: ante un fallo solo se
registra el TIPO de excepción, no su texto (que podría contener la cadena de conexión).
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db import get_engine

logger = logging.getLogger("smartwork")

router = APIRouter(tags=["Salud"])

# Una comprobación de salud nunca debe quedar en una caché intermedia.
SIN_CACHE = {"Cache-Control": "no-store"}


@router.get("/health", summary="Vivacidad: el proceso atiende peticiones")
def vivacidad() -> JSONResponse:
    return JSONResponse({"status": "ok"}, headers=SIN_CACHE)


@router.get("/health/ready", summary="Disponibilidad: PostgreSQL responde")
def disponibilidad() -> JSONResponse:
    try:
        with get_engine().connect() as conexion:
            conexion.execute(text("select 1"))
    except Exception as error:  # cualquier fallo de la base de datos significa "no disponible"
        logger.warning("Disponibilidad: PostgreSQL no responde (%s)", type(error).__name__)
        return JSONResponse(
            {"status": "unavailable", "checks": {"database": "unavailable"}},
            status_code=503,
            headers=SIN_CACHE,
        )
    return JSONResponse({"status": "ok", "checks": {"database": "ok"}}, headers=SIN_CACHE)
