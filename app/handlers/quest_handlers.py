"""
Quest handlers for the Telegram RPG game bot.

This module contains handlers for quest-related commands and callbacks.
"""

from typing import Optional
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.game.actions import Action
from app.game.states import GameStates, QuestStates
from app.services.quest_loop_service import QuestLoopService
from app.services.i18n_service import I18nService
from app.services.user_cache_service import user_cache
from app.services.logging_service import get_logger

logger = get_logger(__name__)

# Create router for quest handlers
quest_router = Router()


@quest_router.message(F.text.in_(["/quest", "/start_quest", "🎯 Start Quest"]))
async def start_quest_handler(message: Message, state: FSMContext, quest_loop_service: QuestLoopService = None, i18n_service = None):
    """Handle quest start command."""
    try:
        user_id = message.from_user.id
        
        if not quest_loop_service or not i18n_service:
            await message.reply("❌ Service not available. Please try again later.")
            return
        
        # Check if user is already in a quest
        quest_status = await quest_loop_service.get_quest_status(user_id)
        if quest_status and quest_status.get("active"):
            await message.reply("🎯 You are already in an active quest!")
            return
        
        # Start quest loop
        success = await quest_loop_service.start_quest_loop(
            user_id=user_id,
            fsm_context=state,
            message=message
        )
        
        if success:
            logger.info("Started quest for user", user_id=user_id)
        else:
            await message.reply("❌ Failed to start quest. Please try again.")
            
    except Exception as e:
        logger.error("Failed to start quest",
                    user_id=message.from_user.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.reply("❌ An error occurred while starting the quest.")


@quest_router.message(F.text.in_(["/quest_status", "/status", "📊 Quest Status"]))
async def quest_status_handler(message: Message, state: FSMContext, quest_loop_service: QuestLoopService = None):
    """Handle quest status command."""
    try:
        user_id = message.from_user.id
        if not quest_loop_service:
            await message.reply("❌ Service not available. Please try again later.")
            return
        
        # Get quest status
        quest_status = await quest_loop_service.get_quest_status(user_id)
        
        if not quest_status or not quest_status.get("active"):
            await message.reply("📊 No active quest found. Use /quest to start a new quest!")
            return
        
        # Format status message
        status_text = f"📊 **Quest Status**\n\n"
        status_text += f"🆔 Session ID: `{quest_status.get('session_id', 'N/A')}`\n"
        status_text += f"📈 Status: {quest_status.get('status', 'Unknown')}\n"
        status_text += f"🎬 Started: {quest_status.get('started_at', 'Unknown')}\n"
        status_text += f"⚡ Actions: {quest_status.get('actions_count', 0)}\n"
        status_text += f"💬 Messages: {quest_status.get('messages_count', 0)}\n"
        
        await message.reply(status_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Failed to get quest status",
                    user_id=message.from_user.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.reply("❌ An error occurred while getting quest status.")


@quest_router.message(F.text.in_(["/end_quest", "/stop_quest", "🛑 End Quest"]))
async def end_quest_handler(message: Message, state: FSMContext, quest_loop_service: QuestLoopService = None):
    """Handle quest end command."""
    try:
        user_id = message.from_user.id
        if not quest_loop_service:
            await message.reply("❌ Service not available. Please try again later.")
            return
        
        # Check if user is in a quest
        quest_status = await quest_loop_service.get_quest_status(user_id)
        if not quest_status or not quest_status.get("active"):
            await message.reply("📊 No active quest to end.")
            return
        
        # End the quest
        await quest_loop_service._end_quest_loop(
            user_id=user_id,
            fsm_context=state,
            reason="Manually ended by player"
        )
        
        await message.reply("🛑 Quest ended successfully!")
        logger.info("Manually ended quest for user", user_id=user_id)
        
    except Exception as e:
        logger.error("Failed to end quest",
                    user_id=message.from_user.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.reply("❌ An error occurred while ending the quest.")


@quest_router.callback_query(F.data.startswith("action:"))
async def action_callback_handler(callback_query: CallbackQuery, state: FSMContext, quest_loop_service: QuestLoopService = None):
    """Handle action callback queries."""
    try:
        user_id = callback_query.from_user.id
        action_str = callback_query.data.split(":", 1)[1]
        if not quest_loop_service:
            await callback_query.answer("❌ Service not available", show_alert=True)
            return
        
        # Check if user is in a quest
        quest_status = await quest_loop_service.get_quest_status(user_id)
        if not quest_status or not quest_status.get("active"):
            await callback_query.answer("❌ No active quest", show_alert=True)
            return
        
        # Validate action
        try:
            action = Action(action_str)
        except ValueError:
            await callback_query.answer("❌ Invalid action", show_alert=True)
            return
        
        # Process the action
        success = await quest_loop_service.process_action(
            user_id=user_id,
            action=action,
            fsm_context=state,
            callback_query=callback_query
        )
        
        if not success:
            await callback_query.answer("❌ Failed to process action", show_alert=True)
        
        logger.info("Processed action callback",
                   user_id=user_id,
                   action=action_str,
                   success=success)
        
    except Exception as e:
        logger.error("Failed to handle action callback",
                    user_id=callback_query.from_user.id,
                    action=callback_query.data,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await callback_query.answer("❌ An error occurred", show_alert=True)


@quest_router.message(F.text.in_(["/help_quest", "/quest_help", "❓ Quest Help"]))
async def quest_help_handler(message: Message, state: FSMContext):
    """Handle quest help command."""
    try:
        help_text = """
🎯 **Quest System Help**

**Commands:**
• `/quest` - Start a new quest
• `/quest_status` - Check current quest status
• `/end_quest` - End current quest
• `/cache_stats` - Show cache statistics
• `/help_quest` - Show this help

**Actions:**
• ⚔️ **Attack** - Engage in combat
• 🛡️ **Defend** - Protect yourself
• 🧙 **Cast** - Use magic
• 💬 **Talk** - Engage in dialogue
• 👻 **Sneak** - Move stealthily
• 💰 **Loot** - Search for items
• 🏃 **Flee** - Escape from danger
• ⏳ **Wait** - Pass time
• 🔍 **Investigate** - Examine surroundings
• 🤖 **AI Action** - Let AI choose action

**Game Flow:**
1. Start a quest with `/quest`
2. Choose actions based on the scene
3. Your stats and energy change based on actions
4. Quest continues until end conditions are met
5. Use `/end_quest` to stop anytime

**Tips:**
• Watch your energy and risk levels
• Different scenes offer different actions
• AI can help choose optimal actions
• Some actions require certain stats

Good luck, adventurer! 🗡️
        """
        
        await message.reply(help_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Failed to show quest help",
                    user_id=message.from_user.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.reply("❌ An error occurred while showing help.")


@quest_router.message(F.text.in_(["/cache_stats", "/stats", "📊 Cache Stats"]))
async def cache_stats_handler(message: Message, state: FSMContext):
    """Handle cache statistics command."""
    try:
        user_id = message.from_user.id
        
        # Get cache statistics
        stats = user_cache.get_cache_stats()
        
        # Format stats message
        stats_text = f"📊 **Cache Statistics**\n\n"
        stats_text += f"📈 Total Entries: {stats['total_entries']}\n"
        stats_text += f"✅ Active Entries: {stats['active_entries']}\n"
        stats_text += f"⏰ Expired Entries: {stats['expired_entries']}\n"
        stats_text += f"🔗 Telegram Mappings: {stats['telegram_mappings']}\n"
        stats_text += f"⏱️ Cache Duration: {stats['cache_duration_minutes']:.1f} minutes\n\n"
        stats_text += f"💡 Cache helps reduce database queries for better performance!"
        
        await message.reply(stats_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Failed to get cache stats",
                    user_id=message.from_user.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.reply("❌ An error occurred while getting cache statistics.")


# Register the router
def register_quest_handlers(router: Router):
    """Register quest handlers with the main router."""
    router.include_router(quest_router)
