"""
Custom exceptions for Sovereign-Mind.

All custom exceptions following fail-closed security philosophy.
"""

from typing import Any


class SovereignMindError(Exception):
    """Base exception for all Sovereign-Mind errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class IntegrityError(SovereignMindError):
    """Raised when cryptographic integrity verification fails."""

    def __init__(self, message: str = "Integrity check failed."):
        super().__init__(message)


# ============================================================================
# Security Exceptions (Module A: The Vault)
# ============================================================================


class VaultError(SovereignMindError):
    """Base exception for vault/security operations."""

    pass


class VaultLockedError(VaultError):
    """Raised when attempting operations on a locked vault.

    Security Boundary: This exception reveals no information about the vault
    contents or encryption state.
    """

    def __init__(self, message: str = "Vault is locked. Unlock with passphrase first."):
        super().__init__(message)


class VaultDecryptionError(VaultError):
    """Raised when decryption fails (wrong key, corrupted data).

    Security Boundary: Error message is intentionally vague to prevent
    oracle attacks.
    """

    def __init__(self, message: str = "Decryption failed. Invalid key or corrupted data."):
        super().__init__(message)


class KeyDerivationError(VaultError):
    """Raised when key derivation fails."""

    def __init__(self, message: str = "Key derivation failed."):
        super().__init__(message)


# ============================================================================
# Privacy Exceptions (Module D: The Filter)
# ============================================================================


class PrivacyError(SovereignMindError):
    """Base exception for privacy/PII operations."""

    pass


class PrivacyThresholdExceeded(PrivacyError):
    """Raised when PII detection fails or confidence is too low.

    Security Boundary: Following fail-closed philosophy, this blocks requests
    when PII detection is uncertain.
    """

    def __init__(
        self,
        message: str = "Privacy threshold exceeded. Request blocked for safety.",
        pii_types: list[str] | None = None,
    ):
        super().__init__(message, {"pii_types": pii_types or []})
        self.pii_types = pii_types or []


class AnonymizationError(PrivacyError):
    """Raised when anonymization fails."""

    def __init__(self, message: str = "Anonymization failed."):
        super().__init__(message)


class RehydrationError(PrivacyError):
    """Raised when rehydrating PII placeholders fails."""

    def __init__(self, message: str = "PII rehydration failed."):
        super().__init__(message)


# ============================================================================
# RAG Exceptions (Module C: Memory)
# ============================================================================


class RAGError(SovereignMindError):
    """Base exception for RAG operations."""

    pass


class DocumentIngestionError(RAGError):
    """Raised when document ingestion fails."""

    def __init__(self, message: str, document_path: str | None = None):
        super().__init__(message, {"document_path": document_path})
        self.document_path = document_path


class RetrievalError(RAGError):
    """Raised when document retrieval fails."""

    def __init__(self, message: str = "Document retrieval failed."):
        super().__init__(message)


class RerankingError(RAGError):
    """Raised when reranking fails."""

    def __init__(self, message: str = "Reranking failed. Falling back to non-reranked results."):
        super().__init__(message)


# ============================================================================
# Agent Exceptions (Module B: The Brain)
# ============================================================================


class AgentError(SovereignMindError):
    """Base exception for agentic reasoning errors."""

    pass


class MaxRetriesExceeded(AgentError):
    """Raised when maximum retries for an operation are exceeded."""

    def __init__(self, operation: str, max_retries: int = 3):
        super().__init__(
            f"Maximum retries ({max_retries}) exceeded for: {operation}",
            {"operation": operation, "max_retries": max_retries},
        )


class IntentClassificationError(AgentError):
    """Raised when intent classification fails."""

    def __init__(self, message: str = "Could not classify user intent."):
        super().__init__(message)


class PlanningError(AgentError):
    """Raised when query planning fails."""

    def __init__(self, message: str = "Query planning failed."):
        super().__init__(message)


# ============================================================================
# LLM Exceptions
# ============================================================================


class LLMError(SovereignMindError):
    """Base exception for LLM operations."""

    pass


class LocalLLMUnavailable(LLMError):
    """Raised when local LLM (ollama) is unavailable."""

    def __init__(self, message: str = "Local LLM is unavailable. Check ollama service."):
        super().__init__(message)


class CloudLLMError(LLMError):
    """Raised when cloud LLM call fails."""

    def __init__(self, message: str = "Cloud LLM call failed."):
        super().__init__(message)
