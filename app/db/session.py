from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings


def is_external_pooler(db_url: str) -> bool:
    """
    Detects if the database URL points to an external connection pooler
    such as PgBouncer, Supabase pooled port 6543, or Neon pooler.
    """
    url_lower = db_url.lower()
    return any([
        ":6543" in url_lower,                # Supabase transaction pooler port
        "pooler.supabase.com" in url_lower,  # Supabase pooler host
        "-pooler." in url_lower,             # Neon pooled host
        "pgbouncer=true" in url_lower,       # Explicit PgBouncer query param
    ])


def create_app_engine(db_url: str):
    """
    Configures SQLAlchemy async engine with connection pooling:
    - If URL points to an external connection pooler (PgBouncer/Supabase/Neon),
      NullPool is used because external poolers manage server-side pooling; maintaining
      a client pool on top exhausts pooler connection slots and causes prepared statement conflicts.
    - Otherwise, a pooled engine with pool_pre_ping and pool_recycle is used to avoid
      handshake latency and automatically discard stale connections.
    """
    if is_external_pooler(db_url):
        return create_async_engine(
            db_url,
            echo=False,
            poolclass=NullPool,
        )
    return create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
    )


engine = create_app_engine(settings.DATABASE_URL)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
