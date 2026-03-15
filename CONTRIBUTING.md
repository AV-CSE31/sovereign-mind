# Contributing to Sovereign-Mind

Thank you for your interest in contributing to Sovereign-Mind.

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker (optional, for containerized development)

### Development Setup

```bash
# Clone the repository
git clone <repo-url>
cd sovereign-mind

# Set up Python environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install all dev dependencies
make dev

# Copy environment template
cp .env.example .env
```

This will install:
- Production dependencies
- Ruff (linter + formatter)
- mypy (type checker)
- pytest + coverage
- pre-commit hooks

### Running the Application

```bash
# Backend
make install
uvicorn app.main:app --reload

# Frontend
make ui-dev

# Docker (all services)
make docker-up
```

## Development Workflow

### Before Committing

Pre-commit hooks run automatically, but you can also run checks manually:

```bash
make lint        # Ruff linter
make format      # Ruff formatter
make typecheck   # mypy type checker
make test        # pytest with coverage
make ci          # All of the above
```

### Code Style

- **Python**: Enforced by Ruff (pycodestyle, pyflakes, isort, bugbear, bandit)
- **TypeScript**: Enforced by ESLint + TypeScript strict mode
- Line length: 100 characters
- Use type hints for all function signatures
- Follow existing patterns in the codebase

### Testing

```bash
make test          # All tests
make test-fast     # Skip slow tests
make test-cov      # Tests with HTML coverage report
make test-parallel # Parallel execution
```

When adding new features:
- Add unit tests in `tests/`
- Use descriptive test names: `test_vault_unlock_with_valid_passphrase`
- Use pytest fixtures for shared setup
- Mark slow tests with `@pytest.mark.slow`
- Mark integration tests with `@pytest.mark.integration`

### Project Structure

```
app/
  api/          # FastAPI routes
  core/         # Core logic (config, security, agent graph)
  middleware/   # Security middleware (rate limiting, auth, headers)
  models/       # Pydantic schemas
  services/     # Business logic (RAG, privacy, audit)
tests/          # pytest test suite
ui/             # Next.js frontend
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear, atomic commits
3. Ensure `make ci` passes
4. Open a PR with a clear description of the changes
5. Link any related issues

### Commit Messages

Use clear, descriptive commit messages:
- `feat: add rate limiting middleware`
- `fix: correct embedding URL for Llamafile`
- `docs: add CONTRIBUTING guide`
- `test: add vault encryption unit tests`
- `refactor: extract security middleware to separate module`

## Security

- Never commit secrets, API keys, or credentials
- Use `.env` for local configuration (gitignored)
- Follow fail-closed security philosophy
- PII must never appear in logs — use `hash_for_audit()`
- Report security vulnerabilities privately (do not open public issues)

## Architecture Decisions

Key design decisions are documented in `docs/adr/`. When making significant architectural changes, create a new ADR using the template in `docs/adr/template.md`.
