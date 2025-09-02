# Fantasy RPG Adventure - Telegram Bot

A text-based RPG game bot for Telegram built with aiogram 3.13, featuring AI-generated quests and medieval fantasy adventures.

## 🎮 Features

- **AI-Generated Quests**: Dynamic quest descriptions using OpenAI API
- **Fantasy World**: Immersive medieval D&D-style setting
- **Webhook Support**: Production-ready with ngrok support for local testing
- **Async Architecture**: Built with modern Python async/await patterns
- **Structured Logging**: JSON-formatted logs for easy monitoring

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API Key
- ngrok (for local webhook testing)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd R-D-telegram-game
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

4. **Configure your bot**
   - Get a bot token from [@BotFather](https://t.me/BotFather)
   - Get an OpenAI API key from [OpenAI Platform](https://platform.openai.com/)
   - For local testing, install ngrok and get a public URL

### Environment Variables

Create a `.env` file with the following variables:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Ngrok Configuration for Local Testing
NGROK_URL=https://your-ngrok-url.ngrok.io

# Logging Configuration
LOG_LEVEL=INFO
```

## 🎯 Usage

### Local Development (Polling Mode)

```bash
python app/main.py
```

### Production (Webhook Mode)

1. **Start ngrok for local testing**
   ```bash
   ngrok http 8000
   ```

2. **Update your .env with the ngrok URL**
   ```env
   NGROK_URL=https://your-ngrok-url.ngrok.io
   ```

3. **Run the bot**
   ```bash
   python app/main.py
   ```

### Available Commands

- `/start` - Welcome message and world introduction
- `/quest` - Get a new AI-generated quest
- `/help` - Show help information
- `/status` - Game status (placeholder for future features)

## 🏗️ Project Structure

```
R-D-telegram-game/
├── app/
│   ├── __init__.py
│   ├── main.py              # Main entry point
│   ├── config.py            # Configuration and environment variables
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py         # Start and help commands
│   │   └── game.py          # Game commands (quest, status)
│   └── services/
│       ├── __init__.py
│       └── openai_service.py # OpenAI API integration
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore patterns
└── README.md                # This file
```

## 🔧 Configuration

### Bot Settings

The bot automatically detects whether to use webhook or polling mode based on the `NGROK_URL` environment variable:

- **With NGROK_URL**: Uses webhook mode on port 8000
- **Without NGROK_URL**: Uses polling mode

### Logging

Logs are written to both console and `logs/bot.log` with JSON formatting for easy parsing.

## 🎲 Game Mechanics

### Quest Generation

Quests are dynamically generated using OpenAI's GPT-3.5-turbo model with:
- Medieval fantasy themes
- D&D-style storytelling
- Concise descriptions (2-3 sentences)
- Adventure objectives and hints

### World Building

The bot generates immersive world descriptions that set the stage for adventures.

## 🚧 Future Features

This is an MVP skeleton. Planned enhancements include:
- Player character system
- Experience and leveling
- Inventory management
- Combat mechanics
- Multiple quest types
- Player interactions
- Save/load game state

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues and questions:
1. Check the existing issues
2. Create a new issue with detailed information
3. Include logs and error messages

## 🔒 Security Notes

- Never commit your `.env` file
- Keep your bot token and API keys secure
- Use environment variables for sensitive data
- Regularly rotate your API keys

---

**Happy adventuring! ⚔️🗡️🛡️**
