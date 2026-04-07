"""Page 6: Qualitative Trace Analysis — Failure categorization, guardrail effectiveness, paper examples."""

from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parent.parent)); import path_setup

import streamlit as st
import pandas as pd

from components.charts import failure_type_pie, confidence_histogram
from components.trace_viewer import render_trace

st.set_page_config(page_title="Trace Analysis", layout="wide")
st.title("Qualitative Trace Analysis")
st.markdown("Categorize agent failures, evaluate guardrail effectiveness, and generate paper examples.")


@st.cache_data
def load_analysis():
    from src.evaluation.trace_analysis import run_full_trace_analysis
    return run_full_trace_analysis(
        path_setup.RESULTS_DIR,
        path_setup.SAMPLE_DIR,
    )


try:
    analysis = load_analysis()
except Exception as e:
    st.error(f"Could not load analysis: {e}")
    st.stop()

fs = analysis["failure_summary"]
failures = analysis["classified_failures"]
catches = analysis["guardrail_catches"]
misses = analysis["guardrail_misses"]
examples = analysis["paper_examples"]
all_results = analysis["all_results"]

# ── Metrics Row ─────────────────────────────────────────────────
st.subheader("Agentic Mode Failure Overview")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Failures", fs["total_failures"], f"of {len(all_results['agentic'])} cases")
col2.metric("Cancelled Blind Spots", fs["by_type"].get("cancelled_blind_spot", 0))
col3.metric("False Approvals", fs["by_type"].get("false_approval", 0))
col4.metric("False Declines", fs["by_type"].get("false_decline", 0))

col5, col6 = st.columns(2)
col5.metric("Avg Confidence When Wrong", f"{fs['avg_confidence_when_wrong']:.0%}")
col6.metric("High-Confidence Errors (>=80%)", fs["high_confidence_errors"])

st.divider()

# ── Charts ──────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    fig_pie = failure_type_pie(fs)
    st.plotly_chart(fig_pie, width="stretch")

with col_right:
    correct_cases = [r for r in all_results["agentic"] if r.get("correct")]
    fig_hist = confidence_histogram(failures, correct_cases)
    st.plotly_chart(fig_hist, width="stretch")

st.divider()

# ── Guardrail Effectiveness ─────────────────────────────────────
st.subheader("Guardrail Effectiveness")
col_catch, col_miss = st.columns(2)

with col_catch:
    st.metric("Errors Caught by Governance", len(catches))
    st.caption("Cases where governed mode was correct but agentic was wrong")
    if catches:
        with st.expander(f"View {len(catches)} caught cases"):
            for c in catches[:10]:
                st.markdown(
                    f"**{c['case_id']}**: Agent said `{c['agentic_decision']}` "
                    f"(conf: {c['agentic_confidence']:.0%}), governed corrected to `{c['governed_decision']}`"
                )

with col_miss:
    st.metric("Errors Missed by Governance", len(misses))
    st.caption("Cases where governed mode was also wrong despite governance")
    if misses:
        with st.expander(f"View {len(misses)} missed cases"):
            for m in misses:
                st.markdown(
                    f"**{m['case_id']}**: Governed decided `{m['decision']}`, "
                    f"HITL interventions: {m['human_interventions']}, "
                    f"governance events: {m['num_governance_events']}"
                )

st.divider()

# ── Case Deep-Dive ──────────────────────────────────────────────
st.subheader("Case Deep-Dive: Cross-Mode Comparison")

failed_ids = [f["case_id"] for f in failures]
selected_case_id = st.selectbox("Select a failed case", failed_ids)

if selected_case_id:
    cross = analysis["cross_mode_comparisons"].get(selected_case_id, {})
    failure_info = next((f for f in failures if f["case_id"] == selected_case_id), None)

    if failure_info:
        st.info(
            f"**Failure type:** {failure_info['failure_type'].replace('_', ' ').title()} | "
            f"**Ground truth:** {failure_info['ground_truth']} | "
            f"**Agent confidence:** {failure_info['confidence']:.0%}"
        )

    col_r, col_a, col_g = st.columns(3)

    for col, mode, label in [
        (col_r, "rule_based", "Rule-Based"),
        (col_a, "agentic", "Agentic"),
        (col_g, "governed", "Governed"),
    ]:
        with col:
            st.markdown(f"### {label}")
            data = cross.get(mode)
            if data:
                correct_icon = "OK" if data["correct"] else "WRONG"
                st.markdown(f"**Decision:** `{data['decision']}` ({correct_icon})")
                if data.get("confidence") is not None:
                    st.markdown(f"**Confidence:** {data['confidence']:.0%}")
                render_trace(data.get("reasoning_trace", []), f"{label} Trace")
            else:
                st.warning("No data")

st.divider()

# ── Paper Examples ──────────────────────────────────────────────
st.subheader("Paper-Ready Examples")
st.markdown("Auto-generated narrative blocks for the ICIS paper Results section.")

for ex in examples:
    with st.expander(f"{ex['title']} — Case {ex['case_id']}", expanded=False):
        st.markdown(ex["narrative"])
        if ex.get("key_trace_excerpt"):
            st.markdown("**Key trace excerpt:**")
            for line in ex["key_trace_excerpt"]:
                st.code(line, language=None)

# Export
examples_text = "\n\n".join(
    f"### {ex['title']} (Case {ex['case_id']})\n{ex['narrative']}"
    for ex in examples
)
st.download_button(
    "Download Examples as Markdown",
    data=examples_text,
    file_name="paper_examples.md",
    mime="text/markdown",
)
