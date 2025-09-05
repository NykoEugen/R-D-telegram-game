# Dynamic Scene Graph System

This document describes the implementation of the dynamic scene graph system for the Telegram RPG game bot.

## Overview

The core game loop follows this pattern:
**City → Adventure → Scene → Choice → (Combat | Event) → Loot → Progress → Return to city**

The system is designed to be flexible and dynamic, with scenes that adapt based on player choices, stats, and previous actions.

## Architecture

### Core Components

1. **Scene Graph Manager** (`app/game/scenes.py`)
   - Manages the dynamic scene graph
   - Handles scene transitions and availability
   - Applies scene consequences
   - Checks end conditions

2. **Action System** (`app/game/actions.py`)
   - Defines available actions for each scene type
   - Processes action consequences
   - Applies stat changes and energy costs

3. **Scene Configuration** (`app/game/scenes.yaml`)
   - Data-driven scene definitions
   - Transition rules and weights
   - End conditions

4. **Game Handler** (`app/handlers/game.py`)
   - Main game loop handler
   - Integrates scene graph with FSM
   - Handles user interactions

## Scene Types

- **story**: Narrative scenes that advance the plot
- **choice**: Decision points with multiple options
- **encounter**: Combat or conflict situations
- **dialogue**: Social interactions
- **rest**: Recovery and energy restoration
- **exploration**: Discovery and investigation
- **quest**: Mission or objective scenes
- **loot**: Reward and treasure scenes
- **combat**: Battle encounters

## Scene Configuration Format

```yaml
scenes:
  - id: "scene_name"
    kind: "scene_type"
    weight: 1.0
    once: true                    # Can only be visited once
    requires: ["stat:bravery>=2"] # Requirements to access
    blocks: []                    # Conditions that block access
    cooldown: 2                   # Steps before can be revisited
    risk_delta: 2                 # Risk level change
    reward:                       # Rewards for completing
      gold: "1d6+2"
      xp: "1d4"
      items: ["item_name"]
    transitions:                  # Possible next scenes
      - to: "next_scene"
        weight: 0.7
        requires: ["visited:current_scene"]

end_conditions:
  - kind: "risk_threshold"
    threshold: 10
  - kind: "step_budget"
    dynamic: true
    base: 4
    bonus_by_stat:
      intellect: 0.5
      stamina: 0.5
```

## Player State

The `PlayerState` class tracks:
- **Energy**: Current energy level (0-100)
- **Risk Level**: Current risk/fatigue level
- **Stats**: Character attributes (bravery, charisma, intellect, stamina, level)
- **Visited Scenes**: Set of previously visited scenes
- **Scene Cooldowns**: Cooldown timers for scenes
- **Goals**: Active objectives
- **Step Count**: Number of actions taken

## Action System

### Available Actions

- **Attack**: Combat actions (energy cost: 15, risk: +2)
- **Defend**: Defensive actions (energy cost: 5, risk: -1)
- **Cast**: Magic actions (energy cost: 20, risk: +1)
- **Talk**: Social interactions (energy cost: 5, risk: 0)
- **Sneak**: Stealth actions (energy cost: 10, risk: -1)
- **Loot**: Search for items (energy cost: 5, risk: +1)
- **Flee**: Escape actions (energy cost: 10, risk: -2)
- **Wait**: Passive actions (energy cost: 0, risk: 0)
- **Accept**: Accept quests/offers (energy cost: 5, risk: +1)
- **Investigate**: Gather information (energy cost: 8, risk: 0)
- **Prepare**: Preparation actions (energy cost: 3, risk: -1)
- **Continue**: Progress forward (energy cost: 5, risk: 0)
- **Rest**: Recover energy (energy cost: -20, risk: -1)
- **Explore**: Discovery actions (energy cost: 12, risk: +2)
- **Negotiate**: Diplomatic actions (energy cost: 8, risk: 0)
- **Retreat**: Withdraw from danger (energy cost: 8, risk: -2)

### Action Consequences

Each action has:
- **Energy Cost**: How much energy it consumes
- **Risk Change**: How it affects risk level
- **Stat Changes**: Which stats it improves
- **Success Probability**: Chance of success
- **Scene Modifiers**: Context-dependent changes

## End Conditions

Adventures end when any of these conditions are met:

1. **Risk Threshold**: Risk level reaches maximum
2. **Energy Depleted**: Energy reaches zero
3. **Step Budget**: Maximum steps exceeded (dynamic based on stats)
4. **Goal Reached**: Specific objective completed
5. **Quest Completed**: Quest objective finished

## Usage

### Starting an Adventure

```python
# User types /adventure
# System creates PlayerState
# Gets starting scene from scene graph
# Generates scene description with AI
# Presents available actions
```

### Processing Actions

```python
# User selects action
# System processes action consequences
# Updates player state
# Checks end conditions
# Gets next scene
# Continues or ends adventure
```

### Scene Transitions

```python
# System checks scene requirements
# Validates cooldowns and blocks
# Applies weighted random selection
# Transitions to next scene
```

## Configuration

### Environment Variables

- `SCENE_SEED`: Random seed for scene generation
- `DEFAULT_ENERGY`: Starting energy level (default: 100)
- `MAX_ENERGY`: Maximum energy level (default: 100)
- `DEFAULT_RISK_THRESHOLD`: Risk threshold for ending (default: 10)
- `DEFAULT_STEP_BUDGET`: Base step budget (default: 4)

### Scene File

The scenes are defined in `app/game/scenes.yaml`. This file can be modified to:
- Add new scenes
- Change transition weights
- Modify requirements
- Add new end conditions

## Testing

Run the test script to verify the system:

```bash
python test_scene_graph.py
```

This will test:
- Scene loading and parsing
- Player state management
- Action processing
- Scene transitions
- End condition checking

## Integration with Existing System

The scene graph system integrates with:
- **FSM Service**: Stores player state in PostgreSQL
- **AI Generation Service**: Generates scene descriptions
- **i18n Service**: Provides localized text
- **Logging Service**: Tracks game events

## Future Enhancements

1. **Dice Expression Parser**: Parse reward expressions like "1d6+2"
2. **Dynamic Scene Generation**: AI-generated scenes
3. **Player Progression**: Level-based scene unlocks
4. **Multiplayer Support**: Shared adventures
5. **Save System**: Persistent adventure progress
6. **Achievement System**: Unlock conditions and rewards

## Troubleshooting

### Common Issues

1. **No Starting Scenes**: Check scene requirements and availability
2. **Action Failures**: Verify energy requirements and success probabilities
3. **Scene Loading Errors**: Validate YAML syntax and file path
4. **Memory Issues**: Monitor scene cooldowns and visited scenes

### Debug Mode

Enable debug logging to see detailed scene graph operations:

```python
import logging
logging.getLogger('app.game.scenes').setLevel(logging.DEBUG)
```

## Performance Considerations

- Scene graph is loaded once at startup
- Player state is cached in FSM
- Scene transitions use efficient weighted selection
- Cooldowns prevent infinite loops
- End conditions prevent runaway adventures
