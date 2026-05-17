#!/usr/bin/env python3
"""
Simple startup script for the Fantasy RPG Adventure Bot.
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv


def check_environment():
    print("🔍 Checking environment...")
    required_vars = ['BOT_TOKEN']
    missing_vars = [v for v in required_vars if not os.getenv(v)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\n📝 Please create a .env file with:\nBOT_TOKEN=your_telegram_bot_token_here")
        return False
    print("✅ Environment variables are set")
    return True


def check_dependencies():
    print("\n📦 Checking dependencies...")
    try:
        import aiogram
        print(f"✅ aiogram {aiogram.__version__}")
    except ImportError:
        print("❌ aiogram not installed. Run: pip install -r requirements.txt")
        return False
    try:
        import dotenv
        print("✅ python-dotenv")
    except ImportError:
        print("❌ python-dotenv not installed. Run: pip install -r requirements.txt")
        return False
    return True


def main():
    print("🎮 Fantasy RPG Adventure Bot - Startup Check")
    print("=" * 50)

    load_dotenv()

    if not check_environment():
        return

    if not check_dependencies():
        print("\n💡 Please install missing dependencies first.")
        return

    print("\n✅ All checks passed!")
    print("\n🚀 Starting the bot...")
    print("💡 Press Ctrl+C to stop the bot")

    try:
        from app.main import main as bot_main
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting bot: {e}")


if __name__ == "__main__":
    main()
