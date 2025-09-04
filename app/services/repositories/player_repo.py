"""
Player repository for the Telegram RPG game bot.

This module provides data access methods for Player entities.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.player import Player, PlayerStatus
from app.models.user import User


class PlayerRepository:
    """Repository class for Player entity operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_player(
        self,
        user_id: int,
        character_name: Optional[str] = None,
        character_class: Optional[str] = None,
        **kwargs
    ) -> Player:
        """
        Create a new player for a user.
        
        Args:
            user_id: ID of the user to create player for
            character_name: Optional character name
            character_class: Optional character class
            **kwargs: Additional player attributes
            
        Returns:
            Player: The created player instance
            
        Raises:
            ValueError: If user already has a player
        """
        # Check if user already has a player
        existing_player = await self.get_player_by_user_id(user_id)
        if existing_player:
            raise ValueError(f"User {user_id} already has a player")
        
        # Create new player
        player_data = {
            "user_id": user_id,
            "character_name": character_name,
            "character_class": character_class,
            "status": PlayerStatus.ACTIVE,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        # Add any additional attributes
        player_data.update(kwargs)
        
        player = Player(**player_data)
        self.session.add(player)
        await self.session.flush()
        await self.session.refresh(player)
        
        return player
    
    async def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """
        Get a player by their ID.
        
        Args:
            player_id: The player ID
            
        Returns:
            Player or None if not found
        """
        stmt = select(Player).where(Player.id == player_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_player_by_user_id(self, user_id: int) -> Optional[Player]:
        """
        Get a player by their user ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            Player or None if not found
        """
        stmt = select(Player).where(Player.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_player_by_telegram_id(self, telegram_id: int) -> Optional[Player]:
        """
        Get a player by their Telegram ID.
        
        Args:
            telegram_id: The Telegram user ID
            
        Returns:
            Player or None if not found
        """
        stmt = (
            select(Player)
            .join(User, Player.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(Player.user))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_player_with_user(self, player_id: int) -> Optional[Player]:
        """
        Get a player with their associated user data.
        
        Args:
            player_id: The player ID
            
        Returns:
            Player with user relationship loaded or None if not found
        """
        stmt = (
            select(Player)
            .where(Player.id == player_id)
            .options(selectinload(Player.user))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_players_by_status(self, status: PlayerStatus) -> List[Player]:
        """
        Get all players with a specific status.
        
        Args:
            status: The player status to filter by
            
        Returns:
            List of players with the specified status
        """
        stmt = select(Player).where(Player.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_online_players(self) -> List[Player]:
        """
        Get all currently online players.
        
        Returns:
            List of online players
        """
        stmt = select(Player).where(Player.is_online == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_players_by_level_range(self, min_level: int, max_level: int) -> List[Player]:
        """
        Get players within a specific level range.
        
        Args:
            min_level: Minimum level (inclusive)
            max_level: Maximum level (inclusive)
            
        Returns:
            List of players within the level range
        """
        stmt = select(Player).where(
            and_(Player.level >= min_level, Player.level <= max_level)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_player(self, player_id: int, **updates) -> Optional[Player]:
        """
        Update a player's attributes.
        
        Args:
            player_id: The player ID to update
            **updates: Dictionary of attributes to update
            
        Returns:
            Updated Player or None if not found
        """
        # Add updated_at timestamp
        updates["updated_at"] = datetime.utcnow()
        
        stmt = (
            update(Player)
            .where(Player.id == player_id)
            .values(**updates)
            .returning(Player)
        )
        result = await self.session.execute(stmt)
        player = result.scalar_one_or_none()
        
        if player:
            await self.session.refresh(player)
        
        return player
    
    async def update_player_status(self, player_id: int, status: PlayerStatus) -> bool:
        """
        Update a player's status.
        
        Args:
            player_id: The player ID
            status: New status
            
        Returns:
            True if updated, False if player not found
        """
        stmt = (
            update(Player)
            .where(Player.id == player_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def set_player_online(self, player_id: int, is_online: bool = True) -> bool:
        """
        Set a player's online status.
        
        Args:
            player_id: The player ID
            is_online: Online status
            
        Returns:
            True if updated, False if player not found
        """
        updates = {
            "is_online": is_online,
            "updated_at": datetime.utcnow()
        }
        
        if is_online:
            updates["last_played"] = datetime.utcnow()
        
        stmt = (
            update(Player)
            .where(Player.id == player_id)
            .values(**updates)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def add_experience(self, player_id: int, exp_amount: int) -> Optional[Player]:
        """
        Add experience to a player and handle level up if needed.
        
        Args:
            player_id: The player ID
            exp_amount: Amount of experience to add
            
        Returns:
            Updated Player or None if not found
        """
        player = await self.get_player_by_id(player_id)
        if not player:
            return None
        
        # Add experience
        new_exp = player.experience + exp_amount
        new_level = self._calculate_level(new_exp)
        
        updates = {
            "experience": new_exp,
            "level": new_level,
            "updated_at": datetime.utcnow()
        }
        
        # If leveled up, increase stats
        if new_level > player.level:
            level_diff = new_level - player.level
            updates.update({
                "max_health": player.max_health + (level_diff * 10),
                "health": player.max_health + (level_diff * 10),  # Full heal on level up
                "max_mana": player.max_mana + (level_diff * 5),
                "mana": player.max_mana + (level_diff * 5),  # Full mana on level up
                "strength": player.strength + level_diff,
                "agility": player.agility + level_diff,
                "intelligence": player.intelligence + level_diff,
                "vitality": player.vitality + level_diff,
            })
        
        return await self.update_player(player_id, **updates)
    
    async def add_currency(self, player_id: int, coins: int = 0, gems: int = 0) -> Optional[Player]:
        """
        Add currency to a player.
        
        Args:
            player_id: The player ID
            coins: Amount of coins to add
            gems: Amount of gems to add
            
        Returns:
            Updated Player or None if not found
        """
        player = await self.get_player_by_id(player_id)
        if not player:
            return None
        
        updates = {
            "coins": player.coins + coins,
            "gems": player.gems + gems,
            "updated_at": datetime.utcnow()
        }
        
        return await self.update_player(player_id, **updates)
    
    async def update_player_flags(self, player_id: int, flags: Dict[str, Any]) -> Optional[Player]:
        """
        Update a player's game flags.
        
        Args:
            player_id: The player ID
            flags: Dictionary of flags to update
            
        Returns:
            Updated Player or None if not found
        """
        player = await self.get_player_by_id(player_id)
        if not player:
            return None
        
        current_flags = player.flags or {}
        current_flags.update(flags)
        
        return await self.update_player(player_id, flags=current_flags)
    
    async def delete_player(self, player_id: int) -> bool:
        """
        Delete a player (soft delete by setting status to inactive).
        
        Args:
            player_id: The player ID
            
        Returns:
            True if deleted, False if player not found
        """
        return await self.update_player_status(player_id, PlayerStatus.INACTIVE)
    
    async def hard_delete_player(self, player_id: int) -> bool:
        """
        Permanently delete a player from the database.
        
        Args:
            player_id: The player ID
            
        Returns:
            True if deleted, False if player not found
        """
        stmt = delete(Player).where(Player.id == player_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    def _calculate_level(self, experience: int) -> int:
        """
        Calculate player level based on experience.
        
        Args:
            experience: Total experience points
            
        Returns:
            Player level
        """
        # Simple level calculation: 100 exp per level
        return max(1, (experience // 100) + 1)
    
    async def get_player_stats(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive player statistics.
        
        Args:
            player_id: The player ID
            
        Returns:
            Dictionary with player stats or None if not found
        """
        player = await self.get_player_by_id(player_id)
        if not player:
            return None
        
        return {
            "id": player.id,
            "character_name": player.character_name,
            "character_class": player.character_class,
            "level": player.level,
            "experience": player.experience,
            "health": player.health,
            "max_health": player.max_health,
            "mana": player.mana,
            "max_mana": player.max_mana,
            "strength": player.strength,
            "agility": player.agility,
            "intelligence": player.intelligence,
            "vitality": player.vitality,
            "coins": player.coins,
            "gems": player.gems,
            "energy": player.energy,
            "max_energy": player.max_energy,
            "status": player.status,
            "is_online": player.is_online,
            "last_played": player.last_played,
            "created_at": player.created_at,
        }
