#!/usr/bin/env python3
"""
Simple startup script for the Fantasy RPG Adventure Bot.
This script provides clear instructions and handles common setup issues.
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if required environment variables are set."""
    print("🔍 Checking environment...")
    
    required_vars = ['BOT_TOKEN', 'OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\n📝 Please create a .env file with the following content:")
        print("BOT_TOKEN=your_telegram_bot_token_here")
        print("OPENAI_API_KEY=your_openai_api_key_here")
        print("OPENAI_MODEL=gpt-3.5-turbo  # Optional, defaults to gpt-3.5-turbo")
        print("NGROK_URL=https://your-ngrok-url.ngrok.io  # Optional for webhook mode")
        print("PORT=8000  # Optional, defaults to 8000")
        print("WEBHOOK_SECRET=your_secret_here  # Optional for webhook security")
        print("\n💡 You can copy from .env.example and fill in your actual values.")
        return False
    
    print("✅ Environment variables are set")
    return True

def check_dependencies():
    """Check if required Python packages are installed."""
    print("\n📦 Checking dependencies...")
    
    try:
        import aiogram
        print(f"✅ aiogram {aiogram.__version__}")
    except ImportError:
        print("❌ aiogram not installed. Run: pip install -r requirements.txt")
        return False
    
    try:
        import openai
        print("✅ openai")
    except ImportError:
        print("❌ openai not installed. Run: pip install -r requirements.txt")
        return False
    
    try:
        import dotenv
        print("✅ python-dotenv")
    except ImportError:
        print("❌ python-dotenv not installed. Run: pip install -r requirements.txt")
        return False
    
    return True

def show_instructions():
    """Show setup and usage instructions."""
    print("\n" + "="*60)
    print("🎮 FANTASY RPG ADVENTURE BOT - SETUP INSTRUCTIONS")
    print("="*60)
    
    print("\n📋 PREREQUISITES:")
    print("1. Python 3.8+ installed")
    print("2. Telegram Bot Token (from @BotFather)")
    print("3. OpenAI API Key (from OpenAI Platform)")
    print("4. ngrok (optional, for webhook testing)")
    
    print("\n🚀 QUICK START:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Copy .env.example to .env")
    print("3. Edit .env with your actual tokens")
    print("4. Run: python app/main.py")
    
    print("\n🔧 MODES:")
    print("• Polling Mode (default): Just run the bot")
    print("• Webhook Mode: Set NGROK_URL in .env and run ngrok http <PORT> (default: 8000)")
    
    print("\n📱 TESTING:")
    print("1. Start the bot")
    print("2. Send /start to your bot on Telegram")
    print("3. Use /quest to get AI-generated quests")
    print("4. Use /help for more commands")
    
    print("\n📚 DOCUMENTATION:")
    print("• README.md - Complete setup guide")
    print("• .env.example - Environment variables template")
    print("• test_basic.py - Basic functionality test")

def main():
    """Main function."""
    print("🎮 Fantasy RPG Adventure Bot - Startup Check")
    print("="*50)
    
    # Check if .env file exists
    if not Path(".env").exists():
        print("❌ .env file not found!")
        print("💡 Please copy .env.example to .env and fill in your values.")
        print()
        show_instructions()
        return
    
    # Check environment variables
    if not check_environment():
        print()
        show_instructions()
        return
    
    # Check dependencies
    if not check_dependencies():
        print("\n💡 Please install missing dependencies first.")
        return
    
    print("\n✅ All checks passed!")
    print("\n🚀 Starting the bot...")
    print("💡 Press Ctrl+C to stop the bot")
    
    try:
        # Import and run the main bot
        from app.main import main as bot_main
        bot_main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting bot: {e}")
        print("\n💡 Check your configuration and try again")

if __name__ == "__main__":
    main()
