import json
from pathlib import Path
from functools import lru_cache
from typing import Dict, Optional, Any
from app.services.logging_service import get_logger

logger = get_logger(__name__)

LOCALES_DIR = Path(__file__).parent.parent / "locales"
DEFAULT_LOCALE = "uk"
SUPPORTED_LOCALES = {"uk", "en"}

@lru_cache(maxsize=16)
def _load_locale(locale: str) -> dict:
    """Load locale data from JSON file with caching."""
    loc = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    try:
        with open(LOCALES_DIR / f"{loc}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Locale file not found: {loc}.json, falling back to {DEFAULT_LOCALE}")
        with open(LOCALES_DIR / f"{DEFAULT_LOCALE}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading locale {loc}: {e}")
        return {}

def t(key: str, locale: str | None = None, **kwargs) -> str:
    """Get translated text by key with formatting support."""
    try:
        data = _load_locale(locale or DEFAULT_LOCALE)
        ref = data
        
        # Navigate through nested keys (e.g., "btn.attack")
        for part in key.split("."):
            if isinstance(ref, dict):
                ref = ref.get(part, {})
            else:
                logger.warning(f"Invalid key path: {key} (stopped at {part})")
                return key
        
        if isinstance(ref, str):
            try:
                return ref.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing format parameter {e} for key {key}")
                return ref
        else:
            logger.warning(f"Key {key} is not a string: {type(ref)}")
            return key
    except Exception as e:
        logger.error(f"Error getting translation for key {key}: {e}")
        return key

# Compatibility layer for existing code
class I18nService:
    """Compatibility layer for the new i18n implementation."""
    
    def __init__(self):
        self.user_languages: Dict[int, str] = {}  # user_id -> language_code
        self.default_language = DEFAULT_LOCALE
        self.supported_languages = list(SUPPORTED_LOCALES)
        self.storage_file = Path(__file__).parent.parent.parent / "user_languages.json"
        self._load_user_languages()
    
    def _load_user_languages(self):
        """Load user language preferences from storage file."""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert string keys back to integers
                    self.user_languages = {int(k): v for k, v in data.items()}
        except Exception:
            self.user_languages = {}
    
    def _save_user_languages(self):
        """Save user language preferences to storage file."""
        try:
            # Convert integer keys to strings for JSON serialization
            data = {str(k): v for k, v in self.user_languages.items()}
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # Silently fail if we can't save
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language, defaulting to default locale."""
        return self.user_languages.get(user_id, self.default_language)
    
    def set_user_language(self, user_id: int, language_code: str):
        """Set user's preferred language."""
        if language_code in self.supported_languages:
            self.user_languages[user_id] = language_code
            self._save_user_languages()
    
    def get_text(self, user_id: int, key: str, **kwargs) -> str:
        """Get translated text for a given key and user."""
        lang_code = self.get_user_language(user_id)
        return t(key, lang_code, **kwargs)
    
    def get_language_name(self, language_code: str) -> str:
        """Get display name for language code."""
        language_names = {
            "en": "English",
            "uk": "Українська"
        }
        return language_names.get(language_code, language_code)
    
    def get_action_prompt(self, user_id: int, action_key: str) -> str:
        """Get AI prompt text for a specific action."""
        lang_code = self.get_user_language(user_id)
        return t(f"action.{action_key}", lang_code)
    
    def get_button_label(self, user_id: int, button_key: str) -> str:
        """Get button label text for a specific button."""
        lang_code = self.get_user_language(user_id)
        return t(f"btn.{button_key}", lang_code)
    
    def get_all_available_keys(self, locale: str = None) -> Dict[str, Any]:
        """Get all available translation keys for a locale."""
        loc = locale or self.default_language
        return _load_locale(loc)
    
    def validate_key(self, key: str, locale: str = None) -> bool:
        """Check if a translation key exists."""
        try:
            data = _load_locale(locale or self.default_language)
            ref = data
            for part in key.split("."):
                if isinstance(ref, dict):
                    ref = ref.get(part, {})
                else:
                    return False
            return isinstance(ref, str)
        except Exception:
            return False

# Global instance for backward compatibility
i18n_service = I18nService()
