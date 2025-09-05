"""
Character creation and management commands for the Telegram RPG game bot.
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
from app.models.character import CharacterClass, CharacterProgression
from app.services.i18n_service import i18n_service
from app.services.logging_service import get_logger

logger = get_logger(__name__)
router = Router()


class CharacterCreationStates(StatesGroup):
    """States for character creation flow."""
    WAITING_FOR_NAME = State()
    WAITING_FOR_CLASS = State()
    CONFIRMING_CREATION = State()


class CharacterManagementStates(StatesGroup):
    """States for character management."""
    VIEWING_STATS = State()
    DISTRIBUTING_POINTS = State()


@router.message(Command("create_character"))
async def cmd_create_character(message: Message, state: FSMContext, db_session: AsyncSession):
    """Start character creation process."""
    user_id = message.from_user.id
    
    # Check if user already has a character
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer(i18n_service.get_text(user_id, 'character.errors.user_not_found'))
        return
    
    if user.player:
        await message.answer(i18n_service.get_text(user_id, 'character.errors.already_has_character'))
        return
    
    # Start character creation
    await state.set_state(CharacterCreationStates.WAITING_FOR_NAME)
    await message.answer(
        i18n_service.get_text(user_id, 'character.creation.welcome'),
        parse_mode="Markdown"
    )


@router.message(CharacterCreationStates.WAITING_FOR_NAME)
async def process_character_name(message: Message, state: FSMContext):
    """Process character name input."""
    user_id = message.from_user.id
    character_name = message.text.strip()
    
    if len(character_name) < 2 or len(character_name) > 20:
        await message.answer(i18n_service.get_text(user_id, 'character.creation.name_too_short'))
        return
    
    # Store name and show class selection
    await state.update_data(character_name=character_name)
    await state.set_state(CharacterCreationStates.WAITING_FOR_CLASS)
    
    # Create class selection keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.warrior'), 
                callback_data="class_warrior"
            ),
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.rogue'), 
                callback_data="class_rogue"
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.mage'), 
                callback_data="class_mage"
            ),
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.cleric'), 
                callback_data="class_cleric"
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.ranger'), 
                callback_data="class_ranger"
            )
        ]
    ])
    
    await message.answer(
        i18n_service.get_text(user_id, 'character.creation.class_selection', name=character_name) + '\n\n' +
        i18n_service.get_text(user_id, 'character.creation.class_descriptions.warrior') + '\n' +
        i18n_service.get_text(user_id, 'character.creation.class_descriptions.rogue') + '\n' +
        i18n_service.get_text(user_id, 'character.creation.class_descriptions.mage') + '\n' +
        i18n_service.get_text(user_id, 'character.creation.class_descriptions.cleric') + '\n' +
        i18n_service.get_text(user_id, 'character.creation.class_descriptions.ranger'),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("class_"), CharacterCreationStates.WAITING_FOR_CLASS)
async def process_character_class(callback: CallbackQuery, state: FSMContext):
    """Process character class selection."""
    class_name = callback.data.split("_")[1]
    character_class = CharacterClass(class_name)
    
    # Get character data
    data = await state.get_data()
    character_name = data["character_name"]
    
    # Get class description
    class_description = CharacterProgression.get_class_description(character_class)
    
    # Create confirmation keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=i18n_service.get_text(callback.from_user.id, 'btn.create_character'), 
                callback_data="confirm_creation"
            ),
            InlineKeyboardButton(
                text=i18n_service.get_text(callback.from_user.id, 'btn.cancel'), 
                callback_data="cancel_creation"
            )
        ]
    ])
    
    await callback.message.edit_text(
        i18n_service.get_text(callback.from_user.id, 'character.creation.summary', 
                             name=character_name, 
                             class_name=character_class.value.title(),
                             description=class_description),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await state.update_data(character_class=character_class)
    await state.set_state(CharacterCreationStates.CONFIRMING_CREATION)


@router.callback_query(F.data == "confirm_creation", CharacterCreationStates.CONFIRMING_CREATION)
async def confirm_character_creation(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Confirm and create the character."""
    data = await state.get_data()
    character_name = data["character_name"]
    character_class = data["character_class"]
    
    # Get user
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == callback.from_user.id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'character.errors.user_not_found'))
        return
    
    # Create player
    player = Player(
        user_id=user.id,
        character_name=character_name,
        character_class=character_class,
        level=1,
        experience=0,
        strength=10,
        agility=10,
        intelligence=10,
        vitality=10,
        luck=10,
        available_stat_points=0,
        health=60,  # 20 + 4*10
        max_health=60
    )
    
    # Apply class bonuses
    player.apply_class_bonuses(character_class)
    
    db_session.add(player)
    await db_session.commit()
    
    await callback.message.edit_text(
        i18n_service.get_text(callback.from_user.id, 'character.creation.created',
                             name=character_name, 
                             class_name=character_class.value.title()),
        parse_mode="Markdown"
    )
    
    await state.clear()


@router.callback_query(F.data == "cancel_creation")
async def cancel_character_creation(callback: CallbackQuery, state: FSMContext):
    """Cancel character creation."""
    await callback.message.edit_text(i18n_service.get_text(callback.from_user.id, 'character.creation.cancelled'))
    await state.clear()


@router.message(Command("character"))
async def cmd_character_stats(message: Message, db_session: AsyncSession):
    """Show character stats."""
    user_id = message.from_user.id
    
    # Get user and player
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await message.answer(
            i18n_service.get_text(user_id, 'character.stats.no_character'),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.create_character'), callback_data="start_creation")]
            ])
        )
        return
    
    player = user.player
    
    # Create stats display keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📊 View Stats", 
                callback_data="view_stats"
            ),
            InlineKeyboardButton(
                text="⬆️ Level Up", 
                callback_data="level_up"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎯 Distribute Points", 
                callback_data="distribute_points"
            )
        ]
    ])
    
    await message.answer(
        player.get_character_summary(),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "view_stats")
async def view_detailed_stats(callback: CallbackQuery, db_session: AsyncSession):
    """Show detailed character stats."""
    user_id = callback.from_user.id
    
    # Get user and player
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await callback.answer(i18n_service.get_text(user_id, 'character.errors.hero_not_found'))
        return
    
    player = user.player
    derived_stats = player.get_derived_stats()
    xp_current, xp_required = player.get_xp_progress()
    
    # Create detailed stats message
    stats_message = i18n_service.get_text(user_id, 'character.stats.detailed',
                                        name=player.character_name,
                                        level=player.level,
                                        class_name=player.get_character_class_name(),
                                        strength=player.strength,
                                        agility=player.agility,
                                        intelligence=player.intelligence,
                                        vitality=player.vitality,
                                        luck=player.luck,
                                        attack=derived_stats.attack,
                                        crit_chance=derived_stats.crit_chance,
                                        dodge=derived_stats.dodge,
                                        magic=derived_stats.magic,
                                        max_health=derived_stats.hp_max,
                                        health=player.health,
                                        experience=player.experience,
                                        xp_current=xp_current,
                                        xp_required=xp_required,
                                        available_points=player.available_stat_points,
                                        coins=player.coins,
                                        gems=player.gems,
                                        energy=player.energy,
                                        max_energy=player.max_energy)
    
    await callback.message.edit_text(
        stats_message,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "level_up")
async def handle_level_up(callback: CallbackQuery, db_session: AsyncSession):
    """Handle level up process."""
    user_id = callback.from_user.id
    
    # Get user and player
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await callback.answer(i18n_service.get_text(user_id, 'character.errors.hero_not_found'))
        return
    
    player = user.player
    
    if not player.can_level_up():
        await callback.answer(i18n_service.get_text(user_id, 'character.level_up.not_enough_xp'))
        return
    
    # Level up the player
    leveled_up = player.add_experience(0)  # Just check for level up
    
    if leveled_up:
        # Get level up bonuses
        if player.character_class:
            class_bonuses, distributable_points = CharacterProgression.get_level_up_bonuses(
                player.character_class, 1
            )
            
            # Apply class bonuses
            player.strength += class_bonuses.strength
            player.agility += class_bonuses.agility
            player.intelligence += class_bonuses.intelligence
            player.vitality += class_bonuses.vitality
            player.luck += class_bonuses.luck
            
            # Add distributable points
            player.available_stat_points += distributable_points
        
        await db_session.commit()
        
        await callback.message.edit_text(
            i18n_service.get_text(user_id, 'character.level_up.congratulations',
                                 level=player.level, points=player.available_stat_points),
            parse_mode="Markdown"
        )
    else:
        await callback.answer(i18n_service.get_text(user_id, 'character.level_up.no_level_up'))


@router.callback_query(F.data == "distribute_points")
async def start_point_distribution(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Start stat point distribution."""
    user_id = callback.from_user.id
    
    # Get user and player
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await callback.answer(i18n_service.get_text(user_id, 'character.errors.hero_not_found'))
        return
    
    player = user.player
    
    if player.available_stat_points <= 0:
        await callback.answer(i18n_service.get_text(user_id, 'character.stat_distribution.no_points'))
        return
    
    await state.set_state(CharacterManagementStates.DISTRIBUTING_POINTS)
    await state.update_data(player_id=player.id, available_points=player.available_stat_points)
    
    # Create point distribution keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.add_str'), callback_data="dist_str"),
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.add_agi'), callback_data="dist_agi")
        ],
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.add_int'), callback_data="dist_int"),
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.add_vit'), callback_data="dist_vit")
        ],
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.add_luk'), callback_data="dist_luk"),
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.confirm'), callback_data="confirm_dist")
        ],
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.cancel'), callback_data="cancel_dist")
        ]
    ])
    
    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'character.stat_distribution.title',
                             points=player.available_stat_points,
                             strength=player.strength,
                             agility=player.agility,
                             intelligence=player.intelligence,
                             vitality=player.vitality,
                             luck=player.luck),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("dist_"), CharacterManagementStates.DISTRIBUTING_POINTS)
async def distribute_stat_point(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Distribute a stat point."""
    stat_type = callback.data.split("_")[1]
    data = await state.get_data()
    available_points = data.get("available_points", 0)
    
    if available_points <= 0:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'character.stat_distribution.no_more_points'))
        return
    
    # Get player
    from sqlalchemy import select
    result = await db_session.execute(
        select(Player).where(Player.id == data["player_id"])
    )
    player = result.scalar_one_or_none()
    
    if not player:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'character.errors.player_not_found'))
        return
    
    # Distribute point
    success = False
    if stat_type == "str":
        success = player.distribute_stat_points(strength=1)
    elif stat_type == "agi":
        success = player.distribute_stat_points(agility=1)
    elif stat_type == "int":
        success = player.distribute_stat_points(intelligence=1)
    elif stat_type == "vit":
        success = player.distribute_stat_points(vitality=1)
    elif stat_type == "luk":
        success = player.distribute_stat_points(luck=1)
    
    if success:
        await db_session.commit()
        await state.update_data(available_points=player.available_stat_points)
        
        # Update keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.add_str'), callback_data="dist_str"),
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.add_agi'), callback_data="dist_agi")
            ],
            [
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.add_int'), callback_data="dist_int"),
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.add_vit'), callback_data="dist_vit")
            ],
            [
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.add_luk'), callback_data="dist_luk"),
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.confirm'), callback_data="confirm_dist")
            ],
            [
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.cancel'), callback_data="cancel_dist")
            ]
        ])
        
        await callback.message.edit_text(
            i18n_service.get_text(callback.from_user.id, 'character.stat_distribution.title',
                                 points=player.available_stat_points,
                                 strength=player.strength,
                                 agility=player.agility,
                                 intelligence=player.intelligence,
                                 vitality=player.vitality,
                                 luck=player.luck),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'character.stat_distribution.point_added', stat=stat_type.upper()))
    else:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'character.stat_distribution.failed_distribute'))


@router.callback_query(F.data == "confirm_dist", CharacterManagementStates.DISTRIBUTING_POINTS)
async def confirm_distribution(callback: CallbackQuery, state: FSMContext):
    """Confirm stat point distribution."""
    await callback.message.edit_text(
        i18n_service.get_text(callback.from_user.id, 'character.stat_distribution.success'),
        parse_mode="Markdown"
    )
    await state.clear()


@router.callback_query(F.data == "cancel_dist", CharacterManagementStates.DISTRIBUTING_POINTS)
async def cancel_distribution(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Cancel stat point distribution and revert changes."""
    data = await state.get_data()
    
    # Get player and revert changes (this is a simplified approach)
    from sqlalchemy import select
    result = await db_session.execute(
        select(Player).where(Player.id == data["player_id"])
    )
    player = result.scalar_one_or_none()
    
    if player:
        # Reset available points to original amount
        player.available_stat_points = data.get("available_points", 0)
        await db_session.commit()
    
    await callback.message.edit_text(i18n_service.get_text(callback.from_user.id, 'character.stat_distribution.cancelled'))
    await state.clear()


@router.callback_query(F.data == "start_creation")
async def start_creation_from_button(callback: CallbackQuery, state: FSMContext):
    """Start character creation from button press."""
    await state.set_state(CharacterCreationStates.WAITING_FOR_NAME)
    await callback.message.edit_text(
        i18n_service.get_text(callback.from_user.id, 'character.creation.welcome'),
        parse_mode="Markdown"
    )
