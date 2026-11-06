"""Acceso a PostgreSQL.

Hay dos conexiones con propósitos distintos (privilegio mínimo):
- ``engine`` (rol de la aplicación): la usa la API. No tiene permisos de DDL.
- ``owner_engine`` (rol propietario): solo para migraciones y la semilla de desarrollo.
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
        pool_timeout=timeout,
        connect_args={"connect_timeout": timeout},
    )


@lru_cache
def get_owner_engine() -> Engine:
    return create_engine(get_settings().migrations_database_url, pool_pre_ping=True)


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
