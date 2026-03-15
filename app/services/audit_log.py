"""
Sovereign-Mind Audit Logger
Tamper-proof logging for agent actions and compliance reporting.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.exceptions import IntegrityError  # Assuming this exists, or use generic Exception

# ============================================================================
# Data Models
# ============================================================================


class AgentAction(BaseModel):
    """A single action taken by an agent node."""

    run_id: str
    node: str
    thought: str
    tool_call: str | None = None
    risk_score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    parent_hash: str | None = None  # Merkle Link: Hash of the previous action
    witness_signature: str | None = None  # ZK-Witness Signature

    def compute_hash(self) -> str:
        """Compute integrity hash for tamper detection.

        The hash now includes the `parent_hash` and `witness_signature`.
        """
        data = f"{self.run_id}:{self.node}:{self.thought}:{self.timestamp.isoformat()}:{self.parent_hash or '0'}:{self.witness_signature or '0'}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class ComplianceReport(BaseModel):
    """Compliance report for a specific run or time period."""

    generated_at: datetime
    total_actions: int
    high_risk_actions: int
    runs_with_pii: int
    runs_total: int
    integrity_verified: bool
    actions: list[AgentAction]


# ============================================================================
# Audit Database
# ============================================================================


class AuditDatabase:
    """SQLite-based audit log storage."""

    def __init__(self, db_path: Path = Path("./data/audit/audit_log.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    node TEXT NOT NULL,
                    thought TEXT NOT NULL,
                    tool_call TEXT,
                    risk_score REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    parent_hash TEXT,
                    witness_signature TEXT,
                    hash TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_run_id ON agent_actions(run_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON agent_actions(timestamp)
            """)
            conn.commit()

    def get_last_hash(self) -> str:
        """Get the hash of the most recent action."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT hash FROM agent_actions ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else "0"

    def insert(self, action: AgentAction):
        """Insert an action into the audit log."""
        # 1. Get previous hash for linking
        last_hash = self.get_last_hash()

        # 2. Set parent hash on the action
        action.parent_hash = last_hash

        # 3. Compute new hash
        current_hash = action.compute_hash()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO agent_actions (run_id, node, thought, tool_call, risk_score, timestamp, parent_hash, witness_signature, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    action.run_id,
                    action.node,
                    action.thought,
                    action.tool_call,
                    action.risk_score,
                    action.timestamp.isoformat(),
                    action.parent_hash,
                    action.witness_signature,
                    current_hash,
                ),
            )
            conn.commit()

    def get_by_run(self, run_id: str) -> list[AgentAction]:
        """Get all actions for a specific run."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM agent_actions WHERE run_id = ? ORDER BY timestamp
            """,
                (run_id,),
            )
            rows = cursor.fetchall()

        return [self._map_row(row) for row in rows]

    def get_recent(self, limit: int = 100) -> list[AgentAction]:
        """Get recent actions across all runs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM agent_actions ORDER BY timestamp DESC LIMIT ?
            """,
                (limit,),
            )
            rows = cursor.fetchall()

        return [self._map_row(row) for row in rows]

    def _map_row(self, row: sqlite3.Row) -> AgentAction:
        # Helper to safely get column or fallback to None/Index
        def get_col(r, key, idx):
            try:
                return r[key]
            except (IndexError, ValueError):
                # Fallback to index if available? Row objects mimic tuples
                return r[idx] if idx < len(r) else None

        return AgentAction(
            run_id=get_col(row, "run_id", 1),
            node=get_col(row, "node", 2),
            thought=get_col(row, "thought", 3),
            tool_call=get_col(row, "tool_call", 5),
            risk_score=get_col(row, "risk_score", 6),
            timestamp=datetime.fromisoformat(get_col(row, "timestamp", 7)),
            parent_hash=get_col(row, "parent_hash", 8),
            witness_signature=get_col(row, "witness_signature", 9),
        )

    # ... [Keeping verify_chain method as is, assuming it uses map_row which we updated] ...

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire Merkle chain."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Fetch all rows ordered by ID (insertion order)
            cursor = conn.execute("SELECT * FROM agent_actions ORDER BY id ASC")
            rows = cursor.fetchall()

        if not rows:
            return True

        previous_hash = "0"

        for _i, row in enumerate(rows):
            # 1. Check if parent_hash matches previous row's hash
            # Row is sqlite3.Row, access by name should work if factory set
            # fallback to index if needed, but let's debug
            current_parent = (
                row["parent_hash"] if "parent_hash" in row else row[7]
            )  # Fallback to index 7

            if current_parent != previous_hash:
                return False

            # 2. Re-compute hash to check for content tampering
            action = self._map_row(row)
            # Important: Ensure the re-computed object has the correct parent_hash
            action.parent_hash = current_parent

            recomputed_hash = action.compute_hash()

            if recomputed_hash != row["hash"]:
                return False

            previous_hash = row["hash"]

        return True

    def get_stats(self) -> dict:
        """Get aggregate statistics for compliance reporting."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_actions,
                    COUNT(DISTINCT run_id) as total_runs,
                    SUM(CASE WHEN risk_score > 0.5 THEN 1 ELSE 0 END) as high_risk_actions,
                    COUNT(DISTINCT CASE WHEN thought LIKE '%PII%' THEN run_id END) as runs_with_pii
                FROM agent_actions
            """)
            row = cursor.fetchone()

        return {
            "total_actions": row[0] or 0,
            "total_runs": row[1] or 0,
            "high_risk_actions": row[2] or 0,
            "runs_with_pii": row[3] or 0,
        }


# ============================================================================
# Audit Logger (Singleton)
# ============================================================================


class AuditLogger:
    """Static interface for audit logging."""

    _db: AuditDatabase | None = None

    @classmethod
    def _get_db(cls) -> AuditDatabase:
        if cls._db is None:
            cls._db = AuditDatabase()
        return cls._db

    @classmethod
    async def log(cls, action: AgentAction):
        """Log an agent action (async-compatible sync operation)."""
        # --- ZK-Witness Step ---
        from app.services.zk_witness import WitnessError, get_witness

        witness = get_witness()
        try:
            # Convert action to dict for signing
            action_data = action.model_dump()
            signature = witness.sign_action(action_data)
            action.witness_signature = signature
        except WitnessError as e:
            # Re-raise as IntegrityError or log failure?
            # fail-closed: reject the log (and thus the action?)
            # Since this is "logging", the action likely happened or is about to.
            # Ideally this happens BEFORE action execution.
            raise IntegrityError(f"Action rejected by ZK-Witness: {e!s}")

        cls._get_db().insert(action)

    @classmethod
    async def get_run_actions(cls, run_id: str) -> list[AgentAction]:
        """Get actions for a specific run."""
        return cls._get_db().get_by_run(run_id)

    @classmethod
    async def get_recent_actions(cls, limit: int = 100) -> list[AgentAction]:
        """Get recent actions."""
        return cls._get_db().get_recent(limit)

    @classmethod
    async def verify_integrity(cls) -> bool:
        """Verify the cryptographic integrity of the audit log."""
        return cls._get_db().verify_chain()

    @classmethod
    async def get_current_hash(cls) -> str:
        """Get the current Merkle Root hash of the audit log.

        Used for synchronization handshakes.
        """
        return cls._get_db().get_last_hash()

    @classmethod
    async def generate_report(cls) -> ComplianceReport:
        """Generate a compliance report."""
        db = cls._get_db()
        stats = db.get_stats()
        recent_actions = db.get_recent(1000)
        is_valid = db.verify_chain()

        return ComplianceReport(
            generated_at=datetime.utcnow(),
            total_actions=stats["total_actions"],
            high_risk_actions=stats["high_risk_actions"],
            runs_with_pii=stats["runs_with_pii"],
            runs_total=stats["total_runs"],
            integrity_verified=is_valid,
            actions=recent_actions[:100],  # Limit for report
        )
