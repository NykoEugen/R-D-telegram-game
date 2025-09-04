"""
Core utilities for the Telegram RPG game bot.

This module contains common utility functions used across the application.
"""

from typing import Any, Dict, Optional
from aiogram.types import TelegramObject, Update


def extract_update_info(event: TelegramObject) -> Dict[str, Any]:
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


def format_exception(exception: Exception) -> Dict[str, Any]:
    """Format exception information for logging."""
    return {
        'type': type(exception).__name__,
        'message': str(exception),
        'module': getattr(exception, '__module__', None),
    }
