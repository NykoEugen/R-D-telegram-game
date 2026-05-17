"""
Cache Cleanup Service for the Telegram RPG game bot.

This service provides background cleanup of expired cache entries.
"""

import asyncio
from typing import Optional
from datetime import datetime, timedelta

from app.services.user_cache_service import user_cache
from app.services.logging_service import get_logger

logger = get_logger(__name__)


class CacheCleanupService:
    """Service for cleaning up expired cache entries."""
    
    def __init__(self, cleanup_interval_minutes: int = 5):
        self.cleanup_interval = timedelta(minutes=cleanup_interval_minutes)
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the cache cleanup service."""
        if self._running:
            logger.warning("Cache cleanup service is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info("Cache cleanup service started", 
                   cleanup_interval_minutes=self.cleanup_interval.total_seconds() / 60)
    
    async def stop(self) -> None:
        """Stop the cache cleanup service."""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Cache cleanup service stopped")
    
    async def _cleanup_loop(self) -> None:
        """Main cleanup loop."""
        while self._running:
            try:
                # Wait for cleanup interval
                await asyncio.sleep(self.cleanup_interval.total_seconds())
                
                if not self._running:
                    break
                
                # Clean up expired entries
                removed_count = user_cache.clear_expired_cache()
                
                if removed_count > 0:
                    logger.info("Cache cleanup completed", 
                               removed_entries=removed_count)
                
                # Log cache stats periodically
                stats = user_cache.get_cache_stats()
                logger.debug("Cache statistics", **stats)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cache cleanup loop",
                           error_type=type(e).__name__,
                           error_message=str(e))
                # Continue running even if there's an error
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        return user_cache.get_cache_stats()


# Global cache cleanup service instance
cache_cleanup_service = CacheCleanupService()
