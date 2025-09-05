"""
SQLAlchemy models for the Telegram RPG game bot.

This module contains all database models used in the application.
Import the Base class and any models you need from this module.
"""

from app.core.db import Base

# Import all models
from .user import User
from .player import Player, PlayerStatus
from .items import Item, InventoryItem, ItemRarity, ItemType
from .lore import Scene, Action, Quest, QuestProgress, SceneType, ActionType, QuestStatus, QuestType
from .telemetry import GameSession, MessageLog, AIGeneration, SessionStatus, MessageType, AIGenerationType
from .i18n import I18nString, I18nCategory
from .player_progress import PlayerProgress, ExplorationSession, RegionUnlock, PlayerStats

__all__ = [
    "Base",
    # User models
    "User",
    "Player",
    "PlayerStatus",
    # Item models
    "Item",
    "InventoryItem", 
    "ItemRarity",
    "ItemType",
    # Lore models
    "Scene",
    "Action",
    "Quest",
    "QuestProgress",
    "SceneType",
    "ActionType", 
    "QuestStatus",
    "QuestType",
    # Telemetry models
    "GameSession",
    "MessageLog",
    "AIGeneration",
    "SessionStatus",
    "MessageType",
    "AIGenerationType",
    # I18n models
    "I18nString",
    "I18nCategory",
    # Player progress models
    "PlayerProgress",
    "ExplorationSession", 
    "RegionUnlock",
    "PlayerStats",
]
