#!/usr/bin/env python3
"""
Test script for the dynamic scene graph system.

This script tests the core functionality of the scene graph manager.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.game.scenes import SceneGraphManager, PlayerState
from app.game.actions import Action, ActionProcessor, get_available_actions


def test_scene_graph():
    """Test the scene graph system."""
    print("🧪 Testing Scene Graph System")
    print("=" * 50)
    
    # Initialize scene graph manager
    scene_graph = SceneGraphManager()
    
    if not scene_graph.scenes:
        print("❌ No scenes loaded!")
        return False
    
    print(f"✅ Loaded {len(scene_graph.scenes)} scenes")
    print(f"✅ Loaded {len(scene_graph.end_conditions)} end conditions")
    
    # Create a test player state
    player_state = PlayerState(
        user_id=12345,
        energy=100,
        risk_level=0,
        stats={
            "bravery": 2, "charisma": 1, "intellect": 3, 
            "stamina": 2, "level": 1, "gold": 0, "xp": 0
        }
    )
    
    print(f"\n👤 Player State:")
    print(f"   Energy: {player_state.energy}")
    print(f"   Risk Level: {player_state.risk_level}")
    print(f"   Stats: {player_state.stats}")
    
    # Test getting starting scene
    starting_scene = scene_graph.get_next_scene(player_state)
    if starting_scene:
        print(f"\n🎬 Starting Scene: {starting_scene.id}")
        print(f"   Type: {starting_scene.kind}")
        print(f"   Weight: {starting_scene.weight}")
        print(f"   Risk Delta: {starting_scene.risk_delta}")
        
        # Apply scene consequences
        scene_graph.apply_scene_consequences(starting_scene, player_state)
        player_state.current_scene = starting_scene.id
        
        print(f"\n📊 After Scene:")
        print(f"   Energy: {player_state.energy}")
        print(f"   Risk Level: {player_state.risk_level}")
        print(f"   Visited Scenes: {player_state.visited_scenes}")
        print(f"   Step Count: {player_state.step_count}")
        
        # Test available actions
        available_actions = get_available_actions(starting_scene.kind.value, player_state)
        print(f"\n🎯 Available Actions: {[action.value for action in available_actions]}")
        
        # Test action processing
        if available_actions:
            test_action = available_actions[0]
            print(f"\n⚔️ Testing Action: {test_action.value}")
            
            scene_context = {
                "scene_type": starting_scene.kind.value,
                "scene_id": starting_scene.id,
                "risk_level": player_state.risk_level
            }
            
            consequence = ActionProcessor.process_action(test_action, player_state, scene_context)
            print(f"   Energy Cost: {consequence.energy_cost}")
            print(f"   Risk Change: {consequence.risk_change}")
            print(f"   Success Probability: {consequence.success_probability}")
            
            # Apply consequence
            result = ActionProcessor.apply_consequence(consequence, player_state)
            print(f"   Result: {result['message']}")
            print(f"   Success: {result['success']}")
            
            print(f"\n📊 After Action:")
            print(f"   Energy: {player_state.energy}")
            print(f"   Risk Level: {player_state.risk_level}")
            print(f"   Stats: {player_state.stats}")
        
        # Test getting next scene
        next_scene = scene_graph.get_next_scene(player_state, starting_scene.id)
        if next_scene:
            print(f"\n➡️ Next Scene: {next_scene.id}")
            print(f"   Type: {next_scene.kind}")
        else:
            print(f"\n❌ No next scene available")
        
        # Test end conditions
        end_reason = scene_graph.check_end_conditions(player_state)
        if end_reason:
            print(f"\n🏁 Adventure would end: {end_reason}")
        else:
            print(f"\n✅ Adventure continues")
    
    else:
        print("❌ No starting scene available!")
        return False
    
    print(f"\n🎉 Scene Graph Test Completed Successfully!")
    return True


def test_scene_requirements():
    """Test scene requirement checking."""
    print(f"\n🔍 Testing Scene Requirements")
    print("=" * 30)
    
    scene_graph = SceneGraphManager()
    
    # Test player with different stats
    high_stat_player = PlayerState(
        user_id=12345,
        stats={"bravery": 5, "charisma": 3, "intellect": 4, "stamina": 2, "level": 3}
    )
    
    low_stat_player = PlayerState(
        user_id=12346,
        stats={"bravery": 1, "charisma": 1, "intellect": 1, "stamina": 1, "level": 1}
    )
    
    # Test forest_encounter scene (requires bravery>=2)
    forest_scene = scene_graph.scenes.get("forest_encounter")
    if forest_scene:
        high_available = scene_graph._check_scene_availability(forest_scene, high_stat_player)
        low_available = scene_graph._check_scene_availability(forest_scene, low_stat_player)
        
        print(f"Forest Encounter (requires bravery>=2):")
        print(f"   High stat player (bravery=5): {high_available}")
        print(f"   Low stat player (bravery=1): {low_available}")
    
    # Test tavern_intro scene (no requirements)
    tavern_scene = scene_graph.scenes.get("tavern_intro")
    if tavern_scene:
        high_available = scene_graph._check_scene_availability(tavern_scene, high_stat_player)
        low_available = scene_graph._check_scene_availability(tavern_scene, low_stat_player)
        
        print(f"Tavern Intro (no requirements):")
        print(f"   High stat player: {high_available}")
        print(f"   Low stat player: {low_available}")


if __name__ == "__main__":
    print("🚀 Starting Scene Graph Tests")
    print("=" * 60)
    
    try:
        success = test_scene_graph()
        test_scene_requirements()
        
        if success:
            print(f"\n✅ All tests passed!")
        else:
            print(f"\n❌ Some tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
