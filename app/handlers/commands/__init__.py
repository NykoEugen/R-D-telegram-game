"""
Command handlers module for the Telegram RPG game bot.

This module contains handlers for bot commands.
"""

from .character import router as character_router
from .combat import router as combat_router
from .language import router as language_router
from .start import router as start_router

__all__ = [
    'start_router',
    'language_router',
    'character_router',
    'combat_router'
]
