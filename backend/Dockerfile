# Imagen del backend de SMARTWORK (FastAPI). Solo lo necesario para ejecutar la API, las migraciones y la semilla de demostración.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts

RUN useradd --system --uid 10001 --no-create-home smartwork && chown -R smartwork /app
USER smartwork

EXPOSE 8000
# Detrás de un proxy inverso (Caddy) en una red privada de Docker: el esquema y la dirección del cliente vienen de sus cabeceras. El puerto 8000 NO se publica.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
