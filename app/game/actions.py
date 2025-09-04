from enum import StrEnum
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import random

from app.services.logging_service import get_logger

logger = get_logger(__name__)


class Action(StrEnum):
    ATTACK = "attack"
    DEFEND = "defend"
    CAST = "cast"
    USE_ITEM = "use_item"
    TALK = "talk"
    SNEAK = "sneak"
    LOOT = "loot"
    FLEE = "flee"
    WAIT = "wait"
    BACK = "back"
    ACCEPT = "accept"
    INVESTIGATE = "investigate"
    PREPARE = "prepare"
    RUN_AI = "run_ai"
    # New actions for scene graph system
    CONTINUE = "continue"
    REST = "rest"
    EXPLORE = "explore"
    NEGOTIATE = "negotiate"
    RETREAT = "retreat"


@dataclass(frozen=True)
class ActionMeta:
    prompt_key: str   # localization hint for LLM
    fallback_key: str # fallback button label key
    max_len: int = 14

ACTION_META: dict[Action, ActionMeta] = {
    Action.ATTACK:   ActionMeta("action.attack", "btn.attack"),
    Action.DEFEND:   ActionMeta("action.defend", "btn.defend"),
    Action.CAST:     ActionMeta("action.cast", "btn.cast"),
    Action.USE_ITEM: ActionMeta("action.use_item", "btn.use_item"),
    Action.TALK:     ActionMeta("action.talk", "btn.talk"),
    Action.SNEAK:    ActionMeta("action.sneak", "btn.sneak"),
    Action.LOOT:     ActionMeta("action.loot", "btn.loot"),
    Action.FLEE:     ActionMeta("action.flee", "btn.flee"),
    Action.WAIT:     ActionMeta("action.wait", "btn.wait"),
    Action.BACK:     ActionMeta("action.back", "btn.back"),
    Action.ACCEPT:   ActionMeta("action.accept", "btn.accept"),
    Action.INVESTIGATE: ActionMeta("action.investigate", "btn.investigate"),
    Action.PREPARE:  ActionMeta("action.prepare", "btn.prepare"),
    Action.RUN_AI:   ActionMeta("action.run_ai", "btn.run_ai"),
    Action.CONTINUE: ActionMeta("action.continue", "btn.continue"),
    Action.REST:     ActionMeta("action.rest", "btn.rest"),
    Action.EXPLORE:  ActionMeta("action.explore", "btn.explore"),
    Action.NEGOTIATE: ActionMeta("action.negotiate", "btn.negotiate"),
    Action.RETREAT:  ActionMeta("action.retreat", "btn.retreat"),
}


@dataclass
class ActionConsequence:
    """Represents the consequences of taking an action."""
    stat_changes: Dict[str, int] = None
    energy_cost: int = 0
    risk_change: int = 0
    goal_updates: List[str] = None
    scene_modifiers: Dict[str, Any] = None
    success_probability: float = 1.0
    failure_consequences: Optional['ActionConsequence'] = None
    
    def __post_init__(self):
        if self.stat_changes is None:
            self.stat_changes = {}
        if self.goal_updates is None:
            self.goal_updates = []
        if self.scene_modifiers is None:
            self.scene_modifiers = {}


class ActionProcessor:
    """Processes actions and applies their consequences to player state."""
    
    @staticmethod
    def process_action(action: Action, player_state, scene_context: Optional[Dict] = None) -> ActionConsequence:
        """Process an action and return its consequences."""
        scene_context = scene_context or {}
        
        # Get base consequence for the action
        consequence = ActionProcessor._get_base_consequence(action, scene_context)
        
        # Apply scene-specific modifiers
        consequence = ActionProcessor._apply_scene_modifiers(consequence, scene_context)
        
        # Apply player stat modifiers
        consequence = ActionProcessor._apply_stat_modifiers(consequence, player_state)
        
        return consequence
    
    @staticmethod
    def _get_base_consequence(action: Action, scene_context: Dict) -> ActionConsequence:
        """Get the base consequence for an action."""
        base_consequences = {
            Action.ATTACK: ActionConsequence(
                stat_changes={"bravery": 1},
                energy_cost=15,
                risk_change=2,
                success_probability=0.7
            ),
            Action.DEFEND: ActionConsequence(
                stat_changes={"stamina": 1},
                energy_cost=5,
                risk_change=-1,
                success_probability=0.9
            ),
            Action.CAST: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=20,
                risk_change=1,
                success_probability=0.6
            ),
            Action.TALK: ActionConsequence(
                stat_changes={"charisma": 1},
                energy_cost=5,
                risk_change=0,
                success_probability=0.8
            ),
            Action.SNEAK: ActionConsequence(
                stat_changes={"stamina": 1},
                energy_cost=10,
                risk_change=-1,
                success_probability=0.6
            ),
            Action.LOOT: ActionConsequence(
                energy_cost=5,
                risk_change=1,
                success_probability=0.7
            ),
            Action.FLEE: ActionConsequence(
                energy_cost=10,
                risk_change=-2,
                success_probability=0.8
            ),
            Action.WAIT: ActionConsequence(
                energy_cost=0,
                risk_change=0,
                success_probability=1.0
            ),
            Action.ACCEPT: ActionConsequence(
                stat_changes={"charisma": 1},
                energy_cost=5,
                risk_change=1,
                success_probability=1.0
            ),
            Action.INVESTIGATE: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=8,
                risk_change=0,
                success_probability=0.7
            ),
            Action.PREPARE: ActionConsequence(
                stat_changes={"stamina": 1},
                energy_cost=3,
                risk_change=-1,
                success_probability=1.0
            ),
            Action.CONTINUE: ActionConsequence(
                energy_cost=5,
                risk_change=0,
                success_probability=1.0
            ),
            Action.REST: ActionConsequence(
                energy_cost=-20,  # Restore energy
                risk_change=-1,
                success_probability=1.0
            ),
            Action.EXPLORE: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=12,
                risk_change=2,
                success_probability=0.6
            ),
            Action.NEGOTIATE: ActionConsequence(
                stat_changes={"charisma": 1},
                energy_cost=8,
                risk_change=0,
                success_probability=0.7
            ),
            Action.RETREAT: ActionConsequence(
                energy_cost=8,
                risk_change=-2,
                success_probability=0.9
            ),
        }
        
        return base_consequences.get(action, ActionConsequence())
    
    @staticmethod
    def _apply_scene_modifiers(consequence: ActionConsequence, scene_context: Dict) -> ActionConsequence:
        """Apply scene-specific modifiers to consequences."""
        scene_type = scene_context.get("scene_type", "")
        
        # Modify consequences based on scene type
        if scene_type == "combat":
            consequence.energy_cost = int(consequence.energy_cost * 1.5)
            consequence.risk_change += 1
        elif scene_type == "rest":
            consequence.energy_cost = max(0, consequence.energy_cost - 5)
            consequence.risk_change = max(-2, consequence.risk_change - 1)
        elif scene_type == "exploration":
            consequence.energy_cost = int(consequence.energy_cost * 1.2)
            consequence.success_probability *= 0.9
        
        return consequence
    
    @staticmethod
    def _apply_stat_modifiers(consequence: ActionConsequence, player_state) -> ActionConsequence:
        """Apply player stat modifiers to consequences."""
        stats = getattr(player_state, 'stats', {})
        
        # High intellect reduces energy cost for mental actions
        if stats.get("intellect", 0) >= 3:
            consequence.energy_cost = max(0, consequence.energy_cost - 2)
        
        # High stamina reduces energy cost for physical actions
        if stats.get("stamina", 0) >= 3:
            consequence.energy_cost = max(0, consequence.energy_cost - 3)
        
        # High charisma improves success probability for social actions
        if stats.get("charisma", 0) >= 3:
            consequence.success_probability = min(1.0, consequence.success_probability + 0.1)
        
        return consequence
    
    @staticmethod
    def apply_consequence(consequence: ActionConsequence, player_state) -> Dict[str, Any]:
        """Apply a consequence to the player state and return results."""
        results = {
            "success": True,
            "energy_change": 0,
            "risk_change": 0,
            "stat_changes": {},
            "goals_added": [],
            "message": ""
        }
        
        # Check if action succeeds
        if random.random() > consequence.success_probability:
            results["success"] = False
            results["message"] = "Your action failed!"
            if consequence.failure_consequences:
                # Apply failure consequences
                results["energy_change"] = consequence.failure_consequences.energy_cost
                results["risk_change"] = consequence.failure_consequences.risk_change
                results["stat_changes"] = consequence.failure_consequences.stat_changes.copy()
            return results
        
        # Apply successful consequences
        results["energy_change"] = consequence.energy_cost
        results["risk_change"] = consequence.risk_change
        results["stat_changes"] = consequence.stat_changes.copy()
        results["goals_added"] = consequence.goal_updates.copy()
        
        # Update player state
        if hasattr(player_state, 'energy'):
            player_state.energy = max(0, min(100, player_state.energy - consequence.energy_cost))
        
        if hasattr(player_state, 'risk_level'):
            player_state.risk_level = max(0, player_state.risk_level + consequence.risk_change)
        
        if hasattr(player_state, 'stats'):
            for stat, change in consequence.stat_changes.items():
                player_state.stats[stat] = player_state.stats.get(stat, 0) + change
        
        if hasattr(player_state, 'goals'):
            for goal in consequence.goal_updates:
                player_state.goals.add(goal)
        
        results["message"] = "Action completed successfully!"
        return results


def get_available_actions(scene_type: str, player_state) -> List[Action]:
    """Get available actions based on scene type and player state."""
    base_actions = {
        "story": [Action.CONTINUE, Action.INVESTIGATE, Action.RUN_AI],
        "choice": [Action.ACCEPT, Action.TALK, Action.INVESTIGATE, Action.RUN_AI],
        "encounter": [Action.ATTACK, Action.DEFEND, Action.TALK, Action.FLEE, Action.RUN_AI],
        "dialogue": [Action.TALK, Action.NEGOTIATE, Action.INVESTIGATE, Action.RUN_AI],
        "rest": [Action.REST, Action.WAIT, Action.CONTINUE],
        "exploration": [Action.EXPLORE, Action.INVESTIGATE, Action.LOOT, Action.RETREAT, Action.RUN_AI],
        "quest": [Action.ACCEPT, Action.INVESTIGATE, Action.PREPARE, Action.RUN_AI],
        "loot": [Action.LOOT, Action.INVESTIGATE, Action.CONTINUE],
        "combat": [Action.ATTACK, Action.DEFEND, Action.CAST, Action.USE_ITEM, Action.FLEE],
    }
    
    actions = base_actions.get(scene_type, [Action.CONTINUE, Action.RUN_AI])
    
    # Filter actions based on player state
    filtered_actions = []
    for action in actions:
        if _can_perform_action(action, player_state):
            filtered_actions.append(action)
    
    return filtered_actions


def _can_perform_action(action: Action, player_state) -> bool:
    """Check if player can perform a specific action."""
    if not hasattr(player_state, 'energy'):
        return True
    
    # Check energy requirements
    consequence = ActionProcessor._get_base_consequence(action, {})
    if player_state.energy < abs(consequence.energy_cost):
        return False
    
    # Check other requirements based on action
    if action == Action.CAST and player_state.stats.get("intellect", 0) < 2:
        return False
    
    return True
