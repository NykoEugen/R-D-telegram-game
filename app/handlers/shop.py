"""
Shop handler — buy from a vendor NPC's stock, sell from inventory.

Entry point: a "🛒 Shop" button shown by npc.py for role=vendor NPCs.
"""

from aiogram import F, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import npc_loader
from app.services.i18n_service import i18n_service
from app.services.repositories.item_repo import ItemRepository
from app.services.repositories.player_repo import PlayerRepository
from app.services.shop_service import ShopService

router = Router()


class ShopCB(CallbackData, prefix="shop"):
    action: str  # "browse" | "buy" | "sell_list" | "sell"
    npc_id: str
    item_id: str = "."


async def _render_browse(
    callback: CallbackQuery, npc_id: str, db_session: AsyncSession
) -> None:
    user_id = callback.from_user.id
    locale = i18n_service.get_user_language(user_id)
    npc = npc_loader.get_npc(npc_id)
    player = await PlayerRepository(db_session).get_player_by_telegram_id(user_id)
    if not npc or not player:
        return

    item_repo = ItemRepository(db_session)
    rows = []
    for entry in npc.vendor_stock:
        item = await item_repo.get_item_by_item_id(entry.item_id)
        name = item.name if item else entry.item_id
        cb = ShopCB(action="buy", npc_id=npc_id, item_id=entry.item_id)
        rows.append([InlineKeyboardButton(
            text=f"{name} — {entry.price}💰", callback_data=cb.pack(),
        )])

    sell_label = (
        "🎒 Продати з інвентаря" if locale == "uk" else "🎒 Sell from inventory"
    )
    rows.append([InlineKeyboardButton(
        text=sell_label, callback_data=ShopCB(action="sell_list", npc_id=npc_id).pack(),
    )])
    back_label = "◀️ Відійти" if locale == "uk" else "◀️ Step away"
    rows.append([InlineKeyboardButton(text=back_label, callback_data="city:return")])

    name = npc.get_name(locale)
    header = f"🛒 <b>{name}</b>\n\n" + (
        f"У тебе {player.coins}💰" if locale == "uk" else f"You have {player.coins}💰"
    )
    await callback.message.edit_text(
        header,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


async def _render_sell_list(
    callback: CallbackQuery, npc_id: str, db_session: AsyncSession
) -> None:
    user_id = callback.from_user.id
    locale = i18n_service.get_user_language(user_id)
    player = await PlayerRepository(db_session).get_player_by_telegram_id(user_id)
    if not player:
        return

    item_repo = ItemRepository(db_session)
    inventory = await item_repo.get_player_inventory(player.id)
    tradeable = [
        inv for inv in inventory if inv.item.is_tradeable and not inv.is_equipped
    ]

    rows = []
    for inv in tradeable:
        cb = ShopCB(action="sell", npc_id=npc_id, item_id=inv.item.item_id)
        rows.append([InlineKeyboardButton(
            text=f"{inv.item.name} x{inv.quantity} — {inv.item.sell_value}💰/шт",
            callback_data=cb.pack(),
        )])

    back_label = "◀️ Назад до магазину" if locale == "uk" else "◀️ Back to shop"
    rows.append([InlineKeyboardButton(
        text=back_label, callback_data=ShopCB(action="browse", npc_id=npc_id).pack(),
    )])

    if not tradeable:
        empty = "Продавати нічого." if locale == "uk" else "Nothing to sell."
        header = f"🎒 {empty}"
    else:
        header = "🎒 Що продати?" if locale == "uk" else "🎒 What to sell?"

    await callback.message.edit_text(
        header, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@router.callback_query(ShopCB.filter(F.action == "browse"))
async def cb_shop_browse(
    callback: CallbackQuery, callback_data: ShopCB, db_session: AsyncSession
):
    await callback.answer()
    await _render_browse(callback, callback_data.npc_id, db_session)


@router.callback_query(ShopCB.filter(F.action == "buy"))
async def cb_shop_buy(
    callback: CallbackQuery, callback_data: ShopCB, db_session: AsyncSession
):
    locale = i18n_service.get_user_language(callback.from_user.id)
    player = await PlayerRepository(db_session).get_player_by_telegram_id(
        callback.from_user.id
    )
    if not player:
        await callback.answer()
        return

    result = await ShopService(db_session).buy(
        player, callback_data.npc_id, callback_data.item_id
    )
    if result.ok:
        toast = "Куплено!" if locale == "uk" else "Bought!"
    elif result.message == "not_enough_coins":
        toast = "Недостатньо грошей." if locale == "uk" else "Not enough coins."
    else:
        toast = "Немає в наявності." if locale == "uk" else "Out of stock."
    await callback.answer(toast, show_alert=not result.ok)
    await _render_browse(callback, callback_data.npc_id, db_session)


@router.callback_query(ShopCB.filter(F.action == "sell_list"))
async def cb_shop_sell_list(
    callback: CallbackQuery, callback_data: ShopCB, db_session: AsyncSession
):
    await callback.answer()
    await _render_sell_list(callback, callback_data.npc_id, db_session)


@router.callback_query(ShopCB.filter(F.action == "sell"))
async def cb_shop_sell(
    callback: CallbackQuery, callback_data: ShopCB, db_session: AsyncSession
):
    locale = i18n_service.get_user_language(callback.from_user.id)
    player = await PlayerRepository(db_session).get_player_by_telegram_id(
        callback.from_user.id
    )
    if not player:
        await callback.answer()
        return

    result = await ShopService(db_session).sell(
        player, callback_data.item_id, quantity=1
    )
    if result.ok:
        toast = (
            f"Продано за {result.gold_delta}💰"
            if locale == "uk"
            else f"Sold for {result.gold_delta}💰"
        )
    else:
        toast = "Не вдалось продати." if locale == "uk" else "Could not sell."
    await callback.answer(toast, show_alert=not result.ok)
    await _render_sell_list(callback, callback_data.npc_id, db_session)
