"""
LangGraph Agent State Definition

Shared state for both ungoverned and governed agent graphs.
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Case data
    case_id: str
    amount_requested: float
    risk_tier: str
    num_events: int
    num_offers: int
    case_duration_hours: float
    ground_truth: str

    # LLM conversation
    messages: Annotated[list, add_messages]

    # Processing tracking
    current_step: str
    steps_taken: list[dict]
    reasoning_trace: list[str]

    # Decision
    decision: str | None          # approved, declined, cancelled
    confidence: float | None
    decision_reasoning: str | None

    # Governance (used by governed graph, ignored by ungoverned)
    intent_contract: dict | None
    autonomy_tier: str | None
    governance_events: list[dict]
    requires_human_review: bool
    human_decision: str | None
