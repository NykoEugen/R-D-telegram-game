import json
import logging
from pathlib import Path
from typing import Any, Dict, Union
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

class I18nMiddleware(BaseMiddleware):
    """Middleware for internationalization support."""
    
    def __init__(self):
        super().__init__()
        self.translations: Dict[str, Dict[str, str]] = {}
        self.user_languages: Dict[int, str] = {}  # user_id -> language_code
        self.default_language = "en"
        self.supported_languages = ["en", "uk"]
        self._load_translations()
    
    def _load_translations(self):
        """Load translation files from the locales directory."""
        try:
            locales_dir = Path(__file__).parent.parent / "locales"
            
            for lang_code in self.supported_languages:
                lang_file = locales_dir / f"{lang_code}.json"
                if lang_file.exists():
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                        logger.info(f"Loaded translations for language: {lang_code}")
                else:
                    logger.warning(f"Translation file not found: {lang_file}")
                    
        except Exception as e:
            logger.error(f"Error loading translations: {e}")
            # Fallback to empty translations
            self.translations = {}
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language, defaulting to English."""
        return self.user_languages.get(user_id, self.default_language)
    
    def set_user_language(self, user_id: int, language_code: str):
        """Set user's preferred language."""
        if language_code in self.supported_languages:
            self.user_languages[user_id] = language_code
            logger.info(f"User {user_id} language set to: {language_code}")
        else:
            logger.warning(f"Unsupported language code: {language_code}")
    
    def get_text(self, user_id: int, key: str, **kwargs) -> str:
        """Get translated text for a given key and user."""
        lang_code = self.get_user_language(user_id)
        translations = self.translations.get(lang_code, {})
        
        text = translations.get(key, key)  # Fallback to key if translation not found
        
        # Format the text with provided kwargs
        try:
            return text.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing format key {e} for text key {key} in language {lang_code}")
            return text
    
    async def __call__(
        self,
        handler: callable,
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        """Process the event through the middleware."""
        user_id = event.from_user.id
        
        # Add i18n functions to data for handlers to use
        data["_"] = lambda key, **kwargs: self.get_text(user_id, key, **kwargs)
        data["get_user_language"] = lambda: self.get_user_language(user_id)
        data["set_user_language"] = lambda lang: self.set_user_language(user_id, lang)
        data["supported_languages"] = self.supported_languages
        
        # Continue processing
        return await handler(event, data)
