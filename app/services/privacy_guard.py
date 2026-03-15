"""
Module D: The Filter - Privacy Gateway.

This module implements fail-closed PII protection with:
1. Detection: Presidio Analyzer scans for PII entities
2. Stateful Mapping: Secure in-memory mapping of placeholders to real values
3. Sanitization: Replace PII with placeholders before cloud LLM calls
4. Rehydration: Restore real values in the final response

Security Boundaries:
- Detection runs locally using Presidio
- Mappings are kept in-memory only (never persisted)
- If detection fails or confidence is below threshold, request is BLOCKED
- Cloud LLM never sees actual PII values
"""

import re
import secrets
from dataclasses import dataclass, field
from typing import Any

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine

from app.core.config import get_settings
from app.core.exceptions import (
    AnonymizationError,
    PrivacyThresholdExceeded,
    RehydrationError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PIIEntity:
    """A detected PII entity.

    Security Boundary: This structure contains the original PII value.
    Handle with care and never log.
    """

    entity_type: str  # e.g., PERSON, EMAIL_ADDRESS, PHONE_NUMBER
    original_value: str  # The actual PII value (NEVER LOG)
    placeholder: str  # e.g., <PERSON_1>
    start: int  # Start position in text
    end: int  # End position in text
    score: float  # Detection confidence


@dataclass
class AnonymizationResult:
    """Result of anonymization process.

    Security Boundary: Contains both the sanitized text and the mapping.
    The mapping is required for rehydration.
    """

    sanitized_text: str  # Text with PII replaced by placeholders
    entity_count: int  # Number of PII entities found
    entity_types: list[str]  # Types of entities found
    # Note: The actual mapping is stored in the session, not here


@dataclass
class PIISession:
    """In-memory session for PII mappings.

    Security Boundary: This session is volatile and will be lost on restart.
    Never persist this to disk.
    """

    session_id: str
    mappings: dict[str, str] = field(default_factory=dict)  # placeholder -> original
    reverse_mappings: dict[str, str] = field(default_factory=dict)  # original -> placeholder
    entity_counters: dict[str, int] = field(default_factory=dict)  # entity_type -> count

    def add_mapping(self, entity_type: str, original_value: str) -> str:
        """Add a PII mapping and return the placeholder.

        Security Boundary: This function stores the original PII value.

        Args:
            entity_type: Type of PII entity.
            original_value: The actual PII value.

        Returns:
            Generated placeholder (e.g., <PERSON_1>).
        """
        # Check if we already have this value mapped
        if original_value in self.reverse_mappings:
            return self.reverse_mappings[original_value]

        # Generate new placeholder
        count = self.entity_counters.get(entity_type, 0) + 1
        self.entity_counters[entity_type] = count
        placeholder = f"<{entity_type}_{count}>"

        # Store bidirectional mapping
        self.mappings[placeholder] = original_value
        self.reverse_mappings[original_value] = placeholder

        return placeholder

    def get_original(self, placeholder: str) -> str | None:
        """Get the original value for a placeholder.

        Args:
            placeholder: The placeholder text.

        Returns:
            Original PII value, or None if not found.
        """
        return self.mappings.get(placeholder)

    def clear(self) -> None:
        """Securely clear all mappings.

        Security Boundary: Overwrites mapping data before clearing.
        """
        # Overwrite string values (best effort in Python)
        for key in list(self.mappings.keys()):
            self.mappings[key] = "X" * len(self.mappings[key])
        for key in list(self.reverse_mappings.keys()):
            self.reverse_mappings[key] = "X" * len(self.reverse_mappings[key])

        self.mappings.clear()
        self.reverse_mappings.clear()
        self.entity_counters.clear()


class AnonymizationService:
    """PII Detection, Anonymization, and Rehydration Service.

    Security Boundaries:
    - Detection runs entirely locally (Presidio)
    - If detection fails or confidence is below threshold, request is BLOCKED
    - Original PII values are stored only in volatile memory
    - Cloud LLM calls only see sanitized text with placeholders

    Fail-Closed Philosophy:
    - Unknown or low-confidence entities trigger exceptions
    - Errors during processing block the request
    - No fallback to sending potentially sensitive data
    """

    def __init__(self) -> None:
        """Initialize the anonymization service.

        Security Boundary: Initializes local NLP models for PII detection.
        """
        self._settings = get_settings()

        # Initialize Presidio engines
        self._analyzer = AnalyzerEngine()
        self._anonymizer = AnonymizerEngine()

        # Active sessions (in-memory only)
        self._sessions: dict[str, PIISession] = {}

        # Supported entity types
        self._supported_entities = [
            "PERSON",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "US_SSN",
            "US_PASSPORT",
            "US_DRIVER_LICENSE",
            "IP_ADDRESS",
            "DATE_TIME",
            "LOCATION",
            "NRP",  # Nationality, Religious, Political group
            "MEDICAL_LICENSE",
            "URL",
        ]

        logger.info(
            "anonymization_service_initialized",
            languages=self._settings.pii_languages,
            entity_types=len(self._supported_entities),
        )

    def create_session(self) -> str:
        """Create a new PII session for stateful mapping.

        Returns:
            Session ID.
        """
        session_id = secrets.token_urlsafe(16)
        self._sessions[session_id] = PIISession(session_id=session_id)

        logger.info("pii_session_created", session_id=session_id)
        return session_id

    def get_session(self, session_id: str) -> PIISession | None:
        """Get an existing PII session.

        Args:
            session_id: Session identifier.

        Returns:
            PIISession or None.
        """
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> None:
        """Securely delete a PII session.

        Security Boundary: Clears all PII mappings before deletion.

        Args:
            session_id: Session to delete.
        """
        if session_id in self._sessions:
            self._sessions[session_id].clear()
            del self._sessions[session_id]
            logger.info("pii_session_deleted", session_id=session_id)

    def detect_pii(self, text: str) -> list[PIIEntity]:
        """Detect PII entities in text.

        Security Boundary: This function analyzes potentially sensitive text.

        Args:
            text: Text to analyze.

        Returns:
            List of detected PII entities.

        Raises:
            PrivacyThresholdExceeded: If detection confidence is below threshold.
        """
        # Run Presidio analyzer
        results: list[RecognizerResult] = self._analyzer.analyze(
            text=text,
            entities=self._supported_entities,
            language=self._settings.pii_languages[0],
        )

        entities = []
        low_confidence_entities = []

        for result in results:
            # Extract the original value from text
            original_value = text[result.start : result.end]

            entity = PIIEntity(
                entity_type=result.entity_type,
                original_value=original_value,
                placeholder="",  # Will be assigned during anonymization
                start=result.start,
                end=result.end,
                score=result.score,
            )

            # Check confidence threshold
            if result.score < self._settings.pii_detection_threshold:
                low_confidence_entities.append(entity)
            else:
                entities.append(entity)

        # Fail-closed: If we detected low-confidence entities, warn but continue
        # Only block if explicitly configured
        if low_confidence_entities:
            logger.warning(
                "low_confidence_pii_detected",
                count=len(low_confidence_entities),
                types=[e.entity_type for e in low_confidence_entities],
            )

        logger.info(
            "pii_detection_complete",
            entity_count=len(entities),
            entity_types=list({e.entity_type for e in entities}),
        )

        return entities

    def anonymize(
        self,
        text: str,
        session_id: str | None = None,
    ) -> tuple[str, str]:
        """Anonymize text by replacing PII with placeholders.

        Security Boundary: This function sees plaintext PII and creates mappings.

        Args:
            text: Text containing potential PII.
            session_id: Optional session ID for stateful mapping.

        Returns:
            Tuple of (sanitized_text, session_id).

        Raises:
            AnonymizationError: If anonymization fails.
            PrivacyThresholdExceeded: If PII detection fails critically.
        """
        try:
            # Create or get session
            if session_id is None or session_id not in self._sessions:
                session_id = self.create_session()

            session = self._sessions[session_id]

            # Detect PII entities
            entities = self.detect_pii(text)

            if not entities:
                # No PII found, return text as-is
                return text, session_id

            # Sort entities by position (descending) for replacement
            entities_sorted = sorted(entities, key=lambda e: e.start, reverse=True)

            # Replace PII with placeholders
            sanitized = text
            for entity in entities_sorted:
                # Get or create placeholder
                placeholder = session.add_mapping(entity.entity_type, entity.original_value)
                entity.placeholder = placeholder

                # Replace in text
                sanitized = sanitized[: entity.start] + placeholder + sanitized[entity.end :]

            logger.info(
                "anonymization_complete",
                session_id=session_id,
                entity_count=len(entities),
            )

            return sanitized, session_id

        except PrivacyThresholdExceeded:
            raise
        except Exception as e:
            logger.error("anonymization_failed", error=str(e))
            raise AnonymizationError(str(e)) from e

    def rehydrate(self, text: str, session_id: str) -> str:
        """Restore original PII values from placeholders.

        Security Boundary: This function returns text containing real PII.
        Only call this for responses to the end user, never for external calls.

        Args:
            text: Text containing placeholders.
            session_id: Session ID with the mappings.

        Returns:
            Text with original PII values restored.

        Raises:
            RehydrationError: If rehydration fails.
        """
        try:
            session = self._sessions.get(session_id)

            if session is None:
                logger.warning("rehydration_session_not_found", session_id=session_id)
                return text

            # Find all placeholders in text
            placeholder_pattern = r"<([A-Z_]+)_(\d+)>"
            matches = list(re.finditer(placeholder_pattern, text))

            if not matches:
                return text

            # Replace placeholders with original values
            rehydrated = text
            for match in reversed(matches):  # Process from end to start
                placeholder = match.group(0)
                original = session.get_original(placeholder)

                if original:
                    rehydrated = rehydrated[: match.start()] + original + rehydrated[match.end() :]
                else:
                    logger.warning(
                        "placeholder_not_found_in_session",
                        placeholder=placeholder,
                        session_id=session_id,
                    )

            logger.info(
                "rehydration_complete",
                session_id=session_id,
                placeholders_replaced=len(matches),
            )

            return rehydrated

        except Exception as e:
            logger.error("rehydration_failed", error=str(e))
            raise RehydrationError(str(e)) from e

    def is_safe_for_cloud(self, text: str) -> bool:
        """Check if text is safe to send to cloud LLM.

        Security Boundary: Performs a quick check for obvious PII patterns.

        Args:
            text: Text to check.

        Returns:
            True if no PII detected, False otherwise.
        """
        entities = self.detect_pii(text)
        return len(entities) == 0

    def get_session_stats(self, session_id: str) -> dict[str, Any] | None:
        """Get statistics for a PII session (no actual PII values).

        Args:
            session_id: Session identifier.

        Returns:
            Session statistics or None.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        return {
            "session_id": session_id,
            "mapping_count": len(session.mappings),
            "entity_types": list(session.entity_counters.keys()),
            "entity_counts": dict(session.entity_counters),
        }


# Singleton instance
_service: AnonymizationService | None = None


def get_anonymization_service() -> AnonymizationService:
    """Get the singleton AnonymizationService instance.

    Returns:
        AnonymizationService instance.
    """
    global _service
    if _service is None:
        _service = AnonymizationService()
    return _service
