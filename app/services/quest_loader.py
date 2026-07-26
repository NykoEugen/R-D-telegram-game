"""Loads static quest definitions from YAML. Singleton — file read once."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ObjectiveDef:
    id: str
    required_actions: list[str]
    count: int = 1


@dataclass
class QuestDef:
    id: str
    tier: int
    min_level: int
    reward_xp: int
    reward_gold: int
    type: str
    title: dict[str, str]
    questgiver: dict[str, str]
    description: dict[str, str]
    proposal_text: dict[str, str]
    exploration_text: dict[str, str]
    confrontation_text: dict[str, str]
    success_text: dict[str, str]
    fail_text: dict[str, str]
    location: str = "tavern"
    objectives: list[ObjectiveDef] = field(default_factory=list)

    def get(self, field_name: str, locale: str) -> str:
        d = getattr(self, field_name, {})
        return d.get(locale) or d.get("en") or ""


_QUESTS: list[QuestDef] | None = None
_QUESTS_BY_ID: dict[str, QuestDef] | None = None

_YAML_PATH = Path(__file__).parent.parent / "game" / "static_quests.yaml"


def _load() -> list[QuestDef]:
    global _QUESTS, _QUESTS_BY_ID
    if _QUESTS is not None:
        return _QUESTS

    with open(_YAML_PATH, encoding="utf-8") as f:
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
                location=q.get("location", "tavern"),
                objectives=objectives,
            )
        )

    _QUESTS_BY_ID = {q.id: q for q in _QUESTS}
    return _QUESTS


def get_available_quests(player_level: int) -> list[QuestDef]:
    """Quests whose min_level <= player_level, sorted by tier."""
    return sorted(
        [q for q in _load() if q.min_level <= player_level],
        key=lambda q: q.tier,
    )


def get_quest_by_id(quest_id: str) -> QuestDef | None:
    _load()
    return (_QUESTS_BY_ID or {}).get(quest_id)
