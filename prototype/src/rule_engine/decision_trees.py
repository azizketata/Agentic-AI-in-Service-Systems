"""
Rule-Based Decision Trees for Loan Processing (RPA Baseline)

Deterministic if/else logic derived from BPI 2012 process patterns.
No LLM involvement — pure programmatic decisions.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.common.types import LoanOutcome


@dataclass
class RuleDecision:
    outcome: str  # "auto_approve", "standard_review", "senior_review", "decline", "incomplete"
    final_decision: LoanOutcome | None = None
    reason: str = ""
    confidence: float = 1.0  # Rules are always 100% confident
    steps: list[dict] = field(default_factory=list)


def _load_rule_settings() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def evaluate_loan(
    amount: float,
    num_events: int,
    num_offers: int,
    case_duration_hours: float,
) -> RuleDecision:
    """
    Deterministic loan evaluation based on rules.

    Mimics RPA: rigid thresholds, no reasoning, binary outcomes.
    """
    settings = _load_rule_settings()
    rules = settings["rule_engine"]
    steps = []

    # Step 1: Check amount ceiling
    steps.append({
        "step": "amount_check",
        "rule": f"amount <= {rules['max_loan_amount']}",
        "value": amount,
        "passed": amount <= rules["max_loan_amount"],
    })
    if amount > rules["max_loan_amount"]:
        return RuleDecision(
            outcome="decline",
            final_decision=LoanOutcome.DECLINED,
            reason=f"Amount {amount:.0f} exceeds maximum {rules['max_loan_amount']}",
            steps=steps,
        )

    # Step 2: Check for minimum viability (amount > 0)
    steps.append({
        "step": "viability_check",
        "rule": "amount > 0",
        "value": amount,
        "passed": amount > 0,
    })
    if amount <= 0:
        return RuleDecision(
            outcome="decline",
            final_decision=LoanOutcome.DECLINED,
            reason="Invalid loan amount",
            steps=steps,
        )

    # Step 3: Auto-approve small loans
    steps.append({
        "step": "auto_approve_check",
        "rule": f"amount <= {rules['auto_approve_max']}",
        "value": amount,
        "passed": amount <= rules["auto_approve_max"],
    })
    if amount <= rules["auto_approve_max"]:
        return RuleDecision(
            outcome="auto_approve",
            final_decision=LoanOutcome.APPROVED,
            reason=f"Amount {amount:.0f} below auto-approval threshold",
            steps=steps,
        )

    # Step 4: Route based on amount tier
    steps.append({
        "step": "tier_routing",
        "rule": f"amount <= {rules['standard_review_max']} -> standard, else senior",
        "value": amount,
        "passed": True,
    })
    if amount <= rules["standard_review_max"]:
        # Standard review: simulate approval based on process completeness heuristic
        # More offers = more engagement = more likely approved
        has_offers = num_offers > 0
        reasonable_duration = 0 < case_duration_hours < 2000

        steps.append({
            "step": "standard_review",
            "rule": "has_offers AND reasonable_duration",
            "has_offers": has_offers,
            "reasonable_duration": reasonable_duration,
            "passed": has_offers and reasonable_duration,
        })
        if has_offers and reasonable_duration:
            return RuleDecision(
                outcome="standard_review",
                final_decision=LoanOutcome.APPROVED,
                reason="Standard review: offers present, reasonable timeline",
                steps=steps,
            )
        else:
            return RuleDecision(
                outcome="standard_review",
                final_decision=LoanOutcome.DECLINED,
                reason="Standard review: missing offers or unusual timeline",
                steps=steps,
            )
    else:
        # Senior review: stricter criteria
        has_offers = num_offers > 0
        sufficient_events = num_events >= 10  # More touchpoints expected for large loans
        reasonable_duration = 0 < case_duration_hours < 2000

        steps.append({
            "step": "senior_review",
            "rule": "has_offers AND sufficient_events AND reasonable_duration",
            "has_offers": has_offers,
            "sufficient_events": sufficient_events,
            "reasonable_duration": reasonable_duration,
            "passed": has_offers and sufficient_events and reasonable_duration,
        })
        if has_offers and sufficient_events and reasonable_duration:
            return RuleDecision(
                outcome="senior_review",
                final_decision=LoanOutcome.APPROVED,
                reason="Senior review: all criteria met for high-value loan",
                steps=steps,
            )
        else:
            return RuleDecision(
                outcome="senior_review",
                final_decision=LoanOutcome.DECLINED,
                reason="Senior review: insufficient evidence for high-value loan",
                steps=steps,
            )
