"""
Repository layer for the Telegram RPG game bot.

This module provides data access layer abstractions for all game entities.
"""

from .player_repo import PlayerRepository
from .item_repo import ItemRepository
from .quest_repo import QuestRepository
from .session_repo import SessionRepository

__all__ = [
    "PlayerRepository",
    "ItemRepository", 
    "QuestRepository",
    "SessionRepository",
]
