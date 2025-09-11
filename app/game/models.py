"""
Game models for the Telegram RPG game bot.

This module contains game-specific data structures and models that are used
for quest management, combat, and other game mechanics.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class QuestContext:
    """
    Stores quest context information for the quest engine.
    
    This dataclass contains all the necessary information to manage
    a quest from proposal to completion, including AI-generated content,
    scene progression, and combat state.
    """
    quest_id: str
    title: str
    hook: str
    details: Optional[str] = None
    scenes: List[Dict[str, Any]] = field(default_factory=list)
    current_idx: int = 0
    reputation_delta: int = 0
    combat: Optional[Dict[str, Any]] = None
    
    # Quest state tracking
    phase: str = "OFFER"  # OFFER, INVESTIGATED, ACTIVE, COMBAT, COMPLETE
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Quest progression
    energy_spent: int = 0
    actions_taken: int = 0
    success_factors: Dict[str, int] = field(default_factory=dict)
    failure_factors: Dict[str, int] = field(default_factory=dict)
    
    # Quest metadata
    questgiver_name: str = ""
    quest_type: str = "investigation"
    risk_level: int = 1
    reward_gold: int = 0
    reward_xp: int = 0
    faction: Optional[str] = None
    
    def is_investigated(self) -> bool:
        """Check if quest details have been investigated."""
        return self.details is not None
    
    def is_active(self) -> bool:
        """Check if quest is currently active."""
        return self.phase == "ACTIVE"
    
    def is_in_combat(self) -> bool:
        """Check if quest is currently in combat."""
        return self.phase == "COMBAT"
    
    def is_complete(self) -> bool:
        """Check if quest is completed."""
        return self.phase == "COMPLETE"
    
    def get_current_scene(self) -> Optional[Dict[str, Any]]:
        """Get the current scene based on current_idx."""
        if 0 <= self.current_idx < len(self.scenes):
            return self.scenes[self.current_idx]
        return None
    
    def advance_scene(self) -> bool:
        """Advance to the next scene. Returns True if successful, False if at end."""
        if self.current_idx < len(self.scenes) - 1:
            self.current_idx += 1
            return True
        return False
    
    def has_next_scene(self) -> bool:
        """Check if there are more scenes to play."""
        return self.current_idx < len(self.scenes) - 1
    
    def get_quest_progress(self) -> Dict[str, Any]:
        """Get quest progress information."""
        return {
            "phase": self.phase,
            "current_scene": self.current_idx + 1,
            "total_scenes": len(self.scenes),
            "actions_taken": self.actions_taken,
            "energy_spent": self.energy_spent,
            "is_investigated": self.is_investigated(),
            "is_active": self.is_active(),
            "is_in_combat": self.is_in_combat(),
            "is_complete": self.is_complete()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert QuestContext to dictionary for serialization."""
        return {
            "quest_id": self.quest_id,
            "title": self.title,
            "hook": self.hook,
            "details": self.details,
            "scenes": self.scenes,
            "current_idx": self.current_idx,
            "reputation_delta": self.reputation_delta,
            "combat": self.combat,
            "phase": self.phase,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "energy_spent": self.energy_spent,
            "actions_taken": self.actions_taken,
            "success_factors": self.success_factors,
            "failure_factors": self.failure_factors,
            "questgiver_name": self.questgiver_name,
            "quest_type": self.quest_type,
            "risk_level": self.risk_level,
            "reward_gold": self.reward_gold,
            "reward_xp": self.reward_xp,
            "faction": self.faction
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuestContext':
        """Create QuestContext from dictionary."""
        # Handle datetime fields
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        started_at = None
        if data.get("started_at"):
            started_at = datetime.fromisoformat(data["started_at"])
        
        completed_at = None
        if data.get("completed_at"):
            completed_at = datetime.fromisoformat(data["completed_at"])
        
        return cls(
            quest_id=data["quest_id"],
            title=data["title"],
            hook=data["hook"],
            details=data.get("details"),
            scenes=data.get("scenes", []),
            current_idx=data.get("current_idx", 0),
            reputation_delta=data.get("reputation_delta", 0),
            combat=data.get("combat"),
            phase=data.get("phase", "OFFER"),
            created_at=created_at or datetime.now(),
            started_at=started_at,
            completed_at=completed_at,
            energy_spent=data.get("energy_spent", 0),
            actions_taken=data.get("actions_taken", 0),
            success_factors=data.get("success_factors", {}),
            failure_factors=data.get("failure_factors", {}),
            questgiver_name=data.get("questgiver_name", ""),
            quest_type=data.get("quest_type", "investigation"),
            risk_level=data.get("risk_level", 1),
            reward_gold=data.get("reward_gold", 0),
            reward_xp=data.get("reward_xp", 0),
            faction=data.get("faction")
        )


@dataclass
class CombatState:
    """
    Represents the state of combat within a quest.
    """
    enemy_name: str
    enemy_hp: int
    enemy_max_hp: int
    enemy_attack: int
    enemy_defense: int
    player_hp: int
    player_max_hp: int
    player_attack: int
    player_defense: int
    turn_count: int = 0
    combat_log: List[str] = field(default_factory=list)
    
    def is_player_turn(self) -> bool:
        """Check if it's the player's turn."""
        return self.turn_count % 2 == 0
    
    def is_enemy_turn(self) -> bool:
        """Check if it's the enemy's turn."""
        return self.turn_count % 2 == 1
    
    def is_combat_over(self) -> bool:
        """Check if combat is over."""
        return self.player_hp <= 0 or self.enemy_hp <= 0
    
    def get_winner(self) -> Optional[str]:
        """Get the winner of combat, or None if still ongoing."""
        if self.player_hp <= 0:
            return "enemy"
        elif self.enemy_hp <= 0:
            return "player"
        return None
    
    def add_combat_log(self, message: str):
        """Add a message to the combat log."""
        self.combat_log.append(f"Turn {self.turn_count + 1}: {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert CombatState to dictionary."""
        return {
            "enemy_name": self.enemy_name,
            "enemy_hp": self.enemy_hp,
            "enemy_max_hp": self.enemy_max_hp,
            "enemy_attack": self.enemy_attack,
            "enemy_defense": self.enemy_defense,
            "player_hp": self.player_hp,
            "player_max_hp": self.player_max_hp,
            "player_attack": self.player_attack,
            "player_defense": self.player_defense,
            "turn_count": self.turn_count,
            "combat_log": self.combat_log
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CombatState':
        """Create CombatState from dictionary."""
        return cls(
            enemy_name=data["enemy_name"],
            enemy_hp=data["enemy_hp"],
            enemy_max_hp=data["enemy_max_hp"],
            enemy_attack=data["enemy_attack"],
            enemy_defense=data["enemy_defense"],
            player_hp=data["player_hp"],
            player_max_hp=data["player_max_hp"],
            player_attack=data["player_attack"],
            player_defense=data["player_defense"],
            turn_count=data.get("turn_count", 0),
            combat_log=data.get("combat_log", [])
        )
