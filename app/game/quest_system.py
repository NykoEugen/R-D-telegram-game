"""
Quest System for the Telegram RPG game bot.

This module manages the complete quest lifecycle from proposal to completion,
including quest progression, scene generation, and reward distribution.
"""

import random
from enum import StrEnum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from app.services.logging_service import get_logger
from app.game.actions import Action, ActionProcessor, get_available_actions
from app.game.scenes import PlayerState, SceneContext, SceneType

logger = get_logger(__name__)


class QuestPhase(StrEnum):
    """Phases of quest progression."""
    PROPOSAL = "proposal"
    ACCEPTED = "accepted"
    EXPLORATION = "exploration"
    CONFRONTATION = "confrontation"
    RESOLUTION = "resolution"
    COMPLETION = "completion"
    FAILURE = "failure"


class QuestType(StrEnum):
    """Types of quests available."""
    INVESTIGATION = "investigation"
    COMBAT = "combat"
    RESCUE = "rescue"
    DELIVERY = "delivery"
    EXPLORATION = "exploration"
    DIPLOMACY = "diplomacy"
    STEALTH = "stealth"
    CRAFTING = "crafting"
    TRADING = "trading"


@dataclass
class QuestObjective:
    """Represents a quest objective."""
    id: str
    description: str
    required_actions: List[Action] = field(default_factory=list)
    optional_actions: List[Action] = field(default_factory=list)
    completion_condition: str = "action_count"
    completion_threshold: int = 3
    rewards: Dict[str, int] = field(default_factory=dict)


@dataclass
class Quest:
    """Represents a complete quest."""
    id: str
    questgiver_name: str
    quest_intro: str
    quest_description: str
    quest_type: QuestType
    risk_level: int
    reward_gold: int
    reward_xp: int
    faction: Optional[str] = None
    additional_info: Optional[str] = None
    
    # Quest progression
    phase: QuestPhase = QuestPhase.PROPOSAL
    objectives: List[QuestObjective] = field(default_factory=list)
    completed_objectives: Set[str] = field(default_factory=set)
    current_scene: Optional[str] = None
    scene_history: List[str] = field(default_factory=list)
    
    # Quest state
    energy_spent: int = 0
    actions_taken: int = 0
    success_factors: Dict[str, int] = field(default_factory=dict)
    failure_factors: Dict[str, int] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class QuestManager:
    """Manages quest lifecycle and progression."""
    
    def __init__(self):
        self.active_quests: Dict[int, Quest] = {}  # user_id -> Quest
        self.quest_templates = self._load_quest_templates()
    
    def _load_quest_templates(self) -> Dict[QuestType, List[Dict]]:
        """Load quest templates for different quest types."""
        return {
            QuestType.INVESTIGATION: [
                {
                    "objectives": [
                        QuestObjective(
                            id="gather_info",
                            description="Зібрати інформацію про подію",
                            required_actions=[Action.INVESTIGATE, Action.SEARCH, Action.OBSERVE],
                            completion_threshold=2
                        ),
                        QuestObjective(
                            id="find_evidence",
                            description="Знайти докази",
                            required_actions=[Action.SEARCH, Action.EXPLORE],
                            completion_threshold=1
                        ),
                        QuestObjective(
                            id="report_findings",
                            description="Повідомити про результати",
                            required_actions=[Action.TALK, Action.NEGOTIATE],
                            completion_threshold=1
                        )
                    ]
                }
            ],
            QuestType.COMBAT: [
                {
                    "objectives": [
                        QuestObjective(
                            id="locate_enemy",
                            description="Знайти ворога",
                            required_actions=[Action.SEARCH, Action.EXPLORE],
                            completion_threshold=1
                        ),
                        QuestObjective(
                            id="defeat_enemy",
                            description="Перемогти ворога",
                            required_actions=[Action.FIGHT, Action.ATTACK],
                            completion_threshold=1
                        ),
                        QuestObjective(
                            id="secure_area",
                            description="Забезпечити безпеку території",
                            required_actions=[Action.PROTECT, Action.DEFEND],
                            completion_threshold=1
                        )
                    ]
                }
            ],
            QuestType.RESCUE: [
                {
                    "objectives": [
                        QuestObjective(
                            id="locate_target",
                            description="Знайти того, кого потрібно врятувати",
                            required_actions=[Action.SEARCH, Action.INVESTIGATE],
                            completion_threshold=1
                        ),
                        QuestObjective(
                            id="reach_target",
                            description="Дістатися до цілі",
                            required_actions=[Action.INFILTRATE, Action.SNEAK, Action.FIGHT],
                            completion_threshold=1
                        ),
                        QuestObjective(
                            id="extract_target",
                            description="Вивести ціль з небезпеки",
                            required_actions=[Action.PROTECT, Action.ESCAPE],
                            completion_threshold=1
                        )
                    ]
                }
            ],
            QuestType.DIPLOMACY: [
                {
                    "objectives": [
                        QuestObjective(
                            id="establish_contact",
                            description="Встановити контакт з стороною",
                            required_actions=[Action.TALK, Action.CHARM],
                            completion_threshold=1
                        ),
                        QuestObjective(
                            id="negotiate_terms",
                            description="Обговорити умови",
                            required_actions=[Action.NEGOTIATE, Action.NEGOTIATE_PEACE],
                            completion_threshold=2
                        ),
                        QuestObjective(
                            id="secure_agreement",
                            description="Досягти угоди",
                            required_actions=[Action.INSPIRE, Action.LEAD],
                            completion_threshold=1
                        )
                    ]
                }
            ]
        }
    
    def create_quest(self, quest_data: Dict[str, Any]) -> Quest:
        """Create a new quest from quest data."""
        quest_type = QuestType(quest_data.get("quest_type", "investigation"))
        
        # Get random template for quest type
        templates = self.quest_templates.get(quest_type, [])
        if not templates:
            # Fallback template
            template = {
                "objectives": [
                    QuestObjective(
                        id="complete_task",
                        description="Виконати завдання",
                        required_actions=[Action.EXPLORE, Action.INVESTIGATE],
                        completion_threshold=3
                    )
                ]
            }
        else:
            template = random.choice(templates)
        
        quest = Quest(
            id=f"quest_{quest_data['user_id']}_{int(datetime.now().timestamp())}",
            questgiver_name=quest_data["questgiver_name"],
            quest_intro=quest_data["quest_intro"],
            quest_description=quest_data["quest_description"],
            quest_type=quest_type,
            risk_level=quest_data.get("risk_level", 1),
            reward_gold=quest_data.get("reward_gold", 0),
            reward_xp=quest_data.get("reward_xp", 0),
            faction=quest_data.get("faction"),
            additional_info=quest_data.get("additional_info"),
            objectives=template["objectives"]
        )
        
        return quest
    
    def start_quest(self, user_id: int, quest: Quest) -> Quest:
        """Start a quest for a user."""
        quest.phase = QuestPhase.ACCEPTED
        quest.started_at = datetime.now()
        self.active_quests[user_id] = quest
        
        logger.info("Quest started", 
                   user_id=user_id,
                   quest_id=quest.id,
                   quest_type=quest.quest_type,
                   risk_level=quest.risk_level)
        
        return quest
    
    def process_quest_action(self, user_id: int, action: Action, player_state: PlayerState) -> Dict[str, Any]:
        """Process an action within an active quest."""
        quest = self.active_quests.get(user_id)
        if not quest:
            return {"error": "No active quest found"}
        
        # Process the action
        scene_context = {
            "scene_type": "quest",
            "scene_id": quest.current_scene or quest.id,
            "quest_type": quest.quest_type,
            "risk_level": quest.risk_level,
            "quest_phase": quest.phase
        }
        
        consequence = ActionProcessor.process_action(action, player_state, scene_context)
        action_result = ActionProcessor.apply_consequence(consequence, player_state)
        
        # Update quest state
        quest.actions_taken += 1
        quest.energy_spent += abs(consequence.energy_cost)
        
        # Check objective completion
        objective_updates = self._check_objective_completion(quest, action)
        
        # Update quest phase based on progress
        new_phase = self._determine_quest_phase(quest, player_state)
        if new_phase != quest.phase:
            quest.phase = new_phase
            logger.info("Quest phase changed", 
                       user_id=user_id,
                       quest_id=quest.id,
                       old_phase=quest.phase,
                       new_phase=new_phase)
        
        # Generate next scene
        next_scene = self._generate_next_scene(quest, action, player_state)
        quest.current_scene = next_scene["scene_id"]
        quest.scene_history.append(next_scene["scene_id"])
        
        # Check quest completion
        completion_status = self._check_quest_completion(quest, player_state)
        
        result = {
            "action_result": action_result,
            "objective_updates": objective_updates,
            "quest_phase": quest.phase,
            "next_scene": next_scene,
            "completion_status": completion_status,
            "quest_progress": self._get_quest_progress(quest)
        }
        
        # Complete quest if finished
        if completion_status["completed"]:
            result["quest_completion"] = self._complete_quest(user_id, quest, player_state)
        elif completion_status["failed"]:
            result["quest_failure"] = self._fail_quest(user_id, quest, player_state)
        
        return result
    
    def _check_objective_completion(self, quest: Quest, action: Action) -> List[Dict[str, Any]]:
        """Check if any objectives have been completed."""
        updates = []
        
        for objective in quest.objectives:
            if objective.id in quest.completed_objectives:
                continue
            
            # Check if action contributes to objective
            if action in objective.required_actions or action in objective.optional_actions:
                # Simple completion logic - could be more complex
                if quest.actions_taken >= objective.completion_threshold:
                    quest.completed_objectives.add(objective.id)
                    updates.append({
                        "objective_id": objective.id,
                        "description": objective.description,
                        "completed": True
                    })
                    logger.info("Quest objective completed",
                               quest_id=quest.id,
                               objective_id=objective.id)
        
        return updates
    
    def _determine_quest_phase(self, quest: Quest, player_state: PlayerState) -> QuestPhase:
        """Determine the current quest phase based on progress."""
        completion_ratio = len(quest.completed_objectives) / len(quest.objectives)
        
        if completion_ratio >= 1.0:
            return QuestPhase.COMPLETION
        elif completion_ratio >= 0.7:
            return QuestPhase.RESOLUTION
        elif completion_ratio >= 0.3:
            return QuestPhase.CONFRONTATION
        elif quest.actions_taken > 0:
            return QuestPhase.EXPLORATION
        else:
            return QuestPhase.ACCEPTED
    
    def _generate_next_scene(self, quest: Quest, action: Action, player_state: PlayerState) -> Dict[str, Any]:
        """Generate the next scene based on quest progress and action."""
        scene_templates = {
            QuestPhase.EXPLORATION: [
                "Ви досліджуєте місцевість, шукаючи підказки...",
                "Ваші кроки ведуть вас далі в невідомість...",
                "Навколо вас розгортається таємнича історія...",
                "Ви помічаєте щось цікаве в далечині..."
            ],
            QuestPhase.CONFRONTATION: [
                "Ви наближаєтесь до кульмінації вашого завдання...",
                "Перед вами постає виклик, який потребує рішення...",
                "Ситуація стає більш напруженою...",
                "Ви відчуваєте, що наближаєтесь до розв'язки..."
            ],
            QuestPhase.RESOLUTION: [
                "Ви майже завершили своє завдання...",
                "Останні кроки до успіху...",
                "Ви відчуваєте, що завдання майже виконане...",
                "Фінальний акт вашої пригоди..."
            ]
        }
        
        templates = scene_templates.get(quest.phase, scene_templates[QuestPhase.EXPLORATION])
        scene_description = random.choice(templates)
        
        # Add action-specific context
        action_context = {
            Action.SEARCH: "Ви ретельно шукаєте підказки...",
            Action.INVESTIGATE: "Ви розслідуєте обставини...",
            Action.FIGHT: "Ви готуєтесь до битви...",
            Action.TALK: "Ви намагаєтесь встановити контакт...",
            Action.NEGOTIATE: "Ви ведете переговори...",
            Action.EXPLORE: "Ви досліджуєте нові території...",
            Action.HIDE: "Ви намагаєтесь залишитись непоміченим...",
            Action.CHARM: "Ви намагаєтесь зачарувати співрозмовника...",
            Action.INTIMIDATE: "Ви намагаєтесь залякати противника...",
            Action.HEAL: "Ви намагаєтесь вилікувати поранення...",
            Action.MEDITATE: "Ви медитуєте, відновлюючи сили...",
            Action.CRAFT: "Ви створюєте щось корисне...",
            Action.TRADE: "Ви ведете торгівлю...",
            Action.BEFRIEND: "Ви намагаєтесь подружитись...",
            Action.SABOTAGE: "Ви намагаєтесь саботувати...",
            Action.INFILTRATE: "Ви намагаєтесь проникнути...",
            Action.NEGOTIATE_PEACE: "Ви намагаєтесь встановити мир...",
            Action.DECEIVE: "Ви намагаєтесь обдурити...",
            Action.INSPIRE: "Ви намагаєтесь надихнути...",
            Action.LEAD: "Ви берете на себе лідерство...",
            Action.FOLLOW: "Ви слідуєте за кимось...",
            Action.OBSERVE: "Ви уважно спостерігаєте...",
            Action.LEARN: "Ви намагаєтесь навчитись чомусь...",
            Action.TEACH: "Ви намагаєтесь навчити когось...",
            Action.PROTECT: "Ви захищаєте когось...",
            Action.SACRIFICE: "Ви жертвуєте чимось...",
            Action.ESCAPE: "Ви намагаєтесь втекти...",
            Action.PURSUE: "Ви переслідуєте когось...",
            Action.AMBUSH: "Ви влаштовуєте засідку...",
            Action.SURRENDER: "Ви здаєтесь...",
            Action.CHALLENGE: "Ви кидаєте виклик...",
            Action.ACCEPT_CHALLENGE: "Ви приймаєте виклик...",
            Action.DECLINE_CHALLENGE: "Ви відмовляєтесь від виклику...",
            Action.COMPLETE_QUEST: "Ви завершуєте завдання..."
        }
        
        if action in action_context:
            scene_description = action_context[action]
        
        scene_id = f"{quest.id}_scene_{len(quest.scene_history) + 1}"
        
        return {
            "scene_id": scene_id,
            "description": scene_description,
            "context_hint": f"Quest: {quest.quest_description}",
            "available_actions": self._get_available_actions_for_phase(quest.phase, player_state)
        }
    
    def _get_available_actions_for_phase(self, phase: QuestPhase, player_state: PlayerState) -> List[Action]:
        """Get available actions based on quest phase."""
        phase_actions = {
            QuestPhase.EXPLORATION: get_available_actions("quest_exploration", player_state),
            QuestPhase.CONFRONTATION: get_available_actions("quest_combat", player_state),
            QuestPhase.RESOLUTION: get_available_actions("quest_leadership", player_state),
            QuestPhase.COMPLETION: [Action.COMPLETE_QUEST]
        }
        
        return phase_actions.get(phase, get_available_actions("quest", player_state))
    
    def _check_quest_completion(self, quest: Quest, player_state: PlayerState) -> Dict[str, Any]:
        """Check if quest is completed or failed."""
        # Check for completion
        if len(quest.completed_objectives) >= len(quest.objectives):
            return {"completed": True, "failed": False}
        
        # Check for failure conditions
        if player_state.energy <= 0:
            return {"completed": False, "failed": True, "reason": "energy_depleted"}
        
        if player_state.risk_level >= 10:
            return {"completed": False, "failed": True, "reason": "risk_too_high"}
        
        if quest.actions_taken >= 20:  # Too many actions without completion
            return {"completed": False, "failed": True, "reason": "too_many_actions"}
        
        return {"completed": False, "failed": False}
    
    def _get_quest_progress(self, quest: Quest) -> Dict[str, Any]:
        """Get quest progress information."""
        return {
            "phase": quest.phase,
            "objectives_completed": len(quest.completed_objectives),
            "objectives_total": len(quest.objectives),
            "actions_taken": quest.actions_taken,
            "energy_spent": quest.energy_spent,
            "completion_ratio": len(quest.completed_objectives) / len(quest.objectives) if quest.objectives else 0
        }
    
    def _complete_quest(self, user_id: int, quest: Quest, player_state: PlayerState) -> Dict[str, Any]:
        """Complete a quest and distribute rewards."""
        quest.phase = QuestPhase.COMPLETION
        quest.completed_at = datetime.now()
        
        # Calculate final rewards
        base_gold = quest.reward_gold
        base_xp = quest.reward_xp
        
        # Bonus for efficiency (fewer actions = more reward)
        efficiency_bonus = max(0, 10 - quest.actions_taken) * 0.1
        gold_bonus = int(base_gold * efficiency_bonus)
        xp_bonus = int(base_xp * efficiency_bonus)
        
        final_gold = base_gold + gold_bonus
        final_xp = base_xp + xp_bonus
        
        # Apply rewards to player
        player_state.stats["gold"] = player_state.stats.get("gold", 0) + final_gold
        player_state.stats["xp"] = player_state.stats.get("xp", 0) + final_xp
        
        # Remove quest from active quests
        if user_id in self.active_quests:
            del self.active_quests[user_id]
        
        logger.info("Quest completed",
                   user_id=user_id,
                   quest_id=quest.id,
                   final_gold=final_gold,
                   final_xp=final_xp,
                   actions_taken=quest.actions_taken)
        
        return {
            "quest_id": quest.id,
            "questgiver": quest.questgiver_name,
            "quest_description": quest.quest_description,
            "rewards": {
                "gold": final_gold,
                "xp": final_xp,
                "gold_bonus": gold_bonus,
                "xp_bonus": xp_bonus
            },
            "efficiency": {
                "actions_taken": quest.actions_taken,
                "efficiency_bonus": efficiency_bonus
            }
        }
    
    def _fail_quest(self, user_id: int, quest: Quest, player_state: PlayerState) -> Dict[str, Any]:
        """Handle quest failure."""
        quest.phase = QuestPhase.FAILURE
        
        # Remove quest from active quests
        if user_id in self.active_quests:
            del self.active_quests[user_id]
        
        logger.info("Quest failed",
                   user_id=user_id,
                   quest_id=quest.id,
                   actions_taken=quest.actions_taken,
                   energy=player_state.energy,
                   risk_level=player_state.risk_level)
        
        return {
            "quest_id": quest.id,
            "questgiver": quest.questgiver_name,
            "quest_description": quest.quest_description,
            "failure_reason": "Quest failed due to insufficient energy or high risk"
        }
    
    def get_active_quest(self, user_id: int) -> Optional[Quest]:
        """Get active quest for a user."""
        return self.active_quests.get(user_id)
    
    def abandon_quest(self, user_id: int) -> Optional[Quest]:
        """Abandon an active quest."""
        quest = self.active_quests.pop(user_id, None)
        if quest:
            quest.phase = QuestPhase.FAILURE
            logger.info("Quest abandoned", user_id=user_id, quest_id=quest.id)
        return quest


# Global quest manager instance
quest_manager = QuestManager()
