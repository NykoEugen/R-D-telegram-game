"""
Player model for the Telegram RPG game bot.

This model represents a player character linked to a User with game stats and progress.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PlayerStatus(str, Enum):
    """Player status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    SUSPENDED = "suspended"


class Player(Base):
    """Player model representing a game character linked to a User."""
    
    __tablename__ = "players"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to User
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Player character information
    character_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    character_class: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Game stats
    health: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_health: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    mana: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    max_mana: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    strength: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    agility: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    intelligence: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    vitality: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    
    # Game currency and resources
    coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gems: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    energy: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_energy: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    
    # Game progress flags
    flags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Game progress flags
    achievements: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # Achievement IDs
    
    # Current game state
    current_scene_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("scenes.id"), nullable=True)
    current_quest_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("quests.id"), nullable=True)
    game_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Additional game state
    
    # Player status
    status: Mapped[PlayerStatus] = mapped_column(String(20), default=PlayerStatus.ACTIVE, nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_played: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="player")
    inventory_items: Mapped[List["InventoryItem"]] = relationship("InventoryItem", back_populates="player")
    quest_progress: Mapped[List["QuestProgress"]] = relationship("QuestProgress", back_populates="player")
    game_sessions: Mapped[List["GameSession"]] = relationship("GameSession", back_populates="player")
    
    def __repr__(self) -> str:
        return f"<Player(id={self.id}, user_id={self.user_id}, character_name={self.character_name}, level={self.level})>"
