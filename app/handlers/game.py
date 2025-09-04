"""
Main game handler for the dynamic scene graph system.

This module handles the core game loop: City → Adventure → Scene → Choice → (Combat | Event) → Loot → Progress → Return to city.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai import AIGenerationService, ai_action_service
from app.services.logging_service import get_logger
from app.services.i18n_service import i18n_service
from app.services.fsm_service import FSMStateService
from app.handlers.keyboards import build_actions_kb
from app.handlers.callbacks import ActionCB
from app.game.actions import Action, ActionProcessor, get_available_actions
from app.game.states import GameStates
from app.game.scenes import (
    SceneGraphManager, PlayerState, SceneContext, SceneType, 
    scene_graph, create_quest_scene, create_demo_scene
)
from app.core.config import settings

router = Router()
logger = get_logger(__name__)


@router.message(Command("adventure"))
async def cmd_adventure(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Start a new adventure using the dynamic scene graph system."""
    try:
        user_id = message.from_user.id
        
        # Set FSM state to adventure active
        await state.set_state(GameStates.QUEST_ACTIVE)
        
        # Create or get player state
        player_state = await _get_or_create_player_state(user_id, state)
        
        # Check if player has enough energy
        if player_state.energy < 20:  # Minimum energy to start adventure
            await message.answer(
                f"⚡ **Not Enough Energy**\n\n"
                f"Your energy is too low to start an adventure.\n"
                f"Current energy: {player_state.energy}/100\n\n"
                f"💡 *Rest or wait for energy to regenerate.*"
            )
            return
        
        # Get starting scene
        starting_scene = scene_graph.get_next_scene(player_state)
        if not starting_scene:
            await message.answer(
                "❌ **Adventure Error**\n\n"
                "No starting scenes available. Please try again later."
            )
            return
        
        # Apply scene consequences
        scene_graph.apply_scene_consequences(starting_scene, player_state)
        player_state.current_scene = starting_scene.id
        
        # Generate scene description using AI
        scene_description = await _generate_scene_description(starting_scene, player_state)
        
        # Get available actions for this scene
        available_actions = get_available_actions(starting_scene.kind.value, player_state)
        
        # Build keyboard
        user_language = i18n_service.get_user_language(user_id)
        keyboard = build_actions_kb(
            actions=available_actions,
            locale=user_language,
            scene_id=starting_scene.id,
            context_hint=scene_description,
            row_width=2
        )
        
        # Store adventure data in FSM
        await state.update_data(
            player_state=player_state,
            current_scene=starting_scene.id,
            scene_description=scene_description,
            available_actions=available_actions,
            adventure_active=True
        )
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action="adventure_start",
            scene_id=starting_scene.id,
            additional_data={
                "scene_type": starting_scene.kind.value,
                "energy": player_state.energy,
                "risk_level": player_state.risk_level
            }
        )
        
        # Send adventure start message
        adventure_text = (
            f"⚔️ **ADVENTURE BEGINS!** ⚔️\n\n"
            f"🌍 **Scene:** {starting_scene.id.replace('_', ' ').title()}\n"
            f"📖 **Type:** {starting_scene.kind.value.title()}\n\n"
            f"{scene_description}\n\n"
            f"⚡ **Energy:** {player_state.energy}/100\n"
            f"⚠️ **Risk Level:** {player_state.risk_level}\n"
            f"📊 **Steps:** {player_state.step_count}\n\n"
            f"🎯 **What will you do?**"
        )
        
        await message.answer(adventure_text, parse_mode="Markdown", reply_markup=keyboard)
        
        logger.info("User started adventure", 
                   user_id=user_id,
                   user_name=message.from_user.first_name,
                   chat_id=message.chat.id,
                   scene_id=starting_scene.id,
                   scene_type=starting_scene.kind.value)
        
    except Exception as e:
        logger.error("Error in adventure command", 
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.answer(
            "❌ **Adventure Error**\n\n"
            "There was an error starting your adventure. Please try again later."
        )


@router.callback_query(ActionCB.filter())
async def on_adventure_action(cb: CallbackQuery, callback_data: ActionCB, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle action button presses during adventure."""
    try:
        user_id = cb.from_user.id
        action = callback_data.a
        scene_id = callback_data.s
        
        # Get current FSM state and data
        fsm_data = await state.get_data()
        player_state = fsm_data.get("player_state")
        current_scene_id = fsm_data.get("current_scene")
        
        if not player_state or not current_scene_id:
            await cb.answer("❌ Adventure state not found", show_alert=True)
            return
        
        # Get current scene
        current_scene = scene_graph.scenes.get(current_scene_id)
        if not current_scene:
            await cb.answer("❌ Scene not found", show_alert=True)
            return
        
        # Process the action
        scene_context = {
            "scene_type": current_scene.kind.value,
            "scene_id": current_scene.id,
            "risk_level": player_state.risk_level
        }
        
        consequence = ActionProcessor.process_action(action, player_state, scene_context)
        action_result = ActionProcessor.apply_consequence(consequence, player_state)
        
        # Handle special actions
        if action == Action.RUN_AI:
            await _handle_ai_action(cb, action, scene_context, player_state, db_session, fsm_service)
            return
        
        # Check if adventure should end
        end_reason = scene_graph.check_end_conditions(player_state)
        if end_reason:
            await _end_adventure(cb, player_state, end_reason, state, fsm_service)
            return
        
        # Get next scene
        next_scene = scene_graph.get_next_scene(player_state, current_scene_id)
        if not next_scene:
            await _end_adventure(cb, player_state, "No more scenes available", state, fsm_service)
            return
        
        # Apply next scene consequences
        scene_graph.apply_scene_consequences(next_scene, player_state)
        player_state.current_scene = next_scene.id
        
        # Generate next scene description
        scene_description = await _generate_scene_description(next_scene, player_state)
        
        # Get available actions for next scene
        available_actions = get_available_actions(next_scene.kind.value, player_state)
        
        # Build keyboard
        user_language = i18n_service.get_user_language(user_id)
        keyboard = build_actions_kb(
            actions=available_actions,
            locale=user_language,
            scene_id=next_scene.id,
            context_hint=scene_description,
            row_width=2
        )
        
        # Update FSM data
        await state.update_data(
            player_state=player_state,
            current_scene=next_scene.id,
            scene_description=scene_description,
            available_actions=available_actions
        )
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action=action,
            scene_id=next_scene.id,
            additional_data={
                "scene_type": next_scene.kind.value,
                "energy": player_state.energy,
                "risk_level": player_state.risk_level,
                "action_result": action_result
            }
        )
        
        # Send next scene message
        scene_text = (
            f"🎮 **Action:** {action.value.title()}\n"
            f"✅ **Result:** {action_result['message']}\n\n"
            f"🌍 **Scene:** {next_scene.id.replace('_', ' ').title()}\n"
            f"📖 **Type:** {next_scene.kind.value.title()}\n\n"
            f"{scene_description}\n\n"
            f"⚡ **Energy:** {player_state.energy}/100\n"
            f"⚠️ **Risk Level:** {player_state.risk_level}\n"
            f"📊 **Steps:** {player_state.step_count}\n\n"
            f"🎯 **What will you do?**"
        )
        
        await cb.message.edit_text(scene_text, parse_mode="Markdown", reply_markup=keyboard)
        await cb.answer()
        
        logger.info("User took action in adventure", 
                   user_id=user_id,
                   action=action,
                   scene_id=next_scene.id,
                   energy=player_state.energy,
                   risk_level=player_state.risk_level)
        
    except Exception as e:
        logger.error("Error in adventure action callback", 
                    user_id=cb.from_user.id,
                    chat_id=cb.message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await cb.answer("❌ Error processing action", show_alert=True)


async def _get_or_create_player_state(user_id: int, state: FSMContext) -> PlayerState:
    """Get or create player state from FSM data."""
    fsm_data = await state.get_data()
    player_state = fsm_data.get("player_state")
    
    if not player_state:
        # Create new player state
        player_state = PlayerState(
            user_id=user_id,
            energy=settings.default_energy,
            risk_level=0,
            stats={
                "bravery": 1, "charisma": 1, "intellect": 1, 
                "stamina": 1, "level": 1, "gold": 0, "xp": 0
            }
        )
    else:
        # Ensure energy doesn't exceed maximum
        player_state.energy = min(player_state.energy, settings.max_energy)
    
    return player_state


async def _generate_scene_description(scene, player_state: PlayerState) -> str:
    """Generate scene description using AI."""
    try:
        user_language = i18n_service.get_user_language(player_state.user_id)
        
        # Create a prompt for scene description
        prompt = f"""
        Generate a vivid, immersive description for a {scene.kind.value} scene in a fantasy RPG.
        Scene ID: {scene.id}
        Player stats: {player_state.stats}
        Risk level: {player_state.risk_level}
        Energy: {player_state.energy}
        
        Make it engaging and appropriate for the scene type. Keep it concise but atmospheric.
        """
        
        # Use AI generation service
        description = await AIGenerationService.generate_quest_description(language=user_language)
        if description:
            return description
        
        # Fallback descriptions
        fallback_descriptions = {
            "story": f"You find yourself in {scene.id.replace('_', ' ')}. The atmosphere is tense.",
            "choice": f"You must make a decision at {scene.id.replace('_', ' ')}. What will you choose?",
            "encounter": f"A dangerous encounter awaits at {scene.id.replace('_', ' ')}!",
            "dialogue": f"You meet someone interesting at {scene.id.replace('_', ' ')}.",
            "rest": f"You find a safe place to rest at {scene.id.replace('_', ' ')}.",
            "exploration": f"You explore the mysterious {scene.id.replace('_', ' ')}.",
            "quest": f"A new quest opportunity presents itself at {scene.id.replace('_', ' ')}.",
            "loot": f"You discover valuable items at {scene.id.replace('_', ' ')}!",
            "combat": f"Battle erupts at {scene.id.replace('_', ' ')}!"
        }
        
        return fallback_descriptions.get(scene.kind.value, f"You are at {scene.id.replace('_', ' ')}.")
        
    except Exception as e:
        logger.error(f"Error generating scene description: {e}")
        return f"You find yourself at {scene.id.replace('_', ' ')}."


async def _handle_ai_action(cb: CallbackQuery, action: Action, scene_context: dict, player_state: PlayerState, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle AI action with generation service."""
    try:
        # Create scene context for AI generation
        scene_context_obj = create_demo_scene(scene_context["scene_id"], scene_context.get("description", "Unknown scene"))
        
        # Execute AI action
        ai_response = await ai_action_service.execute_run_ai_action(
            user_id=player_state.user_id,
            action=action,
            scene_context=scene_context_obj,
            db_session=db_session,
            game_session_id=None,  # Could be stored in player_state
            additional_context={
                "player_stats": player_state.stats,
                "risk_level": player_state.risk_level,
                "energy": player_state.energy,
                "scene_type": scene_context["scene_type"]
            }
        )
        
        if ai_response:
            response_text = (
                f"🤖 **AI Action Executed**\n\n"
                f"{ai_response}\n\n"
                f"*AI generation completed successfully!*"
            )
        else:
            response_text = (
                f"❌ **AI Action Failed**\n\n"
                f"*AI generation failed, but attempt was logged.*"
            )
        
        await cb.message.edit_text(response_text, parse_mode="Markdown")
        await cb.answer()
        
    except Exception as e:
        logger.error(f"Error in AI action: {e}")
        await cb.answer("❌ AI action failed", show_alert=True)


async def _end_adventure(cb: CallbackQuery, player_state: PlayerState, end_reason: str, state: FSMContext, fsm_service: FSMStateService):
    """End the adventure and return to city."""
    try:
        # Calculate final rewards
        total_gold = player_state.stats.get("gold", 0)
        total_xp = player_state.stats.get("xp", 0)
        scenes_visited = len(player_state.visited_scenes)
        
        # Reset adventure state
        await state.set_state(GameStates.MENU)
        await state.update_data(
            player_state=player_state,
            adventure_active=False,
            current_scene=None
        )
        
        # Sync final state
        await fsm_service.sync_fsm_to_postgres(
            state,
            player_state.user_id,
            action="adventure_end",
            scene_id=None,
            additional_data={
                "end_reason": end_reason,
                "final_energy": player_state.energy,
                "final_risk": player_state.risk_level,
                "total_steps": player_state.step_count,
                "scenes_visited": scenes_visited,
                "total_gold": total_gold,
                "total_xp": total_xp
            }
        )
        
        # Send adventure end message
        end_text = (
            f"🏰 **ADVENTURE COMPLETE!** 🏰\n\n"
            f"📊 **Adventure Summary:**\n"
            f"• Scenes visited: {scenes_visited}\n"
            f"• Steps taken: {player_state.step_count}\n"
            f"• Final energy: {player_state.energy}/100\n"
            f"• Final risk level: {player_state.risk_level}\n\n"
            f"💰 **Rewards:**\n"
            f"• Gold earned: {total_gold}\n"
            f"• Experience gained: {total_xp}\n\n"
            f"🏁 **Reason for ending:** {end_reason}\n\n"
            f"Welcome back to the city! Use /adventure to start a new adventure."
        )
        
        await cb.message.edit_text(end_text, parse_mode="Markdown")
        await cb.answer()
        
        logger.info("Adventure ended", 
                   user_id=player_state.user_id,
                   end_reason=end_reason,
                   scenes_visited=scenes_visited,
                   total_steps=player_state.step_count)
        
    except Exception as e:
        logger.error(f"Error ending adventure: {e}")
        await cb.answer("❌ Error ending adventure", show_alert=True)
