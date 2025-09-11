# Виправлення Обробника Квестових Дій

## Проблема

Коли гравець виконував дії під час квесту (наприклад, `investigate`), система показувала загальне повідомлення:

```
🎮 Action Executed

Action: investigate
Result: Action completed successfully!

📊 Effects:
• Energy: 84/100
• Risk Level: 0
• Stats: {'bravery': 1, 'charisma': 1, 'intellect': 3, 'stamina': 1, 'level': 1, 'gold': 0, 'xp': 0}

Scene: quest-385833312-280
State: GameStates:QUEST_ACTIVE → GameStates:DIALOGUE_CHOICE

Action processed and logged!
```

Замість того, щоб показувати прогрес квесту та наступну сцену.

## Причина

Старий обробник `on_action_press` в `app/handlers/commands/game.py` обробляв всі дії, включаючи дії під час квесту, замість того, щоб передавати їх до нової квестової системи.

## Рішення

### 1. Додано перевірку стану в основний обробник

В `app/handlers/commands/game.py` додано перевірку стану:

```python
@router.callback_query(ActionCB.filter())
async def on_action_press(cb: CallbackQuery, callback_data: ActionCB, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle action button presses with real game effects."""
    try:
        user_id = cb.from_user.id
        action = callback_data.a
        scene_id = callback_data.s
        
        # Get current FSM state and data
        current_state = await state.get_state()
        fsm_data = await state.get_data()
        
        # If we're in QUEST_ACTIVE state, let the quest system handle it
        if current_state == GameStates.QUEST_ACTIVE:
            # Import here to avoid circular import
            from app.handlers.quest_proposal import handle_quest_action
            await handle_quest_action(cb, callback_data, state, db_session, fsm_service)
            return
        
        # ... rest of the general handler logic
```

### 2. Рефакторинг обробника квестових дій

В `app/handlers/quest_proposal.py` змінено структуру:

```python
@router.callback_query(ActionCB.filter(), GameStates.QUEST_ACTIVE)
async def handle_quest_action_callback(cb: CallbackQuery, callback_data: ActionCB, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle quest action callbacks."""
    await handle_quest_action(cb, callback_data, state, db_session, fsm_service)


async def handle_quest_action(cb: CallbackQuery, callback_data: ActionCB, state: FSMContext, db_session: AsyncSession, fsm_service: FSMStateService):
    """Handle action button presses during active quest."""
    # ... quest action handling logic
```

## Результат

Тепер коли гравець виконує дії під час квесту, система:

1. **Перевіряє стан** - якщо `GameStates.QUEST_ACTIVE`, передає до квестової системи
2. **Обробляє дію** - використовує `QuestManager` для обробки дії
3. **Генерує сцену** - створює нову сцену на основі дії та прогресу квесту
4. **Показує прогрес** - відображає поточну фазу квесту, виконані цілі та доступні дії
5. **Оновлює інтерфейс** - показує нові кнопки дій для наступного кроку

### Приклад нового повідомлення:

```
📜 Quest Progress

Ви розслідуєте обставини...

⚡ Energy: 84/100
📊 Stats: Bravery: 1, Charisma: 1, Intellect: 3, Stamina: 1

🎯 Quest Phase: confrontation
📋 Objectives: 2/3
⚡ Actions Taken: 4

🎯 What will you do?

[🔍 Шукати] [👀 Спостерігати] [💫 Зачарувати] [😠 Залякати]
[💚 Лікувати] [🧘 Медитувати] [🔨 Створити] [💰 Торгувати]
```

## Тестування

Створено тести для перевірки:

1. **`test_quest_integration.py`** - тестує квестову систему
2. **`test_handler_integration.py`** - тестує маршрутизацію обробників

### Результати тестування:

```
✅ Quest actions will be routed to quest system
✅ search in GameStates:QUEST_ACTIVE → Quest System
✅ investigate in GameStates:QUEST_ACTIVE → Quest System
✅ attack in GameStates:QUEST_ACTIVE → Quest System
```

## Архітектура

### Маршрутизація дій:

```
Action Button Press
        ↓
on_action_press (game.py)
        ↓
Check FSM State
        ↓
┌─────────────────┬─────────────────┐
│ QUEST_ACTIVE    │ Other States    │
│ ↓               │ ↓               │
│ Quest System    │ General Handler │
│ (quest_proposal)│ (game.py)       │
└─────────────────┴─────────────────┘
```

### Стани та обробники:

- **`GameStates.QUEST_ACTIVE`** → `handle_quest_action` (quest_proposal.py)
- **`GameStates.COMBAT_ACTIVE`** → `on_action_press` (game.py)
- **`GameStates.MENU`** → `on_action_press` (game.py)
- **Інші стани** → `on_action_press` (game.py)

## Переваги

1. **Правильна маршрутизація** - дії під час квесту обробляються квестовою системою
2. **Збереження функціональності** - загальні дії продовжують працювати як раніше
3. **Модульність** - квестова система залишається окремим модулем
4. **Розширюваність** - легко додати нові стани та обробники

## Майбутні покращення

1. **Додати більше станів** - для різних типів активності
2. **Покращити маршрутизацію** - використовувати middleware
3. **Додати логування** - для відстеження маршрутизації
4. **Оптимізувати імпорти** - уникнути circular imports

## Висновок

Проблема з обробкою квестових дій успішно вирішена. Тепер система правильно маршрутизує дії до відповідних обробників, забезпечуючи правильний ігровий досвід для гравців.
