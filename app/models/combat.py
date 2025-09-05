"""
Combat system models for the Telegram RPG game bot.

This module defines combat-related models including enemies, combat state,
status effects, and combat actions.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import random
import math


class CombatAction(str, Enum):
    """Combat action types."""
    ATTACK = "attack"
    SKILL = "skill"
    ITEM = "item"
    RUN = "run"


class StatusEffect(str, Enum):
    """Status effect types."""
    BLEED = "bleed"      # -2 HP per turn (1-3 turns)
    WEAKEN = "weaken"    # -1 ATK (1-2 turns)
    STUN = "stun"        # Skip turn (1 turn)


class ClassSkill(str, Enum):
    """Class-specific skills."""
    # Warrior
    POWER_STRIKE = "power_strike"  # ATK + 2d4, CD 2 turns
    
    # Rogue
    BACKSTAB = "backstab"  # ATK + 1d4, 50% armor ignore if first
    
    # Mage
    ARCANE_BOLT = "arcane_bolt"  # MAG + 1d8, chance for Weaken
    
    # Cleric
    SMITE = "smite"  # MAG + 1d6, heal for INT
    
    # Ranger
    AIMED_SHOT = "aimed_shot"  # ATK + 1d6, +10% crit this turn


@dataclass
class StatusEffectInstance:
    """Instance of a status effect on a character."""
    effect_type: StatusEffect
    duration: int
    value: int = 0  # For effects that have variable values


@dataclass
class Enemy:
    """Enemy definition for combat."""
    name: str
    level: int
    hp_max: int
    attack: int
    magic: int
    agility: int
    armor: int = 0
    gold_reward: int = 0
    xp_reward: int = 0
    loot_table: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def hp_current(self) -> int:
        return getattr(self, '_hp_current', self.hp_max)
    
    @hp_current.setter
    def hp_current(self, value: int):
        self._hp_current = max(0, min(value, self.hp_max))


@dataclass
class CombatState:
    """Current state of a combat encounter."""
    player_hp: int
    player_max_hp: int
    enemy: Enemy
    turn_order: List[str]  # "player" or "enemy"
    current_turn: int = 0
    player_status_effects: List[StatusEffectInstance] = field(default_factory=list)
    enemy_status_effects: List[StatusEffectInstance] = field(default_factory=list)
    player_skill_cooldowns: Dict[ClassSkill, int] = field(default_factory=dict)
    combat_log: List[str] = field(default_factory=list)
    player_crit_bonus: float = 0.0  # Temporary crit bonus (e.g., from Aimed Shot)
    
    @property
    def is_player_turn(self) -> bool:
        return self.turn_order[self.current_turn % len(self.turn_order)] == "player"
    
    @property
    def is_combat_over(self) -> bool:
        return self.player_hp <= 0 or self.enemy.hp_current <= 0


class CombatCalculator:
    """Handles combat calculations and mechanics."""
    
    @staticmethod
    def roll_dice(sides: int, count: int = 1) -> int:
        """Roll dice with specified sides and count."""
        return sum(random.randint(1, sides) for _ in range(count))
    
    @staticmethod
    def calculate_initiative(player_agi: int, enemy_agi: int) -> List[str]:
        """Calculate turn order based on agility + random roll."""
        player_init = player_agi + random.randint(1, 6)
        enemy_init = enemy_agi + random.randint(1, 6)
        
        if player_init >= enemy_init:
            return ["player", "enemy"]
        else:
            return ["enemy", "player"]
    
    @staticmethod
    def calculate_hit_chance(player_agi: int, enemy_agi: int) -> float:
        """Calculate hit chance based on agility difference."""
        base_hit = 75.0
        agi_diff = (player_agi - enemy_agi) * 2.0
        hit_chance = base_hit + agi_diff
        return max(40.0, min(95.0, hit_chance))
    
    @staticmethod
    def calculate_damage(base_damage: int, dice_roll: int, is_crit: bool = False) -> int:
        """Calculate final damage with critical hit multiplier."""
        total_damage = base_damage + dice_roll
        if is_crit:
            total_damage = int(total_damage * 1.5)
        return max(1, total_damage)
    
    @staticmethod
    def calculate_crit_chance(base_crit: float, bonus: float = 0.0) -> float:
        """Calculate critical hit chance with bonuses."""
        return min(100.0, base_crit + bonus)
    
    @staticmethod
    def apply_armor_reduction(damage: int, armor: int, ignore_armor: bool = False) -> int:
        """Apply armor damage reduction."""
        if ignore_armor:
            return damage
        return max(1, damage - armor)
    
    @staticmethod
    def calculate_escape_chance(player_agi: int) -> float:
        """Calculate escape chance based on agility."""
        base_escape = 50.0
        agi_bonus = player_agi * 1.0
        return min(85.0, base_escape + agi_bonus)


class CombatActions:
    """Handles combat action execution."""
    
    @staticmethod
    def execute_attack(combat_state: CombatState, player_stats: Dict, is_player_attacking: bool) -> Tuple[int, bool, str]:
        """Execute a basic attack."""
        if is_player_attacking:
            attacker_attack = player_stats["attack"]
            attacker_agi = player_stats["agility"]
            attacker_crit = player_stats["crit_chance"] + combat_state.player_crit_bonus
            defender_agi = combat_state.enemy.agility
            defender_armor = combat_state.enemy.armor
            defender_hp = combat_state.enemy.hp_current
        else:
            attacker_attack = combat_state.enemy.attack
            attacker_agi = combat_state.enemy.agility
            attacker_crit = 5.0  # Base enemy crit chance
            defender_agi = player_stats["agility"]
            defender_armor = 0  # Player has no armor for now
            defender_hp = combat_state.player_hp
        
        # Calculate hit chance
        hit_chance = CombatCalculator.calculate_hit_chance(attacker_agi, defender_agi)
        
        # Roll for hit
        if random.random() * 100 > hit_chance:
            return 0, False, "miss"
        
        # Roll for crit
        is_crit = random.random() * 100 <= attacker_crit
        
        # Calculate damage
        dice_roll = CombatCalculator.roll_dice(6)
        damage = CombatCalculator.calculate_damage(attacker_attack, dice_roll, is_crit)
        
        # Apply armor reduction
        damage = CombatCalculator.apply_armor_reduction(damage, defender_armor)
        
        # Apply damage
        if is_player_attacking:
            combat_state.enemy.hp_current = defender_hp - damage
        else:
            combat_state.player_hp = defender_hp - damage
        
        return damage, is_crit, "hit"
    
    @staticmethod
    def execute_skill(combat_state: CombatState, player_stats: Dict, skill: ClassSkill) -> Tuple[int, bool, str, List[StatusEffectInstance]]:
        """Execute a class skill."""
        new_effects = []
        damage = 0
        is_crit = False
        result = "hit"
        
        if skill == ClassSkill.POWER_STRIKE:
            # Warrior: ATK + 2d4, CD 2 turns
            dice_roll = CombatCalculator.roll_dice(4, 2)
            base_damage = player_stats["attack"]
            hit_chance = CombatCalculator.calculate_hit_chance(player_stats["agility"], combat_state.enemy.agility)
            
            if random.random() * 100 > hit_chance:
                return 0, False, "miss", []
            
            is_crit = random.random() * 100 <= player_stats["crit_chance"]
            damage = CombatCalculator.calculate_damage(base_damage, dice_roll, is_crit)
            damage = CombatCalculator.apply_armor_reduction(damage, combat_state.enemy.armor)
            combat_state.enemy.hp_current = combat_state.enemy.hp_current - damage
            
        elif skill == ClassSkill.BACKSTAB:
            # Rogue: ATK + 1d4, 50% armor ignore if first
            dice_roll = CombatCalculator.roll_dice(4)
            base_damage = player_stats["attack"]
            hit_chance = CombatCalculator.calculate_hit_chance(player_stats["agility"], combat_state.enemy.agility)
            
            if random.random() * 100 > hit_chance:
                return 0, False, "miss", []
            
            is_crit = random.random() * 100 <= player_stats["crit_chance"]
            damage = CombatCalculator.calculate_damage(base_damage, dice_roll, is_crit)
            
            # 50% chance to ignore armor if player went first
            ignore_armor = combat_state.turn_order[0] == "player" and random.random() < 0.5
            damage = CombatCalculator.apply_armor_reduction(damage, combat_state.enemy.armor, ignore_armor)
            combat_state.enemy.hp_current = combat_state.enemy.hp_current - damage
            
        elif skill == ClassSkill.ARCANE_BOLT:
            # Mage: MAG + 1d8, chance for Weaken
            dice_roll = CombatCalculator.roll_dice(8)
            base_damage = player_stats["magic"]
            hit_chance = CombatCalculator.calculate_hit_chance(player_stats["agility"], combat_state.enemy.agility)
            
            if random.random() * 100 > hit_chance:
                return 0, False, "miss", []
            
            is_crit = random.random() * 100 <= player_stats["crit_chance"]
            damage = CombatCalculator.calculate_damage(base_damage, dice_roll, is_crit)
            damage = CombatCalculator.apply_armor_reduction(damage, combat_state.enemy.armor)
            combat_state.enemy.hp_current = combat_state.enemy.hp_current - damage
            
            # 30% chance to apply Weaken
            if random.random() < 0.3:
                new_effects.append(StatusEffectInstance(StatusEffect.WEAKEN, 1))
                
        elif skill == ClassSkill.SMITE:
            # Cleric: MAG + 1d6, heal for INT
            dice_roll = CombatCalculator.roll_dice(6)
            base_damage = player_stats["magic"]
            hit_chance = CombatCalculator.calculate_hit_chance(player_stats["agility"], combat_state.enemy.agility)
            
            if random.random() * 100 > hit_chance:
                return 0, False, "miss", []
            
            is_crit = random.random() * 100 <= player_stats["crit_chance"]
            damage = CombatCalculator.calculate_damage(base_damage, dice_roll, is_crit)
            damage = CombatCalculator.apply_armor_reduction(damage, combat_state.enemy.armor)
            combat_state.enemy.hp_current = combat_state.enemy.hp_current - damage
            
            # Heal player for INT
            heal_amount = player_stats["intelligence"]
            combat_state.player_hp = min(combat_state.player_max_hp, combat_state.player_hp + heal_amount)
            
        elif skill == ClassSkill.AIMED_SHOT:
            # Ranger: ATK + 1d6, +10% crit this turn
            dice_roll = CombatCalculator.roll_dice(6)
            base_damage = player_stats["attack"]
            hit_chance = CombatCalculator.calculate_hit_chance(player_stats["agility"], combat_state.enemy.agility)
            
            if random.random() * 100 > hit_chance:
                return 0, False, "miss", []
            
            # Apply temporary crit bonus
            combat_state.player_crit_bonus = 10.0
            is_crit = random.random() * 100 <= (player_stats["crit_chance"] + 10.0)
            damage = CombatCalculator.calculate_damage(base_damage, dice_roll, is_crit)
            damage = CombatCalculator.apply_armor_reduction(damage, combat_state.enemy.armor)
            combat_state.enemy.hp_current = combat_state.enemy.hp_current - damage
        
        return damage, is_crit, result, new_effects
    
    @staticmethod
    def execute_escape(combat_state: CombatState, player_stats: Dict) -> bool:
        """Execute escape attempt."""
        escape_chance = CombatCalculator.calculate_escape_chance(player_stats["agility"])
        return random.random() * 100 <= escape_chance
    
    @staticmethod
    def process_status_effects(combat_state: CombatState, player_stats: Dict) -> List[str]:
        """Process status effects at the end of turn."""
        effects_log = []
        
        # Process player status effects
        effects_to_remove = []
        for effect in combat_state.player_status_effects:
            if effect.effect_type == StatusEffect.BLEED:
                damage = 2
                combat_state.player_hp = max(0, combat_state.player_hp - damage)
                effects_log.append(f"Bleeding deals {damage} damage!")
            elif effect.effect_type == StatusEffect.WEAKEN:
                # Weaken affects attack power, handled in damage calculation
                pass
            
            effect.duration -= 1
            if effect.duration <= 0:
                effects_to_remove.append(effect)
        
        for effect in effects_to_remove:
            combat_state.player_status_effects.remove(effect)
        
        # Process enemy status effects
        effects_to_remove = []
        for effect in combat_state.enemy_status_effects:
            if effect.effect_type == StatusEffect.BLEED:
                damage = 2
                combat_state.enemy.hp_current = max(0, combat_state.enemy.hp_current - damage)
                effects_log.append(f"Enemy bleeding deals {damage} damage!")
            elif effect.effect_type == StatusEffect.WEAKEN:
                # Weaken affects attack power, handled in damage calculation
                pass
            elif effect.effect_type == StatusEffect.STUN:
                effects_log.append("Enemy is stunned and skips turn!")
            
            effect.duration -= 1
            if effect.duration <= 0:
                effects_to_remove.append(effect)
        
        for effect in effects_to_remove:
            combat_state.enemy_status_effects.remove(effect)
        
        return effects_log
    
    @staticmethod
    def update_skill_cooldowns(combat_state: CombatState):
        """Update skill cooldowns at the end of turn."""
        cooldowns_to_remove = []
        for skill, cooldown in combat_state.player_skill_cooldowns.items():
            combat_state.player_skill_cooldowns[skill] = cooldown - 1
            if combat_state.player_skill_cooldowns[skill] <= 0:
                cooldowns_to_remove.append(skill)
        
        for skill in cooldowns_to_remove:
            del combat_state.player_skill_cooldowns[skill]
    
    @staticmethod
    def get_available_skills(player_class: str, cooldowns: Dict[ClassSkill, int]) -> List[ClassSkill]:
        """Get list of available skills for player class."""
        class_skills = {
            "warrior": [ClassSkill.POWER_STRIKE],
            "rogue": [ClassSkill.BACKSTAB],
            "mage": [ClassSkill.ARCANE_BOLT],
            "cleric": [ClassSkill.SMITE],
            "ranger": [ClassSkill.AIMED_SHOT]
        }
        
        available = []
        for skill in class_skills.get(player_class, []):
            if skill not in cooldowns or cooldowns[skill] <= 0:
                available.append(skill)
        
        return available


class EnemyGenerator:
    """Generates enemies for combat encounters."""
    
    @staticmethod
    def generate_enemy(level: int, enemy_type: str = "goblin", region_multiplier: float = 1.0) -> Enemy:
        """Generate an enemy based on level, type, and region difficulty multiplier."""
        base_stats = {
            "goblin": {
                "name": "Goblin",
                "hp_multiplier": 8,
                "attack_multiplier": 1.2,
                "magic_multiplier": 0.5,
                "agi_multiplier": 1.5,
                "armor": 0,
                "gold_base": 5,
                "xp_base": 10
            },
            "orc": {
                "name": "Orc",
                "hp_multiplier": 12,
                "attack_multiplier": 1.5,
                "magic_multiplier": 0.3,
                "agi_multiplier": 0.8,
                "armor": 2,
                "gold_base": 8,
                "xp_base": 15
            },
            "skeleton": {
                "name": "Skeleton",
                "hp_multiplier": 6,
                "attack_multiplier": 1.0,
                "magic_multiplier": 0.8,
                "agi_multiplier": 1.2,
                "armor": 1,
                "gold_base": 3,
                "xp_base": 8
            },
            "wolf": {
                "name": "Wild Wolf",
                "hp_multiplier": 7,
                "attack_multiplier": 1.3,
                "magic_multiplier": 0.2,
                "agi_multiplier": 1.8,
                "armor": 0,
                "gold_base": 4,
                "xp_base": 8
            },
            "spider": {
                "name": "Giant Spider",
                "hp_multiplier": 5,
                "attack_multiplier": 1.1,
                "magic_multiplier": 0.6,
                "agi_multiplier": 2.0,
                "armor": 0,
                "gold_base": 3,
                "xp_base": 6
            },
            "ghost": {
                "name": "Wailing Ghost",
                "hp_multiplier": 4,
                "attack_multiplier": 0.8,
                "magic_multiplier": 1.5,
                "agi_multiplier": 1.3,
                "armor": 0,
                "gold_base": 2,
                "xp_base": 12
            },
            "gargoyle": {
                "name": "Stone Gargoyle",
                "hp_multiplier": 15,
                "attack_multiplier": 1.8,
                "magic_multiplier": 0.4,
                "agi_multiplier": 0.6,
                "armor": 3,
                "gold_base": 12,
                "xp_base": 20
            },
            "cave_troll": {
                "name": "Cave Troll",
                "hp_multiplier": 20,
                "attack_multiplier": 2.0,
                "magic_multiplier": 0.2,
                "agi_multiplier": 0.5,
                "armor": 2,
                "gold_base": 15,
                "xp_base": 25
            },
            "earth_elemental": {
                "name": "Earth Elemental",
                "hp_multiplier": 18,
                "attack_multiplier": 1.6,
                "magic_multiplier": 1.2,
                "agi_multiplier": 0.4,
                "armor": 4,
                "gold_base": 10,
                "xp_base": 22
            },
            "dragon": {
                "name": "Ancient Dragon",
                "hp_multiplier": 30,
                "attack_multiplier": 3.0,
                "magic_multiplier": 2.5,
                "agi_multiplier": 1.0,
                "armor": 5,
                "gold_base": 50,
                "xp_base": 100
            },
            "dark_dwarf": {
                "name": "Corrupted Dwarf",
                "hp_multiplier": 12,
                "attack_multiplier": 1.7,
                "magic_multiplier": 1.0,
                "agi_multiplier": 0.7,
                "armor": 3,
                "gold_base": 8,
                "xp_base": 18
            }
        }
        
        stats = base_stats.get(enemy_type, base_stats["goblin"])
        
        # Apply region difficulty multiplier
        return Enemy(
            name=stats["name"],
            level=level,
            hp_max=int(stats["hp_multiplier"] * level * region_multiplier),
            attack=int((stats["attack_multiplier"] * level + 2) * region_multiplier),
            magic=int((stats["magic_multiplier"] * level + 1) * region_multiplier),
            agility=int((stats["agi_multiplier"] * level + 8) * region_multiplier),
            armor=int(stats["armor"] * region_multiplier),
            gold_reward=int(stats["gold_base"] * level * region_multiplier),
            xp_reward=int(stats["xp_base"] * level * region_multiplier)
        )
