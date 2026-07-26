"""
Quest runner — complete quest lifecycle:
  /quest → select → proposal → phases (exploration → confrontation) → resolution → XP/level-up
"""

import random
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
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
from app.services import npc_loader
from app.services.i18n_service import i18n_service
from app.services.logging_service import get_logger
from app.services.progression_service import ProgressionService
from app.services.quest_loader import QuestDef, get_eligible_quests, get_quest_by_id
from app.services.repositories.item_repo import ItemRepository
from app.services.repositories.player_repo import PlayerRepository
from app.services.repositories.quest_repo import QuestRepository

router = Router()
logger = get_logger(__name__)

# ── Callback data ────────────────────────────────────────────────────────────

class QuestCB(CallbackData, prefix="qst"):
    action: str   # list | select | accept | decline | do
    data: str = "."  # non-empty sentinel; aiogram passes None for "" causing ValidationError


# ── Labels ───────────────────────────────────────────────────────────────────

_ACTION_LABELS = {
    "uk": {
        "attack": "⚔️ Атакувати", "defend": "🛡 Захищатись",
        "investigate": "🔍 Розслідувати", "explore": "🗺 Досліджувати",
        "talk": "💬 Говорити", "negotiate": "🤝 Перемовини",
        "sneak": "🥷 Красти", "loot": "💰 Обшукати",
        "flee": "💨 Відступити", "rest": "💤 Відпочити",
    },
    "en": {
        "attack": "⚔️ Attack", "defend": "🛡 Defend",
        "investigate": "🔍 Investigate", "explore": "🗺 Explore",
        "talk": "💬 Talk", "negotiate": "🤝 Negotiate",
        "sneak": "🥷 Sneak", "loot": "💰 Loot",
        "flee": "💨 Flee", "rest": "💤 Rest",
    },
}


def _t(user_id: int) -> str:
    return i18n_service.get_user_language(user_id)


# ── Keyboards ────────────────────────────────────────────────────────────────

def _quest_list_kb(quests: list[QuestDef], locale: str) -> InlineKeyboardMarkup:
    tier_stars = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐"}
    rows = []
    for q in quests:
        title = q.title.get(locale) or q.title.get("en", q.id)
        rows.append([InlineKeyboardButton(
            text=f"{tier_stars.get(q.tier, '')} {title}",
            callback_data=QuestCB(action="select", data=q.id).pack(),
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _proposal_kb(locale: str) -> InlineKeyboardMarkup:
    if locale == "uk":
        accept, decline = "✅ Прийняти", "❌ Відмовити"
    else:
        accept, decline = "✅ Accept", "❌ Decline"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=accept, callback_data=QuestCB(action="accept").pack())],
        [InlineKeyboardButton(text=decline, callback_data=QuestCB(action="decline").pack())],
    ])


def _talk_label(npc_id: str, locale: str) -> str:
    npc = npc_loader.get_npc(npc_id)
    name = npc.get_name(locale) if npc else npc_id
    return f"💬 Поговорити з {name}" if locale == "uk" else f"💬 Talk to {name}"


def _action_label(action: str, locale: str) -> str:
    if action.startswith("talk-"):
        return _talk_label(action.removeprefix("talk-"), locale)
    labels = _ACTION_LABELS.get(locale, _ACTION_LABELS["en"])
    return labels.get(action, action.title())


def _phase_kb(actions: list[str], locale: str) -> InlineKeyboardMarkup:
    rows = []
    for a in actions:
        rows.append([InlineKeyboardButton(
            text=_action_label(a, locale),
            callback_data=QuestCB(action="do", data=a).pack(),
        )])
    hero_info = "🧙 Герой" if locale == "uk" else "🧙 Hero"
    abandon = "🏳 Покинути" if locale == "uk" else "🏳 Abandon"
    rows.append([
        InlineKeyboardButton(text=hero_info, callback_data=QuestCB(action="hero_info").pack()),
        InlineKeyboardButton(text=abandon, callback_data=QuestCB(action="decline").pack()),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _result_kb(locale: str) -> InlineKeyboardMarkup:
    city = "🏙 В місто" if locale == "uk" else "🏙 Return to city"
    menu = "🏠 Меню" if locale == "uk" else "🏠 Menu"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=city, callback_data="city:return")],
        [InlineKeyboardButton(text=menu, callback_data="menu:main")],
    ])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _safe_edit(message, text: str, reply_markup=None, parse_mode: str = "Markdown") -> None:
    """Edit message, silently ignoring 'message is not modified' — it means first click already succeeded."""
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


def _success_chance(tier: int, player_level: int, quest_min_level: int) -> int:
    """Base 70% for T1, −10% per tier, +5% per level above minimum."""
    return max(35, min(95, 80 - tier * 10 + (player_level - quest_min_level) * 5))


async def _roll_loot(
    db_session: AsyncSession, player_id: int, quest: QuestDef
) -> list[tuple[str, int]]:
    """Roll a quest's loot_table, grant hits to inventory, return (name, qty) for display."""
    if not quest.loot_table:
        return []

    item_repo = ItemRepository(db_session)
    gained: list[tuple[str, int]] = []
    for entry in quest.loot_table:
        if random.random() > entry.chance:
            continue
        qty = random.randint(entry.qty_min, entry.qty_max)
        if qty <= 0:
            continue
        await item_repo.add_item_to_inventory(
            player_id, entry.item_id, qty, acquired_from=f"quest:{quest.id}"
        )
        item = await item_repo.get_item_by_item_id(entry.item_id)
        gained.append((item.name if item else entry.item_id, qty))
    return gained


async def _show_quest_board(target, state: FSMContext, db_session: AsyncSession, edit: bool = False):
    """Shared logic: fetch player, list quests, show board."""
    user_id = target.from_user.id
    locale = _t(user_id)

    player = await PlayerRepository(db_session).get_player_by_telegram_id(user_id)
    if not player:
        msg = "Спочатку створи героя: /create_character" if locale == "uk" else "Create a hero first: /create_character"
        if edit:
            await target.message.edit_text(msg)
        else:
            await target.answer(msg)
        return

    quest_repo = QuestRepository(db_session)
    completed_ids = {
        qp.quest_id for qp in await quest_repo.get_completed_quests(player.id)
    }
    candidates = get_eligible_quests(player.level, completed_ids)

    quests = []
    for q in candidates:
        is_repeatable = q.quest_type in ("daily", "weekly")
        if is_repeatable and not await quest_repo.is_available_again(player.id, q.id):
            continue
        quests.append(q)

    if not quests:
        all_done = (
            "Усі доступні завдання виконано! Підвищуй рівень для нових." if locale == "uk"
            else "All available quests completed! Level up for new ones."
        )
        if edit:
            await target.message.edit_text(all_done)
        else:
            await target.answer(all_done)
        return

    header = "📋 **Дошка завдань**\n\nОберіть завдання:" if locale == "uk" else "📋 **Quest Board**\n\nChoose a quest:"
    kb = _quest_list_kb(quests, locale)
    if edit:
        await target.message.edit_text(header, reply_markup=kb, parse_mode="Markdown")
    else:
        await target.answer(header, reply_markup=kb, parse_mode="Markdown")

    await state.set_state(GameStates.QUEST_PROPOSAL)


# ── Handlers ──────────────────────────────────────────────────────────────────

@router.message(Command("quest"))
async def cmd_quest(message: Message, state: FSMContext, db_session: AsyncSession):
    await _show_quest_board(message, state, db_session, edit=False)


@router.callback_query(QuestCB.filter(F.action == "list"))
async def cb_quest_list(cb: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await cb.answer()
    await _show_quest_board(cb, state, db_session, edit=True)


@router.callback_query(F.data == "show_quests")
async def cb_show_quests(cb: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await cb.answer()
    await _show_quest_board(cb, state, db_session, edit=True)


@router.callback_query(QuestCB.filter(F.action == "select"))
async def cb_quest_select(cb: CallbackQuery, callback_data: QuestCB, state: FSMContext):
    await cb.answer()
    locale = _t(cb.from_user.id)
    quest = get_quest_by_id(callback_data.data)
    if not quest:
        await cb.answer("Quest not found.", show_alert=True)
        return

    title = quest.get("title", locale)
    questgiver = quest.get("questgiver", locale)
    proposal = quest.get("proposal_text", locale)
    xp_label = "Досвід" if locale == "uk" else "XP"
    gold_label = "Золото" if locale == "uk" else "Gold"
    reward_label = "Нагорода" if locale == "uk" else "Reward"

    text = (
        f"📜 **{title}**\n\n"
        f"*{questgiver}:*\n{proposal}\n\n"
        f"💎 {reward_label}: {quest.reward_xp} {xp_label} · {quest.reward_gold} {gold_label}"
    )

    await state.update_data(quest_id=quest.id)
    await cb.message.edit_text(text, reply_markup=_proposal_kb(locale), parse_mode="Markdown")


async def _start_quest_phase(
    message, state: FSMContext, db_session: AsyncSession, edit: bool = False
) -> None:
    """Shared entry point used by both cb_quest_accept and travel arrival."""
    user_id = message.chat.id  # travel calls with message, not callback
    locale = i18n_service.get_user_language(user_id)

    fsm = await state.get_data()
    quest = get_quest_by_id(fsm.get("quest_id", ""))
    if not quest:
        await message.answer("Quest data lost. Try /quest.")
        return

    player = await PlayerRepository(db_session).get_player_by_telegram_id(user_id)
    if player:
        await QuestRepository(db_session).start_quest(player.id, quest.id)

    obj_progress = {o.id: 0 for o in quest.objectives}
    await state.update_data(
        quest_phase="exploration",
        obj_progress=obj_progress,
        current_obj_idx=0,
    )
    await state.set_state(GameStates.QUEST_ACTIVE)
    await _render_phase(
        message, quest, 0, obj_progress, locale, edit=edit,
        player_level=player.level if player else 1,
    )


@router.callback_query(QuestCB.filter(F.action == "accept"))
async def cb_quest_accept(cb: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await cb.answer()
    if await state.get_state() == GameStates.QUEST_ACTIVE:
        return  # duplicate click — first already succeeded

    fsm = await state.get_data()
    quest = get_quest_by_id(fsm.get("quest_id", ""))
    if not quest:
        await cb.message.edit_text("Quest data lost. Try /quest.")
        return

    from app.handlers.travel import travel_start
    await travel_start(
        message=cb.message,
        state=state,
        quest_id=quest.id,
        quest_location=quest.location,
        start_quest_fn=_start_quest_phase,
        db_session=db_session,
    )


@router.callback_query(QuestCB.filter(F.action == "decline"))
async def cb_quest_decline(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    from app.handlers.menu import build_main_menu_kb
    user_id = cb.from_user.id
    locale = _t(user_id)
    msg = "Ти відмовився від завдання." if locale == "uk" else "You declined the quest."
    await state.set_state(GameStates.CITY_EXPLORATION)
    await state.update_data(quest_id=None, quest_phase=None, obj_progress=None, current_obj_idx=None)
    from app.services.i18n_service import i18n_service as _i18n
    await cb.message.edit_text(
        msg + "\n\n" + _i18n.get_text(user_id, 'menu.title'),
        reply_markup=build_main_menu_kb(user_id),
        parse_mode="Markdown"
    )


@router.callback_query(QuestCB.filter(F.action == "hero_info"), GameStates.QUEST_ACTIVE)
async def cb_quest_hero_info(cb: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await cb.answer()
    user_id = cb.from_user.id
    locale = _t(user_id)

    player = await PlayerRepository(db_session).get_player_by_telegram_id(user_id)
    if not player:
        msg = "Герой не знайдений." if locale == "uk" else "Hero not found."
        await cb.answer(msg, show_alert=True)
        return

    derived = player.get_derived_stats()
    xp_now, xp_need = player.get_xp_progress()
    from app.services.progression_service import ProgressionService
    xp_bar = ProgressionService.calc_xp_bar(player)

    class_label = "Клас" if locale == "uk" else "Class"
    hp_label = "HP" if locale == "uk" else "HP"
    atk_label = "Атака" if locale == "uk" else "Attack"
    mag_label = "Магія" if locale == "uk" else "Magic"
    gold_label = "Золото" if locale == "uk" else "Gold"
    back_label = "◀️ До квесту" if locale == "uk" else "◀️ Back to quest"

    text = (
        f"🧙 **{player.character_name}** · Lv.{player.level}\n"
        f"{class_label}: {player.get_character_class_name()}\n\n"
        f"❤️ {hp_label}: {player.health}/{derived.hp_max}\n"
        f"⚔️ {atk_label}: {derived.attack}  🔮 {mag_label}: {derived.magic}\n"
        f"💰 {gold_label}: {player.coins}\n\n"
        f"{xp_bar}"
    )

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_label, callback_data=QuestCB(action="back_to_quest").pack())]
    ])
    await cb.message.edit_text(text, reply_markup=back_kb, parse_mode="Markdown")


@router.callback_query(QuestCB.filter(F.action == "back_to_quest"), GameStates.QUEST_ACTIVE)
async def cb_back_to_quest(cb: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await cb.answer()
    fsm = await state.get_data()
    locale = _t(cb.from_user.id)
    quest = get_quest_by_id(fsm.get("quest_id", ""))
    if not quest:
        await cb.message.edit_text("Quest data lost. Try /quest.")
        await state.set_state(GameStates.MENU)
        return
    obj_idx = fsm.get("current_obj_idx", 0)
    obj_progress = fsm.get("obj_progress", {})
    player = await PlayerRepository(db_session).get_player_by_telegram_id(cb.from_user.id)
    await _render_phase(
        cb.message, quest, obj_idx, obj_progress, locale, edit=True,
        player_level=player.level if player else 1,
    )


@router.callback_query(QuestCB.filter(F.action == "do"), GameStates.QUEST_ACTIVE)
async def cb_quest_do(cb: CallbackQuery, callback_data: QuestCB, state: FSMContext, db_session: AsyncSession):
    await cb.answer()
    locale = _t(cb.from_user.id)
    action = callback_data.data

    fsm = await state.get_data()
    quest = get_quest_by_id(fsm.get("quest_id", ""))
    if not quest:
        await cb.message.edit_text("Quest data lost. Try /quest.")
        await state.set_state(GameStates.MENU)
        return

    obj_idx: int = fsm.get("current_obj_idx", 0)
    obj_progress: dict = fsm.get("obj_progress", {})
    obj = quest.objectives[obj_idx]

    if action not in obj.required_actions:
        miss = "Це не те що потрібно зараз..." if locale == "uk" else "That doesn't seem to help right now..."
        await cb.answer(miss, show_alert=False)
        return

    obj_progress[obj.id] = obj_progress.get(obj.id, 0) + 1

    if obj_progress[obj.id] >= obj.count:
        obj_idx += 1

    await state.update_data(obj_progress=obj_progress, current_obj_idx=obj_idx)

    player = await PlayerRepository(db_session).get_player_by_telegram_id(
        cb.from_user.id
    )
    if player:
        await QuestRepository(db_session).update_progress(
            player.id,
            quest.id,
            current_objective_idx=obj_idx,
            obj_progress=obj_progress,
        )

    if obj_idx >= len(quest.objectives):
        # All objectives done → resolve
        await _resolve_quest(cb, quest, state, db_session, cb.from_user.id, locale)
    else:
        is_entering_confrontation = obj_idx == len(quest.objectives) - 1
        await _render_phase(
            cb.message, quest, obj_idx, obj_progress, locale,
            edit=not is_entering_confrontation,
            player_level=player.level if player else 1,
        )


# ── Internal rendering ────────────────────────────────────────────────────────

def _talk_objective_npc(obj) -> str | None:
    for action in obj.required_actions:
        if action.startswith("talk-"):
            return action.removeprefix("talk-")
    return None


async def _render_phase(
    message,
    quest: QuestDef,
    obj_idx: int,
    obj_progress: dict,
    locale: str,
    edit: bool,
    player_level: int = 1,
):
    is_last_obj = obj_idx == len(quest.objectives) - 1
    phase_key = "confrontation_text" if is_last_obj else "exploration_text"
    phase_text = quest.get(phase_key, locale)
    title = quest.get("title", locale)

    done = sum(1 for o in quest.objectives if obj_progress.get(o.id, 0) >= o.count)
    total = len(quest.objectives)
    prog_label = "Прогрес" if locale == "uk" else "Progress"

    if is_last_obj:
        divider = "〰〰〰〰〰〰〰〰〰〰"
        transition = "⚡ Вирішальний момент" if locale == "uk" else "⚡ The decisive moment"
        header = f"⚔️ **{title}**\n\n{divider}\n_{transition}_\n{divider}\n\n"
    else:
        header = f"🗺 **{title}**\n\n"

    text = f"{header}{phase_text}\n\n📊 {prog_label}: {done}/{total}"

    obj = quest.objectives[obj_idx]
    talk_npc_id = _talk_objective_npc(obj)
    if talk_npc_id:
        line, _idx = npc_loader.pick_line(talk_npc_id, "rumor", player_level, locale)
        if not line:
            line, _idx = npc_loader.pick_line(talk_npc_id, "greeting", player_level, locale)
        if line:
            text += f"\n\n🗣 _{line}_"
    # Show required actions + 2 extra for variety (deduplicated)
    extra = [a for a in ["investigate", "explore", "talk", "flee"] if a not in obj.required_actions][:2]
    actions = list(dict.fromkeys(obj.required_actions + extra))

    kb = _phase_kb(actions, locale)
    if edit:
        await _safe_edit(message, text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")


async def _resolve_quest(
    cb: CallbackQuery,
    quest: QuestDef,
    state: FSMContext,
    db_session: AsyncSession,
    user_id: int,
    locale: str,
):
    player = await PlayerRepository(db_session).get_player_by_telegram_id(user_id)
    if not player:
        await cb.message.edit_text("❌ Player not found.")
        await state.set_state(GameStates.MENU)
        return

    chance = _success_chance(quest.tier, player.level, quest.min_level)
    success = random.randint(1, 100) <= chance

    result = await ProgressionService(db_session).award_quest_rewards(
        player,
        xp=quest.reward_xp,
        gold=quest.reward_gold,
        partial=1.0 if success else 0.25,
    )

    quest_repo = QuestRepository(db_session)
    if success:
        available_at = (
            datetime.utcnow() + timedelta(hours=quest.reset_hours)
            if quest.reset_hours
            else None
        )
        await quest_repo.complete_quest(player.id, quest.id, available_at=available_at)
    else:
        await quest_repo.fail_quest(player.id, quest.id)

    loot_gained = await _roll_loot(db_session, player.id, quest) if success else []

    title = quest.get("title", locale)
    outcome = quest.get("success_text" if success else "fail_text", locale)
    xp_label = "Досвід" if locale == "uk" else "XP"
    gold_label = "Золото" if locale == "uk" else "Gold"

    if success:
        reward_line = f"\n\n✅ +{result.xp_gained} {xp_label} · +{result.gold_gained} {gold_label}"
    else:
        fail_label = "Завдання провалено" if locale == "uk" else "Quest failed"
        reward_line = f"\n\n❌ {fail_label} · +{result.xp_gained} {xp_label}"

    if loot_gained:
        loot_label = "Здобич" if locale == "uk" else "Loot"
        items_str = ", ".join(f"{name} x{qty}" for name, qty in loot_gained)
        reward_line += f"\n🎁 {loot_label}: {items_str}"

    xp_bar = ProgressionService.calc_xp_bar(player)
    text = f"{'✅' if success else '❌'} **{title}**\n\n{outcome}{reward_line}\n\n{xp_bar}"

    if result.leveled_up:
        if locale == "uk":
            text += f"\n\n🎉 **ПІДВИЩЕННЯ РІВНЯ!** {result.old_level} → {result.new_level}\n+{result.stat_points_gained} очок характеристик · /character"
        else:
            text += f"\n\n🎉 **LEVEL UP!** {result.old_level} → {result.new_level}\n+{result.stat_points_gained} stat points · /character"

    await cb.message.edit_text(text, reply_markup=_result_kb(locale), parse_mode="Markdown")
    # Keep current_location at quest site so next travel starts from here
    await state.update_data(
        quest_id=None, quest_phase=None, obj_progress=None, current_obj_idx=None,
        current_location=quest.location,
    )
    await state.set_state(GameStates.CITY_EXPLORATION)

    logger.info(
        "Quest resolved",
        user_id=user_id,
        quest_id=quest.id,
        success=success,
        xp=result.xp_gained,
        leveled_up=result.leveled_up,
        new_level=result.new_level,
    )
