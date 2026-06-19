"""
Banking Cloud Log Analyser - Database Configuration
Async SQLAlchemy engine and session management.
Supports PostgreSQL (asyncpg) and SQLite (aiosqlite) based on DATABASE_URL.
"""

# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import DeclarativeBase
# pyrefly: ignore [missing-import]
from sqlalchemy import event, JSON

from app.config import get_settings

settings = get_settings()

# Detect database type from URL
is_sqlite = settings.database_url.startswith("sqlite")

# Engine configuration
engine_kwargs = {
    "echo": settings.debug,
}

if not is_sqlite:
    # PostgreSQL connection pool settings
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })

engine = create_async_engine(settings.database_url, **engine_kwargs)

# Enable WAL mode for SQLite (better concurrent access)
if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    # Use JSON type for SQLite compatibility (JSONB falls back to JSON)
    type_annotation_map = {
        dict: JSON,
    }


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. Used on application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the engine. Used on application shutdown."""
    await engine.dispose()
