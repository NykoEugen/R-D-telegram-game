"""
Game scenes and scenarios for the Telegram RPG game bot.

This module contains scene definitions and context for different game situations.
"""

from enum import StrEnum
from dataclasses import dataclass
from typing import List, Optional


class SceneType(StrEnum):
    """Types of game scenes."""
    QUEST = "quest"
    COMBAT = "combat"
    EXPLORATION = "exploration"
    DIALOGUE = "dialogue"
    INVENTORY = "inventory"


@dataclass
class SceneContext:
    """Context information for a game scene."""
    scene_id: str
    scene_type: SceneType
    description: str
    context_hint: Optional[str] = None
    user_id: Optional[int] = None
    message_id: Optional[int] = None


def create_quest_scene(user_id: int, message_id: int, quest_description: str) -> SceneContext:
    """Create a quest scene context."""
    scene_id = f"quest-{user_id}-{message_id}"
    return SceneContext(
        scene_id=scene_id,
        scene_type=SceneType.QUEST,
        description=quest_description,
        context_hint=quest_description,
        user_id=user_id,
        message_id=message_id
    )


def create_demo_scene(scene_id: str, description: str) -> SceneContext:
    """Create a demo scene context."""
    return SceneContext(
        scene_id=scene_id,
        scene_type=SceneType.COMBAT,
        description=description,
        context_hint=description
    )
