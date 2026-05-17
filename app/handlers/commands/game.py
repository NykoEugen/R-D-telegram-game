from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.logging_service import get_logger
from app.services.i18n_service import i18n_service
from app.services.fsm_service import FSMStateService
from app.handlers.keyboards import build_actions_kb
from app.handlers.callbacks import ActionCB
from app.game.actions import Action
from app.game.states import GameStates

router = Router()
logger = get_logger(__name__)

_FALLBACK_QUESTS = [
    "A mysterious artifact was found in ancient ruins. Local villagers speak of strange sounds and glowing lights from the depths. Will you investigate this ancient mystery?",
    "A merchant caravan has gone missing on the northern road. Tracks lead into the dark forest. Someone needs to find out what happened.",
    "Strange creatures have been spotted near the old mill. The miller begs for help. What lurks in the shadows?",
]


@router.message(Command("quest"))
async def cmd_quest(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle the /quest command - provide a quest description."""
    try:
        user_id = message.from_user.id

        await state.set_state(GameStates.QUEST_ACTIVE)
        await message.answer(i18n_service.get_text(user_id, "quest_generating"), parse_mode="HTML")

        import random
        quest_description = random.choice(_FALLBACK_QUESTS)

        quest_text = (
            f"{i18n_service.get_text(user_id, 'new_quest')}\n\n"
            f"{i18n_service.get_text(user_id, 'quest_description', description=quest_description)}\n\n"
            f"{i18n_service.get_text(user_id, 'what_will_you_do')}\n\n"
            f"{i18n_service.get_text(user_id, 'quest_hint')}"
        )

        user_language = i18n_service.get_user_language(user_id)
        scene_id = f"quest-{user_id}-{message.message_id}"
        quest_actions = [Action.ACCEPT, Action.INVESTIGATE, Action.PREPARE, Action.TALK, Action.BACK]

        keyboard = build_actions_kb(
            actions=quest_actions,
            locale=user_language,
            scene_id=scene_id,
            row_width=2,
        )

        await state.update_data(quest_description=quest_description, scene_id=scene_id)

        await fsm_service.sync_fsm_to_postgres(
            state, user_id, action="quest_start", scene_id=scene_id,
            additional_data={"quest_description": quest_description},
        )

        await message.answer(quest_text, parse_mode="Markdown", reply_markup=keyboard)
        logger.info("User requested a quest", user_id=user_id)

    except Exception as e:
        logger.error("Error in quest command", user_id=message.from_user.id,
                     error_type=type(e).__name__, error_message=str(e))
        await message.answer("❌ Quest Error\n\nThere was an error. Please try again later.")


@router.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle the /status command - show game status."""
    try:
        user_id = message.from_user.id
        current_state = await state.get_state()
        fsm_data = await state.get_data()
        session_state = await fsm_service.get_session_state(user_id)

        status_text = (
            f"{i18n_service.get_text(user_id, 'game_status')}\n\n"
            f"{i18n_service.get_text(user_id, 'current_game')}\n"
            f"{i18n_service.get_text(user_id, 'player_level')}\n"
            f"{i18n_service.get_text(user_id, 'experience')}\n"
            f"{i18n_service.get_text(user_id, 'gold')}\n"
            f"{i18n_service.get_text(user_id, 'inventory')}\n\n"
        )

        if current_state:
            status_text += f"🎮 **Current State:** `{current_state}`\n"

        if session_state:
            status_text += f"📊 **Session:** {session_state['session_id'][:8]}...\n"
            status_text += f"⚡ **Actions:** {session_state['actions_count']}\n"

        if fsm_data:
            status_text += f"📝 **FSM Data:** {len(fsm_data)} items\n"

        status_text += (
            f"\n{i18n_service.get_text(user_id, 'under_development')}\n\n"
            f"{i18n_service.get_text(user_id, 'status_hint')}"
        )

        await fsm_service.sync_fsm_to_postgres(
            state, user_id, action="status_check", scene_id=fsm_data.get("scene_id"),
        )

        await message.answer(status_text, parse_mode="Markdown")
        logger.info("User requested game status", user_id=user_id, current_state=current_state)

    except Exception as e:
        logger.error("Error in status command", user_id=message.from_user.id,
                     error_type=type(e).__name__, error_message=str(e))
        await message.answer("❌ Status Error\n\nThere was an error retrieving your status.")


@router.message(Command("demo_actions"))
async def demo_actions(msg: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle the /demo_actions command - demonstrate action buttons."""
    try:
        user_id = msg.from_user.id
        await state.set_state(GameStates.COMBAT_ACTIVE)

        locale = i18n_service.get_user_language(user_id)
        scene_id = "intro-wolf-001"
        actions = [Action.ATTACK, Action.TALK, Action.SNEAK, Action.FLEE, Action.BACK]

        kb = build_actions_kb(actions=actions, locale=locale, scene_id=scene_id)

        await state.update_data(scene_id=scene_id, demo_mode=True)
        await fsm_service.sync_fsm_to_postgres(
            state, user_id, action="demo_actions", scene_id=scene_id,
            additional_data={"demo_mode": True},
        )

        text = "Ти стоїш перед вовком. Що робитимеш?" if locale == "uk" else "You stand before a wolf. What will you do?"
        await msg.answer(text, reply_markup=kb)
        logger.info("User requested demo actions", user_id=user_id)

    except Exception as e:
        logger.error("Error in demo_actions command", user_id=msg.from_user.id,
                     error_type=type(e).__name__, error_message=str(e))
        await msg.answer("❌ Demo Actions Error\n\nThere was an error loading demo actions.")


@router.callback_query(ActionCB.filter())
async def on_action_press(cb: CallbackQuery, callback_data: ActionCB, state: FSMContext,
                           db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle action button presses."""
    try:
        user_id = cb.from_user.id
        action = callback_data.a
        scene_id = callback_data.s

        current_state = await state.get_state()
        fsm_data = await state.get_data()

        if action == Action.BACK:
            await state.set_state(GameStates.MENU)
        elif action in [Action.ATTACK, Action.DEFEND, Action.CAST]:
            await state.set_state(GameStates.COMBAT_CHOICE)
        elif action in [Action.TALK, Action.INVESTIGATE]:
            await state.set_state(GameStates.DIALOGUE_CHOICE)
        elif action == Action.ACCEPT:
            await state.set_state(GameStates.QUEST_CHOICE)

        await state.update_data(
            last_action=action, last_scene_id=scene_id,
            action_count=fsm_data.get("action_count", 0) + 1,
        )

        await fsm_service.sync_fsm_to_postgres(
            state, user_id, action=action, scene_id=scene_id,
            additional_data={"action_type": action},
        )

        await cb.answer()

        response_text = (
            f"🎮 **Action Selected**\n\n"
            f"Action: `{action}`\n"
            f"Scene: `{scene_id}`\n"
            f"State: `{current_state}` → `{await state.get_state()}`"
        )
        await cb.message.edit_text(response_text, parse_mode="Markdown")

        logger.info("User selected action", user_id=user_id, action=action, scene_id=scene_id)

    except Exception as e:
        logger.error("Error in action callback", user_id=cb.from_user.id,
                     error_type=type(e).__name__, error_message=str(e))
        await cb.answer("❌ Error processing action", show_alert=True)
