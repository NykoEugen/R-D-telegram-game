"""
Database middleware for the Telegram RPG game bot.

This middleware provides database session management and FSM state restoration.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.db import get_db_session
from app.services.fsm_service import FSMStateService
from app.services.logging_service import get_logger

logger = get_logger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware for database session management and FSM state restoration."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
        **kwargs
    ) -> Any:
        """Process update with database session and FSM state restoration."""
        
        # Get user ID from the event
        user_id = None
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
        elif hasattr(event, 'message') and event.message and event.message.from_user:
            user_id = event.message.from_user.id
        elif hasattr(event, 'callback_query') and event.callback_query and event.callback_query.from_user:
            user_id = event.callback_query.from_user.id
        
        # Create database session
        async with get_db_session() as session:
            # Add session to data for handlers to use
            data["db_session"] = session
            
            # Create FSM service
            fsm_service = FSMStateService(session)
            data["fsm_service"] = fsm_service

            # Process the update
            try:
                result = await handler(event, data)

                # Sync FSM state to PostgreSQL for telemetry after successful processing
                if user_id and "state" in data:
                    try:
                        action = "callback_query" if hasattr(event, 'data') else "text_message"
                        await fsm_service.sync_fsm_to_postgres(
                            data["state"],
                            user_id,
                            action=action,
                        )
                    except Exception as e:
                        logger.error("Failed to sync FSM state to PostgreSQL",
                                    user_id=user_id,
                                    error_type=type(e).__name__,
                                    error_message=str(e))

                return result

            except Exception as e:
                logger.error("Error in database middleware",
                            user_id=user_id,
                            error_type=type(e).__name__,
                            error_message=str(e))
                raise
