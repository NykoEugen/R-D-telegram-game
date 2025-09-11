#!/usr/bin/env python3
"""
Test script for quest system integration.

This script tests the integration between the quest system and the handlers.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.game.quest_system import quest_manager, QuestType
from app.game.actions import Action
from app.game.scenes import PlayerState
from app.game.states import GameStates


async def test_quest_integration():
    """Test quest system integration."""
    print("🔗 Testing Quest System Integration")
    print("=" * 50)
    
    # Create a test player state
    player_state = PlayerState(
        user_id=12345,
        energy=100,
        risk_level=0,
        stats={
            "bravery": 1,
            "charisma": 1,
            "intellect": 1,
            "stamina": 1,
            "level": 1,
            "gold": 0,
            "xp": 0
        }
    )
    
    print(f"👤 Initial Player State:")
    print(f"   Energy: {player_state.energy}/100")
    print(f"   Risk Level: {player_state.risk_level}")
    print(f"   Stats: {player_state.stats}")
    print()
    
    # Test quest creation and start
    print("📝 Creating and Starting Quest...")
    quest_data = {
        "user_id": 12345,
        "questgiver_name": "Сивий маг",
        "quest_intro": "Слухай, воїн! Потрібна твоя допомога.",
        "quest_description": "Розслідувати дивні звуки в стародавніх руїнах",
        "quest_type": "investigation",
        "risk_level": 3,
        "reward_gold": 100,
        "reward_xp": 50,
        "faction": "Маги Ордену",
        "additional_info": "Кажуть, там лежать стародавні скарби."
    }
    
    quest = quest_manager.create_quest(quest_data)
    quest = quest_manager.start_quest(12345, quest)
    
    print(f"✅ Quest Created and Started: {quest.id}")
    print(f"   Phase: {quest.phase}")
    print(f"   Objectives: {len(quest.objectives)}")
    print()
    
    # Test a few actions to see the progression
    test_actions = [Action.SEARCH, Action.INVESTIGATE, Action.OBSERVE, Action.TALK]
    
    print("⚔️ Testing Quest Actions...")
    for i, action in enumerate(test_actions, 1):
        print(f"\n--- Action {i}: {action} ---")
        
        # Process the action
        result = quest_manager.process_quest_action(12345, action, player_state)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            break
        
        # Display results
        action_result = result["action_result"]
        quest_progress = result["quest_progress"]
        next_scene = result["next_scene"]
        
        print(f"🎯 Action Result: {action_result['message']}")
        print(f"⚡ Energy Change: {action_result['energy_change']}")
        print(f"📊 Stat Changes: {action_result['stat_changes']}")
        print(f"🎭 Next Scene: {next_scene['description']}")
        print(f"📈 Quest Progress:")
        print(f"   Phase: {quest_progress['phase']}")
        print(f"   Objectives: {quest_progress['objectives_completed']}/{quest_progress['objectives_total']}")
        print(f"   Actions Taken: {quest_progress['actions_taken']}")
        print(f"   Completion Ratio: {quest_progress['completion_ratio']:.1%}")
        
        # Check for completion
        completion_status = result["completion_status"]
        if completion_status["completed"]:
            print(f"\n🎉 QUEST COMPLETED!")
            completion_data = result["quest_completion"]
            print(f"   Quest ID: {completion_data['quest_id']}")
            print(f"   Questgiver: {completion_data['questgiver']}")
            print(f"   Rewards:")
            print(f"     Gold: {completion_data['rewards']['gold']}")
            print(f"     XP: {completion_data['rewards']['xp']}")
            print(f"     Gold Bonus: {completion_data['rewards']['gold_bonus']}")
            print(f"     XP Bonus: {completion_data['rewards']['xp_bonus']}")
            print(f"   Efficiency: {completion_data['efficiency']['actions_taken']} actions")
            break
        elif completion_status["failed"]:
            print(f"\n💀 QUEST FAILED!")
            failure_data = result["quest_failure"]
            print(f"   Reason: {failure_data['failure_reason']}")
            break
        
        # Update player state display
        print(f"👤 Updated Player State:")
        print(f"   Energy: {player_state.energy}/100")
        print(f"   Risk Level: {player_state.risk_level}")
        print(f"   Stats: {player_state.stats}")
    
    print(f"\n🏁 Final Player State:")
    print(f"   Energy: {player_state.energy}/100")
    print(f"   Risk Level: {player_state.risk_level}")
    print(f"   Stats: {player_state.stats}")
    print(f"   Gold: {player_state.stats.get('gold', 0)}")
    print(f"   XP: {player_state.stats.get('xp', 0)}")
    
    print(f"\n🎯 Quest Integration Test Complete!")
    print("=" * 50)


if __name__ == "__main__":
    print("🚀 Starting Quest Integration Tests...")
    
    # Run the tests
    asyncio.run(test_quest_integration())
    
    print("\n✅ All integration tests completed!")
