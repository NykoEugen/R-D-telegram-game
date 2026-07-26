"""
Anti-spam throttling middleware — rejects updates from a user that arrive
faster than a minimum interval, using a Redis TTL key as a lock.

This is unrelated to the gameplay energy system (app/services/repositories/
player_repo.py's consume_energy/apply_energy_regen) — it's a pure
rate-limit guard against rapid double-taps/spam, not a game resource.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.redis import get_redis

THROTTLE_MS = 400


class ThrottlingMiddleware(BaseMiddleware):
    """Drops updates from a user arriving within THROTTLE_MS of the previous one."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message | CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        redis = get_redis()
        key = f"throttle:{user_id}"
        acquired = await redis.set(key, b"1", px=THROTTLE_MS, nx=True)

        if not acquired:
            if isinstance(event, CallbackQuery):
                await event.answer()
            return None

        return await handler(event, data)
