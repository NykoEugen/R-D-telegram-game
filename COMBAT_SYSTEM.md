# Combat System Documentation

## 🎯 Overview

The turn-based combat system implements a complete RPG combat experience with initiative-based turns, class-specific skills, status effects, and strategic depth. The system is designed to be simple yet engaging, with clear mechanics and visual feedback.

## ⚔️ Core Mechanics

### Turn Order & Initiative
- **Initiative Calculation**: `AGI_hero + 1d6` vs `AGI_enemy + 1d6`
- **Turn Structure**: Hero Turn → Enemy Turn (repeat)
- **First Turn**: Determined by initiative roll

### Combat Actions

#### 1. Attack (Physical)
- **Damage Formula**: `ATK + 1d6`
- **Critical Hits**: 1.5x damage multiplier
- **Hit Chance**: `75% + (AGI_hero - AGI_enemy) × 2%` (capped at 40-95%)

#### 2. Class Skills
Each class has one unique active skill with a 2-turn cooldown:

**Warrior - Power Strike**
- Damage: `ATK + 2d4`
- Cooldown: 2 turns

**Rogue - Backstab**
- Damage: `ATK + 1d4`
- Special: 50% chance to ignore armor if hero goes first

**Mage - Arcane Bolt**
- Damage: `MAG + 1d8`
- Special: 30% chance to apply "Weaken" (-1 ATK for 1 turn)

**Cleric - Smite**
- Damage: `MAG + 1d6`
- Special: Heals hero for INT amount

**Ranger - Aimed Shot**
- Damage: `ATK + 1d6`
- Special: +10% crit chance for this turn

#### 3. Items
- Potions, scrolls, and consumables (placeholder for future implementation)

#### 4. Run (Escape)
- **Escape Chance**: `50% + 1% × AGI` (capped at 85%)
- **Success**: Exit combat immediately
- **Failure**: Enemy gets a turn

## 🎲 Status Effects

### Bleed
- **Effect**: -2 HP at end of turn
- **Duration**: 1-3 turns
- **Source**: Critical hits, special attacks

### Weaken
- **Effect**: -1 ATK
- **Duration**: 1-2 turns
- **Source**: Mage's Arcane Bolt

### Stun
- **Effect**: Skip turn
- **Duration**: 1 turn
- **Source**: Special attacks, critical hits

## 🏆 Combat Resolution

### Victory Conditions
- Enemy HP reaches 0
- **Rewards**: XP, Gold, potential loot

### Defeat Conditions
- Player HP reaches 0
- **Penalties**: -10% gold, HP set to 1, return to town

### Escape
- Successful escape attempt
- No rewards or penalties

## 🎮 User Interface

### Combat Display
```
⚔️ Combat

Goblin (Level 1)
HP: ████████░░ 8/10

You
HP: ██████████ 24/24

Recent Actions:
• You deal 6 damage!
• Enemy deals 3 damage!
```

### Action Buttons
- ⚔️ Attack
- 🎯 Skill (class-specific)
- 🧪 Item
- 🏃 Run

## 🏗️ Technical Implementation

### Core Files
- `app/models/combat.py` - Combat models and logic
- `app/handlers/combat.py` - Combat UI and flow
- `app/handlers/commands/combat.py` - Combat commands
- `test_combat.py` - Combat system test

### Key Classes

#### CombatState
```python
@dataclass
class CombatState:
    player_hp: int
    player_max_hp: int
    enemy: Enemy
    turn_order: List[str]
    current_turn: int = 0
    player_status_effects: List[StatusEffectInstance] = field(default_factory=list)
    enemy_status_effects: List[StatusEffectInstance] = field(default_factory=list)
    player_skill_cooldowns: Dict[ClassSkill, int] = field(default_factory=dict)
    combat_log: List[str] = field(default_factory=list)
    player_crit_bonus: float = 0.0
```

#### Enemy
```python
@dataclass
class Enemy:
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
```

### Combat Flow
1. **Initiation**: Calculate initiative, create combat state
2. **Player Turn**: Display actions, process player choice
3. **Enemy Turn**: Execute enemy AI, apply damage
4. **Status Effects**: Process end-of-turn effects
5. **Cooldowns**: Update skill cooldowns
6. **Check End**: Victory, defeat, or continue

## 🌍 Localization

### Supported Languages
- **English** (`en.json`)
- **Ukrainian** (`uk.json`)

### Combat Translations
- Combat status messages
- Action button labels
- Skill names and descriptions
- Result messages
- Victory/defeat screens

## 🧪 Testing

### Test Script
Run `python3 test_combat.py` to see a complete combat simulation:

```bash
🎮 COMBAT SYSTEM TEST
==================================================
Player: Test Warrior (Level 1)
Class: warrior
HP: 68/68
Attack: 14
Magic: 12
Crit Chance: 10.0%

Enemy: Goblin (Level 1)
HP: 8
Attack: 3
Agility: 9

Initiative: player → enemy
```

### Test Coverage
- Initiative calculation
- Hit/miss mechanics
- Damage calculation
- Critical hits
- Class skills
- Status effects
- Combat flow
- Victory/defeat conditions

## 🎯 Commands

### Available Commands
- `/combat` - Start combat with random enemy
- `/fight` - Alias for /combat
- `/battle` - Alias for /combat

### Integration
The combat system integrates with:
- Character system (stats, level, class)
- FSM system (combat states)
- Localization system (multi-language support)
- Database system (player data persistence)

## 🚀 Future Enhancements

### Planned Features
- **Equipment System**: Weapons and armor affecting combat stats
- **More Enemy Types**: Dragons, undead, elementals
- **Advanced Skills**: Multi-target attacks, buffs, debuffs
- **Combat Modifiers**: Terrain effects, weather conditions
- **Loot System**: Equipment drops, rare items
- **Combat Achievements**: Special rewards for combat feats

### Technical Improvements
- **AI System**: Smarter enemy behavior
- **Animation System**: Visual combat effects
- **Sound System**: Combat audio feedback
- **Replay System**: Combat history and analysis
- **Balance System**: Dynamic difficulty adjustment

## 📊 Balance Notes

### Current Balance
- **Player Advantage**: Higher HP, better stats, class skills
- **Enemy Advantage**: No cooldowns, consistent damage
- **Risk/Reward**: Escape vs. continued combat

### Design Philosophy
- **Simple Rules**: Easy to understand mechanics
- **Strategic Depth**: Meaningful choices in combat
- **Visual Feedback**: Clear status and progress indicators
- **Fair Play**: Predictable outcomes with random elements

## 🔧 Configuration

### Combat Parameters
```python
# Hit chance bounds
MIN_HIT_CHANCE = 40.0
MAX_HIT_CHANCE = 95.0

# Escape chance cap
MAX_ESCAPE_CHANCE = 85.0

# Critical hit multiplier
CRIT_MULTIPLIER = 1.5

# Skill cooldown
DEFAULT_SKILL_COOLDOWN = 2
```

### Enemy Scaling
```python
# Enemy stats scale with level
hp_multiplier = base_hp * level
attack_multiplier = base_attack * level + 2
agility_multiplier = base_agility * level + 8
```

This combat system provides a solid foundation for RPG gameplay with room for expansion and customization. The modular design allows for easy addition of new features while maintaining the core turn-based combat experience.
