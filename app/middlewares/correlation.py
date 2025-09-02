from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from aiogram.types.base import UNSET

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
        data: Dict[str, Any]
    ) -> Any:
        """Process update with correlation ID and logging."""
        # Generate correlation ID for this update
        corr_id = generate_correlation_id()
        set_correlation_id(corr_id)
        
        # Extract useful information from the update
        update_info = self._extract_update_info(event)
        
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
            # Process the update
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
    
    def _extract_update_info(self, event: TelegramObject) -> Dict[str, Any]:
        """Extract relevant information from the update for logging."""
        info = {'type': 'unknown'}
        
        if isinstance(event, Update):
            # Handle different types of updates
            if event.message:
                info.update({
                    'type': 'message',
                    'user_id': event.message.from_user.id if event.message.from_user else None,
                    'chat_id': event.message.chat.id,
                    'message_id': event.message.message_id,
                    'text': event.message.text[:100] if event.message.text else None,  # Truncate long text
                    'is_command': event.message.text.startswith('/') if event.message.text else False
                })
            elif event.callback_query:
                info.update({
                    'type': 'callback_query',
                    'user_id': event.callback_query.from_user.id if event.callback_query.from_user else None,
                    'chat_id': event.callback_query.message.chat.id if event.callback_query.message else None,
                    'message_id': event.callback_query.message.message_id if event.callback_query.message else None,
                    'callback_data': event.callback_query.data[:100] if event.callback_query.data else None  # Truncate long data
                })
            elif event.inline_query:
                info.update({
                    'type': 'inline_query',
                    'user_id': event.inline_query.from_user.id if event.inline_query.from_user else None,
                    'query': event.inline_query.query[:100] if event.inline_query.query else None
                })
            elif event.chosen_inline_result:
                info.update({
                    'type': 'chosen_inline_result',
                    'user_id': event.chosen_inline_result.from_user.id if event.chosen_inline_result.from_user else None,
                    'result_id': event.chosen_inline_result.result_id
                })
            elif event.shipping_query:
                info.update({
                    'type': 'shipping_query',
                    'user_id': event.shipping_query.from_user.id if event.shipping_query.from_user else None
                })
            elif event.pre_checkout_query:
                info.update({
                    'type': 'pre_checkout_query',
                    'user_id': event.pre_checkout_query.from_user.id if event.pre_checkout_query.from_user else None
                })
            elif event.poll:
                info.update({
                    'type': 'poll',
                    'poll_id': event.poll.id
                })
            elif event.poll_answer:
                info.update({
                    'type': 'poll_answer',
                    'user_id': event.poll_answer.user.id if event.poll_answer.user else None,
                    'poll_id': event.poll_answer.poll_id
                })
            elif event.my_chat_member:
                info.update({
                    'type': 'my_chat_member',
                    'user_id': event.my_chat_member.from_user.id if event.my_chat_member.from_user else None,
                    'chat_id': event.my_chat_member.chat.id
                })
            elif event.chat_member:
                info.update({
                    'type': 'chat_member',
                    'user_id': event.chat_member.from_user.id if event.chat_member.from_user else None,
                    'chat_id': event.chat_member.chat.id
                })
            elif event.chat_join_request:
                info.update({
                    'type': 'chat_join_request',
                    'user_id': event.chat_join_request.from_user.id if event.chat_join_request.from_user else None,
                    'chat_id': event.chat_join_request.chat.id
                })
        
        return info
