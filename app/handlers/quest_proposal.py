"""
Quest proposal handlers for the Telegram RPG game bot.

This module handles the pre-quest loop where players can interact with quest proposals,
ask for additional information, and make decisions about accepting or refusing quests.
"""

import random
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.logging_service import get_logger
from app.services.i18n_service import i18n_service
from app.services.fsm_service import FSMStateService
from app.handlers.keyboards import build_quest_proposal_keyboard, build_actions_kb
from app.handlers.callbacks import ActionCB
from app.game.states import GameStates
from app.game.actions import Action, ActionProcessor, get_available_actions
from app.models.player_progress import QuestProposal, PlayerReputation
from app.models.user import User
from app.core.config import settings

router = Router()
logger = get_logger(__name__)


@router.callback_query(F.data == "quest_ask_info")
async def handle_quest_ask_info(cb: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Handle asking for additional quest information."""
    try:
        telegram_id = cb.from_user.id
        
        # Get current quest proposal from FSM data
        fsm_data = await state.get_data()
        quest_proposal_id = fsm_data.get("quest_proposal_id")
        
        if not quest_proposal_id:
            await cb.answer("❌ No quest proposal found", show_alert=True)
            return
        
        # Get quest proposal from database
        result = await db_session.execute(
            select(QuestProposal).where(QuestProposal.id == quest_proposal_id)
        )
        quest_proposal = result.scalar_one_or_none()
        
        if not quest_proposal or not quest_proposal.can_ask_info():
            await cb.answer(i18n_service.get_text(user_id, "quest_proposal.info_used"), show_alert=True)
            return
        
        # Mark that player has asked for info
        quest_proposal.ask_for_info()
        await db_session.commit()
        
        # Generate additional information based on quest type
        additional_info = _generate_additional_info(quest_proposal)
        quest_proposal.additional_info = additional_info
        await db_session.commit()
        
        # Update FSM data
        await state.update_data(quest_proposal_id=quest_proposal_id)
        
        # Get localized text
        questgiver_name = quest_proposal.questgiver_name
        additional_text = i18n_service.get_text(telegram_id, "quest_proposal.additional_info").format(
            questgiver_name=questgiver_name,
            additional_info=additional_info
        )
        
        # Update message with additional info and new keyboard
        keyboard = build_quest_proposal_keyboard(can_ask_info=False, locale="uk")
        
        response_text = (
            f"{i18n_service.get_text(telegram_id, 'quest_proposal.title')}\n\n"
            f"{i18n_service.get_text(telegram_id, 'quest_proposal.questgiver_intro').format(questgiver_name=questgiver_name, quest_intro=quest_proposal.quest_intro)}\n\n"
            f"{i18n_service.get_text(telegram_id, 'quest_proposal.quest_description').format(description=quest_proposal.quest_description)}\n\n"
            f"{additional_text}\n\n"
            f"{i18n_service.get_text(telegram_id, 'quest_proposal.what_will_you_do')}"
        )
        
        await cb.message.edit_text(response_text, reply_markup=keyboard, parse_mode="HTML")
        await cb.answer()
        
        logger.info("Player asked for quest info", 
                   user_id=telegram_id,
                   quest_proposal_id=quest_proposal_id)
        
    except Exception as e:
        logger.error("Error in quest ask info handler", 
                    user_id=cb.from_user.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await cb.answer("❌ Error processing request", show_alert=True)


@router.callback_query(F.data == "quest_accept")
async def handle_quest_accept(cb: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Handle accepting a quest proposal."""
    try:
        telegram_id = cb.from_user.id
        
        # Get current quest proposal from FSM data
        fsm_data = await state.get_data()
        quest_proposal_id = fsm_data.get("quest_proposal_id")
        
        if not quest_proposal_id:
            await cb.answer("❌ No quest proposal found", show_alert=True)
            return
        
        # Get quest proposal from database
        result = await db_session.execute(
            select(QuestProposal).where(QuestProposal.id == quest_proposal_id)
        )
        quest_proposal = result.scalar_one_or_none()
        
        if not quest_proposal or not quest_proposal.is_pending():
            await cb.answer("❌ Quest proposal no longer available", show_alert=True)
            return
        
        # Mark quest as accepted
        quest_proposal.accept_quest()
        await db_session.commit()
        
        # Update FSM state to quest active
        await state.set_state(GameStates.QUEST_ACTIVE)
        
        # Create initial quest scene and player state
        from app.game.scenes import create_quest_scene, PlayerState
        from app.handlers.keyboards import build_actions_kb
        from app.game.actions import get_available_actions
        
        # Create or get player state
        player_state = await _get_or_create_player_state(telegram_id, state)
        
        # Create quest scene based on the accepted quest
        quest_scene = create_quest_scene(
            user_id=telegram_id,
            message_id=cb.message.message_id,
            quest_description=quest_proposal.quest_description
        )
        
        # Set current scene
        player_state.current_scene = quest_scene.scene_id
        
        # Get available actions for quest start
        available_actions = get_available_actions("quest_start", player_state)
        
        # Build keyboard
        user_language = i18n_service.get_user_language(telegram_id)
        keyboard = build_actions_kb(
            actions=available_actions,
            locale=user_language,
            scene_id=quest_scene.scene_id,
            context_hint=quest_proposal.quest_description,
            row_width=2
        )
        
        # Update FSM data
        await state.update_data(
            quest_proposal_id=None,  # Clear quest proposal data
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
            },
            current_scene=quest_scene.scene_id,
            scene_description=quest_scene.description,
            available_actions=available_actions,
            quest_data={
                "questgiver_name": quest_proposal.questgiver_name,
                "quest_description": quest_proposal.quest_description,
                "reward_gold": quest_proposal.reward_gold,
                "reward_xp": quest_proposal.reward_xp,
                "risk_level": quest_proposal.risk_level,
                "faction": quest_proposal.faction
            }
        )
        
        # Get localized text
        accepted_text = i18n_service.get_text(telegram_id, "quest_proposal.accepted")
        accepted_message = i18n_service.get_text(telegram_id, "quest_proposal.accepted_message")
        
        response_text = (
            f"{accepted_text}\n\n"
            f"{accepted_message}\n\n"
            f"📜 **Quest:** {quest_proposal.quest_description}\n\n"
            f"🎯 **Rewards:** {quest_proposal.reward_gold} gold, {quest_proposal.reward_xp} XP\n"
            f"⚠️ **Risk Level:** {quest_proposal.risk_level}/5\n\n"
            f"{quest_scene.description}\n\n"
            f"🎯 **What will you do?**"
        )
        
        await cb.message.edit_text(response_text, reply_markup=keyboard, parse_mode="HTML")
        await cb.answer()
        
        logger.info("Player accepted quest", 
                   user_id=telegram_id,
                   quest_proposal_id=quest_proposal_id,
                   questgiver=quest_proposal.questgiver_name)
        
    except Exception as e:
        logger.error("Error in quest accept handler", 
                    user_id=cb.from_user.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await cb.answer("❌ Error processing request", show_alert=True)


@router.callback_query(F.data == "quest_refuse")
async def handle_quest_refuse(cb: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Handle refusing a quest proposal."""
    try:
        telegram_id = cb.from_user.id
        
        # Get current quest proposal from FSM data
        fsm_data = await state.get_data()
        quest_proposal_id = fsm_data.get("quest_proposal_id")
        
        if not quest_proposal_id:
            await cb.answer("❌ No quest proposal found", show_alert=True)
            return
        
        # Get quest proposal from database
        result = await db_session.execute(
            select(QuestProposal).where(QuestProposal.id == quest_proposal_id)
        )
        quest_proposal = result.scalar_one_or_none()
        
        if not quest_proposal or not quest_proposal.is_pending():
            await cb.answer("❌ Quest proposal no longer available", show_alert=True)
            return
        
        # Mark quest as refused
        quest_proposal.refuse_quest()
        await db_session.commit()
        
        # Generate refusal consequence
        consequence = _generate_refusal_consequence(quest_proposal)
        
        # Apply reputation changes if any
        if consequence.get("reputation_change") and quest_proposal.faction:
            await _apply_reputation_change(
                db_session, user_id, quest_proposal.faction, 
                consequence["reputation_change"]
            )
        
        # Update FSM state back to menu
        await state.set_state(GameStates.MENU)
        
        # Clear quest proposal data from FSM
        await state.update_data(quest_proposal_id=None)
        
        # Get localized text
        refused_text = i18n_service.get_text(telegram_id, "quest_proposal.refused")
        questgiver_name = quest_proposal.questgiver_name
        
        # Build response based on consequence
        response_text = f"{refused_text}\n\n"
        
        if consequence["type"] == "insult":
            response_text += i18n_service.get_text(telegram_id, "quest_proposal.refused_insult").format(
                questgiver_name=questgiver_name
            )
        elif consequence["type"] == "insist":
            response_text += i18n_service.get_text(telegram_id, "quest_proposal.refused_insist").format(
                questgiver_name=questgiver_name
            )
        elif consequence["type"] == "warning":
            response_text += i18n_service.get_text(telegram_id, "quest_proposal.refused_warning").format(
                questgiver_name=questgiver_name
            )
        
        # Add reputation change message if applicable
        if consequence.get("reputation_change") and quest_proposal.faction:
            response_text += f"\n\n{i18n_service.get_text(telegram_id, 'quest_proposal.reputation_lost').format(faction=quest_proposal.faction)}"
        
        response_text += f"\n\n{i18n_service.get_text(telegram_id, 'quest_proposal.searching_new')}"
        
        await cb.message.edit_text(response_text, parse_mode="HTML")
        await cb.answer()
        
        logger.info("Player refused quest", 
                   user_id=telegram_id,
                   quest_proposal_id=quest_proposal_id,
                   questgiver=quest_proposal.questgiver_name,
                   consequence=consequence["type"])
        
    except Exception as e:
        logger.error("Error in quest refuse handler", 
                    user_id=cb.from_user.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await cb.answer("❌ Error processing request", show_alert=True)


def _generate_additional_info(quest_proposal: QuestProposal) -> str:
    """Generate additional information for a quest proposal."""
    questgiver = quest_proposal.questgiver_name
    risk_level = quest_proposal.risk_level
    
    # Generate additional info based on quest characteristics
    additional_info_templates = [
        f"Кажуть, там лежать стародавні скарби, але хто заходив — не повертався. Нагорода буде щедрою!",
        f"Останній герой, який наважився туди піти, зник безвісти. Але я можу запропонувати тобі {quest_proposal.reward_gold} золота.",
        f"Це небезпечно, але ти виглядаєш на {quest_proposal.risk_level} з 5. Можливо, ти впораєшся.",
        f"Я чув, що там є магічні артефакти. Варто ризикнути за {quest_proposal.reward_xp} досвіду!",
        f"Місцеві жителі бояться туди ходити. Але для героя твого рівня це має бути просто.",
    ]
    
    # Add faction-specific info if available
    if quest_proposal.faction:
        faction_info = {
            "Маги Ордену": "Орден має багато ресурсів і може добре винагородити.",
            "Гільдія Мисливців": "Гільдія відома своєю щедрістю до успішних мисливців.",
            "Королівська Гвардія": "Король особисто зацікавлений у виконанні цього завдання.",
            "Темне Братство": "Братство не терпить невдач. Але нагороди там справді великі.",
        }
        if quest_proposal.faction in faction_info:
            additional_info_templates.append(faction_info[quest_proposal.faction])
    
    return random.choice(additional_info_templates)


def _generate_refusal_consequence(quest_proposal: QuestProposal) -> dict:
    """Generate consequences for refusing a quest."""
    # Weighted random selection of consequence types
    consequences = [
        {"type": "insult", "weight": 40, "reputation_change": -5},
        {"type": "insist", "weight": 30, "reputation_change": 0},
        {"type": "warning", "weight": 30, "reputation_change": 0},
    ]
    
    # Adjust weights based on quest characteristics
    if quest_proposal.risk_level >= 4:
        # High risk quests are more likely to get warning
        consequences[2]["weight"] += 20
    elif quest_proposal.reward_gold >= 100:
        # High reward quests are more likely to get insult
        consequences[0]["weight"] += 20
    
    # Select consequence based on weights
    total_weight = sum(c["weight"] for c in consequences)
    rand = random.randint(1, total_weight)
    
    current_weight = 0
    for consequence in consequences:
        current_weight += consequence["weight"]
        if rand <= current_weight:
            return consequence
    
    # Fallback
    return consequences[0]


async def _apply_reputation_change(db_session: AsyncSession, user_id: int, faction: str, change: int):
    """Apply reputation change for a faction."""
    try:
        # Get or create reputation record
        result = await db_session.execute(
            select(PlayerReputation).where(
                PlayerReputation.user_id == user_id,
                PlayerReputation.faction == faction
            )
        )
        reputation = result.scalar_one_or_none()
        
        if not reputation:
            reputation = PlayerReputation(user_id=user_id, faction=faction)
            db_session.add(reputation)
        
        reputation.modify_reputation(change)
        await db_session.commit()
        
        logger.info("Applied reputation change", 
                   user_id=user_id,
                   faction=faction,
                   change=change,
                   new_reputation=reputation.reputation)
        
    except Exception as e:
        logger.error("Error applying reputation change", 
                    user_id=user_id,
                    faction=faction,
                    change=change,
                    error=str(e))
        # Don't raise - reputation is not critical


async def _get_or_create_player_state(user_id: int, state: FSMContext):
    """Get or create player state from FSM data."""
    from app.game.scenes import PlayerState
    
    fsm_data = await state.get_data()
    player_state_dict = fsm_data.get("player_state_dict")
    
    if player_state_dict:
        # Recreate PlayerState from dict
        player_state = PlayerState(
            user_id=player_state_dict["user_id"],
            energy=player_state_dict["energy"],
            risk_level=player_state_dict["risk_level"],
            stats=player_state_dict["stats"],
            current_scene=player_state_dict["current_scene"],
            visited_scenes=set(player_state_dict["visited_scenes"]),
            scene_cooldowns=player_state_dict["scene_cooldowns"],
            goals=set(player_state_dict["goals"]),
            step_count=player_state_dict["step_count"]
        )
    else:
        # Create new player state
        player_state = PlayerState(
            user_id=user_id,
            energy=100,
            risk_level=1,
            stats={"bravery": 1, "charisma": 1, "intellect": 1, "stamina": 1},
            current_scene="quest_start",
            visited_scenes=set(),
            scene_cooldowns={},
            goals=set(),
            step_count=0
        )
    
    return player_state


async def create_quest_proposal(
    db_session: AsyncSession,
    user_id: int,
    questgiver_name: str,
    quest_intro: str,
    quest_description: str,
    faction: str = None,
    reward_gold: int = 0,
    reward_xp: int = 0,
    risk_level: int = 1
) -> QuestProposal:
    """Create a new quest proposal."""
    quest_proposal = QuestProposal(
        user_id=user_id,
        questgiver_name=questgiver_name,
        quest_intro=quest_intro,
        quest_description=quest_description,
        faction=faction,
        reward_gold=reward_gold,
        reward_xp=reward_xp,
        risk_level=risk_level
    )
    
    db_session.add(quest_proposal)
    await db_session.commit()
    await db_session.refresh(quest_proposal)
    
    return quest_proposal


@router.callback_query(ActionCB.filter(), GameStates.QUEST_ACTIVE)
async def handle_quest_action(cb: CallbackQuery, callback_data: ActionCB, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle action button presses during active quest."""
    try:
        user_id = cb.from_user.id
        action = callback_data.a
        scene_id = callback_data.s
        
        # Get current FSM data
        fsm_data = await state.get_data()
        player_state_dict = fsm_data.get("player_state_dict")
        current_scene_id = fsm_data.get("current_scene")
        quest_data = fsm_data.get("quest_data")
        
        if not player_state_dict or not current_scene_id or not quest_data:
            await cb.answer("❌ Quest state not found", show_alert=True)
            return
        
        # Recreate player state
        player_state = await _get_or_create_player_state(user_id, state)
        
        # Process the action
        scene_context = {
            "scene_type": "quest",
            "scene_id": current_scene_id,
            "risk_level": quest_data["risk_level"],
            "quest_description": quest_data["quest_description"]
        }
        
        consequence = ActionProcessor.process_action(action, player_state, scene_context)
        action_result = ActionProcessor.apply_consequence(consequence, player_state)
        
        # Handle quest completion
        if action == Action.COMPLETE_QUEST:
            await _complete_quest(cb, player_state, quest_data, state, fsm_service)
            return
        
        # Handle quest failure
        if player_state.energy <= 0:
            await _fail_quest(cb, player_state, quest_data, state, fsm_service)
            return
        
        # Generate next scene based on action
        next_scene_description = await _generate_quest_scene_description(action, quest_data, player_state)
        
        # Get available actions for next scene
        available_actions = get_available_actions("quest", player_state)
        
        # Build keyboard
        user_language = i18n_service.get_user_language(user_id)
        keyboard = build_actions_kb(
            actions=available_actions,
            locale=user_language,
            scene_id=current_scene_id,
            context_hint=next_scene_description,
            row_width=2
        )
        
        # Update FSM data
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
            },
            scene_description=next_scene_description,
            available_actions=available_actions
        )
        
        # Build response text
        response_text = (
            f"📜 **Quest Progress**\n\n"
            f"{next_scene_description}\n\n"
            f"⚡ **Energy:** {player_state.energy}/100\n"
            f"📊 **Stats:** Bravery: {player_state.stats.get('bravery', 1)}, "
            f"Charisma: {player_state.stats.get('charisma', 1)}, "
            f"Intellect: {player_state.stats.get('intellect', 1)}, "
            f"Stamina: {player_state.stats.get('stamina', 1)}\n\n"
            f"🎯 **What will you do?**"
        )
        
        await cb.message.edit_text(response_text, reply_markup=keyboard, parse_mode="HTML")
        await cb.answer()
        
        logger.info("Player made quest action", 
                   user_id=user_id,
                   action=action,
                   scene_id=scene_id,
                   energy=player_state.energy)
        
    except Exception as e:
        logger.error("Error in quest action handler", 
                    user_id=cb.from_user.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await cb.answer("❌ Error processing action", show_alert=True)


async def _complete_quest(cb: CallbackQuery, player_state, quest_data: dict, state: FSMContext, fsm_service: FSMStateService):
    """Handle quest completion."""
    try:
        user_id = cb.from_user.id
        
        # Calculate rewards
        reward_gold = quest_data["reward_gold"]
        reward_xp = quest_data["reward_xp"]
        
        # Apply rewards to player (this would need to be implemented in your player system)
        # For now, we'll just show the completion message
        
        # Update FSM state back to menu
        await state.set_state(GameStates.MENU)
        await state.update_data(
            player_state_dict=None,
            current_scene=None,
            quest_data=None
        )
        
        # Get localized text
        completion_text = i18n_service.get_text(user_id, "quest_proposal.completed")
        reward_text = i18n_service.get_text(user_id, "quest_proposal.rewards_received")
        
        response_text = (
            f"🎉 {completion_text} 🎉\n\n"
            f"📜 **Quest:** {quest_data['quest_description']}\n\n"
            f"🏆 {reward_text}\n"
            f"💰 **Gold:** +{reward_gold}\n"
            f"⭐ **XP:** +{reward_xp}\n\n"
            f"💡 *Use /quest for another adventure!*"
        )
        
        await cb.message.edit_text(response_text, parse_mode="HTML")
        await cb.answer()
        
        logger.info("Player completed quest", 
                   user_id=user_id,
                   questgiver=quest_data["questgiver_name"],
                   reward_gold=reward_gold,
                   reward_xp=reward_xp)
        
    except Exception as e:
        logger.error("Error completing quest", 
                    user_id=cb.from_user.id,
                    error=str(e))
        await cb.answer("❌ Error completing quest", show_alert=True)


async def _fail_quest(cb: CallbackQuery, player_state, quest_data: dict, state: FSMContext, fsm_service: FSMStateService):
    """Handle quest failure."""
    try:
        user_id = cb.from_user.id
        
        # Update FSM state back to menu
        await state.set_state(GameStates.MENU)
        await state.update_data(
            player_state_dict=None,
            current_scene=None,
            quest_data=None
        )
        
        # Get localized text
        failure_text = i18n_service.get_text(user_id, "quest_proposal.failed")
        
        response_text = (
            f"💀 {failure_text} 💀\n\n"
            f"📜 **Quest:** {quest_data['quest_description']}\n\n"
            f"⚡ **Energy:** {player_state.energy}/100\n\n"
            f"💡 *Rest and try again with /quest!*"
        )
        
        await cb.message.edit_text(response_text, parse_mode="HTML")
        await cb.answer()
        
        logger.info("Player failed quest", 
                   user_id=user_id,
                   questgiver=quest_data["questgiver_name"],
                   energy=player_state.energy)
        
    except Exception as e:
        logger.error("Error failing quest", 
                    user_id=cb.from_user.id,
                    error=str(e))
        await cb.answer("❌ Error processing quest failure", show_alert=True)


async def _generate_quest_scene_description(action: str, quest_data: dict, player_state) -> str:
    """Generate scene description based on quest action."""
    questgiver = quest_data["questgiver_name"]
    quest_description = quest_data["quest_description"]
    
    # Generate different descriptions based on action
    if action == "explore":
        return f"Ви досліджуєте місцевість, шукаючи підказки для виконання завдання від {questgiver}. {quest_description}"
    elif action == "investigate":
        return f"Ви ретельно розслідуєте обставини завдання. {questgiver} буде задоволений вашою обережністю."
    elif action == "negotiate":
        return f"Ви намагаєтесь домовитись з місцевими жителями про допомогу з завданням від {questgiver}."
    elif action == "fight":
        return f"Ви готуєтесь до битви! Завдання від {questgiver} вимагає мужності та сили."
    elif action == "complete_quest":
        return f"Ви успішно виконали завдання від {questgiver}! Час повертатись за винагородою."
    else:
        return f"Ви продовжуєте працювати над завданням від {questgiver}. {quest_description}"
