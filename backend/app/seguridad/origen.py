"""Verificación del origen de las peticiones que modifican (ADR-002, sección 12).

Se exige ``Origin`` (o ``Referer`` si falta) y debe coincidir con el origen propio del servidor
o con uno de los orígenes de desarrollo configurados. Sin ninguno de los dos, se rechaza.
"""

from urllib.parse import urlsplit

from fastapi import Request

from app.config import get_settings


def _origen_de(valor: str) -> str | None:
    partes = urlsplit(valor)
    if not partes.scheme or not partes.netloc:
        return None
    return f"{partes.scheme}://{partes.netloc}"


def origen_permitido(request: Request) -> bool:
    presentado = request.headers.get("origin")
    if presentado is None:
        referer = request.headers.get("referer")
        presentado = _origen_de(referer) if referer else None
    if not presentado or presentado == "null":
        return False
    propio = f"{request.url.scheme}://{request.headers.get('host', '')}"
    permitidos = {propio}
    settings = get_settings()
    if settings.app_env == "development":
        permitidos.update(settings.cors_allowed_origins)
    return presentado in permitidos
