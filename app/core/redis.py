"""
Redis configuration and connection management for the Telegram RPG game bot.

This module provides Redis connection management and utility functions.
"""

import asyncio
from typing import Optional, Any, Union
import json
import pickle
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool

from .config import settings

# Global Redis connection
redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """
    Initialize the Redis connection.
    
    This function should be called once at application startup.
    """
    global redis_client
    
    if redis_client is not None:
        return
    
    # Create connection pool
    pool = ConnectionPool.from_url(
        settings.redis_url,
        max_connections=20,
        retry_on_timeout=True,
        decode_responses=False,  # We'll handle encoding/decoding manually
    )
    
    # Create Redis client
    redis_client = Redis(connection_pool=pool)


async def close_redis() -> None:
    """
    Close the Redis connection and cleanup resources.
    
    This function should be called at application shutdown.
    """
    global redis_client
    
    if redis_client is not None:
        await redis_client.close()
        redis_client = None


def get_redis() -> Redis:
    """
    Get the Redis client instance.
    
    Returns:
        Redis: The Redis client instance
        
    Raises:
        RuntimeError: If Redis is not initialized
    """
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_client


# Utility functions for common Redis operations
async def set_cache(
    key: str, 
    value: Any, 
    expire: Optional[int] = None,
    serialize: bool = True
) -> bool:
    """
    Set a value in Redis cache.
    
    Args:
        key: Cache key
        value: Value to cache
        expire: Expiration time in seconds
        serialize: Whether to serialize the value (default: True)
    
    Returns:
        bool: True if successful
    """
    redis = get_redis()
    
    if serialize:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        else:
            value = pickle.dumps(value)
    
    return await redis.set(key, value, ex=expire)


async def get_cache(
    key: str, 
    deserialize: bool = True,
    default: Any = None
) -> Any:
    """
    Get a value from Redis cache.
    
    Args:
        key: Cache key
        deserialize: Whether to deserialize the value (default: True)
        default: Default value if key not found
    
    Returns:
        Any: Cached value or default
    """
    redis = get_redis()
    value = await redis.get(key)
    
    if value is None:
        return default
    
    if deserialize:
        try:
            # Try JSON first
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            try:
                # Try pickle
                return pickle.loads(value)
            except (pickle.PickleError, TypeError):
                # Return as string
                return value.decode('utf-8') if isinstance(value, bytes) else value
    
    return value


async def delete_cache(key: str) -> bool:
    """
    Delete a key from Redis cache.
    
    Args:
        key: Cache key to delete
    
    Returns:
        bool: True if key was deleted
    """
    redis = get_redis()
    return bool(await redis.delete(key))


async def exists_cache(key: str) -> bool:
    """
    Check if a key exists in Redis cache.
    
    Args:
        key: Cache key to check
    
    Returns:
        bool: True if key exists
    """
    redis = get_redis()
    return bool(await redis.exists(key))


async def expire_cache(key: str, seconds: int) -> bool:
    """
    Set expiration time for a key.
    
    Args:
        key: Cache key
        seconds: Expiration time in seconds
    
    Returns:
        bool: True if expiration was set
    """
    redis = get_redis()
    return bool(await redis.expire(key, seconds))


async def get_cache_ttl(key: str) -> int:
    """
    Get time to live for a key.
    
    Args:
        key: Cache key
    
    Returns:
        int: TTL in seconds, -1 if no expiration, -2 if key doesn't exist
    """
    redis = get_redis()
    return await redis.ttl(key)


# Session management functions
async def set_user_session(user_id: int, session_data: dict, expire: int = 3600) -> bool:
    """
    Store user session data in Redis.
    
    Args:
        user_id: Telegram user ID
        session_data: Session data to store
        expire: Expiration time in seconds (default: 1 hour)
    
    Returns:
        bool: True if successful
    """
    key = f"user_session:{user_id}"
    return await set_cache(key, session_data, expire=expire)


async def get_user_session(user_id: int) -> Optional[dict]:
    """
    Get user session data from Redis.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        dict: Session data or None if not found
    """
    key = f"user_session:{user_id}"
    return await get_cache(key, default=None)


async def delete_user_session(user_id: int) -> bool:
    """
    Delete user session data from Redis.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        bool: True if deleted
    """
    key = f"user_session:{user_id}"
    return await delete_cache(key)


# Rate limiting functions
async def check_rate_limit(key: str, limit: int, window: int) -> tuple[bool, int]:
    """
    Check if a rate limit is exceeded.
    
    Args:
        key: Rate limit key
        limit: Maximum number of requests
        window: Time window in seconds
    
    Returns:
        tuple: (is_allowed, remaining_requests)
    """
    redis = get_redis()
    
    # Use Redis pipeline for atomic operations
    pipe = redis.pipeline()
    current_time = int(await redis.time()[0])
    
    # Remove expired entries
    pipe.zremrangebyscore(key, 0, current_time - window)
    
    # Count current requests
    pipe.zcard(key)
    
    # Add current request
    pipe.zadd(key, {str(current_time): current_time})
    
    # Set expiration
    pipe.expire(key, window)
    
    results = await pipe.execute()
    current_requests = results[1]
    
    is_allowed = current_requests < limit
    remaining = max(0, limit - current_requests - 1)
    
    return is_allowed, remaining


# Health check function
async def check_redis_health() -> bool:
    """
    Check if Redis connection is healthy.
    
    Returns:
        bool: True if Redis is accessible, False otherwise
    """
    try:
        redis = get_redis()
        await redis.ping()
        return True
    except Exception:
        return False
