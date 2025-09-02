import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("language"))
async def cmd_language(message: Message):
    """Handle the /language command - show language selection."""
    try:
        # Get current language
        current_lang = message.get("get_user_language")()
        current_lang_name = "English" if current_lang == "en" else "Українська"
        
        # Create inline keyboard for language selection
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇺🇸 English",
                    callback_data="lang_en"
                ),
                InlineKeyboardButton(
                    text="🇺🇦 Українська",
                    callback_data="lang_uk"
                )
            ]
        ])
        
        # Send language selection message
        await message.answer(
            message.get("_")("choose_language"),
            reply_markup=keyboard
        )
        
        logger.info(f"User {message.from_user.id} requested language selection")
        
    except Exception as e:
        logger.error(f"Error in language command: {e}")
        # Fallback message
        await message.answer("🌍 Please choose your language: /language")

@router.callback_query(F.data.startswith("lang_"))
async def handle_language_callback(callback: CallbackQuery):
    """Handle language selection callback."""
    try:
        # Extract language code from callback data
        lang_code = callback.data.split("_")[1]
        
        # Set user language
        callback.message.get("set_user_language")(lang_code)
        
        # Get language name for display
        lang_name = "English" if lang_code == "en" else "Українська"
        
        # Send confirmation message
        await callback.message.edit_text(
            callback.message.get("_")("language_changed", language=lang_name)
        )
        
        logger.info(f"User {callback.from_user.id} changed language to: {lang_code}")
        
    except Exception as e:
        logger.error(f"Error in language callback: {e}")
        await callback.answer("❌ Error changing language")
    
    # Answer callback to remove loading state
    await callback.answer()
