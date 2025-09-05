# Character Attributes and Progression System

This document describes the comprehensive character attributes and progression system implemented for the Telegram RPG game bot.

## 🎯 Overview

The character system implements a complete RPG character progression with:
- **5 Base Attributes** (STR, AGI, INT, VIT, LUK)
- **5 Character Classes** with unique bonuses and progression
- **Derived Stats** calculated from base attributes
- **Leveling System** with XP curves and stat point distribution
- **Interactive Character Creation** and management

## 📊 Base Attributes

### Core Attributes
- **STR (Strength)** - Physical damage, carrying capacity
- **AGI (Agility)** - Critical hit chance, dodge chance, accuracy
- **INT (Intelligence)** - Magical damage, spell effectiveness
- **VIT (Vitality)** - Maximum HP, regeneration
- **LUK (Luck)** - Rare loot/events chance

### Starting Values
All characters start with **10** in each attribute, with class bonuses applied during creation.

## 🏆 Derived Stats (Formulas)

All derived stats are calculated automatically from base attributes:

```
HP_MAX = 20 + 4 × VIT
ATK = 2 + STR
MAG = 2 + INT
CRIT_CHANCE = min(35%, 5% + 0.5 × AGI)
DODGE = min(25%, 2% + 0.4 × AGI)
```

## ⚔️ Character Classes

### 1. Warrior
- **Starting Bonuses:** STR +2, VIT +2
- **Level Up:** +STR, +VIT
- **Description:** Strong and resilient fighters who excel in close combat

### 2. Rogue
- **Starting Bonuses:** AGI +2, LUK +1
- **Level Up:** +AGI, +LUK
- **Description:** Agile and lucky adventurers who rely on speed and fortune

### 3. Mage
- **Starting Bonuses:** INT +3
- **Level Up:** +INT, +AGI
- **Description:** Intelligent spellcasters who wield powerful magic

### 4. Cleric
- **Starting Bonuses:** INT +1, VIT +2
- **Level Up:** +VIT, +INT
- **Description:** Divine healers and protectors

### 5. Ranger
- **Starting Bonuses:** STR +1, AGI +2
- **Level Up:** +AGI, +STR
- **Description:** Versatile hunters and scouts

## 📈 Leveling System

### XP Requirements
- **Formula:** XP_to_next = 50 + 25 × level
- **Examples:**
  - Level 1 → 2: 75 XP
  - Level 2 → 3: 100 XP
  - Level 3 → 4: 125 XP

### Level Up Benefits
- **Automatic Class Bonuses:** Based on class progression pattern
- **Distributable Points:** 2 points per level to assign manually
- **Full HP Restoration:** Character is fully healed on level up

## 🎮 Commands

### Character Creation
- `/create_character` - Start character creation process
- Interactive flow: Name → Class Selection → Confirmation

### Character Management
- `/character` - View character stats and management options
- **Available Actions:**
  - View detailed stats
  - Level up (if enough XP)
  - Distribute stat points

## 🗄️ Database Schema

### Player Model Updates
```sql
-- New columns added to players table
ALTER TABLE players ADD COLUMN luck INTEGER NOT NULL DEFAULT 10;
ALTER TABLE players ADD COLUMN available_stat_points INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players ALTER COLUMN character_class TYPE VARCHAR(20);
```

### Key Fields
- `strength`, `agility`, `intelligence`, `vitality`, `luck` - Base attributes
- `available_stat_points` - Points available for manual distribution
- `character_class` - Character class (warrior, rogue, mage, cleric, ranger)
- `level`, `experience` - Level and XP tracking

## 🌍 Localization

### Supported Languages
- **English** (`en.json`)
- **Ukrainian** (`uk.json`)

### Localized Content
- Character creation flow
- Class descriptions
- Stat displays
- Level up messages
- Error messages

## 🔧 Technical Implementation

### Core Files
- `app/models/character.py` - Character system logic
- `app/models/player.py` - Database model with character methods
- `app/handlers/commands/character.py` - Bot command handlers
- `alembic/versions/c030eb610a8e_*.py` - Database migration

### Key Classes
- `BaseAttributes` - Character attribute container
- `DerivedStats` - Calculated stats container
- `CharacterClass` - Class enumeration
- `CharacterProgression` - Progression logic
- `CharacterManager` - High-level character operations

## 🧪 Testing

The system includes comprehensive tests covering:
- Base attribute creation and access
- Derived stats calculations
- Class bonus applications
- XP and leveling mechanics
- Character creation and management
- Level up bonus calculations

## 🚀 Usage Examples

### Creating a Character
1. User runs `/create_character`
2. Enters character name (2-20 characters)
3. Selects class from inline keyboard
4. Confirms creation
5. Character is created with class bonuses applied

### Viewing Stats
1. User runs `/character`
2. Views character summary with all stats
3. Can access detailed stats, level up, or distribute points

### Leveling Up
1. Character gains XP through gameplay
2. When enough XP is accumulated, can level up
3. Receives automatic class bonuses + 2 distributable points
4. Can manually assign distributable points

## 🎯 Future Enhancements

### Planned Features
- Equipment system affecting stats
- Skill trees and specializations
- Prestige/rebirth system
- Stat caps and diminishing returns
- More character classes
- Racial bonuses

### Integration Points
- Combat system (using ATK, MAG, CRIT, DODGE)
- Loot system (using LUK)
- Quest rewards (XP, stat points)
- Equipment bonuses
- Achievement system

## 📝 Notes

- All calculations are done server-side for security
- Character data is persisted in PostgreSQL
- System is fully async and database-optimized
- Supports both English and Ukrainian languages
- Extensible design for future enhancements

This character system provides a solid foundation for RPG gameplay with clear progression mechanics and engaging character customization options.
