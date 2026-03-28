"""Alembic environment — async-capable, reads DB URL from app settings."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Import app settings and all models so Alembic can diff them.
from app.core.config import settings
from app.models.base import Base  # noqa: F401 — registers metadata
from app.models.organization import Organization  # noqa: F401
from app.models.user import User  # noqa: F401

# ─── Alembic config object ─────────────────────────────────────────────────────
config = context.config

# Propagate Python logging config from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Offline mode uses a sync driver to generate SQL without a live connection.
# We swap asyncpg → psycopg2 only for that path; the online path uses asyncpg
# directly via create_async_engine so it never touches this sync URL.
_sync_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)

target_metadata = Base.metadata


# ─── Offline mode ─────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Generate SQL without a live DB connection (uses psycopg2 dialect)."""
    context.configure(
        url=_sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ─── Online mode ──────────────────────────────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations against a live DB using asyncpg."""
    # Build the engine directly from settings.DATABASE_URL (postgresql+asyncpg://)
    # so Alembic never reads the sync URL from the ini config section.
    engine = create_async_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ─── Entry point ──────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
