import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.services.openai_service import OpenAIService
from app.config import Config

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle the /start command - greet player and introduce the RPG world."""
    try:
        user_name = message.from_user.first_name or "Adventurer"
        
        # Generate world description using OpenAI
        world_description = await OpenAIService.generate_world_description()
        
        if world_description:
            welcome_text = (
                f"🎮 **Welcome to {Config.GAME_NAME}, {user_name}!** 🎮\n\n"
                f"🌍 **The World:** {world_description}\n\n"
                f"⚔️ **Your Adventure Awaits!** ⚔️\n\n"
                f"**Available Commands:**\n"
                f"• /start - Show this welcome message\n"
                f"• /quest - Get a new quest\n"
                f"• /help - Show help information\n\n"
                f"Ready to embark on your epic journey? Use /quest to begin your first adventure!"
            )
        else:
            # Fallback if OpenAI fails
            welcome_text = (
                f"🎮 **Welcome to {Config.GAME_NAME}, {user_name}!** 🎮\n\n"
                f"🌍 **The World:** {Config.GAME_DESCRIPTION}\n\n"
                f"⚔️ **Your Adventure Awaits!** ⚔️\n\n"
                f"**Available Commands:**\n"
                f"• /start - Show this welcome message\n"
                f"• /quest - Get a new quest\n"
                f"• /help - Show help information\n\n"
                f"Ready to embark on your epic journey? Use /quest to begin your first adventure!"
            )
        
        await message.answer(welcome_text, parse_mode="Markdown")
        logger.info(f"User {message.from_user.id} started the bot")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer(
            "🎮 Welcome to Fantasy RPG Adventure! 🎮\n\n"
            "Something went wrong with the world generation, but your adventure awaits!\n"
            "Use /quest to begin your journey!"
        )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle the /help command - show available commands and game information."""
    help_text = (
        f"🎮 **{Config.GAME_NAME} - Help** 🎮\n\n"
        f"**Game Commands:**\n"
        f"• /start - Welcome message and world introduction\n"
        f"• /quest - Get a new quest description\n"
        f"• /help - Show this help message\n\n"
        f"**About the Game:**\n"
        f"This is a text-based RPG where you'll receive quests and embark on adventures in a medieval fantasy world.\n\n"
        f"**Getting Started:**\n"
        f"1. Use /start to begin your journey\n"
        f"2. Use /quest to receive your first quest\n"
        f"3. More game features coming soon!\n\n"
        f"⚔️ **May your adventures be legendary!** ⚔️"
    )
    
    await message.answer(help_text, parse_mode="Markdown")
    logger.info(f"User {message.from_user.id} requested help")
