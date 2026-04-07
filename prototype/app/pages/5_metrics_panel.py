"""Page 5: Metrics Panel — Quantitative evaluation and paper-ready exports."""

from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parent.parent)); import path_setup

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Metrics Panel", layout="wide")
st.title("Metrics Panel")
st.markdown("Quantitative evaluation results across all three modes. Paper-ready exports.")

st.divider()

# Expected metrics table
st.subheader("Aggregate Comparison")

metrics_template = pd.DataFrame({
    "Metric": [
        "Accuracy",
        "Avg Steps to Decision",
        "Avg Processing Time (ms)",
        "Avg Confidence",
        "Governance Events (avg)",
        "Human Intervention Rate",
        "Contract Violation Rate",
    ],
    "Rule-Based": ["—", "—", "—", "1.00", "0", "0%", "N/A"],
    "Agentic": ["—", "—", "—", "—", "0", "0%", "N/A"],
    "Governed": ["—", "—", "—", "—", "—", "—", "—"],
})

st.dataframe(metrics_template, width="stretch", hide_index=True)

st.divider()

# Per-case scatter plot placeholder
st.subheader("Decision Accuracy by Loan Amount")

try:
    sample_dir = path_setup.SAMPLE_DIR
    cases_df = pd.read_parquet(sample_dir / "sample_cases.parquet")

    fig = px.scatter(
        cases_df,
        x="amount_requested",
        y="num_events",
        color="outcome",
        size="case_duration_hours",
        title="Case Characteristics (Amount vs Events, colored by outcome)",
        labels={
            "amount_requested": "Loan Amount (EUR)",
            "num_events": "Number of Events",
            "outcome": "Outcome",
        },
        height=450,
    )
    st.plotly_chart(fig, width="stretch")
except Exception:
    st.info("Load sample data to see visualizations.")

st.divider()

# Export section
st.subheader("Paper-Ready Exports")
st.markdown("Download tables and figures for the ICIS paper.")

col1, col2, col3 = st.columns(3)

with col1:
    st.download_button(
        "Download Comparison Table (CSV)",
        data=metrics_template.to_csv(index=False),
        file_name="comparison_table.csv",
        mime="text/csv",
    )

with col2:
    st.download_button(
        "Download Metrics Template (CSV)",
        data=metrics_template.to_csv(index=False),
        file_name="metrics_template.csv",
        mime="text/csv",
    )

with col3:
    st.info("Process all cases to enable full exports.")

st.divider()

st.subheader("Statistical Summary")
st.markdown(
    "After running all cases through the three modes, this section will show:\n"
    "- Confidence intervals for accuracy\n"
    "- Per-tier accuracy breakdown\n"
    "- Correlation between loan amount and decision quality\n"
    "- Human override pattern analysis"
)

st.divider()

# ── Process Conformance Analysis ────────────────────────────────
st.subheader("Process Conformance Analysis")
st.markdown(
    "How well does each mode's process path align with the discovered BPI 2012 process model? "
    "This demonstrates **lifecycle collapse** — the agentic system generates process paths at runtime."
)


@st.cache_data
def load_conformance():
    try:
        from src.evaluation.conformance import run_conformance_analysis
        events_path = path_setup.SAMPLE_DIR / "sample_events.parquet"
        results_dir = path_setup.RESULTS_DIR
        return run_conformance_analysis(events_path, results_dir)
    except Exception as e:
        return {"error": str(e)}


if st.button("Run Conformance Analysis", help="Takes ~30 seconds"):
    with st.spinner("Discovering process model and computing conformance..."):
        conf = load_conformance()
        st.session_state["conformance"] = conf
else:
    conf = st.session_state.get("conformance")

if conf and "error" not in conf:
    col_r, col_a, col_g = st.columns(3)

    col_r.metric("Rule-Based Fitness", f"{conf['rule_based'].get('fitness', 0):.2f}")
    col_r.caption(f"{conf['rule_based'].get('variant_count', 0)} process variants")

    col_a.metric("Agentic Fitness", f"{conf['agentic'].get('fitness', 0):.2f}")
    col_a.caption(f"{conf['agentic'].get('variant_count', 0)} process variants")

    col_g.metric("Governed Fitness", f"{conf['governed'].get('fitness', 0):.2f}")
    col_g.caption(f"{conf['governed'].get('variant_count', 0)} process variants")

    # Conformance bar chart
    conf_df = pd.DataFrame({
        "Metric": ["Fitness", "Variants"],
        "Rule-Based": [conf["rule_based"].get("fitness", 0), conf["rule_based"].get("variant_count", 0)],
        "Agentic": [conf["agentic"].get("fitness", 0), conf["agentic"].get("variant_count", 0)],
        "Governed": [conf["governed"].get("fitness", 0), conf["governed"].get("variant_count", 0)],
    })
    st.dataframe(conf_df, width="stretch", hide_index=True)

    with st.expander("Lifecycle Collapse Evidence"):
        st.markdown(conf.get("lifecycle_collapse_evidence", ""))

elif conf and "error" in conf:
    st.warning(f"Conformance analysis error: {conf['error']}")
else:
    st.info("Click 'Run Conformance Analysis' to compute process conformance metrics.")
