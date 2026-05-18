"""
City exploration handler — free-roam intro for new players.

Flow: hero created → city map → visit locations → tavern+guild unlocks quests.
Visited locations are tracked in FSM state as a list.
"""

from pathlib import Path
from typing import Optional

import yaml
from aiogram import Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.states import GameStates
from app.services.i18n_service import i18n_service
from app.services.logging_service import get_logger

router = Router()
logger = get_logger(__name__)

_CITY_DATA: Optional[dict] = None
_YAML_PATH = Path(__file__).parent.parent / "game" / "city_intro.yaml"

UNLOCK_LOCATIONS = {"tavern", "guild"}


def _load() -> dict:
    global _CITY_DATA
    if _CITY_DATA is not None:
        return _CITY_DATA
    with open(_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _CITY_DATA = data.get("city", {})
    return _CITY_DATA


def _t(data: dict, locale: str) -> str:
    return data.get(locale) or data.get("en") or ""


class CityCB(CallbackData, prefix="city"):
    action: str
    sub: str = ""


# ── keyboards ─────────────────────────────────────────────────────────────────

_LOCATION_ICONS = {
    "tavern": "🍺",
    "guild": "⚔️",
    "market": "🏪",
    "street": "🌆",
}


def _city_map_kb(user_id: int, visited: list[str], quests_unlocked: bool) -> InlineKeyboardMarkup:
    locale = i18n_service.get_user_language(user_id)
    city = _load()
    rows = []
    for loc_id, icon in _LOCATION_ICONS.items():
        loc = city.get("locations", {}).get(loc_id, {})
        name = _t(loc.get("name", {}), locale)
        check = " ✅" if loc_id in visited else ""
        rows.append([InlineKeyboardButton(
            text=f"{icon} {name}{check}",
            callback_data=CityCB(action="loc", sub=loc_id).pack(),
        )])
    if quests_unlocked:
        label = "⚔️ Квести" if locale == "uk" else "⚔️ Quests"
        rows.append([InlineKeyboardButton(text=label, callback_data="show_quests")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _location_kb(user_id: int, loc_id: str, visited: list[str], quests_unlocked: bool) -> InlineKeyboardMarkup:
    locale = i18n_service.get_user_language(user_id)
    city = _load()
    loc = city.get("locations", {}).get(loc_id, {})
    rows = []
    for act_id, act in loc.get("actions", {}).items():
        label = _t(act.get("label", {}), locale)
        rows.append([InlineKeyboardButton(
            text=label,
            callback_data=CityCB(action="act", sub=f"{loc_id}_{act_id}").pack(),
        )])
    back_label = "◀️ В місто" if locale == "uk" else "◀️ Back to city"
    rows.append([InlineKeyboardButton(
        text=back_label,
        callback_data=CityCB(action="main").pack(),
    )])
    if quests_unlocked:
        quest_label = "⚔️ Квести" if locale == "uk" else "⚔️ Quests"
        rows.append([InlineKeyboardButton(text=quest_label, callback_data="show_quests")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── helpers ───────────────────────────────────────────────────────────────────

def _quests_unlocked(visited: list[str]) -> bool:
    return UNLOCK_LOCATIONS.issubset(set(visited))


async def _get_state(state: FSMContext) -> tuple[list[str], bool]:
    data = await state.get_data()
    visited = data.get("city_visited", [])
    return visited, _quests_unlocked(visited)


def _city_map_text(locale: str, visited: list[str]) -> str:
    city = _load()
    city_name = _t(city.get("name", {}), locale)
    if not visited:
        intro = _t(city.get("intro", {}), locale)
    else:
        if locale == "uk":
            intro = f"Ти стоїш посеред {city_name}. Куди далі?"
        else:
            intro = f"You stand in the middle of {city_name}. Where to next?"
    return f"🏙 <b>{city_name}</b>\n\n{intro}"


# ── public entry point ────────────────────────────────────────────────────────

async def enter_city(message: Message, state: FSMContext) -> None:
    """Called after hero creation — lands player directly in the tavern."""
    await state.set_state(GameStates.CITY_EXPLORATION)
    visited = ["tavern"]
    await state.update_data(city_visited=visited)

    locale = i18n_service.get_user_language(message.from_user.id)
    city = _load()
    loc = city.get("locations", {}).get("tavern", {})
    name = _t(loc.get("name", {}), locale)
    description = _t(loc.get("description", {}), locale)
    npc = _t(loc.get("npc", {}), locale)
    city_name = _t(city.get("name", {}), locale)

    arrival = (
        f"Ти щойно прибув до <b>{city_name}</b>."
        if locale == "uk"
        else f"You have just arrived in <b>{city_name}</b>."
    )
    npc_line = f"\n\n<i>Тут: {npc}</i>" if locale == "uk" else f"\n\n<i>Here: {npc}</i>"
    text = f"{arrival}\n\n🏛 <b>{name}</b>\n\n{description}{npc_line}"

    await message.answer(
        text,
        reply_markup=_location_kb(message.from_user.id, "tavern", visited, False),
        parse_mode="HTML",
    )


# ── handlers ──────────────────────────────────────────────────────────────────

@router.callback_query(CityCB.filter(F.action == "main"), GameStates.CITY_EXPLORATION)
async def cb_city_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    visited, unlocked = await _get_state(state)
    locale = i18n_service.get_user_language(callback.from_user.id)
    await callback.message.edit_text(
        _city_map_text(locale, visited),
        reply_markup=_city_map_kb(callback.from_user.id, visited, unlocked),
        parse_mode="HTML",
    )


@router.callback_query(CityCB.filter(F.action == "loc"), GameStates.CITY_EXPLORATION)
async def cb_city_location(callback: CallbackQuery, callback_data: CityCB, state: FSMContext):
    await callback.answer()
    loc_id = callback_data.sub
    locale = i18n_service.get_user_language(callback.from_user.id)
    city = _load()
    loc = city.get("locations", {}).get(loc_id)
    if not loc:
        return

    visited, was_unlocked = await _get_state(state)
    just_unlocked = False
    if loc_id not in visited:
        visited = visited + [loc_id]
        await state.update_data(city_visited=visited)
        unlocked = _quests_unlocked(visited)
        just_unlocked = not was_unlocked and unlocked
    else:
        unlocked = was_unlocked

    name = _t(loc.get("name", {}), locale)
    description = _t(loc.get("description", {}), locale)
    npc = _t(loc.get("npc", {}), locale)
    npc_line = f"\n\n<i>Тут: {npc}</i>" if locale == "uk" else f"\n\n<i>Here: {npc}</i>"

    text = f"🏛 <b>{name}</b>\n\n{description}{npc_line if npc else ''}"

    unlock_notice = ""
    if just_unlocked:
        unlock_notice = "\n\n🔓 <b>Квести розблоковано!</b>" if locale == "uk" else "\n\n🔓 <b>Quests unlocked!</b>"
        city_data = _load()
        unlock_text = _t(city_data.get("intro_quests_unlocked", {}), locale)
        if unlock_text:
            unlock_notice += f"\n{unlock_text}"

    await callback.message.edit_text(
        text + unlock_notice,
        reply_markup=_location_kb(callback.from_user.id, loc_id, visited, unlocked),
        parse_mode="HTML",
    )


@router.callback_query(CityCB.filter(F.action == "act"), GameStates.CITY_EXPLORATION)
async def cb_city_action(callback: CallbackQuery, callback_data: CityCB, state: FSMContext):
    await callback.answer()
    parts = callback_data.sub.split("_", 1)
    if len(parts) != 2:
        return
    loc_id, act_id = parts
    locale = i18n_service.get_user_language(callback.from_user.id)
    city = _load()
    loc = city.get("locations", {}).get(loc_id, {})
    act = loc.get("actions", {}).get(act_id, {})

    visited, unlocked = await _get_state(state)
    loc_name = _t(loc.get("name", {}), locale)
    act_text = _t(act.get("text", {}), locale)

    text = f"🏛 <b>{loc_name}</b>\n\n{act_text}"
    await callback.message.edit_text(
        text,
        reply_markup=_location_kb(callback.from_user.id, loc_id, visited, unlocked),
        parse_mode="HTML",
    )
