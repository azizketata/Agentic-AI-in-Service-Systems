"""
Prospective Intent Contracts (Design Principle 1)

Machine-readable contracts created BEFORE agent execution that specify:
- Goal, constraints, acceptable actions, escalation triggers
- Validated at every governance checkpoint
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml


@dataclass
class IntentContract:
    case_id: str
    goal: str
    constraints: list[str]
    acceptable_actions: list[str]
    forbidden_actions: list[str]
    escalation_triggers: list[str]
    max_steps: int
    timeout_seconds: int
    autonomy_tier: str
    created_at: datetime = field(default_factory=datetime.now)

    def is_action_allowed(self, action: str) -> bool:
        """Check if an action is permitted under this contract."""
        if action in self.forbidden_actions:
            return False
        if action in self.acceptable_actions:
            return True
        return False

    def is_within_step_limit(self, current_steps: int) -> bool:
        return current_steps < self.max_steps

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "goal": self.goal,
            "constraints": self.constraints,
            "acceptable_actions": self.acceptable_actions,
            "forbidden_actions": self.forbidden_actions,
            "escalation_triggers": self.escalation_triggers,
            "max_steps": self.max_steps,
            "timeout_seconds": self.timeout_seconds,
            "autonomy_tier": self.autonomy_tier,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IntentContract":
        data = data.copy()
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


def _load_governance_policies() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "governance_policies.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def create_intent_contract(
    case_id: str,
    amount: float,
    autonomy_tier: str,
) -> IntentContract:
    """
    Create an intent contract for a loan application case.

    The contract is generated BEFORE the agent starts processing,
    establishing boundaries for its behavior.
    """
    policies = _load_governance_policies()
    defaults = policies["intent_contract"]

    constraints = [
        f"Loan amount: EUR {amount:,.2f}",
        f"Autonomy tier: {autonomy_tier}",
    ]
    if amount > 25000:
        constraints.append("High-value loan: senior review policies apply")
    if amount > 50000:
        constraints.append("Amount exceeds personal loan ceiling — must decline or redirect")

    escalation_triggers = [
        "confidence < 0.7",
    ]
    if autonomy_tier == "supervised":
        escalation_triggers.append("final_decision requires human approval")
    elif autonomy_tier == "restricted":
        escalation_triggers.append("every significant action requires human approval")

    return IntentContract(
        case_id=case_id,
        goal=f"Evaluate loan application {case_id} for approval or decline",
        constraints=constraints,
        acceptable_actions=defaults["acceptable_actions"],
        forbidden_actions=defaults["forbidden_actions"],
        escalation_triggers=escalation_triggers,
        max_steps=defaults["max_steps"],
        timeout_seconds=defaults["timeout_seconds"],
        autonomy_tier=autonomy_tier,
    )
