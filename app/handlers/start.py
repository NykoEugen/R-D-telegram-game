from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.services.openai_service import OpenAIService
from app.services.logging_service import get_logger
from app.config import Config

router = Router()
logger = get_logger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle the /start command - greet player and introduce the RPG world."""
    try:
        user_name = message.from_user.first_name or "Adventurer"
        _ = message.get("_")  # Get translation function
        
        # Generate world description using OpenAI
        world_description = await OpenAIService.generate_world_description()
        
        if world_description:
            welcome_text = (
                f"{_('start_welcome', name=user_name)}\n\n"
                f"{_('world_description', description=world_description)}\n\n"
                f"{_('adventure_awaits')}\n\n"
                f"{_('available_commands')}\n"
                f"{_('start_command')}\n"
                f"{_('quest_command')}\n"
                f"{_('help_command')}\n"
                f"{_('language_command')}\n\n"
                f"{_('ready_adventure')}"
            )
        else:
            # Fallback if OpenAI fails
            welcome_text = (
                f"{_('start_welcome', name=user_name)}\n\n"
                f"{_('fallback_world', description=Config.GAME_DESCRIPTION)}\n\n"
                f"{_('adventure_awaits')}\n\n"
                f"{_('available_commands')}\n"
                f"{_('start_command')}\n"
                f"{_('quest_command')}\n"
                f"{_('help_command')}\n"
                f"{_('language_command')}\n\n"
                f"{_('ready_adventure')}"
            )
        
        await message.answer(welcome_text, parse_mode="Markdown")
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
        _ = message.get("_")
        await message.answer(
            f"{_('fallback_welcome')}\n\n"
            f"{_('error_message')}\n"
            f"{_('quest_command')}"
        )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle the /help command - show available commands and game information."""
    _ = message.get("_")  # Get translation function
    
    help_text = (
        f"{_('help_title')}\n\n"
        f"{_('game_commands')}\n"
        f"{_('start_command')}\n"
        f"{_('quest_command')}\n"
        f"{_('help_command')}\n"
        f"{_('language_command')}\n\n"
        f"{_('about_game')}\n"
        f"{_('about_description')}\n\n"
        f"{_('getting_started')}\n"
        f"{_('getting_started_1')}\n"
        f"{_('getting_started_2')}\n"
        f"{_('getting_started_3')}\n\n"
        f"{_('adventure_legendary')}"
    )
    
    await message.answer(help_text, parse_mode="Markdown")
    logger.info("User requested help", 
               user_id=message.from_user.id,
               user_name=message.from_user.first_name,
               chat_id=message.chat.id)
