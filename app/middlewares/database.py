"""
Database middleware for the Telegram RPG game bot.

This middleware provides database session management and FSM state restoration.
"""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.services.fsm_service import FSMStateService
from app.services.logging_service import get_logger

logger = get_logger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware for database session management and FSM state restoration."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
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
            
            # Restore FSM state if user_id is available
            if user_id:
                try:
                    # Get FSM context from data
                    fsm_context = data.get("state")
                    if fsm_context:
                        # Restore FSM state from PostgreSQL
                        game_session = await fsm_service.restore_fsm_from_postgres(
                            fsm_context, user_id
                        )
                        if game_session:
                            data["game_session"] = game_session
                            logger.info("Restored FSM state from PostgreSQL",
                                       user_id=user_id,
                                       session_id=game_session.session_id)
                        else:
                            logger.info("No active session found for user",
                                       user_id=user_id)
                    else:
                        logger.warning("No FSM context found in data", user_id=user_id)
                        
                except Exception as e:
                    logger.error("Failed to restore FSM state",
                                user_id=user_id,
                                error_type=type(e).__name__,
                                error_message=str(e))
                    # Continue processing even if FSM restoration fails
            
            # Process the update
            try:
                result = await handler(event, data)
                
                # Sync FSM state to PostgreSQL after successful processing
                if user_id and "state" in data:
                    fsm_context = data["state"]
                    try:
                        # Extract action and scene info from the event
                        action = None
                        scene_id = None
                        
                        if hasattr(event, 'data') and event.data:
                            # Callback query with action data
                            action = "callback_query"
                        elif hasattr(event, 'text') and event.text:
                            # Text message
                            action = "text_message"
                        
                        # Sync FSM state
                        await fsm_service.sync_fsm_to_postgres(
                            fsm_context,
                            user_id,
                            action=action,
                            scene_id=scene_id
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
