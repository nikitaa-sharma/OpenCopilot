import logging
from typing import AsyncGenerator, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings
from app.models.base import Base
import app.models  # noqa: F401 - ensure all entity models are registered on Base.metadata

logger = logging.getLogger(__name__)

# Lazy or configured async engine for PostgreSQL
# Supports connection pooling once PostgreSQL is provisioned
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an asynchronous database session.
    Automatically handles session closing and rollback on errors.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(target_engine: Optional[AsyncEngine] = None) -> bool:
    """
    Initialize database extension 'vector' and create all tables.
    Returns True if successfully initialized, False if database is unreachable.
    Safe to run repeatedly.
    """
    eng = target_engine or engine
    try:
        async with eng.begin() as conn:
            # Enable pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            # Create tables
            await conn.run_sync(Base.metadata.create_all)
            # Ensure users table schema migrations for backward compatibility
            try:
                await conn.execute(
                    text(
                        """
                        DO $$
                        BEGIN
                            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
                                ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
                                ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(100);
                                ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
                                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'username') THEN
                                    ALTER TABLE users ALTER COLUMN username DROP NOT NULL;
                                END IF;
                            END IF;
                        END $$;
                        """
                    )
                )
            except Exception as mig_exc:
                logger.debug("Users schema sync notice: %s", mig_exc)
        logger.info("Database and pgvector extension initialized successfully.")
        return True
    except Exception as exc:
        logger.warning(
            f"Database initialization skipped or failed (PostgreSQL/pgvector may be offline): {exc}"
        )
        return False
