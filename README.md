# Fantasy RPG Adventure - Telegram Bot

A text-based RPG game bot for Telegram built with aiogram 3.13, featuring AI-generated quests and medieval fantasy adventures.

## 🎮 Features

- **AI-Generated Quests**: Dynamic quest descriptions using OpenAI API
- **Fantasy World**: Immersive medieval D&D-style setting
- **Multilingual Support**: English and Ukrainian with easy extension
- **Action-Based Gameplay**: Interactive buttons for player choices
- **State Management**: FSM (Finite State Machine) with PostgreSQL persistence
- **Database Integration**: PostgreSQL 16 with SQLAlchemy 2.0 async support
- **Redis Caching**: Fast session management and caching layer
- **Webhook Support**: Production-ready with ngrok support for local testing
- **Async Architecture**: Built with modern Python async/await patterns
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Modular Design**: Clean separation of concerns for maintainability
- **Repository Pattern**: Clean data access layer with repositories
- **Database Migrations**: Alembic for schema versioning and management

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API Key
- ngrok (for local webhook testing)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd R-D-telegram-game
   ```

2. **Start database services**
   ```bash
   make docker-up
   # This starts PostgreSQL 16 and Redis 7
   ```

3. **Install dependencies**
   ```bash
   make install-dev
   # This installs both production and development dependencies
   ```

4. **Set up environment variables**
   ```bash
   cp env_template.txt .env
   # Edit .env with your actual values
   ```

5. **Initialize the database**
   ```bash
   make db-init
   # This runs database migrations
   ```

6. **Test the setup**
   ```bash
   make test-db    # Test database connection
   make test-redis # Test Redis connection
   ```

7. **Configure your bot**
   - Get a bot token from [@BotFather](https://t.me/BotFather)
   - Get an OpenAI API key from [OpenAI Platform](https://platform.openai.com/)
   - For local testing, install ngrok and get a public URL

## 🛠️ Development Setup

### Prerequisites

- Python 3.12+
- Git with pre-commit support

### Development Installation

1. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Set up pre-commit hooks**
   ```bash
   make precommit-install
   ```

3. **Verify installation**
   ```bash
   make check
   ```

### Development Commands

#### Code Quality
- `make install-dev` - Install all dependencies (including dev tools)
- `make format` - Format code with Black and isort
- `make lint` - Run Ruff linter
- `make typecheck` - Run MyPy type checker
- `make fix` - Auto-fix linting issues and format code
- `make check` - Run all checks (format, lint, typecheck)
- `make clean` - Clean up cache directories

#### Database Operations
- `make docker-up` - Start PostgreSQL and Redis services
- `make docker-down` - Stop all services
- `make docker-logs` - View service logs
- `make db-init` - Initialize database with migrations
- `make db-migrate MSG="message"` - Create new migration
- `make db-upgrade` - Apply pending migrations
- `make db-downgrade` - Rollback last migration
- `make db-reset` - Reset database (drop and recreate)

#### Testing & Health Checks
- `make test-db` - Test database connection
- `make test-redis` - Test Redis connection
- `make redis-cli` - Access Redis command line interface

#### Application
- `make run` - Run the bot application

### Code Quality Tools

- **Black** - Code formatter (line length: 88)
- **isort** - Import sorting (Black-compatible)
- **Ruff** - Fast Python linter with auto-fix
- **MyPy** - Static type checker
- **pre-commit** - Git hooks for code quality

### Environment Variables

Create a `.env` file with the following variables:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# Database Configuration
DATABASE_URL=postgresql+asyncpg://telegram_user:telegram_password@localhost:5432/telegram_game

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Ngrok Configuration for Local Testing
NGROK_URL=https://your-ngrok-url.ngrok.io

# Logging Configuration
LOG_LEVEL=INFO

# Webhook Configuration
PORT=8000
WEBHOOK_SECRET=your_webhook_secret_here

# Game Configuration (optional - these have defaults)
# GAME_NAME=Fantasy RPG Adventure
# GAME_DESCRIPTION=Embark on epic quests in a medieval fantasy world!
```

### Database Services

The project uses Docker Compose to run:
- **PostgreSQL 16**: Main database for persistent storage
- **Redis 7**: Caching and session management
- **pgAdmin** (optional): Database administration interface

Default credentials:
- **Database**: `telegram_game`
- **User**: `telegram_user`
- **Password**: `telegram_password`
- **Redis**: No authentication required for local development

## 🎯 Usage

### Local Development (Polling Mode)

```bash
python app/main.py
```

### Production (Webhook Mode)

1. **Start ngrok for local testing**
   ```bash
   ngrok http 8000  # or use your custom PORT from .env
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
- `/quest` - Get a new AI-generated quest with action buttons
- `/help` - Show help information
- `/status` - Game status (placeholder for future features)
- `/language` - Change bot language (English/Ukrainian)
- `/demo_actions` - Demo interactive action buttons

## 🏗️ Project Structure

```
R-D-telegram-game/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Main entry point
│   ├── core/                      # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py              # Configuration management
│   │   ├── db.py                  # Database connection and session management
│   │   ├── redis.py               # Redis connection and caching
│   │   └── utils.py               # Common utilities
│   ├── services/                  # Service layer
│   │   ├── __init__.py
│   │   ├── ai/                    # AI services
│   │   │   ├── __init__.py
│   │   │   ├── action_service.py  # Action processing service
│   │   │   ├── generation_service.py  # AI content generation
│   │   │   └── label_generator.py     # Action button labels
│   │   ├── fsm_service.py         # FSM state management
│   │   ├── i18n_service.py        # Internationalization
│   │   ├── logging_service.py     # Structured logging
│   │   └── repositories/          # Data access layer
│   │       ├── __init__.py
│   │       ├── item_repo.py       # Item repository
│   │       ├── player_repo.py     # Player repository
│   │       ├── quest_repo.py      # Quest repository
│   │       └── session_repo.py    # Session repository
│   ├── handlers/                  # Request handlers
│   │   ├── __init__.py
│   │   ├── commands/              # Command handlers
│   │   │   ├── __init__.py
│   │   │   ├── start.py           # Start and help commands
│   │   │   ├── game.py            # Game commands and callbacks
│   │   │   └── language.py        # Language selection
│   │   ├── callbacks.py           # Callback query handlers
│   │   ├── errors.py              # Error handling
│   │   └── keyboards.py           # Inline keyboard builders
│   ├── game/                      # Game logic
│   │   ├── __init__.py
│   │   ├── actions.py             # Game actions and metadata
│   │   ├── scenes.py              # Scene management
│   │   └── states.py              # FSM state definitions
│   ├── middlewares/               # Middleware components
│   │   ├── __init__.py
│   │   ├── correlation.py         # Request correlation
│   │   └── database.py            # Database middleware
│   ├── models/                    # Database models
│   │   ├── __init__.py
│   │   ├── i18n.py                # Internationalization models
│   │   ├── items.py               # Item models
│   │   ├── lore.py                # Lore and story models
│   │   ├── player.py              # Player models
│   │   ├── telemetry.py           # Telemetry models
│   │   └── user.py                # User models
│   ├── locales/                   # Translation files
│   │   ├── __init__.py
│   │   ├── en.json                # English translations
│   │   └── uk.json                # Ukrainian translations
│   └── prompts.py                 # AI prompt templates
├── alembic/                       # Database migrations
│   ├── versions/                  # Migration files
│   ├── env.py                     # Alembic environment
│   └── script.py.mako             # Migration template
├── requirements.txt               # Python dependencies
├── requirements-dev.txt           # Development dependencies
├── pyproject.toml                # Project configuration and tool settings
├── docker-compose.yml            # Database services configuration
├── alembic.ini                   # Alembic configuration
├── init.sql                      # Database initialization
├── env_template.txt              # Environment variables template
├── Makefile                      # Development task automation
├── .gitignore                    # Git ignore patterns
├── ARCHITECTURE.md               # Architecture documentation
├── DATABASE_SETUP.md             # Database setup guide
├── FSM_INTEGRATION.md            # FSM integration guide
└── README.md                     # This file
```

## 🔧 Configuration

### Configuration System

The bot uses **Pydantic BaseSettings** for robust configuration management:

- **Automatic .env loading** with environment variable support
- **Type validation** and default values for all settings
- **Model validation** ensures only valid OpenAI models are used
- **Backward compatibility** with existing code
- **Environment variable overrides** for flexible deployment

### Environment Variables

All configuration is managed through environment variables with sensible defaults:

- **Required**: `BOT_TOKEN`, `OPENAI_API_KEY`
- **Database**: `DATABASE_URL`, `REDIS_URL`
- **Optional**: `OPENAI_MODEL`, `LOG_LEVEL`, `PORT`, `WEBHOOK_SECRET`, `NGROK_URL`
- **Game settings**: `GAME_NAME`, `GAME_DESCRIPTION` (with defaults)

### Dependencies

#### Core Dependencies
- **aiogram 3.13.0**: Modern Telegram Bot API framework
- **openai 1.40.0**: OpenAI API client for AI content generation
- **pydantic 2.8.2**: Data validation and settings management
- **aiohttp 3.9.1**: Async HTTP client for external APIs
- **uvicorn**: ASGI server for webhook support

#### Database & Storage
- **sqlalchemy[asyncio] 2.0.25**: Async ORM with PostgreSQL support
- **asyncpg 0.29.0**: Async PostgreSQL driver
- **alembic 1.13.1**: Database migration tool
- **redis 5.0.1**: Redis client for caching
- **aioredis 2.0.1**: Async Redis client

#### Development Tools
- **black 24.8.0**: Code formatter
- **isort 5.13.2**: Import sorter
- **ruff 0.6.9**: Fast Python linter
- **mypy 1.11.2**: Static type checker
- **pre-commit 3.8.0**: Git hooks for code quality

### Available OpenAI Models

The bot supports all current OpenAI chat completion models:

**🚀 GPT-4 Models (Most Capable):**
- `gpt-4o` - Best overall performance, great for storytelling
- `gpt-4-turbo` - Excellent balance of capability and cost
- `gpt-4` - High-quality responses
- `gpt-4-32k` - Extended context window

**⚡ GPT-3.5 Models (Fast & Cost-Effective):**
- `gpt-3.5-turbo` - Fast and cost-effective (default)
- `gpt-3.5-turbo-16k` - Extended context
- `gpt-3.5-turbo-instruct` - Instruction-following

**📚 Legacy Models:**
- Various snapshot versions for specific use cases

**💡 Recommendations:**
- **For best quality**: `gpt-4o` (most expensive)
- **For balanced performance**: `gpt-4-turbo`
- **For cost-effectiveness**: `gpt-3.5-turbo` (default)

### Bot Settings

The bot automatically detects whether to use webhook or polling mode based on the `NGROK_URL` environment variable:

- **With NGROK_URL**: Uses webhook mode on configurable port (default: 8000)
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

### State Management (FSM)

The bot uses a Finite State Machine for game flow:
- **Persistent State**: Game state survives bot restarts via PostgreSQL
- **State Groups**: Organized by game scenarios (Game, Quest, Combat, Dialogue)
- **Automatic Sync**: FSM state automatically synced to database after actions
- **State Restoration**: Seamless reconnection with state recovery

### Interactive Actions
- **Action Buttons**: Context-aware buttons for player choices
- **Scene Management**: Dynamic scene contexts for different situations
- **AI-Generated Labels**: Smart button labels based on context
- **Quest System**: AI-generated quests with multiple action options

### Database Integration
- **Session Management**: Persistent game sessions with full state tracking
- **User Data**: Player profiles, preferences, and progress
- **Caching Layer**: Redis for fast session and data access
- **Repository Pattern**: Clean data access with type-safe operations

### Multilingual Support
- **Language Selection**: Easy switching between English and Ukrainian
- **Localized Content**: All game content translated
- **Fallback System**: Graceful handling of missing translations

## 📚 Documentation

The project includes comprehensive documentation:

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Detailed architecture overview and design patterns
- **[DATABASE_SETUP.md](DATABASE_SETUP.md)**: Database setup and migration guide
- **[FSM_INTEGRATION.md](FSM_INTEGRATION.md)**: FSM state management integration guide
- **[LOGGING.md](LOGGING.md)**: Logging configuration and best practices

## 🚧 Future Features

Current MVP includes core functionality with database and FSM integration. Planned enhancements:

### Core Game Features
- Player character system with stats and progression
- Experience and leveling mechanics
- Inventory management system
- Combat mechanics with turn-based battles
- Multiple quest types and storylines
- Player interactions and NPCs
- Achievement system
- Multiplayer features

### Technical Enhancements
- Advanced analytics and telemetry
- Performance monitoring and optimization
- Enhanced caching strategies
- API rate limiting and throttling
- Advanced error recovery mechanisms

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
