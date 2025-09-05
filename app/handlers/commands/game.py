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
from app.game.actions import Action
from app.game.states import GameStates
from app.game.scenes import create_quest_scene, create_demo_scene

router = Router()
logger = get_logger(__name__)

@router.message(Command("quest"))
async def cmd_quest(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle the /quest command - generate and provide a new quest description."""
    try:
        user_id = message.from_user.id
        
        # Check if user has a hero first
        from app.handlers.utils import check_hero_required
        has_hero, user = await check_hero_required(message, db_session)
        if not has_hero:
            return
        
        # Set FSM state to quest active
        await state.set_state(GameStates.QUEST_ACTIVE)
        
        # Show typing indicator
        await message.answer(i18n_service.get_text(user_id, 'quest_generating'), parse_mode="HTML")
        
        # Generate quest description using OpenAI with user's language
        user_language = i18n_service.get_user_language(user_id)
        quest_description = await AIGenerationService.generate_quest_description(language=user_language)
        
        if quest_description:
            quest_text = (
                f"{i18n_service.get_text(user_id, 'new_quest')}\n\n"
                f"{i18n_service.get_text(user_id, 'quest_description', description=quest_description)}\n\n"
                f"{i18n_service.get_text(user_id, 'what_will_you_do')}\n\n"
                f"{i18n_service.get_text(user_id, 'quest_hint')}"
            )
        else:
            # Fallback if OpenAI fails
            quest_text = (
                f"{i18n_service.get_text(user_id, 'quest_failed')}\n\n"
                f"{i18n_service.get_text(user_id, 'fallback_quest')}\n\n"
                f"{i18n_service.get_text(user_id, 'what_will_you_do')}\n\n"
                f"{i18n_service.get_text(user_id, 'quest_hint')}"
            )
        
        # Create action buttons for quest scenarios
        user_language = i18n_service.get_user_language(user_id)
        scene_id = f"quest-{user_id}-{message.message_id}"  # Unique scene ID
        quest_actions = [Action.ACCEPT, Action.INVESTIGATE, Action.PREPARE, Action.TALK, Action.RUN_AI, Action.BACK]
        
        # Build keyboard with context hint from quest description
        context_hint = quest_description if quest_description else "A mysterious quest awaits your decision."
        keyboard = build_actions_kb(
            actions=quest_actions,
            locale=user_language,
            scene_id=scene_id,
            context_hint=context_hint,
            row_width=2
        )
        
        # Store quest data in FSM
        await state.update_data(
            quest_description=quest_description,
            scene_id=scene_id,
            quest_actions=quest_actions,
            context_hint=context_hint
        )
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action="quest_start",
            scene_id=scene_id,
            additional_data={"quest_description": quest_description}
        )
        
        await message.answer(quest_text, parse_mode="Markdown", reply_markup=keyboard)
        logger.info("User requested a quest", 
                   user_id=message.from_user.id,
                   user_name=message.from_user.first_name,
                   chat_id=message.chat.id)
        
    except Exception as e:
        logger.error("Error in quest command", 
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.answer(
            "❌ **Quest Generation Error**\n\n"
            "There was an error generating your quest. Please try again later.\n\n"
            "💡 **Hint:** Use /quest again in a few moments."
        )

@router.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle the /status command - show game status and current FSM state."""
    try:
        user_id = message.from_user.id
        
        # Check if user has a hero first
        from app.handlers.utils import check_hero_required
        has_hero, user = await check_hero_required(message, db_session)
        if not has_hero:
            return
        
        # Get current FSM state
        current_state = await state.get_state()
        fsm_data = await state.get_data()
        
        # Get session state from PostgreSQL
        session_state = await fsm_service.get_session_state(user_id)
        
        # Build status text
        status_text = (
            f"{i18n_service.get_text(user_id, 'game_status')}\n\n"
            f"{i18n_service.get_text(user_id, 'current_game')}\n"
            f"{i18n_service.get_text(user_id, 'player_level')}\n"
            f"{i18n_service.get_text(user_id, 'experience')}\n"
            f"{i18n_service.get_text(user_id, 'gold')}\n"
            f"{i18n_service.get_text(user_id, 'inventory')}\n\n"
        )
        
        # Add FSM state information
        if current_state:
            status_text += f"🎮 **Current State:** `{current_state}`\n"
        
        if session_state:
            status_text += f"📊 **Session:** {session_state['session_id'][:8]}...\n"
            status_text += f"⚡ **Actions:** {session_state['actions_count']}\n"
            status_text += f"💬 **Messages:** {session_state['messages_count']}\n"
        
        if fsm_data:
            status_text += f"📝 **FSM Data:** {len(fsm_data)} items\n"
        
        status_text += (
            f"\n{i18n_service.get_text(user_id, 'under_development')}\n\n"
            f"{i18n_service.get_text(user_id, 'status_hint')}"
        )
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action="status_check",
            scene_id=fsm_data.get("scene_id")
        )
        
        await message.answer(status_text, parse_mode="Markdown")
        logger.info("User requested game status", 
                   user_id=message.from_user.id,
                   user_name=message.from_user.first_name,
                   chat_id=message.chat.id,
                   current_state=current_state)
        
    except Exception as e:
        logger.error("Error in status command", 
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.answer(
            "❌ **Status Error**\n\n"
            "There was an error retrieving your status. Please try again later."
        )

@router.message(Command("demo_actions"))
async def demo_actions(msg: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle the /demo_actions command - demonstrate action buttons."""
    try:
        user_id = msg.from_user.id
        
        # Set FSM state to combat active
        await state.set_state(GameStates.COMBAT_ACTIVE)
        
        locale = i18n_service.get_user_language(user_id)
        scene_id = "intro-wolf-001"
        actions = [Action.ATTACK, Action.TALK, Action.SNEAK, Action.FLEE, Action.RUN_AI, Action.BACK]
        
        kb = build_actions_kb(
            actions=actions,
            locale=locale,
            scene_id=scene_id,
            context_hint="A wolf blocks the path in a dark forest."
        )
        
        # Store demo data in FSM
        await state.update_data(
            scene_id=scene_id,
            actions=actions,
            context_hint="A wolf blocks the path in a dark forest.",
            demo_mode=True
        )
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action="demo_actions",
            scene_id=scene_id,
            additional_data={"demo_mode": True}
        )
        
        # Use localized text for the message
        if locale == "uk":
            message_text = "Ти стоїш перед вовком. Що робитимеш?"
        else:
            message_text = "You stand before a wolf. What will you do?"
        
        await msg.answer(message_text, reply_markup=kb)
        logger.info("User requested demo actions", 
                   user_id=user_id,
                   user_name=msg.from_user.first_name,
                   chat_id=msg.chat.id)
        
    except Exception as e:
        logger.error("Error in demo_actions command", 
                    user_id=msg.from_user.id,
                    chat_id=msg.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await msg.answer("❌ **Demo Actions Error**\n\nThere was an error loading the demo actions. Please try again later.")

@router.callback_query(ActionCB.filter())
async def on_action_press(cb: CallbackQuery, callback_data: ActionCB, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle action button presses."""
    try:
        user_id = cb.from_user.id
        action = callback_data.a   # e.g. "attack"
        scene_id = callback_data.s
        
        # Get current FSM state and data
        current_state = await state.get_state()
        fsm_data = await state.get_data()
        
        # Handle RUN_AI action with AI generation and logging
        if action == Action.RUN_AI:
            # Create scene context for AI generation
            scene_context = create_demo_scene(scene_id, fsm_data.get("context_hint", "Unknown scene"))
            
            # Execute AI action with logging
            ai_response = await ai_action_service.execute_run_ai_action(
                user_id=user_id,
                action=action,
                scene_context=scene_context,
                db_session=db_session,
                game_session_id=fsm_data.get("game_session_id"),
                additional_context={
                    "fsm_state": current_state,
                    "fsm_data": fsm_data
                }
            )
            
            if ai_response:
                response_text = (
                    f"🤖 **AI Action Executed**\n\n"
                    f"{ai_response}\n\n"
                    f"Action: `{action}`\n"
                    f"Scene: `{scene_id}`\n"
                    f"State: `{current_state}`\n\n"
                    f"*AI generation logged to database!*"
                )
            else:
                response_text = (
                    f"❌ **AI Action Failed**\n\n"
                    f"Action: `{action}`\n"
                    f"Scene: `{scene_id}`\n"
                    f"State: `{current_state}`\n\n"
                    f"*AI generation failed, but attempt was logged.*"
                )
            
            await cb.message.edit_text(response_text, parse_mode="Markdown")
            return
        
        # Update FSM state based on action
        if action == Action.BACK:
            await state.set_state(GameStates.MENU)
        elif action in [Action.ATTACK, Action.DEFEND, Action.CAST]:
            await state.set_state(GameStates.COMBAT_CHOICE)
        elif action in [Action.TALK, Action.INVESTIGATE]:
            await state.set_state(GameStates.DIALOGUE_CHOICE)
        elif action == Action.ACCEPT:
            await state.set_state(GameStates.QUEST_CHOICE)
        else:
            # Keep current state for other actions
            pass
        
        # Update FSM data with action info
        await state.update_data(
            last_action=action,
            last_scene_id=scene_id,
            action_count=fsm_data.get("action_count", 0) + 1
        )
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action=action,
            scene_id=scene_id,
            additional_data={"action_type": action}
        )
        
        await cb.answer()  # small UX improvement
        
        # Create a more informative response
        response_text = (
            f"🎮 **Action Selected**\n\n"
            f"Action: `{action}`\n"
            f"Scene: `{scene_id}`\n"
            f"State: `{current_state}` → `{await state.get_state()}`\n\n"
            f"*FSM state synced to PostgreSQL!*"
        )
        
        await cb.message.edit_text(response_text, parse_mode="Markdown")
        
        logger.info("User selected action", 
                   user_id=user_id,
                   user_name=cb.from_user.first_name,
                   chat_id=cb.message.chat.id,
                   action=action,
                   scene_id=scene_id,
                   old_state=current_state,
                   new_state=await state.get_state())
        
    except Exception as e:
        logger.error("Error in action callback", 
                    user_id=cb.from_user.id,
                    chat_id=cb.message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await cb.answer("❌ Error processing action", show_alert=True)
