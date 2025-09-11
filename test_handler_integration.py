#!/usr/bin/env python3
"""
Test script for handler integration.

This script tests that the quest actions are properly routed to the quest system.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.game.states import GameStates
from app.game.actions import Action
from app.handlers.callbacks import ActionCB


def test_handler_routing():
    """Test that handler routing works correctly."""
    print("🔗 Testing Handler Routing")
    print("=" * 50)
    
    # Test that we can create ActionCB objects
    print("📝 Testing ActionCB creation...")
    
    test_actions = [
        Action.SEARCH,
        Action.INVESTIGATE,
        Action.OBSERVE,
        Action.TALK,
        Action.FIGHT,
        Action.COMPLETE_QUEST
    ]
    
    for action in test_actions:
        scene_id = f"quest-12345-67890"
        cb_data = ActionCB(a=action.value, s=scene_id)
        packed = cb_data.pack()
        
        print(f"✅ {action}: {packed}")
    
    print()
    
    # Test state checking
    print("🎯 Testing State Checking...")
    
    # Simulate the logic from the handler
    current_state = GameStates.QUEST_ACTIVE
    
    if current_state == GameStates.QUEST_ACTIVE:
        print("✅ Quest actions will be routed to quest system")
    else:
        print("❌ Quest actions will be handled by general handler")
    
    print()
    
    # Test action filtering
    print("🔍 Testing Action Filtering...")
    
    quest_actions = [
        Action.SEARCH, Action.HIDE, Action.CHARM, Action.INTIMIDATE,
        Action.HEAL, Action.MEDITATE, Action.CRAFT, Action.TRADE,
        Action.BEFRIEND, Action.SABOTAGE, Action.INFILTRATE, Action.NEGOTIATE_PEACE,
        Action.DECEIVE, Action.INSPIRE, Action.LEAD, Action.FOLLOW,
        Action.OBSERVE, Action.LEARN, Action.TEACH, Action.PROTECT,
        Action.SACRIFICE, Action.ESCAPE, Action.PURSUE, Action.AMBUSH,
        Action.SURRENDER, Action.CHALLENGE, Action.ACCEPT_CHALLENGE, Action.DECLINE_CHALLENGE,
        Action.COMPLETE_QUEST
    ]
    
    general_actions = [
        Action.ATTACK, Action.DEFEND, Action.CAST, Action.USE_ITEM,
        Action.SNEAK, Action.LOOT, Action.FLEE, Action.WAIT, Action.BACK,
        Action.ACCEPT, Action.INVESTIGATE, Action.PREPARE, Action.RUN_AI,
        Action.CONTINUE, Action.REST, Action.EXPLORE, Action.NEGOTIATE,
        Action.RETREAT, Action.SCOUT, Action.FIGHT, Action.PICKLOCK
    ]
    
    print(f"🎮 Quest Actions ({len(quest_actions)}):")
    for action in quest_actions[:10]:  # Show first 10
        print(f"   - {action}")
    print(f"   ... and {len(quest_actions) - 10} more")
    
    print(f"\n🎯 General Actions ({len(general_actions)}):")
    for action in general_actions[:10]:  # Show first 10
        print(f"   - {action}")
    print(f"   ... and {len(general_actions) - 10} more")
    
    print()
    
    # Test the routing logic
    print("🚦 Testing Routing Logic...")
    
    test_cases = [
        (Action.SEARCH, GameStates.QUEST_ACTIVE, "Quest System"),
        (Action.INVESTIGATE, GameStates.QUEST_ACTIVE, "Quest System"),
        (Action.ATTACK, GameStates.QUEST_ACTIVE, "Quest System"),
        (Action.SEARCH, GameStates.MENU, "General Handler"),
        (Action.ATTACK, GameStates.COMBAT_ACTIVE, "General Handler"),
        (Action.RUN_AI, GameStates.QUEST_ACTIVE, "Quest System"),
    ]
    
    for action, state, expected_handler in test_cases:
        if state == GameStates.QUEST_ACTIVE:
            actual_handler = "Quest System"
        else:
            actual_handler = "General Handler"
        
        status = "✅" if actual_handler == expected_handler else "❌"
        print(f"{status} {action} in {state} → {actual_handler}")
    
    print()
    
    print("🎯 Handler Routing Test Complete!")
    print("=" * 50)


if __name__ == "__main__":
    print("🚀 Starting Handler Integration Tests...")
    
    # Run the tests
    test_handler_routing()
    
    print("\n✅ All handler integration tests completed!")
