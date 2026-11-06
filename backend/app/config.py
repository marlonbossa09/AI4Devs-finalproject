"""Configuración del backend.

Todos los parámetros configurables (límites de texto, duración de sesión, ventana de
idempotencia, costes de Argon2) se leen del entorno. Ningún valor está fijado en el código
(BE-01). Los valores por defecto son de desarrollo y no son reglas del producto.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Solo existen entornos de desarrollo y de pruebas; no hay configuración de producción.
    app_env: Literal["development", "test"] = "development"

    # Nombre del rol de la aplicación: lo usan las migraciones para conceder permisos por tabla
    app_db_role: str = "smartwork_app"

    # Segundos máximos para conectar con PostgreSQL y para esperar una conexión libre del pool.
    # Acota también la comprobación /health/ready: una base caída responde 503 en vez de colgarse.
    db_connect_timeout_seconds: int = Field(default=3, gt=0)

    database_url: str
    migrations_database_url: str
    test_database_url: str | None = None
    test_migrations_database_url: str | None = None

    # Carpeta del cliente web compilado (flutter build web). Si se indica y existe, FastAPI la sirve
    # en el mismo origen que la API (ADR-002); si no, solo se publica la API.
    web_client_dir: str | None = None

    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    session_idle_minutes: int = Field(default=30, gt=0)
    session_absolute_minutes: int = Field(default=480, gt=0)

    # Cada cuántos segundos se actualiza el último uso de la sesión (para no escribir en cada petición)
    session_touch_seconds: int = Field(default=60, gt=0)
    # Longitudes máximas de entrada del inicio de sesión (evita costes abusivos de hash)
    login_identifier_max_length: int = Field(default=200, gt=0)
    login_password_max_length: int = Field(default=1024, gt=0)
    # Longitud mínima de una contraseña nueva (ADR-002, sección 7). Parámetro configurable.
    password_min_length: int = Field(default=10, gt=0)

    text_max_title: int = Field(default=200, gt=0)
    text_max_description: int = Field(default=4000, gt=0)
    text_max_summary: int = Field(default=8000, gt=0)

    idempotency_window_hours: int = Field(default=24, gt=0)

    argon2_memory_kib: int = Field(default=19456, gt=0)
    argon2_iterations: int = Field(default=2, gt=0)
    argon2_parallelism: int = Field(default=1, gt=0)

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
