import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from app.config import Config
from app.handlers import start, game, language


def main():
    """Main function to start the bot."""
    print("🚀 Starting Fantasy RPG Adventure Bot...")
    
    # Initialize bot and dispatcher
    bot = Bot(token=Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    
    # Register routers (no middleware for now)
    dp.include_router(start.router)
    dp.include_router(game.router)
    dp.include_router(language.router)
    
    print("✅ Bot initialized successfully")
    print("📱 Bot is running in polling mode")
    print("💡 Press Ctrl+C to stop the bot")
    
    # Start polling
    try:
        asyncio.run(dp.start_polling(bot))
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
