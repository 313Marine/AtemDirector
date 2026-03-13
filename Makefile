.PHONY: help dev test lint format clean install-dev db-init db-migrate

help:
	@echo "ATEM Director - Development Commands"
	@echo ""
	@echo "dev              Run development server with auto-reload"
	@echo "test             Run all tests"
	@echo "test-cov         Run tests with coverage report"
	@echo "lint             Run code linting (ruff, mypy)"
	@echo "format           Format code (black, isort)"
	@echo "clean            Clean build artifacts and cache"
	@echo "install-dev      Install development dependencies"
	@echo "db-init          Initialize database"
	@echo "db-migrate       Run database migrations"
	@echo ""

dev:
	python -m atem_director.main

test:
	pytest

test-cov:
	pytest --cov=src/atem_director --cov-report=html

lint:
	ruff check src/ tests/
	mypy src/atem_director

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ htmlcov/
	rm -rf .coverage

install-dev:
	pip install -e ".[dev]"

db-init:
	python -c "from atem_director.persistence.models import Base; print('Database models defined')"

db-migrate:
	alembic upgrade head
