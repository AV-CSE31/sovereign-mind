.PHONY: help install dev lint format typecheck test test-cov test-fast ci clean docker docker-up docker-down ui-dev ui-build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Installation
# =============================================================================

install: ## Install production dependencies
	pip install -e .

dev: ## Install all dependencies (production + dev)
	pip install -e ".[dev]"
	cd ui && npm ci
	pre-commit install

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run linter (ruff)
	ruff check app/ tests/

format: ## Format code (ruff)
	ruff format app/ tests/
	ruff check --fix app/ tests/

typecheck: ## Run type checker (mypy)
	mypy app/

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests
	pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-report=html

test-fast: ## Run tests excluding slow tests
	pytest tests/ -v --tb=short -m "not slow"

test-parallel: ## Run tests in parallel
	pytest tests/ -v --tb=short -n auto

# =============================================================================
# CI (runs all checks)
# =============================================================================

ci: lint typecheck test ## Run full CI pipeline (lint + typecheck + test)

# =============================================================================
# Docker
# =============================================================================

docker: ## Build all Docker images
	docker compose build

docker-up: ## Start all services
	docker compose up -d

docker-down: ## Stop all services
	docker compose down

# =============================================================================
# Frontend
# =============================================================================

ui-dev: ## Start frontend dev server
	cd ui && npm run dev

ui-build: ## Build frontend for production
	cd ui && npm run build

ui-lint: ## Lint frontend code
	cd ui && npm run lint

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage
