"""
AI services module for the Telegram RPG game bot.

This module contains AI-powered services for content generation and label creation.
"""

from .generation_service import AIGenerationService
from .label_generator import ActionLabelGenerator
from .action_service import AIActionService, ai_action_service

# Backward compatibility
OpenAIService = AIGenerationService

__all__ = [
    'AIGenerationService',
    'ActionLabelGenerator',
    'AIActionService',
    'ai_action_service',
    'OpenAIService'  # For backward compatibility
]
