"""
Utility functions for handlers.
"""

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.services.i18n_service import i18n_service


async def check_hero_required(message: Message, db_session: AsyncSession) -> tuple[bool, User | None]:
    """
    Check if user has a hero. Returns (has_hero, user_object).
    If no hero, sends a message with creation options.
    """
    user_id = message.from_user.id
    
    # Get user with player relationship
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Please use /start first to register.")
        return False, None
    
    if not user.player:
        # User doesn't have a hero - show creation options
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎭 Create Hero", 
                    callback_data="create_hero"
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ About Heroes", 
                    callback_data="hero_info"
                )
            ]
        ])
        
        await message.answer(
            i18n_service.get_text(message.from_user.id, 'hero.required'),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return False, user
    
    return True, user


async def get_user_hero(user_id: int, db_session: AsyncSession) -> tuple[User | None, bool]:
    """
    Get user and check if they have a hero. Returns (user, has_hero).
    """
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return None, False
    
    return user, user.player is not None
