"""Loads static quest definitions from YAML. Singleton — file read once."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class ObjectiveDef:
    id: str
    required_actions: List[str]
    count: int = 1


@dataclass
class QuestDef:
    id: str
    tier: int
    min_level: int
    reward_xp: int
    reward_gold: int
    type: str
    title: Dict[str, str]
    questgiver: Dict[str, str]
    description: Dict[str, str]
    proposal_text: Dict[str, str]
    exploration_text: Dict[str, str]
    confrontation_text: Dict[str, str]
    success_text: Dict[str, str]
    fail_text: Dict[str, str]
    objectives: List[ObjectiveDef] = field(default_factory=list)

    def get(self, field_name: str, locale: str) -> str:
        d = getattr(self, field_name, {})
        return d.get(locale) or d.get("en") or ""


_QUESTS: Optional[List[QuestDef]] = None
_QUESTS_BY_ID: Optional[Dict[str, QuestDef]] = None

_YAML_PATH = Path(__file__).parent.parent / "game" / "static_quests.yaml"


def _load() -> List[QuestDef]:
    global _QUESTS, _QUESTS_BY_ID
    if _QUESTS is not None:
        return _QUESTS

    with open(_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _QUESTS = []
    for q in data.get("quests", []):
        objectives = [
            ObjectiveDef(
                id=o["id"],
                required_actions=o.get("required_actions", []),
                count=o.get("count", 1),
            )
            for o in q.get("objectives", [])
        ]
        _QUESTS.append(
            QuestDef(
                id=q["id"],
                tier=q["tier"],
                min_level=q["min_level"],
                reward_xp=q["reward_xp"],
                reward_gold=q["reward_gold"],
                type=q["type"],
                title=q["title"],
                questgiver=q["questgiver"],
                description=q["description"],
                proposal_text=q["proposal_text"],
                exploration_text=q["exploration_text"],
                confrontation_text=q["confrontation_text"],
                success_text=q["success_text"],
                fail_text=q["fail_text"],
                objectives=objectives,
            )
        )

    _QUESTS_BY_ID = {q.id: q for q in _QUESTS}
    return _QUESTS


def get_available_quests(player_level: int) -> List[QuestDef]:
    """Quests whose min_level <= player_level, sorted by tier."""
    return sorted(
        [q for q in _load() if q.min_level <= player_level],
        key=lambda q: q.tier,
    )


def get_quest_by_id(quest_id: str) -> Optional[QuestDef]:
    _load()
    return (_QUESTS_BY_ID or {}).get(quest_id)
