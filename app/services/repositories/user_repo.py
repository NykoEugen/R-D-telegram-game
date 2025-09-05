"""
User repository for the Telegram RPG game bot.

This module provides data access methods for User entities.
"""

from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User


class UserRepository:
    """Repository class for User entity operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language: str = "en",
        **kwargs
    ) -> User:
        """
        Create a new user.
        
        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            first_name: Telegram first name
            last_name: Telegram last name
            language: User's preferred language
            **kwargs: Additional user attributes
            
        Returns:
            User: The created user instance
            
        Raises:
            ValueError: If user with telegram_id already exists
        """
        # Check if user already exists
        existing_user = await self.get_user_by_telegram_id(telegram_id)
        if existing_user:
            raise ValueError(f"User with telegram_id {telegram_id} already exists")
        
        # Create new user
        user_data = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "language": language,
            "is_active": True,
            "is_bot": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        # Add any additional attributes
        user_data.update(kwargs)
        
        user = User(**user_data)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        
        return user
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get a user by their ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            User or None if not found
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Get a user by their Telegram ID.
        
        Args:
            telegram_id: The Telegram user ID
            
        Returns:
            User or None if not found
        """
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_with_player(self, telegram_id: int) -> Optional[User]:
        """
        Get a user with their associated player data.
        
        Args:
            telegram_id: The Telegram user ID
            
        Returns:
            User with player relationship loaded or None if not found
        """
        stmt = (
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(User.player))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language: str = "en"
    ) -> User:
        """
        Get an existing user or create a new one.
        
        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            first_name: Telegram first name
            last_name: Telegram last name
            language: User's preferred language
            
        Returns:
            User: The existing or newly created user instance
        """
        # Try to get existing user
        user = await self.get_user_by_telegram_id(telegram_id)
        if user:
            # Update user info if provided
            updates = {}
            if username is not None:
                updates["username"] = username
            if first_name is not None:
                updates["first_name"] = first_name
            if last_name is not None:
                updates["last_name"] = last_name
            if language is not None:
                updates["language"] = language
            
            if updates:
                updates["updated_at"] = datetime.utcnow()
                await self.update_user(user.id, **updates)
                await self.session.refresh(user)
            
            return user
        
        # Create new user
        return await self.create_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language=language
        )
    
    async def update_user(self, user_id: int, **updates) -> Optional[User]:
        """
        Update a user's attributes.
        
        Args:
            user_id: The user ID to update
            **updates: Dictionary of attributes to update
            
        Returns:
            Updated User or None if not found
        """
        # Add updated_at timestamp
        updates["updated_at"] = datetime.utcnow()
        
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**updates)
            .returning(User)
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            await self.session.refresh(user)
        
        return user
    
    async def update_user_activity(self, telegram_id: int) -> bool:
        """
        Update user's last activity timestamp.
        
        Args:
            telegram_id: The Telegram user ID
            
        Returns:
            True if updated, False if user not found
        """
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(last_activity=datetime.utcnow(), updated_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def set_user_active(self, user_id: int, is_active: bool = True) -> bool:
        """
        Set a user's active status.
        
        Args:
            user_id: The user ID
            is_active: Active status
            
        Returns:
            True if updated, False if user not found
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(is_active=is_active, updated_at=datetime.utcnow())
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Delete a user (soft delete by setting is_active to False).
        
        Args:
            user_id: The user ID
            
        Returns:
            True if deleted, False if user not found
        """
        return await self.set_user_active(user_id, False)
    
    async def hard_delete_user(self, user_id: int) -> bool:
        """
        Permanently delete a user from the database.
        
        Args:
            user_id: The user ID
            
        Returns:
            True if deleted, False if user not found
        """
        stmt = delete(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def get_active_users(self) -> List[User]:
        """
        Get all active users.
        
        Returns:
            List of active users
        """
        stmt = select(User).where(User.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_users_by_language(self, language: str) -> List[User]:
        """
        Get all users with a specific language preference.
        
        Args:
            language: The language code
            
        Returns:
            List of users with the specified language
        """
        stmt = select(User).where(User.language == language)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
