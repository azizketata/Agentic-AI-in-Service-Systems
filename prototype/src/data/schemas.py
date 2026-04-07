from datetime import datetime

from pydantic import BaseModel, Field

from src.common.types import LoanOutcome, RiskTier


class ProcessEvent(BaseModel):
    activity: str
    timestamp: datetime
    resource: str | None = None
    lifecycle: str = "complete"


class LoanApplication(BaseModel):
    case_id: str
    amount_requested: float
    risk_tier: RiskTier
    events: list[ProcessEvent] = Field(default_factory=list)
    ground_truth_outcome: LoanOutcome
    num_events: int = 0
    num_offers: int = 0
    case_duration_hours: float = 0.0

    @property
    def activity_sequence(self) -> list[str]:
        return [e.activity for e in self.events]


class CaseResult(BaseModel):
    case_id: str
    mode: str  # rule_based, agentic, governed
    decision: LoanOutcome | None = None
    confidence: float | None = None
    steps_taken: list[dict] = Field(default_factory=list)
    reasoning_trace: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    governance_events: list[dict] = Field(default_factory=list)
    human_interventions: int = 0
    contract_violations: int = 0
    correct: bool = False
