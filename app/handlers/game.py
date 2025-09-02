from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.services.openai_service import OpenAIService
from app.services.logging_service import get_logger

router = Router()
logger = get_logger(__name__)

@router.message(Command("quest"))
async def cmd_quest(message: Message):
    """Handle the /quest command - generate and provide a new quest description."""
    try:
        # Show typing indicator
        await message.answer("⚔️ Generating your quest...", parse_mode="HTML")
        
        # Generate quest description using OpenAI
        quest_description = await OpenAIService.generate_quest_description()
        
        if quest_description:
            quest_text = (
                f"🗺️ **NEW QUEST GENERATED!**\n\n"
                f"📜 **Quest Description:**\n{quest_description}\n\n"
                f"🤔 **What will you do?**\n"
                f"• Accept the quest and begin your journey\n"
                f"• Ask for more details\n"
                f"• Request a different quest\n\n"
                f"💡 **Hint:** Use /quest again to generate a new quest!"
            )
        else:
            # Fallback if OpenAI fails
            quest_text = (
                f"🗺️ **QUEST GENERATION FAILED**\n\n"
                f"📜 **Fallback Quest:**\n"
                f"Journey to the ancient ruins of Eldoria and retrieve the Crystal of Wisdom. "
                f"Beware of the shadow creatures that lurk in the darkness.\n\n"
                f"🤔 **What will you do?**\n"
                f"• Accept the quest and begin your journey\n"
                f"• Ask for more details\n"
                f"• Request a different quest\n\n"
                f"💡 **Hint:** Use /quest again to generate a new quest!"
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
    status_text = (
        f"📊 **GAME STATUS**\n\n"
        f"🎮 **Current Game:** Fantasy RPG Adventure\n"
        f"👤 **Player Level:** 1\n"
        f"⭐ **Experience:** 0/100\n"
        f"💰 **Gold:** 10\n"
        f"🎒 **Inventory:** Empty\n\n"
        f"🚧 **Under Development**\n\n"
        f"💡 **Hint:** This feature is coming soon! For now, focus on completing quests."
    )
    
    await message.answer(status_text, parse_mode="Markdown")
    logger.info("User requested game status", 
               user_id=message.from_user.id,
               user_name=message.from_user.first_name,
               chat_id=message.chat.id)
