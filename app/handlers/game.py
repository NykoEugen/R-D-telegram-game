import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.services.openai_service import OpenAIService

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("quest"))
async def cmd_quest(message: Message):
    """Handle the /quest command - generate and provide a new quest description."""
    try:
        _ = message.get("_")  # Get translation function
        
        # Show typing indicator
        await message.answer(_("quest_generating"), parse_mode="Markdown")
        
        # Generate quest description using OpenAI
        quest_description = await OpenAIService.generate_quest_description()
        
        if quest_description:
            quest_text = (
                f"{_('new_quest')}\n\n"
                f"{_('quest_description', description=quest_description)}\n\n"
                f"{_('what_will_you_do')}\n"
                f"{_('quest_options')}\n\n"
                f"{_('quest_hint')}"
            )
        else:
            # Fallback if OpenAI fails
            quest_text = (
                f"{_('quest_failed')}\n\n"
                f"{_('fallback_quest')}\n\n"
                f"{_('what_will_you_do')}\n"
                f"{_('quest_options')}\n\n"
                f"{_('quest_hint')}"
            )
        
        await message.answer(quest_text, parse_mode="Markdown")
        logger.info(f"User {message.from_user.id} requested a quest")
        
    except Exception as e:
        logger.error(f"Error in quest command: {e}")
        _ = message.get("_")
        await message.answer(
            f"{_('quest_error')}\n\n"
            f"{_('quest_error_message')}\n\n"
            f"{_('quest_error_hint')}"
        )

@router.message(Command("status"))
async def cmd_status(message: Message):
    """Handle the /status command - placeholder for future game status functionality."""
    _ = message.get("_")  # Get translation function
    
    status_text = (
        f"{_('game_status')}\n\n"
        f"{_('current_game')}\n"
        f"{_('player_level')}\n"
        f"{_('experience')}\n"
        f"{_('gold')}\n"
        f"{_('inventory')}\n\n"
        f"{_('under_development')}\n\n"
        f"{_('status_hint')}"
    )
    
    await message.answer(status_text, parse_mode="Markdown")
    logger.info(f"User {message.from_user.id} requested game status")
