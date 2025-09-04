"""
Database configuration and session management for the Telegram RPG game bot.

This module provides async SQLAlchemy engine, session management, and base model class.
"""

import asyncio
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import settings

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    metadata = metadata


# Global engine and session factory
engine: Optional[AsyncEngine] = None
async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


async def init_db() -> None:
    """
    Initialize the database engine and session maker.
    
    This function should be called once at application startup.
    """
    global engine, async_session_maker
    
    if engine is not None:
        return
    
    # Create async engine with optimized settings
    engine = create_async_engine(
        settings.database_url,
        echo=settings.log_level == "DEBUG",  # Enable SQL logging in debug mode
        poolclass=NullPool,  # Use NullPool for async operations
        future=True,
    )
    
    # Create session maker
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_db() -> None:
    """
    Close the database engine and cleanup resources.
    
    This function should be called at application shutdown.
    """
    global engine
    
    if engine is not None:
        await engine.dispose()
        engine = None


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session with automatic cleanup.
    
    Usage:
        async with get_db_session() as session:
            # Use session here
            pass
    """
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI or similar frameworks.
    
    This is a generator that yields a database session.
    """
    async with get_db_session() as session:
        yield session


async def create_tables() -> None:
    """
    Create all database tables.
    
    This function should be called after defining all models.
    """
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data!
    """
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Health check function
async def check_db_health() -> bool:
    """
    Check if the database connection is healthy.
    
    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        if engine is None:
            return False
        
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# Utility functions for common database operations
async def execute_in_session(func, *args, **kwargs):
    """
    Execute a function within a database session.
    
    Args:
        func: Function to execute
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        Result of the function execution
    """
    async with get_db_session() as session:
        return await func(session, *args, **kwargs)
