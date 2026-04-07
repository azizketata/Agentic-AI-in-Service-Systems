"""
Guardrails — Pre/Post Execution Policy Checks

Validates agent actions against intent contracts and governance policies.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from src.governance.intent_contract import IntentContract


@dataclass
class GuardrailResult:
    allowed: bool
    guardrail_name: str
    reason: str
    details: dict | None = None


def _load_governance_policies() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "governance_policies.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def check_action_allowlist(
    contract: IntentContract, proposed_action: str
) -> GuardrailResult:
    """Check if the proposed action is in the intent contract's acceptable set."""
    if contract.is_action_allowed(proposed_action):
        return GuardrailResult(
            allowed=True,
            guardrail_name="action_allowlist",
            reason=f"Action '{proposed_action}' is permitted",
        )
    return GuardrailResult(
        allowed=False,
        guardrail_name="action_allowlist",
        reason=f"Action '{proposed_action}' is not in acceptable actions or is forbidden",
        details={"action": proposed_action, "acceptable": contract.acceptable_actions},
    )


def check_step_limit(
    contract: IntentContract, current_steps: int
) -> GuardrailResult:
    """Check if the agent has exceeded the maximum step count."""
    if contract.is_within_step_limit(current_steps):
        return GuardrailResult(
            allowed=True,
            guardrail_name="step_limit",
            reason=f"Step {current_steps}/{contract.max_steps} within limit",
        )
    return GuardrailResult(
        allowed=False,
        guardrail_name="step_limit",
        reason=f"Step limit exceeded: {current_steps}/{contract.max_steps}",
    )


def check_confidence_gate(
    confidence: float | None, threshold: float = 0.7
) -> GuardrailResult:
    """Check if confidence meets the threshold for autonomous decision."""
    if confidence is None:
        return GuardrailResult(
            allowed=False,
            guardrail_name="confidence_gate",
            reason="No confidence score available — escalate to human",
        )
    if confidence >= threshold:
        return GuardrailResult(
            allowed=True,
            guardrail_name="confidence_gate",
            reason=f"Confidence {confidence:.2f} meets threshold {threshold}",
        )
    return GuardrailResult(
        allowed=False,
        guardrail_name="confidence_gate",
        reason=f"Confidence {confidence:.2f} below threshold {threshold} — escalate to human",
    )


def check_amount_ceiling(
    amount: float, max_auto_approve: float = 5000
) -> GuardrailResult:
    """Check if auto-approval is allowed for this amount."""
    if amount <= max_auto_approve:
        return GuardrailResult(
            allowed=True,
            guardrail_name="amount_ceiling",
            reason=f"Amount {amount:.0f} within auto-approval ceiling",
        )
    return GuardrailResult(
        allowed=False,
        guardrail_name="amount_ceiling",
        reason=f"Amount {amount:.0f} exceeds auto-approval ceiling of {max_auto_approve:.0f}",
    )


def run_all_guardrails(
    contract: IntentContract,
    proposed_action: str,
    current_steps: int,
    confidence: float | None = None,
    amount: float = 0,
) -> list[GuardrailResult]:
    """Run all configured guardrails and return results."""
    policies = _load_governance_policies()
    guardrail_configs = {g["name"]: g for g in policies["guardrails"]}
    results = []

    if guardrail_configs.get("action_allowlist", {}).get("enabled", True):
        results.append(check_action_allowlist(contract, proposed_action))

    if guardrail_configs.get("step_limit", {}).get("enabled", True):
        results.append(check_step_limit(contract, current_steps))

    if guardrail_configs.get("confidence_gate", {}).get("enabled", True):
        threshold = guardrail_configs.get("confidence_gate", {}).get("threshold", 0.7)
        results.append(check_confidence_gate(confidence, threshold))

    if guardrail_configs.get("amount_ceiling", {}).get("enabled", True):
        results.append(check_amount_ceiling(amount))

    return results


def any_guardrail_blocked(results: list[GuardrailResult]) -> bool:
    """Check if any guardrail blocked the action."""
    return any(not r.allowed for r in results)


def get_blocked_reasons(results: list[GuardrailResult]) -> list[str]:
    """Get reasons from all blocked guardrails."""
    return [r.reason for r in results if not r.allowed]
