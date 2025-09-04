.PHONY: install-dev precommit-install format format-check lint typecheck fix check clean

VENV ?= .venv
PYTHON ?= python3

install-dev:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -r requirements-dev.txt

precommit-install:
	pre-commit install

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

run:
	${PYTHON} run_bot.py
