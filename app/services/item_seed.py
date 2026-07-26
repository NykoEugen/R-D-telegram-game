"""Idempotently syncs the Item catalog (app/game/items.yaml) into the DB.

Called once at bot startup. Only creates missing items — never overwrites
existing rows, so already-granted inventory items are unaffected by catalog
edits.
"""

from pathlib import Path

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.items import ItemRarity, ItemType
from app.services.logging_service import get_logger
from app.services.repositories.item_repo import ItemRepository

logger = get_logger(__name__)

_YAML_PATH = Path(__file__).parent.parent / "game" / "items.yaml"


async def sync_items_from_yaml(session: AsyncSession) -> int:
    """Create any catalog items missing from the DB. Returns count created."""
    with open(_YAML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    repo = ItemRepository(session)
    created = 0
    for entry in data.get("items", []):
        item_id = entry["item_id"]
        if await repo.get_item_by_item_id(item_id):
            continue

        await repo.create_item(
            item_id=item_id,
            name=entry["name"],
            item_type=ItemType(entry["item_type"]),
            rarity=ItemRarity(entry.get("rarity", "common")),
            description=entry.get("description"),
            base_value=entry.get("base_value", 0),
            sell_value=entry.get("sell_value", 0),
            is_consumable=entry.get("is_consumable", False),
            effects=entry.get("effects"),
            health_bonus=entry.get("health_bonus", 0),
            mana_bonus=entry.get("mana_bonus", 0),
            strength_bonus=entry.get("strength_bonus", 0),
            agility_bonus=entry.get("agility_bonus", 0),
            intelligence_bonus=entry.get("intelligence_bonus", 0),
            vitality_bonus=entry.get("vitality_bonus", 0),
        )
        created += 1

    if created:
        await session.commit()
        logger.info("Item catalog synced", items_created=created)
    return created
