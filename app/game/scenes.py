"""
Game scenes and scenarios for the Telegram RPG game bot.

This module contains scene definitions, scene graph management, and context for different game situations.
"""

import random
import yaml
from enum import StrEnum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from pathlib import Path

from app.services.logging_service import get_logger

logger = get_logger(__name__)


class SceneType(StrEnum):
    """Types of game scenes."""
    STORY = "story"
    CHOICE = "choice"
    ENCOUNTER = "encounter"
    DIALOGUE = "dialogue"
    REST = "rest"
    EXPLORATION = "exploration"
    QUEST = "quest"
    LOOT = "loot"
    COMBAT = "combat"
    INVENTORY = "inventory"


@dataclass
class SceneTransition:
    """Represents a transition from one scene to another."""
    to: str
    weight: float
    requires: List[str] = field(default_factory=list)


@dataclass
class SceneReward:
    """Represents rewards that can be gained from a scene."""
    gold: Optional[str] = None
    xp: Optional[str] = None
    stamina: Optional[str] = None
    items: List[str] = field(default_factory=list)


@dataclass
class Scene:
    """Represents a single scene in the game."""
    id: str
    kind: SceneType
    weight: float
    once: bool = False
    requires: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    transitions: List[SceneTransition] = field(default_factory=list)
    cooldown: Optional[int] = None
    risk_delta: int = 0
    reward: Optional[SceneReward] = None


@dataclass
class EndCondition:
    """Represents conditions that can end the adventure cycle."""
    kind: str
    threshold: Optional[int] = None
    goal: Optional[str] = None
    quest_id: Optional[str] = None
    dynamic: bool = False
    base: Optional[int] = None
    bonus_by_stat: Dict[str, float] = field(default_factory=dict)


@dataclass
class SceneContext:
    """Context information for a game scene."""
    scene_id: str
    scene_type: SceneType
    description: str
    context_hint: Optional[str] = None
    user_id: Optional[int] = None
    message_id: Optional[int] = None


@dataclass
class PlayerState:
    """Represents the current state of a player in the adventure."""
    user_id: int
    current_scene: Optional[str] = None
    visited_scenes: Set[str] = field(default_factory=set)
    scene_cooldowns: Dict[str, int] = field(default_factory=dict)
    risk_level: int = 0
    energy: int = 100
    stats: Dict[str, int] = field(default_factory=lambda: {
        "bravery": 1, "charisma": 1, "intellect": 1, "stamina": 1, "level": 1
    })
    goals: Set[str] = field(default_factory=set)
    step_count: int = 0


class SceneGraphManager:
    """Manages the dynamic scene graph and scene selection logic."""
    
    def __init__(self, scenes_file: str = "app/game/scenes.yaml"):
        self.scenes_file = scenes_file
        self.scenes: Dict[str, Scene] = {}
        self.end_conditions: List[EndCondition] = []
        self._load_scenes()
    
    def _load_scenes(self):
        """Load scenes and end conditions from YAML file."""
        try:
            scenes_path = Path(self.scenes_file)
            if not scenes_path.exists():
                logger.error(f"Scenes file not found: {self.scenes_file}")
                return
            
            with open(scenes_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Load scenes
            for scene_data in data.get('scenes', []):
                scene = Scene(
                    id=scene_data['id'],
                    kind=SceneType(scene_data['kind']),
                    weight=scene_data['weight'],
                    once=scene_data.get('once', False),
                    requires=scene_data.get('requires', []),
                    blocks=scene_data.get('blocks', []),
                    cooldown=scene_data.get('cooldown'),
                    risk_delta=scene_data.get('risk_delta', 0),
                    reward=SceneReward(**scene_data.get('reward', {})) if scene_data.get('reward') else None
                )
                
                # Load transitions
                for trans_data in scene_data.get('transitions', []):
                    transition = SceneTransition(
                        to=trans_data['to'],
                        weight=trans_data['weight'],
                        requires=trans_data.get('requires', [])
                    )
                    scene.transitions.append(transition)
                
                self.scenes[scene.id] = scene
            
            # Load end conditions
            for cond_data in data.get('end_conditions', []):
                condition = EndCondition(
                    kind=cond_data['kind'],
                    threshold=cond_data.get('threshold'),
                    goal=cond_data.get('goal'),
                    quest_id=cond_data.get('quest_id'),
                    dynamic=cond_data.get('dynamic', False),
                    base=cond_data.get('base'),
                    bonus_by_stat=cond_data.get('bonus_by_stat', {})
                )
                self.end_conditions.append(condition)
            
            logger.info(f"Loaded {len(self.scenes)} scenes and {len(self.end_conditions)} end conditions")
            
        except Exception as e:
            logger.error(f"Error loading scenes: {e}", exc_info=True)
    
    def get_next_scene(self, player_state: PlayerState, current_scene_id: Optional[str] = None) -> Optional[Scene]:
        """Get the next scene based on current state and transition rules."""
        if not current_scene_id:
            # Start with a random scene that has no requirements
            available_scenes = [
                scene for scene in self.scenes.values()
                if not scene.requires and self._check_scene_availability(scene, player_state)
            ]
            if available_scenes:
                return random.choices(available_scenes, weights=[s.weight for s in available_scenes])[0]
            return None
        
        current_scene = self.scenes.get(current_scene_id)
        if not current_scene:
            return None
        
        # Get available transitions
        available_transitions = []
        for transition in current_scene.transitions:
            if self._check_transition_requirements(transition, player_state):
                target_scene = self.scenes.get(transition.to)
                if target_scene and self._check_scene_availability(target_scene, player_state):
                    available_transitions.append((transition, target_scene))
        
        if not available_transitions:
            return None
        
        # Weighted random selection
        weights = [trans[0].weight for trans in available_transitions]
        selected_transition, selected_scene = random.choices(available_transitions, weights=weights)[0]
        
        return selected_scene
    
    def _check_scene_availability(self, scene: Scene, player_state: PlayerState) -> bool:
        """Check if a scene is available for the player."""
        # Check if scene was already visited and is once-only
        if scene.once and scene.id in player_state.visited_scenes:
            return False
        
        # Check cooldown
        if scene.cooldown and scene.id in player_state.scene_cooldowns:
            if player_state.scene_cooldowns[scene.id] > 0:
                return False
        
        # Check requirements
        for requirement in scene.requires:
            if not self._check_requirement(requirement, player_state):
                return False
        
        # Check blocks
        for block in scene.blocks:
            if self._check_requirement(block, player_state):
                return False
        
        return True
    
    def _check_transition_requirements(self, transition: SceneTransition, player_state: PlayerState) -> bool:
        """Check if a transition's requirements are met."""
        for requirement in transition.requires:
            if not self._check_requirement(requirement, player_state):
                return False
        return True
    
    def _check_requirement(self, requirement: str, player_state: PlayerState) -> bool:
        """Check if a single requirement is met."""
        if requirement.startswith("visited:"):
            scene_id = requirement[8:]  # Remove "visited:" prefix
            return scene_id in player_state.visited_scenes
        
        elif requirement.startswith("stat:"):
            # Format: "stat:stat_name>=value" or "stat:stat_name<=value" or "stat:stat_name==value"
            parts = requirement[5:].split(">=")
            if len(parts) == 2:
                stat_name, value = parts
                return player_state.stats.get(stat_name, 0) >= int(value)
            
            parts = requirement[5:].split("<=")
            if len(parts) == 2:
                stat_name, value = parts
                return player_state.stats.get(stat_name, 0) <= int(value)
            
            parts = requirement[5:].split("==")
            if len(parts) == 2:
                stat_name, value = parts
                return player_state.stats.get(stat_name, 0) == int(value)
        
        elif requirement.startswith("goal:"):
            goal = requirement[5:]  # Remove "goal:" prefix
            return goal in player_state.goals
        
        return False
    
    def apply_scene_consequences(self, scene: Scene, player_state: PlayerState):
        """Apply the consequences of visiting a scene."""
        # Mark scene as visited
        player_state.visited_scenes.add(scene.id)
        
        # Update cooldowns
        if scene.cooldown:
            player_state.scene_cooldowns[scene.id] = scene.cooldown
        
        # Decrease cooldowns for other scenes
        for scene_id in list(player_state.scene_cooldowns.keys()):
            if player_state.scene_cooldowns[scene_id] > 0:
                player_state.scene_cooldowns[scene_id] -= 1
                if player_state.scene_cooldowns[scene_id] == 0:
                    del player_state.scene_cooldowns[scene_id]
        
        # Update risk level
        player_state.risk_level += scene.risk_delta
        player_state.risk_level = max(0, player_state.risk_level)  # Don't go below 0
        
        # Update step count
        player_state.step_count += 1
        
        # Apply rewards if any
        if scene.reward:
            self._apply_rewards(scene.reward, player_state)
    
    def _apply_rewards(self, reward: SceneReward, player_state: PlayerState):
        """Apply rewards to player state."""
        # This is a simplified implementation
        # In a real game, you'd want to parse dice expressions like "1d6+2"
        if reward.gold:
            # Simple implementation - just add a base amount
            player_state.stats["gold"] = player_state.stats.get("gold", 0) + 5
        
        if reward.xp:
            player_state.stats["xp"] = player_state.stats.get("xp", 0) + 3
        
        if reward.stamina:
            player_state.energy = min(100, player_state.energy + 10)
    
    def check_end_conditions(self, player_state: PlayerState) -> Optional[str]:
        """Check if any end conditions are met and return the reason."""
        for condition in self.end_conditions:
            if condition.kind == "risk_threshold" and condition.threshold:
                if player_state.risk_level >= condition.threshold:
                    return f"Risk threshold reached: {player_state.risk_level}"
            
            elif condition.kind == "energy_depleted" and condition.threshold is not None:
                if player_state.energy <= condition.threshold:
                    return "Energy depleted"
            
            elif condition.kind == "goal_reached" and condition.goal:
                if condition.goal in player_state.goals:
                    return f"Goal reached: {condition.goal}"
            
            elif condition.kind == "step_budget":
                max_steps = condition.base or 4
                if condition.dynamic:
                    for stat_name, bonus in condition.bonus_by_stat.items():
                        stat_value = player_state.stats.get(stat_name, 0)
                        max_steps += int(stat_value * bonus)
                
                if player_state.step_count >= max_steps:
                    return f"Step budget exceeded: {player_state.step_count}/{max_steps}"
        
        return None


# Global scene graph manager instance
scene_graph = SceneGraphManager()


def create_quest_scene(user_id: int, message_id: int, quest_description: str) -> SceneContext:
    """Create a quest scene context."""
    scene_id = f"quest-{user_id}-{message_id}"
    return SceneContext(
        scene_id=scene_id,
        scene_type=SceneType.QUEST,
        description=quest_description,
        context_hint=quest_description,
        user_id=user_id,
        message_id=message_id
    )


def create_demo_scene(scene_id: str, description: str) -> SceneContext:
    """Create a demo scene context."""
    return SceneContext(
        scene_id=scene_id,
        scene_type=SceneType.COMBAT,
        description=description,
        context_hint=description
    )
