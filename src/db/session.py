"""
Database session and engine management.

Provides async database connections with proper connection pooling,
transaction management, and context managers.

Responsibility: Manage database connections and sessions
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker
)
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class Database:
    """
    Database connection manager.
    
    Handles engine creation, connection pooling, and session management
    for PostgreSQL/pgvector environments.
    
    Example:
        # Initialize
        db = Database()
        await db.initialize()
        
        # Use session
        async with db.session() as session:
            result = await session.execute(query)
        
        # Cleanup
        await db.close()
    """
    
    def __init__(self):
        """Initialize database manager"""
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize database engine and session factory.
        
    Creates an async engine configured for PostgreSQL/pgvector.
        """
        if self._initialized:
            logger.warning("Database already initialized")
            return
        
        connection_string = settings.db.connection_string
        
        logger.info(f"Initializing database: {connection_string.split('://')[0]}")
        
        # Configure PostgreSQL connection pool
        pool_kwargs = {
            "pool_size": settings.db.pool_size,
            "max_overflow": settings.db.max_overflow,
            "pool_timeout": settings.db.pool_timeout,
            "pool_recycle": settings.db.pool_recycle,
        }
        logger.info(
            "Using PostgreSQL with async pooling "
            f"(size={settings.db.pool_size}, max_overflow={settings.db.max_overflow})"
        )
        
        # Create async engine
        engine_kwargs = {
            "echo": settings.db.echo,
            "echo_pool": settings.db.echo_pool,
            **pool_kwargs
        }
        
        self.engine = create_async_engine(connection_string, **engine_kwargs)
        
        # Create session factory
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Manual flush control
            autocommit=False  # Manual transaction control
        )
        
        self._initialized = True
        logger.info("Database initialized successfully")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create a new database session with automatic cleanup.
        
        Provides proper transaction management with automatic rollback
        on errors and commit on success.
        
        Yields:
            AsyncSession for database operations
        
        Example:
            async with db.session() as session:
                result = await session.execute(query)
                await session.commit()
        """
        if not self._initialized or not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        session = self.session_factory()
        
        try:
            yield session
            # Auto-commit on success (if not already committed)
            if session.in_transaction():
                await session.commit()
        except Exception as e:
            # Auto-rollback on error
            logger.error(f"Session error, rolling back: {e}")
            await session.rollback()
            raise
        finally:
            # Always close session
            await session.close()
    
    async def create_tables(self) -> None:
        """
        Create all database tables.
        
        Uses SQLAlchemy metadata to create tables if they don't exist.
        For production, use Alembic migrations instead.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("Database not initialized")
        
        from .models import Base
        
        logger.info("Creating database tables...")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
    
    async def drop_tables(self) -> None:
        """
        Drop all database tables.
        
        WARNING: This deletes all data! Only use in development/testing.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("Database not initialized")
        
        from .models import Base
        
        logger.warning("Dropping all database tables...")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("All database tables dropped")
    
    async def close(self) -> None:
        """
        Close database engine and cleanup connections.
        
        Should be called during application shutdown.
        """
        if not self._initialized:
            return
        
        if self.engine:
            logger.info("Closing database connections...")
            await self.engine.dispose()
            self.engine = None
        
        self.session_factory = None
        self._initialized = False
        
        logger.info("Database closed")


# MARK: - Global helpers

# Global database instance
db = Database()


@asynccontextmanager
async def async_session_factory() -> AsyncGenerator[AsyncSession, None]:
    """Provide an initialized async session context for ad-hoc usage."""
    if not db._initialized:
        await db.initialize()
    async with db.session() as session:
        yield session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency entry point for retrieving an async session."""
    if not db._initialized:
        await db.initialize()

    async with db.session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Backwards-compatible dependency alias expected by existing API routes.
    
    Yields:
        AsyncSession: database session managed with the same commit/rollback
        semantics as `get_db`.
    """
    async for session in get_db():
        yield session
