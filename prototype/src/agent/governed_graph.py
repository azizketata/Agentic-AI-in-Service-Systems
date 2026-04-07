"""
Governed Agent Graph (DSR Artifact Core)

LangGraph StateGraph with governance mechanisms:
- Prospective Intent Contracts (Principle 1)
- Graduated Autonomy (Principle 2)
- Reasoning Trace Transparency (Principle 3)
- Procedural Literacy Preservation via HITL (Principle 4)
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.agent.nodes import assess_application, call_tools, make_decision, should_continue
from src.agent.state import AgentState
from src.common.types import GovernanceEventType
from src.governance.audit_logger import AuditEntry, audit_log
from src.governance.autonomy_tiers import classify_autonomy_tier, get_hitl_points
from src.governance.guardrails import (
    any_guardrail_blocked,
    get_blocked_reasons,
    run_all_guardrails,
)
from src.governance.hitl import should_trigger_hitl, simulate_hitl_response, create_hitl_request
from src.governance.intent_contract import create_intent_contract


# ── Governance Nodes ────────────────────────────────────────────────


def create_contract_node(state: AgentState) -> dict:
    """Create an intent contract before processing begins."""
    tier = classify_autonomy_tier(state["amount_requested"], state["risk_tier"])
    contract = create_intent_contract(
        case_id=state["case_id"],
        amount=state["amount_requested"],
        autonomy_tier=tier.value,
    )

    audit_log.log(
        case_id=state["case_id"],
        mode="governed",
        event_type=GovernanceEventType.CONTRACT_CREATED,
        step_number=0,
        action="create_intent_contract",
        reasoning=f"Contract created for {tier.value} autonomy",
        governance_tier=tier.value,
    )

    return {
        "intent_contract": contract.to_dict(),
        "autonomy_tier": tier.value,
        "current_step": "contract_created",
        "reasoning_trace": state.get("reasoning_trace", []) + [
            f"[GOV] Intent contract created. Autonomy tier: {tier.value}"
        ],
        "governance_events": state.get("governance_events", []) + [
            {"event": "contract_created", "tier": tier.value}
        ],
    }


def pre_decision_guardrail(state: AgentState) -> dict:
    """Run guardrails before the final decision is executed."""
    from src.governance.intent_contract import IntentContract

    contract_data = state.get("intent_contract")
    if not contract_data:
        return {}

    contract = IntentContract.from_dict(contract_data)
    current_steps = len(state.get("steps_taken", []))

    results = run_all_guardrails(
        contract=contract,
        proposed_action="make_decision",
        current_steps=current_steps,
        confidence=state.get("confidence"),
        amount=state["amount_requested"],
    )

    blocked = any_guardrail_blocked(results)
    blocked_reasons = get_blocked_reasons(results)

    guardrail_dicts = [
        {"name": r.guardrail_name, "allowed": r.allowed, "reason": r.reason}
        for r in results
    ]

    event_type = GovernanceEventType.GUARDRAIL_TRIGGERED if blocked else GovernanceEventType.STEP
    audit_log.log(
        case_id=state["case_id"],
        mode="governed",
        event_type=event_type,
        step_number=current_steps,
        action="pre_decision_guardrail",
        reasoning="; ".join(blocked_reasons) if blocked else "All guardrails passed",
        confidence=state.get("confidence"),
        governance_tier=state.get("autonomy_tier"),
        contract_compliant=not blocked,
        guardrail_results=guardrail_dicts,
    )

    trace_entries = []
    for r in results:
        status = "PASS" if r.allowed else "BLOCK"
        trace_entries.append(f"[GUARDRAIL] {r.guardrail_name}: {status} — {r.reason}")

    new_gov_events = [{"event": "guardrail_check", "blocked": blocked, "reasons": blocked_reasons}]

    if blocked:
        # If blocked, flag for human review
        new_gov_events.append({"event": "escalation", "reason": "Guardrail blocked"})
        return {
            "requires_human_review": True,
            "reasoning_trace": state.get("reasoning_trace", []) + trace_entries,
            "governance_events": state.get("governance_events", []) + new_gov_events,
        }

    return {
        "requires_human_review": False,
        "reasoning_trace": state.get("reasoning_trace", []) + trace_entries,
        "governance_events": state.get("governance_events", []) + new_gov_events,
    }


def human_review_node(state: AgentState) -> dict:
    """
    HITL checkpoint — in batch mode uses simulated human, in interactive
    mode this node is interrupted and the Streamlit UI handles the response.
    """
    hitl_points = get_hitl_points(
        classify_autonomy_tier(state["amount_requested"], state["risk_tier"])
    )

    needs_hitl = should_trigger_hitl(
        autonomy_tier=state.get("autonomy_tier", "supervised"),
        checkpoint_name="final_decision",
        hitl_points=hitl_points,
    ) or state.get("requires_human_review", False)

    if not needs_hitl:
        return {
            "reasoning_trace": state.get("reasoning_trace", []) + [
                "[HITL] No human review required for this tier/checkpoint"
            ],
        }

    # Create HITL request
    request = create_hitl_request(
        case_id=state["case_id"],
        checkpoint_name="final_decision",
        agent_proposal=state.get("decision", "unknown"),
        reasoning_trace=state.get("reasoning_trace", []),
        confidence=state.get("confidence"),
        autonomy_tier=state.get("autonomy_tier", "supervised"),
    )

    # In batch mode, simulate; in interactive mode, this would be interrupted
    response = simulate_hitl_response(request, state["ground_truth"])

    event_type = (
        GovernanceEventType.HITL_APPROVAL
        if response.approved
        else GovernanceEventType.OVERRIDE
    )

    audit_log.log(
        case_id=state["case_id"],
        mode="governed",
        event_type=event_type,
        step_number=len(state.get("steps_taken", [])),
        action="human_review",
        reasoning=response.feedback,
        confidence=state.get("confidence"),
        governance_tier=state.get("autonomy_tier"),
        human_involved=True,
        human_decision=response.human_decision,
    )

    trace_entry = f"[HITL] Human review: {response.human_decision} — {response.feedback}"

    updates = {
        "human_decision": response.human_decision,
        "reasoning_trace": state.get("reasoning_trace", []) + [trace_entry],
        "governance_events": state.get("governance_events", []) + [
            {"event": "hitl_review", "decision": response.human_decision, "approved": response.approved}
        ],
    }

    # If human overrode the decision, update it
    if response.modified_action:
        updates["decision"] = response.modified_action
        updates["reasoning_trace"] = updates["reasoning_trace"] + [
            f"[HITL] Decision overridden to: {response.modified_action}"
        ]

    return updates


# ── Routing Functions ───────────────────────────────────────────────


def governed_should_continue(state: AgentState) -> str:
    """Routing after assessment — same as ungoverned but with guardrails."""
    return should_continue(state)


def post_decision_route(state: AgentState) -> str:
    """After decision, route to guardrail check."""
    return "pre_decision_guardrail"


def post_guardrail_route(state: AgentState) -> str:
    """After guardrails, route to human review or end."""
    if state.get("requires_human_review", False):
        return "human_review"
    # Check if HITL is needed based on autonomy tier
    hitl_points = get_hitl_points(
        classify_autonomy_tier(state["amount_requested"], state["risk_tier"])
    )
    if should_trigger_hitl(state.get("autonomy_tier", "supervised"), "final_decision", hitl_points):
        return "human_review"
    return "end"


# ── Graph Builder ───────────────────────────────────────────────────


def build_governed_graph(checkpointer=None):
    """
    Build the governed agentic processing graph.

    Flow:
        create_contract -> assess_application -> [tool loop] ->
        make_decision -> pre_decision_guardrail ->
        [human_review if needed] -> END
    """
    workflow = StateGraph(AgentState)

    # Governance nodes
    workflow.add_node("create_contract", create_contract_node)
    workflow.add_node("pre_decision_guardrail", pre_decision_guardrail)
    workflow.add_node("human_review", human_review_node)

    # Processing nodes (shared with ungoverned)
    workflow.add_node("assess_application", assess_application)
    workflow.add_node("call_tools", call_tools)
    workflow.add_node("make_decision", make_decision)

    # Entry: create contract first
    workflow.set_entry_point("create_contract")

    # Contract -> assessment
    workflow.add_edge("create_contract", "assess_application")

    # Assessment -> tool loop or decision
    workflow.add_conditional_edges(
        "assess_application",
        governed_should_continue,
        {
            "call_tools": "call_tools",
            "make_decision": "make_decision",
            "end": END,
        },
    )

    # Tool results -> back to assessment
    workflow.add_edge("call_tools", "assess_application")

    # Decision -> guardrail check
    workflow.add_edge("make_decision", "pre_decision_guardrail")

    # Guardrail -> human review or end
    workflow.add_conditional_edges(
        "pre_decision_guardrail",
        post_guardrail_route,
        {
            "human_review": "human_review",
            "end": END,
        },
    )

    # Human review -> end
    workflow.add_edge("human_review", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)
