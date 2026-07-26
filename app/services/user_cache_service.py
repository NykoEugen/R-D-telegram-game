"""
User Cache Service for the Telegram RPG game bot.

This service provides caching for users and players to avoid repeated database queries.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.models.player import Player
from app.models.user import User
from app.services.logging_service import get_logger

logger = get_logger(__name__)


@dataclass
class CachedUser:
    """Cached user data with expiration."""
    user: User
    player: Player
    cached_at: datetime
    expires_at: datetime


class UserCacheService:
    """Service for caching users and players to reduce database queries."""
    
    def __init__(self, cache_duration_minutes: int = 30):
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self._cache: dict[int, CachedUser] = {}
        self._telegram_to_user_id: dict[int, int] = {}
    
    def get_cached_user(self, telegram_id: int) -> CachedUser | None:
        """
        Get cached user data if still valid.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            CachedUser if found and not expired, None otherwise
        """
        # First check if we have telegram_id mapping
        user_id = self._telegram_to_user_id.get(telegram_id)
        if not user_id:
            return None
        
        # Get cached user
        cached_user = self._cache.get(user_id)
        if not cached_user:
            return None
        
        # Check if cache is still valid
        if datetime.utcnow() > cached_user.expires_at:
            # Cache expired, remove it
            self._remove_from_cache(user_id, telegram_id)
            return None
        
        logger.debug("User cache hit", 
                    telegram_id=telegram_id, 
                    user_id=user_id,
                    cached_at=cached_user.cached_at)
        
        return cached_user
    
    def cache_user(self, telegram_id: int, user: User, player: Player) -> None:
        """
        Cache user and player data.
        
        Args:
            telegram_id: Telegram user ID
            user: User instance
            player: Player instance
        """
        now = datetime.utcnow()
        expires_at = now + self.cache_duration
        
        cached_user = CachedUser(
            user=user,
            player=player,
            cached_at=now,
            expires_at=expires_at
        )
        
        # Store in cache
        self._cache[user.id] = cached_user
        self._telegram_to_user_id[telegram_id] = user.id
        
        logger.debug("User cached", 
                    telegram_id=telegram_id, 
                    user_id=user.id,
                    player_id=player.id,
                    expires_at=expires_at)
    
    def _remove_from_cache(self, user_id: int, telegram_id: int) -> None:
        """Remove user from cache."""
        if user_id in self._cache:
            del self._cache[user_id]
        if telegram_id in self._telegram_to_user_id:
            del self._telegram_to_user_id[telegram_id]
        
        logger.debug("User removed from cache", 
                    telegram_id=telegram_id, 
                    user_id=user_id)
    
    def invalidate_user(self, telegram_id: int) -> None:
        """
        Invalidate cached user data.
        
        Args:
            telegram_id: Telegram user ID
        """
        user_id = self._telegram_to_user_id.get(telegram_id)
        if user_id:
            self._remove_from_cache(user_id, telegram_id)
            logger.info("User cache invalidated", 
                       telegram_id=telegram_id, 
                       user_id=user_id)
    
    def clear_expired_cache(self) -> int:
        """
        Clear expired cache entries.
        
        Returns:
            Number of entries removed
        """
        now = datetime.utcnow()
        expired_telegram_ids = []
        
        for user_id, cached_user in list(self._cache.items()):
            if now > cached_user.expires_at:
                # Find telegram_id for this user_id
                for tg_id, uid in self._telegram_to_user_id.items():
                    if uid == user_id:
                        expired_telegram_ids.append(tg_id)
                        break
                
                del self._cache[user_id]
        
        for telegram_id in expired_telegram_ids:
            if telegram_id in self._telegram_to_user_id:
                del self._telegram_to_user_id[telegram_id]
        
        if expired_telegram_ids:
            logger.info("Cleared expired cache entries", 
                       count=len(expired_telegram_ids))
        
        return len(expired_telegram_ids)
    
    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        now = datetime.utcnow()
        active_entries = sum(1 for cached_user in self._cache.values() 
                           if now <= cached_user.expires_at)
        
        return {
            "total_entries": len(self._cache),
            "active_entries": active_entries,
            "expired_entries": len(self._cache) - active_entries,
            "telegram_mappings": len(self._telegram_to_user_id),
            "cache_duration_minutes": self.cache_duration.total_seconds() / 60
        }


# Global cache instance
user_cache = UserCacheService()
