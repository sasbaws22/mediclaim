import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logging.config import fileConfig
import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config, AsyncConnection
from sqlalchemy import pool
from alembic import context
from sqlmodel import SQLModel
from app.core.config import settings

# Load the database URL from the configuration
database_url = settings.DATABASE_URL

# Alembic Config object
config = context.config

# Set the database URL in Alembic's config
config.set_main_option("sqlalchemy.url", database_url)

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
# For example: from myapp.models import Base
target_metadata = SQLModel.metadata


def do_run_migrations(connection: AsyncConnection) -> None:
    """
    Configure and run migrations within the given connection.
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with an asynchronous engine.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    meaning no database connection is required.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode by invoking the async migration logic.
    """
    asyncio.run(run_async_migrations())


# Run migrations based on the context mode (offline/online)
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
