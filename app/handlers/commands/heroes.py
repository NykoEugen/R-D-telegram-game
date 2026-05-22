"""
Multi-hero management commands (/heroes, /create_hero).
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.player import Player
from app.models.user import User
from app.models.character import CharacterClass, CharacterProgression
from app.services.repositories.player_repo import PlayerRepository
from app.services.i18n_service import i18n_service
from app.services.logging_service import get_logger

logger = get_logger(__name__)
router = Router()

MAX_HEROES = 3


class HeroesCreationStates(StatesGroup):
    WAITING_FOR_NAME = State()
    WAITING_FOR_CLASS = State()
    CONFIRMING_CREATION = State()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _heroes_keyboard_with_back(user_id: int, players: list, lang_user_id: int) -> InlineKeyboardMarkup:
    kb = _heroes_keyboard(user_id, players, lang_user_id)
    back_btn = InlineKeyboardButton(
        text=i18n_service.get_text(lang_user_id, 'menu.back'),
        callback_data="menu:hero"
    )
    kb.inline_keyboard.append([back_btn])
    return kb


def _heroes_keyboard(user_id: int, players: list, lang_user_id: int) -> InlineKeyboardMarkup:
    rows = []
    for p in players:
        active_badge = i18n_service.get_text(lang_user_id, 'heroes.active_badge') if p.is_active else ""
        slot_label = i18n_service.get_text(lang_user_id, 'heroes.slot', slot=p.slot)
        class_name = p.get_character_class_name()
        header = f"{slot_label} — {p.character_name} ({class_name}) Lv.{p.level}{active_badge}"
        rows.append([InlineKeyboardButton(text=header, callback_data=f"heroes_noop")])
        rows.append([
            InlineKeyboardButton(
                text=i18n_service.get_text(lang_user_id, 'heroes.btn_select'),
                callback_data=f"hero:select:{p.id}"
            ),
            InlineKeyboardButton(
                text=i18n_service.get_text(lang_user_id, 'heroes.btn_delete'),
                callback_data=f"hero:delete:{p.id}"
            ),
        ])

    if len(players) < MAX_HEROES:
        rows.append([
            InlineKeyboardButton(
                text=i18n_service.get_text(lang_user_id, 'heroes.btn_create'),
                callback_data="heroes_create_new"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _get_user(db_session: AsyncSession, telegram_id: int) -> User | None:
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(selectinload(User.players))
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# /heroes
# ---------------------------------------------------------------------------

@router.message(Command("heroes"))
async def cmd_heroes(message: Message, db_session: AsyncSession):
    user_id = message.from_user.id
    user = await _get_user(db_session, user_id)

    if not user:
        await message.answer(i18n_service.get_text(user_id, 'hero.errors.user_not_found'))
        return

    players = user.players

    if not players:
        await message.answer(
            i18n_service.get_text(user_id, 'heroes.list_title') + "\n\n" +
            i18n_service.get_text(user_id, 'heroes.empty'),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=i18n_service.get_text(user_id, 'heroes.btn_create'),
                    callback_data="heroes_create_new"
                )
            ]]),
            parse_mode="Markdown"
        )
        return

    await message.answer(
        i18n_service.get_text(user_id, 'heroes.list_title'),
        reply_markup=_heroes_keyboard(user_id, players, user_id),
        parse_mode="Markdown"
    )


# ---------------------------------------------------------------------------
# /create_hero
# ---------------------------------------------------------------------------

@router.message(Command("create_hero"))
async def cmd_create_hero(message: Message, state: FSMContext, db_session: AsyncSession):
    user_id = message.from_user.id
    user = await _get_user(db_session, user_id)

    if not user:
        await message.answer(i18n_service.get_text(user_id, 'hero.errors.user_not_found'))
        return

    if len(user.players) >= MAX_HEROES:
        await message.answer(i18n_service.get_text(user_id, 'heroes.no_free_slots'))
        return

    await state.set_state(HeroesCreationStates.WAITING_FOR_NAME)
    await message.answer(
        i18n_service.get_text(user_id, 'hero.creation.welcome'),
        parse_mode="Markdown"
    )


# ---------------------------------------------------------------------------
# Button: create new hero from /heroes list
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "heroes_create_new")
async def cb_heroes_create_new(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await callback.answer()
    user_id = callback.from_user.id
    user = await _get_user(db_session, user_id)

    if not user:
        await callback.answer(i18n_service.get_text(user_id, 'hero.errors.user_not_found'))
        return

    if len(user.players) >= MAX_HEROES:
        await callback.answer(i18n_service.get_text(user_id, 'heroes.no_free_slots'), show_alert=True)
        return

    await state.set_state(HeroesCreationStates.WAITING_FOR_NAME)
    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'hero.creation.welcome'),
        parse_mode="Markdown"
    )


# ---------------------------------------------------------------------------
# No-op button (hero name header row)
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "heroes_noop")
async def cb_heroes_noop(callback: CallbackQuery):
    await callback.answer()


# ---------------------------------------------------------------------------
# FSM: name input
# ---------------------------------------------------------------------------

@router.message(HeroesCreationStates.WAITING_FOR_NAME)
async def mhero_process_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()

    if len(name) < 2 or len(name) > 20:
        await message.answer(i18n_service.get_text(user_id, 'hero.creation.name_too_short'))
        return

    await state.update_data(hero_name=name)
    await state.set_state(HeroesCreationStates.WAITING_FOR_CLASS)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.warrior'), callback_data="mhero_class_warrior"),
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.rogue'), callback_data="mhero_class_rogue"),
        ],
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.mage'), callback_data="mhero_class_mage"),
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.cleric'), callback_data="mhero_class_cleric"),
        ],
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.ranger'), callback_data="mhero_class_ranger"),
        ],
    ])

    await message.answer(
        i18n_service.get_text(user_id, 'hero.creation.class_selection', name=name) + "\n\n" +
        i18n_service.get_text(user_id, 'hero.creation.class_descriptions.warrior') + "\n" +
        i18n_service.get_text(user_id, 'hero.creation.class_descriptions.rogue') + "\n" +
        i18n_service.get_text(user_id, 'hero.creation.class_descriptions.mage') + "\n" +
        i18n_service.get_text(user_id, 'hero.creation.class_descriptions.cleric') + "\n" +
        i18n_service.get_text(user_id, 'hero.creation.class_descriptions.ranger'),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ---------------------------------------------------------------------------
# FSM: class selection
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("mhero_class_"), HeroesCreationStates.WAITING_FOR_CLASS)
async def mhero_process_class(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    class_raw = callback.data.split("_")[2]
    character_class = CharacterClass(class_raw)

    data = await state.get_data()
    hero_name = data["hero_name"]

    loc_class_name = i18n_service.get_text(user_id, f'hero.creation.class_names.{class_raw}')
    loc_description = i18n_service.get_text(user_id, f'hero.creation.class_full_descriptions.{class_raw}')
    class_bonus = CharacterProgression.CLASS_DEFINITIONS[character_class].starting_bonus

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=i18n_service.get_text(user_id, 'btn.create_hero'),
            callback_data="mhero_confirm"
        ),
        InlineKeyboardButton(
            text=i18n_service.get_text(user_id, 'btn.cancel'),
            callback_data="mhero_cancel"
        ),
    ]])

    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'hero.creation.summary',
                              name=hero_name,
                              class_name=loc_class_name,
                              description=loc_description,
                              strength=class_bonus.strength,
                              agility=class_bonus.agility,
                              intelligence=class_bonus.intelligence,
                              vitality=class_bonus.vitality,
                              luck=class_bonus.luck),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

    await state.update_data(character_class=class_raw)
    await state.set_state(HeroesCreationStates.CONFIRMING_CREATION)


# ---------------------------------------------------------------------------
# FSM: confirm creation
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "mhero_confirm", HeroesCreationStates.CONFIRMING_CREATION)
async def mhero_confirm(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await callback.answer()
    user_id = callback.from_user.id
    data = await state.get_data()
    hero_name = data["hero_name"]
    character_class = CharacterClass(data["character_class"])

    user = await _get_user(db_session, user_id)
    if not user:
        await callback.answer(i18n_service.get_text(user_id, 'hero.errors.user_not_found'))
        return

    if len(user.players) >= MAX_HEROES:
        await callback.answer(i18n_service.get_text(user_id, 'heroes.no_free_slots'), show_alert=True)
        await state.clear()
        return

    repo = PlayerRepository(db_session)
    player = await repo.create_player(
        user_id=user.id,
        character_name=hero_name,
        character_class=character_class,
        level=1,
        experience=0,
        strength=10,
        agility=10,
        intelligence=10,
        vitality=10,
        luck=10,
        available_stat_points=0,
        health=60,
        max_health=60,
    )
    player.apply_class_bonuses(character_class)
    await db_session.commit()
    await db_session.refresh(player)

    hp_max = 20 + 4 * player.vitality
    attack = 2 + player.strength
    magic = 2 + player.intelligence
    crit_chance = min(35.0, 5.0 + 0.5 * player.agility)
    dodge = min(25.0, 2.0 + 0.3 * player.agility)

    loc_class_name = i18n_service.get_text(user_id, f'hero.creation.class_names.{character_class.value}')

    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'hero.creation.created',
                              name=hero_name,
                              class_name=loc_class_name,
                              hp=hp_max,
                              attack=attack,
                              magic=magic,
                              crit_chance=crit_chance,
                              dodge=dodge),
        parse_mode="Markdown"
    )
    await state.clear()

    logger.info("Multi-hero created", user_id=user_id, hero_name=hero_name, slot=player.slot)

    from app.handlers.city import enter_city
    await enter_city(callback.message, state)


# ---------------------------------------------------------------------------
# FSM: cancel creation
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "mhero_cancel")
async def mhero_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    from app.handlers.menu import build_main_menu_kb
    user_id = callback.from_user.id
    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'hero.creation.cancelled') + "\n\n" +
        i18n_service.get_text(user_id, 'menu.title'),
        reply_markup=build_main_menu_kb(user_id),
        parse_mode="Markdown"
    )


# ---------------------------------------------------------------------------
# Callback: select active hero
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("hero:select:"))
async def cb_hero_select(callback: CallbackQuery, db_session: AsyncSession):
    await callback.answer()
    user_id = callback.from_user.id
    player_id = int(callback.data.split(":")[2])

    user = await _get_user(db_session, user_id)
    if not user:
        await callback.answer(i18n_service.get_text(user_id, 'hero.errors.user_not_found'))
        return

    repo = PlayerRepository(db_session)
    success = await repo.set_active_player(player_id, user.id)
    await db_session.commit()

    if not success:
        await callback.answer(i18n_service.get_text(user_id, 'hero.errors.hero_not_found'))
        return

    # Reload players
    await db_session.refresh(user)
    player = next((p for p in user.players if p.id == player_id), None)
    name = player.character_name if player else "?"

    # Refresh the heroes list
    await db_session.refresh(user)
    players = sorted(user.players, key=lambda p: p.slot)
    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'heroes.list_title'),
        reply_markup=_heroes_keyboard_with_back(user_id, players, user_id),
        parse_mode="Markdown"
    )


# ---------------------------------------------------------------------------
# Callback: delete hero — confirmation
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("hero:delete:") & ~F.data.startswith("hero:delete_confirmed:"))
async def cb_hero_delete_confirm(callback: CallbackQuery, db_session: AsyncSession):
    await callback.answer()
    user_id = callback.from_user.id
    player_id = int(callback.data.split(":")[2])

    user = await _get_user(db_session, user_id)
    if not user:
        await callback.answer(i18n_service.get_text(user_id, 'hero.errors.user_not_found'))
        return

    if len(user.players) <= 1:
        await callback.answer(
            i18n_service.get_text(user_id, 'heroes.cannot_delete_only'),
            show_alert=True
        )
        return

    player = next((p for p in user.players if p.id == player_id), None)
    if not player:
        await callback.answer(i18n_service.get_text(user_id, 'hero.errors.hero_not_found'))
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=i18n_service.get_text(user_id, 'heroes.btn_confirm_delete'),
            callback_data=f"hero:delete_confirmed:{player_id}"
        ),
        InlineKeyboardButton(
            text=i18n_service.get_text(user_id, 'heroes.btn_cancel'),
            callback_data="heroes_back"
        ),
    ]])

    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'heroes.confirm_delete', name=player.character_name),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ---------------------------------------------------------------------------
# Callback: delete hero — confirmed
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("hero:delete_confirmed:"))
async def cb_hero_delete(callback: CallbackQuery, db_session: AsyncSession):
    await callback.answer()
    user_id = callback.from_user.id
    player_id = int(callback.data.split(":")[2])

    user = await _get_user(db_session, user_id)
    if not user:
        await callback.answer(i18n_service.get_text(user_id, 'hero.errors.user_not_found'))
        return

    if len(user.players) <= 1:
        await callback.answer(
            i18n_service.get_text(user_id, 'heroes.cannot_delete_only'),
            show_alert=True
        )
        return

    player = next((p for p in user.players if p.id == player_id), None)
    if not player:
        await callback.answer(i18n_service.get_text(user_id, 'hero.errors.hero_not_found'))
        return

    name = player.character_name
    repo = PlayerRepository(db_session)
    await repo.hard_delete_player(player_id)
    await db_session.commit()

    # Reload and show updated list
    await db_session.refresh(user)
    players = sorted(user.players, key=lambda p: p.slot)

    text = i18n_service.get_text(user_id, 'heroes.hero_deleted', name=name) + "\n\n" + \
           i18n_service.get_text(user_id, 'heroes.list_title')

    if players:
        await callback.message.edit_text(
            text,
            reply_markup=_heroes_keyboard(user_id, players, user_id),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            text + "\n\n" + i18n_service.get_text(user_id, 'heroes.empty'),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=i18n_service.get_text(user_id, 'heroes.btn_create'),
                    callback_data="heroes_create_new"
                )
            ]]),
            parse_mode="Markdown"
        )

    logger.info("Hero deleted", user_id=user_id, player_id=player_id, name=name)


# ---------------------------------------------------------------------------
# Callback: back to heroes list
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "heroes_back")
async def cb_heroes_back(callback: CallbackQuery, db_session: AsyncSession):
    await callback.answer()
    user_id = callback.from_user.id
    user = await _get_user(db_session, user_id)

    if not user or not user.players:
        await callback.message.edit_text(
            i18n_service.get_text(user_id, 'heroes.list_title') + "\n\n" +
            i18n_service.get_text(user_id, 'heroes.empty'),
            parse_mode="Markdown"
        )
        return

    players = sorted(user.players, key=lambda p: p.slot)
    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'heroes.list_title'),
        reply_markup=_heroes_keyboard_with_back(user_id, players, user_id),
        parse_mode="Markdown"
    )
