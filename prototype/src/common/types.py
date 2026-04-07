from enum import Enum


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AutonomyTier(str, Enum):
    FULL_AUTO = "full_auto"
    SUPERVISED = "supervised"
    RESTRICTED = "restricted"


class LoanOutcome(str, Enum):
    APPROVED = "approved"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class ProcessingMode(str, Enum):
    RULE_BASED = "rule_based"
    AGENTIC = "agentic"
    GOVERNED = "governed"


class GovernanceEventType(str, Enum):
    STEP = "step"
    DECISION = "decision"
    ESCALATION = "escalation"
    VIOLATION = "violation"
    OVERRIDE = "override"
    HITL_APPROVAL = "hitl_approval"
    HITL_REJECTION = "hitl_rejection"
    CONTRACT_CREATED = "contract_created"
    GUARDRAIL_TRIGGERED = "guardrail_triggered"
