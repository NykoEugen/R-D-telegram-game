"""Buy/sell logic for vendor NPCs — spends/grants Player.coins via ItemRepository."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player
from app.services import npc_loader
from app.services.repositories.item_repo import ItemRepository


@dataclass
class ShopResult:
    ok: bool
    message: str
    gold_delta: int = 0


class ShopService:
    def __init__(self, db_session: AsyncSession):
        self.item_repo = ItemRepository(db_session)

    async def buy(self, player: Player, npc_id: str, item_id: str) -> ShopResult:
        npc = npc_loader.get_npc(npc_id)
        stock_entry = next(
            (s for s in (npc.vendor_stock if npc else []) if s.item_id == item_id), None
        )
        if not stock_entry:
            return ShopResult(False, "not_in_stock")
        if player.coins < stock_entry.price:
            return ShopResult(False, "not_enough_coins")

        player.coins -= stock_entry.price
        await self.item_repo.add_item_to_inventory(
            player.id, item_id, 1, acquired_from=f"shop:{npc_id}"
        )
        return ShopResult(True, "bought", gold_delta=-stock_entry.price)

    async def sell(self, player: Player, item_id: str, quantity: int = 1) -> ShopResult:
        item = await self.item_repo.get_item_by_item_id(item_id)
        if not item or not item.is_tradeable:
            return ShopResult(False, "not_tradeable")
        if not await self.item_repo.has_item(player.id, item_id, quantity):
            return ShopResult(False, "not_enough_items")

        removed = await self.item_repo.remove_item_from_inventory(
            player.id, item_id, quantity
        )
        if not removed:
            return ShopResult(False, "not_enough_items")

        gold = item.sell_value * quantity
        player.coins += gold
        return ShopResult(True, "sold", gold_delta=gold)
