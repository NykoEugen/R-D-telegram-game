"""
Lore and game content models for the Telegram RPG game bot.

This module defines Scene, Action, Quest, and QuestProgress models with enums for game content.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class SceneType(str, Enum):
    """Scene type enumeration."""
    DIALOGUE = "dialogue"
    COMBAT = "combat"
    EXPLORATION = "exploration"
    SHOP = "shop"
    INVENTORY = "inventory"
    QUEST = "quest"
    CUTSCENE = "cutscene"
    MINIGAME = "minigame"
    MENU = "menu"


class ActionType(str, Enum):
    """Action type enumeration."""
    MOVE = "move"
    TALK = "talk"
    ATTACK = "attack"
    DEFEND = "defend"
    USE_ITEM = "use_item"
    EQUIP_ITEM = "equip_item"
    BUY_ITEM = "buy_item"
    SELL_ITEM = "sell_item"
    ACCEPT_QUEST = "accept_quest"
    COMPLETE_QUEST = "complete_quest"
    CUSTOM = "custom"


class QuestStatus(str, Enum):
    """Quest status enumeration."""
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class QuestType(str, Enum):
    """Quest type enumeration."""
    MAIN = "main"
    SIDE = "side"
    DAILY = "daily"
    WEEKLY = "weekly"
    EVENT = "event"
    TUTORIAL = "tutorial"


class Scene(Base):
    """Scene model representing game scenes and locations."""
    
    __tablename__ = "scenes"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Scene identification
    scene_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Scene properties
    scene_type: Mapped[SceneType] = mapped_column(String(50), nullable=False)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    level_requirement: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Scene content
    content: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Scene-specific data
    background_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    music_track: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Scene connections
    connected_scenes: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # List of connected scene IDs
    
    # Scene requirements
    required_flags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # Required player flags
    required_items: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # Required item IDs
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    actions: Mapped[List["Action"]] = relationship("Action", back_populates="scene")
    
    def __repr__(self) -> str:
        return f"<Scene(id={self.id}, scene_id={self.scene_id}, name={self.name}, type={self.scene_type})>"


class Action(Base):
    """Action model representing available actions in scenes."""
    
    __tablename__ = "actions"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to Scene
    scene_id: Mapped[int] = mapped_column(Integer, ForeignKey("scenes.id"), nullable=False)
    
    # Action identification
    action_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Action properties
    action_type: Mapped[ActionType] = mapped_column(String(50), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Display order
    
    # Action requirements
    level_requirement: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    required_flags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    required_items: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    cost_energy: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_mana: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Action effects
    effects: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    target_scene_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Action data
    action_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    scene: Mapped["Scene"] = relationship("Scene", back_populates="actions")
    
    def __repr__(self) -> str:
        return f"<Action(id={self.id}, action_id={self.action_id}, name={self.name}, type={self.action_type})>"


class Quest(Base):
    """Quest model representing game quests and objectives."""
    
    __tablename__ = "quests"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Quest identification
    quest_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Quest properties
    quest_type: Mapped[QuestType] = mapped_column(String(50), nullable=False)
    is_repeatable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_repeats: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Quest requirements
    level_requirement: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    required_flags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    required_quests: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # Prerequisite quest IDs
    
    # Quest objectives
    objectives: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    
    # Quest rewards
    experience_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_reward: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    
    # Quest data
    quest_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Quest availability
    start_scene_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    end_scene_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    quest_progress: Mapped[List["QuestProgress"]] = relationship("QuestProgress", back_populates="quest")
    
    def __repr__(self) -> str:
        return f"<Quest(id={self.id}, quest_id={self.quest_id}, name={self.name}, type={self.quest_type})>"


class QuestProgress(Base):
    """QuestProgress model representing player progress on quests."""
    
    __tablename__ = "quest_progress"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    quest_id: Mapped[int] = mapped_column(Integer, ForeignKey("quests.id"), nullable=False)
    
    # Quest progress
    status: Mapped[QuestStatus] = mapped_column(String(20), default=QuestStatus.AVAILABLE, nullable=False)
    current_objective: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Quest completion
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    repeat_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Quest rewards (tracking what was given)
    rewards_claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="quest_progress")
    quest: Mapped["Quest"] = relationship("Quest", back_populates="quest_progress")
    
    def __repr__(self) -> str:
        return f"<QuestProgress(id={self.id}, player_id={self.player_id}, quest_id={self.quest_id}, status={self.status})>"
