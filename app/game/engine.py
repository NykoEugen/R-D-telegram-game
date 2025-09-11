"""
Quest Engine for the Telegram RPG game bot.

This module implements the quest engine that manages the complete quest lifecycle
from proposal to completion, including AI-powered content generation and combat resolution.
"""

import uuid
import random
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.services.ai.generation_service import AIGenerationService
from app.services.ai.action_service import ai_action_service
from app.services.logging_service import get_logger
from app.services.i18n_service import i18n_service
from app.game.models import QuestContext, CombatState
from app.game.states import QuestStates
from app.game.actions import Action

logger = get_logger(__name__)


class QuestEngine:
    """
    Quest engine that manages the complete quest lifecycle.
    
    This engine handles:
    - Quest proposal generation (title + hook)
    - Quest detail generation (when player asks)
    - Quest scene generation and progression
    - Combat resolution
    - Quest completion and rewards
    """
    
    def __init__(self):
        self.generation_service = AIGenerationService()
        self.active_quests: Dict[int, QuestContext] = {}  # user_id -> QuestContext
    
    async def start_offer(self, user_id: int, state: Dict[str, Any]) -> QuestContext:
        """
        Start a quest offer by calling AI to generate title + hook.
        
        Args:
            user_id: User ID
            state: Current game state
            
        Returns:
            QuestContext with generated title and hook
        """
        try:
            # Generate unique quest ID
            quest_id = f"quest_{user_id}_{int(datetime.now().timestamp())}"
            
            # Get user language
            user_language = i18n_service.get_user_language(user_id)
            
            # Generate quest title and hook using AI
            quest_content = await self._generate_quest_proposal(user_language)
            
            if not quest_content:
                # Fallback if AI generation fails
                quest_content = self._get_fallback_quest_proposal(user_language)
            
            # Parse the AI response to extract title and hook
            title, hook = self._parse_quest_proposal(quest_content)
            
            # Create quest context
            quest_context = QuestContext(
                quest_id=quest_id,
                title=title,
                hook=hook,
                questgiver_name=state.get("questgiver_name", "Mysterious Stranger"),
                quest_type=state.get("quest_type", "investigation"),
                risk_level=state.get("risk_level", 1),
                reward_gold=state.get("reward_gold", 0),
                reward_xp=state.get("reward_xp", 0),
                faction=state.get("faction")
            )
            
            # Store in active quests
            self.active_quests[user_id] = quest_context
            
            logger.info(
                "Quest offer started",
                user_id=user_id,
                quest_id=quest_id,
                title=title,
                quest_type=quest_context.quest_type
            )
            
            return quest_context
            
        except Exception as e:
            logger.error(
                "Failed to start quest offer",
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise
    
    async def ask_once(self, user_id: int, state: Dict[str, Any]) -> QuestContext:
        """
        Call AI for additional quest details (only once).
        
        Args:
            user_id: User ID
            state: Current game state
            
        Returns:
            Updated QuestContext with details
        """
        try:
            quest_context = self.active_quests.get(user_id)
            if not quest_context:
                raise ValueError("No active quest found for user")
            
            if quest_context.is_investigated():
                # Already investigated, return existing details
                return quest_context
            
            # Get user language
            user_language = i18n_service.get_user_language(user_id)
            
            # Generate additional details using AI
            details = await self._generate_quest_details(
                quest_context, user_language
            )
            
            if not details:
                # Fallback if AI generation fails
                details = self._get_fallback_quest_details(quest_context, user_language)
            
            # Update quest context
            quest_context.details = details
            quest_context.phase = "INVESTIGATED"
            
            logger.info(
                "Quest details generated",
                user_id=user_id,
                quest_id=quest_context.quest_id,
                details_length=len(details)
            )
            
            return quest_context
            
        except Exception as e:
            logger.error(
                "Failed to generate quest details",
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise
    
    async def accept_and_prepare(self, user_id: int, state: Dict[str, Any]) -> QuestContext:
        """
        Generate scenes and move quest to ACTIVE state.
        
        Args:
            user_id: User ID
            state: Current game state
            
        Returns:
            Updated QuestContext with generated scenes
        """
        try:
            quest_context = self.active_quests.get(user_id)
            if not quest_context:
                raise ValueError("No active quest found for user")
            
            # Get user language
            user_language = i18n_service.get_user_language(user_id)
            
            # Generate quest scenes using AI
            scenes = await self._generate_quest_scenes(
                quest_context, user_language
            )
            
            if not scenes:
                # Fallback if AI generation fails
                scenes = self._get_fallback_quest_scenes(quest_context)
            
            # Update quest context
            quest_context.scenes = scenes
            quest_context.phase = "ACTIVE"
            quest_context.started_at = datetime.now()
            quest_context.current_idx = 0
            
            logger.info(
                "Quest accepted and prepared",
                user_id=user_id,
                quest_id=quest_context.quest_id,
                scenes_count=len(scenes)
            )
            
            return quest_context
            
        except Exception as e:
            logger.error(
                "Failed to accept and prepare quest",
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise
    
    async def play_next_scene(self, user_id: int, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Iterate through scenes, trigger combat if needed.
        
        Args:
            user_id: User ID
            state: Current game state
            
        Returns:
            Scene result with potential combat trigger
        """
        try:
            quest_context = self.active_quests.get(user_id)
            if not quest_context:
                raise ValueError("No active quest found for user")
            
            if not quest_context.is_active():
                raise ValueError("Quest is not in active state")
            
            # Get current scene
            current_scene = quest_context.get_current_scene()
            if not current_scene:
                # No more scenes, complete quest
                return await self._complete_quest(user_id, quest_context)
            
            # Check if scene triggers combat
            if current_scene.get("triggers_combat", False):
                # Initialize combat
                combat_state = await self._initialize_combat(
                    quest_context, current_scene, state
                )
                quest_context.combat = combat_state.to_dict()
                quest_context.phase = "COMBAT"
                
                logger.info(
                    "Combat triggered in quest scene",
                    user_id=user_id,
                    quest_id=quest_context.quest_id,
                    scene_idx=quest_context.current_idx
                )
                
                return {
                    "scene_result": current_scene,
                    "combat_triggered": True,
                    "combat_state": combat_state.to_dict(),
                    "message": f"⚔️ Combat begins! {current_scene.get('combat_description', 'A battle starts!')}"
                }
            else:
                # Regular scene progression
                result = {
                    "scene_result": current_scene,
                    "combat_triggered": False,
                    "message": current_scene.get("description", "You continue your quest...")
                }
                
                # Advance to next scene if available
                if quest_context.advance_scene():
                    result["has_next_scene"] = True
                    result["next_scene_preview"] = quest_context.get_current_scene()
                else:
                    result["has_next_scene"] = False
                    # Quest completed
                    return await self._complete_quest(user_id, quest_context)
                
                return result
                
        except Exception as e:
            logger.error(
                "Failed to play next scene",
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise
    
    async def combat_turn(self, user_id: int, action: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve combat step via AI and update state.
        
        Args:
            user_id: User ID
            state: Current game state
            
        Returns:
            Combat result with updated state
        """
        try:
            quest_context = self.active_quests.get(user_id)
            if not quest_context:
                raise ValueError("No active quest found for user")
            
            if not quest_context.is_in_combat():
                raise ValueError("Quest is not in combat state")
            
            # Get combat state
            combat_data = quest_context.combat
            if not combat_data:
                raise ValueError("No combat state found")
            
            combat_state = CombatState.from_dict(combat_data)
            
            # Get user language
            user_language = i18n_service.get_user_language(user_id)
            
            # Process combat turn using AI
            combat_result = await self._process_combat_turn(
                combat_state, action, user_language
            )
            
            # Update combat state
            quest_context.combat = combat_state.to_dict()
            
            # Check if combat is over
            if combat_state.is_combat_over():
                winner = combat_state.get_winner()
                if winner == "player":
                    # Player won, continue quest
                    quest_context.phase = "ACTIVE"
                    quest_context.combat = None
                    quest_context.advance_scene()
                    
                    logger.info(
                        "Combat won, quest continues",
                        user_id=user_id,
                        quest_id=quest_context.quest_id
                    )
                    
                    return {
                        "combat_result": combat_result,
                        "combat_over": True,
                        "winner": "player",
                        "message": f"🎉 Victory! {combat_result.get('victory_message', 'You defeated the enemy!')}",
                        "quest_continues": True
                    }
                else:
                    # Player lost, quest failed
                    quest_context.phase = "COMPLETE"
                    quest_context.combat = None
                    
                    logger.info(
                        "Combat lost, quest failed",
                        user_id=user_id,
                        quest_id=quest_context.quest_id
                    )
                    
                    return {
                        "combat_result": combat_result,
                        "combat_over": True,
                        "winner": "enemy",
                        "message": f"💀 Defeat! {combat_result.get('defeat_message', 'You were defeated!')}",
                        "quest_failed": True
                    }
            else:
                # Combat continues
                return {
                    "combat_result": combat_result,
                    "combat_over": False,
                    "message": combat_result.get("turn_message", "Combat continues..."),
                    "combat_state": combat_state.to_dict()
                }
                
        except Exception as e:
            logger.error(
                "Failed to process combat turn",
                user_id=user_id,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise
    
    # Private helper methods
    
    async def _generate_quest_proposal(self, language: str) -> Optional[str]:
        """Generate quest proposal using AI."""
        try:
            # Use the existing generation service
            return await self.generation_service.generate_quest_description(language)
        except Exception as e:
            logger.error(f"Failed to generate quest proposal: {e}")
            return None
    
    def _get_fallback_quest_proposal(self, language: str) -> str:
        """Get fallback quest proposal if AI generation fails."""
        if language == "uk":
            return "Таємниче завдання|Стародавній артефакт зник з храму. Місцеві жителі просять допомоги в його пошуку."
        else:
            return "Mysterious Quest|An ancient artifact has disappeared from the temple. The locals are asking for help in finding it."
    
    def _parse_quest_proposal(self, content: str) -> tuple[str, str]:
        """Parse AI-generated quest content to extract title and hook."""
        try:
            # Try to split by common separators
            if "|" in content:
                parts = content.split("|", 1)
                return parts[0].strip(), parts[1].strip()
            elif "\n" in content:
                lines = content.split("\n", 1)
                return lines[0].strip(), lines[1].strip()
            else:
                # Single line, use as title, generate simple hook
                title = content.strip()
                hook = f"A mysterious quest awaits: {title.lower()}"
                return title, hook
        except Exception:
            # Fallback
            return "Mysterious Quest", "A mysterious quest awaits your attention."
    
    async def _generate_quest_details(self, quest_context: QuestContext, language: str) -> Optional[str]:
        """Generate quest details using AI."""
        try:
            # Create a custom prompt for quest details
            prompt = f"""
Generate detailed information about this quest:

Title: {quest_context.title}
Hook: {quest_context.hook}
Quest Type: {quest_context.quest_type}
Risk Level: {quest_context.risk_level}

Provide additional details including:
- Background story
- Specific objectives
- Potential challenges
- Rewards and consequences

Language: {language}
"""
            
            # For now, use the existing generation service with a custom prompt
            # In a full implementation, you'd create a dedicated method for this
            return await self.generation_service.generate_quest_description(language)
        except Exception as e:
            logger.error(f"Failed to generate quest details: {e}")
            return None
    
    def _get_fallback_quest_details(self, quest_context: QuestContext, language: str) -> str:
        """Get fallback quest details if AI generation fails."""
        if language == "uk":
            return f"Детальна інформація про завдання '{quest_context.title}': {quest_context.hook} Це завдання потребує ретельного підходу та може принести значні нагороди."
        else:
            return f"Detailed information about the quest '{quest_context.title}': {quest_context.hook} This quest requires careful approach and may bring significant rewards."
    
    async def _generate_quest_scenes(self, quest_context: QuestContext, language: str) -> List[Dict[str, Any]]:
        """Generate quest scenes using AI."""
        try:
            # Generate a series of scenes for the quest
            scenes = []
            
            # Scene 1: Introduction
            scenes.append({
                "scene_id": f"{quest_context.quest_id}_scene_1",
                "description": f"You begin your quest: {quest_context.title}",
                "triggers_combat": False,
                "actions_available": ["explore", "investigate", "talk"]
            })
            
            # Scene 2: Investigation/Exploration
            scenes.append({
                "scene_id": f"{quest_context.quest_id}_scene_2",
                "description": "You investigate the area, looking for clues and information.",
                "triggers_combat": False,
                "actions_available": ["search", "observe", "explore"]
            })
            
            # Scene 3: Confrontation (may trigger combat)
            combat_chance = 0.7 if quest_context.risk_level >= 3 else 0.3
            scenes.append({
                "scene_id": f"{quest_context.quest_id}_scene_3",
                "description": "You encounter a challenge that requires your attention.",
                "triggers_combat": random.random() < combat_chance,
                "combat_description": "A dangerous enemy blocks your path!",
                "actions_available": ["fight", "negotiate", "flee"]
            })
            
            # Scene 4: Resolution
            scenes.append({
                "scene_id": f"{quest_context.quest_id}_scene_4",
                "description": "You reach the final stage of your quest.",
                "triggers_combat": False,
                "actions_available": ["complete", "claim_reward"]
            })
            
            return scenes
            
        except Exception as e:
            logger.error(f"Failed to generate quest scenes: {e}")
            return []
    
    def _get_fallback_quest_scenes(self, quest_context: QuestContext) -> List[Dict[str, Any]]:
        """Get fallback quest scenes if AI generation fails."""
        return [
            {
                "scene_id": f"{quest_context.quest_id}_scene_1",
                "description": f"You begin your quest: {quest_context.title}",
                "triggers_combat": False,
                "actions_available": ["explore", "investigate"]
            },
            {
                "scene_id": f"{quest_context.quest_id}_scene_2",
                "description": "You investigate the area and find important clues.",
                "triggers_combat": False,
                "actions_available": ["search", "observe"]
            },
            {
                "scene_id": f"{quest_context.quest_id}_scene_3",
                "description": "You complete your quest successfully.",
                "triggers_combat": False,
                "actions_available": ["complete"]
            }
        ]
    
    async def _initialize_combat(self, quest_context: QuestContext, scene: Dict[str, Any], state: Dict[str, Any]) -> CombatState:
        """Initialize combat state for the quest."""
        # Get player stats from state
        player_hp = state.get("player_hp", 100)
        player_attack = state.get("player_attack", 10)
        player_defense = state.get("player_defense", 5)
        
        # Generate enemy stats based on quest risk level
        enemy_hp = 50 + (quest_context.risk_level * 20)
        enemy_attack = 8 + (quest_context.risk_level * 3)
        enemy_defense = 3 + (quest_context.risk_level * 2)
        
        return CombatState(
            enemy_name=f"Quest Enemy (Risk {quest_context.risk_level})",
            enemy_hp=enemy_hp,
            enemy_max_hp=enemy_hp,
            enemy_attack=enemy_attack,
            enemy_defense=enemy_defense,
            player_hp=player_hp,
            player_max_hp=player_hp,
            player_attack=player_attack,
            player_defense=player_defense
        )
    
    async def _process_combat_turn(self, combat_state: CombatState, action: str, language: str) -> Dict[str, Any]:
        """Process a combat turn using AI."""
        try:
            # Simple combat logic for now
            # In a full implementation, this would use AI to generate dynamic combat results
            
            if combat_state.is_player_turn():
                # Player's turn
                damage = max(1, combat_state.player_attack - combat_state.enemy_defense)
                combat_state.enemy_hp -= damage
                combat_state.add_combat_log(f"Player attacks for {damage} damage!")
                
                if combat_state.enemy_hp <= 0:
                    return {
                        "turn_message": f"You deal {damage} damage and defeat the enemy!",
                        "victory_message": "You have successfully defeated your opponent!",
                        "damage_dealt": damage
                    }
                else:
                    # Enemy's turn
                    enemy_damage = max(1, combat_state.enemy_attack - combat_state.player_defense)
                    combat_state.player_hp -= enemy_damage
                    combat_state.add_combat_log(f"Enemy attacks for {enemy_damage} damage!")
                    combat_state.turn_count += 1
                    
                    if combat_state.player_hp <= 0:
                        return {
                            "turn_message": f"The enemy deals {enemy_damage} damage!",
                            "defeat_message": "You have been defeated in combat!",
                            "damage_taken": enemy_damage
                        }
                    else:
                        return {
                            "turn_message": f"You deal {damage} damage. Enemy deals {enemy_damage} damage back!",
                            "damage_dealt": damage,
                            "damage_taken": enemy_damage
                        }
            else:
                # Enemy's turn
                enemy_damage = max(1, combat_state.enemy_attack - combat_state.player_defense)
                combat_state.player_hp -= enemy_damage
                combat_state.add_combat_log(f"Enemy attacks for {enemy_damage} damage!")
                combat_state.turn_count += 1
                
                if combat_state.player_hp <= 0:
                    return {
                        "turn_message": f"The enemy deals {enemy_damage} damage!",
                        "defeat_message": "You have been defeated in combat!",
                        "damage_taken": enemy_damage
                    }
                else:
                    return {
                        "turn_message": f"The enemy deals {enemy_damage} damage!",
                        "damage_taken": enemy_damage
                    }
                    
        except Exception as e:
            logger.error(f"Failed to process combat turn: {e}")
            return {
                "turn_message": "Combat continues...",
                "error": "Failed to process combat turn"
            }
    
    async def _complete_quest(self, user_id: int, quest_context: QuestContext) -> Dict[str, Any]:
        """Complete the quest and distribute rewards."""
        try:
            quest_context.phase = "COMPLETE"
            quest_context.completed_at = datetime.now()
            
            # Calculate rewards
            base_gold = quest_context.reward_gold
            base_xp = quest_context.reward_xp
            
            # Bonus for efficiency
            efficiency_bonus = max(0, 10 - quest_context.actions_taken) * 0.1
            gold_bonus = int(base_gold * efficiency_bonus)
            xp_bonus = int(base_xp * efficiency_bonus)
            
            final_gold = base_gold + gold_bonus
            final_xp = base_xp + xp_bonus
            
            # Remove from active quests
            if user_id in self.active_quests:
                del self.active_quests[user_id]
            
            logger.info(
                "Quest completed",
                user_id=user_id,
                quest_id=quest_context.quest_id,
                final_gold=final_gold,
                final_xp=final_xp
            )
            
            return {
                "quest_completed": True,
                "quest_id": quest_context.quest_id,
                "title": quest_context.title,
                "rewards": {
                    "gold": final_gold,
                    "xp": final_xp,
                    "gold_bonus": gold_bonus,
                    "xp_bonus": xp_bonus
                },
                "message": f"🎉 Quest '{quest_context.title}' completed! You earned {final_gold} gold and {final_xp} XP!"
            }
            
        except Exception as e:
            logger.error(f"Failed to complete quest: {e}")
            return {
                "quest_completed": False,
                "error": "Failed to complete quest"
            }
    
    def get_active_quest(self, user_id: int) -> Optional[QuestContext]:
        """Get active quest for a user."""
        return self.active_quests.get(user_id)
    
    def abandon_quest(self, user_id: int) -> Optional[QuestContext]:
        """Abandon an active quest."""
        quest_context = self.active_quests.pop(user_id, None)
        if quest_context:
            quest_context.phase = "COMPLETE"
            logger.info("Quest abandoned", user_id=user_id, quest_id=quest_context.quest_id)
        return quest_context


# Global quest engine instance
quest_engine = QuestEngine()
