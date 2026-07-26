"""
Travel handler — moves player step-by-step along world graph path to quest location.

Flow: quest accepted → travel_start() → QUEST_TRAVEL → steps → quest starts.
Each step shows edge text (from→to) + arrival description + Continue button.
"""

from aiogram import F, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.states import GameStates
from app.game.world_graph import (
    get_edge_text,
    get_node_description,
    get_node_name,
    shortest_path,
)
from app.services.i18n_service import i18n_service
from app.services.logging_service import get_logger

router = Router()
logger = get_logger(__name__)


class TravelCB(CallbackData, prefix="trv"):
    action: str  # "next" | "arrive"


def _continue_kb(locale: str, is_last: bool) -> InlineKeyboardMarkup:
    if is_last:
        label = "⚔️ Почати завдання" if locale == "uk" else "⚔️ Start quest"
        cb = TravelCB(action="arrive").pack()
    else:
        label = "▶️ Продовжити" if locale == "uk" else "▶️ Continue"
        cb = TravelCB(action="next").pack()
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=cb)]])


def _build_step_text(prev: str, current: str, locale: str) -> str:
    edge = get_edge_text(prev, current, locale)
    arrival = get_node_description(current, locale)
    name = get_node_name(current, locale)
    parts = []
    if edge:
        parts.append(edge)
    parts.append(f"\n📍 <b>{name}</b>\n{arrival}")
    return "\n".join(parts)


async def travel_start(
    message: Message,
    state: FSMContext,
    quest_id: str,
    quest_location: str,
    start_quest_fn,
    db_session: AsyncSession,
) -> None:
    """
    Called from quest_runner after player accepts a quest.
    If already at quest location — starts quest immediately.
    Otherwise enters QUEST_TRAVEL state.
    """

    fsm = await state.get_data()
    # Read current location from FSM (set by city/travel) or fall back to player flags
    current_location = fsm.get("current_location", "tavern")

    path = shortest_path(current_location, quest_location)

    if not path:
        # Already at destination
        await start_quest_fn(message, state, db_session, edit=False)
        return

    locale = i18n_service.get_user_language(message.from_user.id)
    await state.set_state(GameStates.QUEST_TRAVEL)
    await state.update_data(
        travel_path=path,
        travel_step=0,
        travel_from=current_location,
        travel_quest_id=quest_id,
    )

    step_text = _build_step_text(current_location, path[0], locale)
    is_last = len(path) == 1
    await message.answer(step_text, reply_markup=_continue_kb(locale, is_last), parse_mode="HTML")


@router.callback_query(TravelCB.filter(F.action == "next"), GameStates.QUEST_TRAVEL)
async def cb_travel_next(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    locale = i18n_service.get_user_language(callback.from_user.id)

    fsm = await state.get_data()
    path: list = fsm["travel_path"]
    step: int = fsm["travel_step"]
    prev = path[step - 1] if step > 0 else fsm["travel_from"]

    step += 1
    await state.update_data(travel_step=step)

    current = path[step]
    is_last = step == len(path) - 1
    step_text = _build_step_text(prev, current, locale)
    await callback.message.edit_text(step_text, reply_markup=_continue_kb(locale, is_last), parse_mode="HTML")


@router.callback_query(TravelCB.filter(F.action == "arrive"), GameStates.QUEST_TRAVEL)
async def cb_travel_arrive(
    callback: CallbackQuery, state: FSMContext, db_session: AsyncSession
):
    """Last travel step — update player location and start the quest."""
    await callback.answer()

    fsm = await state.get_data()
    path: list = fsm["travel_path"]
    quest_location = path[-1]

    # Persist arrived location so future travel uses correct origin
    await state.update_data(current_location=quest_location)

    # Delegate to quest runner
    from app.handlers.quest_runner import _start_quest_phase
    await _start_quest_phase(callback.message, state, db_session, edit=True)
