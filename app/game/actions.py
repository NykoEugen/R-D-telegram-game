import random
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Optional

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
    CONTINUE = "continue"
    REST = "rest"
    EXPLORE = "explore"
    NEGOTIATE = "negotiate"
    RETREAT = "retreat"
    # AI Scene System Actions
    SCOUT = "scout"
    FIGHT = "fight"
    PICKLOCK = "picklock"
    # Quest Proposal Actions
    ACCEPT_QUEST = "accept_quest"
    REFUSE_QUEST = "refuse_quest"
    ASK_QUEST_INFO = "ask_quest_info"
    # Quest Actions
    COMPLETE_QUEST = "complete_quest"
    # Extended Quest Actions
    SEARCH = "search"
    HIDE = "hide"
    CHARM = "charm"
    INTIMIDATE = "intimidate"
    HEAL = "heal"
    MEDITATE = "meditate"
    CRAFT = "craft"
    TRADE = "trade"
    BEFRIEND = "befriend"
    SABOTAGE = "sabotage"
    INFILTRATE = "infiltrate"
    NEGOTIATE_PEACE = "negotiate_peace"
    DECEIVE = "deceive"
    INSPIRE = "inspire"
    LEAD = "lead"
    FOLLOW = "follow"
    OBSERVE = "observe"
    LEARN = "learn"
    TEACH = "teach"
    PROTECT = "protect"
    SACRIFICE = "sacrifice"
    ESCAPE = "escape"
    PURSUE = "pursue"
    AMBUSH = "ambush"
    SURRENDER = "surrender"
    CHALLENGE = "challenge"
    ACCEPT_CHALLENGE = "accept_challenge"
    DECLINE_CHALLENGE = "decline_challenge"


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
    Action.CONTINUE: ActionMeta("action.continue", "btn.continue"),
    Action.REST:     ActionMeta("action.rest", "btn.rest"),
    Action.EXPLORE:  ActionMeta("action.explore", "btn.explore"),
    Action.NEGOTIATE: ActionMeta("action.negotiate", "btn.negotiate"),
    Action.RETREAT:  ActionMeta("action.retreat", "btn.retreat"),
    # AI Scene System Actions
    Action.SCOUT:    ActionMeta("action.scout", "btn.scout"),
    Action.FIGHT:    ActionMeta("action.fight", "btn.fight"),
    Action.PICKLOCK: ActionMeta("action.picklock", "btn.picklock"),
    # Quest Proposal Actions
    Action.ACCEPT_QUEST: ActionMeta("action.accept_quest", "btn.accept_quest"),
    Action.REFUSE_QUEST: ActionMeta("action.refuse_quest", "btn.refuse_quest"),
    Action.ASK_QUEST_INFO: ActionMeta("action.ask_quest_info", "btn.ask_quest_info"),
    # Quest Actions
    Action.COMPLETE_QUEST: ActionMeta("action.complete_quest", "btn.complete_quest"),
    # Extended Quest Actions
    Action.SEARCH: ActionMeta("action.search", "btn.search"),
    Action.HIDE: ActionMeta("action.hide", "btn.hide"),
    Action.CHARM: ActionMeta("action.charm", "btn.charm"),
    Action.INTIMIDATE: ActionMeta("action.intimidate", "btn.intimidate"),
    Action.HEAL: ActionMeta("action.heal", "btn.heal"),
    Action.MEDITATE: ActionMeta("action.meditate", "btn.meditate"),
    Action.CRAFT: ActionMeta("action.craft", "btn.craft"),
    Action.TRADE: ActionMeta("action.trade", "btn.trade"),
    Action.BEFRIEND: ActionMeta("action.befriend", "btn.befriend"),
    Action.SABOTAGE: ActionMeta("action.sabotage", "btn.sabotage"),
    Action.INFILTRATE: ActionMeta("action.infiltrate", "btn.infiltrate"),
    Action.NEGOTIATE_PEACE: ActionMeta("action.negotiate_peace", "btn.negotiate_peace"),
    Action.DECEIVE: ActionMeta("action.deceive", "btn.deceive"),
    Action.INSPIRE: ActionMeta("action.inspire", "btn.inspire"),
    Action.LEAD: ActionMeta("action.lead", "btn.lead"),
    Action.FOLLOW: ActionMeta("action.follow", "btn.follow"),
    Action.OBSERVE: ActionMeta("action.observe", "btn.observe"),
    Action.LEARN: ActionMeta("action.learn", "btn.learn"),
    Action.TEACH: ActionMeta("action.teach", "btn.teach"),
    Action.PROTECT: ActionMeta("action.protect", "btn.protect"),
    Action.SACRIFICE: ActionMeta("action.sacrifice", "btn.sacrifice"),
    Action.ESCAPE: ActionMeta("action.escape", "btn.escape"),
    Action.PURSUE: ActionMeta("action.pursue", "btn.pursue"),
    Action.AMBUSH: ActionMeta("action.ambush", "btn.ambush"),
    Action.SURRENDER: ActionMeta("action.surrender", "btn.surrender"),
    Action.CHALLENGE: ActionMeta("action.challenge", "btn.challenge"),
    Action.ACCEPT_CHALLENGE: ActionMeta("action.accept_challenge", "btn.accept_challenge"),
    Action.DECLINE_CHALLENGE: ActionMeta("action.decline_challenge", "btn.decline_challenge"),
}


@dataclass
class ActionConsequence:
    """Represents the consequences of taking an action."""
    stat_changes: dict[str, int] = None
    energy_cost: int = 0
    risk_change: int = 0
    goal_updates: list[str] = None
    scene_modifiers: dict[str, Any] = None
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
    def process_action(action: Action, player_state, scene_context: dict | None = None) -> ActionConsequence:
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
    def _get_base_consequence(action: Action, scene_context: dict) -> ActionConsequence:
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
            # AI Scene System Actions
            Action.SCOUT: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=8,
                risk_change=-1,
                success_probability=0.8
            ),
            Action.FIGHT: ActionConsequence(
                stat_changes={"bravery": 1},
                energy_cost=15,
                risk_change=2,
                success_probability=0.7
            ),
            Action.PICKLOCK: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=10,
                risk_change=1,
                success_probability=0.6
            ),
            # Quest Proposal Actions
            Action.ACCEPT_QUEST: ActionConsequence(
                stat_changes={"charisma": 1},
                energy_cost=5,
                risk_change=1,
                success_probability=1.0
            ),
            Action.REFUSE_QUEST: ActionConsequence(
                stat_changes={"charisma": -1},
                energy_cost=0,
                risk_change=0,
                success_probability=1.0
            ),
            Action.ASK_QUEST_INFO: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=2,
                risk_change=0,
                success_probability=1.0
            ),
            # Extended Quest Actions
            Action.SEARCH: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=8,
                risk_change=1,
                success_probability=0.7
            ),
            Action.HIDE: ActionConsequence(
                stat_changes={"stamina": 1},
                energy_cost=6,
                risk_change=-1,
                success_probability=0.6
            ),
            Action.CHARM: ActionConsequence(
                stat_changes={"charisma": 1},
                energy_cost=10,
                risk_change=0,
                success_probability=0.7
            ),
            Action.INTIMIDATE: ActionConsequence(
                stat_changes={"bravery": 1},
                energy_cost=8,
                risk_change=2,
                success_probability=0.6
            ),
            Action.HEAL: ActionConsequence(
                energy_cost=15,
                risk_change=-1,
                success_probability=0.8
            ),
            Action.MEDITATE: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=-10,  # Restore energy
                risk_change=-2,
                success_probability=1.0
            ),
            Action.CRAFT: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=12,
                risk_change=0,
                success_probability=0.6
            ),
            Action.TRADE: ActionConsequence(
                stat_changes={"charisma": 1},
                energy_cost=5,
                risk_change=0,
                success_probability=0.8
            ),
            Action.BEFRIEND: ActionConsequence(
                stat_changes={"charisma": 1},
                energy_cost=8,
                risk_change=-1,
                success_probability=0.7
            ),
            Action.SABOTAGE: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=15,
                risk_change=3,
                success_probability=0.5
            ),
            Action.INFILTRATE: ActionConsequence(
                stat_changes={"stamina": 1},
                energy_cost=12,
                risk_change=2,
                success_probability=0.6
            ),
            Action.NEGOTIATE_PEACE: ActionConsequence(
                stat_changes={"charisma": 1},
                energy_cost=10,
                risk_change=-2,
                success_probability=0.6
            ),
            Action.DECEIVE: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=8,
                risk_change=1,
                success_probability=0.6
            ),
            Action.INSPIRE: ActionConsequence(
                stat_changes={"charisma": 1},
                energy_cost=10,
                risk_change=-1,
                success_probability=0.7
            ),
            Action.LEAD: ActionConsequence(
                stat_changes={"charisma": 1, "bravery": 1},
                energy_cost=15,
                risk_change=1,
                success_probability=0.7
            ),
            Action.FOLLOW: ActionConsequence(
                stat_changes={"stamina": 1},
                energy_cost=5,
                risk_change=0,
                success_probability=0.8
            ),
            Action.OBSERVE: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=3,
                risk_change=0,
                success_probability=0.9
            ),
            Action.LEARN: ActionConsequence(
                stat_changes={"intellect": 1},
                energy_cost=8,
                risk_change=0,
                success_probability=0.8
            ),
            Action.TEACH: ActionConsequence(
                stat_changes={"charisma": 1},
                energy_cost=6,
                risk_change=0,
                success_probability=0.8
            ),
            Action.PROTECT: ActionConsequence(
                stat_changes={"bravery": 1, "stamina": 1},
                energy_cost=12,
                risk_change=1,
                success_probability=0.7
            ),
            Action.SACRIFICE: ActionConsequence(
                stat_changes={"bravery": 2},
                energy_cost=20,
                risk_change=2,
                success_probability=0.8
            ),
            Action.ESCAPE: ActionConsequence(
                stat_changes={"stamina": 1},
                energy_cost=10,
                risk_change=-2,
                success_probability=0.7
            ),
            Action.PURSUE: ActionConsequence(
                stat_changes={"stamina": 1},
                energy_cost=12,
                risk_change=1,
                success_probability=0.6
            ),
            Action.AMBUSH: ActionConsequence(
                stat_changes={"bravery": 1},
                energy_cost=8,
                risk_change=2,
                success_probability=0.7
            ),
            Action.SURRENDER: ActionConsequence(
                stat_changes={"charisma": -1},
                energy_cost=0,
                risk_change=-3,
                success_probability=1.0
            ),
            Action.CHALLENGE: ActionConsequence(
                stat_changes={"bravery": 1},
                energy_cost=10,
                risk_change=2,
                success_probability=0.6
            ),
            Action.ACCEPT_CHALLENGE: ActionConsequence(
                stat_changes={"bravery": 1},
                energy_cost=15,
                risk_change=2,
                success_probability=0.7
            ),
            Action.DECLINE_CHALLENGE: ActionConsequence(
                stat_changes={"charisma": -1},
                energy_cost=0,
                risk_change=-1,
                success_probability=1.0
            ),
        }
        
        return base_consequences.get(action, ActionConsequence())
    
    @staticmethod
    def _apply_scene_modifiers(consequence: ActionConsequence, scene_context: dict) -> ActionConsequence:
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
    def apply_consequence(consequence: ActionConsequence, player_state) -> dict[str, Any]:
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


def get_available_actions(scene_type: str, player_state) -> list[Action]:
    """Get available actions based on scene type and player state."""
    base_actions = {
        "story": [Action.CONTINUE, Action.INVESTIGATE, Action.CONTINUE],
        "choice": [Action.ACCEPT, Action.TALK, Action.INVESTIGATE, Action.CONTINUE],
        "encounter": [Action.ATTACK, Action.DEFEND, Action.TALK, Action.FLEE, Action.CONTINUE],
        "dialogue": [Action.TALK, Action.NEGOTIATE, Action.INVESTIGATE, Action.CONTINUE],
        "rest": [Action.REST, Action.WAIT, Action.CONTINUE],
        "exploration": [Action.EXPLORE, Action.INVESTIGATE, Action.LOOT, Action.RETREAT, Action.CONTINUE],
        "quest": [
            Action.EXPLORE, Action.INVESTIGATE, Action.FIGHT, Action.NEGOTIATE,
            Action.SEARCH, Action.HIDE, Action.CHARM, Action.INTIMIDATE,
            Action.HEAL, Action.MEDITATE, Action.CRAFT, Action.TRADE,
            Action.BEFRIEND, Action.SABOTAGE, Action.INFILTRATE, Action.NEGOTIATE_PEACE,
            Action.DECEIVE, Action.INSPIRE, Action.LEAD, Action.FOLLOW,
            Action.OBSERVE, Action.LEARN, Action.TEACH, Action.PROTECT,
            Action.SACRIFICE, Action.ESCAPE, Action.PURSUE, Action.AMBUSH,
            Action.SURRENDER, Action.CHALLENGE, Action.ACCEPT_CHALLENGE, Action.DECLINE_CHALLENGE,
            Action.COMPLETE_QUEST
        ],
        "quest_start": [
            Action.EXPLORE, Action.INVESTIGATE, Action.FIGHT, Action.NEGOTIATE,
            Action.SEARCH, Action.OBSERVE, Action.LEARN, Action.TRADE
        ],
        "quest_exploration": [
            Action.SEARCH, Action.EXPLORE, Action.OBSERVE, Action.HIDE,
            Action.INVESTIGATE, Action.LEARN, Action.ESCAPE, Action.RETREAT
        ],
        "quest_social": [
            Action.TALK, Action.NEGOTIATE, Action.CHARM, Action.INTIMIDATE,
            Action.BEFRIEND, Action.DECEIVE, Action.INSPIRE, Action.TEACH,
            Action.TRADE, Action.NEGOTIATE_PEACE
        ],
        "quest_combat": [
            Action.FIGHT, Action.ATTACK, Action.DEFEND, Action.AMBUSH,
            Action.CHALLENGE, Action.ACCEPT_CHALLENGE, Action.SURRENDER,
            Action.ESCAPE, Action.PURSUE, Action.PROTECT
        ],
        "quest_stealth": [
            Action.HIDE, Action.SNEAK, Action.INFILTRATE, Action.SABOTAGE,
            Action.DECEIVE, Action.ESCAPE, Action.AMBUSH
        ],
        "quest_leadership": [
            Action.LEAD, Action.INSPIRE, Action.PROTECT, Action.TEACH,
            Action.NEGOTIATE_PEACE, Action.CHALLENGE, Action.ACCEPT_CHALLENGE
        ],
        "quest_proposal": [Action.ACCEPT_QUEST, Action.REFUSE_QUEST, Action.ASK_QUEST_INFO],
        "loot": [Action.LOOT, Action.INVESTIGATE, Action.CONTINUE],
        "combat": [Action.ATTACK, Action.DEFEND, Action.CAST, Action.USE_ITEM, Action.FLEE],
    }
    
    actions = base_actions.get(scene_type, [Action.CONTINUE, Action.CONTINUE])
    
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
