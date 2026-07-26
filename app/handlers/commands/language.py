from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.handlers.menu import build_main_menu_kb
from app.services.i18n_service import i18n_service
from app.services.logging_service import get_logger

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
    await callback.answer()
    try:
        user_id = callback.from_user.id
        lang_code = callback.data.split("_")[1]
        i18n_service.set_user_language(user_id, lang_code)
        lang_name = i18n_service.get_language_name(lang_code)

        await callback.message.edit_text(
            i18n_service.get_text(user_id, 'language_changed', language=lang_name) + "\n\n" +
            i18n_service.get_text(user_id, 'menu.title'),
            reply_markup=build_main_menu_kb(user_id),
            parse_mode="Markdown"
        )

        logger.info("User changed language", user_id=user_id, language_code=lang_code)

    except Exception as e:
        logger.error("Error in language callback", user_id=callback.from_user.id,
                     error_type=type(e).__name__, error_message=str(e))
