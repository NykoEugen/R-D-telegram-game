from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.states import GameStates
from app.handlers.menu import build_main_menu_kb
from app.services.fsm_service import FSMStateService
from app.services.i18n_service import i18n_service
from app.services.logging_service import get_logger

router = Router()
logger = get_logger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle the /start command - greet player and introduce the RPG world."""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name or "Adventurer"
        
        # Set FSM state to menu
        await state.set_state(GameStates.MENU)
        
        welcome_text = (
            f"🎮 <b>Welcome to Fantasy RPG Adventure, {user_name}!</b>\n\n"
            f"🌍 Embark on epic quests in a medieval fantasy world filled with magic, monsters, and treasure!\n\n"
            f"🗡️ <b>Adventure awaits!</b> Choose your path:\n\n"
            f"<b>Available Commands:</b>\n"
            f"🎯 /quest - Start a new quest adventure\n"
            f"📊 /quest_status - Check your current quest status\n"
            f"🛑 /end_quest - End your current quest\n"
            f"❓ /help_quest - Get quest system help\n"
            f"🌐 /language - Change language\n"
            f"❓ /help - Show all commands\n\n"
            f"<b>Ready for your legendary adventure?</b> 🏰"
        )
        world_description = None
        
        # Store initial data in FSM
        await state.update_data(
            user_name=user_name,
            world_description=world_description,
            start_time=message.date.isoformat()
        )
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action="start",
            scene_id="main_menu",
            additional_data={"user_name": user_name, "world_description": world_description}
        )
        
        await message.answer(welcome_text, parse_mode="HTML")
        await message.answer(
            i18n_service.get_text(user_id, 'menu.title'),
            reply_markup=build_main_menu_kb(user_id),
            parse_mode="Markdown"
        )
        logger.info("User started the bot", 
                   user_id=message.from_user.id,
                   user_name=message.from_user.first_name,
                   chat_id=message.chat.id)
        
    except Exception as e:
        logger.error("Error in start command", 
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.answer(
            "🎮 Welcome to the Fantasy RPG Adventure!\n\n"
            "❌ There was an error, but you can still use:\n"
            "• /quest - Generate a new quest"
        )

@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle the /help command - show available commands and game information."""
    try:
        user_id = message.from_user.id
        
        # Get current FSM state
        current_state = await state.get_state()
        
        help_text = (
            f"{i18n_service.get_text(user_id, 'help_title')}\n\n"
            f"{i18n_service.get_text(user_id, 'game_commands')}\n"
            f"{i18n_service.get_text(user_id, 'start_command')}\n"
            f"{i18n_service.get_text(user_id, 'quest_command')}\n"
            f"{i18n_service.get_text(user_id, 'help_command')}\n"
            f"{i18n_service.get_text(user_id, 'language_command')}\n\n"
            f"{i18n_service.get_text(user_id, 'about_game')}\n"
            f"{i18n_service.get_text(user_id, 'about_description')}\n\n"
            f"{i18n_service.get_text(user_id, 'getting_started')}\n"
            f"{i18n_service.get_text(user_id, 'getting_started_1')}\n"
            f"{i18n_service.get_text(user_id, 'getting_started_2')}\n"
            f"{i18n_service.get_text(user_id, 'getting_started_3')}\n\n"
            f"{i18n_service.get_text(user_id, 'adventure_legendary')}"
        )
        
        # Add FSM state info if available
        if current_state:
            help_text += f"\n\n🎮 **Current State:** `{current_state}`"
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action="help",
            scene_id="help_menu"
        )
        
        await message.answer(help_text, parse_mode="Markdown")
        logger.info("User requested help", 
                   user_id=message.from_user.id,
                   user_name=message.from_user.first_name,
                   chat_id=message.chat.id,
                   current_state=current_state)
        
    except Exception as e:
        logger.error("Error in help command", 
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.answer(
            "❌ **Help Error**\n\n"
            "There was an error retrieving help information. Please try again later."
        )
