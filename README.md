# Sovereign-Mind

**Enterprise-Grade Private AI Assistant with Zero-Knowledge Storage**

A local-first AI backend combining military-grade privacy (Zero-Knowledge encryption) with agentic reasoning capabilities (System 2 Thinking). All data stays on your device by default — cloud bursting is optional and always anonymized.

[![CI](https://github.com/AV-CSE31/sovereign-mind/actions/workflows/ci.yml/badge.svg)](https://github.com/AV-CSE31/sovereign-mind/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Why Sovereign-Mind?

Most AI assistants send your data to the cloud. Sovereign-Mind takes a different approach:

- **Your data never leaves your device** unless you explicitly enable anonymized cloud mode
- **Zero-Knowledge encryption** — even if someone accesses your storage, they can't read your conversations
- **PII is auto-detected and stripped** before any cloud call, then rehydrated in the response
- **Full audit trail** with cryptographic hashes — compliance without content exposure
- **Agentic reasoning** — not just a chatbot, but an agent that plans, retrieves, grades, and refines

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI + Security Middleware                     │
│          (Rate Limiting · API Auth · CSP/HSTS Headers)               │
├─────────────────────────────────────────────────────────────────────┤
│  POST /v1/chat/completions    │    POST /v1/system/ingest            │
│  POST /v1/agent/run           │    GET  /v1/compliance/report        │
└──────────────┬────────────────┴────────────────┬─────────────────────┘
               │                                  │
               ▼                                  ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│   Module B: The Brain        │    │   Module C: SOTA RAG         │
│   (LangGraph Agent)          │    │   (Hybrid Retriever)         │
│   ┌─────────────────────┐    │    │   ┌─────────────────────┐    │
│   │  Supervisor (Intent) │    │    │   │  Dense (ChromaDB)   │    │
│   │  Planner → Retriever │    │    │   │  Sparse (BM25)      │    │
│   │  Grader → Generator  │    │    │   │  Fusion (RRF)       │    │
│   │  Memorize (Mem0)     │    │    │   │  Rerank (FlashRank) │    │
│   └─────────────────────┘    │    │   │  GraphRAG (NetworkX) │    │
│                              │    │   └─────────────────────┘    │
└──────────────────────────────┘    └──────────────────────────────┘
               │                                  │
               ▼                                  ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│   Module D: Privacy Guard    │    │   Module A: The Vault        │
│   (PII Anonymization)        │    │   (Encrypted Storage)        │
│   ┌─────────────────────┐    │    │   ┌─────────────────────┐    │
│   │  Presidio (13+ PII) │    │    │   │  Argon2id KDF       │    │
│   │  Fail-Closed Design  │    │    │   │  AES-256-GCM        │    │
│   │  Anonymize/Rehydrate │    │    │   │  Envelope Encryption│    │
│   └─────────────────────┘    │    │   │  SHA-256 Audit Chain │    │
└──────────────────────────────┘    └──────────────────────────────┘
```

---

## Features

### Zero-Knowledge Storage (Module A)
- **Argon2id** key derivation (OWASP-recommended, configurable time/memory/parallelism)
- **AES-256-GCM** envelope encryption — unique Data Encryption Key per session
- **SHA-256** tamper-evident audit logging (hashes only, never content)

### Agentic Reasoning (Module B)
- **LangGraph** state machine: Classify → Plan → Retrieve → Grade → Generate → Memorize
- Intent classification: Simple Chat, Complex Reasoning, RAG Search
- Automatic query rewriting when retrieval quality is low
- **Mem0** episodic long-term memory across sessions

### SOTA RAG Pipeline (Module C)
- **Dense Search**: ChromaDB with mxbai-embed-large embeddings
- **Sparse Search**: BM25 for exact keyword matching
- **Fusion**: Reciprocal Rank Fusion (parameter-free)
- **Reranking**: FlashRank cross-encoder for precision
- **GraphRAG**: Knowledge graph extraction + multi-hop traversal

### Privacy Gateway (Module D)
- **Presidio** PII detection (13+ entity types: names, emails, SSN, credit cards, etc.)
- **Fail-closed** philosophy: blocks requests when detection is uncertain
- **Stateful mapping**: anonymize before cloud LLM, rehydrate in response

### Security Middleware
- **Rate limiting** per IP (configurable, default 60/min)
- **Security headers**: CSP, HSTS, X-Frame-Options, X-XSS-Protection
- **API key authentication** (optional, for production deployments)
- **Request timing** headers for observability

### Compliance & Audit
- Cryptographic audit trail with Merkle chain integrity verification
- Compliance reports for EU AI Act / SOC 2
- Shadow AI scanner — detects unauthorized LLM processes on your network
- Zero-knowledge proof witness for audit verification

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, Uvicorn (ASGI) |
| **Agent** | LangGraph, LangChain, Mem0 |
| **RAG** | ChromaDB, BM25, FlashRank, NetworkX (GraphRAG) |
| **LLM** | Ollama (local, default: qwen2.5:7b), OpenAI (optional cloud) |
| **Encryption** | AES-256-GCM, Argon2id, cryptography lib |
| **Privacy** | Microsoft Presidio |
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4, TypeScript |
| **Tooling** | Ruff, mypy, pytest + coverage, pre-commit, GitHub Actions CI |
| **Deployment** | Docker Compose (3 services), Kubernetes-ready health probes |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+ (for frontend)
- [Ollama](https://ollama.ai/) installed and running

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/AV-CSE31/sovereign-mind.git
cd sovereign-mind

# Copy environment template
cp .env.example .env

# Pull required models
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large

# Start all services
docker compose up -d
```

Services will be available at:
- **Backend API**: http://localhost:8000
- **Custom UI**: http://localhost:3001
- **Open WebUI**: http://localhost:3000

### Option 2: Local Development

```bash
# Clone and setup
git clone https://github.com/AV-CSE31/sovereign-mind.git
cd sovereign-mind

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install all dependencies (backend + frontend + dev tools + pre-commit hooks)
make dev

# Copy environment template
cp .env.example .env

# Pull required models
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large

# Start backend
uvicorn app.main:app --reload

# In another terminal — start frontend
make ui-dev
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/v1/system/health

# Simple chat
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "config": {"mode": "local", "depth": "fast"}
  }'
```

---

## API Reference

### Chat & Agent

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | Chat (OpenAI-compatible format) |
| `/v1/agent/run` | POST | Execute agentic research pipeline |
| `/v1/agent/run/{run_id}` | GET | Get audit trail for a run |
| `/v1/models` | GET | List models (OpenAI-compatible) |

### Document Ingestion (RAG)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/system/ingest` | POST | Ingest document (PDF, TXT, or text) |
| `/v1/system/collection` | GET | RAG collection statistics |

### Vault (Encrypted Storage)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/vault/unlock` | POST | Unlock vault with passphrase |
| `/v1/vault/lock` | POST | Lock vault, clear keys from memory |
| `/v1/vault/sessions` | GET/POST | List or create encrypted sessions |
| `/v1/vault/sessions/{id}/messages` | GET | Retrieve decrypted messages |
| `/v1/vault/sessions/{id}` | DELETE | Delete encrypted session |

### Compliance & Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/compliance/logs` | GET | Audit logs with optional limit |
| `/v1/compliance/report` | GET | EU AI Act / SOC 2 compliance report |
| `/v1/compliance/verify` | GET | Merkle chain integrity verification |
| `/v1/system/shadow-scan` | GET | Scan for unauthorized AI processes |
| `/v1/system/health` | GET | Detailed health status |
| `/v1/system/liveness` | GET | Kubernetes liveness probe |
| `/v1/system/readiness` | GET | Kubernetes readiness probe |
| `/v1/system/memory/{user_id}` | GET | User memory profile (Mem0) |
| `/v1/system/traces` | GET | Execution traces |

---

## API Usage Examples

### Deep Reasoning Mode

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Compare renewable energy adoption strategies"}],
    "config": {"mode": "local", "depth": "deep_reasoning"}
  }'
```

### Ingest a Document

```bash
curl -X POST http://localhost:8000/v1/system/ingest \
  -F "file=@/path/to/document.pdf"
```

### Encrypted Chat Session

```bash
# Unlock vault
curl -X POST http://localhost:8000/v1/vault/unlock \
  -d "passphrase=your-secret-passphrase"

# Create encrypted session
curl -X POST http://localhost:8000/v1/vault/sessions

# Chat with encrypted history
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "This is a private conversation"}],
    "session_id": "<session-id-from-above>"
  }'
```

### Run Agentic Pipeline

```bash
curl -X POST http://localhost:8000/v1/agent/run \
  -d "query=Research the security implications of local LLMs"
```

---

## Project Structure

```
sovereign-mind/
├── app/                           # Backend application
│   ├── main.py                    #   FastAPI app with lifespan + graceful shutdown
│   ├── api/routes.py              #   All API endpoints
│   ├── core/                      #   Core logic
│   │   ├── config.py              #     Pydantic Settings (env validation)
│   │   ├── agent_graph.py         #     LangGraph state machine (The Brain)
│   │   ├── security.py            #     VaultManager (AES-256-GCM, Argon2id)
│   │   ├── memory.py              #     Mem0 episodic memory service
│   │   ├── exceptions.py          #     Custom exception hierarchy
│   │   └── logging.py             #     Structured logging with PII redaction
│   ├── middleware/security.py     #   Rate limiting, CSP headers, API auth
│   ├── models/schemas.py          #   Pydantic request/response models
│   └── services/                  #   Business logic
│       ├── rag_engine.py          #     Hybrid retriever (Dense+Sparse+RRF+Rerank)
│       ├── privacy_guard.py       #     Presidio PII anonymization
│       ├── knowledge_graph.py     #     GraphRAG with NetworkX
│       ├── audit_log.py           #     Merkle chain audit trail
│       ├── shadow_scanner.py      #     Unauthorized AI detection
│       └── zk_witness.py          #     Zero-knowledge proof witness
│
├── ui/                            # Next.js 16 frontend
│   ├── src/app/                   #   App Router pages
│   ├── src/components/            #   React components (Chat, Vault, Agents, etc.)
│   ├── playwright.config.ts       #   E2E testing config
│   └── Dockerfile                 #   Multi-stage production build
│
├── tests/                         # pytest test suite
│   ├── test_e2e.py                #   End-to-end API tests
│   ├── test_audit_integrity.py    #   Vault/encryption tests
│   ├── test_reflexion.py          #   Agent reflexion tests
│   └── ...                        #   Module-specific tests
│
├── scripts/                       # Utility scripts
│   ├── start_sovereign.sh         #   Linux launcher
│   ├── start_sovereign.ps1        #   Windows launcher
│   ├── download_model.py          #   Model downloader
│   └── debug/                     #   Debug & verification scripts
│
├── docs/                          # Documentation
│   ├── adr/                       #   Architecture Decision Records
│   └── internal/                  #   Strategy docs (pivot, market analysis)
│
├── .github/workflows/ci.yml      # CI: lint, typecheck, test, build, security
├── pyproject.toml                 # Python config (deps, Ruff, mypy, pytest)
├── Makefile                       # Dev commands (make dev, make ci, make test)
├── docker-compose.yml             # 3-service deployment
├── .pre-commit-config.yaml        # Pre-commit hooks
├── CONTRIBUTING.md                # Developer guide
├── CHANGELOG.md                   # Release history
└── LICENSE                        # MIT
```

---

## Development

```bash
# Install everything + pre-commit hooks
make dev

# Run full CI locally
make ci          # lint + typecheck + test

# Individual checks
make lint        # Ruff linter
make format      # Ruff formatter
make typecheck   # mypy
make test        # pytest with coverage
make test-fast   # skip slow tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development workflow.

---

## Security Model

### Local-First Default
- All processing runs on your device via Ollama
- No data leaves the device without explicit `cloud_secure` mode

### Fail-Closed Privacy
- PII detection uses strict thresholds (configurable, default 0.7)
- Uncertainty **blocks** requests rather than risking leakage
- Cloud mode requires successful anonymization pass

### Zero-Knowledge Audit
- All prompts/responses hashed with SHA-256
- Audit logs contain hashes only — compliance without content exposure
- Merkle chain integrity verification via `/v1/compliance/verify`

### Production Security
- Rate limiting per IP (default 60 req/min)
- Security headers: CSP, HSTS, X-Frame-Options
- Optional API key authentication
- Non-root Docker containers with resource limits

---

## Configuration

Key environment variables (see [`.env.example`](.env.example) for the full list):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `qwen2.5:7b` | Local LLM model |
| `EMBEDDING_MODEL` | `mxbai-embed-large` | Embedding model for RAG |
| `DEBUG` | `false` | Enable debug mode (exposes /docs) |
| `PII_DETECTION_THRESHOLD` | `0.7` | PII confidence threshold |
| `FINAL_TOP_K` | `5` | Documents returned to LLM |
| `API_KEY` | *(empty)* | Optional API key for production |
| `RATE_LIMIT` | `60/minute` | Rate limit per IP |
| `CHUNKING_STRATEGY` | `fixed` | `fixed` or `semantic` chunking |

---

## License

MIT License — See [LICENSE](LICENSE) for details.
