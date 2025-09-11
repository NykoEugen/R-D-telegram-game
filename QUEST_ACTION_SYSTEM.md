# Quest Action System

## Overview

The Quest Action System now provides real game effects when players interact with quest buttons. Instead of just showing system notifications, each action now has meaningful consequences that affect the player's stats, energy, and risk level.

## Key Features

### 1. Real Game Effects
- **Energy Management**: Actions consume energy and can restore it
- **Stat Progression**: Actions increase relevant character stats
- **Risk System**: Actions affect the player's risk level
- **Consequence Processing**: Each action has calculated effects based on game rules

### 2. Available Quest Actions
- **ACCEPT** - Accept the quest (increases charisma, moderate energy cost)
- **INVESTIGATE** - Gather information (increases intellect, low energy cost)
- **PREPARE** - Get ready for action (increases stamina, low energy cost)
- **TALK** - Engage in dialogue (increases charisma, low energy cost)
- **SCOUT** - Scout the area (increases intellect, reduces risk)
- **FIGHT** - Engage in combat (increases bravery, high energy cost, increases risk)
- **RETREAT** - Withdraw safely (reduces risk, moderate energy cost)
- **RUN_AI** - Use AI generation (special action with AI response)
- **BACK** - Return to menu

### 3. Player State Integration
- **Energy System**: Actions consume energy (10-20 points typically)
- **Risk Level**: Actions can increase or decrease risk
- **Stats**: Actions improve relevant character attributes
- **Persistence**: Player state is saved and restored between sessions

## Implementation Details

### Action Processing Flow

1. **Action Selection**: Player clicks a quest action button
2. **State Retrieval**: System gets current player state from FSM
3. **Consequence Calculation**: ActionProcessor calculates effects
4. **State Update**: Player stats, energy, and risk are updated
5. **Response Generation**: System shows action results and updated stats
6. **Persistence**: Updated state is saved to database

### Energy Requirements

- **Quest Start**: Requires minimum 10 energy
- **Action Execution**: Each action has specific energy costs
- **Energy Display**: Current energy is shown in quest interface
- **Low Energy**: Players with insufficient energy cannot start quests

### Stat Progression

Actions improve relevant character stats:
- **ACCEPT/TALK**: +1 Charisma
- **INVESTIGATE/SCOUT**: +1 Intellect  
- **PREPARE**: +1 Stamina
- **FIGHT**: +1 Bravery

### Risk Management

Actions affect risk level:
- **SCOUT/PREPARE**: Reduces risk (-1)
- **FIGHT**: Increases risk (+2)
- **RETREAT**: Significantly reduces risk (-2)

## User Experience

### Quest Interface
```
⚔️ NEW QUEST RECEIVED! ⚔️

📜 Quest: [AI-generated quest description]

⚡ Energy: 85/100
⚠️ Risk Level: 2
📊 Stats: Bravery: 3, Charisma: 2, Intellect: 4, Stamina: 3

🎯 What will you do?

[Accept] [Investigate] [Prepare] [Talk]
[Scout] [Fight] [Retreat] [AI Action] [Back]
```

### Action Results
```
🎮 Action Executed

Action: scout
Result: Action completed successfully!

📊 Effects:
• Energy: 77/100
• Risk Level: 1
• Stats: {'bravery': 3, 'charisma': 2, 'intellect': 5, 'stamina': 3}

Scene: quest-12345-67890
State: QUEST_ACTIVE → DIALOGUE_CHOICE

*Action processed and logged!*
```

## Technical Implementation

### Core Components

1. **ActionProcessor** (`app/game/actions.py`)
   - Calculates action consequences
   - Applies stat changes and energy costs
   - Handles success/failure logic

2. **Quest Handler** (`app/handlers/commands/game.py`)
   - Processes quest commands
   - Manages player state
   - Handles action callbacks

3. **PlayerState** (`app/game/scenes.py`)
   - Stores player data
   - Manages energy and stats
   - Tracks progression

### Database Integration

- **FSM State**: Player state stored in finite state machine
- **PostgreSQL Sync**: State synchronized to database
- **Action Logging**: All actions logged with timestamps
- **Session Management**: State persists across bot restarts

## Configuration

### Energy Settings
- **Default Energy**: 100 points
- **Quest Minimum**: 10 energy required
- **Action Costs**: 5-20 energy per action
- **Energy Display**: Shown in quest interface

### Stat Ranges
- **Initial Stats**: All start at 1
- **Stat Increases**: +1 per relevant action
- **No Maximum**: Stats can grow indefinitely
- **Stat Display**: Shown in quest interface

## Testing

Run the test script to verify functionality:
```bash
python test_quest_actions.py
```

The test script will:
- Create a test player state
- Execute various quest actions
- Show energy and stat changes
- Verify consequence calculations

## Future Enhancements

1. **Quest Chains**: Link multiple quests together
2. **Difficulty Scaling**: Adjust action costs based on quest difficulty
3. **Reward System**: Add gold and XP rewards for quest completion
4. **Quest Types**: Different quest categories with unique mechanics
5. **Achievement System**: Track quest completion milestones

## Migration Notes

### Breaking Changes
- Quest actions now have real effects instead of just notifications
- Player state is required for quest participation
- Energy system is enforced for quest access

### Backward Compatibility
- Existing quest interface remains the same
- All previous actions are still available
- FSM state management is preserved

## Troubleshooting

### Common Issues

1. **"Not Enough Energy" Error**
   - Player needs minimum 10 energy to start quests
   - Solution: Wait for energy regeneration or use /status to check

2. **Action Not Working**
   - Check if player state exists in FSM
   - Verify action is in available actions list
   - Check energy requirements

3. **Stats Not Updating**
   - Ensure ActionProcessor is being called
   - Check if consequence is being applied
   - Verify player state is being saved

### Debug Information

The system provides detailed logging for troubleshooting:
- Action execution logs
- Player state changes
- Energy consumption tracking
- Risk level modifications
- Database sync status
