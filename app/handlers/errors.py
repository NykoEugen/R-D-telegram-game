from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, Router
from aiogram.types import TelegramObject, ErrorEvent
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramRetryAfter

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
            update_info = self._extract_update_info(event)
            
            # Log the error with full context
            logger.error(
                "Unhandled exception in update processing",
                correlation_id=corr_id,
                update_type=update_info.get('type'),
                user_id=update_info.get('user_id'),
                chat_id=update_info.get('chat_id'),
                error_type=type(e).__name__,
                error_message=str(e),
                exception_details=self._format_exception(e)
            )
            
            # Re-raise the exception to maintain original behavior
            raise
    
    def _extract_update_info(self, event: TelegramObject) -> Dict[str, Any]:
        """Extract basic update information for error logging."""
        info = {}
        
        try:
            if hasattr(event, 'message') and event.message:
                info.update({
                    'type': 'message',
                    'user_id': event.message.from_user.id if event.message.from_user else None,
                    'chat_id': event.message.chat.id if event.message.chat else None,
                })
            elif hasattr(event, 'callback_query') and event.callback_query:
                info.update({
                    'type': 'callback_query',
                    'user_id': event.callback_query.from_user.id if event.callback_query.from_user else None,
                    'chat_id': event.callback_query.message.chat.id if event.callback_query.message else None,
                })
            elif hasattr(event, 'inline_query') and event.inline_query:
                info.update({
                    'type': 'inline_query',
                    'user_id': event.inline_query.from_user.id if event.inline_query.from_user else None,
                })
        except Exception:
            # If we can't extract info, just continue
            pass
        
        return info
    


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
            update_info = {}
            try:
                if update.message:
                    update_info.update({
                        'type': 'message',
                        'user_id': update.message.from_user.id if update.message.from_user else None,
                        'chat_id': update.message.chat.id if update.message.chat else None,
                    })
                elif update.callback_query:
                    update_info.update({
                        'type': 'callback_query',
                        'user_id': update.callback_query.from_user.id if update.callback_query.from_user else None,
                        'chat_id': update.callback_query.message.chat.id if update.callback_query.message else None,
                    })
            except Exception:
                pass
            
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
