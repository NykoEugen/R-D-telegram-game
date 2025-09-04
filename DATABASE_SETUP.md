# Database and Storage Setup

This document describes the database and storage infrastructure for the R-D-telegram-game project.

## Overview

The project uses:
- **PostgreSQL 16** for persistent data storage
- **Redis 7** for caching and session management
- **SQLAlchemy 2.0** with async support for database operations
- **Alembic** for database migrations

## Quick Start

### 1. Start the Services

```bash
# Start PostgreSQL and Redis using Docker Compose
make docker-up

# Or manually:
docker-compose up -d
```

### 2. Install Dependencies

```bash
# Install all required packages
make install-dev
```

### 3. Initialize the Database

```bash
# Run database migrations
make db-init

# Or manually:
alembic upgrade head
```

### 4. Test Connections

```bash
# Test database connection
make test-db

# Test Redis connection
make test-redis
```

### 5. Create Your First Model

```bash
# Create a new migration for your model
make db-migrate MSG="Add your model name"

# Apply the migration
make db-upgrade
```

## ✅ System Status

The database and storage system is now fully operational:

- ✅ **PostgreSQL 16**: Running and accessible
- ✅ **Redis 7**: Running and accessible  
- ✅ **SQLAlchemy 2.0**: Configured with async support
- ✅ **Alembic**: Ready for migrations
- ✅ **Example User Model**: Created and tested
- ✅ **Health Checks**: Both database and Redis working

## Configuration

### Environment Variables

Copy `env_template.txt` to `.env` and configure:

```bash
cp env_template.txt .env
```

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

### Default Configuration

- **Database**: `postgresql+asyncpg://telegram_user:telegram_password@localhost:5432/telegram_game`
- **Redis**: `redis://localhost:6379/0`

## Database Operations

### Migrations

```bash
# Create a new migration
make db-migrate MSG="Add user table"

# Apply migrations
make db-upgrade

# Rollback one migration
make db-downgrade

# Reset database (drop and recreate all tables)
make db-reset
```

### Manual Alembic Commands

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Redis Operations

### Access Redis CLI

```bash
make redis-cli
```

### Common Redis Commands

```bash
# List all keys
KEYS *

# Get a value
GET key_name

# Set a value with expiration
SET key_name "value" EX 3600

# Delete a key
DEL key_name
```

## Code Usage

### Database Session Management

```python
from app.core.db import get_db_session, init_db

# Initialize database (call once at startup)
await init_db()

# Use database session
async with get_db_session() as session:
    # Your database operations here
    result = await session.execute(select(User))
    users = result.scalars().all()
```

### Redis Operations

```python
from app.core.redis import init_redis, set_cache, get_cache

# Initialize Redis (call once at startup)
await init_redis()

# Cache operations
await set_cache("user:123", {"name": "John"}, expire=3600)
user_data = await get_cache("user:123")

# Session management
await set_user_session(user_id, session_data)
session = await get_user_session(user_id)
```

## Project Structure

```
app/
├── core/
│   ├── config.py      # Configuration with Pydantic
│   ├── db.py          # SQLAlchemy setup
│   └── redis.py       # Redis setup
├── models/            # SQLAlchemy models
│   └── __init__.py
alembic/               # Database migrations
├── versions/          # Migration files
├── env.py            # Alembic environment
└── script.py.mako    # Migration template
docker-compose.yml    # Services configuration
alembic.ini          # Alembic configuration
init.sql             # Database initialization
```

## Services

### PostgreSQL

- **Port**: 5432
- **Database**: telegram_game
- **User**: telegram_user
- **Password**: telegram_password

### Redis

- **Port**: 6379
- **Database**: 0

### pgAdmin (Optional)

- **Port**: 8080
- **Email**: admin@example.com
- **Password**: admin

Access at: http://localhost:8080

## Health Checks

The system includes health check functions:

```python
from app.core.db import check_db_health
from app.core.redis import check_redis_health

# Check database health
db_healthy = await check_db_health()

# Check Redis health
redis_healthy = await check_redis_health()
```

## Troubleshooting

### Common Issues

1. **Connection refused**: Make sure Docker services are running
   ```bash
   make docker-up
   ```

2. **Migration errors**: Check if database is accessible
   ```bash
   make test-db
   ```

3. **Redis connection issues**: Verify Redis is running
   ```bash
   make test-redis
   ```

### Logs

```bash
# View service logs
make docker-logs

# View specific service logs
docker-compose logs postgres
docker-compose logs redis
```

### Reset Everything

```bash
# Stop services and remove volumes
docker-compose down -v

# Start fresh
make docker-up
make db-init
```

## Development Workflow

1. **Create a new model** in `app/models/`
2. **Generate migration**: `make db-migrate MSG="Add new model"`
3. **Apply migration**: `make db-upgrade`
4. **Test your changes**

## Production Considerations

- Use environment-specific configuration
- Set up proper backup strategies
- Configure connection pooling
- Monitor database and Redis performance
- Use SSL/TLS for connections in production
