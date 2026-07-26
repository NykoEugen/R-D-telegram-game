"""Loads NPC definitions + shared vendor/flavor bark pool from YAML. Singleton."""

import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml

Line = dict[str, str]


@dataclass
class StageDialogues:
    min_level: int
    dialogues: dict[str, list[Line]]
    max_level: int | None = None

    def matches(self, level: int) -> bool:
        if level < self.min_level:
            return False
        return self.max_level is None or level <= self.max_level


@dataclass
class VendorStockEntry:
    item_id: str
    price: int


@dataclass
class NPCDef:
    id: str
    name: dict[str, str]
    location: str
    role: str  # questgiver | vendor | flavor
    quest_links: list[str] = field(default_factory=list)
    dialogues: dict[str, list[Line]] = field(default_factory=dict)
    stage_dialogues: list[StageDialogues] = field(default_factory=list)
    vendor_stock: list[VendorStockEntry] = field(default_factory=list)

    def get_name(self, locale: str) -> str:
        return self.name.get(locale) or self.name.get("en") or self.id

    def lines_for(self, category: str, player_level: int) -> list[Line]:
        """Lines for a category, honoring stage overrides (highest matching
        min_level wins, merged over the base list)."""
        lines = list(self.dialogues.get(category, []))
        applicable = [sd for sd in self.stage_dialogues if sd.matches(player_level)]
        for sd in sorted(applicable, key=lambda s: s.min_level):
            override = sd.dialogues.get(category)
            if override:
                lines = list(override)
        return lines


_NPCS: list[NPCDef] | None = None
_NPCS_BY_ID: dict[str, NPCDef] | None = None
_NPCS_BY_LOCATION: dict[str, list[NPCDef]] | None = None
_BARKS: dict[str, dict[str, list[Line]]] | None = None

_NPCS_YAML_PATH = Path(__file__).parent.parent / "game" / "npcs.yaml"
_BARKS_YAML_PATH = Path(__file__).parent.parent / "game" / "npc_barks.yaml"


def _parse_stage_dialogues(raw: list[dict[str, object]]) -> list[StageDialogues]:
    return [
        StageDialogues(
            min_level=sd["min_level"],
            max_level=sd.get("max_level"),
            dialogues=sd.get("dialogues", {}),
        )
        for sd in raw
    ]


def _load() -> list[NPCDef]:
    global _NPCS, _NPCS_BY_ID, _NPCS_BY_LOCATION
    if _NPCS is not None:
        return _NPCS

    with open(_NPCS_YAML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _NPCS = []
    for n in data.get("npcs", []):
        _NPCS.append(
            NPCDef(
                id=n["id"],
                name=n["name"],
                location=n["location"],
                role=n.get("role", "flavor"),
                quest_links=n.get("quest_links", []),
                dialogues=n.get("dialogues", {}) or {},
                stage_dialogues=_parse_stage_dialogues(n.get("stage_dialogues", [])),
                vendor_stock=[
                    VendorStockEntry(item_id=s["item_id"], price=s["price"])
                    for s in n.get("vendor_stock", [])
                ],
            )
        )

    _NPCS_BY_ID = {n.id: n for n in _NPCS}
    _NPCS_BY_LOCATION = {}
    for n in _NPCS:
        _NPCS_BY_LOCATION.setdefault(n.location, []).append(n)

    return _NPCS


def _load_barks() -> dict[str, dict[str, list[Line]]]:
    global _BARKS
    if _BARKS is not None:
        return _BARKS
    with open(_BARKS_YAML_PATH, encoding="utf-8") as f:
        _BARKS = yaml.safe_load(f) or {}
    return _BARKS


def get_npc(npc_id: str) -> NPCDef | None:
    _load()
    return (_NPCS_BY_ID or {}).get(npc_id)


def get_npcs_by_location(location_id: str) -> list[NPCDef]:
    _load()
    return (_NPCS_BY_LOCATION or {}).get(location_id, [])


def get_dialogue_categories(npc_id: str, player_level: int) -> list[str]:
    """Categories with at least one line available (own content or bark fallback)."""
    npc = get_npc(npc_id)
    if not npc:
        return []
    categories = set(npc.dialogues.keys())
    for sd in npc.stage_dialogues:
        categories.update(sd.dialogues.keys())
    barks = _load_barks().get(npc.role, {})
    categories.update(barks.keys())
    return sorted(categories)


def pick_line(
    npc_id: str,
    category: str,
    player_level: int,
    locale: str,
    seen: list[int] | None = None,
) -> tuple[str, int]:
    """Pick a line for (npc, category), cycling through variants before repeating.

    Returns (text, index_used) — caller persists `index_used` in `seen` (FSM)
    so the next call can avoid repeating until the pool is exhausted.
    """
    npc = get_npc(npc_id)
    seen = seen or []

    lines: list[Line] = []
    if npc:
        lines = npc.lines_for(category, player_level)
    if not lines and npc:
        lines = _load_barks().get(npc.role, {}).get(category, [])

    if not lines:
        return "", -1

    unseen_indices = [i for i in range(len(lines)) if i not in seen]
    idx = (
        random.choice(unseen_indices)
        if unseen_indices
        else random.randrange(len(lines))
    )

    line = lines[idx]
    text = line.get(locale) or line.get("en") or ""
    return text, idx
