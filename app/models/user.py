"""
User model for the Telegram RPG game bot.

This model represents a user in the game system with basic Telegram information.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.player import Player
    from app.models.player_progress import PlayerProgress


class User(Base):
    """User model representing a Telegram user in the game."""
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Telegram user information
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # User preferences
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    players: Mapped[List["Player"]] = relationship(
        "Player",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="Player.slot"
    )
    progress: Mapped[Optional["PlayerProgress"]] = relationship(
        "PlayerProgress", 
        back_populates="user", 
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    
    @property
    def player(self) -> Optional["Player"]:
        """Return active player for backward compatibility."""
        for p in self.players:
            if p.is_active:
                return p
        return self.players[0] if self.players else None

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"
