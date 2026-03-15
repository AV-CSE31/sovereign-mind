"""
Module A: The Vault - Security & Storage.

This module implements military-grade encryption for chat history storage.
It uses envelope encryption (DEK + KEK) where:
- Master Key (MEK): Derived from user passphrase using Argon2id
- Data Encryption Key (DEK): Unique AES-256 key per session
- The DEK is wrapped (encrypted) with the MEK

Security Boundaries:
- Passphrase is NEVER stored, only used to derive the master key
- All data at rest is encrypted with AES-256-GCM
- Audit logs contain only SHA-256 hashes, never plaintext
"""

import base64
import json
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings
from app.core.exceptions import (
    KeyDerivationError,
    VaultDecryptionError,
    VaultLockedError,
)
from app.core.logging import audit_log, get_logger, hash_for_audit

logger = get_logger(__name__)


@dataclass
class EncryptedData:
    """Container for encrypted data with associated metadata.

    Security Boundary: This structure contains encrypted bytes only.
    The nonce and ciphertext are required for decryption.
    """

    nonce: bytes  # 12-byte nonce for AES-GCM
    ciphertext: bytes  # Encrypted data
    aad: bytes | None = None  # Additional authenticated data (optional)

    def to_dict(self) -> dict[str, str]:
        """Serialize to dictionary with base64-encoded values."""
        return {
            "nonce": base64.b64encode(self.nonce).decode("utf-8"),
            "ciphertext": base64.b64encode(self.ciphertext).decode("utf-8"),
            "aad": base64.b64encode(self.aad).decode("utf-8") if self.aad else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "EncryptedData":
        """Deserialize from dictionary."""
        return cls(
            nonce=base64.b64decode(data["nonce"]),
            ciphertext=base64.b64decode(data["ciphertext"]),
            aad=base64.b64decode(data["aad"]) if data.get("aad") else None,
        )


@dataclass
class WrappedDEK:
    """Data Encryption Key wrapped (encrypted) with Master Key.

    Security Boundary: The DEK is never stored in plaintext.
    This structure holds the encrypted DEK.
    """

    encrypted_dek: EncryptedData
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "encrypted_dek": self.encrypted_dek.to_dict(),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WrappedDEK":
        """Deserialize from dictionary."""
        return cls(
            encrypted_dek=EncryptedData.from_dict(data["encrypted_dek"]),
            created_at=data["created_at"],
        )


@dataclass
class ChatSession:
    """Encrypted chat session data.

    Security Boundary: All message content is encrypted.
    Only metadata (session_id, timestamps) is in plaintext.
    """

    session_id: str
    wrapped_dek: WrappedDEK
    encrypted_messages: list[EncryptedData] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "session_id": self.session_id,
            "wrapped_dek": self.wrapped_dek.to_dict(),
            "encrypted_messages": [msg.to_dict() for msg in self.encrypted_messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatSession":
        """Deserialize from dictionary."""
        return cls(
            session_id=data["session_id"],
            wrapped_dek=WrappedDEK.from_dict(data["wrapped_dek"]),
            encrypted_messages=[
                EncryptedData.from_dict(msg) for msg in data.get("encrypted_messages", [])
            ],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


class VaultManager:
    """Enterprise-grade encrypted storage using envelope encryption.

    Security Boundaries:
    - This class handles encryption/decryption of chat data
    - The passphrase is used only to derive the master key, then discarded
    - All data at rest is encrypted with AES-256-GCM
    - Audit logs record SHA-256 hashes only, never content

    Envelope Encryption Flow:
    1. User provides passphrase → Argon2id → Master Key (MEK)
    2. For each session: Generate random DEK → Encrypt with MEK → Store wrapped DEK
    3. Messages encrypted with DEK → Stored as ciphertext
    """

    def __init__(self) -> None:
        """Initialize the vault in locked state.

        Security Boundary: Vault starts locked. Must call unlock() with passphrase.
        """
        self._settings = get_settings()
        self._master_key: bytes | None = None
        self._salt: bytes | None = None
        self._sessions: dict[str, ChatSession] = {}

        # Ensure storage directories exist
        self._vault_path = Path(self._settings.vault_storage_path)
        self._vault_path.mkdir(parents=True, exist_ok=True)

        self._audit_path = Path(self._settings.audit_log_path)
        self._audit_path.mkdir(parents=True, exist_ok=True)

        # Load salt if exists
        self._salt_file = self._vault_path / ".salt"
        if self._salt_file.exists():
            self._salt = self._salt_file.read_bytes()

        logger.info("vault_initialized", storage_path=str(self._vault_path))

    @property
    def is_locked(self) -> bool:
        """Check if the vault is locked."""
        return self._master_key is None

    def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
        """Derive master key from passphrase using Argon2id.

        Security Boundary: This function sees the plaintext passphrase.
        The passphrase should be cleared from memory after this call.

        Args:
            passphrase: User's secret passphrase.
            salt: Random salt for key derivation.

        Returns:
            32-byte (256-bit) derived key.

        Raises:
            KeyDerivationError: If key derivation fails.
        """
        try:
            key = hash_secret_raw(
                secret=passphrase.encode("utf-8"),
                salt=salt,
                time_cost=self._settings.argon2_time_cost,
                memory_cost=self._settings.argon2_memory_cost,
                parallelism=self._settings.argon2_parallelism,
                hash_len=self._settings.argon2_hash_len,
                type=Type.ID,  # Argon2id hybrid mode
            )
            return key
        except Exception as e:
            logger.error("key_derivation_failed", error=str(e))
            raise KeyDerivationError() from e

    def unlock(self, passphrase: str) -> None:
        """Unlock the vault with user passphrase.

        Security Boundary: This function sees the plaintext passphrase.
        The passphrase is used only to derive the master key.

        Args:
            passphrase: User's secret passphrase.

        Raises:
            KeyDerivationError: If key derivation fails.
        """
        # Generate or load salt
        if self._salt is None:
            self._salt = secrets.token_bytes(self._settings.argon2_salt_len)
            self._salt_file.write_bytes(self._salt)
            logger.info("salt_generated")

        # Derive master key
        self._master_key = self._derive_key(passphrase, self._salt)

        # Load existing sessions
        self._load_sessions()

        logger.info("vault_unlocked", session_count=len(self._sessions))
        audit_log("vault_unlocked", session_id="system")

    def lock(self) -> None:
        """Lock the vault and clear the master key from memory.

        Security Boundary: This clears sensitive key material.
        """
        if self._master_key is not None:
            # Overwrite key memory before discarding
            self._master_key = b"\x00" * len(self._master_key)
        self._master_key = None
        self._sessions.clear()

        logger.info("vault_locked")
        audit_log("vault_locked", session_id="system")

    def _require_unlocked(self) -> None:
        """Ensure vault is unlocked."""
        if self.is_locked:
            raise VaultLockedError()

    def _encrypt(self, key: bytes, plaintext: bytes, aad: bytes | None = None) -> EncryptedData:
        """Encrypt data using AES-256-GCM.

        Security Boundary: This function sees plaintext data.

        Args:
            key: 32-byte encryption key.
            plaintext: Data to encrypt.
            aad: Additional authenticated data (optional).

        Returns:
            EncryptedData container.
        """
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad)

        return EncryptedData(nonce=nonce, ciphertext=ciphertext, aad=aad)

    def _decrypt(self, key: bytes, encrypted: EncryptedData) -> bytes:
        """Decrypt data using AES-256-GCM.

        Security Boundary: This function returns plaintext data.

        Args:
            key: 32-byte encryption key.
            encrypted: EncryptedData container.

        Returns:
            Decrypted plaintext bytes.

        Raises:
            VaultDecryptionError: If decryption fails.
        """
        try:
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(encrypted.nonce, encrypted.ciphertext, encrypted.aad)
            return plaintext
        except Exception as e:
            logger.warning("decryption_failed", error=str(e))
            raise VaultDecryptionError() from e

    def _generate_dek(self) -> bytes:
        """Generate a new Data Encryption Key.

        Security Boundary: DEK is a cryptographically random key.
        It should be wrapped (encrypted) immediately and never stored plaintext.

        Returns:
            32-byte random key.
        """
        return secrets.token_bytes(32)

    def _wrap_dek(self, dek: bytes) -> WrappedDEK:
        """Wrap (encrypt) a DEK with the Master Key.

        Security Boundary: This function sees the plaintext DEK.
        After wrapping, the plaintext DEK should be kept only in memory.

        Args:
            dek: Plaintext Data Encryption Key.

        Returns:
            WrappedDEK containing the encrypted DEK.
        """
        self._require_unlocked()
        encrypted_dek = self._encrypt(self._master_key, dek)  # type: ignore
        return WrappedDEK(encrypted_dek=encrypted_dek)

    def _unwrap_dek(self, wrapped: WrappedDEK) -> bytes:
        """Unwrap (decrypt) a DEK with the Master Key.

        Security Boundary: This function returns the plaintext DEK.

        Args:
            wrapped: WrappedDEK containing the encrypted DEK.

        Returns:
            Plaintext Data Encryption Key.
        """
        self._require_unlocked()
        return self._decrypt(self._master_key, wrapped.encrypted_dek)  # type: ignore

    def create_session(self) -> str:
        """Create a new encrypted chat session.

        Security Boundary: Generates a unique session with its own DEK.

        Returns:
            Session ID.
        """
        self._require_unlocked()

        # Generate unique session ID
        session_id = secrets.token_urlsafe(16)

        # Generate and wrap DEK for this session
        dek = self._generate_dek()
        wrapped_dek = self._wrap_dek(dek)

        # Create session
        session = ChatSession(session_id=session_id, wrapped_dek=wrapped_dek)
        self._sessions[session_id] = session

        # Persist session
        self._save_session(session)

        logger.info("session_created", session_id=session_id)
        audit_log("session_created", session_id=session_id)

        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Add an encrypted message to a session.

        Security Boundary: This function sees plaintext content.
        Content is encrypted before storage and hashed for audit.

        Args:
            session_id: Target session ID.
            role: Message role (user, assistant, system).
            content: Plaintext message content.
        """
        self._require_unlocked()

        if session_id not in self._sessions:
            raise ValueError(f"Session not found: {session_id}")

        session = self._sessions[session_id]

        # Unwrap DEK for this session
        dek = self._unwrap_dek(session.wrapped_dek)

        # Serialize and encrypt message
        message_data = json.dumps(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ).encode("utf-8")

        encrypted_message = self._encrypt(dek, message_data)
        session.encrypted_messages.append(encrypted_message)
        session.updated_at = datetime.now(UTC).isoformat()

        # Persist session
        self._save_session(session)

        # Audit log with hash only
        content_hash = hash_for_audit(content)
        audit_log(
            "message_added",
            session_id=session_id,
            role=role,
            prompt_hash=content_hash if role == "user" else None,
            response_hash=content_hash if role == "assistant" else None,
        )

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve and decrypt all messages from a session.

        Security Boundary: This function returns plaintext messages.
        Caller is responsible for handling plaintext securely.

        Args:
            session_id: Target session ID.

        Returns:
            List of decrypted message dictionaries.
        """
        self._require_unlocked()

        if session_id not in self._sessions:
            raise ValueError(f"Session not found: {session_id}")

        session = self._sessions[session_id]

        # Unwrap DEK for this session
        dek = self._unwrap_dek(session.wrapped_dek)

        # Decrypt all messages
        messages = []
        for encrypted_message in session.encrypted_messages:
            plaintext = self._decrypt(dek, encrypted_message)
            message = json.loads(plaintext.decode("utf-8"))
            messages.append(message)

        return messages

    def _save_session(self, session: ChatSession) -> None:
        """Persist a session to disk.

        Security Boundary: Only encrypted data is written to disk.
        """
        session_file = self._vault_path / f"{session.session_id}.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2)

    def _load_sessions(self) -> None:
        """Load all sessions from disk.

        Security Boundary: Sessions are loaded in encrypted form.
        Decryption happens only when accessing messages.
        """
        self._sessions.clear()

        for session_file in self._vault_path.glob("*.json"):
            try:
                with open(session_file, encoding="utf-8") as f:
                    data = json.load(f)
                session = ChatSession.from_dict(data)
                self._sessions[session.session_id] = session
            except Exception as e:
                logger.warning("session_load_failed", file=str(session_file), error=str(e))

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all sessions (metadata only, no content).

        Security Boundary: Returns only metadata, no decrypted content.

        Returns:
            List of session metadata dictionaries.
        """
        self._require_unlocked()

        return [
            {
                "session_id": session.session_id,
                "message_count": len(session.encrypted_messages),
                "created_at": session.created_at,
                "updated_at": session.updated_at,
            }
            for session in self._sessions.values()
        ]

    def delete_session(self, session_id: str) -> None:
        """Securely delete a session.

        Security Boundary: Removes session data from memory and disk.

        Args:
            session_id: Session to delete.
        """
        self._require_unlocked()

        if session_id in self._sessions:
            del self._sessions[session_id]

        session_file = self._vault_path / f"{session_id}.json"
        if session_file.exists():
            # Overwrite with zeros before deletion
            file_size = session_file.stat().st_size
            with open(session_file, "wb") as f:
                f.write(b"\x00" * file_size)
            session_file.unlink()

        logger.info("session_deleted", session_id=session_id)
        audit_log("session_deleted", session_id=session_id)


# Singleton instance
_vault: VaultManager | None = None


def get_vault() -> VaultManager:
    """Get the singleton VaultManager instance.

    Returns:
        VaultManager instance.
    """
    global _vault
    if _vault is None:
        _vault = VaultManager()
    return _vault
