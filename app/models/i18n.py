"""
Internationalization models for the Telegram RPG game bot.

This module defines I18nString model for optional database-based localization.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import String, Integer, DateTime, Boolean, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class I18nCategory(str, Enum):
    """I18n category enumeration."""
    UI = "ui"
    GAME_CONTENT = "game_content"
    ITEM_NAMES = "item_names"
    ITEM_DESCRIPTIONS = "item_descriptions"
    SCENE_DESCRIPTIONS = "scene_descriptions"
    QUEST_NAMES = "quest_names"
    QUEST_DESCRIPTIONS = "quest_descriptions"
    ACTION_NAMES = "action_names"
    ACTION_DESCRIPTIONS = "action_descriptions"
    DIALOGUE = "dialogue"
    SYSTEM_MESSAGES = "system_messages"
    ERROR_MESSAGES = "error_messages"
    HELP_TEXT = "help_text"
    TUTORIAL = "tutorial"
    ACHIEVEMENTS = "achievements"
    NOTIFICATIONS = "notifications"


class I18nString(Base):
    """I18nString model for database-based localization strings."""
    
    __tablename__ = "i18n_strings"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # String identification
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[I18nCategory] = mapped_column(String(50), nullable=False, index=True)
    
    # Language and content
    language_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # e.g., 'en', 'uk', 'ru'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # String metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Description for translators
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Usage context
    variables: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Template variables
    
    # String properties
    is_plural: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    plural_forms: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)  # For languages with multiple plural forms
    
    # String status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Translation verified by native speaker
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # String usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # String versioning
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # For string variations
    
    # String tags and categorization
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Tags for categorization
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Translation priority
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('key', 'language_code', name='uq_i18n_strings_key_language'),
        UniqueConstraint('key', 'category', 'language_code', name='uq_i18n_strings_key_category_language'),
    )
    
    def __repr__(self) -> str:
        return f"<I18nString(id={self.id}, key={self.key}, language={self.language_code}, category={self.category})>"
    
    @classmethod
    def get_string(cls, key: str, language_code: str, category: Optional[I18nCategory] = None) -> Optional[str]:
        """
        Get a localized string by key and language.
        
        Args:
            key: The string key
            language_code: The language code (e.g., 'en', 'uk')
            category: Optional category filter
            
        Returns:
            The localized string content or None if not found
        """
        # This would be implemented as a class method or service method
        # that queries the database for the string
        pass
    
    def format_string(self, **kwargs) -> str:
        """
        Format the string with provided variables.
        
        Args:
            **kwargs: Variables to substitute in the string
            
        Returns:
            The formatted string
        """
        if not self.variables:
            return self.content
        
        try:
            return self.content.format(**kwargs)
        except (KeyError, ValueError):
            # Return original content if formatting fails
            return self.content
