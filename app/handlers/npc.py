"""
NPC dialogue handler — talk to NPCs present at a city/world location.

Entry point: NpcCB(action="open", npc_id=...) button rendered by city.py's
location keyboard. Dialogue lines are picked from app/game/npcs.yaml (with
app/game/npc_barks.yaml as a shared fallback pool for vendor/flavor NPCs),
via app/services/npc_loader.py.
"""

from aiogram import F, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.states import GameStates
from app.handlers.shop import ShopCB
from app.services import npc_loader
from app.services.i18n_service import i18n_service
from app.services.repositories.player_repo import PlayerRepository

router = Router()

_CATEGORY_LABELS: dict[str, dict[str, str]] = {
    "greeting": {"uk": "👋 Привітатись", "en": "👋 Say hello"},
    "rumor": {"uk": "👂 Розпитати про плітки", "en": "👂 Ask for rumors"},
    "farewell": {"uk": "🚪 Попрощатись", "en": "🚪 Say goodbye"},
    "haggle": {"uk": "💰 Поторгуватись", "en": "💰 Haggle"},
    "out_of_stock": {"uk": "📦 Що є в наявності?", "en": "📦 What's in stock?"},
}


def _t(d: dict[str, str], locale: str) -> str:
    return d.get(locale) or d.get("en") or ""


def _category_label(category: str, locale: str) -> str:
    labels = _CATEGORY_LABELS.get(category)
    if labels:
        return _t(labels, locale)
    return category.replace("_", " ").title()


class NpcCB(CallbackData, prefix="npc"):
    action: str  # "open" | "say"
    npc_id: str
    cat: str = "."


def _npc_kb(
    npc_id: str, categories: list[str], locale: str, has_shop: bool = False
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=_category_label(cat, locale),
            callback_data=NpcCB(action="say", npc_id=npc_id, cat=cat).pack(),
        )]
        for cat in categories
        if cat != "greeting"
    ]
    if has_shop:
        shop_label = "🛒 Магазин" if locale == "uk" else "🛒 Shop"
        rows.append([InlineKeyboardButton(
            text=shop_label, callback_data=ShopCB(action="browse", npc_id=npc_id).pack(),
        )])
    back_label = "◀️ Відійти" if locale == "uk" else "◀️ Step away"
    rows.append([InlineKeyboardButton(text=back_label, callback_data="city:return")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _player_level(db_session: AsyncSession, user_id: int) -> int:
    player = await PlayerRepository(db_session).get_player_by_telegram_id(user_id)
    return player.level if player else 1


@router.callback_query(NpcCB.filter(F.action == "open"), GameStates.CITY_EXPLORATION)
async def cb_npc_open(
    callback: CallbackQuery,
    callback_data: NpcCB,
    state: FSMContext,
    db_session: AsyncSession,
):
    await callback.answer()
    user_id = callback.from_user.id
    locale = i18n_service.get_user_language(user_id)
    npc = npc_loader.get_npc(callback_data.npc_id)
    if not npc:
        return

    level = await _player_level(db_session, user_id)
    fsm_data = await state.get_data()
    seen = fsm_data.get("npc_seen", {}).get(npc.id, {}).get("greeting", [])

    text, idx = npc_loader.pick_line(npc.id, "greeting", level, locale, seen)
    if idx >= 0:
        await _remember_seen(state, npc.id, "greeting", idx)

    categories = npc_loader.get_dialogue_categories(npc.id, level)
    name = npc.get_name(locale)
    body = text or ("..." if locale != "uk" else "...")

    await callback.message.edit_text(
        f"🗣 <b>{name}</b>\n\n{body}",
        reply_markup=_npc_kb(npc.id, categories, locale, has_shop=bool(npc.vendor_stock)),
        parse_mode="HTML",
    )


@router.callback_query(NpcCB.filter(F.action == "say"), GameStates.CITY_EXPLORATION)
async def cb_npc_say(
    callback: CallbackQuery,
    callback_data: NpcCB,
    state: FSMContext,
    db_session: AsyncSession,
):
    await callback.answer()
    user_id = callback.from_user.id
    locale = i18n_service.get_user_language(user_id)
    npc = npc_loader.get_npc(callback_data.npc_id)
    if not npc:
        return

    level = await _player_level(db_session, user_id)
    fsm_data = await state.get_data()
    seen = fsm_data.get("npc_seen", {}).get(npc.id, {}).get(callback_data.cat, [])

    text, idx = npc_loader.pick_line(npc.id, callback_data.cat, level, locale, seen)
    if idx >= 0:
        await _remember_seen(state, npc.id, callback_data.cat, idx)

    categories = npc_loader.get_dialogue_categories(npc.id, level)
    name = npc.get_name(locale)
    body = text or ("..." if locale != "uk" else "...")

    await callback.message.edit_text(
        f"🗣 <b>{name}</b>\n\n{body}",
        reply_markup=_npc_kb(npc.id, categories, locale, has_shop=bool(npc.vendor_stock)),
        parse_mode="HTML",
    )


async def _remember_seen(
    state: FSMContext, npc_id: str, category: str, idx: int
) -> None:
    fsm_data = await state.get_data()
    npc_seen = fsm_data.get("npc_seen", {})
    per_npc = npc_seen.get(npc_id, {})
    seen_list = per_npc.get(category, [])
    if idx not in seen_list:
        seen_list = seen_list + [idx]
    per_npc[category] = seen_list
    npc_seen[npc_id] = per_npc
    await state.update_data(npc_seen=npc_seen)
