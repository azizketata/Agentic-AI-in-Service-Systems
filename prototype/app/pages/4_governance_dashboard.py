"""Page 4: Governance Dashboard — Violations, overrides, escalations, audit log."""

from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parent.parent)); import path_setup

import streamlit as st
import pandas as pd

from components.charts import tier_distribution_pie

st.set_page_config(page_title="Governance Dashboard", layout="wide")
st.title("Governance Dashboard")
st.markdown("Monitor agent governance: violations, escalations, HITL events, and compliance.")

st.divider()

# Summary cards
col1, col2, col3, col4 = st.columns(4)

# Try to load audit log data
try:
    from src.governance.audit_logger import audit_log
    summary = audit_log.summary()
    col1.metric("Total Events", summary["total_entries"])
    col2.metric("Violations", summary["violations"])
    col3.metric("Escalations", summary["escalations"])
    col4.metric("Human Reviews", summary["hitl_events"])
except Exception:
    col1.metric("Total Events", 0)
    col2.metric("Violations", 0)
    col3.metric("Escalations", 0)
    col4.metric("Human Reviews", 0)

st.divider()

# Autonomy tier distribution
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Autonomy Tier Distribution")

    # Try to load from sample cases
    try:
        sample_dir = path_setup.SAMPLE_DIR
        cases_df = pd.read_parquet(sample_dir / "sample_cases.parquet")

        from src.governance.autonomy_tiers import classify_autonomy_tier
        tiers = cases_df.apply(
            lambda r: classify_autonomy_tier(r["amount_requested"], r["risk_tier"]).value,
            axis=1,
        )
        tier_counts = tiers.value_counts().to_dict()
        fig = tier_distribution_pie(tier_counts)
        st.plotly_chart(fig, width="stretch")
    except Exception:
        st.info("Load sample data to see tier distribution.")

with col_right:
    st.subheader("Governance Design Principles")
    st.markdown("""
    | Principle | Status |
    |-----------|--------|
    | Prospective Intent Contracts | Active |
    | Graduated Autonomy | Active |
    | Reasoning Trace Transparency | Active |
    | Procedural Literacy Preservation | Active |
    """)

st.divider()

# Audit log table
st.subheader("Audit Event Log")

try:
    if audit_log.entries:
        log_df = audit_log.to_dataframe()
        st.dataframe(
            log_df[["timestamp", "case_id", "event_type", "action", "reasoning",
                     "governance_tier", "contract_compliant", "human_involved"]],
            width="stretch",
            height=400,
        )
    else:
        st.info(
            "No governance events recorded yet. "
            "Process cases through the governed agent to see audit data."
        )
except Exception:
    st.info("Process cases through the governed agent to populate the audit log.")

# Intent contract compliance
st.subheader("Intent Contract Compliance")
st.markdown(
    "Tracks what percentage of governed agent executions "
    "completed within their intent contract boundaries."
)

compliance_placeholder = pd.DataFrame({
    "Metric": [
        "Cases within step limit",
        "Cases with no forbidden actions",
        "Cases with confidence above threshold",
        "Overall contract compliance",
    ],
    "Value": ["—", "—", "—", "—"],
})
st.table(compliance_placeholder)
