from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.services.openai_service import OpenAIService
from app.services.logging_service import get_logger

router = Router()
logger = get_logger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle the /start command - greet player and introduce the RPG world."""
    try:
        user_name = message.from_user.first_name or "Adventurer"
        
        # Generate world description using OpenAI
        world_description = await OpenAIService.generate_world_description()
        
        if world_description:
            welcome_text = (
                f"🎮 Welcome to the Fantasy RPG Adventure, {user_name}!\n\n"
                f"🌍 {world_description}\n\n"
                f"⚔️ Adventure awaits! Here are your available commands:\n"
                f"• /start - Show this welcome message\n"
                f"• /quest - Generate a new quest\n"
                f"• /help - Show all commands\n"
                f"• /language - Change language\n\n"
                f"🚀 Are you ready for an epic adventure?"
            )
        else:
            # Fallback if OpenAI fails
            welcome_text = (
                f"🎮 Welcome to the Fantasy RPG Adventure, {user_name}!\n\n"
                f"🌍 Embark on epic quests in a medieval fantasy world!\n\n"
                f"⚔️ Adventure awaits! Here are your available commands:\n"
                f"• /start - Show this welcome message\n"
                f"• /quest - Generate a new quest\n"
                f"• /help - Show all commands\n"
                f"• /language - Change language\n\n"
                f"🚀 Are you ready for an epic adventure?"
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
    help_text = (
        "📚 **FANTASY RPG ADVENTURE BOT - HELP**\n\n"
        "🎮 **GAME COMMANDS:**\n"
        "• /start - Welcome message and game introduction\n"
        "• /quest - Generate AI-powered quests\n"
        "• /help - Show this help message\n"
        "• /language - Change language (English/Ukrainian)\n\n"
        "🌍 **ABOUT THE GAME:**\n"
        "Embark on epic quests in a medieval fantasy world! Each quest is uniquely generated using AI to provide endless adventures.\n\n"
        "🚀 **GETTING STARTED:**\n"
        "1. Use /start to begin your journey\n"
        "2. Use /quest to get your first quest\n"
        "3. Complete quests and level up\n"
        "4. Explore the fantasy world!\n\n"
        "⚔️ **ADVENTURE AWAITS!**"
    )
    
    await message.answer(help_text, parse_mode="Markdown")
    logger.info("User requested help", 
               user_id=message.from_user.id,
               user_name=message.from_user.first_name,
               chat_id=message.chat.id)
