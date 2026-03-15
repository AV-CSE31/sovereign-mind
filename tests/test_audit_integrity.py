import contextlib
import os
import sqlite3
from pathlib import Path

import pytest

from app.services.audit_log import AgentAction, AuditDatabase

# Use a temporary database for testing
TEST_DB = Path("./data/test_audit/audit_log.db")


@pytest.fixture
def db():
    if TEST_DB.exists():
        os.remove(TEST_DB)

    db = AuditDatabase(db_path=TEST_DB)
    yield db

    # Cleanup
    if TEST_DB.exists():
        os.remove(TEST_DB)
        if TEST_DB.parent.exists():
            with contextlib.suppress(OSError):
                TEST_DB.parent.rmdir()


def test_merkle_chain_integrity(db):
    """Test that the Merkle chain is valid when data is untampered."""

    # Insert 3 actions
    actions = []
    for i in range(3):
        action = AgentAction(run_id="run-1", node="node-1", thought=f"Action {i}", risk_score=0.1)
        db.insert(action)
        actions.append(action)

    # Verify chain
    assert db.verify_chain() is True
    print("\n[PASS] Chain is valid for untampered data.")


def test_merkle_chain_tamper_detection(db):
    """Test that the Merkle chain detects tampering."""

    # Insert 3 actions
    for i in range(3):
        action = AgentAction(run_id="run-1", node="node-1", thought=f"Action {i}", risk_score=0.1)
        db.insert(action)

    # Verify initial state
    assert db.verify_chain() is True

    # TAMPER WITH DATA: Modify the thought of the second action (ID=2)
    # This should invalidate the hash of ID=2
    with sqlite3.connect(TEST_DB) as conn:
        conn.execute("UPDATE agent_actions SET thought = 'TAMPERED' WHERE id = 2")
        conn.commit()

    # Verify chain detects tampering
    assert db.verify_chain() is False
    print("\n[PASS] Chain correctly detected content tampering.")


def test_merkle_chain_deletion_detection(db):
    """Test that the Merkle chain detects row deletion (broken link)."""

    # Insert 3 actions
    for i in range(3):
        action = AgentAction(run_id="run-1", node="node-1", thought=f"Action {i}", risk_score=0.1)
        db.insert(action)

    # TAMPER: Delete the middle row (ID=2)
    # ID 3's parent_hash will now point to a non-existent previous hash (or the chain logic will break)
    # Actually, in our simple verify_chain loop, if we delete a row, the `previous_hash` logic
    # will compare ID 3's parent_hash (which is ID 2's hash) with ID 1's hash. They won't match.

    with sqlite3.connect(TEST_DB) as conn:
        conn.execute("DELETE FROM agent_actions WHERE id = 2")
        conn.commit()

    # Verify chain detects break
    assert db.verify_chain() is False
    print("\n[PASS] Chain correctly detected row deletion.")
