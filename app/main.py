import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.config import Config
from app.handlers import start, game, language
from app.handlers.errors import setup_error_handlers
from app.middlewares.i18n import I18nMiddleware
from app.middlewares.correlation import CorrelationMiddleware
from app.services.logging_service import setup_logging, get_logger

# Configure logging
def setup_logging_config():
    """Configure logging with structured JSON format and orjson."""
    # Setup logging with our new service
    setup_logging(
        log_level=Config.LOG_LEVEL,
        log_file="logs/bot.log",
        enable_console=True
    )

async def on_startup(bot: Bot, base_url: str):
    """Actions to perform on bot startup."""
    logger = get_logger(__name__)
    
    if base_url:
        # Set webhook
        await bot.set_webhook(
            url=f"{base_url}{Config.WEBHOOK_PATH}",
            drop_pending_updates=True
        )
        logger.info("Webhook set successfully", 
                   webhook_url=f"{base_url}{Config.WEBHOOK_PATH}")
    else:
        # Delete webhook for polling mode
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted, using polling mode")
    
    logger.info("Bot started successfully")

async def on_shutdown(bot: Bot):
    """Actions to perform on bot shutdown."""
    logger = get_logger(__name__)
    
    # Delete webhook
    await bot.delete_webhook()
    logger.info("Webhook deleted")
    
    # Close bot session
    await bot.session.close()
    logger.info("Bot session closed")

def main():
    """Main function to start the bot."""
    # Setup logging
    setup_logging_config()
    logger = get_logger(__name__)
    
    # Initialize bot and dispatcher
    bot = Bot(token=Config.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    
    # Register middleware in order of execution
    dp.message.middleware(CorrelationMiddleware())
    dp.callback_query.middleware(CorrelationMiddleware())
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())
    
    # Register routers
    dp.include_router(start.router)
    dp.include_router(game.router)
    dp.include_router(language.router)
    
    # Setup error handlers
    setup_error_handlers(dp)
    
    # Register startup and shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Check if webhook mode is enabled
    if Config.WEBHOOK_URL:
        # Webhook mode
        logger.info("Starting bot in webhook mode")
        
        # Create aiohttp application
        app = web.Application()
        
        # Setup webhook handler
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot
        )
        webhook_handler.register(app, path=Config.WEBHOOK_PATH)
        
        # Setup application
        setup_application(app, dp, bot=bot)
        
        # Start webhook
        web.run_app(
            app,
            host="0.0.0.0",
            port=Config.PORT,
            print=lambda _: None  # Disable default logging
        )
    else:
        # Polling mode
        logger.info("Starting bot in polling mode")
        asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    main()
