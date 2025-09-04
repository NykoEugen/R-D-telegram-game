# FSM State Management Integration

This document describes the implementation of FSM (Finite State Machine) state management with PostgreSQL persistence in the Telegram RPG game bot.

## 🎯 Overview

The bot now uses FSMContext to store temporary state and automatically syncs FSM data to PostgreSQL GameSession.current_state after each significant action. On reconnect/restart, FSM state is restored from PostgreSQL snapshots.

## 🏗️ Architecture

### 1. FSM States (`app/game/states.py`)

Defined comprehensive state groups for different game scenarios:

- **GameStates**: Main game flow states (IDLE, MENU, QUEST_ACTIVE, COMBAT_ACTIVE, etc.)
- **QuestStates**: Quest-specific states (QUEST_START, QUEST_PROGRESS, QUEST_COMPLETE, etc.)
- **CombatStates**: Combat-specific states (COMBAT_INIT, COMBAT_TURN, COMBAT_VICTORY, etc.)
- **DialogueStates**: Dialogue-specific states (DIALOGUE_START, DIALOGUE_CONTINUE, etc.)

### 2. FSM Service (`app/services/fsm_service.py`)

Core service for managing FSM state synchronization:

- **sync_fsm_to_postgres()**: Syncs FSM state and data to PostgreSQL after actions
- **restore_fsm_from_postgres()**: Restores FSM state from PostgreSQL on reconnect
- **create_or_get_session()**: Creates new sessions or retrieves existing ones
- **end_session()**: Properly ends game sessions
- **get_session_state()**: Retrieves current session state information

### 3. Database Middleware (`app/middlewares/database.py`)

Middleware that automatically:
- Provides database session to handlers
- Restores FSM state from PostgreSQL on each request
- Syncs FSM state to PostgreSQL after successful request processing

### 4. Updated GameSession Model

Added `current_state` field to store the current FSM state:
```python
current_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
```

## 🔄 State Flow

### 1. User Interaction Flow

```
User Action → Handler → FSM State Update → PostgreSQL Sync → Response
```

### 2. Reconnect/Restart Flow

```
Bot Restart → Middleware → FSM State Restoration → Continue Game
```

### 3. State Transitions

- **/start** → `GameStates.MENU`
- **/quest** → `GameStates.QUEST_ACTIVE`
- **Action buttons** → State changes based on action type
- **/status** → Shows current FSM state and session info

## 📊 Database Schema

### GameSession Table Updates

```sql
ALTER TABLE game_sessions ADD COLUMN current_state VARCHAR(100);
```

### Session Data Structure

```json
{
  "quest_description": "AI-generated quest text",
  "scene_id": "quest-12345-67890",
  "action_count": 5,
  "last_action": "attack",
  "last_scene_id": "combat_scene",
  "last_sync": "2024-01-01T12:00:00Z"
}
```

## 🛠️ Implementation Details

### 1. Handler Updates

All game handlers now:
- Accept `FSMContext`, `AsyncSession`, and `FSMStateService` parameters
- Set appropriate FSM states
- Store relevant data in FSM context
- Sync state to PostgreSQL after significant actions

### 2. Middleware Integration

The `DatabaseMiddleware` is registered for both message and callback query handlers:
```python
dp.message.middleware(DatabaseMiddleware())
dp.callback_query.middleware(DatabaseMiddleware())
```

### 3. State Synchronization

FSM state is synced to PostgreSQL:
- After each command execution
- After each action button press
- With action metadata and scene information
- With automatic session management

## 🧪 Testing

### Test Script (`test_fsm_integration.py`)

Comprehensive test suite that verifies:
1. Session creation
2. FSM state synchronization
3. FSM state restoration
4. Session state retrieval
5. Session ending

Run tests with:
```bash
python test_fsm_integration.py
```

## 📈 Benefits

### 1. State Persistence
- Game state survives bot restarts
- Users can continue where they left off
- No loss of progress during maintenance

### 2. Scalability
- Multiple bot instances can share state
- Horizontal scaling support
- Centralized state management

### 3. Debugging
- Complete state history in database
- Action tracking and analytics
- Session monitoring capabilities

### 4. User Experience
- Seamless reconnection
- Consistent game flow
- Reliable state management

## 🔧 Configuration

### Environment Variables

No additional environment variables required. Uses existing database configuration.

### Database Migration

Run the migration to add the `current_state` field:
```bash
alembic upgrade head
```

## 🚀 Usage Examples

### 1. Starting a Quest

```python
@router.message(Command("quest"))
async def cmd_quest(message: Message, state: FSMContext, fsm_service: FSMStateService):
    await state.set_state(GameStates.QUEST_ACTIVE)
    await state.update_data(quest_description="...")
    await fsm_service.sync_fsm_to_postgres(state, user_id, action="quest_start")
```

### 2. Action Button Handling

```python
@router.callback_query(ActionCB.filter())
async def on_action_press(cb: CallbackQuery, state: FSMContext, fsm_service: FSMStateService):
    await state.set_state(GameStates.COMBAT_CHOICE)
    await fsm_service.sync_fsm_to_postgres(state, user_id, action="attack")
```

### 3. State Restoration

```python
# Automatically handled by DatabaseMiddleware
async def restore_fsm_from_postgres(fsm_context, user_id):
    game_session = await fsm_service.restore_fsm_from_postgres(fsm_context, user_id)
    if game_session:
        await fsm_context.set_state(game_session.current_state)
```

## 🔍 Monitoring

### Logging

All FSM operations are logged with:
- User ID and session information
- State transitions
- Action tracking
- Error handling

### Database Queries

Monitor FSM state with:
```sql
SELECT session_id, current_state, session_data, actions_count 
FROM game_sessions 
WHERE status = 'active';
```

## 🎯 Future Enhancements

1. **State Analytics**: Track user behavior patterns
2. **State Validation**: Ensure state consistency
3. **State Compression**: Optimize storage for large sessions
4. **State Migration**: Handle state schema changes
5. **State Cleanup**: Automatic cleanup of old sessions

## 📝 Notes

- FSM state is automatically restored on every request
- State synchronization happens after successful handler execution
- Failed operations don't affect FSM state
- Session data is stored as JSON for flexibility
- All operations are logged for debugging and monitoring
