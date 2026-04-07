"""
Human-in-the-Loop — Procedural Literacy Preservation (Design Principle 4)

HITL checkpoints force humans to review agent reasoning details
before approving actions, preserving procedural knowledge.
"""

from dataclasses import dataclass


@dataclass
class HITLRequest:
    case_id: str
    checkpoint_name: str
    agent_proposal: str
    reasoning_trace: list[str]
    confidence: float | None
    autonomy_tier: str
    requires_approval: bool = True


@dataclass
class HITLResponse:
    approved: bool
    human_decision: str  # "approve", "reject", "modify", "escalate"
    feedback: str = ""
    modified_action: str | None = None


def should_trigger_hitl(
    autonomy_tier: str,
    checkpoint_name: str,
    hitl_points: list[str],
) -> bool:
    """
    Determine if HITL should be triggered at this checkpoint.

    Args:
        autonomy_tier: Current autonomy tier (full_auto, supervised, restricted)
        checkpoint_name: Name of the current checkpoint
        hitl_points: List of checkpoints that require HITL for this tier
    """
    if autonomy_tier == "full_auto":
        return False
    return checkpoint_name in hitl_points


def create_hitl_request(
    case_id: str,
    checkpoint_name: str,
    agent_proposal: str,
    reasoning_trace: list[str],
    confidence: float | None,
    autonomy_tier: str,
) -> HITLRequest:
    """Create an HITL request for the Streamlit UI to display."""
    return HITLRequest(
        case_id=case_id,
        checkpoint_name=checkpoint_name,
        agent_proposal=agent_proposal,
        reasoning_trace=reasoning_trace,
        confidence=confidence,
        autonomy_tier=autonomy_tier,
    )


def simulate_hitl_response(
    request: HITLRequest,
    ground_truth: str,
) -> HITLResponse:
    """
    Simulate HITL response using ground truth for batch evaluation.

    In batch mode, the human always provides the "correct" answer
    based on ground truth data. In interactive mode, real Streamlit
    interaction replaces this function.
    """
    agent_decision = request.agent_proposal.lower()

    # Simulated human always provides ground truth
    if agent_decision == ground_truth:
        return HITLResponse(
            approved=True,
            human_decision="approve",
            feedback="Agent decision matches expected outcome",
        )
    else:
        return HITLResponse(
            approved=False,
            human_decision="modify",
            feedback=f"Corrected from {agent_decision} to {ground_truth}",
            modified_action=ground_truth,
        )
