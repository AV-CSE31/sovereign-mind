# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `pyproject.toml` with modern Python project configuration (PEP 621)
- Ruff linter and formatter configuration
- mypy type checking configuration
- pytest-cov for code coverage tracking with 50% minimum threshold
- Pre-commit hooks (Ruff, mypy, trailing whitespace, secret detection)
- GitHub Actions CI/CD pipeline (lint, typecheck, test, frontend, Docker, security)
- Makefile with common development commands
- Rate limiting middleware (slowapi)
- Security headers middleware (CSP, HSTS, X-Frame-Options, etc.)
- API key authentication middleware (optional, for production)
- Request timing middleware for observability
- Readiness and liveness health probe endpoints
- Graceful shutdown with signal handling
- React Error Boundary component for frontend resilience
- Prettier configuration for frontend code formatting
- Playwright configuration for E2E frontend testing
- MIT LICENSE file
- CONTRIBUTING.md with development workflow guide
- CHANGELOG.md (this file)
- Architecture Decision Records template (`docs/adr/`)
- SOTA analysis document (`SOTA_ANALYSIS.md`)

### Changed
- Upgraded default local model from TinyLlama-1.1B to `qwen2.5:7b` for reliable agentic reasoning
- Upgraded default embedding model from `nomic-embed-text` to `mxbai-embed-large`
- Added semantic chunking configuration options to Settings
- Improved CORS configuration with explicit origin allowlisting
- Enhanced Docker Compose with resource limits and restart policies
- Updated Dockerfile to use `pyproject.toml` for dependency installation
- Improved `.gitignore` with coverage, Ruff, mypy, and Playwright artifacts

### Fixed
- Missing LICENSE file (referenced in README but not present)
- Duplicate import of `get_retriever` in routes.py
- Bare `except` clause in trace endpoint

## [0.1.0] - 2024-12-01

### Added
- Initial release
- Zero-Knowledge Vault with Argon2id + AES-256-GCM envelope encryption
- LangGraph agentic reasoning with Plan-Execute-Grade-Refine loop
- Hybrid RAG pipeline (Dense + Sparse + RRF + FlashRank reranking)
- GraphRAG with knowledge graph extraction
- Mem0 episodic memory integration
- Presidio PII anonymization with fail-closed design
- Privacy Guard with stateful anonymize/rehydrate
- FastAPI backend with OpenAI-compatible API
- Next.js 16 frontend with React 19
- Docker Compose multi-service deployment
- Shadow AI scanner
- Compliance audit logging with SHA-256 hashing
- Zero-knowledge proof witness
- MCP (Model Context Protocol) integration
