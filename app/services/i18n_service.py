import json
from pathlib import Path
from typing import Dict, Any
from app.services.logging_service import get_logger

logger = get_logger(__name__)

class I18nService:
    """Standalone internationalization service without middleware dependencies."""
    
    def __init__(self):
        self.translations: Dict[str, Dict[str, str]] = {}
        self.user_languages: Dict[int, str] = {}  # user_id -> language_code
        self.default_language = "en"
        self.supported_languages = ["en", "uk"]
        self.storage_file = Path(__file__).parent.parent.parent / "user_languages.json"
        self._load_translations()
        self._load_user_languages()
    
    def _load_translations(self):
        """Load translation files from the locales directory."""
        try:
            locales_dir = Path(__file__).parent.parent / "locales"
            
            for lang_code in self.supported_languages:
                lang_file = locales_dir / f"{lang_code}.json"
                if lang_file.exists():
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                        logger.info("Loaded translations for language", language_code=lang_code)
                else:
                    logger.warning("Translation file not found", language_file=str(lang_file))
                    
        except Exception as e:
            logger.error("Error loading translations", 
                        error_type=type(e).__name__,
                        error_message=str(e))
            # Fallback to empty translations
            self.translations = {}
    
    def _load_user_languages(self):
        """Load user language preferences from storage file."""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert string keys back to integers
                    self.user_languages = {int(k): v for k, v in data.items()}
                    logger.info("Loaded user language preferences", count=len(self.user_languages))
            else:
                logger.info("No user language storage file found, starting with empty preferences")
        except Exception as e:
            logger.error("Error loading user language preferences", 
                        error_type=type(e).__name__,
                        error_message=str(e))
            self.user_languages = {}
    
    def _save_user_languages(self):
        """Save user language preferences to storage file."""
        try:
            # Convert integer keys to strings for JSON serialization
            data = {str(k): v for k, v in self.user_languages.items()}
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("Saved user language preferences", count=len(self.user_languages))
        except Exception as e:
            logger.error("Error saving user language preferences", 
                        error_type=type(e).__name__,
                        error_message=str(e))
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language, defaulting to English."""
        return self.user_languages.get(user_id, self.default_language)
    
    def set_user_language(self, user_id: int, language_code: str):
        """Set user's preferred language."""
        if language_code in self.supported_languages:
            self.user_languages[user_id] = language_code
            self._save_user_languages()  # Persist the change
            logger.info("User language set", user_id=user_id, language_code=language_code)
        else:
            logger.warning("Unsupported language code", 
                          user_id=user_id, 
                          language_code=language_code,
                          supported_languages=self.supported_languages)
    
    def get_text(self, user_id: int, key: str, **kwargs) -> str:
        """Get translated text for a given key and user."""
        lang_code = self.get_user_language(user_id)
        translations = self.translations.get(lang_code, {})
        
        text = translations.get(key, key)  # Fallback to key if translation not found
        
        # Format the text with provided kwargs
        try:
            return text.format(**kwargs)
        except KeyError as e:
            logger.warning("Missing format key for text", 
                          missing_key=str(e),
                          text_key=key,
                          language_code=lang_code)
            return text
    
    def get_language_name(self, language_code: str) -> str:
        """Get display name for language code."""
        language_names = {
            "en": "English",
            "uk": "Українська"
        }
        return language_names.get(language_code, language_code)

# Global instance
i18n_service = I18nService()
