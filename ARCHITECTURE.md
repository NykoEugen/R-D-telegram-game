# 🏗️ Project Architecture

This document describes the refactored architecture of the Fantasy RPG Adventure Telegram Bot, highlighting the improved structure and design patterns.

## 🎯 Architecture Overview

The project follows a **modular, layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Handlers      │  │   Middlewares   │  │   Keyboards  │ │
│  │   (Commands)    │  │   (Correlation) │  │   (UI)       │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     Business Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Game Logic    │  │   AI Services   │  │   I18n       │ │
│  │   (Actions)     │  │   (Generation)  │  │   (i18n)     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Configuration │  │   Utilities     │  │   Logging    │ │
│  │   (Settings)    │  │   (Common)      │  │   (Structured)│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Module Structure

### 🎮 Core Module (`app/core/`)

**Purpose**: Foundation layer providing essential functionality.

#### `config.py`
- **Single source of truth** for all configuration
- **Pydantic BaseSettings** for type validation and environment variable handling
- **Backward compatibility** with legacy Config class
- **Model validation** for OpenAI models and other settings

#### `utils.py`
- **Common utilities** used across the application
- **Update information extraction** for logging and debugging
- **Exception formatting** for structured error reporting
- **Reusable functions** to avoid code duplication

### 🤖 Services Module (`app/services/`)

**Purpose**: Business logic and external service integrations.

#### AI Services (`app/services/ai/`)

**`generation_service.py`**
- **AI content generation** using OpenAI API
- **Async HTTP client** with connection pooling
- **Retry logic** with exponential backoff
- **Quest and world description** generation

**`label_generator.py`**
- **Context-aware button labels** for game actions
- **Fallback system** when AI is unavailable
- **Localized label generation** based on user language
- **Deterministic seeding** for consistent results

#### Other Services

**`i18n_service.py`**
- **Internationalization** support (English/Ukrainian)
- **User language preferences** with persistent storage
- **Translation caching** for performance
- **Fallback system** for missing translations

**`logging_service.py`**
- **Structured JSON logging** with correlation IDs
- **Context-aware logging** with request tracking
- **Performance optimized** with orjson
- **Configurable log levels** and outputs

### 🎯 Handlers Module (`app/handlers/`)

**Purpose**: Request handling and user interaction.

#### Command Handlers (`app/handlers/commands/`)

**`start.py`**
- **Welcome messages** with AI-generated world descriptions
- **Help command** with comprehensive information
- **Error handling** with graceful fallbacks

**`game.py`**
- **Quest generation** with interactive action buttons
- **Game status** display (placeholder for future features)
- **Action callbacks** for user interactions
- **Demo functionality** for testing

**`language.py`**
- **Language selection** with inline keyboards
- **Language switching** with immediate feedback
- **User preference** persistence

#### Other Handlers

**`callbacks.py`**
- **Callback data structures** for inline buttons
- **Type-safe callback** handling

**`keyboards.py`**
- **Dynamic keyboard generation** based on game context
- **Action button creation** with AI-generated labels
- **Layout management** for optimal UX

**`errors.py`**
- **Global error handling** with correlation IDs
- **Structured error logging** with context
- **Graceful error recovery**

### 🎲 Game Module (`app/game/`)

**Purpose**: Game logic and mechanics.

#### `actions.py`
- **Game action definitions** with metadata
- **Action metadata** for AI label generation
- **Type-safe action** handling

#### `scenes.py`
- **Scene management** for different game situations
- **Context creation** for quests and interactions
- **Scene type definitions** for extensibility

### 🔧 Middlewares Module (`app/middlewares/`)

**Purpose**: Cross-cutting concerns and request processing.

#### `correlation.py`
- **Request correlation IDs** for tracing
- **Structured logging** of all requests
- **Performance monitoring** capabilities

## 🔄 Data Flow

### 1. Request Processing Flow

```
User Message → Middleware → Handler → Service → AI/Game Logic → Response
     ↓              ↓          ↓         ↓           ↓
  Correlation    Logging   Validation  Business   External
     ID         Context    & Auth      Logic      APIs
```

### 2. Configuration Flow

```
Environment Variables → Pydantic Settings → Config Classes → Application
         ↓                    ↓                ↓              ↓
    .env file          Type Validation    Backward        Services
                       & Defaults        Compatibility    & Handlers
```

### 3. Internationalization Flow

```
User Request → Language Detection → Translation Loading → Localized Response
     ↓              ↓                    ↓                    ↓
  User ID      i18n Service         JSON Files          Formatted Text
```

## 🎨 Design Patterns

### 1. **Dependency Injection**
- Services are injected into handlers
- Configuration is centralized and injected
- Easy testing and mocking

### 2. **Service Layer Pattern**
- Business logic separated from presentation
- Reusable services across handlers
- Clear API boundaries

### 3. **Factory Pattern**
- Dynamic keyboard generation
- Context-aware label creation
- Scene creation based on game state

### 4. **Observer Pattern**
- Middleware for cross-cutting concerns
- Event-driven error handling
- Request/response logging

### 5. **Strategy Pattern**
- Different AI models for different content types
- Fallback strategies for AI failures
- Multiple translation strategies

## 🚀 Benefits of Refactored Architecture

### ✅ **Maintainability**
- **Single Responsibility**: Each module has a clear purpose
- **Loose Coupling**: Modules depend on interfaces, not implementations
- **High Cohesion**: Related functionality is grouped together

### ✅ **Scalability**
- **Modular Design**: Easy to add new features
- **Service Layer**: Business logic can be scaled independently
- **Plugin Architecture**: New handlers and services can be added easily

### ✅ **Testability**
- **Dependency Injection**: Easy to mock dependencies
- **Separation of Concerns**: Each layer can be tested independently
- **Clear Interfaces**: Well-defined contracts between modules

### ✅ **Performance**
- **Connection Pooling**: Reused HTTP connections for AI services
- **Caching**: Translation and configuration caching
- **Async Architecture**: Non-blocking I/O operations

### ✅ **Developer Experience**
- **Clear Structure**: Easy to navigate and understand
- **Type Safety**: Pydantic models and type hints
- **Documentation**: Comprehensive inline documentation
- **Error Handling**: Structured error reporting and logging

## 🔮 Future Extensibility

### Adding New Features

1. **New Commands**: Add to `app/handlers/commands/`
2. **New Services**: Add to `app/services/`
3. **New Game Logic**: Extend `app/game/`
4. **New Middleware**: Add to `app/middlewares/`

### Adding New Languages

1. **Translation Files**: Add to `app/locales/`
2. **Service Configuration**: Update `i18n_service.py`
3. **UI Elements**: Update language selection handlers

### Adding New AI Models

1. **Service Extension**: Extend `generation_service.py`
2. **Configuration**: Add to `config.py`
3. **Model Selection**: Update service logic

## 🧪 Testing Strategy

### Unit Tests
- **Service Layer**: Test business logic in isolation
- **Utilities**: Test common functions
- **Configuration**: Test settings validation

### Integration Tests
- **Handler Tests**: Test request/response flow
- **Service Integration**: Test AI service interactions
- **Database Integration**: Test persistence layer

### End-to-End Tests
- **Bot Functionality**: Test complete user workflows
- **Multilingual**: Test language switching
- **Error Scenarios**: Test error handling and recovery

## 📊 Monitoring and Observability

### Logging
- **Structured JSON logs** with correlation IDs
- **Request/response tracking** for debugging
- **Performance metrics** for optimization

### Error Tracking
- **Centralized error handling** with context
- **Exception formatting** for analysis
- **Graceful degradation** for user experience

### Metrics
- **Request volume** and response times
- **AI service usage** and costs
- **User engagement** and language preferences

---

**🎯 This architecture provides a solid foundation for building a scalable, maintainable, and feature-rich Telegram bot!**
