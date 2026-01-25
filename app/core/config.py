"""
Application configuration using Pydantic Settings.

Security Boundary: This module loads configuration from environment variables.
No secrets are hardcoded. All sensitive values must be provided at runtime.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Security Boundary: This class reads from environment/files only.
    Never log or expose these settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========================================================================
    # Application Settings
    # ========================================================================
    app_name: str = "Sovereign-Mind"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # ========================================================================
    # Security Settings (Module A: The Vault)
    # ========================================================================
    # Argon2 parameters for key derivation
    argon2_time_cost: int = Field(default=3, ge=1)
    argon2_memory_cost: int = Field(default=65536, ge=1024)  # 64MB
    argon2_parallelism: int = Field(default=4, ge=1)
    argon2_hash_len: int = Field(default=32, ge=16)  # 256-bit key
    argon2_salt_len: int = Field(default=16, ge=8)

    # Vault storage path
    vault_storage_path: str = "./data/vault"
    audit_log_path: str = "./data/audit"

    # ========================================================================
    # LLM Settings (Local-First Default)
    # ========================================================================
    # Local LLM (ollama/llamafile)
    ollama_base_url: str = "http://localhost:8080"
    ollama_model: str = "TinyLlama-1.1B-Chat-v1.0.Q5_K_M"
    ollama_timeout: int = 120

    # Cloud LLM (fallback)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout: int = 60

    # Default mode
    default_mode: Literal["local", "cloud_secure"] = "local"
    default_depth: Literal["fast", "deep_reasoning"] = "fast"

    # ========================================================================
    # RAG Settings (Module C: Memory)
    # ========================================================================
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "sovereign_mind_docs"

    # Embedding model (local)
    embedding_model: str = "nomic-embed-text"

    # Retrieval settings
    dense_top_k: int = 25  # Initial dense retrieval
    sparse_top_k: int = 25  # Initial sparse retrieval
    rerank_top_n: int = 50  # Candidates for reranking
    final_top_k: int = 5  # Final documents to LLM

    # Chunking settings
    chunk_size: int = 512
    chunk_overlap: int = 50

    # ========================================================================
    # Privacy Settings (Module D: The Filter)
    # ========================================================================
    # PII detection threshold (fail-closed if below)
    pii_detection_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # Supported languages for PII detection
    pii_languages: list[str] = ["en"]

    # Whether to block requests with PII when using cloud
    block_pii_on_cloud: bool = True

    # ========================================================================
    # Agent Settings (Module B: The Brain)
    # ========================================================================
    max_retrieval_retries: int = 3
    grader_relevance_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_planning_steps: int = 5


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Security Boundary: Settings are cached to prevent repeated file reads
    and potential timing attacks on configuration loading.
    """
    return Settings()
