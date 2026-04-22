import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from core.config import settings

# Celery workers use NullPool: each task gets a fresh connection,
# avoiding asyncio event-loop cross-contamination between tasks.
_in_celery = os.getenv("CELERY_WORKER_RUNNING", "0") == "1"

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    **({} if _in_celery else {"pool_size": 10, "max_overflow": 20}),
    **({"poolclass": NullPool} if _in_celery else {}),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
