"""
Player model for the Telegram RPG game bot.

This model represents a player character linked to a User with game stats and progress.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.character import CharacterClass, BaseAttributes, DerivedStats, CharacterProgression


class PlayerStatus(str, Enum):
    """Player status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    SUSPENDED = "suspended"


class Player(Base):
    """Player model representing a game character linked to a User."""
    
    __tablename__ = "players"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to User
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Player character information
    character_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    character_class: Mapped[Optional[CharacterClass]] = mapped_column(String(20), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Base attributes (STR, AGI, INT, VIT, LUK)
    strength: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    agility: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    intelligence: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    vitality: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    luck: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    
    # Available stat points for manual distribution
    available_stat_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Current health (calculated from vitality)
    health: Mapped[int] = mapped_column(Integer, default=60, nullable=False)  # 20 + 4*10 = 60
    
    # Legacy fields (kept for compatibility, will be calculated from attributes)
    max_health: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    mana: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    max_mana: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # Game currency and resources
    coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gems: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    energy: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_energy: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    
    # Game progress flags
    flags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Game progress flags
    achievements: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # Achievement IDs
    
    # Current game state
    current_scene_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("scenes.id"), nullable=True)
    current_quest_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("quests.id"), nullable=True)
    game_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Additional game state
    
    # Player status
    status: Mapped[PlayerStatus] = mapped_column(String(20), default=PlayerStatus.ACTIVE, nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_played: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="player")
    inventory_items: Mapped[List["InventoryItem"]] = relationship("InventoryItem", back_populates="player")
    quest_progress: Mapped[List["QuestProgress"]] = relationship("QuestProgress", back_populates="player")
    game_sessions: Mapped[List["GameSession"]] = relationship("GameSession", back_populates="player")
    
    def get_base_attributes(self) -> BaseAttributes:
        """Get base attributes as BaseAttributes object."""
        return BaseAttributes(
            strength=self.strength,
            agility=self.agility,
            intelligence=self.intelligence,
            vitality=self.vitality,
            luck=self.luck
        )
    
    def get_derived_stats(self) -> DerivedStats:
        """Calculate and return derived stats from base attributes."""
        return CharacterProgression.calculate_derived_stats(self.get_base_attributes())
    
    def get_max_health(self) -> int:
        """Calculate maximum health from vitality."""
        return 20 + 4 * self.vitality
    
    def get_attack_power(self) -> int:
        """Calculate attack power from strength."""
        return 2 + self.strength
    
    def get_magic_power(self) -> int:
        """Calculate magic power from intelligence."""
        return 2 + self.intelligence
    
    def get_crit_chance(self) -> float:
        """Calculate critical hit chance from agility."""
        return min(35.0, 5.0 + 0.5 * self.agility)
    
    def get_dodge_chance(self) -> float:
        """Calculate dodge chance from agility."""
        return min(25.0, 2.0 + 0.4 * self.agility)
    
    def can_level_up(self) -> bool:
        """Check if player can level up."""
        return CharacterProgression.can_level_up(self.level, self.experience)
    
    def get_xp_progress(self) -> tuple[int, int]:
        """Get XP progress towards next level (current, required)."""
        return CharacterProgression.get_xp_progress_to_next_level(self.level, self.experience)
    
    def add_experience(self, xp: int) -> bool:
        """Add experience and return True if leveled up."""
        old_level = self.level
        self.experience += xp
        new_level = CharacterProgression.get_level_from_xp(self.experience)
        
        if new_level > old_level:
            self.level = new_level
            # Full heal on level up
            self.health = self.get_max_health()
            self.max_health = self.get_max_health()
            return True
        return False
    
    def apply_class_bonuses(self, character_class: CharacterClass) -> None:
        """Apply starting class bonuses to attributes."""
        if self.character_class is not None:
            return  # Already has a class
        
        base_attrs = BaseAttributes(
            strength=self.strength,
            agility=self.agility,
            intelligence=self.intelligence,
            vitality=self.vitality,
            luck=self.luck
        )
        
        attrs_with_bonuses = CharacterProgression.apply_class_bonuses(base_attrs, character_class)
        
        self.strength = attrs_with_bonuses.strength
        self.agility = attrs_with_bonuses.agility
        self.intelligence = attrs_with_bonuses.intelligence
        self.vitality = attrs_with_bonuses.vitality
        self.luck = attrs_with_bonuses.luck
        
        self.character_class = character_class
        self.health = self.get_max_health()
        self.max_health = self.get_max_health()
    
    def distribute_stat_points(self, strength: int = 0, agility: int = 0, 
                             intelligence: int = 0, vitality: int = 0, luck: int = 0) -> bool:
        """Distribute available stat points. Returns True if successful."""
        total_points = strength + agility + intelligence + vitality + luck
        
        if total_points > self.available_stat_points:
            return False
        
        self.strength += strength
        self.agility += agility
        self.intelligence += intelligence
        self.vitality += vitality
        self.luck += luck
        self.available_stat_points -= total_points
        
        # Update max health if vitality changed
        if vitality > 0:
            self.max_health = self.get_max_health()
            # Heal proportionally
            health_ratio = self.health / (self.max_health - vitality * 4)
            self.health = int(self.max_health * health_ratio)
        
        return True
    
    def get_character_summary(self) -> str:
        """Get a formatted summary of character stats."""
        derived = self.get_derived_stats()
        xp_current, xp_required = self.get_xp_progress()
        
        class_name = self.character_class.value.title() if self.character_class else "None"
        
        return f"""
**{self.character_name or 'Unnamed'}** (Level {self.level})
Class: {class_name}

**Base Attributes:**
• Strength: {self.strength}
• Agility: {self.agility}
• Intelligence: {self.intelligence}
• Vitality: {self.vitality}
• Luck: {self.luck}

**Derived Stats:**
• HP: {self.health}/{derived.hp_max}
• Attack: {derived.attack}
• Magic: {derived.magic}
• Crit Chance: {derived.crit_chance:.1f}%
• Dodge: {derived.dodge:.1f}%

**Progress:**
• XP: {self.experience} ({xp_current}/{xp_required} to next level)
• Available Stat Points: {self.available_stat_points}
"""

    def __repr__(self) -> str:
        return f"<Player(id={self.id}, user_id={self.user_id}, character_name={self.character_name}, level={self.level})>"
