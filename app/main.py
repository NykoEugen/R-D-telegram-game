import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from pythonjsonlogger import jsonlogger

from app.config import Config
from app.handlers import start, game, language
from app.middlewares.i18n import I18nMiddleware

# Configure logging
def setup_logging():
    """Configure logging with JSON format and proper level."""
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    
    # Create JSON formatter
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler
    log_file = Path("logs/bot.log")
    log_file.parent.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")

async def on_startup(bot: Bot, base_url: str):
    """Actions to perform on bot startup."""
    logger = logging.getLogger(__name__)
    
    if base_url:
        # Set webhook
        await bot.set_webhook(
            url=f"{base_url}{Config.WEBHOOK_PATH}",
            drop_pending_updates=True
        )
        logger.info(f"Webhook set to {base_url}{Config.WEBHOOK_PATH}")
    else:
        # Delete webhook for polling mode
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted, using polling mode")
    
    logger.info("Bot started successfully")

async def on_shutdown(bot: Bot):
    """Actions to perform on bot shutdown."""
    logger = logging.getLogger(__name__)
    
    # Delete webhook
    await bot.delete_webhook()
    logger.info("Webhook deleted")
    
    # Close bot session
    await bot.session.close()
    logger.info("Bot session closed")

def main():
    """Main function to start the bot."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Initialize bot and dispatcher
    bot = Bot(token=Config.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    
    # Register middleware
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())
    
    # Register routers
    dp.include_router(start.router)
    dp.include_router(game.router)
    dp.include_router(language.router)
    
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
