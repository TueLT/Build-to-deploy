from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import get_settings
from src.db.base import Base

settings = get_settings()


def _async_url(url: str) -> str:
    # SQLite is accepted only in APP_ENV=test (enforced by Settings) and is kept here solely for
    # fast, isolated unit tests.
    if url.startswith("sqlite:///") and "+aiosqlite" not in url:
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# Tests exercise the app from more than one event loop (pytest-asyncio's session loop for the
# httpx-based `client` fixture, plus Starlette TestClient's own background-thread loop for
# websocket tests) - a real asyncpg connection is bound to the loop that created it, so a pooled
# connection checked out from a different loop than the one that opened it breaks with
# "attached to a different loop". NullPool sidesteps this by opening a fresh connection on every
# checkout instead of reusing one across loops; production keeps normal pooling.
_engine_kwargs = {"poolclass": NullPool} if settings.app_env == "test" else {}
# asyncpg's connect() takes an `ssl` kwarg, but the SQLite unit-test driver does not.
if settings.database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
    # "prefer" negotiates SSL when the server offers it (managed Postgres like Supabase) and
    # falls back to plaintext otherwise (local dev, CI's postgres service container).
    _engine_kwargs["connect_args"] = {"ssl": "prefer"}
engine = create_async_engine(_async_url(settings.database_url), **_engine_kwargs)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
