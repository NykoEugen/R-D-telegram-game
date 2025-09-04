from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, Router
from aiogram.types import TelegramObject, ErrorEvent
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramRetryAfter

from app.core.utils import extract_update_info, format_exception
from app.services.logging_service import get_logger, get_correlation_id

logger = get_logger(__name__)

class GlobalErrorHandler(BaseMiddleware):
    """Global error handler that catches all exceptions and logs them with correlation IDs."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Process update with global error handling."""
        try:
            return await handler(event, data)
        except Exception as e:
            # Get correlation ID if available
            corr_id = get_correlation_id()
            
            # Extract update information for logging
            update_info = extract_update_info(event)
            
            # Log the error with full context
            logger.error(
                "Unhandled exception in update processing",
                correlation_id=corr_id,
                update_type=update_info.get('type'),
                user_id=update_info.get('user_id'),
                chat_id=update_info.get('chat_id'),
                error_type=type(e).__name__,
                error_message=str(e),
                exception_details=format_exception(e)
            )
            
            # Re-raise the exception to maintain original behavior
            raise
    
    


def setup_error_handlers(router: Router) -> None:
    """Setup error handlers for the router."""
    
    @router.errors()
    async def errors_handler(event: ErrorEvent) -> bool:
        """Handle all errors that occur during update processing."""
        try:
            corr_id = get_correlation_id()
            
            # Extract error information
            error = event.exception
            update = event.update
            
            # Extract update information
            update_info = extract_update_info(update)
            
            # Log the error with full context
            logger.error(
                "Error event occurred",
                correlation_id=corr_id,
                update_type=update_info.get('type'),
                user_id=update_info.get('user_id'),
                chat_id=update_info.get('chat_id'),
                error_type=type(error).__name__,
                error_message=str(error)
            )
            
        except Exception as e:
            # Fallback error logging
            logger.error("Error in error handler", error=str(e))
        
        # Return True to indicate the error was handled
        return True
