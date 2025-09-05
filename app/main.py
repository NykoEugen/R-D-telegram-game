import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from app.core.config import Config
from app.core.redis import init_redis, close_redis, get_redis
from app.handlers.commands import start_router, game_router, language_router
from app.handlers.game import router as adventure_router
from app.handlers.errors import setup_error_handlers, GlobalErrorHandler
from app.middlewares.correlation import CorrelationMiddleware
from app.middlewares.database import DatabaseMiddleware
from app.services.logging_service import setup_logging, get_logger
from app.services.i18n_service import i18n_service


async def main():
    """Main function to start the bot."""
    # Setup logging first
    setup_logging(
        log_level=Config.LOG_LEVEL,
        log_file="logs/bot.log",
        enable_console=True
    )
    
    logger = get_logger(__name__)
    logger.info("🚀 Starting Fantasy RPG Adventure Bot...")
    
    # Initialize Redis connection
    logger.info("🔗 Initializing Redis connection...")
    await init_redis()
    logger.info("✅ Redis connection initialized")
    
    # Create Redis storage for FSM
    redis_client = get_redis()
    storage = RedisStorage(redis=redis_client)
    logger.info("📦 Redis FSM storage configured")
    
    # Initialize bot and dispatcher with Redis storage
    bot = Bot(token=Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=storage)
    
    # Add middlewares
    dp.message.middleware(GlobalErrorHandler())
    dp.callback_query.middleware(GlobalErrorHandler())
    dp.message.middleware(CorrelationMiddleware())
    dp.callback_query.middleware(CorrelationMiddleware())
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    
    # Initialize i18n service (no middleware needed)
    logger.info("i18n service initialized", supported_languages=i18n_service.supported_languages)
    
    # Setup error handlers
    setup_error_handlers(dp)
    
    # Register routers
    dp.include_router(start_router)
    dp.include_router(game_router)
    dp.include_router(language_router)
    dp.include_router(adventure_router)
    
    logger.info("✅ Bot initialized successfully")
    logger.info("📱 Bot is running in polling mode")
    logger.info("💡 Press Ctrl+C to stop the bot")
    
    # Start polling
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error("❌ Fatal error occurred", error_type=type(e).__name__, error_message=str(e))
        raise
    finally:
        # Cleanup Redis connection
        logger.info("🧹 Cleaning up Redis connection...")
        await close_redis()
        logger.info("✅ Redis connection closed")

if __name__ == "__main__":
    asyncio.run(main())
