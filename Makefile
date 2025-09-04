.PHONY: install-dev precommit-install format format-check lint typecheck fix check clean
.PHONY: docker-up docker-down docker-logs db-init db-migrate db-upgrade db-downgrade db-reset
.PHONY: redis-cli test-db test-redis

VENV ?= .venv
PYTHON ?= python3

# Development setup
install-dev:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -r requirements-dev.txt

precommit-install:
	pre-commit install

# Code formatting and linting
format:
	black .
	isort .

format-check:
	black --check .
	isort --check-only .

lint:
	ruff check .

typecheck:
	mypy app

fix:
	ruff check --fix .
	black .
	isort .

check: format-check lint typecheck

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

# Application
run:
	${PYTHON} run_bot.py

# Docker services
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Database operations
db-init:
	alembic upgrade head

db-migrate:
	alembic revision --autogenerate -m "$(MSG)"

db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-reset:
	alembic downgrade base
	alembic upgrade head

# Redis operations
redis-cli:
	docker-compose exec redis redis-cli

# Testing connections
test-db:
	${PYTHON} -c "import asyncio; from app.core.db import init_db, check_db_health; asyncio.run(init_db()); print('DB Health:', asyncio.run(check_db_health()))"

test-redis:
	${PYTHON} -c "import asyncio; from app.core.redis import init_redis, check_redis_health; asyncio.run(init_redis()); print('Redis Health:', asyncio.run(check_redis_health()))"
