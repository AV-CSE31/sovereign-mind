from unittest.mock import patch

import pytest

from app.core.exceptions import IntegrityError
from app.services.audit_log import AgentAction, AuditLogger
from app.services.zk_witness import WitnessError, ZkWitness


@pytest.mark.asyncio
async def test_compliant_action_signed():
    """Test that a compliant action gets signed and logged."""

    # Mock DB insert to avoid actual DB writes
    with patch("app.services.audit_log.AuditDatabase.insert") as mock_insert:
        action = AgentAction(run_id="run-1", node="test", thought="Safe thought", risk_score=0.1)

        await AuditLogger.log(action)

        # Verify signature was added
        assert action.witness_signature is not None
        assert len(action.witness_signature) > 0
        mock_insert.assert_called_once()


@pytest.mark.asyncio
async def test_violation_blocked():
    """Test that a policy violation raises IntegrityError."""

    # Action with PII triggering Witness Policy
    action = AgentAction(run_id="run-2", node="test", thought="My SSN is 123-45", risk_score=0.9)

    with pytest.raises(IntegrityError):
        await AuditLogger.log(action)


def test_manual_witness_signing():
    """Test manual signing with ZkWitness class."""
    witness = ZkWitness()

    # Valid
    sig = witness.sign_action({"thought": "hello"})
    assert sig

    # Invalid
    with pytest.raises(WitnessError):
        witness.sign_action({"thought": "delete all with --force"})
