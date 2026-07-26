"""Loads quest definitions from YAML (app/game/quests/*.yaml). Singleton — read once."""

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
    quest_type: str = "main"  # main | side | daily | weekly
    requires: list[str] = field(default_factory=list)  # prerequisite quest ids
    npc_id: str | None = None  # questgiver NPC, links into app/services/npc_loader.py
    reset_hours: int | None = None  # for daily/weekly: hours until repeatable again
    objectives: list[ObjectiveDef] = field(default_factory=list)

    def get(self, field_name: str, locale: str) -> str:
        d = getattr(self, field_name, {})
        return d.get(locale) or d.get("en") or ""


_QUESTS: list[QuestDef] | None = None
_QUESTS_BY_ID: dict[str, QuestDef] | None = None

_QUESTS_DIR = Path(__file__).parent.parent / "game" / "quests"


def _load() -> list[QuestDef]:
    global _QUESTS, _QUESTS_BY_ID
    if _QUESTS is not None:
        return _QUESTS

    _QUESTS = []
    for yaml_path in sorted(_QUESTS_DIR.glob("*.yaml")):
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

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
                    quest_type=q.get("quest_type", "main"),
                    requires=q.get("requires", []),
                    npc_id=q.get("npc_id"),
                    reset_hours=q.get("reset_hours"),
                    objectives=objectives,
                )
            )

    _QUESTS_BY_ID = {q.id: q for q in _QUESTS}
    return _QUESTS


def get_eligible_quests(player_level: int, completed_ids: set[str]) -> list[QuestDef]:
    """Quests within level range whose `requires` graph is satisfied.

    Non-repeatable (main/side) quests already in `completed_ids` are excluded.
    Daily/weekly quests are NOT excluded here — the caller checks their
    cooldown separately via QuestRepository.is_available_again (DB-backed).
    """
    result = []
    for q in _load():
        if q.min_level > player_level:
            continue
        if q.requires and not set(q.requires).issubset(completed_ids):
            continue
        if q.quest_type not in ("daily", "weekly") and q.id in completed_ids:
            continue
        result.append(q)
    return sorted(result, key=lambda q: q.tier)


def get_quest_by_id(quest_id: str) -> QuestDef | None:
    _load()
    return (_QUESTS_BY_ID or {}).get(quest_id)
