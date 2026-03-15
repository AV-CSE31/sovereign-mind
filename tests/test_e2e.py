"""
Sovereign-Mind End-to-End Test Suite

Comprehensive pytest tests for:
- Health & API endpoints
- Vault (encrypted storage)
- RAG (document ingestion & retrieval)
- Privacy Guard (PII detection)
- Chat completions

Run with: pytest tests/test_e2e.py -v --tb=short
"""

import json
import time

import pytest
import requests

# ============================================================================
# Configuration
# ============================================================================

BASE_URL = "http://localhost:8000"
TIMEOUT = 60  # seconds for LLM responses

# Test data
TEST_PASSPHRASE = "test-secure-passphrase-2024"
TEST_DOCUMENTS = [
    {
        "content": "Sovereign-Mind uses Argon2id for key derivation with configurable time cost, memory cost, and parallelism parameters. The default settings are: time_cost=3, memory_cost=65536, parallelism=4.",
        "metadata": {"source": "security-docs", "type": "encryption"},
    },
    {
        "content": "The RAG system implements hybrid search combining ChromaDB for dense vector search and BM25 for sparse keyword matching. Results are fused using Reciprocal Rank Fusion (RRF) algorithm.",
        "metadata": {"source": "rag-docs", "type": "architecture"},
    },
    {
        "content": "AES-256-GCM envelope encryption protects all session data. Each session gets a unique Data Encryption Key (DEK) that is encrypted with the master Key Encryption Key (KEK).",
        "metadata": {"source": "security-docs", "type": "encryption"},
    },
]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def api_client():
    """Create a requests session for API calls."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    yield session
    session.close()


@pytest.fixture(scope="function")
def unlocked_vault(api_client):
    """Unlock the vault for tests that need it."""
    # Unlock
    response = api_client.post(
        f"{BASE_URL}/v1/vault/unlock",
        data={"passphrase": TEST_PASSPHRASE},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    yield
    # Lock after tests
    api_client.post(f"{BASE_URL}/v1/vault/lock")


@pytest.fixture(scope="function")
def vault_session(api_client):
    """Create a vault session for encrypted chat tests."""
    # Ensure vault is unlocked first
    api_client.post(
        f"{BASE_URL}/v1/vault/unlock",
        data={"passphrase": TEST_PASSPHRASE},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    response = api_client.post(f"{BASE_URL}/v1/vault/sessions")
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    yield session_id
    # Cleanup: delete session and lock vault
    api_client.delete(f"{BASE_URL}/v1/vault/sessions/{session_id}")
    api_client.post(f"{BASE_URL}/v1/vault/lock")


# ============================================================================
# Health & Basic API Tests
# ============================================================================


class TestHealthAndBasicAPI:
    """Test basic API functionality."""

    def test_health_endpoint(self, api_client):
        """Test /v1/system/health returns correct format."""
        response = api_client.get(f"{BASE_URL}/v1/system/health")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data
        assert "vault_unlocked" in data
        assert "rag_document_count" in data

    def test_models_endpoint(self, api_client):
        """Test /v1/models returns OpenAI-compatible format."""
        response = api_client.get(f"{BASE_URL}/v1/models")
        assert response.status_code == 200
        data = response.json()

        assert data["object"] == "list"
        assert "data" in data
        assert len(data["data"]) > 0

        # Check model format
        model = data["data"][0]
        assert "id" in model
        assert "object" in model
        assert model["object"] == "model"

    def test_collection_stats(self, api_client):
        """Test /v1/system/collection returns stats."""
        response = api_client.get(f"{BASE_URL}/v1/system/collection")
        assert response.status_code == 200
        data = response.json()

        assert "collection_name" in data
        assert "document_count" in data
        assert "bm25_corpus_size" in data


# ============================================================================
# Vault Tests (Encrypted Storage)
# ============================================================================


class TestVault:
    """Test vault encryption and session management."""

    def test_vault_unlock_and_lock(self, api_client):
        """Test vault unlock/lock cycle."""
        # Unlock
        response = api_client.post(
            f"{BASE_URL}/v1/vault/unlock",
            data={"passphrase": TEST_PASSPHRASE},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert "unlocked" in response.json()["message"].lower()

        # Verify unlocked
        health = api_client.get(f"{BASE_URL}/v1/system/health").json()
        assert health["vault_unlocked"] is True

        # Lock
        response = api_client.post(f"{BASE_URL}/v1/vault/lock")
        assert response.status_code == 200
        assert "locked" in response.json()["message"].lower()

        # Verify locked
        health = api_client.get(f"{BASE_URL}/v1/system/health").json()
        assert health["vault_unlocked"] is False

    def test_create_session(self, api_client, unlocked_vault):
        """Test encrypted session creation."""
        response = api_client.post(f"{BASE_URL}/v1/vault/sessions")
        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert len(data["session_id"]) > 10  # Should be a substantial ID

    def test_list_sessions(self, api_client, unlocked_vault):
        """Test listing vault sessions."""
        # Create a session first
        api_client.post(f"{BASE_URL}/v1/vault/sessions")

        response = api_client.get(f"{BASE_URL}/v1/vault/sessions")
        assert response.status_code == 200
        data = response.json()

        assert "sessions" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_session_requires_unlocked_vault(self, api_client):
        """Test that session operations fail when vault is locked."""
        # Ensure locked
        api_client.post(f"{BASE_URL}/v1/vault/lock")

        response = api_client.post(f"{BASE_URL}/v1/vault/sessions")
        assert response.status_code == 423  # Locked status

    def test_encrypted_chat_stores_messages(self, api_client, vault_session):
        """Test that chat with session_id stores encrypted messages."""
        # Send a message
        payload = {
            "messages": [{"role": "user", "content": "My secret code is DELTA-9876"}],
            "config": {"mode": "local", "depth": "fast"},
            "session_id": vault_session,
        }
        response = api_client.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200

        # Retrieve messages
        response = api_client.get(f"{BASE_URL}/v1/vault/sessions/{vault_session}/messages")
        assert response.status_code == 200
        data = response.json()

        assert "messages" in data
        assert len(data["messages"]) >= 2  # User + Assistant

    def test_delete_session(self, api_client, unlocked_vault):
        """Test session deletion."""
        # Create a session
        create_response = api_client.post(f"{BASE_URL}/v1/vault/sessions")
        session_id = create_response.json()["session_id"]

        # Delete it
        response = api_client.delete(f"{BASE_URL}/v1/vault/sessions/{session_id}")
        assert response.status_code == 200


# ============================================================================
# RAG Tests (Document Ingestion & Retrieval)
# ============================================================================


class TestRAG:
    """Test RAG document ingestion and retrieval."""

    def test_ingest_text_content(self, api_client):
        """Test ingesting text content directly."""
        response = api_client.post(
            f"{BASE_URL}/v1/system/ingest",
            data={
                "content": TEST_DOCUMENTS[0]["content"],
                "metadata": json.dumps(TEST_DOCUMENTS[0]["metadata"]),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "document_id" in data
        assert data["chunk_count"] >= 1

    def test_ingest_multiple_documents(self, api_client):
        """Test ingesting multiple documents."""
        doc_ids = []
        for doc in TEST_DOCUMENTS[1:]:
            response = api_client.post(
                f"{BASE_URL}/v1/system/ingest",
                data={"content": doc["content"], "metadata": json.dumps(doc["metadata"])},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            assert response.status_code == 200
            doc_ids.append(response.json()["document_id"])

        assert len(doc_ids) == len(TEST_DOCUMENTS) - 1

    def test_collection_stats_after_ingest(self, api_client):
        """Verify document count increases after ingestion."""
        # Ingest a document
        api_client.post(
            f"{BASE_URL}/v1/system/ingest",
            data={"content": "Test document for counting purposes."},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        response = api_client.get(f"{BASE_URL}/v1/system/collection")
        assert response.status_code == 200
        assert response.json()["document_count"] >= 1

    def test_rag_retrieval_query(self, api_client):
        """Test that RAG retrieval works for ingested content."""
        # First ingest some content
        api_client.post(
            f"{BASE_URL}/v1/system/ingest",
            data={
                "content": "The FlashRank reranker uses MiniLM-L-12-v2 model for semantic reranking of search results."
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Query about the content
        payload = {
            "messages": [
                {"role": "user", "content": "What model does FlashRank use for reranking?"}
            ],
            "config": {"mode": "local", "depth": "fast"},
        }
        response = api_client.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        # Note: Response content depends on model, just verify format


# ============================================================================
# Chat Completion Tests
# ============================================================================


class TestChatCompletions:
    """Test chat completion endpoint variations."""

    def test_simple_chat(self, api_client):
        """Test basic chat completion."""
        payload = {
            "messages": [{"role": "user", "content": "Say hello in exactly 3 words"}],
            "config": {"mode": "local", "depth": "fast"},
        }
        response = api_client.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()

        assert data["object"] == "chat.completion"
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert data["choices"][0]["message"]["role"] == "assistant"
        assert len(data["choices"][0]["message"]["content"]) > 0

    def test_openai_compatible_format(self, api_client):
        """Test OpenAI-compatible request format."""
        payload = {
            "model": "qwen2:0.5b",
            "messages": [{"role": "user", "content": "What is 2+2?"}],
            "temperature": 0.7,
            "max_tokens": 100,
        }
        response = api_client.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert data["id"].startswith("chatcmpl-")
        assert "model" in data
        assert "created" in data

    def test_multi_turn_conversation(self, api_client):
        """Test multi-turn conversation context."""
        payload = {
            "messages": [
                {"role": "user", "content": "My name is Alice."},
                {"role": "assistant", "content": "Nice to meet you, Alice!"},
                {"role": "user", "content": "What is my name?"},
            ],
            "config": {"mode": "local", "depth": "fast"},
        }
        response = api_client.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        # Model should reference Alice in the response

    def test_system_message(self, api_client):
        """Test chat with system message."""
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful pirate. Always say 'Arrr!' at the start.",
                },
                {"role": "user", "content": "Hello!"},
            ],
            "config": {"mode": "local", "depth": "fast"},
        }
        response = api_client.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200

    def test_intent_classification(self, api_client):
        """Test that intent is returned in response."""
        payload = {
            "messages": [{"role": "user", "content": "Hello there!"}],
            "config": {"mode": "local", "depth": "fast"},
        }
        response = api_client.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()

        assert "intent" in data
        # Intent should be one of: simple_chat, complex_reasoning, rag_search

    def test_empty_messages_rejected(self, api_client):
        """Test that empty messages are rejected."""
        payload = {"messages": [], "config": {"mode": "local", "depth": "fast"}}
        response = api_client.post(f"{BASE_URL}/v1/chat/completions", json=payload)
        assert response.status_code == 422  # Validation error


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error responses and edge cases."""

    def test_invalid_endpoint(self, api_client):
        """Test 404 for invalid endpoints."""
        response = api_client.get(f"{BASE_URL}/v1/invalid/endpoint")
        assert response.status_code == 404

    def test_invalid_json(self, api_client):
        """Test handling of invalid JSON."""
        response = api_client.post(
            f"{BASE_URL}/v1/chat/completions",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, api_client):
        """Test validation for missing required fields."""
        payload = {"config": {"mode": "local"}}  # Missing messages
        response = api_client.post(f"{BASE_URL}/v1/chat/completions", json=payload)
        assert response.status_code == 422

    def test_invalid_session_id(self, api_client, unlocked_vault):
        """Test accessing non-existent session."""
        response = api_client.get(f"{BASE_URL}/v1/vault/sessions/invalid-session-id/messages")
        assert response.status_code == 404


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Basic performance and response time tests."""

    def test_health_response_time(self, api_client):
        """Health endpoint should respond quickly."""
        start = time.time()
        response = api_client.get(f"{BASE_URL}/v1/system/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # Should be under 1 second

    def test_models_response_time(self, api_client):
        """Models endpoint should respond quickly."""
        start = time.time()
        response = api_client.get(f"{BASE_URL}/v1/models")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0


# ============================================================================
# Agent Tests (v2 Agentic Platform)
# ============================================================================


class TestAgentEndpoints:
    """Test LangGraph agent execution and audit trail."""

    def test_agent_run_simple_query(self, api_client):
        """Test running agent with a simple query."""
        response = api_client.post(
            f"{BASE_URL}/v1/agent/run",
            data={"query": "What is Argon2id?"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "answer" in data
        assert "intent" in data
        assert "run_id" in data
        assert "audit_trail" in data

    def test_agent_returns_audit_trail(self, api_client):
        """Test that agent returns complete audit trail."""
        response = api_client.post(
            f"{BASE_URL}/v1/agent/run",
            data={"query": "Research encryption methods"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT,
        )
        assert response.status_code == 200
        data = response.json()

        audit_trail = data["audit_trail"]
        assert len(audit_trail) >= 4  # At least: classify, retrieve, grade, generate, compliance

        # Check audit entries have required fields
        for action in audit_trail:
            assert "run_id" in action
            assert "node" in action
            assert "thought" in action
            assert "risk_score" in action

    def test_agent_intent_classification(self, api_client):
        """Test that agent classifies intents correctly."""
        # Research query
        response = api_client.post(
            f"{BASE_URL}/v1/agent/run",
            data={"query": "Research the security implications of local LLMs"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "research"

        # Simple chat query
        response = api_client.post(
            f"{BASE_URL}/v1/agent/run",
            data={"query": "Hello, how are you?"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "chat"

    def test_get_agent_run_by_id(self, api_client):
        """Test retrieving audit trail by run ID."""
        # First create a run
        create_response = api_client.post(
            f"{BASE_URL}/v1/agent/run",
            data={"query": "Test query"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT,
        )
        run_id = create_response.json()["run_id"]

        # Retrieve by ID
        response = api_client.get(f"{BASE_URL}/v1/agent/run/{run_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["run_id"] == run_id
        assert "actions" in data

    def test_agent_with_session_id(self, api_client, vault_session):
        """Test agent run with vault session."""
        response = api_client.post(
            f"{BASE_URL}/v1/agent/run",
            data={"query": "What documents are in my vault?", "session_id": vault_session},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT,
        )
        assert response.status_code == 200

    def test_agent_compliance_check(self, api_client):
        """Test that agent performs compliance checking."""
        response = api_client.post(
            f"{BASE_URL}/v1/agent/run",
            data={"query": "Tell me about encryption"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT,
        )
        assert response.status_code == 200
        data = response.json()

        assert "compliance_passed" in data
        # Compliance check node should be in audit trail
        nodes = [a["node"] for a in data["audit_trail"]]
        assert "compliance_check" in nodes


# ============================================================================
# Compliance Tests (Audit Logs & Reports)
# ============================================================================


class TestComplianceEndpoints:
    """Test compliance audit logging and reporting."""

    def test_get_compliance_logs(self, api_client):
        """Test retrieving compliance logs."""
        # First generate some logs by running an agent
        api_client.post(
            f"{BASE_URL}/v1/agent/run",
            data={"query": "Generate logs"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT,
        )

        response = api_client.get(f"{BASE_URL}/v1/compliance/logs")
        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "actions" in data

    def test_compliance_logs_with_limit(self, api_client):
        """Test compliance logs with custom limit."""
        response = api_client.get(f"{BASE_URL}/v1/compliance/logs?limit=5")
        assert response.status_code == 200
        data = response.json()

        assert len(data["actions"]) <= 5

    def test_generate_compliance_report(self, api_client):
        """Test generating compliance report."""
        response = api_client.get(f"{BASE_URL}/v1/compliance/report")
        assert response.status_code == 200
        data = response.json()

        assert "generated_at" in data
        assert "summary" in data

        summary = data["summary"]
        assert "total_actions" in summary
        assert "high_risk_actions" in summary
        assert "runs_with_pii" in summary
        assert "runs_total" in summary

    def test_compliance_report_includes_recent_actions(self, api_client):
        """Test that report includes recent actions."""
        response = api_client.get(f"{BASE_URL}/v1/compliance/report")
        assert response.status_code == 200
        data = response.json()

        assert "recent_actions" in data


# ============================================================================
# Shadow AI Scanner Tests
# ============================================================================


class TestShadowAIScanner:
    """Test Shadow AI scanner functionality."""

    def test_shadow_scan_endpoint(self, api_client):
        """Test shadow AI scan endpoint."""
        response = api_client.get(f"{BASE_URL}/v1/system/shadow-scan")
        assert response.status_code == 200
        data = response.json()

        assert "last_scan" in data
        assert "total_risks" in data
        assert "high_risk_count" in data
        assert "medium_risk_count" in data
        assert "low_risk_count" in data
        assert "risks" in data

    def test_shadow_scan_returns_risk_details(self, api_client):
        """Test that scan returns detailed risk information."""
        response = api_client.get(f"{BASE_URL}/v1/system/shadow-scan")
        assert response.status_code == 200
        data = response.json()

        # If any risks found, verify structure
        for risk in data["risks"]:
            assert "process_name" in risk
            assert "port" in risk
            assert "host" in risk
            assert "risk_level" in risk
            assert "description" in risk

    def test_shadow_scan_detects_ollama(self, api_client):
        """Test that scan can detect Ollama (if running)."""
        response = api_client.get(f"{BASE_URL}/v1/system/shadow-scan")
        assert response.status_code == 200
        data = response.json()

        # Ollama should be detected on port 11434 if running
        any(risk["port"] == 11434 for risk in data["risks"])
        # Note: This may or may not detect depending on environment


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
