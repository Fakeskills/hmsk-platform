import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def set_rls_context(
    session: AsyncSession,
    tenant_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> None:
    t = str(tenant_id) if tenant_id else ""
    u = str(user_id) if user_id else ""
    await session.execute(text(f"SET LOCAL app.tenant_id = '{t}'"))
    await session.execute(text(f"SET LOCAL app.user_id   = '{u}'"))


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
