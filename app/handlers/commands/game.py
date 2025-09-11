from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai import AIGenerationService, ai_action_service
from app.services.logging_service import get_logger
from app.services.i18n_service import i18n_service
from app.services.fsm_service import FSMStateService
from app.handlers.keyboards import build_actions_kb
from app.handlers.callbacks import ActionCB
from app.game.actions import Action, ActionProcessor, get_available_actions
from app.game.states import GameStates
from app.game.scenes import create_quest_scene, create_demo_scene, PlayerState
from app.core.config import settings

router = Router()
logger = get_logger(__name__)

@router.message(Command("quest"))
async def cmd_quest(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle the /quest command - generate and provide a new quest description."""
    try:
        user_id = message.from_user.id
        
        # Check if user has a hero first
        from app.handlers.utils import check_hero_required
        has_hero, user = await check_hero_required(message, db_session)
        if not has_hero:
            return
        
        # Set FSM state to quest proposal
        await state.set_state(GameStates.QUEST_PROPOSAL)
        
        # Create or get player state
        player_state = await _get_or_create_player_state(user_id, state)
        
        # Check if player has enough energy for quest
        if player_state.energy < 10:  # Minimum energy for quest
            await message.answer(
                f"⚡ **Not Enough Energy**\n\n"
                f"Your energy is too low to start a quest.\n"
                f"Current energy: {player_state.energy}/100\n\n"
                f"💡 *Rest or wait for energy to regenerate.*"
            )
            return
        
        # Show typing indicator
        await message.answer(i18n_service.get_text(user_id, 'quest_generating'), parse_mode="HTML")
        
        # Generate quest proposal using AI
        user_language = i18n_service.get_user_language(user_id)
        quest_data = await _generate_quest_proposal(user_language)
        
        # Create quest proposal in database
        from app.handlers.quest_proposal import create_quest_proposal
        quest_proposal = await create_quest_proposal(
            db_session=db_session,
            user_id=user.id,  # Use internal user ID, not telegram_id
            questgiver_name=quest_data["questgiver_name"],
            quest_intro=quest_data["quest_intro"],
            quest_description=quest_data["quest_description"],
            faction=quest_data.get("faction"),
            reward_gold=quest_data.get("reward_gold", 0),
            reward_xp=quest_data.get("reward_xp", 0),
            risk_level=quest_data.get("risk_level", 1)
        )
        
        # Store quest proposal ID in FSM
        await state.update_data(quest_proposal_id=quest_proposal.id)
        
        # Build quest proposal message
        quest_text = (
            f"{i18n_service.get_text(user_id, 'quest_proposal.title')}\n\n"
            f"{i18n_service.get_text(user_id, 'quest_proposal.questgiver_intro').format(questgiver_name=quest_proposal.questgiver_name, quest_intro=quest_proposal.quest_intro)}\n\n"
            f"{i18n_service.get_text(user_id, 'quest_proposal.quest_description').format(description=quest_proposal.quest_description)}\n\n"
            f"⚡ **Energy:** {player_state.energy}/100\n"
            f"⚠️ **Risk Level:** {player_state.risk_level}\n"
            f"📊 **Stats:** Bravery: {player_state.stats.get('bravery', 1)}, "
            f"Charisma: {player_state.stats.get('charisma', 1)}, "
            f"Intellect: {player_state.stats.get('intellect', 1)}, "
            f"Stamina: {player_state.stats.get('stamina', 1)}\n\n"
            f"{i18n_service.get_text(user_id, 'quest_proposal.what_will_you_do')}"
        )
        
        # Create quest proposal keyboard
        from app.handlers.keyboards import build_quest_proposal_keyboard
        keyboard = build_quest_proposal_keyboard(can_ask_info=True, locale=user_language)
        
        # Store player state in FSM (convert PlayerState to dict for JSON serialization)
        await state.update_data(
            player_state_dict={
                "user_id": player_state.user_id,
                "energy": player_state.energy,
                "risk_level": player_state.risk_level,
                "stats": player_state.stats,
                "current_scene": player_state.current_scene,
                "visited_scenes": list(player_state.visited_scenes),
                "scene_cooldowns": player_state.scene_cooldowns,
                "goals": list(player_state.goals),
                "step_count": player_state.step_count
            }
        )
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action="quest_proposal",
            scene_id=f"quest_proposal_{quest_proposal.id}",
            additional_data={"quest_proposal_id": quest_proposal.id}
        )
        
        await message.answer(quest_text, parse_mode="Markdown", reply_markup=keyboard)
        logger.info("User requested a quest", 
                   user_id=message.from_user.id,
                   user_name=message.from_user.first_name,
                   chat_id=message.chat.id)
        
    except Exception as e:
        logger.error("Error in quest command", 
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.answer(
            "❌ **Quest Generation Error**\n\n"
            "There was an error generating your quest. Please try again later.\n\n"
            "💡 **Hint:** Use /quest again in a few moments."
        )

@router.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle the /status command - show game status and current FSM state."""
    try:
        user_id = message.from_user.id
        
        # Check if user has a hero first
        from app.handlers.utils import check_hero_required
        has_hero, user = await check_hero_required(message, db_session)
        if not has_hero:
            return
        
        # Get current FSM state
        current_state = await state.get_state()
        fsm_data = await state.get_data()
        
        # Get session state from PostgreSQL
        session_state = await fsm_service.get_session_state(user_id)
        
        # Build status text
        status_text = (
            f"{i18n_service.get_text(user_id, 'game_status')}\n\n"
            f"{i18n_service.get_text(user_id, 'current_game')}\n"
            f"{i18n_service.get_text(user_id, 'player_level')}\n"
            f"{i18n_service.get_text(user_id, 'experience')}\n"
            f"{i18n_service.get_text(user_id, 'gold')}\n"
            f"{i18n_service.get_text(user_id, 'inventory')}\n\n"
        )
        
        # Add FSM state information
        if current_state:
            status_text += f"🎮 **Current State:** `{current_state}`\n"
        
        if session_state:
            status_text += f"📊 **Session:** {session_state['session_id'][:8]}...\n"
            status_text += f"⚡ **Actions:** {session_state['actions_count']}\n"
            status_text += f"💬 **Messages:** {session_state['messages_count']}\n"
        
        if fsm_data:
            status_text += f"📝 **FSM Data:** {len(fsm_data)} items\n"
        
        status_text += (
            f"\n{i18n_service.get_text(user_id, 'under_development')}\n\n"
            f"{i18n_service.get_text(user_id, 'status_hint')}"
        )
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action="status_check",
            scene_id=fsm_data.get("scene_id")
        )
        
        await message.answer(status_text, parse_mode="Markdown")
        logger.info("User requested game status", 
                   user_id=message.from_user.id,
                   user_name=message.from_user.first_name,
                   chat_id=message.chat.id,
                   current_state=current_state)
        
    except Exception as e:
        logger.error("Error in status command", 
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await message.answer(
            "❌ **Status Error**\n\n"
            "There was an error retrieving your status. Please try again later."
        )

@router.message(Command("demo_actions"))
async def demo_actions(msg: Message, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle the /demo_actions command - demonstrate action buttons."""
    try:
        user_id = msg.from_user.id
        
        # Set FSM state to combat active
        await state.set_state(GameStates.COMBAT_ACTIVE)
        
        locale = i18n_service.get_user_language(user_id)
        scene_id = "intro-wolf-001"
        actions = [Action.ATTACK, Action.TALK, Action.SNEAK, Action.FLEE, Action.RUN_AI, Action.BACK]
        
        kb = build_actions_kb(
            actions=actions,
            locale=locale,
            scene_id=scene_id,
            context_hint="A wolf blocks the path in a dark forest."
        )
        
        # Store demo data in FSM
        await state.update_data(
            scene_id=scene_id,
            actions=actions,
            context_hint="A wolf blocks the path in a dark forest.",
            demo_mode=True
        )
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action="demo_actions",
            scene_id=scene_id,
            additional_data={"demo_mode": True}
        )
        
        # Use localized text for the message
        if locale == "uk":
            message_text = "Ти стоїш перед вовком. Що робитимеш?"
        else:
            message_text = "You stand before a wolf. What will you do?"
        
        await msg.answer(message_text, reply_markup=kb)
        logger.info("User requested demo actions", 
                   user_id=user_id,
                   user_name=msg.from_user.first_name,
                   chat_id=msg.chat.id)
        
    except Exception as e:
        logger.error("Error in demo_actions command", 
                    user_id=msg.from_user.id,
                    chat_id=msg.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await msg.answer("❌ **Demo Actions Error**\n\nThere was an error loading the demo actions. Please try again later.")

@router.callback_query(ActionCB.filter())
async def on_action_press(cb: CallbackQuery, callback_data: ActionCB, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle action button presses with real game effects."""
    try:
        user_id = cb.from_user.id
        action = callback_data.a   # e.g. "attack"
        scene_id = callback_data.s
        
        # Get current FSM state and data
        current_state = await state.get_state()
        fsm_data = await state.get_data()
        
        # Get or create player state
        player_state = await _get_or_create_player_state(user_id, state)
        
        # Handle RUN_AI action with AI generation and logging
        if action == Action.RUN_AI:
            # Create scene context for AI generation
            scene_context = create_demo_scene(scene_id, fsm_data.get("context_hint", "Unknown scene"))
            
            # Execute AI action with logging
            ai_response = await ai_action_service.execute_run_ai_action(
                user_id=user_id,
                action=action,
                scene_context=scene_context,
                db_session=db_session,
                game_session_id=fsm_data.get("game_session_id"),
                additional_context={
                    "fsm_state": current_state,
                    "fsm_data": fsm_data,
                    "player_stats": player_state.stats,
                    "energy": player_state.energy,
                    "risk_level": player_state.risk_level
                }
            )
            
            if ai_response:
                response_text = (
                    f"🤖 **AI Action Executed**\n\n"
                    f"{ai_response}\n\n"
                    f"Action: `{action}`\n"
                    f"Scene: `{scene_id}`\n"
                    f"State: `{current_state}`\n\n"
                    f"*AI generation logged to database!*"
                )
            else:
                response_text = (
                    f"❌ **AI Action Failed**\n\n"
                    f"Action: `{action}`\n"
                    f"Scene: `{scene_id}`\n"
                    f"State: `{current_state}`\n\n"
                    f"*AI generation failed, but attempt was logged.*"
                )
            
            await cb.message.edit_text(response_text, parse_mode="Markdown")
            return
        
        # Process the action with real game effects
        scene_context = {
            "scene_type": "quest",
            "scene_id": scene_id,
            "risk_level": player_state.risk_level
        }
        
        consequence = ActionProcessor.process_action(action, player_state, scene_context)
        action_result = ActionProcessor.apply_consequence(consequence, player_state)
        
        # Update FSM state based on action
        if action == Action.BACK:
            await state.set_state(GameStates.MENU)
        elif action in [Action.ATTACK, Action.DEFEND, Action.CAST, Action.FIGHT]:
            await state.set_state(GameStates.COMBAT_CHOICE)
        elif action in [Action.TALK, Action.INVESTIGATE, Action.SCOUT]:
            await state.set_state(GameStates.DIALOGUE_CHOICE)
        elif action == Action.ACCEPT:
            await state.set_state(GameStates.QUEST_CHOICE)
        elif action == Action.RETREAT:
            await state.set_state(GameStates.MENU)
        else:
            # Keep current state for other actions
            pass
        
        # Update FSM data with action info and player state (convert to dict for JSON serialization)
        await state.update_data(
            last_action=action,
            last_scene_id=scene_id,
            action_count=fsm_data.get("action_count", 0) + 1,
            player_state_dict={
                "user_id": player_state.user_id,
                "energy": player_state.energy,
                "risk_level": player_state.risk_level,
                "stats": player_state.stats,
                "current_scene": player_state.current_scene,
                "visited_scenes": list(player_state.visited_scenes),
                "scene_cooldowns": player_state.scene_cooldowns,
                "goals": list(player_state.goals),
                "step_count": player_state.step_count
            }
        )
        
        # Sync FSM state to PostgreSQL
        await fsm_service.sync_fsm_to_postgres(
            state,
            user_id,
            action=action,
            scene_id=scene_id,
            additional_data={
                "action_type": action,
                "action_result": action_result,
                "player_stats": player_state.stats,
                "energy": player_state.energy,
                "risk_level": player_state.risk_level
            }
        )
        
        await cb.answer()  # small UX improvement
        
        # Create a more informative response with game effects
        response_text = (
            f"🎮 **Action Executed**\n\n"
            f"Action: `{action}`\n"
            f"Result: {action_result['message']}\n\n"
            f"📊 **Effects:**\n"
            f"• Energy: {player_state.energy}/100\n"
            f"• Risk Level: {player_state.risk_level}\n"
            f"• Stats: {player_state.stats}\n\n"
            f"Scene: `{scene_id}`\n"
            f"State: `{current_state}` → `{await state.get_state()}`\n\n"
            f"*Action processed and logged!*"
        )
        
        await cb.message.edit_text(response_text, parse_mode="Markdown")
        
        logger.info("User executed action", 
                   user_id=user_id,
                   user_name=cb.from_user.first_name,
                   chat_id=cb.message.chat.id,
                   action=action,
                   scene_id=scene_id,
                   old_state=current_state,
                   new_state=await state.get_state(),
                   energy=player_state.energy,
                   risk_level=player_state.risk_level)
        
    except Exception as e:
        logger.error("Error in action callback", 
                    user_id=cb.from_user.id,
                    chat_id=cb.message.chat.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await cb.answer("❌ Error processing action", show_alert=True)


async def _get_or_create_player_state(user_id: int, state: FSMContext) -> PlayerState:
    """Get or create player state from FSM data."""
    fsm_data = await state.get_data()
    player_state_dict = fsm_data.get("player_state_dict")
    
    if not player_state_dict:
        # Create new player state
        player_state = PlayerState(
            user_id=user_id,
            energy=settings.default_energy,
            risk_level=0,
            stats={
                "bravery": 1, "charisma": 1, "intellect": 1, 
                "stamina": 1, "level": 1, "gold": 0, "xp": 0
            }
        )
    else:
        # Recreate PlayerState from dict
        player_state = PlayerState(
            user_id=player_state_dict["user_id"],
            energy=player_state_dict["energy"],
            risk_level=player_state_dict["risk_level"],
            stats=player_state_dict["stats"],
            current_scene=player_state_dict.get("current_scene"),
            visited_scenes=set(player_state_dict.get("visited_scenes", [])),
            scene_cooldowns=player_state_dict.get("scene_cooldowns", {}),
            goals=set(player_state_dict.get("goals", [])),
            step_count=player_state_dict.get("step_count", 0)
        )
        
        # Ensure energy doesn't exceed maximum
        player_state.energy = min(player_state.energy, settings.max_energy)
    
    return player_state


async def _generate_quest_proposal(language: str) -> dict:
    """Generate a quest proposal with questgiver, intro, and description."""
    import random
    
    # Questgiver names and factions
    questgivers = [
        {"name": "Сивий маг", "faction": "Маги Ордену"},
        {"name": "Капітан гвардії", "faction": "Королівська Гвардія"},
        {"name": "Старий мисливець", "faction": "Гільдія Мисливців"},
        {"name": "Тіньовий агент", "faction": "Темне Братство"},
        {"name": "Дерев'яний друїд", "faction": "Коло Друїдів"},
        {"name": "Коваль-майстер", "faction": "Гільдія Ремісників"},
    ]
    
    # Quest intro templates
    quest_intros = [
        "Слухай, воїн! Потрібна твоя допомога. У руїнах пробудилося давнє зло…",
        "Герою! Я бачу в тобі силу. Є справа, яка потребує твоєї мужності.",
        "Привіт, мандрівнику. Чи не хочеш заробити трохи золота?",
        "Слухай, друже! У мене є пропозиція, від якої ти не зможеш відмовитися.",
        "Воїне! Час показати свою доблесть. Є завдання, яке під силу тільки тобі.",
        "Молодий герою! Світ потребує твоєї допомоги. Чи готовий ти до виклику?",
    ]
    
    # Quest descriptions
    quest_descriptions = [
        "Розслідувати дивні звуки в стародавніх руїнах та з'ясувати джерело магічного порушення.",
        "Знайти та повернути вкрадену реліквію, яка належить королівській сім'ї.",
        "Очистити печеру від гоблінів, які нападають на торгові каравани.",
        "Доставити важливе послання до сусіднього міста через небезпечні території.",
        "Знайти зниклого дослідника, який вирушив у заборонені землі.",
        "Захистити село від нападу диких звірів під час нічної варти.",
    ]
    
    # Select random elements
    questgiver_data = random.choice(questgivers)
    quest_intro = random.choice(quest_intros)
    quest_description = random.choice(quest_descriptions)
    
    # Generate rewards based on risk level
    risk_level = random.randint(1, 5)
    reward_gold = random.randint(20, 100) + (risk_level * 20)
    reward_xp = random.randint(10, 50) + (risk_level * 10)
    
    return {
        "questgiver_name": questgiver_data["name"],
        "quest_intro": quest_intro,
        "quest_description": quest_description,
        "faction": questgiver_data["faction"],
        "reward_gold": reward_gold,
        "reward_xp": reward_xp,
        "risk_level": risk_level
    }
