from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from app.services.logging_service import get_logger
from app.services.i18n_service import i18n_service

router = Router()
logger = get_logger(__name__)

@router.message(Command("language"))
async def cmd_language(message: Message):
    """Handle the /language command - show language selection."""
    try:
        user_id = message.from_user.id
        
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
            i18n_service.get_text(user_id, 'choose_language'),
            reply_markup=keyboard
        )
        
        logger.info("User requested language selection", 
                   user_id=message.from_user.id,
                   user_name=message.from_user.first_name,
                   chat_id=message.chat.id)
        
    except Exception as e:
        logger.error("Error in language command", 
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        # Fallback message
        await message.answer("🌍 Please choose your language: /language")

@router.callback_query(F.data.startswith("lang_"))
async def handle_language_callback(callback: CallbackQuery):
    """Handle language selection callback."""
    try:
        user_id = callback.from_user.id
        
        # Extract language code from callback data
        lang_code = callback.data.split("_")[1]
        
        # Set user language
        i18n_service.set_user_language(user_id, lang_code)
        
        # Get language name for display
        lang_name = i18n_service.get_language_name(lang_code)
        
        # Send confirmation message
        await callback.message.edit_text(
            i18n_service.get_text(user_id, 'language_changed', language=lang_name)
        )
        
        logger.info("User changed language", 
                   user_id=callback.from_user.id,
                   user_name=callback.from_user.first_name,
                   chat_id=callback.message.chat.id,
                   language_code=lang_code,
                   language_name=lang_name)
        
    except Exception as e:
        logger.error("Error in language callback", 
                    user_id=callback.from_user.id,
                    chat_id=callback.message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await callback.answer("❌ Error changing language")
    
    # Answer callback to remove loading state
    await callback.answer()
