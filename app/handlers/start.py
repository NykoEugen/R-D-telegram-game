from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.services.openai_service import OpenAIService
from app.services.logging_service import get_logger
from app.services.i18n_service import i18n_service

router = Router()
logger = get_logger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle the /start command - greet player and introduce the RPG world."""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name or "Adventurer"
        
        # Generate world description using OpenAI with user's language
        user_language = i18n_service.get_user_language(user_id)
        world_description = await OpenAIService.generate_world_description(language=user_language)
        
        if world_description:
            welcome_text = (
                f"{i18n_service.get_text(user_id, 'start_welcome', name=user_name)}\n\n"
                f"{i18n_service.get_text(user_id, 'world_description', description=world_description)}\n\n"
                f"{i18n_service.get_text(user_id, 'adventure_awaits')}\n"
                f"{i18n_service.get_text(user_id, 'available_commands')}\n"
                f"{i18n_service.get_text(user_id, 'start_command')}\n"
                f"{i18n_service.get_text(user_id, 'quest_command')}\n"
                f"{i18n_service.get_text(user_id, 'help_command')}\n"
                f"{i18n_service.get_text(user_id, 'language_command')}\n\n"
                f"{i18n_service.get_text(user_id, 'ready_adventure')}"
            )
        else:
            # Fallback if OpenAI fails
            welcome_text = (
                f"{i18n_service.get_text(user_id, 'fallback_welcome')}\n\n"
                f"{i18n_service.get_text(user_id, 'fallback_world', description='Embark on epic quests in a medieval fantasy world!')}\n\n"
                f"{i18n_service.get_text(user_id, 'adventure_awaits')}\n"
                f"{i18n_service.get_text(user_id, 'available_commands')}\n"
                f"{i18n_service.get_text(user_id, 'start_command')}\n"
                f"{i18n_service.get_text(user_id, 'quest_command')}\n"
                f"{i18n_service.get_text(user_id, 'help_command')}\n"
                f"{i18n_service.get_text(user_id, 'language_command')}\n\n"
                f"{i18n_service.get_text(user_id, 'ready_adventure')}"
            )
        
        await message.answer(welcome_text, parse_mode="HTML")
        logger.info("User started the bot", 
                   user_id=message.from_user.id,
                   user_name=message.from_user.first_name,
                   chat_id=message.chat.id)
        
    except Exception as e:
        logger.error("Error in start command", 
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.answer(
            "🎮 Welcome to the Fantasy RPG Adventure!\n\n"
            "❌ There was an error, but you can still use:\n"
            "• /quest - Generate a new quest"
        )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle the /help command - show available commands and game information."""
    user_id = message.from_user.id
    
    help_text = (
        f"{i18n_service.get_text(user_id, 'help_title')}\n\n"
        f"{i18n_service.get_text(user_id, 'game_commands')}\n"
        f"{i18n_service.get_text(user_id, 'start_command')}\n"
        f"{i18n_service.get_text(user_id, 'quest_command')}\n"
        f"{i18n_service.get_text(user_id, 'help_command')}\n"
        f"{i18n_service.get_text(user_id, 'language_command')}\n\n"
        f"{i18n_service.get_text(user_id, 'about_game')}\n"
        f"{i18n_service.get_text(user_id, 'about_description')}\n\n"
        f"{i18n_service.get_text(user_id, 'getting_started')}\n"
        f"{i18n_service.get_text(user_id, 'getting_started_1')}\n"
        f"{i18n_service.get_text(user_id, 'getting_started_2')}\n"
        f"{i18n_service.get_text(user_id, 'getting_started_3')}\n\n"
        f"{i18n_service.get_text(user_id, 'adventure_legendary')}"
    )
    
    await message.answer(help_text, parse_mode="Markdown")
    logger.info("User requested help", 
               user_id=message.from_user.id,
               user_name=message.from_user.first_name,
               chat_id=message.chat.id)
