#!/usr/bin/env python3
"""
Basic test script to verify the project structure and imports.
Run this to check if everything is set up correctly.
"""

import sys
import os

def test_imports():
    """Test if all required modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        # Test basic imports
        from app.config import Config
        print("✅ Config imported successfully")
        
        from app.services.openai_service import OpenAIService
        print("✅ OpenAI service imported successfully")
        
        from app.handlers.start import router as start_router
        print("✅ Start handler imported successfully")
        
        from app.handlers.game import router as game_router
        print("✅ Game handler imported successfully")
        
        print("\n🎉 All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_config():
    """Test configuration loading (without actual env vars)."""
    print("\n🔧 Testing configuration...")
    
    try:
        # Temporarily set required env vars
        os.environ['BOT_TOKEN'] = 'test_token'
        os.environ['OPENAI_API_KEY'] = 'test_key'
        
        from app.config import Config
        
        # Test config attributes
        assert Config.BOT_TOKEN == 'test_token'
        assert Config.OPENAI_API_KEY == 'test_key'
        assert Config.LOG_LEVEL == 'INFO'
        
        print("✅ Configuration loaded successfully")
        
        # Clean up
        del os.environ['BOT_TOKEN']
        del os.environ['OPENAI_API_KEY']
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_project_structure():
    """Test if all required files and directories exist."""
    print("\n📁 Testing project structure...")
    
    required_files = [
        'app/__init__.py',
        'app/main.py',
        'app/config.py',
        'app/handlers/__init__.py',
        'app/handlers/start.py',
        'app/handlers/game.py',
        'app/services/__init__.py',
        'app/services/openai_service.py',
        'requirements.txt',
        '.env.example',
        'README.md'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ Missing files: {len(missing_files)}")
        return False
    else:
        print(f"\n✅ All required files present: {len(required_files)}")
        return True

def main():
    """Run all tests."""
    print("🚀 Fantasy RPG Adventure Bot - Basic Tests")
    print("=" * 50)
    
    tests = [
        test_project_structure,
        test_imports,
        test_config
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The project is ready to run.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env")
        print("2. Add your BOT_TOKEN and OPENAI_API_KEY")
        print("3. Run: python app/main.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
