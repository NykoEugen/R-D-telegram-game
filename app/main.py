import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from app.config import Config
from app.handlers import start, game, language
from app.handlers.errors import setup_error_handlers, GlobalErrorHandler
from app.middlewares.correlation import CorrelationMiddleware
from app.middlewares.i18n import I18nMiddleware
from app.services.logging_service import setup_logging, get_logger


def main():
    """Main function to start the bot."""
    # Setup logging first
    setup_logging(
        log_level=Config.LOG_LEVEL,
        log_file="logs/bot.log",
        enable_console=True
    )
    
    logger = get_logger(__name__)
    logger.info("🚀 Starting Fantasy RPG Adventure Bot...")
    
    # Initialize bot and dispatcher
    bot = Bot(token=Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    
    # Add middlewares
    dp.message.middleware(GlobalErrorHandler())
    dp.callback_query.middleware(GlobalErrorHandler())
    dp.message.middleware(CorrelationMiddleware())
    dp.callback_query.middleware(CorrelationMiddleware())
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())
    
    # Setup error handlers
    setup_error_handlers(dp)
    
    # Register routers
    dp.include_router(start.router)
    dp.include_router(game.router)
    dp.include_router(language.router)
    
    logger.info("✅ Bot initialized successfully")
    logger.info("📱 Bot is running in polling mode")
    logger.info("💡 Press Ctrl+C to stop the bot")
    
    # Start polling
    try:
        asyncio.run(dp.start_polling(bot))
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error("❌ Fatal error occurred", error_type=type(e).__name__, error_message=str(e))
        raise

if __name__ == "__main__":
    main()
