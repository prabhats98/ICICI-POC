"""
Database Configuration — Supports PostgreSQL and SQLite (local dev fallback).

For Python 3.14+ compatibility (greenlet DLL issue), SQLite mode uses
synchronous SQLAlchemy wrapped in asyncio.to_thread() instead of the
async engine which depends on greenlet.
"""

import asyncio
from functools import partial
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

settings = get_settings()

# SQLite doesn't support pool_size / pool_pre_ping
_is_sqlite = settings.database_url.startswith("sqlite")

# Build sync URL (strip +aiosqlite or +asyncpg)
_sync_url = settings.database_url
if "+aiosqlite" in _sync_url:
    _sync_url = _sync_url.replace("+aiosqlite", "")
elif "+asyncpg" in _sync_url:
    _sync_url = _sync_url.replace("+asyncpg", "")

_engine_kwargs = {
    "echo": settings.debug,
}
if _is_sqlite:
    _engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    })
else:
    _engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })

# Use synchronous engine (greenlet-free)
sync_engine = create_engine(_sync_url, **_engine_kwargs)

SyncSession = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    type_annotation_map = {
        dict: JSON,
    }


class AsyncSessionWrapper:
    """
    Wraps a synchronous SQLAlchemy Session to provide an async-compatible interface.
    Runs all blocking DB operations via asyncio.to_thread() to avoid blocking the event loop.
    """

    def __init__(self, sync_session: Session):
        self._session = sync_session

    async def execute(self, *args, **kwargs):
        return await asyncio.to_thread(self._session.execute, *args, **kwargs)

    def add(self, instance):
        self._session.add(instance)

    def add_all(self, instances):
        self._session.add_all(instances)

    async def commit(self):
        await asyncio.to_thread(self._session.commit)

    async def rollback(self):
        await asyncio.to_thread(self._session.rollback)

    async def close(self):
        await asyncio.to_thread(self._session.close)

    async def flush(self):
        await asyncio.to_thread(self._session.flush)

    async def refresh(self, instance):
        await asyncio.to_thread(self._session.refresh, instance)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


@asynccontextmanager
async def _async_session_ctx() -> AsyncGenerator[AsyncSessionWrapper, None]:
    """Create an async-compatible session context manager."""
    sync_session = SyncSession()
    wrapper = AsyncSessionWrapper(sync_session)
    try:
        yield wrapper
    finally:
        await wrapper.close()


class _AsyncSessionFactory:
    """Callable that returns async session context managers (mimics async_sessionmaker)."""

    def __call__(self) -> AsyncSessionWrapper:
        """Return a context manager that yields an AsyncSessionWrapper."""
        return _async_session_ctx()


# This replaces async_sessionmaker — used throughout the codebase
async_session = _AsyncSessionFactory()


async def get_db() -> AsyncSessionWrapper:
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
    """Create all tables on application startup."""
    Base.metadata.create_all(sync_engine)


async def close_db() -> None:
    """Dispose the engine on application shutdown."""
    sync_engine.dispose()
