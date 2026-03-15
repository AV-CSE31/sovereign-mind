"""
Shadow AI Scanner
Detects unauthorized LLM processes running on the local network (Mock implementation).
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ShadowAIRisk:
    """Represents a detected unauthorized AI process."""

    process_name: str
    port: int
    host: str
    risk_level: str  # "low", "medium", "high"
    detected_at: datetime
    description: str


class ShadowAIScanner:
    """Scanner for detecting unauthorized LLM processes."""

    # Known LLM service ports
    KNOWN_LLM_PORTS = {
        11434: ("Ollama", "high"),
        1234: ("LM Studio", "high"),
        5001: ("Text Generation WebUI", "medium"),
        8080: ("Generic AI Server", "low"),
        3000: ("Open WebUI", "medium"),
        8000: ("Sovereign-Mind (expected)", "low"),
    }

    def __init__(self):
        self.last_scan: datetime | None = None
        self.cached_risks: list[ShadowAIRisk] = []

    def scan_ports(self, host: str = "localhost") -> list[ShadowAIRisk]:
        """Scan for known LLM service ports."""
        risks: list[ShadowAIRisk] = []

        for port, (name, risk_level) in self.KNOWN_LLM_PORTS.items():
            if self._is_port_open(host, port):
                # Skip Sovereign-Mind's own port
                if port == 8000:
                    continue

                risks.append(
                    ShadowAIRisk(
                        process_name=name,
                        port=port,
                        host=host,
                        risk_level=risk_level,
                        detected_at=datetime.utcnow(),
                        description=f"Detected {name} running on {host}:{port}. "
                        f"This may be an unmanaged AI service.",
                    )
                )

        self.last_scan = datetime.utcnow()
        self.cached_risks = risks
        return risks

    def _is_port_open(self, host: str, port: int, timeout: float = 0.5) -> bool:
        """Check if a port is open."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except OSError:
            return False

    def get_report(self) -> dict:
        """Get a summary report of shadow AI risks."""
        risks = self.cached_risks if self.cached_risks else self.scan_ports()

        return {
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "total_risks": len(risks),
            "high_risk_count": len([r for r in risks if r.risk_level == "high"]),
            "medium_risk_count": len([r for r in risks if r.risk_level == "medium"]),
            "low_risk_count": len([r for r in risks if r.risk_level == "low"]),
            "risks": [
                {
                    "process_name": r.process_name,
                    "port": r.port,
                    "host": r.host,
                    "risk_level": r.risk_level,
                    "detected_at": r.detected_at.isoformat(),
                    "description": r.description,
                }
                for r in risks
            ],
        }


# Singleton instance
_scanner: ShadowAIScanner | None = None


def get_shadow_scanner() -> ShadowAIScanner:
    """Get or create the shadow scanner singleton."""
    global _scanner
    if _scanner is None:
        _scanner = ShadowAIScanner()
    return _scanner
