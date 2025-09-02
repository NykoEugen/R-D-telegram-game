# Logging System Documentation

This document describes the comprehensive logging system implemented for the Telegram RPG bot, featuring structured JSON logs, correlation IDs, and global error handling.

## Features

### 1. Structured JSON Logging
- **Format**: All logs are output in structured JSON format for easy parsing and analysis
- **Performance**: Uses `orjson` for fast JSON serialization
- **Context**: Includes timestamp, log level, logger name, module, function, and line number
- **Extra Fields**: Supports additional structured data through keyword arguments

### 2. Correlation IDs
- **Unique Tracking**: Each update/request gets a unique correlation ID (UUID)
- **Context Propagation**: Correlation IDs are automatically propagated through the request lifecycle
- **Traceability**: Enables tracking of related log entries across different components
- **Automatic Cleanup**: Correlation IDs are automatically cleared after request processing

### 3. Global Error Handling
- **Comprehensive Coverage**: Catches all exceptions at the middleware level
- **Structured Error Logs**: Errors include correlation IDs, user context, and detailed exception information
- **Telegram API Errors**: Special handling for Telegram-specific exceptions with detailed error codes
- **Non-blocking**: Errors are logged but don't prevent normal operation

## Architecture

### Components

1. **Logging Service** (`app/services/logging_service.py`)
   - Core logging functionality
   - JSON formatter with orjson
   - Correlation ID management
   - Structured logger interface

2. **Correlation Middleware** (`app/middlewares/correlation.py`)
   - Generates correlation IDs for each update
   - Logs request/response information
   - Extracts update metadata for logging

3. **Global Error Handler** (`app/handlers/errors.py`)
   - Catches all unhandled exceptions
   - Logs errors with full context
   - Maintains bot stability

4. **Updated Handlers**
   - All handlers now use structured logging
   - Consistent error handling patterns
   - Rich context information in logs

## Usage

### Basic Logging

```python
from app.services.logging_service import get_logger

logger = get_logger(__name__)

# Simple logging
logger.info("User action completed")
logger.warning("Resource usage high")
logger.error("Operation failed")

# Structured logging with extra fields
logger.info("User login successful",
           user_id=12345,
           ip_address="192.168.1.1",
           user_agent="TelegramBot/1.0")
```

### Exception Logging

```python
try:
    # Some operation
    result = risky_operation()
except Exception as e:
    logger.exception("Operation failed",
                    operation_type="data_processing",
                    input_data=input_data,
                    error_details=str(e))
```

### Correlation IDs

```python
from app.services.logging_service import (
    get_correlation_id, 
    set_correlation_id, 
    generate_correlation_id
)

# Get current correlation ID
current_id = get_correlation_id()

# Set custom correlation ID
custom_id = generate_correlation_id()
set_correlation_id(custom_id)

# Log with correlation ID
logger.info("Processing request", correlation_id=get_correlation_id())
```

## Log Format

### Standard Log Entry
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "app.handlers.start",
  "message": "User started the bot",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "module": "start",
  "function": "cmd_start",
  "line": 25,
  "user_id": 12345,
  "user_name": "John",
  "chat_id": 67890
}
```

### Error Log Entry
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "ERROR",
  "logger": "app.handlers.start",
  "message": "Error in start command",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "module": "start",
  "function": "cmd_start",
  "line": 35,
  "exception": {
    "type": "ValueError",
    "message": "Invalid input data",
    "traceback": "Traceback (most recent call last)..."
  },
  "user_id": 12345,
  "chat_id": 67890,
  "error_type": "ValueError",
  "error_message": "Invalid input data"
}
```

## Configuration

### Environment Variables
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Default: INFO

### Log Files
- **Console**: Structured JSON output to stdout
- **File**: `logs/bot.log` (configurable)
- **Rotation**: Manual (can be extended with log rotation)

## Testing

Run the logging test script to verify functionality:

```bash
python test_logging.py
```

This will:
1. Test all logging levels
2. Verify correlation ID functionality
3. Test structured logging with extra fields
4. Test exception logging
5. Generate sample log files

## Best Practices

### 1. Use Structured Logging
```python
# Good
logger.info("User action", user_id=123, action="login", success=True)

# Avoid
logger.info(f"User {user_id} performed {action} with result {success}")
```

### 2. Include Relevant Context
```python
logger.error("API call failed",
            endpoint="/api/users",
            status_code=500,
            user_id=user_id,
            correlation_id=get_correlation_id())
```

### 3. Handle Exceptions Properly
```python
try:
    result = await operation()
except SpecificException as e:
    logger.warning("Expected error occurred", 
                  error_type=type(e).__name__,
                  context="user_validation")
except Exception as e:
    logger.exception("Unexpected error", 
                    operation="user_creation",
                    user_data=user_data)
```

### 4. Use Correlation IDs for Tracing
```python
# At the start of a complex operation
corr_id = generate_correlation_id()
set_correlation_id(corr_id)

# Throughout the operation
logger.info("Step 1 completed", correlation_id=corr_id, step="validation")
logger.info("Step 2 completed", correlation_id=corr_id, step="processing")

# Clear at the end
set_correlation_id(None)
```

## Monitoring and Analysis

### Log Aggregation
- Logs are in JSON format for easy ingestion into log aggregation systems
- Correlation IDs enable request tracing across distributed systems
- Structured fields support advanced filtering and alerting

### Common Queries
```bash
# Find all logs for a specific user
grep '"user_id": 12345' logs/bot.log

# Find all errors with correlation IDs
grep '"level": "ERROR"' logs/bot.log | jq '.correlation_id'

# Find logs for a specific correlation ID
grep '550e8400-e29b-41d4-a716-446655440000' logs/bot.log
```

## Troubleshooting

### Common Issues

1. **Correlation ID not showing**: Ensure middleware is registered before other middleware
2. **Logs not appearing**: Check log level configuration and file permissions
3. **JSON parsing errors**: Verify orjson is installed and working

### Debug Mode
Set `LOG_LEVEL=DEBUG` to see detailed logging information including:
- All middleware operations
- Request/response details
- Internal system state

## Future Enhancements

- **Log Rotation**: Automatic log file rotation and compression
- **Metrics**: Integration with monitoring systems (Prometheus, etc.)
- **Alerting**: Automated alerts for error patterns
- **Distributed Tracing**: Integration with OpenTelemetry for microservices
- **Performance Monitoring**: Request duration and resource usage tracking
