"""Entorno de Alembic.

Las migraciones se ejecutan con el rol PROPIETARIO (``MIGRATIONS_DATABASE_URL``), nunca con el
rol de la aplicación. Se escriben a mano en SQL: las restricciones de exclusión, los
disparadores y los permisos por tabla no se pueden expresar con autogeneración.
"""

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import get_settings

config = context.config
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(url=get_settings().migrations_database_url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_settings().migrations_database_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
