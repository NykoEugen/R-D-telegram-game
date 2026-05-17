"""
Quest Loop Service for the Telegram RPG game bot.

This service orchestrates the quest loop by integrating actions, states, scene graph,
and FSM management to provide a cohesive game experience.
"""

import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.game.actions import Action, ActionProcessor, get_available_actions, ACTION_META
from app.game.scenes import SceneGraphManager, Scene, SceneType, PlayerState, SceneContext
from app.game.states import GameStates, QuestStates, CombatStates, DialogueStates
from app.services.fsm_service import FSMStateService
from app.services.i18n_service import I18nService
from app.services.logging_service import get_logger

logger = get_logger(__name__)


class QuestLoopService:
    """Service that manages the quest loop and game flow."""
    
    def __init__(self, bot: Bot, fsm_service: FSMStateService, i18n_service: I18nService):
        self.bot = bot
        self.fsm_service = fsm_service
        self.i18n_service = i18n_service
        self.scene_graph = SceneGraphManager()
    
    async def start_quest_loop(
        self,
        user_id: int,
        fsm_context: FSMContext,
        message: Optional[Message] = None,
        initial_scene_id: Optional[str] = None
    ) -> bool:
        """
        Start a new quest loop for a user.
        
        Args:
            user_id: Telegram user ID
            fsm_context: FSM context
            message: Optional message to edit
            initial_scene_id: Optional starting scene ID
            
        Returns:
            True if quest loop started successfully
        """
        try:
            # Set initial FSM state
            await fsm_context.set_state(GameStates.QUEST_ACTIVE)
            
            # Create or get session
            game_session = await self.fsm_service.create_or_get_session(
                user_id=user_id,
                scene_id=initial_scene_id,
                initial_data={
                    "quest_started_at": datetime.utcnow().isoformat(),
                    "quest_loop_active": True
                }
            )
            
            if not game_session:
                logger.error("Failed to create game session", user_id=user_id)
                return False
            
            # Get or create player state
            player_state = await self._get_or_create_player_state(user_id, game_session)
            
            # Get starting scene
            starting_scene = self.scene_graph.get_next_scene(player_state, initial_scene_id)
            if not starting_scene:
                logger.error("No starting scene available", user_id=user_id)
                return False
            
            # Update player state with starting scene
            player_state.current_scene = starting_scene.id
            await self._save_player_state(user_id, player_state, game_session)
            
            # Present the scene to the player
            await self._present_scene(
                user_id=user_id,
                scene=starting_scene,
                player_state=player_state,
                message=message,
                fsm_context=fsm_context
            )
            
            logger.info("Started quest loop", 
                       user_id=user_id, 
                       scene_id=starting_scene.id,
                       session_id=game_session.session_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to start quest loop",
                        user_id=user_id,
                        error_type=type(e).__name__,
                        error_message=str(e))
            return False
    
    async def process_action(
        self,
        user_id: int,
        action: Action,
        fsm_context: FSMContext,
        callback_query: Optional[CallbackQuery] = None
    ) -> bool:
        """
        Process a player action in the quest loop.
        
        Args:
            user_id: Telegram user ID
            action: Action to process
            fsm_context: FSM context
            callback_query: Optional callback query to answer
            
        Returns:
            True if action was processed successfully
        """
        try:
            # Answer callback query if provided
            if callback_query:
                await callback_query.answer()
            
            # Get current session and player state
            game_session = await self.fsm_service.sync_fsm_to_postgres(
                fsm_context, user_id, action.value
            )
            if not game_session:
                logger.error("Failed to sync FSM state", user_id=user_id)
                return False
            
            player_state = await self._get_player_state_from_session(game_session)
            if not player_state:
                logger.error("Failed to get player state", user_id=user_id)
                return False
            
            # Get current scene
            current_scene = self.scene_graph.scenes.get(player_state.current_scene)
            if not current_scene:
                logger.error("Current scene not found", 
                           user_id=user_id, 
                           scene_id=player_state.current_scene)
                return False
            
            # Process the action
            scene_context = {
                "scene_type": current_scene.kind.value,
                "scene_id": current_scene.id
            }
            
            consequence = ActionProcessor.process_action(action, player_state, scene_context)
            action_result = ActionProcessor.apply_consequence(consequence, player_state)
            
            # Update player state
            await self._save_player_state(user_id, player_state, game_session)
            
            # Check for end conditions
            end_reason = self.scene_graph.check_end_conditions(player_state)
            if end_reason:
                await self._end_quest_loop(user_id, fsm_context, end_reason)
                return True
            
            # Get next scene based on action result
            next_scene = await self._get_next_scene_after_action(
                current_scene, action, action_result, player_state
            )
            
            if next_scene:
                # Apply scene consequences
                self.scene_graph.apply_scene_consequences(next_scene, player_state)
                player_state.current_scene = next_scene.id
                
                # Save updated state
                await self._save_player_state(user_id, player_state, game_session)
                
                # Present next scene
                await self._present_scene(
                    user_id=user_id,
                    scene=next_scene,
                    player_state=player_state,
                    fsm_context=fsm_context
                )
            else:
                # No next scene, end quest loop
                await self._end_quest_loop(user_id, fsm_context, "No more scenes available")
            
            logger.info("Processed action", 
                       user_id=user_id, 
                       action=action.value,
                       success=action_result["success"])
            
            return True
            
        except Exception as e:
            logger.error("Failed to process action",
                        user_id=user_id,
                        action=action.value,
                        error_type=type(e).__name__,
                        error_message=str(e))
            return False
    
    async def _get_or_create_player_state(self, user_id: int, game_session) -> PlayerState:
        """Get or create player state from session data."""
        session_data = game_session.session_data or {}
        
        # Extract player state from session data
        player_state = PlayerState(
            user_id=user_id,
            current_scene=session_data.get("current_scene"),
            visited_scenes=set(session_data.get("visited_scenes", [])),
            scene_cooldowns=session_data.get("scene_cooldowns", {}),
            risk_level=session_data.get("risk_level", 0),
            energy=session_data.get("energy", 100),
            stats=session_data.get("stats", {
                "bravery": 1, "charisma": 1, "intellect": 1, "stamina": 1, "level": 1
            }),
            goals=set(session_data.get("goals", [])),
            step_count=session_data.get("step_count", 0)
        )
        
        return player_state
    
    async def _get_player_state_from_session(self, game_session) -> PlayerState:
        """Get player state from existing session."""
        return await self._get_or_create_player_state(
            game_session.player.telegram_id, game_session
        )
    
    async def _save_player_state(self, user_id: int, player_state: PlayerState, game_session):
        """Save player state to session data."""
        session_data = game_session.session_data or {}
        session_data.update({
            "current_scene": player_state.current_scene,
            "visited_scenes": list(player_state.visited_scenes),
            "scene_cooldowns": player_state.scene_cooldowns,
            "risk_level": player_state.risk_level,
            "energy": player_state.energy,
            "stats": player_state.stats,
            "goals": list(player_state.goals),
            "step_count": player_state.step_count
        })
        
        await self.fsm_service.session_repo.update_session(
            game_session.session_id,
            session_data=session_data
        )
    
    async def _present_scene(
        self,
        user_id: int,
        scene: Scene,
        player_state: PlayerState,
        message: Optional[Message] = None,
        fsm_context: Optional[FSMContext] = None
    ):
        """Present a scene to the player with appropriate actions."""
        try:
            # Get scene description
            scene_description = await self._get_scene_description(scene, player_state)
            
            # Get available actions for this scene
            available_actions = get_available_actions(scene.kind.value, player_state)
            
            # Create keyboard with available actions
            keyboard = await self._create_scene_keyboard(available_actions, user_id)
            
            # Send or edit message
            if message:
                await message.edit_text(
                    scene_description,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=scene_description,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            
            # Update FSM state based on scene type
            if fsm_context:
                await self._update_fsm_state_for_scene(fsm_context, scene)
            
            logger.info("Presented scene", 
                       user_id=user_id, 
                       scene_id=scene.id,
                       scene_type=scene.kind.value,
                       available_actions=[a.value for a in available_actions])
            
        except Exception as e:
            logger.error("Failed to present scene",
                        user_id=user_id,
                        scene_id=scene.id,
                        error_type=type(e).__name__,
                        error_message=str(e))
    
    async def _get_scene_description(self, scene: Scene, player_state: PlayerState) -> str:
        """Get description for a scene based on its type and player state."""
        # This is a simplified implementation
        # In a real game, you'd want to use AI or predefined descriptions
        
        base_descriptions = {
            SceneType.STORY: f"📖 {scene.id.replace('_', ' ').title()}\n\nYou find yourself in an interesting situation...",
            SceneType.CHOICE: f"🤔 {scene.id.replace('_', ' ').title()}\n\nYou need to make a decision...",
            SceneType.ENCOUNTER: f"⚔️ {scene.id.replace('_', ' ').title()}\n\nYou encounter something unexpected...",
            SceneType.DIALOGUE: f"💬 {scene.id.replace('_', ' ').title()}\n\nSomeone wants to talk to you...",
            SceneType.REST: f"🛌 {scene.id.replace('_', ' ').title()}\n\nA good place to rest and recover...",
            SceneType.EXPLORATION: f"🗺️ {scene.id.replace('_', ' ').title()}\n\nYou explore the area...",
            SceneType.QUEST: f"🎯 {scene.id.replace('_', ' ').title()}\n\nA quest opportunity presents itself...",
            SceneType.LOOT: f"💰 {scene.id.replace('_', ' ').title()}\n\nYou find something valuable...",
            SceneType.COMBAT: f"⚔️ {scene.id.replace('_', ' ').title()}\n\nCombat begins!",
            SceneType.INVENTORY: f"🎒 {scene.id.replace('_', ' ').title()}\n\nYou check your inventory..."
        }
        
        description = base_descriptions.get(scene.kind, f"📍 {scene.id.replace('_', ' ').title()}")
        
        # Add player state info
        description += f"\n\n💪 Energy: {player_state.energy}/100"
        description += f"\n⚠️ Risk: {player_state.risk_level}"
        description += f"\n📊 Stats: B{player_state.stats.get('bravery', 1)} C{player_state.stats.get('charisma', 1)} I{player_state.stats.get('intellect', 1)} S{player_state.stats.get('stamina', 1)}"
        
        return description
    
    async def _create_scene_keyboard(self, available_actions: List[Action], user_id: int) -> InlineKeyboardMarkup:
        """Create keyboard with available actions for the scene."""
        buttons = []
        
        for action in available_actions:
            action_meta = ACTION_META.get(action)
            if action_meta:
                # Get localized button text
                button_text = await self.i18n_service.get_text(
                    user_id, action_meta.fallback_key, action.value
                )
                
                buttons.append([
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"action:{action.value}"
                    )
                ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    async def _update_fsm_state_for_scene(self, fsm_context: FSMContext, scene: Scene):
        """Update FSM state based on scene type."""
        state_mapping = {
            SceneType.STORY: GameStates.QUEST_ACTIVE,
            SceneType.CHOICE: GameStates.QUEST_CHOICE,
            SceneType.ENCOUNTER: GameStates.QUEST_ACTIVE,
            SceneType.DIALOGUE: GameStates.DIALOGUE_ACTIVE,
            SceneType.REST: GameStates.QUEST_ACTIVE,
            SceneType.EXPLORATION: GameStates.EXPLORATION,
            SceneType.QUEST: QuestStates.QUEST_PROGRESS,
            SceneType.LOOT: GameStates.QUEST_ACTIVE,
            SceneType.COMBAT: CombatStates.COMBAT_ACTIVE,
            SceneType.INVENTORY: GameStates.INVENTORY_OPEN
        }
        
        new_state = state_mapping.get(scene.kind, GameStates.QUEST_ACTIVE)
        await fsm_context.set_state(new_state)
    
    async def _get_next_scene_after_action(
        self,
        current_scene: Scene,
        action: Action,
        action_result: Dict[str, Any],
        player_state: PlayerState
    ) -> Optional[Scene]:
        """Get the next scene based on the action taken and its result."""
        # Use scene graph to get next scene
        next_scene = self.scene_graph.get_next_scene(player_state, current_scene.id)
        
        # Apply action-specific scene transitions
        if action == Action.FLEE or action == Action.RETREAT:
            # Try to find a safer scene
            safer_scenes = [
                scene for scene in self.scene_graph.scenes.values()
                if scene.risk_delta < current_scene.risk_delta
                and self.scene_graph._check_scene_availability(scene, player_state)
            ]
            if safer_scenes:
                next_scene = safer_scenes[0]  # Take the first available safer scene
        
        elif action == Action.EXPLORE:
            # Try to find an exploration scene
            exploration_scenes = [
                scene for scene in self.scene_graph.scenes.values()
                if scene.kind == SceneType.EXPLORATION
                and self.scene_graph._check_scene_availability(scene, player_state)
            ]
            if exploration_scenes:
                next_scene = exploration_scenes[0]
        
        return next_scene
    
    async def _end_quest_loop(
        self,
        user_id: int,
        fsm_context: FSMContext,
        reason: str
    ):
        """End the quest loop and return to menu."""
        try:
            # Set FSM state to menu
            await fsm_context.set_state(GameStates.MENU)
            
            # End the session
            await self.fsm_service.end_session(
                user_id=user_id,
                status="completed" if "completed" in reason.lower() else "abandoned"
            )
            
            # Send end message
            end_message = f"🏁 Quest ended: {reason}\n\nReturning to main menu..."
            await self.bot.send_message(chat_id=user_id, text=end_message)
            
            logger.info("Ended quest loop", user_id=user_id, reason=reason)
            
        except Exception as e:
            logger.error("Failed to end quest loop",
                        user_id=user_id,
                        reason=reason,
                        error_type=type(e).__name__,
                        error_message=str(e))
    
    async def get_quest_status(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get current quest status for a user."""
        try:
            session_state = await self.fsm_service.get_session_state(user_id)
            if not session_state:
                return None
            
            return {
                "active": session_state.get("session_data", {}).get("quest_loop_active", False),
                "session_id": session_state.get("session_id"),
                "status": session_state.get("status"),
                "started_at": session_state.get("started_at"),
                "actions_count": session_state.get("actions_count", 0),
                "messages_count": session_state.get("messages_count", 0)
            }
            
        except Exception as e:
            logger.error("Failed to get quest status",
                        user_id=user_id,
                        error_type=type(e).__name__,
                        error_message=str(e))
            return None
