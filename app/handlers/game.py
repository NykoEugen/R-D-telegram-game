"""
Main game handler for the dynamic scene graph system.
"""

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
from app.game.actions import Action, ActionProcessor, get_available_actions
from app.game.states import GameStates
from app.game.scenes import (
    SceneGraphManager, PlayerState, SceneType,
    scene_graph,
)
from app.core.config import settings
from app.services.scene_text_loader import get_scene_text

router = Router()
logger = get_logger(__name__)


def _scene_description(scene, locale: str = "en") -> str:
    text = get_scene_text(scene.id, locale)
    if text:
        return text
    # Fallback to generic template if scene not in YAML
    fallbacks = {
        "story": "You find yourself in {scene}.",
        "choice": "You must make a decision at {scene}.",
        "encounter": "A dangerous encounter awaits at {scene}!",
        "dialogue": "You meet someone at {scene}.",
        "rest": "You rest at {scene}.",
        "exploration": "You explore {scene}.",
        "quest": "A quest presents itself at {scene}.",
        "loot": "You discover items at {scene}!",
        "combat": "Battle erupts at {scene}!",
    }
    template = fallbacks.get(scene.kind.value, "You are at {scene}.")
    return template.format(scene=scene.id.replace("_", " ").title())


@router.message(Command("adventure"))
async def cmd_adventure(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Start a new adventure using the dynamic scene graph system."""
    try:
        user_id = message.from_user.id

        await state.set_state(GameStates.QUEST_ACTIVE)

        player_state = await _get_or_create_player_state(user_id, state)

        if player_state.energy < 20:
            await message.answer(
                f"⚡ Not Enough Energy\n\n"
                f"Current energy: {player_state.energy}/100\n"
                f"Rest or wait for energy to regenerate."
            )
            return

        starting_scene = scene_graph.get_next_scene(player_state)
        if not starting_scene:
            await message.answer("❌ No starting scenes available. Please try again later.")
            return

        scene_graph.apply_scene_consequences(starting_scene, player_state)
        player_state.current_scene = starting_scene.id

        description = _scene_description(starting_scene)
        available_actions = get_available_actions(starting_scene.kind.value, player_state)

        user_language = i18n_service.get_user_language(user_id)
        keyboard = build_actions_kb(
            actions=available_actions,
            locale=user_language,
            scene_id=starting_scene.id,
            row_width=2,
        )

        await state.update_data(
            player_state=player_state,
            current_scene=starting_scene.id,
            adventure_active=True,
        )

        await fsm_service.sync_fsm_to_postgres(
            state, user_id, action="adventure_start", scene_id=starting_scene.id,
            additional_data={"scene_type": starting_scene.kind.value, "energy": player_state.energy},
        )

        text = (
            f"⚔️ ADVENTURE BEGINS!\n\n"
            f"Scene: {starting_scene.id.replace('_', ' ').title()}\n"
            f"Type: {starting_scene.kind.value.title()}\n\n"
            f"{description}\n\n"
            f"⚡ Energy: {player_state.energy}/100  "
            f"⚠️ Risk: {player_state.risk_level}  "
            f"📊 Steps: {player_state.step_count}\n\n"
            f"What will you do?"
        )
        await message.answer(text, reply_markup=keyboard)

        logger.info("User started adventure", user_id=user_id, scene_id=starting_scene.id)

    except Exception as e:
        logger.error("Error in adventure command", user_id=message.from_user.id,
                     error_type=type(e).__name__, error_message=str(e))
        await message.answer("❌ Error starting adventure. Please try again later.")


@router.callback_query(ActionCB.filter())
async def on_adventure_action(cb: CallbackQuery, callback_data: ActionCB, state: FSMContext,
                               db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle action button presses during adventure."""
    try:
        user_id = cb.from_user.id
        action = callback_data.a
        scene_id = callback_data.s

        fsm_data = await state.get_data()
        player_state = fsm_data.get("player_state")
        current_scene_id = fsm_data.get("current_scene")

        if not player_state or not current_scene_id:
            await cb.answer("❌ Adventure state not found", show_alert=True)
            return

        current_scene = scene_graph.scenes.get(current_scene_id)
        if not current_scene:
            await cb.answer("❌ Scene not found", show_alert=True)
            return

        scene_context = {"scene_type": current_scene.kind.value, "scene_id": current_scene.id}
        consequence = ActionProcessor.process_action(action, player_state, scene_context)
        action_result = ActionProcessor.apply_consequence(consequence, player_state)

        end_reason = scene_graph.check_end_conditions(player_state)
        if end_reason:
            await _end_adventure(cb, player_state, end_reason, state, fsm_service)
            return

        next_scene = scene_graph.get_next_scene(player_state, current_scene_id)
        if not next_scene:
            await _end_adventure(cb, player_state, "No more scenes available", state, fsm_service)
            return

        scene_graph.apply_scene_consequences(next_scene, player_state)
        player_state.current_scene = next_scene.id

        description = _scene_description(next_scene)
        available_actions = get_available_actions(next_scene.kind.value, player_state)

        user_language = i18n_service.get_user_language(user_id)
        keyboard = build_actions_kb(
            actions=available_actions,
            locale=user_language,
            scene_id=next_scene.id,
            row_width=2,
        )

        await state.update_data(player_state=player_state, current_scene=next_scene.id)

        await fsm_service.sync_fsm_to_postgres(
            state, user_id, action=action, scene_id=next_scene.id,
            additional_data={"energy": player_state.energy, "risk_level": player_state.risk_level},
        )

        text = (
            f"Action: {action.title()}  ✅ {action_result['message']}\n\n"
            f"Scene: {next_scene.id.replace('_', ' ').title()}\n"
            f"Type: {next_scene.kind.value.title()}\n\n"
            f"{description}\n\n"
            f"⚡ Energy: {player_state.energy}/100  "
            f"⚠️ Risk: {player_state.risk_level}  "
            f"📊 Steps: {player_state.step_count}\n\n"
            f"What will you do?"
        )
        await cb.message.edit_text(text, reply_markup=keyboard)
        await cb.answer()

        logger.info("User took action", user_id=user_id, action=action, scene_id=next_scene.id)

    except Exception as e:
        logger.error("Error in adventure action", user_id=cb.from_user.id,
                     error_type=type(e).__name__, error_message=str(e))
        await cb.answer("❌ Error processing action", show_alert=True)


async def _get_or_create_player_state(user_id: int, state: FSMContext) -> PlayerState:
    fsm_data = await state.get_data()
    player_state = fsm_data.get("player_state")
    if not player_state:
        player_state = PlayerState(
            user_id=user_id,
            energy=settings.default_energy,
            risk_level=0,
            stats={"bravery": 1, "charisma": 1, "intellect": 1, "stamina": 1, "level": 1, "gold": 0, "xp": 0},
        )
    else:
        player_state.energy = min(player_state.energy, settings.max_energy)
    return player_state


async def _end_adventure(cb: CallbackQuery, player_state: PlayerState, end_reason: str,
                          state: FSMContext, fsm_service: FSMStateService):
    try:
        total_gold = player_state.stats.get("gold", 0)
        total_xp = player_state.stats.get("xp", 0)
        scenes_visited = len(player_state.visited_scenes)

        await state.set_state(GameStates.MENU)
        await state.update_data(player_state=player_state, adventure_active=False, current_scene=None)

        await fsm_service.sync_fsm_to_postgres(
            state, player_state.user_id, action="adventure_end", scene_id=None,
            additional_data={"end_reason": end_reason, "total_gold": total_gold, "total_xp": total_xp},
        )

        text = (
            f"🏰 ADVENTURE COMPLETE!\n\n"
            f"Scenes visited: {scenes_visited}\n"
            f"Steps taken: {player_state.step_count}\n"
            f"Final energy: {player_state.energy}/100\n"
            f"Final risk: {player_state.risk_level}\n\n"
            f"Gold earned: {total_gold}\n"
            f"Experience gained: {total_xp}\n\n"
            f"Reason: {end_reason}\n\n"
            f"Use /adventure to start a new adventure."
        )
        await cb.message.edit_text(text)
        await cb.answer()

        logger.info("Adventure ended", user_id=player_state.user_id, end_reason=end_reason)

    except Exception as e:
        logger.error("Error ending adventure", error_type=type(e).__name__, error_message=str(e))
        await cb.answer("❌ Error ending adventure", show_alert=True)
