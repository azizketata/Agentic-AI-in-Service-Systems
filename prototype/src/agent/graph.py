"""
Ungoverned Agent Graph (Agentic Mode)

LangGraph StateGraph with ReAct-style tool-calling loop.
No governance, no guardrails, no HITL — full autonomy.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.agent.nodes import assess_application, call_tools, make_decision, should_continue
from src.agent.state import AgentState


def build_ungoverned_graph(checkpointer=None):
    """
    Build the ungoverned agentic processing graph.

    Flow:
        assess_application -> [tool loop] -> make_decision -> END
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("assess_application", assess_application)
    workflow.add_node("call_tools", call_tools)
    workflow.add_node("make_decision", make_decision)

    # Entry point
    workflow.set_entry_point("assess_application")

    # After assessment, route based on LLM response
    workflow.add_conditional_edges(
        "assess_application",
        should_continue,
        {
            "call_tools": "call_tools",
            "make_decision": "make_decision",
            "end": END,
        },
    )

    # After tool execution, LLM processes results
    workflow.add_edge("call_tools", "assess_application")

    # After decision, end
    workflow.add_edge("make_decision", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


def create_initial_state(case: dict) -> AgentState:
    """Create the initial agent state from a case dictionary."""
    return AgentState(
        case_id=case["case_id"],
        amount_requested=case["amount_requested"],
        risk_tier=case["risk_tier"],
        num_events=case.get("num_events", 0),
        num_offers=case.get("num_offers", 0),
        case_duration_hours=case.get("case_duration_hours", 0),
        ground_truth=case["outcome"],
        messages=[],
        current_step="start",
        steps_taken=[],
        reasoning_trace=[],
        decision=None,
        confidence=None,
        decision_reasoning=None,
        intent_contract=None,
        autonomy_tier=None,
        governance_events=[],
        requires_human_review=False,
        human_decision=None,
    )
