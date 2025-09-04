from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.services.openai_service import OpenAIService
from app.services.logging_service import get_logger
from app.services.i18n_service import i18n_service

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
