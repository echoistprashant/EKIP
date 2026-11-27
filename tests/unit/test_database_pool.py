from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from app.db.session import create_app_engine, is_external_pooler


def test_is_external_pooler_detection():
    """Verify detection of various external connection poolers."""
    # Supabase port 6543
    assert is_external_pooler("postgresql+asyncpg://postgres:pass@db.project.supabase.co:6543/postgres")

    # Supabase pooler host
    assert is_external_pooler("postgresql+asyncpg://postgres.tenant:pass@aws-0-us-east-1.pooler.supabase.com:5432/postgres")

    # Neon pooler endpoint
    assert is_external_pooler("postgresql+asyncpg://user:pass@ep-cool-frog-123456-pooler.us-east-2.aws.neon.tech/neondb")

    # Explicit PgBouncer query flag
    assert is_external_pooler("postgresql+asyncpg://user:pass@render-postgres:5432/db?pgbouncer=true")

    # Direct connection (standard port 5432, local, RDS, Render)
    assert not is_external_pooler("postgresql+asyncpg://ekip_user:ekip_password@localhost:5432/ekip_db")
    assert not is_external_pooler("postgresql+asyncpg://user:pass@dpg-abc-a.oregon-postgres.render.com/db")


def test_create_app_engine_uses_nullpool_for_external_pooler():
    """Verify that external pooler URLs use NullPool to avoid double-pooling."""
    engine = create_app_engine("postgresql+asyncpg://user:pass@ep-cool-frog-pooler.neon.tech/db")
    assert isinstance(engine.pool, NullPool)


def test_create_app_engine_uses_queue_pool_with_pre_ping_for_direct_db():
    """Verify that direct connections use AsyncAdaptedQueuePool with pre_ping and recycle."""
    engine = create_app_engine("postgresql+asyncpg://user:pass@localhost:5432/ekip_db")
    assert isinstance(engine.pool, AsyncAdaptedQueuePool)
    assert engine.pool._pre_ping is True
    assert engine.pool._recycle == 1800
