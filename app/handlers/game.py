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
        # Show typing indicator
        await message.answer("🔍 **Generating your quest...** 🔍", parse_mode="Markdown")
        
        # Generate quest description using OpenAI
        quest_description = await OpenAIService.generate_quest_description()
        
        if quest_description:
            quest_text = (
                "⚔️ **NEW QUEST RECEIVED!** ⚔️\n\n"
                f"📜 **Quest:** {quest_description}\n\n"
                "🎯 **What will you do?**\n"
                "• Accept the challenge?\n"
                "• Seek more information?\n"
                "• Prepare for battle?\n\n"
                "💡 *Use /quest again for another quest, or /help for more commands.*"
            )
        else:
            # Fallback if OpenAI fails
            quest_text = (
                "⚔️ **QUEST GENERATION FAILED** ⚔️\n\n"
                "📜 **Fallback Quest:** A mysterious artifact has been discovered in the ancient ruins. "
                "Local villagers speak of strange noises and glowing lights emanating from the depths. "
                "Will you investigate this ancient mystery?\n\n"
                "🎯 **What will you do?**\n"
                "• Accept the challenge?\n"
                "• Seek more information?\n"
                "• Prepare for battle?\n\n"
                "💡 *Use /quest again for another quest, or /help for more commands.*"
            )
        
        await message.answer(quest_text, parse_mode="Markdown")
        logger.info(f"User {message.from_user.id} requested a quest")
        
    except Exception as e:
        logger.error(f"Error in quest command: {e}")
        await message.answer(
            "❌ **Quest generation failed!** ❌\n\n"
            "Something went wrong while generating your quest. Please try again later.\n\n"
            "💡 *Use /help for available commands.*"
        )

@router.message(Command("status"))
async def cmd_status(message: Message):
    """Handle the /status command - placeholder for future game status functionality."""
    status_text = (
        "📊 **GAME STATUS** 📊\n\n"
        "🎮 **Current Game:** Fantasy RPG Adventure\n"
        "⚔️ **Player Level:** Coming Soon\n"
        "🏆 **Experience:** Coming Soon\n"
        "💰 **Gold:** Coming Soon\n"
        "🎒 **Inventory:** Coming Soon\n\n"
        "🚧 **Game features are under development!** 🚧\n\n"
        "💡 *Use /quest for adventures or /help for commands.*"
    )
    
    await message.answer(status_text, parse_mode="Markdown")
    logger.info(f"User {message.from_user.id} requested game status")
