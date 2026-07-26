"""
SQLAlchemy models for the Telegram RPG game bot.

This module contains all database models used in the application.
Import the Base class and any models you need from this module.
"""

from app.core.db import Base

from .i18n import I18nCategory, I18nString
from .items import InventoryItem, Item, ItemRarity, ItemType
from .lore import QuestProgress, QuestStatus, QuestType
from .player import Player, PlayerStatus
from .telemetry import (
    AIGeneration,
    AIGenerationType,
    GameSession,
    MessageLog,
    MessageType,
    SessionStatus,
)

# Import all models
from .user import User

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
    # Quest progress models
    "QuestProgress",
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
]
