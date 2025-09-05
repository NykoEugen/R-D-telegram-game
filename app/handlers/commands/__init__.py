"""
Command handlers module for the Telegram RPG game bot.

This module contains handlers for bot commands.
"""

from .start import router as start_router
from .game import router as game_router
from .language import router as language_router
from .character import router as character_router

__all__ = [
    'start_router',
    'game_router', 
    'language_router',
    'character_router'
]
