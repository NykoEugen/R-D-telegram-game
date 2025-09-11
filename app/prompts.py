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
    },
    "scene": {
        "system": (
            "You are a master storyteller creating dynamic fantasy scenes for a medieval RPG game. "
            "Create immersive 3-5 sentence descriptions that set the scene and atmosphere. "
            "Include environmental details, potential dangers, and opportunities for the player. "
            "Make each scene feel unique and engaging."
        ),
        "user": (
            "Generate a fantasy scene description for a medieval RPG adventure. "
            "The scene should be 3-5 sentences long and include: "
            "1. Environmental setting and atmosphere "
            "2. Potential dangers or challenges "
            "3. Opportunities or interesting elements "
            "4. A sense of mystery or adventure "
            "Make it immersive and engaging for the player."
        )
    },
    "choices": {
        "system": (
            "You are creating choice options for a fantasy RPG game. "
            "Generate exactly 3 diverse and interesting choice options that fit the scene context. "
            "Each choice should be 2-4 words maximum and represent different approaches: "
            "aggressive, cautious, diplomatic, investigative, or tactical. "
            "Make choices feel natural and exciting for the player."
        ),
        "user": (
            "Based on this fantasy scene, generate exactly 3 choice options for the player. "
            "Each choice should be 2-4 words maximum and represent different approaches. "
            "Make them diverse and interesting. "
            "Scene: {scene_description}"
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
        },
        "scene": {
            "system": (
                "Ви майстер оповідач, який створює динамічні фентезійні сцени для середньовічної RPG гри. "
                "Створюйте іммерсивні описи на 3-5 речень, які задають сцену та атмосферу. "
                "Включіть деталі навколишнього середовища, потенційні небезпеки та можливості для гравця. "
                "Зробіть кожну сцену унікальною та захоплюючою."
            ),
            "user": (
                "Створіть опис фентезійної сцени для середньовічної RPG пригоди. "
                "Сцена має бути 3-5 речень і включати: "
                "1. Навколишнє середовище та атмосферу "
                "2. Потенційні небезпеки або виклики "
                "3. Можливості або цікаві елементи "
                "4. Відчуття таємниці або пригоди "
                "Зробіть її іммерсивною та захоплюючою для гравця."
            )
        },
        "choices": {
            "system": (
                "Ви створюєте варіанти вибору для фентезійної RPG гри. "
                "Створіть рівно 3 різноманітні та цікаві варіанти вибору, які підходять до контексту сцени. "
                "Кожен вибір має бути максимум 2-4 слова і представляти різні підходи: "
                "агресивний, обережний, дипломатичний, розвідувальний або тактичний. "
                "Зробіть вибори природними та захоплюючими для гравця."
            ),
            "user": (
                "На основі цієї фентезійної сцени створіть рівно 3 варіанти вибору для гравця. "
                "Кожен вибір має бути максимум 2-4 слова і представляти різні підходи. "
                "Зробіть їх різноманітними та цікавими. "
                "Сцена: {scene_description}"
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
    },
    "scene": {
        "max_tokens": 200,
        "temperature": 0.8
    },
    "choices": {
        "max_tokens": 100,
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
