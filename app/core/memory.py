"""
Module: Episodic Memory (Mem0 Integration).

This module manages long-term memory using the `mem0` library.
It is configured to run LOCALLY using Ollama and ChromaDB.

Reference: https://github.com/mem0ai/mem0
"""

from typing import Any

from mem0 import Memory

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Mem0Service:
    """Wrapper around mem0.Memory for local configuration."""

    def __init__(self):
        settings = get_settings()

        # Configure Mem0 for Local operation
        # See mem0 docs for config structure
        self.config = {
            "llm": {
                "provider": "ollama",
                "config": {
                    "model": settings.ollama_model,
                    # "base_url": settings.ollama_base_url, # Causes init error, relying on env/default
                    "temperature": 0.0,
                    # Mem0 might default to 11434, ensure we listen to config
                },
            },
            "embedder": {
                "provider": "huggingface",
                "config": {"model": "sentence-transformers/all-MiniLM-L6-v2"},
            },
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": "sovereign_mem0",
                    "path": "./data/mem0_storage",
                },
            },
            "history_db_path": "./data/mem0_storage/history.db",
        }

        try:
            self.memory = Memory.from_config(self.config)
            logger.info("mem0_initialized", model=settings.ollama_model, path="./data/mem0_storage")
        except Exception as e:
            logger.error("mem0_init_failed", error=str(e))
            # Fallback or re-raise depends on strictness.
            # We'll re-raise in dev, but might want safe fallback in prod.
            raise e

    def add(self, user_id: str, text: str, metadata: dict[str, Any] | None = None):
        """Add a memory (fact/experience) for the user."""
        try:
            # Mem0 handles extraction automatically from text!
            self.memory.add(text, user_id=user_id, metadata=metadata or {})
            logger.info("mem0_add_success", user_id=user_id)
        except Exception as e:
            logger.error("mem0_add_failed", error=str(e))

    def get_all(self, user_id: str) -> str:
        """Get all memories for a user as a formatted string."""
        try:
            memories = self.memory.get_all(user_id=user_id)
            if not memories:
                return ""

            # Format: "- Fact (date)"
            formatted = []
            for m in memories:
                # Mem0 returns dict with 'memory', 'id', etc.
                if isinstance(m, dict):
                    formatted.append(f"- {m.get('memory', '')}")
                else:
                    formatted.append(f"- {m!s}")

            return "\n".join(formatted)
        except Exception as e:
            logger.error("mem0_get_failed", error=str(e))
            return ""

    def search(self, user_id: str, query: str) -> str:
        """Search relevant memories."""
        try:
            results = self.memory.search(query, user_id=user_id)
            if not results:
                return ""

            formatted = []
            for m in results:
                if isinstance(m, dict):
                    formatted.append(f"- {m.get('memory', '')}")
            return "\n".join(formatted)
        except Exception as e:
            logger.error("mem0_search_failed", error=str(e))
            return ""


# Singleton
_mem0_service = None


def get_memory_service() -> Mem0Service:
    global _mem0_service
    if _mem0_service is None:
        _mem0_service = Mem0Service()
    return _mem0_service


# Backwards compatibility adaptor for Agent Graph
class MemoryExtractor:
    """Compat layer: Simply passes text to Mem0, which does extraction internally."""

    async def extract_from_messages(self, messages: list[Any]) -> list[str]:
        """
        In the previous design, this extracted facts.
        With Mem0, we just return the raw text of the conversation
        and let Mem0's 'add' method handle the extraction logic if enabled,
        OR we rely on the agent to pass profound 'insights' to be memorized.

        For SOTA Sovereign-Mind: We'll take the RELEVANT interactions.
        """
        # Simple heuristics: take the last interaction (Human + AI)
        if len(messages) < 2:
            return []

        last_human = ""
        last_ai = ""

        for m in reversed(messages):
            if hasattr(m, "type"):
                if m.type == "human" and not last_human:
                    last_human = m.content
                elif m.type == "ai" and not last_ai:
                    last_ai = m.content

            if last_human and last_ai:
                break

        # We return a single string representation to be passed to Mem0
        return [f"User said: {last_human}. AI answered: {last_ai}"]
