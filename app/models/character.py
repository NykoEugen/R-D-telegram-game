"""
Character attributes and progression system for the Telegram RPG game bot.

This module defines character classes, attributes, and progression mechanics.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math


class CharacterClass(str, Enum):
    """Character class enumeration."""
    WARRIOR = "warrior"
    ROGUE = "rogue"
    MAGE = "mage"
    CLERIC = "cleric"
    RANGER = "ranger"


@dataclass
class BaseAttributes:
    """Base character attributes."""
    strength: int = 10      # STR - physical damage, carrying capacity
    agility: int = 10       # AGI - crit chance, dodge, accuracy
    intelligence: int = 10  # INT - magical damage, spell effectiveness
    vitality: int = 10      # VIT - HP, regeneration
    luck: int = 10          # LUK - rare loot/events chance


@dataclass
class DerivedStats:
    """Calculated stats derived from base attributes."""
    hp_max: int = 0
    attack: int = 0
    magic: int = 0
    crit_chance: float = 0.0
    dodge: float = 0.0


@dataclass
class ClassBonus:
    """Starting bonuses and level-up bonuses for character classes."""
    starting_bonus: BaseAttributes
    level_up_bonus: List[str]  # List of attributes to increase on level up


class CharacterProgression:
    """Character progression and leveling system."""
    
    # Class definitions with starting bonuses and level-up patterns
    CLASS_DEFINITIONS: Dict[CharacterClass, ClassBonus] = {
        CharacterClass.WARRIOR: ClassBonus(
            starting_bonus=BaseAttributes(strength=2, agility=0, intelligence=0, vitality=2, luck=0),
            level_up_bonus=["strength", "vitality"]
        ),
        CharacterClass.ROGUE: ClassBonus(
            starting_bonus=BaseAttributes(strength=0, agility=2, intelligence=0, vitality=0, luck=1),
            level_up_bonus=["agility", "luck"]
        ),
        CharacterClass.MAGE: ClassBonus(
            starting_bonus=BaseAttributes(strength=0, agility=0, intelligence=3, vitality=0, luck=0),
            level_up_bonus=["intelligence", "agility"]
        ),
        CharacterClass.CLERIC: ClassBonus(
            starting_bonus=BaseAttributes(strength=0, agility=0, intelligence=1, vitality=2, luck=0),
            level_up_bonus=["vitality", "intelligence"]
        ),
        CharacterClass.RANGER: ClassBonus(
            starting_bonus=BaseAttributes(strength=1, agility=2, intelligence=0, vitality=0, luck=0),
            level_up_bonus=["agility", "strength"]
        ),
    }
    
    @staticmethod
    def calculate_derived_stats(attributes: BaseAttributes) -> DerivedStats:
        """Calculate derived stats from base attributes."""
        return DerivedStats(
            hp_max=20 + 4 * attributes.vitality,
            attack=2 + attributes.strength,
            magic=2 + attributes.intelligence,
            crit_chance=min(35.0, 5.0 + 0.5 * attributes.agility),
            dodge=min(25.0, 2.0 + 0.4 * attributes.agility)
        )
    
    @staticmethod
    def get_xp_required_for_level(level: int) -> int:
        """Calculate XP required to reach the next level."""
        return 50 + 25 * level
    
    @staticmethod
    def get_total_xp_for_level(level: int) -> int:
        """Calculate total XP required to reach a specific level."""
        total_xp = 0
        for lvl in range(1, level):
            total_xp += CharacterProgression.get_xp_required_for_level(lvl)
        return total_xp
    
    @staticmethod
    def can_level_up(current_level: int, current_xp: int) -> bool:
        """Check if character can level up."""
        required_xp = CharacterProgression.get_total_xp_for_level(current_level + 1)
        return current_xp >= required_xp
    
    @staticmethod
    def get_level_from_xp(xp: int) -> int:
        """Calculate character level from total XP."""
        level = 1
        total_xp = 0
        
        while True:
            xp_for_next = CharacterProgression.get_xp_required_for_level(level)
            if total_xp + xp_for_next > xp:
                break
            total_xp += xp_for_next
            level += 1
        
        return level
    
    @staticmethod
    def get_xp_progress_to_next_level(current_level: int, current_xp: int) -> Tuple[int, int]:
        """Get XP progress towards next level (current, required)."""
        total_xp_for_current = CharacterProgression.get_total_xp_for_level(current_level)
        total_xp_for_next = CharacterProgression.get_total_xp_for_level(current_level + 1)
        
        xp_in_current_level = current_xp - total_xp_for_current
        xp_needed_for_next = total_xp_for_next - total_xp_for_current
        
        return xp_in_current_level, xp_needed_for_next
    
    @staticmethod
    def apply_class_bonuses(attributes: BaseAttributes, character_class: CharacterClass) -> BaseAttributes:
        """Apply starting class bonuses to attributes."""
        class_bonus = CharacterProgression.CLASS_DEFINITIONS[character_class].starting_bonus
        
        return BaseAttributes(
            strength=attributes.strength + class_bonus.strength,
            agility=attributes.agility + class_bonus.agility,
            intelligence=attributes.intelligence + class_bonus.intelligence,
            vitality=attributes.vitality + class_bonus.vitality,
            luck=attributes.luck + class_bonus.luck
        )
    
    @staticmethod
    def get_level_up_bonuses(character_class: CharacterClass, levels_gained: int = 1) -> BaseAttributes:
        """Get attribute bonuses for leveling up."""
        level_up_bonus = CharacterProgression.CLASS_DEFINITIONS[character_class].level_up_bonus
        
        # Each level gives 2 distributable points + class bonuses
        distributable_points = levels_gained * 2
        
        # Calculate class bonuses
        class_bonuses = BaseAttributes(strength=0, agility=0, intelligence=0, vitality=0, luck=0)
        for _ in range(levels_gained):
            for attr in level_up_bonus:
                if attr == "strength":
                    class_bonuses.strength += 1
                elif attr == "agility":
                    class_bonuses.agility += 1
                elif attr == "intelligence":
                    class_bonuses.intelligence += 1
                elif attr == "vitality":
                    class_bonuses.vitality += 1
                elif attr == "luck":
                    class_bonuses.luck += 1
        
        return class_bonuses, distributable_points
    
    @staticmethod
    def get_class_description(character_class: CharacterClass) -> str:
        """Get description of character class."""
        descriptions = {
            CharacterClass.WARRIOR: "Strong and resilient fighters who excel in close combat. High strength and vitality.",
            CharacterClass.ROGUE: "Agile and lucky adventurers who rely on speed and fortune. High agility and luck.",
            CharacterClass.MAGE: "Intelligent spellcasters who wield powerful magic. High intelligence and agility.",
            CharacterClass.CLERIC: "Divine healers and protectors. Balanced intelligence and vitality.",
            CharacterClass.RANGER: "Versatile hunters and scouts. Balanced strength and agility."
        }
        return descriptions.get(character_class, "Unknown class")


class CharacterManager:
    """Manages character creation, progression, and stat calculations."""
    
    @staticmethod
    def create_character(character_class: CharacterClass, name: str) -> Dict:
        """Create a new character with class bonuses applied."""
        base_attributes = BaseAttributes()
        attributes_with_bonuses = CharacterProgression.apply_class_bonuses(base_attributes, character_class)
        derived_stats = CharacterProgression.calculate_derived_stats(attributes_with_bonuses)
        
        return {
            "name": name,
            "character_class": character_class,
            "level": 1,
            "experience": 0,
            "attributes": attributes_with_bonuses,
            "derived_stats": derived_stats,
            "available_stat_points": 0,  # Points to distribute manually
            "health": derived_stats.hp_max,
            "max_health": derived_stats.hp_max
        }
    
    @staticmethod
    def level_up_character(character_data: Dict, stat_distribution: Optional[BaseAttributes] = None) -> Dict:
        """Level up a character and apply bonuses."""
        current_level = character_data["level"]
        new_level = CharacterProgression.get_level_from_xp(character_data["experience"])
        
        if new_level <= current_level:
            return character_data  # No level up
        
        levels_gained = new_level - current_level
        character_class = CharacterClass(character_data["character_class"])
        
        # Get class bonuses and distributable points
        class_bonuses, distributable_points = CharacterProgression.get_level_up_bonuses(
            character_class, levels_gained
        )
        
        # Apply class bonuses automatically
        current_attrs = character_data["attributes"]
        new_attributes = BaseAttributes(
            strength=current_attrs.strength + class_bonuses.strength,
            agility=current_attrs.agility + class_bonuses.agility,
            intelligence=current_attrs.intelligence + class_bonuses.intelligence,
            vitality=current_attrs.vitality + class_bonuses.vitality,
            luck=current_attrs.luck + class_bonuses.luck
        )
        
        # Apply manual stat distribution if provided
        if stat_distribution:
            new_attributes = BaseAttributes(
                strength=new_attributes.strength + stat_distribution.strength,
                agility=new_attributes.agility + stat_distribution.agility,
                intelligence=new_attributes.intelligence + stat_distribution.intelligence,
                vitality=new_attributes.vitality + stat_distribution.vitality,
                luck=new_attributes.luck + stat_distribution.luck
            )
        
        # Recalculate derived stats
        new_derived_stats = CharacterProgression.calculate_derived_stats(new_attributes)
        
        # Update character data
        character_data.update({
            "level": new_level,
            "attributes": new_attributes,
            "derived_stats": new_derived_stats,
            "available_stat_points": distributable_points - (
                (stat_distribution.strength + stat_distribution.agility + 
                 stat_distribution.intelligence + stat_distribution.vitality + 
                 stat_distribution.luck) if stat_distribution else 0
            ),
            "max_health": new_derived_stats.hp_max,
            "health": new_derived_stats.hp_max  # Full heal on level up
        })
        
        return character_data
    
    @staticmethod
    def add_experience(character_data: Dict, xp_gained: int) -> Dict:
        """Add experience to character and handle level ups."""
        character_data["experience"] += xp_gained
        
        # Check for level ups
        old_level = character_data["level"]
        new_level = CharacterProgression.get_level_from_xp(character_data["experience"])
        
        if new_level > old_level:
            character_data = CharacterManager.level_up_character(character_data)
        
        return character_data
    
    @staticmethod
    def get_character_summary(character_data: Dict) -> str:
        """Get a formatted summary of character stats."""
        attrs = character_data["attributes"]
        derived = character_data["derived_stats"]
        
        return f"""
**{character_data['name']}** (Level {character_data['level']})
Class: {character_data['character_class'].title()}

**Base Attributes:**
• Strength: {attrs.strength}
• Agility: {attrs.agility}
• Intelligence: {attrs.intelligence}
• Vitality: {attrs.vitality}
• Luck: {attrs.luck}

**Derived Stats:**
• HP: {character_data['health']}/{derived.hp_max}
• Attack: {derived.attack}
• Magic: {derived.magic}
• Crit Chance: {derived.crit_chance:.1f}%
• Dodge: {derived.dodge:.1f}%

**Progress:**
• XP: {character_data['experience']}
• Available Stat Points: {character_data.get('available_stat_points', 0)}
"""
