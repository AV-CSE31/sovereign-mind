# ADR-002: Unified LLM Router (LiteLLM-Style Abstraction Layer)

**Status**: Proposed
**Date**: 2026-03-15
**Author**: Architecture Planning Session

---

## Context

Sovereign-Mind currently has LLM instantiation scattered across multiple files with no unified abstraction:

| Location | Current Pattern | Problem |
|----------|----------------|---------|
| `app/core/agent_graph.py` → `create_llm()` | Binary local/cloud switch via `ChatOllama` or `ChatOpenAI` | No fallback, no multi-provider routing |
| `app/services/knowledge_graph.py` → `GraphExtractor.__init__` | Hardcoded `ChatOllama(temperature=0.0)` | Independent instantiation, no shared config |
| `app/core/memory.py` → `Mem0Service.__init__` | Separate Mem0 config dict with provider/model | Completely disconnected from main LLM config |
| 7 agent nodes in `agent_graph.py` | Each calls `create_llm(state["local"])` | Redundant instantiation per node invocation |

### Pain Points

1. **No resilience** — If Ollama goes down, every request fails. No fallback to cloud or alternative local.
2. **Only 2 providers** — Ollama (local) and OpenAI (cloud). No Anthropic, vLLM, Groq, Together, Azure, etc.
3. **No cost awareness** — Cloud calls have no token tracking, cost estimation, or budget enforcement.
4. **No caching** — Identical prompts (e.g., intent classification) hit the LLM every time.
5. **No load balancing** — Can't distribute across multiple Ollama instances or multiple API keys.
6. **Privacy routing is ad-hoc** — The `local` boolean is passed through agent state; no centralized policy for which queries can go to cloud.

---

## Decision

Build a **`SovereignLLMRouter`** — a unified LLM abstraction layer inspired by LiteLLM's architecture but tailored to Sovereign-Mind's privacy-first requirements.

### Design Principles

1. **Privacy as a first-class routing constraint** — Unlike LiteLLM, routing decisions must consider PII content
2. **LangChain-compatible** — Must return `BaseChatModel` instances so existing LangGraph nodes work unchanged
3. **Local-first with graceful degradation** — Always prefer local, fall back to cloud only when explicitly allowed AND after anonymization
4. **Zero new external dependencies** — Build on top of existing `langchain-*` packages, not LiteLLM itself

---

## Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     SovereignLLMRouter                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ ProviderReg  │  │ RoutingEngine│  │ PrivacyGate           │  │
│  │              │  │              │  │                       │  │
│  │ • ollama     │  │ • strategy   │  │ • PII check           │  │
│  │ • openai     │  │ • fallback   │  │ • anonymize/rehydrate │  │
│  │ • anthropic  │  │ • cooldown   │  │ • fail-closed         │  │
│  │ • vllm       │  │ • health     │  │                       │  │
│  │ • groq       │  │              │  │                       │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘  │
│         │                 │                      │              │
│  ┌──────┴─────────────────┴──────────────────────┴───────────┐  │
│  │                    Unified Interface                       │  │
│  │  completion() / acompletion() / stream()                  │  │
│  │  → Returns LangChain BaseChatModel or ModelResponse       │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────┴────────────────────────────────┐  │
│  │                    Observability Layer                     │  │
│  │  • Token counting  • Cost tracking  • Latency metrics     │  │
│  │  • Response cache  • Audit logging  • Budget enforcement  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
app/
├── core/
│   └── llm/                          # NEW — Unified LLM layer
│       ├── __init__.py               #   Public API: get_router(), get_llm()
│       ├── router.py                 #   SovereignLLMRouter main class
│       ├── providers/                #   Provider adapters
│       │   ├── __init__.py
│       │   ├── base.py               #     Abstract LLMProvider
│       │   ├── ollama.py             #     OllamaProvider (local)
│       │   ├── openai.py             #     OpenAIProvider (cloud)
│       │   ├── anthropic.py          #     AnthropicProvider (cloud)
│       │   ├── vllm.py               #     vLLMProvider (local/remote)
│       │   └── groq.py               #     GroqProvider (cloud)
│       ├── routing.py                #   Routing strategies + fallback chains
│       ├── privacy_gate.py           #   PII-aware routing decisions
│       ├── cache.py                  #   Local-first response cache
│       ├── cost.py                   #   Token counting + cost tracking
│       └── models.py                 #   ModelResponse, ModelDeployment, etc.
```

---

## Detailed Design

### 1. Provider Registry

```python
# app/core/llm/providers/base.py

from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel

class LLMProvider(ABC):
    """Base class for all LLM providers."""

    name: str                    # "ollama", "openai", "anthropic", etc.
    is_local: bool               # True = no data leaves device
    supports_streaming: bool
    supports_function_calling: bool

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is reachable and ready."""
        ...

    @abstractmethod
    def get_chat_model(self, model: str, **kwargs) -> BaseChatModel:
        """Return a LangChain-compatible chat model instance."""
        ...

    @abstractmethod
    async def get_model_list(self) -> list[str]:
        """List available models from this provider."""
        ...

    def get_cost_per_token(self, model: str) -> tuple[float, float]:
        """Return (input_cost_per_1k, output_cost_per_1k). Default: (0, 0) for local."""
        return (0.0, 0.0)
```

```python
# app/core/llm/providers/ollama.py

class OllamaProvider(LLMProvider):
    name = "ollama"
    is_local = True
    supports_streaming = True
    supports_function_calling = False  # model-dependent

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    async def health_check(self) -> bool:
        # GET {base_url}/api/tags — if 200, healthy
        ...

    def get_chat_model(self, model: str, **kwargs) -> BaseChatModel:
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model, base_url=self.base_url, **kwargs)
```

### 2. Model Deployment Configuration

```python
# app/core/llm/models.py

from pydantic import BaseModel
from enum import Enum

class PrivacyTier(str, Enum):
    LOCAL_ONLY = "local_only"        # Never leaves device
    ANONYMIZED_CLOUD = "anon_cloud"  # PII stripped before sending
    TRUSTED_CLOUD = "trusted_cloud"  # Sent as-is (e.g., on-prem API)

class ModelDeployment(BaseModel):
    """A specific model on a specific provider."""
    deployment_id: str               # Unique ID: "ollama/qwen2.5:7b"
    provider: str                    # "ollama", "openai", etc.
    model: str                       # "qwen2.5:7b", "gpt-4o-mini", etc.
    privacy_tier: PrivacyTier        # Routing constraint
    priority: int = 0                # Lower = preferred (0 = primary)
    max_tokens: int = 4096
    temperature: float = 0.7
    rpm_limit: int | None = None     # Rate limit (requests per minute)
    tpm_limit: int | None = None     # Token limit (tokens per minute)
    enabled: bool = True

class ModelResponse(BaseModel):
    """Normalized response across all providers."""
    content: str
    model: str                       # Actual model used
    provider: str                    # Actual provider used
    deployment_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float                  # 0.0 for local models
    cached: bool = False
    privacy_tier: PrivacyTier
```

### 3. Router Configuration (YAML/TOML)

```toml
# In pyproject.toml or separate llm_config.toml

[tool.sovereign-mind.llm]
default_strategy = "privacy-first"   # or "lowest-latency", "lowest-cost"
cache_enabled = true
cache_ttl_seconds = 3600
monthly_budget_usd = 50.0

[[tool.sovereign-mind.llm.deployments]]
deployment_id = "local-primary"
provider = "ollama"
model = "qwen2.5:7b"
privacy_tier = "local_only"
priority = 0                         # Primary

[[tool.sovereign-mind.llm.deployments]]
deployment_id = "local-large"
provider = "ollama"
model = "llama3.1:70b"
privacy_tier = "local_only"
priority = 1                         # Fallback for complex tasks

[[tool.sovereign-mind.llm.deployments]]
deployment_id = "cloud-openai"
provider = "openai"
model = "gpt-4o-mini"
privacy_tier = "anonymized_cloud"
priority = 10                        # Only when local fails + PII stripped
rpm_limit = 60

[[tool.sovereign-mind.llm.deployments]]
deployment_id = "cloud-anthropic"
provider = "anthropic"
model = "claude-sonnet-4-6"
privacy_tier = "anonymized_cloud"
priority = 11                        # Fallback to OpenAI fallback
```

### 4. Routing Engine

```python
# app/core/llm/routing.py

class RoutingStrategy(str, Enum):
    PRIVACY_FIRST = "privacy-first"     # Local → anon cloud → error
    LOWEST_LATENCY = "lowest-latency"   # Fastest healthy deployment
    LOWEST_COST = "lowest-cost"         # Cheapest deployment ($0 for local)
    ROUND_ROBIN = "round-robin"         # Distribute across same-priority

class CooldownCache:
    """Track unhealthy deployments with exponential backoff."""
    # deployment_id → (cooldown_until, failure_count)
    # Initial cooldown: 10s, doubles each failure, max 5 minutes
    # Auto-removed after successful health check

class FallbackChain:
    """Multi-level fallback logic."""

    async def execute(self, messages, deployments, privacy_context):
        # Level 1: Try primary deployment (retry up to 2x with backoff)
        # Level 2: Try same-provider fallback (different model)
        # Level 3: Try cross-provider fallback (respecting privacy tier)
        # Level 4: Return structured error with attempted deployments
        ...
```

#### Privacy-First Routing Algorithm

```
1. Receive request with messages + privacy_mode (local/cloud_secure/auto)
2. If privacy_mode == "local":
   → Filter deployments to privacy_tier == LOCAL_ONLY
   → Route by strategy among local deployments
   → If all local fail → return error (never escalate to cloud)

3. If privacy_mode == "cloud_secure":
   → Run PII detection on messages via PrivacyGate
   → If PII detected → anonymize, set rehydration map
   → Filter to LOCAL_ONLY + ANONYMIZED_CLOUD deployments
   → Route by strategy
   → If response from cloud → rehydrate PII tokens
   → Return response

4. If privacy_mode == "auto":
   → Try LOCAL_ONLY first
   → If all local in cooldown AND query has no PII → try ANONYMIZED_CLOUD
   → If query has PII → anonymize first, then try ANONYMIZED_CLOUD
   → If all fail → return error
```

### 5. Privacy Gate Integration

```python
# app/core/llm/privacy_gate.py

class PrivacyGate:
    """Intercepts cloud-bound requests to enforce PII anonymization."""

    def __init__(self, privacy_guard: PrivacyGuard):
        self.guard = privacy_guard  # Existing Presidio-based service

    async def process_outbound(
        self, messages: list[dict], deployment: ModelDeployment
    ) -> tuple[list[dict], dict | None]:
        """
        If deployment requires anonymization:
        1. Run PII detection on all message content
        2. If PII found → anonymize, return (clean_messages, rehydration_map)
        3. If PII detection fails → BLOCK (fail-closed)
        4. If deployment is local → pass through unchanged
        """
        if deployment.privacy_tier == PrivacyTier.LOCAL_ONLY:
            return messages, None

        # Anonymize each message's content
        rehydration_map = {}
        clean_messages = []
        for msg in messages:
            clean_text, mapping = await self.guard.anonymize(msg["content"])
            clean_messages.append({**msg, "content": clean_text})
            rehydration_map.update(mapping)

        return clean_messages, rehydration_map

    async def process_inbound(
        self, response: str, rehydration_map: dict | None
    ) -> str:
        """Rehydrate PII tokens in the response."""
        if not rehydration_map:
            return response
        return self.guard.rehydrate(response, rehydration_map)
```

### 6. Response Cache

```python
# app/core/llm/cache.py

class SovereignCache:
    """Privacy-respecting local-first cache."""

    # DESIGN DECISIONS:
    # - Cache stored locally only (never cloud-based Redis)
    # - Cache key = SHA-256(model + sorted messages + temperature)
    # - PII content is NEVER cached (detected at cache-write time)
    # - TTL-based expiry (default 1 hour)
    # - Max cache size: configurable (default 1000 entries, LRU eviction)
    # - Separate cache namespace per deployment

    # TWO-TIER ARCHITECTURE:
    # Tier 1: In-memory dict (fast, lost on restart, ~100 entries)
    # Tier 2: SQLite file in data/cache/ (persistent, ~1000 entries)
    # No Redis — stays local-first
```

### 7. Cost & Token Tracking

```python
# app/core/llm/cost.py

class CostTracker:
    """Track token usage and costs across all providers."""

    # Per-request: log (deployment_id, input_tokens, output_tokens, cost_usd, timestamp)
    # Aggregated: daily/monthly rollups per provider and per model
    # Budget enforcement: if monthly_budget_usd exceeded, block cloud deployments
    # Storage: append-only SQLite in data/cost_tracking.db

    # Token counting strategy:
    # - OpenAI/Anthropic: use response.usage from API
    # - Ollama: use response.eval_count / response.prompt_eval_count
    # - Fallback: tiktoken estimate for prompt, actual count from response

    # PRICING TABLE (updateable):
    PRICING = {
        "gpt-4o-mini": (0.15, 0.60),       # per 1M tokens (input, output)
        "gpt-4o": (2.50, 10.00),
        "claude-sonnet-4-6": (3.00, 15.00),
        "claude-haiku-4-5": (0.80, 4.00),
        # Local models: all (0, 0)
    }
```

### 8. Main Router Class

```python
# app/core/llm/router.py

class SovereignLLMRouter:
    """Unified LLM interface for Sovereign-Mind."""

    def __init__(self, settings: Settings):
        self.providers: dict[str, LLMProvider] = {}
        self.deployments: list[ModelDeployment] = []
        self.routing = RoutingEngine(strategy=settings.llm_routing_strategy)
        self.privacy_gate = PrivacyGate(privacy_guard)
        self.cache = SovereignCache()
        self.cost_tracker = CostTracker()
        self.cooldowns = CooldownCache()

    def register_provider(self, provider: LLMProvider) -> None:
        """Register a new provider (called during app startup)."""
        self.providers[provider.name] = provider

    def get_langchain_model(
        self,
        purpose: str = "general",    # "general", "classification", "extraction", "embedding"
        privacy_mode: str = "local",
        temperature: float | None = None,
    ) -> BaseChatModel:
        """
        Return a LangChain-compatible model for use in LangGraph nodes.
        This is the PRIMARY interface for existing code migration.
        """
        # Select deployment based on purpose + privacy_mode + strategy
        # Wrap in a TrackedChatModel that reports tokens/cost
        ...

    async def acompletion(
        self,
        messages: list[dict],
        privacy_mode: str = "local",
        **kwargs,
    ) -> ModelResponse:
        """
        Direct completion (non-LangChain path).
        Handles: privacy gate → routing → fallback → caching → cost tracking
        """
        ...

    async def astream(
        self,
        messages: list[dict],
        privacy_mode: str = "local",
        **kwargs,
    ) -> AsyncIterator[str]:
        """Streaming completion with same routing logic."""
        ...

    async def health(self) -> dict:
        """Health status of all providers and deployments."""
        return {
            d.deployment_id: {
                "healthy": d.deployment_id not in self.cooldowns,
                "provider": d.provider,
                "model": d.model,
                "privacy_tier": d.privacy_tier,
            }
            for d in self.deployments
        }
```

### 9. LangChain Integration Wrapper

```python
# Wrapper that makes the router behave like a BaseChatModel

class TrackedChatModel(BaseChatModel):
    """
    Wraps any LangChain chat model to add:
    - Automatic token counting
    - Cost tracking
    - Latency measurement
    - Audit logging
    - Fallback to next deployment on failure
    """

    def _generate(self, messages, stop=None, **kwargs):
        start = time.perf_counter()
        try:
            result = self.inner_model._generate(messages, stop, **kwargs)
            latency = (time.perf_counter() - start) * 1000
            self.router.cost_tracker.record(...)
            return result
        except Exception:
            self.router.cooldowns.add(self.deployment_id)
            # Try next deployment in fallback chain
            ...
```

---

## Migration Plan

### Phase 1: Foundation (Non-Breaking)

Create `app/core/llm/` module with `SovereignLLMRouter`, `OllamaProvider`, and `OpenAIProvider`. Wire it into app startup via lifespan. **Do not modify any existing code yet.**

```python
# app/main.py lifespan addition
router = SovereignLLMRouter(settings)
router.register_provider(OllamaProvider(settings.ollama_base_url))
if settings.openai_api_key:
    router.register_provider(OpenAIProvider(settings.openai_api_key))
app.state.llm_router = router
```

### Phase 2: Replace `create_llm()` (Minimal Breaking Change)

Replace the `create_llm()` function in `agent_graph.py` to delegate to the router:

```python
# BEFORE (agent_graph.py)
def create_llm(local: bool = True):
    settings = get_settings()
    if local:
        return ChatOllama(model=settings.ollama_model, ...)
    else:
        return ChatOpenAI(model=settings.openai_model, ...)

# AFTER
def create_llm(local: bool = True) -> BaseChatModel:
    router = get_llm_router()  # Singleton from app state
    privacy_mode = "local" if local else "cloud_secure"
    return router.get_langchain_model(privacy_mode=privacy_mode)
```

This single change gives all 7 agent nodes: fallback, health checking, cost tracking — **zero changes to node code**.

### Phase 3: Unify Knowledge Graph & Memory

```python
# BEFORE (knowledge_graph.py)
class GraphExtractor:
    def __init__(self):
        self.llm = ChatOllama(model=settings.ollama_model, temperature=0.0)

# AFTER
class GraphExtractor:
    def __init__(self, router: SovereignLLMRouter):
        self.llm = router.get_langchain_model(
            purpose="extraction", temperature=0.0
        )
```

```python
# BEFORE (memory.py)
self.config = {
    "llm": {"provider": "ollama", "config": {"model": settings.ollama_model}},
    ...
}

# AFTER — Mem0 still needs its own config format, but source from router
deployment = router.get_deployment_for(purpose="memory")
self.config = {
    "llm": {"provider": deployment.provider, "config": {"model": deployment.model}},
    ...
}
```

### Phase 4: Add New Providers

Add `AnthropicProvider`, `GroqProvider`, `vLLMProvider` etc. Each is ~50 lines implementing the `LLMProvider` interface. No core changes needed.

### Phase 5: Advanced Features

- Response caching (SQLite-backed)
- Cost tracking dashboard endpoint (`GET /v1/system/llm/costs`)
- Budget enforcement
- Latency-based routing
- Model health dashboard (`GET /v1/system/llm/health`)

---

## Configuration Changes

### New Settings in `app/core/config.py`

```python
# LLM Router settings
llm_routing_strategy: Literal["privacy-first", "lowest-latency", "lowest-cost"] = "privacy-first"
llm_cache_enabled: bool = True
llm_cache_ttl: int = 3600
llm_monthly_budget_usd: float = 50.0
llm_fallback_enabled: bool = True
llm_cooldown_initial_seconds: int = 10
llm_cooldown_max_seconds: int = 300

# Additional provider configs (optional)
anthropic_api_key: str | None = None
groq_api_key: str | None = None
vllm_base_url: str | None = None
```

### New API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/system/llm/health` | GET | Health status of all LLM deployments |
| `/v1/system/llm/costs` | GET | Token usage and cost summary |
| `/v1/system/llm/models` | GET | Available models across all providers |
| `/v1/system/llm/config` | GET | Current routing configuration (redacted keys) |

---

## Key Differentiators vs. LiteLLM

| Aspect | LiteLLM | SovereignLLMRouter |
|--------|---------|-------------------|
| **Privacy** | No PII awareness | PII detection + anonymization baked into routing |
| **Fail-closed** | Retries, then error | Blocks cloud if PII detection uncertain |
| **Caching** | Redis (cloud) | SQLite (local-first, privacy-respecting) |
| **Cost storage** | External DB / hosted | Local SQLite (sovereign data) |
| **LangChain** | Separate integration | Native LangChain `BaseChatModel` returns |
| **Dependencies** | `litellm` package (heavy) | Zero new deps — uses existing `langchain-*` |
| **Scope** | 100+ providers | 5-6 providers (focused, maintained) |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Increased complexity in LLM path | Higher latency, harder debugging | Keep router code minimal; extensive tracing via structlog |
| Cache poisoning (wrong response served) | Incorrect answers | Cache key includes full message history + model + temp; PII content never cached |
| Cost tracking drift | Budget overspend | Conservative estimates; alerts at 80% budget |
| Mem0 config incompatibility | Memory service breaks | Phase 3 is opt-in; Mem0 keeps its own config format, just sourced from router |
| Provider API changes | Adapter breaks | Each provider is isolated; tests per provider; version-pinned deps |

---

## Estimated Effort

| Phase | Scope | Complexity |
|-------|-------|------------|
| Phase 1: Foundation | Router + 2 providers + routing engine | Medium |
| Phase 2: Replace create_llm() | 1 function change + tests | Low |
| Phase 3: Unify KG + Memory | 2 file changes + tests | Low |
| Phase 4: New providers | ~50 LOC per provider | Low each |
| Phase 5: Cache + cost + dashboards | Cache, cost tracker, 4 endpoints | Medium |

**Total new code estimate**: ~800-1200 lines (excluding tests)
**Test coverage target**: 90%+ for router, routing, privacy gate

---

## Decision Outcome

Proceed with this architecture. The phased approach ensures:
- **Phase 1-2 delivers immediate value** (fallback + health checking) with minimal risk
- **Phase 3 eliminates code duplication** across the codebase
- **Phase 4-5 are additive** — can be built incrementally based on actual usage patterns
- **Zero breaking changes** to the LangGraph agent pipeline — nodes continue calling `create_llm()` unchanged

The privacy-first routing constraint is the key differentiator that justifies building this in-house rather than adopting LiteLLM as a dependency.
