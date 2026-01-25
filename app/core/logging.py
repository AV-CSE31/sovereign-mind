"""
Structured logging configuration using structlog.

Security Boundary: This logger is configured to NEVER log PII.
Only metadata, hashes, and operation results are logged.
All sensitive data must be hashed before logging.
"""

import hashlib
import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.core.config import get_settings


def hash_for_audit(data: str) -> str:
    """Create SHA-256 hash for audit logging.

    Security Boundary: This function creates a one-way hash of content
    for compliance auditing without storing the actual content.

    Args:
        data: The plaintext data to hash (will not be stored).

    Returns:
        Hex-encoded SHA-256 hash of the data.
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def redact_sensitive_keys(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Redact sensitive keys from log events.

    Security Boundary: This processor prevents accidental PII leakage
    by redacting known sensitive key patterns.
    """
    sensitive_patterns = {
        "password",
        "passphrase",
        "secret",
        "api_key",
        "token",
        "key",
        "pii",
        "plaintext",
        "content",
        "message",
        "prompt",
        "response",
        "text",
    }

    for key in list(event_dict.keys()):
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in sensitive_patterns):
            event_dict[key] = "[REDACTED]"

    return event_dict


def add_service_context(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add service context to all log events."""
    settings = get_settings()
    event_dict["service"] = settings.app_name
    event_dict["version"] = settings.app_version
    return event_dict


def configure_logging() -> None:
    """Configure structured logging for the application.

    Security Boundary: Logging is configured to output JSON format
    with automatic redaction of sensitive keys.
    """
    settings = get_settings()

    # Determine log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Shared processors for all loggers
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_service_context,
        redact_sensitive_keys,  # Security: Always redact before output
    ]

    # Configure structlog
    if settings.debug:
        # Pretty printing for development
        structlog.configure(
            processors=shared_processors
            + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=shared_processors,
        )
    else:
        # JSON output for production
        structlog.configure(
            processors=shared_processors
            + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )

    # Configure root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Security Boundary: All loggers obtained through this function
    have automatic PII redaction enabled.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured structured logger.
    """
    return structlog.get_logger(name)


# Convenience function for audit logging
def audit_log(
    operation: str,
    prompt_hash: str | None = None,
    response_hash: str | None = None,
    session_id: str | None = None,
    **kwargs: Any,
) -> None:
    """Log an audit event with content hashes.

    Security Boundary: This function logs ONLY hashes, never plaintext.
    Use hash_for_audit() to generate hashes from content.

    Args:
        operation: The operation being audited (e.g., "chat_completion").
        prompt_hash: SHA-256 hash of the prompt (optional).
        response_hash: SHA-256 hash of the response (optional).
        session_id: Session identifier (optional).
        **kwargs: Additional metadata to log.
    """
    logger = get_logger("audit")
    logger.info(
        operation,
        prompt_sha256=prompt_hash,
        response_sha256=response_hash,
        session_id=session_id,
        **kwargs,
    )
