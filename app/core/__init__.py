"""
Core module for the Telegram RPG game bot.

This module contains core functionality and utilities used throughout the application.
"""

from .config import settings, Config
from .utils import extract_update_info, format_exception

__all__ = [
    'settings',
    'Config', 
    'extract_update_info',
    'format_exception'
]
