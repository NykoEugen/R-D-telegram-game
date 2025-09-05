"""
Region exploration commands for the Telegram RPG game bot.

This module handles commands for exploring regions, viewing available locations,
and managing world progression.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from app.services.i18n_service import I18nService
from app.services.fsm_service import FSMStateService
from app.models.world import WorldManager, Region
from app.models.player_progress import PlayerProgress, ProgressManager
from app.models.combat import EnemyGenerator
from app.models.character import CharacterManager
from app.handlers.keyboards import build_region_keyboard, build_exploration_keyboard

router = Router()


@router.message(Command("regions"))
async def cmd_regions(message: Message, state: FSMContext, db_session: AsyncSession, 
                     fsm_service: FSMStateService, i18n: I18nService):
    """Show available regions for exploration."""
    user_id = message.from_user.id
    
    # Get player progress
    progress = await fsm_service.get_player_progress(db_session, user_id)
    if not progress:
        await message.answer(_("You need to start your adventure first! Use /start to begin."))
        return
    
    # Get available regions
    available_regions = []
    for region_id in progress.get_available_regions():
        region = WorldManager.get_region_by_id(region_id)
        if region:
            available_regions.append(region)
    
    if not available_regions:
        await message.answer(_("No regions are currently available. Complete more quests to unlock new areas!"))
        return
    
    # Build regions list message
    regions_text = _("🌍 **Available Regions** 🌍\n\n")
    
    for region in available_regions:
        tier_emoji = {
            "tier_1": "🟢",
            "tier_2": "🟡", 
            "tier_3": "🔴"
        }.get(region.difficulty.tier.value, "⚪")
        
        visit_count = progress.get_visit_count(region.region_id)
        visit_text = f" (visited {visit_count} times)" if visit_count > 0 else ""
        
        regions_text += f"{tier_emoji} **{region.name}**\n"
        regions_text += f"   {region.description}\n"
        regions_text += f"   Level: {region.difficulty.level_range[0]}-{region.difficulty.level_range[1]}{visit_text}\n\n"
    
    # Create keyboard with region buttons
    keyboard = build_region_keyboard(available_regions)
    
    await message.answer(regions_text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("explore_region_"))
async def cb_explore_region(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession,
                           fsm_service: FSMStateService, i18n: I18nService):
    """Handle region exploration callback."""
    region_id = callback.data.replace("explore_region_", "")
    user_id = callback.from_user.id
    
    # Get player progress and character data
    progress = await fsm_service.get_player_progress(db_session, user_id)
    character_data = await fsm_service.get_character_data(db_session, user_id)
    
    if not progress or not character_data:
        await callback.answer(_("Error: Player data not found!"), show_alert=True)
        return
    
    # Check if region is available
    if not progress.can_access_region(region_id):
        await callback.answer(_("This region is not available yet!"), show_alert=True)
        return
    
    # Get region data
    region = WorldManager.get_region_by_id(region_id)
    if not region:
        await callback.answer(_("Region not found!"), show_alert=True)
        return
    
    # Check if player level is appropriate
    player_level = character_data.get("level", 1)
    if player_level < region.difficulty.level_range[0]:
        await callback.answer(
            _("You need to be at least level {min_level} to explore this region!").format(
                min_level=region.difficulty.level_range[0]
            ), 
            show_alert=True
        )
        return
    
    # Record visit
    progress.visit_location(region_id)
    await db_session.commit()
    
    # Start exploration
    await state.update_data(current_region=region_id)
    
    # Generate exploration event
    event = WorldManager.get_random_event(region, character_data)
    
    if event:
        await handle_region_event(callback, event, region, character_data, db_session, fsm_service, i18n)
    else:
        # No event occurred, show region description
        await show_region_description(callback, region, character_data, i18n)


async def handle_region_event(callback: CallbackQuery, event, region: Region, character_data: Dict[str, Any],
                             db_session: AsyncSession, fsm_service: FSMStateService, i18n: I18nService):
    """Handle a region event (combat, treasure, story, etc.)."""
    user_id = callback.from_user.id
    
    if event.event_type == "combat":
        await handle_combat_event(callback, event, region, character_data, db_session, fsm_service, i18n)
    elif event.event_type == "treasure":
        await handle_treasure_event(callback, event, region, character_data, db_session, fsm_service, i18n)
    elif event.event_type == "story":
        await handle_story_event(callback, event, region, character_data, db_session, fsm_service, i18n)
    elif event.event_type == "trap":
        await handle_trap_event(callback, event, region, character_data, db_session, fsm_service, i18n)
    elif event.event_type == "merchant":
        await handle_merchant_event(callback, event, region, character_data, db_session, fsm_service, i18n)
    else:
        await show_region_description(callback, region, character_data, i18n)


async def handle_combat_event(callback: CallbackQuery, event, region: Region, character_data: Dict[str, Any],
                             db_session: AsyncSession, fsm_service: FSMStateService, i18n: I18nService):
    """Handle combat events in regions."""
    user_id = callback.from_user.id
    
    # Get random enemy for this region
    enemy_data = WorldManager.get_random_enemy(region, character_data.get("level", 1))
    if not enemy_data:
        await callback.answer(_("No enemies found in this region!"), show_alert=True)
        return
    
    # Generate enemy with region difficulty multiplier
    region_multiplier = WorldManager.get_region_difficulty_multiplier(region)
    enemy = EnemyGenerator.generate_enemy(
        level=character_data.get("level", 1),
        enemy_type=enemy_data.enemy_type,
        region_multiplier=region_multiplier
    )
    
    # Create combat message
    combat_text = f"⚔️ **{event.name}** ⚔️\n\n"
    combat_text += f"{event.description}\n\n"
    combat_text += f"**{enemy.name}** (Level {enemy.level}) appears!\n"
    combat_text += f"HP: {enemy.hp_current}/{enemy.hp_max}\n"
    combat_text += f"Attack: {enemy.attack} | Magic: {enemy.magic} | Agility: {enemy.agility}\n\n"
    combat_text += _("What will you do?")
    
    # Create combat keyboard
    keyboard = build_exploration_keyboard("combat", enemy_data.enemy_type)
    
    # Store combat data in state
    await callback.message.edit_text(combat_text, reply_markup=keyboard, parse_mode="Markdown")
    
    # Store enemy data for combat resolution
    await callback.answer()


async def handle_treasure_event(callback: CallbackQuery, event, region: Region, character_data: Dict[str, Any],
                               db_session: AsyncSession, fsm_service: FSMStateService, i18n: I18nService):
    """Handle treasure events in regions."""
    user_id = callback.from_user.id
    
    # Calculate rewards with region multipliers
    xp_mult, gold_mult = WorldManager.get_region_reward_multipliers(region)
    
    # Parse reward dice (simplified for now)
    import random
    xp_reward = random.randint(1, 4) + 2  # 1d4+2 base
    gold_reward = random.randint(1, 6) + 1  # 1d6+1 base
    
    xp_reward = int(xp_reward * xp_mult)
    gold_reward = int(gold_reward * gold_mult)
    
    # Get random loot
    loot_items = WorldManager.get_random_loot(region, character_data)
    
    # Create treasure message
    treasure_text = f"💰 **{event.name}** 💰\n\n"
    treasure_text += f"{event.description}\n\n"
    treasure_text += f"**Rewards:**\n"
    treasure_text += f"• Experience: +{xp_reward}\n"
    treasure_text += f"• Gold: +{gold_reward}\n"
    
    if loot_items:
        treasure_text += f"• Items found:\n"
        for item in loot_items:
            treasure_text += f"  - {item.name}\n"
    
    # Apply rewards to character
    character_data = CharacterManager.add_experience(character_data, xp_reward)
    character_data["gold"] = character_data.get("gold", 0) + gold_reward
    
    # Check for level up
    old_level = character_data.get("level", 1)
    new_level = character_data.get("level", 1)
    if new_level > old_level:
        treasure_text += f"\n🎉 **Level Up!** You are now level {new_level}! 🎉\n"
    
    # Save character data
    await fsm_service.save_character_data(db_session, user_id, character_data)
    
    # Create continue keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("Continue Exploring"), callback_data=f"continue_explore_{region.region_id}")],
        [InlineKeyboardButton(text=_("Return to Regions"), callback_data="back_to_regions")]
    ])
    
    await callback.message.edit_text(treasure_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


async def handle_story_event(callback: CallbackQuery, event, region: Region, character_data: Dict[str, Any],
                            db_session: AsyncSession, fsm_service: FSMStateService, i18n: I18nService):
    """Handle story events in regions."""
    user_id = callback.from_user.id
    
    # Calculate rewards
    xp_mult, gold_mult = WorldManager.get_region_reward_multipliers(region)
    xp_reward = int((random.randint(1, 6) + 2) * xp_mult)  # 1d6+2 base
    
    # Apply rewards
    character_data = CharacterManager.add_experience(character_data, xp_reward)
    await fsm_service.save_character_data(db_session, user_id, character_data)
    
    # Create story message
    story_text = f"📖 **{event.name}** 📖\n\n"
    story_text += f"{event.description}\n\n"
    story_text += f"**Experience gained: +{xp_reward}**\n"
    
    # Check for level up
    old_level = character_data.get("level", 1)
    new_level = character_data.get("level", 1)
    if new_level > old_level:
        story_text += f"\n🎉 **Level Up!** You are now level {new_level}! 🎉\n"
    
    # Create continue keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("Continue Exploring"), callback_data=f"continue_explore_{region.region_id}")],
        [InlineKeyboardButton(text=_("Return to Regions"), callback_data="back_to_regions")]
    ])
    
    await callback.message.edit_text(story_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


async def handle_trap_event(callback: CallbackQuery, event, region: Region, character_data: Dict[str, Any],
                           db_session: AsyncSession, fsm_service: FSMStateService, i18n: I18nService):
    """Handle trap events in regions."""
    user_id = callback.from_user.id
    
    # Apply trap consequences
    damage = random.randint(1, 4) + 1  # 1d4+1 damage
    character_data["health"] = max(1, character_data.get("health", 1) - damage)
    
    # Save character data
    await fsm_service.save_character_data(db_session, user_id, character_data)
    
    # Create trap message
    trap_text = f"⚠️ **{event.name}** ⚠️\n\n"
    trap_text += f"{event.description}\n\n"
    trap_text += f"**You take {damage} damage!**\n"
    trap_text += f"Current HP: {character_data['health']}/{character_data.get('max_health', 1)}\n"
    
    # Create continue keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("Continue Exploring"), callback_data=f"continue_explore_{region.region_id}")],
        [InlineKeyboardButton(text=_("Return to Regions"), callback_data="back_to_regions")]
    ])
    
    await callback.message.edit_text(trap_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


async def handle_merchant_event(callback: CallbackQuery, event, region: Region, character_data: Dict[str, Any],
                               db_session: AsyncSession, fsm_service: FSMStateService, i18n: I18nService):
    """Handle merchant events in regions."""
    # Create merchant message
    merchant_text = f"🏪 **{event.name}** 🏪\n\n"
    merchant_text += f"{event.description}\n\n"
    merchant_text += _("The merchant offers various goods for sale. (Shop system coming soon!)")
    
    # Create continue keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("Continue Exploring"), callback_data=f"continue_explore_{region.region_id}")],
        [InlineKeyboardButton(text=_("Return to Regions"), callback_data="back_to_regions")]
    ])
    
    await callback.message.edit_text(merchant_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


async def show_region_description(callback: CallbackQuery, region: Region, character_data: Dict[str, Any], i18n: I18nService):
    """Show region description when no event occurs."""
    region_text = f"🌍 **{region.name}** 🌍\n\n"
    region_text += f"{region.description}\n\n"
    region_text += f"**Difficulty:** {region.difficulty.tier.value.replace('_', ' ').title()}\n"
    region_text += f"**Level Range:** {region.difficulty.level_range[0]}-{region.difficulty.level_range[1]}\n\n"
    region_text += _("You explore the area but nothing of interest happens this time.")
    
    # Create continue keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("Continue Exploring"), callback_data=f"continue_explore_{region.region_id}")],
        [InlineKeyboardButton(text=_("Return to Regions"), callback_data="back_to_regions")]
    ])
    
    await callback.message.edit_text(region_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("continue_explore_"))
async def cb_continue_explore(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession,
                             fsm_service: FSMStateService, i18n: I18nService):
    """Continue exploring the current region."""
    region_id = callback.data.replace("continue_explore_", "")
    user_id = callback.from_user.id
    
    # Get player data
    progress = await fsm_service.get_player_progress(db_session, user_id)
    character_data = await fsm_service.get_character_data(db_session, user_id)
    
    if not progress or not character_data:
        await callback.answer(_("Error: Player data not found!"), show_alert=True)
        return
    
    # Get region data
    region = WorldManager.get_region_by_id(region_id)
    if not region:
        await callback.answer(_("Region not found!"), show_alert=True)
        return
    
    # Generate new event
    event = WorldManager.get_random_event(region, character_data)
    
    if event:
        await handle_region_event(callback, event, region, character_data, db_session, fsm_service, i18n)
    else:
        await show_region_description(callback, region, character_data, i18n)


@router.callback_query(F.data == "back_to_regions")
async def cb_back_to_regions(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession,
                            fsm_service: FSMStateService, i18n: I18nService):
    """Return to regions list."""
    user_id = callback.from_user.id
    
    # Get player progress
    progress = await fsm_service.get_player_progress(db_session, user_id)
    if not progress:
        await callback.answer(_("You need to start your adventure first! Use /start to begin."))
        return
    
    # Get available regions
    available_regions = []
    for region_id in progress.get_available_regions():
        region = WorldManager.get_region_by_id(region_id)
        if region:
            available_regions.append(region)
    
    if not available_regions:
        await callback.answer(_("No regions are currently available. Complete more quests to unlock new areas!"))
        return
    
    # Build regions list message
    regions_text = _("🌍 **Available Regions** 🌍\n\n")
    
    for region in available_regions:
        tier_emoji = {
            "tier_1": "🟢",
            "tier_2": "🟡", 
            "tier_3": "🔴"
        }.get(region.difficulty.tier.value, "⚪")
        
        visit_count = progress.get_visit_count(region.region_id)
        visit_text = f" (visited {visit_count} times)" if visit_count > 0 else ""
        
        regions_text += f"{tier_emoji} **{region.name}**\n"
        regions_text += f"   {region.description}\n"
        regions_text += f"   Level: {region.difficulty.level_range[0]}-{region.difficulty.level_range[1]}{visit_text}\n\n"
    
    # Create keyboard with region buttons
    keyboard = build_region_keyboard(available_regions)
    
    await callback.message.edit_text(regions_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.message(Command("world"))
async def cmd_world(message: Message, state: FSMContext, db_session: AsyncSession,
                   fsm_service: FSMStateService, i18n: I18nService):
    """Show world overview and player progress."""
    user_id = message.from_user.id
    
    # Get player progress
    progress = await fsm_service.get_player_progress(db_session, user_id)
    if not progress:
        await message.answer(_("You need to start your adventure first! Use /start to begin."))
        return
    
    # Get character data
    character_data = await fsm_service.get_character_data(db_session, user_id)
    if not character_data:
        await message.answer(_("Character data not found!"))
        return
    
    # Build world overview
    world_text = _("🌍 **World Overview** 🌍\n\n")
    world_text += f"**Your Progress:**\n"
    world_text += f"• Level: {character_data.get('level', 1)}\n"
    world_text += f"• Experience: {character_data.get('experience', 0)}\n"
    world_text += f"• Regions Unlocked: {len(progress.unlocked_regions)}\n"
    world_text += f"• Quests Completed: {len(progress.completed_quests)}\n\n"
    
    # Show all regions (locked and unlocked)
    world_text += _("**All Regions:**\n")
    
    for region_id, region in WorldManager.REGIONS.items():
        is_unlocked = region_id in progress.unlocked_regions
        status_emoji = "✅" if is_unlocked else "🔒"
        tier_emoji = {
            "tier_1": "🟢",
            "tier_2": "🟡", 
            "tier_3": "🔴"
        }.get(region.difficulty.tier.value, "⚪")
        
        world_text += f"{status_emoji} {tier_emoji} **{region.name}**\n"
        world_text += f"   Level {region.difficulty.level_range[0]}-{region.difficulty.level_range[1]}\n"
        
        if not is_unlocked:
            req = region.difficulty.unlock_requirement
            if "level" in req:
                world_text += f"   Requires: Level {req['level']}\n"
            if "quest" in req:
                world_text += f"   Requires: Quest '{req['quest']}'\n"
        
        world_text += "\n"
    
    await message.answer(world_text, parse_mode="Markdown")
