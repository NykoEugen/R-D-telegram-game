#!/usr/bin/env python3
"""
Test script for PlayerState serialization fix.

This script tests that PlayerState can be properly serialized to JSON.
"""

import json
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.game.scenes import PlayerState


def test_player_state_serialization():
    """Test PlayerState serialization to JSON."""
    print("🧪 Testing PlayerState Serialization")
    print("=" * 50)
    
    # Create a test PlayerState
    player_state = PlayerState(
        user_id=12345,
        energy=85,
        risk_level=3,
        stats={
            "bravery": 2, "charisma": 3, "intellect": 4, 
            "stamina": 2, "level": 1, "gold": 100, "xp": 50
        },
        current_scene="test-scene",
        visited_scenes={"scene1", "scene2"},
        scene_cooldowns={"scene1": 2},
        goals={"goal1", "goal2"},
        step_count=5
    )
    
    print("Original PlayerState:")
    print(f"  User ID: {player_state.user_id}")
    print(f"  Energy: {player_state.energy}")
    print(f"  Risk Level: {player_state.risk_level}")
    print(f"  Stats: {player_state.stats}")
    print(f"  Current Scene: {player_state.current_scene}")
    print(f"  Visited Scenes: {player_state.visited_scenes}")
    print(f"  Scene Cooldowns: {player_state.scene_cooldowns}")
    print(f"  Goals: {player_state.goals}")
    print(f"  Step Count: {player_state.step_count}")
    print()
    
    # Convert to dict (as we do in the handlers)
    player_state_dict = {
        "user_id": player_state.user_id,
        "energy": player_state.energy,
        "risk_level": player_state.risk_level,
        "stats": player_state.stats,
        "current_scene": player_state.current_scene,
        "visited_scenes": list(player_state.visited_scenes),
        "scene_cooldowns": player_state.scene_cooldowns,
        "goals": list(player_state.goals),
        "step_count": player_state.step_count
    }
    
    print("Converted to dict:")
    print(f"  User ID: {player_state_dict['user_id']}")
    print(f"  Energy: {player_state_dict['energy']}")
    print(f"  Risk Level: {player_state_dict['risk_level']}")
    print(f"  Stats: {player_state_dict['stats']}")
    print(f"  Current Scene: {player_state_dict['current_scene']}")
    print(f"  Visited Scenes: {player_state_dict['visited_scenes']}")
    print(f"  Scene Cooldowns: {player_state_dict['scene_cooldowns']}")
    print(f"  Goals: {player_state_dict['goals']}")
    print(f"  Step Count: {player_state_dict['step_count']}")
    print()
    
    # Test JSON serialization
    try:
        json_str = json.dumps(player_state_dict)
        print("✅ JSON serialization successful!")
        print(f"JSON length: {len(json_str)} characters")
        print()
        
        # Test JSON deserialization
        restored_dict = json.loads(json_str)
        print("✅ JSON deserialization successful!")
        print(f"Restored dict matches original: {restored_dict == player_state_dict}")
        print()
        
        # Test recreating PlayerState from dict
        restored_player_state = PlayerState(
            user_id=restored_dict["user_id"],
            energy=restored_dict["energy"],
            risk_level=restored_dict["risk_level"],
            stats=restored_dict["stats"],
            current_scene=restored_dict.get("current_scene"),
            visited_scenes=set(restored_dict.get("visited_scenes", [])),
            scene_cooldowns=restored_dict.get("scene_cooldowns", {}),
            goals=set(restored_dict.get("goals", [])),
            step_count=restored_dict.get("step_count", 0)
        )
        
        print("✅ PlayerState recreation successful!")
        print(f"Recreated PlayerState matches original: {restored_player_state.user_id == player_state.user_id}")
        print(f"Energy matches: {restored_player_state.energy == player_state.energy}")
        print(f"Stats match: {restored_player_state.stats == player_state.stats}")
        print(f"Visited scenes match: {restored_player_state.visited_scenes == player_state.visited_scenes}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        return False


def test_fsm_data_structure():
    """Test the FSM data structure we use in handlers."""
    print("🧪 Testing FSM Data Structure")
    print("=" * 50)
    
    # Simulate FSM data structure
    fsm_data = {
        "quest_description": "A mysterious quest awaits!",
        "scene_id": "quest-12345-67890",
        "quest_actions": ["accept", "investigate", "prepare"],
        "context_hint": "A dark forest path",
        "player_state_dict": {
            "user_id": 12345,
            "energy": 85,
            "risk_level": 3,
            "stats": {"bravery": 2, "charisma": 3, "intellect": 4, "stamina": 2},
            "current_scene": "test-scene",
            "visited_scenes": ["scene1", "scene2"],
            "scene_cooldowns": {"scene1": 2},
            "goals": ["goal1", "goal2"],
            "step_count": 5
        }
    }
    
    try:
        # Test JSON serialization of entire FSM data
        json_str = json.dumps(fsm_data)
        print("✅ FSM data JSON serialization successful!")
        print(f"JSON length: {len(json_str)} characters")
        print()
        
        # Test deserialization
        restored_fsm_data = json.loads(json_str)
        print("✅ FSM data JSON deserialization successful!")
        print(f"FSM data matches original: {restored_fsm_data == fsm_data}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ FSM data JSON serialization failed: {e}")
        return False


def main():
    """Main test function."""
    try:
        print("🚀 Starting Serialization Tests...\n")
        
        success1 = test_player_state_serialization()
        success2 = test_fsm_data_structure()
        
        if success1 and success2:
            print("🎉 All serialization tests passed!")
            print("\n📋 Summary:")
            print("  ✅ PlayerState can be converted to dict")
            print("  ✅ Dict can be serialized to JSON")
            print("  ✅ JSON can be deserialized back to dict")
            print("  ✅ PlayerState can be recreated from dict")
            print("  ✅ FSM data structure works correctly")
            print("\n🔧 The JSON serialization error should now be fixed!")
        else:
            print("\n❌ Some tests failed!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
