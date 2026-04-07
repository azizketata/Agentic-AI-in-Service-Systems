"""
Graduated Autonomy (Design Principle 2)

Risk-tier classification determines agent freedom level:
- full_auto: end-to-end, post-hoc review only
- supervised: agent reasons freely, human approves final decision
- restricted: human approves each significant action
"""

from pathlib import Path

import yaml

from src.common.types import AutonomyTier, RiskTier


def _load_governance_policies() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "governance_policies.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def classify_autonomy_tier(
    amount: float,
    risk_tier: str | RiskTier,
) -> AutonomyTier:
    """
    Classify the autonomy tier based on loan amount and risk tier.

    Higher risk = more human oversight required.
    """
    policies = _load_governance_policies()
    tiers = policies["autonomy_tiers"]

    if isinstance(risk_tier, RiskTier):
        risk_tier = risk_tier.value

    # Check restricted first (most restrictive)
    restricted = tiers["restricted"]["conditions"]
    if amount >= restricted.get("min_amount", float("inf")) or risk_tier == "high":
        return AutonomyTier.RESTRICTED

    # Check full_auto
    full_auto = tiers["full_auto"]["conditions"]
    if amount <= full_auto["max_amount"] and risk_tier == "low":
        return AutonomyTier.FULL_AUTO

    # Default to supervised
    return AutonomyTier.SUPERVISED


def get_hitl_points(tier: AutonomyTier) -> list[str]:
    """Get the list of HITL checkpoint names for a given autonomy tier."""
    policies = _load_governance_policies()
    tier_config = policies["autonomy_tiers"].get(tier.value, {})
    return tier_config.get("hitl_points", [])


def get_tier_description(tier: AutonomyTier) -> str:
    """Get human-readable description of an autonomy tier."""
    policies = _load_governance_policies()
    tier_config = policies["autonomy_tiers"].get(tier.value, {})
    return tier_config.get("description", "Unknown tier")
