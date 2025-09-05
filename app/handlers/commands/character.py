"""
Character creation and management commands for the Telegram RPG game bot.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

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
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Please use /start first to register.")
        return
    
    if user.player:
        await message.answer("You already have a character! Use /character to view your stats.")
        return
    
    # Start character creation
    await state.set_state(CharacterCreationStates.WAITING_FOR_NAME)
    await message.answer(
        "🎭 **Character Creation**\n\n"
        "Welcome to the world of adventure! Let's create your character.\n\n"
        "What would you like to name your character?",
        parse_mode="Markdown"
    )


@router.message(CharacterCreationStates.WAITING_FOR_NAME)
async def process_character_name(message: Message, state: FSMContext):
    """Process character name input."""
    character_name = message.text.strip()
    
    if len(character_name) < 2 or len(character_name) > 20:
        await message.answer("Character name must be between 2 and 20 characters long.")
        return
    
    # Store name and show class selection
    await state.update_data(character_name=character_name)
    await state.set_state(CharacterCreationStates.WAITING_FOR_CLASS)
    
    # Create class selection keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⚔️ Warrior", 
                callback_data="class_warrior"
            ),
            InlineKeyboardButton(
                text="🗡️ Rogue", 
                callback_data="class_rogue"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔮 Mage", 
                callback_data="class_mage"
            ),
            InlineKeyboardButton(
                text="⛑️ Cleric", 
                callback_data="class_cleric"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏹 Ranger", 
                callback_data="class_ranger"
            )
        ]
    ])
    
    await message.answer(
        f"Great! Your character will be named **{character_name}**.\n\n"
        "Now choose your character class:\n\n"
        "⚔️ **Warrior** - Strong and resilient fighters\n"
        "🗡️ **Rogue** - Agile and lucky adventurers\n"
        "🔮 **Mage** - Intelligent spellcasters\n"
        "⛑️ **Cleric** - Divine healers and protectors\n"
        "🏹 **Ranger** - Versatile hunters and scouts",
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
                text="✅ Create Character", 
                callback_data="confirm_creation"
            ),
            InlineKeyboardButton(
                text="❌ Cancel", 
                callback_data="cancel_creation"
            )
        ]
    ])
    
    await callback.message.edit_text(
        f"**Character Summary**\n\n"
        f"Name: {character_name}\n"
        f"Class: {character_class.value.title()}\n\n"
        f"Description: {class_description}\n\n"
        f"Are you sure you want to create this character?",
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
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Error: User not found. Please use /start first.")
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
        f"🎉 **Character Created!**\n\n"
        f"Welcome, **{character_name}** the {character_class.value.title()}!\n\n"
        f"Your adventure begins now. Use /character to view your stats or /adventure to start exploring!",
        parse_mode="Markdown"
    )
    
    await state.clear()


@router.callback_query(F.data == "cancel_creation")
async def cancel_character_creation(callback: CallbackQuery, state: FSMContext):
    """Cancel character creation."""
    await callback.message.edit_text("Character creation cancelled.")
    await state.clear()


@router.message(Command("character"))
async def cmd_character_stats(message: Message, db_session: AsyncSession):
    """Show character stats."""
    user_id = message.from_user.id
    
    # Get user and player
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await message.answer(
            "You don't have a character yet! Use /create_character to create one.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Create Character", callback_data="start_creation")]
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
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await callback.answer("Character not found!")
        return
    
    player = user.player
    derived_stats = player.get_derived_stats()
    xp_current, xp_required = player.get_xp_progress()
    
    # Create detailed stats message
    stats_message = f"""
**📊 Detailed Character Stats**

**{player.character_name}** (Level {player.level})
Class: {player.character_class.value.title() if player.character_class else 'None'}

**Base Attributes:**
• 💪 Strength: {player.strength} (Attack: {derived_stats.attack})
• 🏃 Agility: {player.agility} (Crit: {derived_stats.crit_chance:.1f}%, Dodge: {derived_stats.dodge:.1f}%)
• 🧠 Intelligence: {player.intelligence} (Magic: {derived_stats.magic})
• ❤️ Vitality: {player.vitality} (HP: {derived_stats.hp_max})
• 🍀 Luck: {player.luck}

**Combat Stats:**
• HP: {player.health}/{derived_stats.hp_max}
• Attack Power: {derived_stats.attack}
• Magic Power: {derived_stats.magic}
• Critical Hit Chance: {derived_stats.crit_chance:.1f}%
• Dodge Chance: {derived_stats.dodge:.1f}%

**Progress:**
• Experience: {player.experience}
• XP to Next Level: {xp_current}/{xp_required}
• Available Stat Points: {player.available_stat_points}

**Resources:**
• Coins: {player.coins}
• Gems: {player.gems}
• Energy: {player.energy}/{player.max_energy}
"""
    
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
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await callback.answer("Character not found!")
        return
    
    player = user.player
    
    if not player.can_level_up():
        await callback.answer("You don't have enough XP to level up!")
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
            f"🎉 **Level Up!**\n\n"
            f"Congratulations! You've reached level {player.level}!\n\n"
            f"You have {player.available_stat_points} stat points to distribute.\n"
            f"Use /character to view your updated stats.",
            parse_mode="Markdown"
        )
    else:
        await callback.answer("No level up available!")


@router.callback_query(F.data == "distribute_points")
async def start_point_distribution(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Start stat point distribution."""
    user_id = callback.from_user.id
    
    # Get user and player
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db_session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.player:
        await callback.answer("Character not found!")
        return
    
    player = user.player
    
    if player.available_stat_points <= 0:
        await callback.answer("You don't have any stat points to distribute!")
        return
    
    await state.set_state(CharacterManagementStates.DISTRIBUTING_POINTS)
    await state.update_data(player_id=player.id, available_points=player.available_stat_points)
    
    # Create point distribution keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💪 +STR", callback_data="dist_str"),
            InlineKeyboardButton(text="🏃 +AGI", callback_data="dist_agi")
        ],
        [
            InlineKeyboardButton(text="🧠 +INT", callback_data="dist_int"),
            InlineKeyboardButton(text="❤️ +VIT", callback_data="dist_vit")
        ],
        [
            InlineKeyboardButton(text="🍀 +LUK", callback_data="dist_luk"),
            InlineKeyboardButton(text="✅ Confirm", callback_data="confirm_dist")
        ],
        [
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_dist")
        ]
    ])
    
    await callback.message.edit_text(
        f"🎯 **Stat Point Distribution**\n\n"
        f"Available Points: {player.available_stat_points}\n\n"
        f"Current Stats:\n"
        f"• Strength: {player.strength}\n"
        f"• Agility: {player.agility}\n"
        f"• Intelligence: {player.intelligence}\n"
        f"• Vitality: {player.vitality}\n"
        f"• Luck: {player.luck}\n\n"
        f"Choose which stat to increase:",
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
        await callback.answer("No more points to distribute!")
        return
    
    # Get player
    from sqlalchemy import select
    result = await db_session.execute(
        select(Player).where(Player.id == data["player_id"])
    )
    player = result.scalar_one_or_none()
    
    if not player:
        await callback.answer("Player not found!")
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
                InlineKeyboardButton(text="💪 +STR", callback_data="dist_str"),
                InlineKeyboardButton(text="🏃 +AGI", callback_data="dist_agi")
            ],
            [
                InlineKeyboardButton(text="🧠 +INT", callback_data="dist_int"),
                InlineKeyboardButton(text="❤️ +VIT", callback_data="dist_vit")
            ],
            [
                InlineKeyboardButton(text="🍀 +LUK", callback_data="dist_luk"),
                InlineKeyboardButton(text="✅ Confirm", callback_data="confirm_dist")
            ],
            [
                InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_dist")
            ]
        ])
        
        await callback.message.edit_text(
            f"🎯 **Stat Point Distribution**\n\n"
            f"Available Points: {player.available_stat_points}\n\n"
            f"Current Stats:\n"
            f"• Strength: {player.strength}\n"
            f"• Agility: {player.agility}\n"
            f"• Intelligence: {player.intelligence}\n"
            f"• Vitality: {player.vitality}\n"
            f"• Luck: {player.luck}\n\n"
            f"Choose which stat to increase:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        await callback.answer(f"+1 {stat_type.upper()}!")
    else:
        await callback.answer("Failed to distribute point!")


@router.callback_query(F.data == "confirm_dist", CharacterManagementStates.DISTRIBUTING_POINTS)
async def confirm_distribution(callback: CallbackQuery, state: FSMContext):
    """Confirm stat point distribution."""
    await callback.message.edit_text(
        "✅ **Stat points distributed successfully!**\n\n"
        "Use /character to view your updated stats.",
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
    
    await callback.message.edit_text("Stat point distribution cancelled.")
    await state.clear()


@router.callback_query(F.data == "start_creation")
async def start_creation_from_button(callback: CallbackQuery, state: FSMContext):
    """Start character creation from button press."""
    await state.set_state(CharacterCreationStates.WAITING_FOR_NAME)
    await callback.message.edit_text(
        "🎭 **Character Creation**\n\n"
        "Welcome to the world of adventure! Let's create your character.\n\n"
        "What would you like to name your character?",
        parse_mode="Markdown"
    )
