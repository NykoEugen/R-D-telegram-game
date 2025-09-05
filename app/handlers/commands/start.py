from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.services.ai import AIGenerationService
from app.services.logging_service import get_logger
from app.services.i18n_service import i18n_service
from app.services.fsm_service import FSMStateService
from app.game.states import GameStates
from app.models.user import User

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
        
        # Generate world description using OpenAI with user's language
        user_language = i18n_service.get_user_language(user_id)
        world_description = await AIGenerationService.generate_world_description(language=user_language)
        
        # Check if user exists, create if not
        result = await db_session.execute(
            select(User)
            .where(User.telegram_id == user_id)
            .options(selectinload(User.player))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            from app.services.repositories.user_repo import UserRepository
            user_repo = UserRepository(db_session)
            user = await user_repo.create_user(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language=user_language,
                is_bot=message.from_user.is_bot
            )
            await db_session.commit()
            logger.info("Created new user in start command", 
                       user_id=user.id, 
                       telegram_id=user_id,
                       username=user.username)
        
        # Check if user has a player by querying the database directly
        from app.models.player import Player
        player_result = await db_session.execute(
            select(Player).where(Player.user_id == user.id)
        )
        player = player_result.scalar_one_or_none()
        
        if not player:
            # User exists but no hero - show welcome and offer hero creation
            if world_description:
                welcome_text = (
                    f"{i18n_service.get_text(user_id, 'start_welcome', name=user_name)}\n\n"
                    f"{i18n_service.get_text(user_id, 'world_description', description=world_description)}\n\n"
                    f"{i18n_service.get_text(user_id, 'adventure_awaits')}\n\n"
                    f"{i18n_service.get_text(user_id, 'start.new_user')}"
                )
            else:
                # Fallback if OpenAI fails
                welcome_text = (
                    f"{i18n_service.get_text(user_id, 'fallback_welcome')}\n\n"
                    f"{i18n_service.get_text(user_id, 'fallback_world', description='Embark on epic quests in a medieval fantasy world!')}\n\n"
                    f"{i18n_service.get_text(user_id, 'adventure_awaits')}\n\n"
                    f"{i18n_service.get_text(user_id, 'start.new_user')}"
                )
            
            # Create hero creation keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=i18n_service.get_text(user_id, 'btn.create_hero'), 
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
            
        else:
            # User has a hero - show welcome and offer quest
            hero_name = player.character_name
            hero_class = player.get_character_class_name()
            
            if world_description:
                welcome_text = (
                    f"{i18n_service.get_text(user_id, 'start_welcome', name=user_name)}\n\n"
                    f"{i18n_service.get_text(user_id, 'world_description', description=world_description)}\n\n"
                    f"{i18n_service.get_text(user_id, 'adventure_awaits')}\n\n"
                    f"{i18n_service.get_text(user_id, 'start.returning_with_hero', hero_name=hero_name, hero_class=hero_class, level=player.level, experience=player.experience)}"
                )
            else:
                welcome_text = (
                    f"{i18n_service.get_text(user_id, 'fallback_welcome')}\n\n"
                    f"{i18n_service.get_text(user_id, 'fallback_world', description='Embark on epic quests in a medieval fantasy world!')}\n\n"
                    f"{i18n_service.get_text(user_id, 'adventure_awaits')}\n\n"
                    f"{i18n_service.get_text(user_id, 'start.returning_with_hero', hero_name=hero_name, hero_class=hero_class, level=player.level, experience=player.experience)}"
                )
            
            # Create quest/adventure keyboard
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
                        text=i18n_service.get_text(user_id, 'btn.regions'), 
                        callback_data="view_regions"
                    )
                ]
            ])
        
        # Store initial data in FSM
        await state.update_data(
            user_name=user_name,
            world_description=world_description,
            start_time=message.date.isoformat()
        )
        
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
        
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
            i18n_service.get_text(user_id, 'error_fallback_welcome')
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
            help_text += f"\n\n{i18n_service.get_text(user_id, 'current_state', state=current_state)}"
        
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
            i18n_service.get_text(user_id, 'help_error')
        )


# Callback handlers for start command buttons
@router.callback_query(F.data == "start_quest")
async def start_quest_from_button(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Start quest from start command button."""
    # Import here to avoid circular imports
    from app.handlers.commands.game import cmd_quest
    
    # Create a fake message object for the quest command
    class FakeMessage:
        def __init__(self, callback_query):
            self.from_user = callback_query.from_user
            self.chat = callback_query.message.chat
            self.message_id = callback_query.message.message_id
            self.date = callback_query.message.date
        
        async def answer(self, text, **kwargs):
            await callback.message.edit_text(text, **kwargs)
    
    fake_message = FakeMessage(callback)
    await cmd_quest(fake_message, state, db_session, fsm_service)


@router.callback_query(F.data == "start_adventure")
async def start_adventure_from_button(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Start adventure from start command button."""
    # Import here to avoid circular imports
    from app.handlers.game import cmd_adventure
    
    # Create a fake message object for the adventure command
    class FakeMessage:
        def __init__(self, callback_query):
            self.from_user = callback_query.from_user
            self.chat = callback_query.message.chat
            self.message_id = callback_query.message.message_id
            self.date = callback_query.message.date
        
        async def answer(self, text, **kwargs):
            await callback.message.edit_text(text, **kwargs)
    
    fake_message = FakeMessage(callback)
    await cmd_adventure(fake_message, state, db_session, fsm_service)


@router.callback_query(F.data == "view_regions")
async def view_regions_from_button(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """View regions from start command button."""
    # Import here to avoid circular imports
    from app.handlers.commands.regions import cmd_regions
    from app.services.i18n_service import i18n_service
    
    # Create a fake message object for the regions command
    class FakeMessage:
        def __init__(self, callback_query):
            self.from_user = callback_query.from_user
            self.chat = callback_query.message.chat
            self.message_id = callback_query.message.message_id
            self.date = callback_query.message.date
        
        async def answer(self, text, **kwargs):
            await callback.message.edit_text(text, **kwargs)
    
    fake_message = FakeMessage(callback)
    await cmd_regions(fake_message, state, db_session, fsm_service, i18n_service)
