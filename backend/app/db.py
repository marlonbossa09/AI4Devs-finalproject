"""Acceso a PostgreSQL.

Hay dos conexiones con propósitos distintos (privilegio mínimo):
- ``engine`` (rol de la aplicación): la usa la API. No tiene permisos de DDL.
- ``owner_engine`` (rol propietario): solo para migraciones y la semilla de desarrollo.
- ``provision_engine`` (rol de provisión): solo para las órdenes de provisión (CLI del servidor).

Los tres ocultan los parámetros de las sentencias en los errores (``hide_parameters``, M1-T8.6): SQLAlchemy los incluye por defecto en el texto de sus
excepciones y el manejador de errores internos las registra; sin esto, un fallo de la base durante un canje dejaría en el registro el hash Argon2 de la
contraseña nueva, el HMAC del código y el identificador de acceso.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    timeout = settings.db_connect_timeout_seconds
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        pool_timeout=timeout,
        connect_args={"connect_timeout": timeout},
    )


@lru_cache
def get_owner_engine() -> Engine:
    return create_engine(get_settings().migrations_database_url, pool_pre_ping=True, hide_parameters=True)


@lru_cache
def get_provision_engine() -> Engine:
    """Conexión del rol de provisión (privilegio mínimo, M1-T2). La usa solo la CLI de provisión."""
    url = get_settings().provision_database_url
    if not url:
        raise RuntimeError("Falta PROVISION_DATABASE_URL: la provisión usa su propio rol de PostgreSQL")
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)


def new_session() -> Session:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)()


def get_db() -> Iterator[Session]:
    """Una sesión por petición. La transacción se confirma solo si la operación termina bien;
    ante cualquier excepción se deshace por completo (una operación rechazada no deja cambios)."""
    session = new_session()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
