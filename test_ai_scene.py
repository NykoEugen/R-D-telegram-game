#!/usr/bin/env python3
"""
Test script for AI Scene Generation System.

This script tests the AI scene generation with controlled choice mapping.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ai.scene_generation_service import AISceneGenerationService
from app.game.actions import Action


async def test_ai_scene_generation():
    """Test AI scene generation and choice mapping."""
    print("🤖 Testing AI Scene Generation System")
    print("=" * 50)
    
    # Test scene generation
    print("\n1. Generating AI Scene...")
    ai_scene = await AISceneGenerationService.generate_scene("en")
    
    if not ai_scene:
        print("❌ Failed to generate AI scene")
        return False
    
    print(f"✅ Generated scene: {ai_scene.description[:100]}...")
    print(f"✅ Scene type: {ai_scene.scene_type}")
    print(f"✅ Number of choices: {len(ai_scene.choices)}")
    
    # Test choice mapping
    print("\n2. Testing Choice Mapping...")
    for i, (choice_text, action) in enumerate(ai_scene.choices, 1):
        print(f"   Choice {i}: '{choice_text}' -> {action}")
    
    # Test available actions
    print("\n3. Available Actions:")
    available_actions = AISceneGenerationService.get_available_actions()
    for action in available_actions:
        print(f"   - {action}")
    
    # Test choice mapping keywords
    print("\n4. Testing Choice Mapping Keywords:")
    test_choices = [
        "Scout the area",
        "Fight the enemy", 
        "Retreat safely",
        "Talk to the guard",
        "Pick the lock"
    ]
    
    for choice in test_choices:
        mapped_action = None
        choice_lower = choice.lower()
        
        for keyword, action in AISceneGenerationService.CHOICE_MAPPING.items():
            if keyword in choice_lower:
                mapped_action = action
                break
        
        print(f"   '{choice}' -> {mapped_action}")
    
    print("\n✅ AI Scene Generation System Test Complete!")
    return True


async def main():
    """Main test function."""
    try:
        success = await test_ai_scene_generation()
        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
