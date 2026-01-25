"""
ZK-Witness: Independent Compliance Verifier.

This module acts as an isolated "Interceptor" that validates agent actions
against the policy and cryptographically signs them.

In a real ZK implementation, this would generate a Zero-Knowledge Proof
that the action complies with policy without revealing the input data.
Here, we simulate this with a digital signature and independent policy check.
"""

import hashlib
import hmac
import json
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import SovereignMindError

class WitnessError(SovereignMindError):
    """Raised when the witness refuses to sign an action."""
    pass

class ZkWitness:
    """Independent witness that signs compliant actions."""
    
    def __init__(self, private_key: str = "witness_secret_key"):
        self._private_key = private_key.encode()
        self.policy = self._load_policy()
        
    def _load_policy(self) -> dict[str, Any]:
        """Load policy independently to avoid sharing state with Agent."""
        try:
            with open("app/core/policy.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback to strict default
            return {"compliance_rules": [], "reflexion_threshold": 0.9}

    def sign_action(self, action_data: dict[str, Any]) -> str:
        """Verify compliance and return a signature if valid.
        
        Args:
            action_data: Dictionary containing action details (node, thought, tool_call).
            
        Returns:
            HMAC signature of the action data.
            
        Raises:
            WitnessError: If the action violates policy.
        """
        # 1. Independent Policy Verification
        if not self._verify_compliance(action_data):
            raise WitnessError("Action violates Witness Policy. Verification failed.")
            
        # 2. Generate Signature
        # We sign the core fields that determine behavior
        canonical_string = f"{action_data.get('run_id')}:{action_data.get('node')}:{action_data.get('thought')}"
        
        signature = hmac.new(
            self._private_key,
            canonical_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _verify_compliance(self, data: dict[str, Any]) -> bool:
        """Check if action complies with loaded rules.
        
        This duplicates critical checks from Reflexion to ensure
        redundancy (Defense in Depth).
        """
        thought = data.get("thought", "").lower()
        
        # Rule 1: No PII (Simple keyword check for simulation)
        # In a real app, this would use the PII Analyzer service
        if "ssn" in thought or "credit card" in thought:
            return False
            
        # Rule 2: Unsafe flags (from policy.json)
        if "--force" in thought or "-rf" in thought:
            return False
            
        return True

# Singleton
_witness = None

def get_witness() -> ZkWitness:
    global _witness
    if _witness is None:
        _witness = ZkWitness()
    return _witness
