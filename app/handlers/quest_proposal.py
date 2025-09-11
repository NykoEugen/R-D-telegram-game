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
from app.handlers.callbacks import ActionCB, QuestActionCB
from app.game.states import GameStates, QuestStates
from app.game.actions import Action, ActionProcessor, get_available_actions
from app.models.player_progress import QuestProposal, PlayerReputation
from app.models.user import User
from app.core.config import settings

router = Router()
logger = get_logger(__name__)


@router.callback_query(QuestActionCB.filter(F.action == "ask"), QuestStates.OFFER)
async def handle_quest_ask_info(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession):
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
            await cb.answer(i18n_service.get_text(telegram_id, "quest_proposal.info_used"), show_alert=True)
            return
        
        # Mark that player has asked for info
        quest_proposal.ask_for_info()
        await db_session.commit()
        
        # Generate additional information based on quest type
        additional_info = _generate_additional_info(quest_proposal)
        quest_proposal.additional_info = additional_info
        await db_session.commit()
        
        # Update FSM state to INVESTIGATED
        await state.set_state(QuestStates.INVESTIGATED)
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


@router.callback_query(QuestActionCB.filter(F.action == "accept"))
async def handle_quest_accept(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession):
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
        await state.set_state(QuestStates.ACTIVE)
        
        # Create initial quest scene and player state
        from app.game.scenes import create_quest_scene, PlayerState
        from app.handlers.keyboards import build_actions_kb
        from app.game.actions import get_available_actions
        from app.game.quest_system import quest_manager, QuestType
        
        # Create or get player state
        player_state = await _get_or_create_player_state(telegram_id, state)
        
        # Create quest using quest manager
        quest_data = {
            "user_id": telegram_id,
            "questgiver_name": quest_proposal.questgiver_name,
            "quest_intro": quest_proposal.quest_intro,
            "quest_description": quest_proposal.quest_description,
            "quest_type": "investigation",  # Default type, could be determined by quest content
            "risk_level": quest_proposal.risk_level,
            "reward_gold": quest_proposal.reward_gold,
            "reward_xp": quest_proposal.reward_xp,
            "faction": quest_proposal.faction,
            "additional_info": quest_proposal.additional_info
        }
        
        quest = quest_manager.create_quest(quest_data)
        quest = quest_manager.start_quest(telegram_id, quest)
        
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
        
        # Build keyboard using new quest action system
        user_language = i18n_service.get_user_language(telegram_id)
        keyboard = build_actions_kb(
            actions=available_actions,
            locale=user_language,
            scene_id=quest_scene.scene_id,
            context_hint=quest_scene.description,
            row_width=2,
            use_quest_callback=True
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


@router.callback_query(QuestActionCB.filter(F.action == "decline"))
async def handle_quest_refuse(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession):
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
        
        # Always apply -1 reputation penalty for declining quests
        if quest_proposal.faction:
            await _apply_reputation_change(
                db_session, telegram_id, quest_proposal.faction, 
                -1  # Always -1 reputation for declining
            )
            # Update consequence to reflect the reputation change
            consequence["reputation_change"] = -1
        
        # Update FSM state to complete
        await state.set_state(QuestStates.COMPLETE)
        
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
        elif consequence["type"] == "disappointed":
            response_text += i18n_service.get_text(telegram_id, "quest_proposal.refused_disappointed").format(
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
    # All consequences now have -1 reputation (applied separately)
    consequences = [
        {"type": "insult", "weight": 35, "reputation_change": -1},
        {"type": "insist", "weight": 30, "reputation_change": -1},
        {"type": "warning", "weight": 25, "reputation_change": -1},
        {"type": "disappointed", "weight": 10, "reputation_change": -1},
    ]
    
    # Adjust weights based on quest characteristics
    if quest_proposal.risk_level >= 4:
        # High risk quests are more likely to get warning or disappointed reaction
        consequences[2]["weight"] += 15  # warning
        consequences[3]["weight"] += 10  # disappointed
    elif quest_proposal.reward_gold >= 100:
        # High reward quests are more likely to get insult
        consequences[0]["weight"] += 15  # insult
    elif quest_proposal.risk_level <= 2:
        # Low risk quests are more likely to get insist reaction
        consequences[1]["weight"] += 15  # insist
    
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


@router.callback_query(QuestActionCB.filter(), QuestStates.ACTIVE)
async def handle_quest_action_callback(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle quest action callbacks."""
    await handle_quest_action(cb, callback_data, state, db_session, fsm_service)


async def handle_quest_action(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle action button presses during active quest."""
    try:
        user_id = cb.from_user.id
        action = callback_data.action
        scene_id = callback_data.scene_id
        
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
        
        # Process the action using quest manager
        from app.game.quest_system import quest_manager
        
        quest_result = quest_manager.process_quest_action(user_id, action, player_state)
        
        if "error" in quest_result:
            await cb.answer("❌ Quest state not found", show_alert=True)
            return
        
        action_result = quest_result["action_result"]
        next_scene = quest_result["next_scene"]
        completion_status = quest_result["completion_status"]
        
        # Handle quest completion
        if completion_status["completed"]:
            await _complete_quest_with_rewards(cb, quest_result["quest_completion"], state, fsm_service)
            return
        
        # Handle quest failure
        if completion_status["failed"]:
            await _fail_quest_with_reason(cb, quest_result["quest_failure"], state, fsm_service)
            return
        
        # Get available actions for next scene
        available_actions = next_scene["available_actions"]
        
        # Build keyboard
        user_language = i18n_service.get_user_language(user_id)
        keyboard = build_actions_kb(
            actions=available_actions,
            locale=user_language,
            scene_id=next_scene["scene_id"],
            context_hint=next_scene["description"],
            row_width=2,
            use_quest_callback=True
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
            scene_description=next_scene["description"],
            available_actions=available_actions,
            quest_progress=quest_result["quest_progress"]
        )
        
        # Build response text
        quest_progress = quest_result["quest_progress"]
        response_text = (
            f"📜 **Quest Progress**\n\n"
            f"{next_scene['description']}\n\n"
            f"⚡ **Energy:** {player_state.energy}/100\n"
            f"📊 **Stats:** Bravery: {player_state.stats.get('bravery', 1)}, "
            f"Charisma: {player_state.stats.get('charisma', 1)}, "
            f"Intellect: {player_state.stats.get('intellect', 1)}, "
            f"Stamina: {player_state.stats.get('stamina', 1)}\n\n"
            f"🎯 **Quest Phase:** {quest_progress['phase']}\n"
            f"📋 **Objectives:** {quest_progress['objectives_completed']}/{quest_progress['objectives_total']}\n"
            f"⚡ **Actions Taken:** {quest_progress['actions_taken']}\n\n"
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


async def _complete_quest_with_rewards(cb: CallbackQuery, completion_data: dict, state: FSMContext, fsm_service: FSMStateService):
    """Handle quest completion with rewards."""
    try:
        user_id = cb.from_user.id
        
        # Get rewards from completion data
        rewards = completion_data["rewards"]
        efficiency = completion_data["efficiency"]
        
        # Update FSM state to complete
        await state.set_state(QuestStates.COMPLETE)
        await state.update_data(
            player_state_dict=None,
            current_scene=None,
            quest_data=None
        )
        
        # Get localized text
        completion_text = i18n_service.get_text(user_id, "quest_proposal.completed")
        reward_text = i18n_service.get_text(user_id, "quest_proposal.rewards_received")
        
        # Build completion message
        response_text = (
            f"🎉 {completion_text} 🎉\n\n"
            f"📜 **Quest:** {completion_data['quest_description']}\n"
            f"🧙‍♂️ **Questgiver:** {completion_data['questgiver']}\n\n"
            f"🏆 {reward_text}\n"
            f"💰 **Gold:** +{rewards['gold']}"
        )
        
        if rewards['gold_bonus'] > 0:
            response_text += f" (+{rewards['gold_bonus']} efficiency bonus)"
        
        response_text += f"\n⭐ **XP:** +{rewards['xp']}"
        
        if rewards['xp_bonus'] > 0:
            response_text += f" (+{rewards['xp_bonus']} efficiency bonus)"
        
        response_text += (
            f"\n\n📊 **Efficiency:** {efficiency['actions_taken']} actions taken\n"
            f"💡 *Use /quest for another adventure!*"
        )
        
        await cb.message.edit_text(response_text, parse_mode="HTML")
        await cb.answer()
        
        logger.info("Player completed quest", 
                   user_id=user_id,
                   quest_id=completion_data["quest_id"],
                   questgiver=completion_data["questgiver"],
                   reward_gold=rewards["gold"],
                   reward_xp=rewards["xp"],
                   actions_taken=efficiency["actions_taken"])
        
    except Exception as e:
        logger.error("Error completing quest", 
                    user_id=cb.from_user.id,
                    error=str(e))
        await cb.answer("❌ Error completing quest", show_alert=True)


async def _fail_quest_with_reason(cb: CallbackQuery, failure_data: dict, state: FSMContext, fsm_service: FSMStateService):
    """Handle quest failure with reason."""
    try:
        user_id = cb.from_user.id
        
        # Update FSM state to complete
        await state.set_state(QuestStates.COMPLETE)
        await state.update_data(
            player_state_dict=None,
            current_scene=None,
            quest_data=None
        )
        
        # Get localized text
        failure_text = i18n_service.get_text(user_id, "quest_proposal.failed")
        
        # Build failure message
        response_text = (
            f"💀 {failure_text} 💀\n\n"
            f"📜 **Quest:** {failure_data['quest_description']}\n"
            f"🧙‍♂️ **Questgiver:** {failure_data['questgiver']}\n\n"
            f"❌ **Reason:** {failure_data['failure_reason']}\n\n"
            f"💡 *Rest and try again with /quest!*"
        )
        
        await cb.message.edit_text(response_text, parse_mode="HTML")
        await cb.answer()
        
        logger.info("Player failed quest", 
                   user_id=user_id,
                   quest_id=failure_data["quest_id"],
                   questgiver=failure_data["questgiver"],
                   reason=failure_data["failure_reason"])
        
    except Exception as e:
        logger.error("Error failing quest", 
                    user_id=cb.from_user.id,
                    error=str(e))
        await cb.answer("❌ Error processing quest failure", show_alert=True)


# Combat action handlers
@router.callback_query(QuestActionCB.filter(F.action == "attack"), QuestStates.COMBAT)
async def handle_quest_attack(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession):
    """Handle attack action in combat."""
    await _handle_combat_action(cb, "attack", state, db_session)


@router.callback_query(QuestActionCB.filter(F.action == "defend"), QuestStates.COMBAT)
async def handle_quest_defend(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession):
    """Handle defend action in combat."""
    await _handle_combat_action(cb, "defend", state, db_session)


@router.callback_query(QuestActionCB.filter(F.action == "flee"), QuestStates.COMBAT)
async def handle_quest_flee(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession):
    """Handle flee action in combat."""
    await _handle_combat_action(cb, "flee", state, db_session)


# Quest progression handlers
@router.callback_query(QuestActionCB.filter(F.action == "continue"), QuestStates.ACTIVE)
async def handle_quest_continue(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession):
    """Handle continue action in active quest."""
    await _handle_quest_progression(cb, "continue", state, db_session)


@router.callback_query(QuestActionCB.filter(F.action == "next"), QuestStates.ACTIVE)
async def handle_quest_next(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession):
    """Handle next action in active quest."""
    await _handle_quest_progression(cb, "next", state, db_session)


@router.callback_query(QuestActionCB.filter(F.action == "loot"), QuestStates.ACTIVE)
async def handle_quest_loot(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession):
    """Handle loot action in active quest."""
    await _handle_quest_progression(cb, "loot", state, db_session)


@router.callback_query(QuestActionCB.filter(F.action == "search_new"), QuestStates.ACTIVE)
async def handle_quest_search_new(cb: CallbackQuery, callback_data: QuestActionCB, state: FSMContext, db_session: AsyncSession):
    """Handle search new action in active quest."""
    await _handle_quest_progression(cb, "search_new", state, db_session)


async def _handle_combat_action(cb: CallbackQuery, action: str, state: FSMContext, db_session: AsyncSession):
    """Handle combat actions with real consequences."""
    try:
        user_id = cb.from_user.id
        
        # Get current FSM data
        fsm_data = await state.get_data()
        player_state_dict = fsm_data.get("player_state_dict")
        quest_data = fsm_data.get("quest_data")
        
        if not player_state_dict or not quest_data:
            await cb.answer("❌ Quest state not found", show_alert=True)
            return
        
        # Recreate player state
        player_state = await _get_or_create_player_state(user_id, state)
        
        # Process combat action with consequences
        combat_result = _process_combat_action(action, player_state, quest_data)
        
        # Update player state
        player_state.energy += combat_result["energy_change"]
        player_state.risk_level += combat_result["risk_change"]
        
        # Check if combat is over
        if combat_result["combat_ended"]:
            if combat_result["victory"]:
                # Return to active quest state
                await state.set_state(QuestStates.ACTIVE)
                response_text = f"🎉 {combat_result['message']}\n\nYou have defeated the enemy and can continue your quest!"
            else:
                # Quest failed due to combat loss
                await state.set_state(QuestStates.COMPLETE)
                response_text = f"💀 {combat_result['message']}\n\nYour quest has failed due to defeat in combat."
        else:
            # Combat continues
            response_text = f"⚔️ {combat_result['message']}\n\nCombat continues! Choose your next action."
        
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
            }
        )
        
        # Build keyboard based on combat state
        if combat_result["combat_ended"]:
            if combat_result["victory"]:
                keyboard = _build_quest_continue_keyboard()
            else:
                keyboard = None
        else:
            keyboard = _build_combat_keyboard()
        
        if keyboard:
            await cb.message.edit_text(response_text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await cb.message.edit_text(response_text, parse_mode="HTML")
        
        await cb.answer()
        
        logger.info("Player made combat action", 
                   user_id=user_id,
                   action=action,
                   energy=player_state.energy,
                   risk_level=player_state.risk_level,
                   combat_ended=combat_result["combat_ended"],
                   victory=combat_result.get("victory", False))
        
    except Exception as e:
        logger.error("Error in combat action handler", 
                    user_id=cb.from_user.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await cb.answer("❌ Error processing combat action", show_alert=True)


async def _handle_quest_progression(cb: CallbackQuery, action: str, state: FSMContext, db_session: AsyncSession):
    """Handle quest progression actions with real consequences."""
    try:
        user_id = cb.from_user.id
        
        # Get current FSM data
        fsm_data = await state.get_data()
        player_state_dict = fsm_data.get("player_state_dict")
        quest_data = fsm_data.get("quest_data")
        
        if not player_state_dict or not quest_data:
            await cb.answer("❌ Quest state not found", show_alert=True)
            return
        
        # Recreate player state
        player_state = await _get_or_create_player_state(user_id, state)
        
        # Process quest progression action
        progression_result = _process_quest_progression(action, player_state, quest_data)
        
        # Update player state
        player_state.energy += progression_result["energy_change"]
        player_state.risk_level += progression_result["risk_change"]
        player_state.step_count += 1
        
        # Check if quest should transition to combat
        if progression_result["triggers_combat"]:
            await state.set_state(QuestStates.COMBAT)
            response_text = f"⚔️ {progression_result['message']}\n\nCombat has begun! Choose your action."
            keyboard = _build_combat_keyboard()
        elif progression_result["quest_completed"]:
            await state.set_state(QuestStates.COMPLETE)
            response_text = f"🎉 {progression_result['message']}\n\nQuest completed successfully!"
            keyboard = None
        else:
            # Continue quest
            response_text = f"📜 {progression_result['message']}\n\nContinue your quest adventure."
            keyboard = _build_quest_continue_keyboard()
        
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
            }
        )
        
        if keyboard:
            await cb.message.edit_text(response_text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await cb.message.edit_text(response_text, parse_mode="HTML")
        
        await cb.answer()
        
        logger.info("Player made quest progression action", 
                   user_id=user_id,
                   action=action,
                   energy=player_state.energy,
                   risk_level=player_state.risk_level,
                   step_count=player_state.step_count,
                   triggers_combat=progression_result["triggers_combat"],
                   quest_completed=progression_result["quest_completed"])
        
    except Exception as e:
        logger.error("Error in quest progression handler", 
                    user_id=cb.from_user.id,
                    error_type=type(e).__name__,
                    error_message=str(e))
        await cb.answer("❌ Error processing quest action", show_alert=True)


def _process_combat_action(action: str, player_state, quest_data: dict) -> dict:
    """Process combat action with real consequences."""
    import random
    
    # Base combat mechanics
    base_energy_cost = 15
    base_risk_increase = 2
    
    if action == "attack":
        # Attack has high energy cost but good chance of victory
        energy_cost = base_energy_cost + random.randint(5, 15)
        risk_increase = base_risk_increase + random.randint(1, 3)
        victory_chance = 0.6 + (player_state.stats.get("bravery", 1) * 0.1)
        
        if random.random() < victory_chance:
            return {
                "message": "Your attack was successful! The enemy is defeated!",
                "energy_change": -energy_cost,
                "risk_change": risk_increase,
                "combat_ended": True,
                "victory": True
            }
        else:
            return {
                "message": "Your attack missed! The enemy counterattacks!",
                "energy_change": -energy_cost - 10,
                "risk_change": risk_increase + 2,
                "combat_ended": False,
                "victory": False
            }
    
    elif action == "defend":
        # Defend has lower energy cost and reduces risk
        energy_cost = base_energy_cost - 5
        risk_increase = max(0, base_risk_increase - 1)
        
        return {
            "message": "You defend against the enemy's attack, reducing damage taken.",
            "energy_change": -energy_cost,
            "risk_change": risk_increase,
            "combat_ended": False,
            "victory": False
        }
    
    elif action == "flee":
        # Flee has moderate energy cost but ends combat
        energy_cost = base_energy_cost - 5
        risk_increase = base_risk_increase + 3  # Fleeing increases risk
        
        return {
            "message": "You successfully flee from combat, but your reputation suffers.",
            "energy_change": -energy_cost,
            "risk_change": risk_increase,
            "combat_ended": True,
            "victory": False
        }
    
    return {
        "message": "Unknown combat action.",
        "energy_change": 0,
        "risk_change": 0,
        "combat_ended": False,
        "victory": False
    }


def _process_quest_progression(action: str, player_state, quest_data: dict) -> dict:
    """Process quest progression action with real consequences."""
    import random
    
    # Base progression mechanics
    base_energy_cost = 10
    base_risk_increase = 1
    
    if action == "continue":
        energy_cost = base_energy_cost + random.randint(0, 10)
        risk_increase = base_risk_increase + random.randint(0, 2)
        combat_chance = 0.3 + (quest_data.get("risk_level", 1) * 0.1)
        
        if random.random() < combat_chance:
            return {
                "message": "As you continue your quest, you encounter hostile creatures!",
                "energy_change": -energy_cost,
                "risk_change": risk_increase,
                "triggers_combat": True,
                "quest_completed": False
            }
        else:
            return {
                "message": "You make progress on your quest without incident.",
                "energy_change": -energy_cost,
                "risk_change": risk_increase,
                "triggers_combat": False,
                "quest_completed": False
            }
    
    elif action == "next":
        energy_cost = base_energy_cost + random.randint(5, 15)
        risk_increase = base_risk_increase + random.randint(1, 3)
        
        # Check if quest should be completed
        if player_state.step_count >= 5:  # Simple completion condition
            return {
                "message": "You have successfully completed your quest objectives!",
                "energy_change": -energy_cost,
                "risk_change": risk_increase,
                "triggers_combat": False,
                "quest_completed": True
            }
        else:
            return {
                "message": "You advance further in your quest, discovering new challenges.",
                "energy_change": -energy_cost,
                "risk_change": risk_increase,
                "triggers_combat": False,
                "quest_completed": False
            }
    
    elif action == "loot":
        energy_cost = base_energy_cost - 5
        risk_increase = base_risk_increase + random.randint(0, 2)
        
        # Loot can provide benefits but also risks
        loot_benefit = random.randint(5, 15)
        player_state.energy += loot_benefit
        
        return {
            "message": f"You find valuable loot that restores {loot_benefit} energy!",
            "energy_change": loot_benefit - energy_cost,
            "risk_change": risk_increase,
            "triggers_combat": False,
            "quest_completed": False
        }
    
    elif action == "search_new":
        energy_cost = base_energy_cost + random.randint(0, 5)
        risk_increase = base_risk_increase + random.randint(0, 1)
        
        return {
            "message": "You search for new paths and opportunities in your quest.",
            "energy_change": -energy_cost,
            "risk_change": risk_increase,
            "triggers_combat": False,
            "quest_completed": False
        }
    
    return {
        "message": "Unknown quest action.",
        "energy_change": 0,
        "risk_change": 0,
        "triggers_combat": False,
        "quest_completed": False
    }


def _build_combat_keyboard():
    """Build keyboard for combat actions."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚔️ Attack", callback_data=QuestActionCB(action="attack").pack()),
            InlineKeyboardButton(text="🛡️ Defend", callback_data=QuestActionCB(action="defend").pack())
        ],
        [
            InlineKeyboardButton(text="🏃 Flee", callback_data=QuestActionCB(action="flee").pack())
        ]
    ])


def _build_quest_continue_keyboard():
    """Build keyboard for quest continuation actions."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➡️ Continue", callback_data=QuestActionCB(action="continue").pack()),
            InlineKeyboardButton(text="🔍 Search New", callback_data=QuestActionCB(action="search_new").pack())
        ],
        [
            InlineKeyboardButton(text="📦 Loot", callback_data=QuestActionCB(action="loot").pack()),
            InlineKeyboardButton(text="⏭️ Next", callback_data=QuestActionCB(action="next").pack())
        ]
    ])


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
