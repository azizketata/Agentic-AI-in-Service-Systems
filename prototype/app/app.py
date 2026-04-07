"""
Streamlit Dashboard — Entry Point

Governable Agentic Service Systems Prototype
"""

import sys
from pathlib import Path

# Add prototype root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Agentic Governance Prototype",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Governable Agentic Service Systems")
st.markdown(
    "**DSR Prototype** — Comparing Rule-Based, Agentic, and Governed "
    "processing of loan applications (BPI Challenge 2012)"
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Rule-Based (RPA)")
    st.markdown(
        "Deterministic if/else decision trees. "
        "No LLM, no reasoning. Fixed thresholds and routing."
    )

with col2:
    st.subheader("Agentic (LangGraph)")
    st.markdown(
        "LLM-powered ReAct agent. Autonomous reasoning, "
        "tool use, and decision-making. Full autonomy."
    )

with col3:
    st.subheader("Governed (DSR Artifact)")
    st.markdown(
        "Same agent with governance guardrails: "
        "intent contracts, graduated autonomy, HITL checkpoints, audit trail."
    )

st.divider()

st.markdown("### Design Principles Demonstrated")

principles = {
    "1. Prospective Intent Contracts": "Machine-readable contracts created before agent execution — goal, constraints, allowed actions",
    "2. Graduated Autonomy": "Agent freedom varies by decision risk — full-auto, supervised, or restricted",
    "3. Reasoning Trace Transparency": "Every reasoning step logged in human-readable format",
    "4. Procedural Literacy Preservation": "HITL checkpoints keep humans engaged with process details",
}

for title, desc in principles.items():
    st.markdown(f"**{title}** — {desc}")

st.divider()
st.markdown("Navigate using the sidebar to explore the different views.")
