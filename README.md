# Sovereign-Mind 🧠

**Enterprise-Grade Private AI Assistant with Zero-Knowledge Storage**

A local-first AI backend combining military-grade privacy (Zero-Knowledge encryption) with agentic reasoning capabilities (System 2 Thinking), defaulting to local execution but allowing controlled, anonymized cloud bursting.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
├─────────────────────────────────────────────────────────────────┤
│  POST /v1/chat/completions    │    POST /v1/system/ingest       │
└──────────────┬────────────────┴────────────────┬────────────────┘
               │                                  │
               ▼                                  ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│   Module B: The Brain        │    │   Module C: SOTA RAG         │
│   (LangGraph Agent)          │    │   (Hybrid Retriever)         │
│   ┌─────────────────────┐    │    │   ┌─────────────────────┐    │
│   │     Supervisor      │    │    │   │  Dense (ChromaDB)   │    │
│   │   (Intent Classify) │    │    │   │  Sparse (BM25)      │    │
│   └──────────┬──────────┘    │    │   │  RRF Fusion         │    │
│              ▼               │    │   │  Rerank (FlashRank) │    │
│   ┌──────────────────┐       │    │   └─────────────────────┘    │
│   │ Planner/Retriever│◄──────┼────┤                              │
│   │ Grader/Generator │       │    └──────────────────────────────┘
│   └──────────────────┘       │
└──────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│   Module D: Privacy Guard    │    │   Module A: The Vault        │
│   (PII Anonymization)        │    │   (Encrypted Storage)        │
│   ┌─────────────────────┐    │    │   ┌─────────────────────┐    │
│   │  Presidio Detect    │    │    │   │  Argon2 Key Derive  │    │
│   │  Stateful Mapping   │    │    │   │  AES-256-GCM        │    │
│   │  Anonymize/Rehydrate│    │    │   │  Envelope Encryption│    │
│   └─────────────────────┘    │    │   └─────────────────────┘    │
└──────────────────────────────┘    └──────────────────────────────┘
```

## ✨ Features

### 🔒 Zero-Knowledge Storage (Module A)
- **Argon2id** key derivation from user passphrase
- **AES-256-GCM** envelope encryption (unique DEK per session)
- **SHA-256** audit logging (hashes only, never content)

### 🧠 Agentic Reasoning (Module B)
- **LangGraph** state machine with Plan-Execute-Grade-Refine loop
- Intent classification: Simple Chat, Complex Reasoning, RAG Search
- Automatic query rewriting with grading threshold (0.7)

### 📚 SOTA RAG (Module C)
- **Dense Search**: ChromaDB with local embeddings (nomic-embed-text)
- **Sparse Search**: BM25 for exact keyword matches
- **Fusion**: Reciprocal Rank Fusion (RRF)
- **Reranking**: FlashRank (MiniLM-L-12-v2)

### 🛡️ Privacy Gateway (Module D)
- **Presidio** PII detection (13+ entity types)
- **Fail-closed** philosophy: block on uncertainty
- **Stateful mapping**: anonymize → cloud LLM → rehydrate

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.ai/) installed and running
- Pull required models:
  ```bash
  ollama pull llama3.2:latest
  ollama pull nomic-embed-text
  ```

### Installation

```bash
# Clone and enter directory
cd sovereign-mind

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Run the application
python -m uvicorn app.main:app --reload
```

### API Usage

#### Chat Completion (Local Mode)
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is quantum computing?"}],
    "config": {"mode": "local", "depth": "fast"}
  }'
```

#### Deep Reasoning Mode
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Compare renewable energy adoption in Germany vs USA"}],
    "config": {"mode": "local", "depth": "deep_reasoning"}
  }'
```

#### Ingest Document
```bash
curl -X POST http://localhost:8000/v1/system/ingest \
  -F "file=@/path/to/document.pdf"
```

#### Vault Operations
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
    "messages": [{"role": "user", "content": "Hello!"}],
    "session_id": "your-session-id"
  }'
```

## 📁 Project Structure

```
sovereign-mind/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Pydantic settings
│   │   ├── exceptions.py    # Custom exceptions
│   │   ├── logging.py       # Structured logging
│   │   ├── security.py      # Module A: VaultManager
│   │   └── agent_graph.py   # Module B: LangGraph agent
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic models
│   └── services/
│       ├── __init__.py
│       ├── rag_engine.py    # Module C: HybridRetriever
│       └── privacy_guard.py # Module D: AnonymizationService
├── data/                    # Persistent storage (gitignored)
│   ├── vault/              # Encrypted sessions
│   ├── chroma/             # Vector database
│   └── audit/              # Audit logs
├── requirements.txt
├── .env.example
└── README.md
```

## 🔐 Security Model

### Local-First Default
- 90%+ workloads run locally via Ollama
- No data leaves device without explicit `cloud_secure` mode

### Fail-Closed Privacy
- PII detection uses strict thresholds
- Uncertainty blocks requests (doesn't leak)
- Cloud mode requires anonymization pass

### Zero-Knowledge Audit
- All prompts/responses hashed with SHA-256
- Audit logs contain hashes only
- Compliance without content exposure

## ⚙️ Configuration

Key environment variables (see `.env.example` for all):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.2:latest` | Local LLM model |
| `DEBUG` | `false` | Enable debug mode |
| `PII_DETECTION_THRESHOLD` | `0.7` | PII confidence threshold |
| `GRADER_RELEVANCE_THRESHOLD` | `0.7` | RAG grading threshold |
| `FINAL_TOP_K` | `5` | Documents returned to LLM |

## 📊 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | Chat with AI assistant |
| `/v1/system/ingest` | POST | Ingest document to RAG |
| `/v1/system/collection` | GET | Get RAG statistics |
| `/v1/system/health` | GET | Health check |
| `/v1/vault/unlock` | POST | Unlock vault |
| `/v1/vault/lock` | POST | Lock vault |
| `/v1/vault/sessions` | GET/POST | List/create sessions |
| `/v1/vault/sessions/{id}/messages` | GET | Get session messages |

## 📝 License

MIT License - See LICENSE file for details.
