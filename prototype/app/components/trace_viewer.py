"""Reasoning trace rendering component."""

import streamlit as st


def render_trace(trace: list[str], title: str = "Reasoning Trace"):
    """Render a reasoning trace as an expandable list of steps."""
    st.subheader(title)

    if not trace:
        st.info("No reasoning trace available.")
        return

    for i, entry in enumerate(trace):
        # Color-code by type
        if "[GOV]" in entry or "[GUARDRAIL]" in entry:
            icon = "🛡️"
            color = "blue"
        elif "[HITL]" in entry:
            icon = "👤"
            color = "orange"
        elif "[TOOL]" in entry:
            icon = "🔧"
            color = "green"
        elif "[DECIDE]" in entry:
            icon = "⚖️"
            color = "red"
        elif "[ASSESS]" in entry:
            icon = "📋"
            color = "violet"
        else:
            icon = "📝"
            color = "gray"

        with st.expander(f"{icon} Step {i+1}: {entry[:80]}...", expanded=i < 3):
            st.markdown(f":{color}[{entry}]")


def render_governance_annotations(governance_events: list[dict]):
    """Render governance events as annotations."""
    if not governance_events:
        st.info("No governance events recorded.")
        return

    for event in governance_events:
        event_type = event.get("event", "unknown")

        if event_type == "contract_created":
            st.success(f"📄 Contract created — Tier: {event.get('tier', 'N/A')}")
        elif event_type == "guardrail_check":
            if event.get("blocked"):
                st.error(f"🚫 Guardrail blocked: {', '.join(event.get('reasons', []))}")
            else:
                st.success("✅ All guardrails passed")
        elif event_type == "hitl_review":
            decision = event.get("decision", "N/A")
            if event.get("approved"):
                st.success(f"👤 Human approved: {decision}")
            else:
                st.warning(f"👤 Human override: {decision}")
        elif event_type == "escalation":
            st.warning(f"⚠️ Escalated: {event.get('reason', 'N/A')}")
