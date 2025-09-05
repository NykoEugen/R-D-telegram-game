"""
Hero creation and selection handlers for the Telegram RPG game bot.

This module provides streamlined hero creation and management functionality.
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
from app.services.i18n_service import i18n_service
from app.services.logging_service import get_logger
from app.services.fsm_service import FSMStateService

logger = get_logger(__name__)
router = Router()


class HeroCreationStates(StatesGroup):
    """States for hero creation flow."""
    WAITING_FOR_NAME = State()
    WAITING_FOR_CLASS = State()
    CONFIRMING_CREATION = State()


class HeroSelectionStates(StatesGroup):
    """States for hero selection flow."""
    SELECTING_HERO = State()
    VIEWING_HERO_DETAILS = State()


@router.message(Command("hero"))
async def cmd_hero_menu(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Main hero menu - create new or manage existing hero."""
    try:
        user_id = message.from_user.id
        
        # Get user with player relationship
        result = await db_session.execute(
            select(User)
            .where(User.telegram_id == user_id)
            .options(selectinload(User.player))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(i18n_service.get_text(user_id, 'hero.errors.user_not_found'))
            return
        
        # Hero menu displayed
        
        # Check if user has a hero
        if user.player:
            # User has a hero - show management options
            await show_hero_management_menu(message, user.player)
        else:
            # User doesn't have a hero - show creation options
            await show_hero_creation_menu(message)
        
        logger.info("Showed hero menu", 
                   user_id=user_id,
                   has_hero=bool(user.player),
                   chat_id=message.chat.id)
        
    except Exception as e:
        logger.error("Error in cmd_hero_menu", 
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.answer(
            i18n_service.get_text(message.from_user.id, 'hero.errors.menu_error')
        )


async def show_hero_creation_menu(message: Message, user_id: int = None):
    """Show hero creation menu."""
    if user_id is None:
        user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.create_new_hero'), 
                callback_data="create_hero"
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.about_heroes'), 
                callback_data="hero_info"
            )
        ]
    ])
    
    await message.answer(
        i18n_service.get_text(user_id, 'hero.management.no_hero_menu'),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def show_hero_management_menu(message: Message, player: Player, user_id: int = None):
    """Show hero management menu for existing heroes."""
    if user_id is None:
        user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.view_hero'), 
                callback_data="view_hero"
            ),
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.hero_stats'), 
                callback_data="hero_stats"
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.level_up'), 
                callback_data="hero_level_up"
            ),
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.distribute_points'), 
                callback_data="hero_distribute"
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.create_new_hero'), 
                callback_data="create_new_hero"
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n_service.get_text(user_id, 'btn.exit_menu'), 
                callback_data="exit_hero_menu"
            )
        ]
    ])
    
    class_name = player.get_character_class_name()
    
    await message.answer(
        i18n_service.get_text(user_id, 'hero.management.has_hero_menu',
                             hero_name=player.character_name, 
                             hero_class=class_name,
                             level=player.level,
                             experience=player.experience),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "create_hero")
async def start_hero_creation(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Start hero creation process."""
    try:
        user_id = callback.from_user.id
        
        # Set FSM state to hero creation
        await state.set_state(HeroCreationStates.WAITING_FOR_NAME)
        
        await callback.message.edit_text(
            i18n_service.get_text(user_id, 'hero.creation.welcome'),
            parse_mode="Markdown"
        )
        
        logger.info("Started hero creation process", 
                   user_id=user_id,
                   chat_id=callback.message.chat.id)
        
    except Exception as e:
        logger.error('Error in start_hero_creation', 
                    user_id=callback.from_user.id,
                    chat_id=callback.message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await callback.message.edit_text(
            i18n_service.get_text(callback.from_user.id, 'hero.errors.creation_error')
        )


@router.callback_query(F.data == "create_new_hero")
async def start_new_hero_creation(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Start creation of a new hero (replacing existing one)."""
    try:
        user_id = callback.from_user.id
        
        # Set FSM state to hero creation
        await state.set_state(HeroCreationStates.WAITING_FOR_NAME)
        
        await callback.message.edit_text(
            i18n_service.get_text(user_id, 'hero.creation.new_hero_warning'),
            parse_mode="Markdown"
        )
        
        logger.info("Started new hero creation process", 
                   user_id=user_id,
                   chat_id=callback.message.chat.id)
        
    except Exception as e:
        logger.error('Error in start_new_hero_creation', 
                    user_id=callback.from_user.id,
                    chat_id=callback.message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await callback.message.edit_text(
            i18n_service.get_text(callback.from_user.id, 'hero.errors.creation_error')
        )


@router.message(HeroCreationStates.WAITING_FOR_NAME)
async def process_hero_name(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Process hero name input."""
    try:
        user_id = message.from_user.id
        hero_name = message.text.strip()
        
        if len(hero_name) < 2 or len(hero_name) > 20:
            await message.answer(i18n_service.get_text(user_id, 'hero.creation.name_too_short'))
            return
        
        # Store name and show class selection
        await state.update_data(hero_name=hero_name)
        await state.set_state(HeroCreationStates.WAITING_FOR_CLASS)
        
        # Create class selection keyboard with descriptions
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n_service.get_text(user_id, 'btn.warrior'), 
                    callback_data="hero_class_warrior"
                ),
                InlineKeyboardButton(
                    text=i18n_service.get_text(user_id, 'btn.rogue'), 
                    callback_data="hero_class_rogue"
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n_service.get_text(user_id, 'btn.mage'), 
                    callback_data="hero_class_mage"
                ),
                InlineKeyboardButton(
                    text=i18n_service.get_text(user_id, 'btn.cleric'), 
                    callback_data="hero_class_cleric"
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n_service.get_text(user_id, 'btn.ranger'), 
                    callback_data="hero_class_ranger"
                )
            ]
        ])
        
        await message.answer(
            i18n_service.get_text(user_id, 'hero.creation.class_selection', name=hero_name) + "\n\n" +
            i18n_service.get_text(user_id, 'hero.creation.class_descriptions.warrior') + "\n" +
            i18n_service.get_text(user_id, 'hero.creation.class_descriptions.rogue') + "\n" +
            i18n_service.get_text(user_id, 'hero.creation.class_descriptions.mage') + "\n" +
            i18n_service.get_text(user_id, 'hero.creation.class_descriptions.cleric') + "\n" +
            i18n_service.get_text(user_id, 'hero.creation.class_descriptions.ranger'),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        logger.info("Hero name processed, showing class selection", 
                   user_id=user_id,
                   hero_name=hero_name,
                   chat_id=message.chat.id)
        
    except Exception as e:
        logger.error('Error in process_hero_name', 
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.answer(
            i18n_service.get_text(message.from_user.id, 'hero.errors.name_processing_error')
        )


@router.callback_query(F.data.startswith("hero_class_"), HeroCreationStates.WAITING_FOR_CLASS)
async def process_hero_class(callback: CallbackQuery, state: FSMContext):
    """Process hero class selection."""
    class_name = callback.data.split("_")[2]  # hero_class_warrior -> warrior
    character_class = CharacterClass(class_name)
    
    # Get hero data
    data = await state.get_data()
    hero_name = data["hero_name"]
    
    # Get class description and bonuses
    class_description = CharacterProgression.get_class_description(character_class)
    class_bonus = CharacterProgression.CLASS_DEFINITIONS[character_class].starting_bonus
    
    # Create confirmation keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=i18n_service.get_text(callback.from_user.id, 'btn.create_hero'), 
                callback_data="confirm_hero_creation"
            ),
            InlineKeyboardButton(
                text=i18n_service.get_text(callback.from_user.id, 'btn.cancel'), 
                callback_data="cancel_hero_creation"
            )
        ]
    ])
    
    await callback.message.edit_text(
        i18n_service.get_text(callback.from_user.id, 'hero.creation.summary',
                             name=hero_name,
                             class_name=character_class.value.title(),
                             description=class_description,
                             strength=class_bonus.strength,
                             agility=class_bonus.agility,
                             intelligence=class_bonus.intelligence,
                             vitality=class_bonus.vitality,
                             luck=class_bonus.luck),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await state.update_data(character_class=character_class)
    await state.set_state(HeroCreationStates.CONFIRMING_CREATION)


@router.callback_query(F.data == "confirm_hero_creation", HeroCreationStates.CONFIRMING_CREATION)
async def confirm_hero_creation(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Confirm and create the hero."""
    try:
        user_id = callback.from_user.id
        data = await state.get_data()
        hero_name = data["hero_name"]
        character_class = data["character_class"]
        
        # Get user with player relationship
        result = await db_session.execute(
            select(User)
            .where(User.telegram_id == user_id)
            .options(selectinload(User.player))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer(i18n_service.get_text(user_id, 'hero.errors.user_not_found'))
            return
        
        # Check if user already has a player (for replacement)
        from app.models.player import Player
        existing_player_result = await db_session.execute(
            select(Player).where(Player.user_id == user.id)
        )
        existing_player = existing_player_result.scalar_one_or_none()
        
        if existing_player:
            # Delete existing player
            await db_session.delete(existing_player)
            await db_session.commit()
        
        # Create new player
        player = Player(
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
            health=60,  # 20 + 4*10
            max_health=60
        )
    
        # Apply class bonuses
        player.apply_class_bonuses(character_class)
        
        db_session.add(player)
        await db_session.commit()
        await db_session.refresh(player)  # Refresh the player object after commit
        
        # Calculate basic stats for display (avoid potential async issues)
        hp_max = 20 + 4 * player.vitality
        attack = 2 + player.strength
        magic = 2 + player.intelligence
        crit_chance = min(35.0, 5.0 + 0.5 * player.agility)
        dodge = min(25.0, 2.0 + 0.3 * player.agility)
        
        # Create keyboard with quest options
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n_service.get_text(user_id, 'btn.start_quest'), 
                    callback_data="start_quest"
                ),
                InlineKeyboardButton(
                    text=i18n_service.get_text(user_id, 'btn.adventure'), 
                    callback_data="start_adventure"
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n_service.get_text(user_id, 'btn.view_hero'), 
                    callback_data="view_hero"
                ),
                InlineKeyboardButton(
                    text=i18n_service.get_text(user_id, 'btn.main_menu'), 
                    callback_data="back_to_start"
                )
            ]
        ])
        
        await callback.message.edit_text(
            i18n_service.get_text(user_id, 'hero.creation.created',
                                 name=hero_name,
                                 class_name=character_class.value.title(),
                                 hp=hp_max,
                                 attack=attack,
                                 magic=magic,
                                 crit_chance=crit_chance,
                                 dodge=dodge),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        await state.clear()
        
        # Hero creation completed successfully
        
        logger.info("Hero created successfully", 
                   user_id=user_id,
                   hero_name=hero_name,
                   character_class=character_class.value,
                   chat_id=callback.message.chat.id)
        
    except Exception as e:
        logger.error("Error in confirm_hero_creation", 
                    user_id=callback.from_user.id,
                    chat_id=callback.message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await callback.message.edit_text(
            i18n_service.get_text(callback.from_user.id, 'hero.errors.creation_failed')
        )


@router.callback_query(F.data == "cancel_hero_creation")
async def cancel_hero_creation(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Cancel hero creation."""
    try:
        user_id = callback.from_user.id
        
        # Clear FSM state
        await state.clear()
        
        await callback.message.edit_text(i18n_service.get_text(user_id, 'hero.creation.cancelled'))
        
        logger.info("Hero creation cancelled", 
                   user_id=user_id,
                   chat_id=callback.message.chat.id)
        
    except Exception as e:
        logger.error("Error in cancel_hero_creation", 
                    user_id=callback.from_user.id,
                    chat_id=callback.message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await callback.message.edit_text(i18n_service.get_text(callback.from_user.id, 'hero.creation.cancelled'))


@router.callback_query(F.data == "view_hero")
async def view_hero_details(callback: CallbackQuery, db_session: AsyncSession):
    """View detailed hero information."""
    user_id = callback.from_user.id
    
    # Get user and player
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.errors.hero_not_found'))
        return
    
    player = user.player
    derived_stats = player.get_derived_stats()
    xp_current, xp_required = player.get_xp_progress()
    
    # Create detailed hero display
    hero_message = i18n_service.get_text(user_id, 'hero.stats.detailed',
                                        name=player.character_name,
                                        class_name=player.get_character_class_name(),
                                        level=player.level,
                                        experience=player.experience,
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
                                        xp_current=xp_current,
                                        xp_required=xp_required,
                                        available_points=player.available_stat_points,
                                        coins=player.coins,
                                        gems=player.gems,
                                        energy=player.energy,
                                        max_energy=player.max_energy)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.back_to_menu'), callback_data="back_to_hero_menu")
        ]
    ])
    
    await callback.message.edit_text(
        hero_message,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "hero_stats")
async def show_hero_stats(callback: CallbackQuery, db_session: AsyncSession):
    """Show hero stats in a compact format."""
    user_id = callback.from_user.id
    
    # Get user and player
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.errors.hero_not_found'))
        return
    
    player = user.player
    derived_stats = player.get_derived_stats()
    xp_current, xp_required = player.get_xp_progress()
    
    # Create compact stats display
    stats_message = i18n_service.get_text(user_id, 'hero.stats.compact',
                                        name=player.character_name,
                                        level=player.level,
                                        class_name=player.get_character_class_name(),
                                        strength=player.strength,
                                        agility=player.agility,
                                        intelligence=player.intelligence,
                                        vitality=player.vitality,
                                        luck=player.luck,
                                        attack=derived_stats.attack,
                                        magic=derived_stats.magic,
                                        crit_chance=derived_stats.crit_chance,
                                        dodge=derived_stats.dodge,
                                        xp_current=xp_current,
                                        xp_required=xp_required,
                                        available_points=player.available_stat_points,
                                        health=player.health,
                                        max_health=derived_stats.hp_max,
                                        energy=player.energy,
                                        max_energy=player.max_energy)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.back_to_menu'), callback_data="back_to_hero_menu")
        ]
    ])
    
    await callback.message.edit_text(
        stats_message,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "hero_level_up")
async def handle_hero_level_up(callback: CallbackQuery, db_session: AsyncSession):
    """Handle hero level up process."""
    user_id = callback.from_user.id
    
    # Get user and player
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.errors.hero_not_found'))
        return
    
    player = user.player
    
    if not player.can_level_up():
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.errors.not_enough_xp'))
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
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.back_to_menu'), callback_data="back_to_hero_menu")
            ]
        ])
        
        await callback.message.edit_text(
            i18n_service.get_text(user_id, 'hero.level_up.congratulations',
                                 name=player.character_name,
                                 level=player.level,
                                 points=player.available_stat_points),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.errors.no_level_up'))


@router.callback_query(F.data == "hero_distribute")
async def start_hero_point_distribution(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Start stat point distribution for hero."""
    user_id = callback.from_user.id
    
    # Get user and player
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.errors.hero_not_found'))
        return
    
    player = user.player
    
    if player.available_stat_points <= 0:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.errors.no_points'))
        return
    
    await state.set_state(HeroSelectionStates.VIEWING_HERO_DETAILS)
    await state.update_data(player_id=player.id, available_points=player.available_stat_points)
    
    # Create point distribution keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.add_str'), callback_data="hero_dist_str"),
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.add_agi'), callback_data="hero_dist_agi")
        ],
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.add_int'), callback_data="hero_dist_int"),
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.add_vit'), callback_data="hero_dist_vit")
        ],
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.add_luk'), callback_data="hero_dist_luk"),
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.confirm'), callback_data="hero_confirm_dist")
        ],
        [
            InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.cancel'), callback_data="hero_cancel_dist")
        ]
    ])
    
    await callback.message.edit_text(
        i18n_service.get_text(user_id, 'hero.stat_distribution.title',
                             points=player.available_stat_points,
                             strength=player.strength,
                             agility=player.agility,
                             intelligence=player.intelligence,
                             vitality=player.vitality,
                             luck=player.luck),
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("hero_dist_"), HeroSelectionStates.VIEWING_HERO_DETAILS)
async def distribute_hero_stat_point(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Distribute a stat point for hero."""
    stat_type = callback.data.split("_")[2]  # hero_dist_str -> str
    data = await state.get_data()
    available_points = data.get("available_points", 0)
    
    if available_points <= 0:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.errors.no_more_points'))
        return
    
    # Get player
    result = await db_session.execute(
        select(Player).where(Player.id == data["player_id"])
    )
    player = result.scalar_one_or_none()
    
    if not player:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.errors.hero_not_found'))
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
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.add_str'), callback_data="hero_dist_str"),
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.add_agi'), callback_data="hero_dist_agi")
            ],
            [
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.add_int'), callback_data="hero_dist_int"),
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.add_vit'), callback_data="hero_dist_vit")
            ],
            [
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.add_luk'), callback_data="hero_dist_luk"),
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.confirm'), callback_data="hero_confirm_dist")
            ],
            [
                InlineKeyboardButton(text=i18n_service.get_text(callback.from_user.id, 'btn.cancel'), callback_data="hero_cancel_dist")
            ]
        ])
        
        await callback.message.edit_text(
            i18n_service.get_text(callback.from_user.id, 'hero.stat_distribution.title',
                                 points=player.available_stat_points,
                                 strength=player.strength,
                                 agility=player.agility,
                                 intelligence=player.intelligence,
                                 vitality=player.vitality,
                                 luck=player.luck),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.stat_distribution.point_added', stat=stat_type.upper()))
    else:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.errors.failed_distribute'))


@router.callback_query(F.data == "hero_confirm_dist", HeroSelectionStates.VIEWING_HERO_DETAILS)
async def confirm_hero_distribution(callback: CallbackQuery, state: FSMContext):
    """Confirm stat point distribution for hero."""
    await callback.message.edit_text(
        i18n_service.get_text(callback.from_user.id, 'hero.stat_distribution.success'),
        parse_mode="Markdown"
    )
    await state.clear()


@router.callback_query(F.data == "hero_cancel_dist", HeroSelectionStates.VIEWING_HERO_DETAILS)
async def cancel_hero_distribution(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Cancel stat point distribution and revert changes for hero."""
    data = await state.get_data()
    
    # Get player and revert changes (this is a simplified approach)
    result = await db_session.execute(
        select(Player).where(Player.id == data["player_id"])
    )
    player = result.scalar_one_or_none()
    
    if player:
        # Reset available points to original amount
        player.available_stat_points = data.get("available_points", 0)
        await db_session.commit()
    
    await callback.message.edit_text(i18n_service.get_text(callback.from_user.id, 'hero.stat_distribution.cancelled'))
    await state.clear()


@router.callback_query(F.data == "hero_info")
async def show_hero_info(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Show information about heroes and classes."""
    try:
        user_id = callback.from_user.id
        
        # Hero info displayed
        
        info_message = i18n_service.get_text(user_id, 'hero.info.title') + "\n\n" + i18n_service.get_text(user_id, 'hero.info.description')
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n_service.get_text(user_id, 'btn.create_hero'), callback_data="create_hero")
            ]
        ])
        
        await callback.message.edit_text(
            info_message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        logger.info("Showed hero info", 
                   user_id=user_id,
                   chat_id=callback.message.chat.id)
        
    except Exception as e:
        logger.error("Error in show_hero_info", 
                    user_id=callback.from_user.id,
                    chat_id=callback.message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await callback.message.edit_text(
            i18n_service.get_text(callback.from_user.id, 'hero.errors.info_error')
        )


@router.callback_query(F.data == "back_to_hero_menu")
async def back_to_hero_menu(callback: CallbackQuery, db_session: AsyncSession):
    """Return to hero menu."""
    user_id = callback.from_user.id
    
    # Get user
    result = await db_session.execute(
        select(User)
        .where(User.telegram_id == user_id)
        .options(selectinload(User.player))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer(i18n_service.get_text(callback.from_user.id, 'hero.errors.user_not_found'))
        return
    
    if user.player:
        await show_hero_management_menu(callback.message, user.player, user_id)
    else:
        await show_hero_creation_menu(callback.message, user_id)


@router.callback_query(F.data == "exit_hero_menu")
async def exit_hero_menu(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Exit hero menu and return to start menu."""
    # Import here to avoid circular imports
    from app.handlers.commands.start import cmd_start
    
    # Create a fake message object for the start command
    class FakeMessage:
        def __init__(self, callback_query):
            self.from_user = callback_query.from_user
            self.chat = callback_query.message.chat
            self.message_id = callback_query.message.message_id
            self.date = callback_query.message.date
        
        async def answer(self, text, **kwargs):
            await callback.message.edit_text(text, **kwargs)
    
    fake_message = FakeMessage(callback)
    await cmd_start(fake_message, state, db_session, fsm_service)


@router.callback_query(F.data == "back_to_start")
async def back_to_start_menu(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Return to start menu."""
    # Import here to avoid circular imports
    from app.handlers.commands.start import cmd_start
    
    # Create a fake message object for the start command
    class FakeMessage:
        def __init__(self, callback_query):
            self.from_user = callback_query.from_user
            self.chat = callback_query.message.chat
            self.message_id = callback_query.message.message_id
            self.date = callback_query.message.date
        
        async def answer(self, text, **kwargs):
            await callback.message.edit_text(text, **kwargs)
    
    fake_message = FakeMessage(callback)
    await cmd_start(fake_message, state, db_session, fsm_service)
