from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from app.services.openai_service import OpenAIService
from app.services.logging_service import get_logger
from app.services.i18n_service import i18n_service
from app.handlers.keyboards import build_actions_kb
from app.handlers.callbacks import ActionCB
from app.game.actions import Action

router = Router()
logger = get_logger(__name__)

@router.message(Command("quest"))
async def cmd_quest(message: Message):
    """Handle the /quest command - generate and provide a new quest description."""
    try:
        user_id = message.from_user.id
        
        # Show typing indicator
        await message.answer(i18n_service.get_text(user_id, 'quest_generating'), parse_mode="HTML")
        
        # Generate quest description using OpenAI with user's language
        user_language = i18n_service.get_user_language(user_id)
        quest_description = await OpenAIService.generate_quest_description(language=user_language)
        
        if quest_description:
            quest_text = (
                f"{i18n_service.get_text(user_id, 'new_quest')}\n\n"
                f"{i18n_service.get_text(user_id, 'quest_description', description=quest_description)}\n\n"
                f"{i18n_service.get_text(user_id, 'what_will_you_do')}\n"
                f"{i18n_service.get_text(user_id, 'quest_options')}\n\n"
                f"{i18n_service.get_text(user_id, 'quest_hint')}"
            )
        else:
            # Fallback if OpenAI fails
            quest_text = (
                f"{i18n_service.get_text(user_id, 'quest_failed')}\n\n"
                f"{i18n_service.get_text(user_id, 'fallback_quest')}\n\n"
                f"{i18n_service.get_text(user_id, 'what_will_you_do')}\n"
                f"{i18n_service.get_text(user_id, 'quest_options')}\n\n"
                f"{i18n_service.get_text(user_id, 'quest_hint')}"
            )
        
        await message.answer(quest_text, parse_mode="Markdown")
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
async def cmd_status(message: Message):
    """Handle the /status command - placeholder for future game status functionality."""
    user_id = message.from_user.id
    
    status_text = (
        f"{i18n_service.get_text(user_id, 'game_status')}\n\n"
        f"{i18n_service.get_text(user_id, 'current_game')}\n"
        f"{i18n_service.get_text(user_id, 'player_level')}\n"
        f"{i18n_service.get_text(user_id, 'experience')}\n"
        f"{i18n_service.get_text(user_id, 'gold')}\n"
        f"{i18n_service.get_text(user_id, 'inventory')}\n\n"
        f"{i18n_service.get_text(user_id, 'under_development')}\n\n"
        f"{i18n_service.get_text(user_id, 'status_hint')}"
    )
    
    await message.answer(status_text, parse_mode="Markdown")
    logger.info("User requested game status", 
               user_id=message.from_user.id,
               user_name=message.from_user.first_name,
               chat_id=message.chat.id)

@router.message(Command("demo_actions"))
async def demo_actions(msg: Message):
    """Handle the /demo_actions command - demonstrate action buttons."""
    try:
        user_id = msg.from_user.id
        locale = i18n_service.get_user_language(user_id)
        scene_id = "intro-wolf-001"
        actions = [Action.ATTACK, Action.TALK, Action.SNEAK, Action.FLEE, Action.BACK]
        
        kb = build_actions_kb(
            actions=actions,
            locale=locale,
            scene_id=scene_id,
            context_hint="A wolf blocks the path in a dark forest."
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
async def on_action_press(cb: CallbackQuery, callback_data: ActionCB):
    """Handle action button presses."""
    try:
        action = callback_data.a   # e.g. "attack"
        scene_id = callback_data.s
        
        # TODO: plug into existing game state machine / scene logic
        await cb.answer()  # small UX improvement
        
        # Create a more informative response
        response_text = f"🎮 **Action Selected**\n\nAction: `{action}`\nScene: `{scene_id}`\n\n*This is a demo - game logic integration coming soon!*"
        
        await cb.message.edit_text(response_text, parse_mode="Markdown")
        
        logger.info("User selected action", 
                   user_id=cb.from_user.id,
                   user_name=cb.from_user.first_name,
                   chat_id=cb.message.chat.id,
                   action=action,
                   scene_id=scene_id)
        
    except Exception as e:
        logger.error("Error in action callback", 
                    user_id=cb.from_user.id,
                    chat_id=cb.message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await cb.answer("❌ Error processing action", show_alert=True)
