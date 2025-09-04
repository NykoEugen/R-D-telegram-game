"""
OpenAI prompts configuration for the Fantasy RPG Adventure bot.

This module contains all the prompts used for generating game content via OpenAI API.
The prompts are organized by language and content type for easy localization.
"""

from typing import Dict, Any

# Default language (English) prompts
DEFAULT_PROMPTS = {
    "quest": {
        "system": (
            "You are a master storyteller creating epic fantasy quests in a medieval D&D style world. "
            "Keep descriptions concise (2-3 sentences) and engaging."
        ),
        "user": (
            "Generate a short, exciting fantasy quest description for a medieval RPG game. "
            "Include a quest objective and a hint of danger or reward."
        )
    },
    "world": {
        "system": (
            "You are describing a rich medieval fantasy world similar to Dungeons & Dragons. "
            "Keep descriptions vivid but concise (2-3 sentences)."
        ),
        "user": (
            "Describe a medieval fantasy world with magic, dragons, and epic adventures. "
            "Make it sound exciting and immersive."
        )
    }
}

# Localized prompts for different languages
LOCALIZED_PROMPTS: Dict[str, Dict[str, Dict[str, str]]] = {
    "en": DEFAULT_PROMPTS,
    "uk": {
        "quest": {
            "system": (
                "Ви майстер оповідач, який створює епічні фентезійні квести у середньовічному світі у стилі D&D. "
                "Тримайте описи лаконічними (2-3 речення) та захоплюючими."
            ),
            "user": (
                "Створіть короткий, захоплюючий опис фентезійного квесту для середньовічної RPG гри. "
                "Включіть ціль квесту та натяк на небезпеку або винагороду."
            )
        },
        "world": {
            "system": (
                "Ви описуєте багатий середньовічний фентезійний світ, схожий на Dungeons & Dragons. "
                "Тримайте описи яскравими, але лаконічними (2-3 речення)."
            ),
            "user": (
                "Опишіть середньовічний фентезійний світ з магією, драконами та епічними пригодами. "
                "Зробіть його захоплюючим та іммерсивним."
            )
        }
    }
}

# Configuration for different prompt types
PROMPT_CONFIG = {
    "quest": {
        "max_tokens": 150,
        "temperature": 0.8
    },
    "world": {
        "max_tokens": 120,
        "temperature": 0.7
    }
}


def get_prompts(language: str = "en", prompt_type: str = "quest") -> Dict[str, str]:
    """
    Get localized prompts for a specific language and prompt type.
    
    Args:
        language: Language code (e.g., 'en', 'uk')
        prompt_type: Type of prompt ('quest' or 'world')
    
    Returns:
        Dictionary containing 'system' and 'user' prompts
    
    Raises:
        KeyError: If language or prompt_type is not found
    """
    if language not in LOCALIZED_PROMPTS:
        language = "en"  # Fallback to English
    
    if prompt_type not in LOCALIZED_PROMPTS[language]:
        raise KeyError(f"Prompt type '{prompt_type}' not found for language '{language}'")
    
    return LOCALIZED_PROMPTS[language][prompt_type]


def get_prompt_config(prompt_type: str) -> Dict[str, Any]:
    """
    Get configuration for a specific prompt type.
    
    Args:
        prompt_type: Type of prompt ('quest' or 'world')
    
    Returns:
        Dictionary containing configuration (max_tokens, temperature)
    
    Raises:
        KeyError: If prompt_type is not found
    """
    if prompt_type not in PROMPT_CONFIG:
        raise KeyError(f"Prompt type '{prompt_type}' not found")
    
    return PROMPT_CONFIG[prompt_type]


def get_available_languages() -> list:
    """Get list of available languages for prompts."""
    return list(LOCALIZED_PROMPTS.keys())


def get_available_prompt_types() -> list:
    """Get list of available prompt types."""
    return list(PROMPT_CONFIG.keys())
