"""
Game FSM states for the Telegram RPG game bot.

This module defines the finite state machine states for game flow management.
"""

from aiogram.fsm.state import State, StatesGroup


class GameStates(StatesGroup):
    """Main game state group."""
    
    # Initial states
    IDLE = State()  # Player is not in any active game state
    MENU = State()  # Player is in main menu
    
    # Quest states
    QUEST_ACTIVE = State()  # Player is in an active quest
    QUEST_CHOICE = State()  # Player needs to make a quest choice
    QUEST_DIALOGUE = State()  # Player is in dialogue during quest
    
    # Combat states
    COMBAT_ACTIVE = State()  # Player is in combat
    COMBAT_CHOICE = State()  # Player needs to make combat choice
    COMBAT_RESULT = State()  # Combat result is being processed
    
    # Exploration states
    EXPLORATION = State()  # Player is exploring
    LOCATION_CHOICE = State()  # Player needs to choose location
    
    # Inventory states
    INVENTORY_OPEN = State()  # Player has inventory open
    ITEM_USE = State()  # Player is using an item
    
    # Dialogue states
    DIALOGUE_ACTIVE = State()  # Player is in dialogue
    DIALOGUE_CHOICE = State()  # Player needs to make dialogue choice
    
    # System states
    LOADING = State()  # System is loading/processing
    ERROR = State()  # Error state for recovery


class QuestStates(StatesGroup):
    """Quest-specific state group."""
    
    QUEST_START = State()  # Quest is starting
    QUEST_PROGRESS = State()  # Quest is in progress
    QUEST_COMPLETE = State()  # Quest is completed
    QUEST_FAILED = State()  # Quest has failed
    QUEST_ABANDONED = State()  # Quest was abandoned


class CombatStates(StatesGroup):
    """Combat-specific state group."""
    
    COMBAT_INIT = State()  # Combat is initializing
    COMBAT_TURN = State()  # Player's turn in combat
    COMBAT_ENEMY_TURN = State()  # Enemy's turn in combat
    COMBAT_VICTORY = State()  # Player won combat
    COMBAT_DEFEAT = State()  # Player lost combat
    COMBAT_ESCAPE = State()  # Player escaped combat


class DialogueStates(StatesGroup):
    """Dialogue-specific state group."""
    
    DIALOGUE_START = State()  # Dialogue is starting
    DIALOGUE_CONTINUE = State()  # Dialogue is continuing
    DIALOGUE_END = State()  # Dialogue has ended
    DIALOGUE_CHOICE = State()  # Player needs to make dialogue choice
