from unittest.mock import AsyncMock, patch

import pytest

from app.core.minion_orchestrator import ContextSyncError, MinionOrchestrator


@pytest.mark.asyncio
async def test_handshake_success():
    """Test that execution proceeds when handshake passes."""
    with patch(
        "app.core.minion_orchestrator.AuditLogger.get_current_hash", new_callable=AsyncMock
    ) as mock_hash:
        # Mock valid hash
        mock_hash.return_value = "abc123hash"

        orchestrator = MinionOrchestrator()

        # Mock internal methods to isolate handshake test
        orchestrator._verify_handshake = AsyncMock(return_value=True)
        orchestrator._decompose_task = AsyncMock(return_value={"steps": []})
        orchestrator._aggregate_results = AsyncMock(return_value="Done")

        result = await orchestrator.orchestrate("run task")

        assert result["handshake_hash"] == "abc123hash"
        assert result["answer"] == "Done"


@pytest.mark.asyncio
async def test_handshake_failure():
    """Test that ContextSyncError is raised when handshake fails."""
    with patch(
        "app.core.minion_orchestrator.AuditLogger.get_current_hash", new_callable=AsyncMock
    ) as mock_hash:
        mock_hash.return_value = "bad_hash"

        orchestrator = MinionOrchestrator()

        # Mock handshake to fail
        orchestrator._verify_handshake = AsyncMock(return_value=False)

        with pytest.raises(ContextSyncError) as excinfo:
            await orchestrator.orchestrate("run task")

        assert "Context mismatch" in str(excinfo.value)
