from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from aiogram.types.base import UNSET

from app.core.utils import extract_update_info
from app.services.logging_service import (
    get_logger, 
    set_correlation_id, 
    generate_correlation_id,
    get_correlation_id
)

logger = get_logger(__name__)

class CorrelationMiddleware(BaseMiddleware):
    """Middleware that adds correlation IDs to updates and logs request/response information."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
        **kwargs
    ) -> Any:
        """Process update with correlation ID and logging."""
        # Generate correlation ID for this update
        corr_id = generate_correlation_id()
        set_correlation_id(corr_id)
        
        # Extract useful information from the update
        update_info = extract_update_info(event)
        
        # Log incoming update
        logger.info(
            "Processing update",
            correlation_id=corr_id,
            update_type=update_info['type'],
            user_id=update_info.get('user_id'),
            chat_id=update_info.get('chat_id'),
            message_id=update_info.get('message_id'),
            callback_data=update_info.get('callback_data'),
            **{k: v for k, v in update_info.items() if v is not None}
        )
        
        try:
            # Process the update - avoid unpacking data to prevent handler parameter conflicts
            result = await handler(event, data)
            
            # Log successful processing
            logger.info(
                "Update processed successfully",
                correlation_id=corr_id,
                update_type=update_info['type'],
                user_id=update_info.get('user_id'),
                chat_id=update_info.get('chat_id')
            )
            
            return result
            
        except Exception as e:
            # Log error with correlation ID
            logger.error(
                "Error processing update",
                correlation_id=corr_id,
                update_type=update_info['type'],
                user_id=update_info.get('user_id'),
                chat_id=update_info.get('chat_id'),
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
        finally:
            # Clear correlation ID from context
            set_correlation_id(None)
    
