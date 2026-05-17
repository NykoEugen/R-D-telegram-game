# Quest Loop System

This document describes the quest loop system implementation for the Telegram RPG game bot.

## Overview

The quest loop system provides a dynamic, state-driven adventure experience that integrates:
- **Actions**: Player choices with consequences
- **States**: FSM-based game state management
- **Scene Graph**: Dynamic scene transitions and progression
- **AI Integration**: Intelligent action selection

## Architecture

### Core Components

1. **QuestLoopService** (`app/services/quest_loop_service.py`)
   - Main orchestrator for quest flow
   - Integrates all subsystems
   - Manages player state and scene transitions

2. **Action System** (`app/game/actions.py`)
   - Defines available actions and their consequences
   - Processes action results and stat changes
   - Filters actions based on player state

3. **Scene Graph** (`app/game/scenes.py`)
   - Manages scene definitions and transitions
   - Handles scene availability and cooldowns
   - Applies scene consequences and rewards

4. **FSM States** (`app/game/states.py`)
   - Defines game state machine states
   - Manages state transitions
   - Integrates with PostgreSQL storage

5. **Quest Handlers** (`app/handlers/quest_handlers.py`)
   - Telegram bot command handlers
   - Callback query processing
   - User interaction management

## Game Flow

### 1. Quest Start
```
User: /quest
→ QuestLoopService.start_quest_loop()
→ Create/Get Player State
→ Select Starting Scene
→ Present Scene with Actions
```

### 2. Action Processing
```
User: Clicks Action Button
→ QuestHandlers.action_callback_handler()
→ QuestLoopService.process_action()
→ Apply Action Consequences
→ Update Player State
→ Select Next Scene
→ Present New Scene
```

### 3. Quest End
```
End Condition Met
→ QuestLoopService._end_quest_loop()
→ Update Session Status
→ Return to Main Menu
```

## Scene Types

| Scene Type | Description | Available Actions |
|------------|-------------|-------------------|
| `story` | Narrative scenes | Continue, Investigate, AI Action |
| `choice` | Decision points | Accept, Talk, Investigate, AI Action |
| `encounter` | Random events | Attack, Defend, Talk, Flee, AI Action |
| `dialogue` | Conversations | Talk, Negotiate, Investigate, AI Action |
| `rest` | Recovery scenes | Rest, Wait, Continue |
| `exploration` | Discovery scenes | Explore, Investigate, Loot, Retreat, AI Action |
| `quest` | Quest opportunities | Accept, Investigate, Prepare, AI Action |
| `loot` | Treasure scenes | Loot, Investigate, Continue |
| `combat` | Battle scenes | Attack, Defend, Cast, Use Item, Flee |

## Actions

### Core Actions
- **Attack**: Engage in combat (+Bravery, -Energy, +Risk)
- **Defend**: Protect yourself (+Stamina, -Energy, -Risk)
- **Cast**: Use magic (+Intellect, -Energy, +Risk)
- **Talk**: Social interaction (+Charisma, -Energy)
- **Sneak**: Stealth movement (+Stamina, -Energy, -Risk)
- **Loot**: Search for items (-Energy, +Risk)
- **Flee**: Escape danger (-Energy, -Risk)
- **Wait**: Pass time (no cost)
- **Investigate**: Examine surroundings (+Intellect, -Energy)
- **AI Action**: Let AI choose optimal action

### Special Actions
- **Continue**: Progress story
- **Rest**: Recover energy
- **Explore**: Discover new areas
- **Negotiate**: Diplomatic solutions
- **Retreat**: Strategic withdrawal

## Player State

```python
@dataclass
class PlayerState:
    user_id: int
    current_scene: Optional[str]
    visited_scenes: Set[str]
    scene_cooldowns: Dict[str, int]
    risk_level: int
    energy: int
    stats: Dict[str, int]  # bravery, charisma, intellect, stamina, level
    goals: Set[str]
    step_count: int
```

## Scene Configuration

Scenes are defined in `app/game/scenes.yaml`:

```yaml
scenes:
  - id: "tavern_intro"
    kind: "story"
    weight: 1.0
    once: true
    requires: []
    blocks: []
    transitions:
      - to: "rumors_board"
        weight: 0.7
        requires: []
    risk_delta: 0
    reward:
      gold: "1d6+2"
      xp: "1d4"
```

## End Conditions

The quest loop ends when any of these conditions are met:

1. **Risk Threshold**: Player risk level reaches maximum
2. **Energy Depleted**: Player energy reaches zero
3. **Goal Reached**: Specific quest goal achieved
4. **Step Budget**: Maximum steps exceeded
5. **Quest Completed**: Specific quest finished

## Commands

| Command | Description |
|---------|-------------|
| `/quest` | Start a new quest |
| `/quest_status` | Check current quest status |
| `/end_quest` | End current quest |
| `/help_quest` | Show quest system help |

## Integration

### Main Bot Integration
The quest loop is integrated into the main bot in `app/main.py`:

```python
# Initialize services
fsm_service = FSMStateService(session)
quest_loop_service = QuestLoopService(bot, fsm_service, i18n_service)

# Store in bot context
bot["quest_loop_service"] = quest_loop_service
bot["fsm_service"] = fsm_service

# Register handlers
register_quest_handlers(dp)
```

### Database Integration
- Player state synchronized with PostgreSQL
- Session data persisted across restarts
- FSM state stored in Redis for performance

## Testing

Run the test suite to verify functionality:

```bash
python3 test_quest_loop.py
```

The test covers:
- Scene graph loading and navigation
- Action processing and consequences
- Player state management
- Scene transitions
- End condition checking

## Configuration

### Environment Variables
- `BOT_TOKEN`: Telegram bot token
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `OPENAI_API_KEY`: OpenAI API key for AI actions

### Scene Customization
Modify `app/game/scenes.yaml` to:
- Add new scenes
- Adjust transition weights
- Set scene requirements
- Configure rewards

## Future Enhancements

1. **Dynamic Scene Generation**: AI-generated scenes
2. **Multiplayer Support**: Shared quest experiences
3. **Inventory System**: Item management and usage
4. **Character Classes**: Specialized abilities
5. **Quest Chains**: Connected quest sequences
6. **Achievement System**: Progress tracking
7. **Leaderboards**: Competitive elements

## Troubleshooting

### Common Issues

1. **No Starting Scene**: Check scene requirements in YAML
2. **Action Not Available**: Verify player stats and energy
3. **Scene Not Loading**: Check scene ID and transitions
4. **State Sync Issues**: Verify database connection

### Debug Mode
Enable debug logging to trace quest flow:

```python
logger.setLevel(logging.DEBUG)
```

## Performance Considerations

- Scene graph cached in memory
- Player state synchronized asynchronously
- Redis used for FSM state storage
- Database queries optimized with indexes

## Security

- User input validation
- SQL injection prevention
- Rate limiting on actions
- Session isolation

---

The quest loop system provides a robust foundation for creating engaging, dynamic RPG experiences in Telegram. The modular design allows for easy extension and customization while maintaining performance and reliability.
