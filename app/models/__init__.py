"""
SQLAlchemy models for the Telegram RPG game bot.

This module contains all database models used in the application.
Import the Base class and any models you need from this module.
"""

from app.core.db import Base

# Import all models here when they are created
from .user import User
# from .game_session import GameSession
# from .character import Character
# from .inventory import Inventory
# from .quest import Quest

__all__ = [
    "Base",
    "User",
    # "GameSession", 
    # "Character",
    # "Inventory",
    # "Quest",
]
