"""
Audit Logger — Reasoning Trace Transparency (Design Principle 3)

Structured logging of every governance event for auditability.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime

from src.common.types import GovernanceEventType


@dataclass
class AuditEntry:
    timestamp: str
    case_id: str
    mode: str
    event_type: str
    step_number: int
    action: str
    reasoning: str
    confidence: float | None = None
    governance_tier: str | None = None
    contract_compliant: bool = True
    human_involved: bool = False
    human_decision: str | None = None
    guardrail_results: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class AuditLog:
    """In-memory audit log for a processing session."""

    def __init__(self):
        self.entries: list[AuditEntry] = []

    def log(
        self,
        case_id: str,
        mode: str,
        event_type: GovernanceEventType | str,
        step_number: int,
        action: str,
        reasoning: str,
        **kwargs,
    ) -> AuditEntry:
        if isinstance(event_type, GovernanceEventType):
            event_type = event_type.value

        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            case_id=case_id,
            mode=mode,
            event_type=event_type,
            step_number=step_number,
            action=action,
            reasoning=reasoning,
            **kwargs,
        )
        self.entries.append(entry)
        return entry

    def get_entries_for_case(self, case_id: str) -> list[AuditEntry]:
        return [e for e in self.entries if e.case_id == case_id]

    def get_violations(self) -> list[AuditEntry]:
        return [e for e in self.entries if e.event_type == "violation"]

    def get_escalations(self) -> list[AuditEntry]:
        return [e for e in self.entries if e.event_type == "escalation"]

    def get_overrides(self) -> list[AuditEntry]:
        return [e for e in self.entries if e.event_type == "override"]

    def get_hitl_events(self) -> list[AuditEntry]:
        return [e for e in self.entries if e.human_involved]

    def summary(self) -> dict:
        return {
            "total_entries": len(self.entries),
            "cases": len(set(e.case_id for e in self.entries)),
            "violations": len(self.get_violations()),
            "escalations": len(self.get_escalations()),
            "overrides": len(self.get_overrides()),
            "hitl_events": len(self.get_hitl_events()),
        }

    def to_json(self) -> str:
        return json.dumps([e.to_dict() for e in self.entries], indent=2)

    def to_dataframe(self):
        import pandas as pd
        return pd.DataFrame([e.to_dict() for e in self.entries])


# Global audit log instance
audit_log = AuditLog()
