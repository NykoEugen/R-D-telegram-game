from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.i18n_service import i18n_service
from app.services.logging_service import get_logger

router = Router()
logger = get_logger(__name__)


def build_main_menu_kb(user_id: int) -> InlineKeyboardMarkup:
    t = lambda key: i18n_service.get_text(user_id, key)
    locale = i18n_service.get_user_language(user_id)
    city_label = "🏙 В місто" if locale == "uk" else "🏙 City"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=city_label, callback_data="city:return")],
        [InlineKeyboardButton(text=t('menu.quest'), callback_data="show_quests")],
        [
            InlineKeyboardButton(text=t('menu.hero'), callback_data="menu:hero"),
            InlineKeyboardButton(text=t('menu.settings'), callback_data="menu:settings"),
        ],
    ])


def build_hero_menu_kb(user_id: int) -> InlineKeyboardMarkup:
    t = lambda key: i18n_service.get_text(user_id, key)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t('menu.hero_stats'), callback_data="view_stats")],
        [
            InlineKeyboardButton(text=t('menu.heroes'), callback_data="menu:heroes"),
            InlineKeyboardButton(text=t('menu.create_hero'), callback_data="heroes_create_new"),
        ],
        [InlineKeyboardButton(text=t('menu.back'), callback_data="menu:main")],
    ])


def build_stats_kb(user_id: int, has_points: bool) -> InlineKeyboardMarkup:
    t = lambda key: i18n_service.get_text(user_id, key)
    rows = []
    if has_points:
        rows.append([InlineKeyboardButton(text=t('menu.distribute'), callback_data="distribute_points")])
    rows.append([InlineKeyboardButton(text=t('menu.back'), callback_data="menu:hero")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_settings_kb(user_id: int) -> InlineKeyboardMarkup:
    t = lambda key: i18n_service.get_text(user_id, key)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t('menu.language'), callback_data="menu:language")],
        [InlineKeyboardButton(text=t('menu.back'), callback_data="menu:main")],
    ])


def build_language_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_uk"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        ],
        [InlineKeyboardButton(
            text=i18n_service.get_text(user_id, 'menu.back'),
            callback_data="menu:settings"
        )],
    ])


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    user_id = message.from_user.id
    await message.answer(
        i18n_service.get_text(user_id, 'menu.title'),
        reply_markup=build_main_menu_kb(user_id),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "menu:main")
async def cb_menu_main(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'menu.title'),
        reply_markup=build_main_menu_kb(user_id),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "menu:settings")
async def cb_menu_settings(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'menu.settings_title'),
        reply_markup=build_settings_kb(user_id),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "menu:language")
async def cb_menu_language(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'choose_language'),
        reply_markup=build_language_kb(user_id),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "menu:hero")
async def cb_menu_hero(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'menu.hero_title'),
        reply_markup=build_hero_menu_kb(user_id),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "menu:heroes")
async def cb_menu_heroes(callback: CallbackQuery, db_session: AsyncSession):
    await callback.answer()
    from app.handlers.commands.heroes import _get_user, _heroes_keyboard_with_back
    user_id = callback.from_user.id
    user = await _get_user(db_session, user_id)

    if not user or not user.players:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'menu.create_hero'),
                callback_data="heroes_create_new"
            )],
            [InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'menu.back'),
                callback_data="menu:hero"
            )],
        ])
        await callback.message.edit_text(
            i18n_service.get_text(user_id, 'menu.no_hero'),
            reply_markup=kb,
            parse_mode="Markdown"
        )
        return

    players = sorted(user.players, key=lambda p: p.slot)
    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'heroes.list_title'),
        reply_markup=_heroes_keyboard_with_back(user_id, players, user_id),
        parse_mode="Markdown"
    )
