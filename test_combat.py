#!/usr/bin/env python3
"""
Test script for the combat system.

This script demonstrates the turn-based combat system with all features:
- Initiative calculation
- Hit/miss mechanics
- Class skills with cooldowns
- Status effects
- Combat flow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.combat import (
    CombatState, Enemy, CombatAction, ClassSkill, StatusEffect,
    CombatCalculator, CombatActions, EnemyGenerator, StatusEffectInstance
)
from app.models.character import CharacterClass, BaseAttributes, CharacterProgression


def create_test_player():
    """Create a test player with warrior class."""
    attributes = BaseAttributes(strength=12, agility=10, intelligence=10, vitality=12, luck=10)
    derived_stats = CharacterProgression.calculate_derived_stats(attributes)
    
    return {
        "name": "Test Warrior",
        "character_class": "warrior",
        "level": 1,
        "health": derived_stats.hp_max,
        "max_health": derived_stats.hp_max,
        "attributes": attributes,
        "derived_stats": derived_stats
    }


def print_combat_status(combat_state: CombatState):
    """Print current combat status."""
    print(f"\n{'='*50}")
    print(f"⚔️ COMBAT STATUS")
    print(f"{'='*50}")
    
    # Enemy status
    enemy_hp_percent = (combat_state.enemy.hp_current / combat_state.enemy.hp_max) * 100
    enemy_hp_bar = "█" * int(enemy_hp_percent / 10) + "░" * (10 - int(enemy_hp_percent / 10))
    print(f"Enemy: {combat_state.enemy.name} (Level {combat_state.enemy.level})")
    print(f"HP: {enemy_hp_bar} {combat_state.enemy.hp_current}/{combat_state.enemy.hp_max}")
    
    # Player status
    player_hp_percent = (combat_state.player_hp / combat_state.player_max_hp) * 100
    player_hp_bar = "█" * int(player_hp_percent / 10) + "░" * (10 - int(player_hp_percent / 10))
    print(f"Player: {player_hp_bar} {combat_state.player_hp}/{combat_state.player_max_hp}")
    
    # Status effects
    if combat_state.player_status_effects:
        effects = [effect.effect_type.value for effect in combat_state.player_status_effects]
        print(f"Player effects: {', '.join(effects)}")
    
    if combat_state.enemy_status_effects:
        effects = [effect.effect_type.value for effect in combat_state.enemy_status_effects]
        print(f"Enemy effects: {', '.join(effects)}")
    
    # Recent actions
    if combat_state.combat_log:
        print(f"\nRecent actions:")
        for action in combat_state.combat_log[-3:]:
            print(f"  • {action}")


def simulate_combat():
    """Simulate a complete combat encounter."""
    print("🎮 COMBAT SYSTEM TEST")
    print("="*50)
    
    # Create test player
    player_data = create_test_player()
    print(f"Player: {player_data['name']} (Level {player_data['level']})")
    print(f"Class: {player_data['character_class']}")
    print(f"HP: {player_data['health']}/{player_data['max_health']}")
    print(f"Attack: {player_data['derived_stats'].attack}")
    print(f"Magic: {player_data['derived_stats'].magic}")
    print(f"Crit Chance: {player_data['derived_stats'].crit_chance:.1f}%")
    
    # Generate enemy
    enemy = EnemyGenerator.generate_enemy(1, "goblin")
    print(f"\nEnemy: {enemy.name} (Level {enemy.level})")
    print(f"HP: {enemy.hp_max}")
    print(f"Attack: {enemy.attack}")
    print(f"Agility: {enemy.agility}")
    
    # Calculate initiative
    turn_order = CombatCalculator.calculate_initiative(
        player_data["attributes"].agility,
        enemy.agility
    )
    print(f"\nInitiative: {' → '.join(turn_order)}")
    
    # Create combat state
    combat_state = CombatState(
        player_hp=player_data["health"],
        player_max_hp=player_data["max_health"],
        enemy=enemy,
        turn_order=turn_order
    )
    
    print_combat_status(combat_state)
    
    # Combat loop
    turn = 0
    while not combat_state.is_combat_over:
        turn += 1
        print(f"\n--- TURN {turn} ---")
        
        if combat_state.is_player_turn:
            print("Player's turn!")
            
            # Simulate player action (attack or skill)
            if turn == 1:
                # Use skill on first turn
                available_skills = CombatActions.get_available_skills(
                    player_data["character_class"], 
                    combat_state.player_skill_cooldowns
                )
                if available_skills:
                    skill = available_skills[0]
                    print(f"Using skill: {skill.value}")
                    
                    damage, is_crit, result, new_effects = CombatActions.execute_skill(
                        combat_state,
                        {
                            "attack": player_data["derived_stats"].attack,
                            "magic": player_data["derived_stats"].magic,
                            "agility": player_data["attributes"].agility,
                            "intelligence": player_data["attributes"].intelligence,
                            "crit_chance": player_data["derived_stats"].crit_chance
                        },
                        skill
                    )
                    
                    # Add skill to cooldown
                    combat_state.player_skill_cooldowns[skill] = 2
                    
                    # Add effects to enemy
                    combat_state.enemy_status_effects.extend(new_effects)
                    
                    # Add to combat log
                    skill_name = skill.value.replace("_", " ").title()
                    if result == "miss":
                        combat_state.combat_log.append(f"{skill_name} misses!")
                    elif is_crit:
                        combat_state.combat_log.append(f"Critical {skill_name}! You deal {damage} damage!")
                    else:
                        combat_state.combat_log.append(f"{skill_name} deals {damage} damage!")
                    
                    # Add effect messages
                    for effect in new_effects:
                        effect_name = effect.effect_type.value.title()
                        combat_state.combat_log.append(f"Enemy is affected by {effect_name}!")
                else:
                    # Regular attack
                    print("Using regular attack")
                    damage, is_crit, result = CombatActions.execute_attack(
                        combat_state,
                        {
                            "attack": player_data["derived_stats"].attack,
                            "agility": player_data["attributes"].agility,
                            "crit_chance": player_data["derived_stats"].crit_chance
                        },
                        True
                    )
                    
                    if result == "miss":
                        combat_state.combat_log.append("You miss your attack!")
                    elif is_crit:
                        combat_state.combat_log.append(f"Critical hit! You deal {damage} damage!")
                    else:
                        combat_state.combat_log.append(f"You deal {damage} damage!")
            else:
                # Regular attack
                print("Using regular attack")
                damage, is_crit, result = CombatActions.execute_attack(
                    combat_state,
                    {
                        "attack": player_data["derived_stats"].attack,
                        "agility": player_data["attributes"].agility,
                        "crit_chance": player_data["derived_stats"].crit_chance
                    },
                    True
                )
                
                if result == "miss":
                    combat_state.combat_log.append("You miss your attack!")
                elif is_crit:
                    combat_state.combat_log.append(f"Critical hit! You deal {damage} damage!")
                else:
                    combat_state.combat_log.append(f"You deal {damage} damage!")
            
            # Check if enemy is defeated
            if combat_state.enemy.hp_current <= 0:
                print("\n🎉 VICTORY! Enemy defeated!")
                break
        else:
            print("Enemy's turn!")
            
            # Check if enemy is stunned
            enemy_stunned = any(effect.effect_type == StatusEffect.STUN for effect in combat_state.enemy_status_effects)
            
            if enemy_stunned:
                combat_state.combat_log.append("Enemy is stunned and skips their turn!")
            else:
                # Execute enemy attack
                damage, is_crit, result = CombatActions.execute_attack(
                    combat_state,
                    {
                        "attack": combat_state.enemy.attack,
                        "agility": combat_state.enemy.agility,
                        "crit_chance": 5.0
                    },
                    False
                )
                
                if result == "miss":
                    combat_state.combat_log.append("Enemy misses their attack!")
                elif is_crit:
                    combat_state.combat_log.append(f"Enemy critical hit! You take {damage} damage!")
                else:
                    combat_state.combat_log.append(f"Enemy deals {damage} damage!")
            
            # Check if player is defeated
            if combat_state.player_hp <= 0:
                print("\n💀 DEFEAT! Player defeated!")
                break
        
        # Process status effects
        status_logs = CombatActions.process_status_effects(combat_state, {
            "attack": player_data["derived_stats"].attack,
            "agility": player_data["attributes"].agility,
            "intelligence": player_data["attributes"].intelligence
        })
        combat_state.combat_log.extend(status_logs)
        
        # Update cooldowns
        CombatActions.update_skill_cooldowns(combat_state)
        
        # Reset temporary bonuses
        combat_state.player_crit_bonus = 0.0
        
        # Advance turn
        combat_state.current_turn += 1
        
        print_combat_status(combat_state)
        
        # Safety break to prevent infinite loops
        if turn > 20:
            print("\n⚠️ Combat ended due to turn limit!")
            break
    
    # Final results
    print(f"\n{'='*50}")
    print("COMBAT RESULTS")
    print(f"{'='*50}")
    
    if combat_state.enemy.hp_current <= 0:
        print("🎉 VICTORY!")
        print(f"XP gained: {enemy.xp_reward}")
        print(f"Gold gained: {enemy.gold_reward}")
    elif combat_state.player_hp <= 0:
        print("💀 DEFEAT!")
        print("Player returns to town with 1 HP")
    else:
        print("⚠️ Combat ended without clear winner")
    
    print(f"\nTotal turns: {turn}")
    print(f"Final player HP: {combat_state.player_hp}/{combat_state.player_max_hp}")
    print(f"Final enemy HP: {combat_state.enemy.hp_current}/{combat_state.enemy.hp_max}")


if __name__ == "__main__":
    simulate_combat()
