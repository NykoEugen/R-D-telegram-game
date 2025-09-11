#!/usr/bin/env python3
"""
Test script for the complete quest cycle.

This script tests the full quest lifecycle from proposal to completion,
including all quest actions and their consequences.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.game.quest_system import quest_manager, QuestType, QuestPhase
from app.game.actions import Action, ActionProcessor
from app.game.scenes import PlayerState


async def test_quest_cycle():
    """Test the complete quest cycle."""
    print("🎮 Testing Complete Quest Cycle")
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
    
    # Test quest creation
    print("📝 Creating Quest...")
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
    print(f"✅ Quest Created: {quest.id}")
    print(f"   Type: {quest.quest_type}")
    print(f"   Risk Level: {quest.risk_level}")
    print(f"   Objectives: {len(quest.objectives)}")
    print()
    
    # Start the quest
    print("🚀 Starting Quest...")
    quest = quest_manager.start_quest(12345, quest)
    print(f"✅ Quest Started")
    print(f"   Phase: {quest.phase}")
    print(f"   Started at: {quest.started_at}")
    print()
    
    # Test quest actions
    test_actions = [
        Action.SEARCH,
        Action.INVESTIGATE,
        Action.OBSERVE,
        Action.EXPLORE,
        Action.TALK,
        Action.NEGOTIATE,
        Action.COMPLETE_QUEST
    ]
    
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
    
    # Test different quest types
    print(f"\n🧪 Testing Different Quest Types...")
    quest_types = [QuestType.COMBAT, QuestType.RESCUE, QuestType.DIPLOMACY]
    
    for quest_type in quest_types:
        print(f"\n--- Testing {quest_type} Quest ---")
        
        # Create quest of this type
        quest_data["quest_type"] = quest_type.value
        quest = quest_manager.create_quest(quest_data)
        quest = quest_manager.start_quest(12346, quest)  # Different user ID
        
        print(f"✅ {quest_type} Quest Created")
        print(f"   Objectives: {len(quest.objectives)}")
        for obj in quest.objectives:
            print(f"     - {obj.description}")
        
        # Test a few actions
        test_actions_for_type = [
            Action.SEARCH,
            Action.FIGHT if quest_type == QuestType.COMBAT else Action.TALK,
            Action.COMPLETE_QUEST
        ]
        
        for action in test_actions_for_type:
            result = quest_manager.process_quest_action(12346, action, player_state)
            if "error" not in result:
                quest_progress = result["quest_progress"]
                print(f"   {action}: Phase {quest_progress['phase']}, "
                      f"Objectives {quest_progress['objectives_completed']}/{quest_progress['objectives_total']}")
                
                if result["completion_status"]["completed"]:
                    print(f"   ✅ Quest completed!")
                    break
                elif result["completion_status"]["failed"]:
                    print(f"   ❌ Quest failed!")
                    break
    
    print(f"\n🎯 Quest Cycle Test Complete!")
    print("=" * 50)


async def test_action_consequences():
    """Test action consequences in detail."""
    print("\n🔬 Testing Action Consequences")
    print("=" * 50)
    
    # Create test player state
    player_state = PlayerState(
        user_id=99999,
        energy=100,
        risk_level=0,
        stats={"bravery": 1, "charisma": 1, "intellect": 1, "stamina": 1}
    )
    
    # Test various actions
    test_actions = [
        Action.SEARCH,
        Action.HIDE,
        Action.CHARM,
        Action.INTIMIDATE,
        Action.HEAL,
        Action.MEDITATE,
        Action.CRAFT,
        Action.TRADE,
        Action.BEFRIEND,
        Action.SABOTAGE,
        Action.INFILTRATE,
        Action.NEGOTIATE_PEACE,
        Action.DECEIVE,
        Action.INSPIRE,
        Action.LEAD,
        Action.FOLLOW,
        Action.OBSERVE,
        Action.LEARN,
        Action.TEACH,
        Action.PROTECT,
        Action.SACRIFICE,
        Action.ESCAPE,
        Action.PURSUE,
        Action.AMBUSH,
        Action.SURRENDER,
        Action.CHALLENGE,
        Action.ACCEPT_CHALLENGE,
        Action.DECLINE_CHALLENGE
    ]
    
    print(f"Testing {len(test_actions)} different actions...")
    print()
    
    for action in test_actions:
        # Reset player state
        player_state.energy = 100
        player_state.risk_level = 0
        player_state.stats = {"bravery": 1, "charisma": 1, "intellect": 1, "stamina": 1}
        
        # Process action
        scene_context = {"scene_type": "quest", "risk_level": 1}
        consequence = ActionProcessor.process_action(action, player_state, scene_context)
        action_result = ActionProcessor.apply_consequence(consequence, player_state)
        
        print(f"🎯 {action}:")
        print(f"   Energy Cost: {consequence.energy_cost}")
        print(f"   Risk Change: {consequence.risk_change}")
        print(f"   Stat Changes: {consequence.stat_changes}")
        print(f"   Success Rate: {consequence.success_probability:.1%}")
        print(f"   Result: {action_result['message']}")
        print(f"   Final Energy: {player_state.energy}/100")
        print(f"   Final Risk: {player_state.risk_level}")
        print()


if __name__ == "__main__":
    print("🚀 Starting Quest System Tests...")
    
    # Run the tests
    asyncio.run(test_quest_cycle())
    asyncio.run(test_action_consequences())
    
    print("\n✅ All tests completed!")
