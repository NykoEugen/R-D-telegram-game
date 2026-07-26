"""
Game module for the Telegram RPG game bot.

This module contains game logic, actions, and scene management.
"""

from .actions import ACTION_META, Action, ActionMeta

__all__ = [
    'Action',
    'ActionMeta',
    'ACTION_META',
]
