# 🌍 Multilingual Support for Telegram RPG Bot

This document describes the multilingual (i18n) system implemented in the aiogram 3.13 Telegram RPG bot.

## 🎯 Overview

The bot now supports **Ukrainian** and **English** languages, with a flexible system that makes it easy to add more languages in the future.

## 🏗️ Architecture

### 1. Locales Directory (`app/locales/`)
- **`en.json`** - English translations
- **`uk.json`** - Ukrainian translations
- Each file contains key-value pairs for all bot messages

### 2. I18n Service (`app/services/i18n_service.py`)
- Automatically detects and manages user language preferences
- Loads translations from JSON files with caching
- Provides translation functions to handlers
- Stores user language preferences in JSON file (easily extensible to database)

### 3. Language Handler (`app/handlers/commands/language.py`)
- Implements `/language` command
- Provides inline keyboard for language selection
- Handles language switching callbacks

## 🚀 Features

### ✅ Implemented
- **Automatic language detection** (defaults to English)
- **User language preferences** stored per user
- **Seamless language switching** via `/language` command
- **All bot messages localized** (start, help, quest, status)
- **Fallback system** for missing translations
- **Easy extension** for new languages

### 🔮 Future Enhancements
- Database storage for language preferences
- Language detection from Telegram user settings
- More languages (German, French, Spanish, etc.)
- Dynamic language loading without restart

## 📱 Usage

### For Users
1. **Default language**: English
2. **Change language**: Use `/language` command
3. **Select language**: Choose from inline keyboard buttons
4. **All messages**: Automatically appear in selected language

### For Developers
1. **Add new translation keys** to locale files
2. **Use `_()` function** in handlers: `_("key_name", param=value)`
3. **Add new languages** by creating new JSON files
4. **Extend middleware** for database storage

## 🛠️ Implementation Details

### Translation Function Usage
```python
# In handlers, use the i18n service
from app.services.i18n_service import i18n_service

# Get translated text for user
user_id = message.from_user.id
welcome_text = i18n_service.get_text(user_id, "start_welcome", name=user_name)
quest_text = i18n_service.get_text(user_id, "quest_description", description=quest_desc)
```

### Adding New Translation Keys
1. Add key to `app/locales/en.json`:
   ```json
   {
     "new_feature": "This is a new feature!"
   }
   ```

2. Add corresponding translation to `app/locales/uk.json`:
   ```json
   {
     "new_feature": "Це нова функція!"
   }
   ```

3. Use in handlers:
   ```python
   user_id = message.from_user.id
   message_text = i18n_service.get_text(user_id, "new_feature")
   ```

### Adding New Languages
1. Create new locale file: `app/locales/de.json`
2. Add language code to i18n service: `self.supported_languages = ["en", "uk", "de"]`
3. Add language button to `/language` command

## 📊 Current Translation Coverage

### Commands
- `/start` - Welcome message and world introduction
- `/help` - Help information and available commands
- `/quest` - Quest generation and description
- `/status` - Game status information
- `/language` - Language selection

### Message Types
- Welcome messages
- Help text
- Quest descriptions
- Error messages
- Status information
- Command descriptions

## 🧪 Testing

### Run Tests
```bash
# Activate virtual environment
source venv/bin/activate

# Run i18n tests
python test_i18n.py

# Run multilingual demo
python demo_i18n.py
```

### Test Coverage
- ✅ Translation loading
- ✅ Language switching
- ✅ Text formatting with parameters
- ✅ Fallback for missing keys
- ✅ JSON file validation

## 🔧 Configuration

### Environment Variables
No additional environment variables required. The system works with existing bot configuration.

### Service Settings
```python
# In app/services/i18n_service.py
self.default_language = "uk"  # Change default language
self.supported_languages = ["en", "uk"]  # Add/remove languages
```

## 📁 File Structure

```
app/
├── locales/
│   ├── __init__.py
│   ├── en.json          # English translations
│   └── uk.json          # Ukrainian translations
├── services/
│   └── i18n_service.py  # I18n service (replaces middleware)
├── handlers/
│   ├── __init__.py
│   └── commands/        # Command handlers
│       ├── __init__.py
│       ├── start.py     # Updated with i18n
│       ├── game.py      # Updated with i18n
│       └── language.py  # Language selection handler
├── core/
│   ├── __init__.py
│   ├── config.py        # Configuration management
│   └── utils.py         # Common utilities
└── main.py              # Updated with new structure
```

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Bot
```bash
python app/main.py
```

### 3. Test Multilingual Features
- Send `/start` to see welcome message in default language
- Send `/language` to change language
- Send `/quest` to see quest in selected language
- Send `/help` to see help in selected language

## 🔍 Troubleshooting

### Common Issues

1. **Translations not loading**
   - Check file paths in `app/locales/`
   - Verify JSON syntax in locale files
   - Check i18n service initialization in `main.py`

2. **Language not switching**
   - Verify i18n service is properly initialized
   - Check callback query handling in language handler
   - Ensure user ID is being passed correctly

3. **Missing translation keys**
   - Add missing keys to all locale files
   - Use fallback system for development
   - Check key names match between files

### Debug Mode
Enable debug logging to see middleware operations:
```python
# In config.py
LOG_LEVEL = "DEBUG"
```

## 🌟 Best Practices

1. **Always use translation keys** instead of hardcoded strings
2. **Keep translation keys descriptive** and consistent
3. **Test with multiple languages** during development
4. **Use parameters** for dynamic content: `i18n_service.get_text(user_id, "key", param=value)`
5. **Maintain parallel structure** between locale files

## 🔮 Roadmap

### Phase 1 (Current) ✅
- Basic English/Ukrainian support
- In-memory language storage
- Manual language switching

### Phase 2 (Future)
- Database storage for language preferences
- Automatic language detection from Telegram
- More language options

### Phase 3 (Future)
- Dynamic language loading
- Translation management interface
- Community translation contributions

## 📚 Resources

- [aiogram 3.x Documentation](https://docs.aiogram.dev/)
- [JSON Format Specification](https://www.json.org/)
- [Unicode Language Codes](https://www.iana.org/assignments/language-subtag-registry)

## 🤝 Contributing

To add new languages or improve translations:

1. Fork the repository
2. Create new locale file or update existing ones
3. Test with `python test_i18n.py`
4. Submit pull request

## 📄 License

This multilingual system is part of the main bot project and follows the same license terms.

---

**🎯 The multilingual system is now fully integrated and ready for production use!**
