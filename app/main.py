import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.core.config import Config
from app.core.db import close_db, init_db
from app.core.redis import close_redis, get_redis, init_redis
from app.handlers.city import router as city_router
from app.handlers.commands import character_router, language_router, start_router
from app.handlers.commands.hero import router as hero_router
from app.handlers.commands.heroes import router as heroes_router
from app.handlers.errors import GlobalErrorHandler, setup_error_handlers
from app.handlers.menu import router as menu_router
from app.handlers.quest_runner import router as quest_runner_router
from app.handlers.travel import router as travel_router
from app.middlewares.correlation import CorrelationMiddleware
from app.middlewares.database import DatabaseMiddleware
from app.services.cache_cleanup_service import cache_cleanup_service
from app.services.i18n_service import i18n_service
from app.services.logging_service import get_logger, setup_logging


async def main():
    setup_logging(log_level=Config.LOG_LEVEL, log_file="logs/bot.log", enable_console=True)

    logger = get_logger(__name__)
    logger.info("Starting Fantasy RPG Adventure Bot...")

    logger.info("Initializing database connection...")
    await init_db()

    logger.info("Initializing Redis connection...")
    await init_redis()

    storage = RedisStorage(redis=get_redis())
    bot = Bot(token=Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=storage)

    dp.message.middleware(GlobalErrorHandler())
    dp.callback_query.middleware(GlobalErrorHandler())
    dp.message.middleware(CorrelationMiddleware())
    dp.callback_query.middleware(CorrelationMiddleware())
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    logger.info("i18n service initialized", supported_languages=i18n_service.supported_languages)

    await cache_cleanup_service.start()
    bot.i18n_service = i18n_service

    setup_error_handlers(dp)

    dp.include_router(city_router)
    dp.include_router(travel_router)
    dp.include_router(menu_router)
    dp.include_router(start_router)
    dp.include_router(language_router)
    dp.include_router(character_router)
    dp.include_router(hero_router)
    dp.include_router(heroes_router)
    dp.include_router(quest_runner_router)
    logger.info("All routers registered")

    try:
        if Config.WEBHOOK_BASE_URL:
            logger.info("Bot is running in webhook mode", webhook_url=Config.WEBHOOK_URL)
            await bot.set_webhook(
                url=Config.WEBHOOK_URL,
                secret_token=Config.WEBHOOK_SECRET,
            )
            app = web.Application()
            SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
                secret_token=Config.WEBHOOK_SECRET,
            ).register(app, path=Config.WEBHOOK_PATH)
            setup_application(app, dp, bot=bot)

            async def health(_: web.Request) -> web.Response:
                return web.Response(text="ok")

            app.router.add_get("/health", health)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host="0.0.0.0", port=Config.PORT)
            await site.start()
            logger.info("Webhook server started", host="0.0.0.0", port=Config.PORT)
            await asyncio.Event().wait()
        else:
            logger.info("Bot is running in polling mode")
            await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Fatal error occurred", error_type=type(e).__name__, error_message=str(e))
        raise
    finally:
        if Config.WEBHOOK_BASE_URL:
            await bot.delete_webhook()
        await cache_cleanup_service.stop()
        await close_db()
        await close_redis()
        logger.info("All connections closed")


if __name__ == "__main__":
    asyncio.run(main())
