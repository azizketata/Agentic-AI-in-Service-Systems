"""Page 3: Reasoning Trace Viewer + HITL Experiment."""

import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # prototype root
sys.path.insert(0, str(Path(__file__).parent.parent))         # app dir

import streamlit as st
import pandas as pd

from components.trace_viewer import render_trace, render_governance_annotations
from components.case_selector import render_case_selector

st.set_page_config(page_title="Reasoning Trace", layout="wide")
st.title("Reasoning Trace Viewer")

tab_view, tab_experiment = st.tabs(["View Traces", "HITL Experiment"])


# ── Shared Data Loading ─────────────────────────────────────────

@st.cache_data
def load_cases():
    try:
        sample_dir = Path(__file__).parent.parent.parent / "data" / "sample"
        return pd.read_parquet(sample_dir / "sample_cases.parquet")
    except FileNotFoundError:
        return None


@st.cache_data
def load_agentic_results():
    try:
        path = Path(__file__).parent.parent.parent / "data" / "results" / "agentic_results.json"
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return []


cases_df = load_cases()
agentic_results = load_agentic_results()


# ══════════════════════════════════════════════════════════════════
# TAB 1: VIEW TRACES (original page behavior)
# ══════════════════════════════════════════════════════════════════

with tab_view:
    st.markdown("Explore step-by-step agent reasoning with governance annotations.")

    selected_case = render_case_selector(cases_df) if cases_df is not None else None

    if selected_case is None:
        st.info("Select a case from the sidebar to view its reasoning trace.")
    else:
        mode = st.radio(
            "Processing Mode",
            options=["Rule-Based", "Agentic", "Governed"],
            horizontal=True,
        )
        st.divider()

        if mode == "Governed":
            with st.expander("Intent Contract", expanded=True):
                st.markdown("**Goal:** Evaluate loan application for approval or decline")
                st.markdown(f"**Constraints:** Loan amount EUR {selected_case['amount_requested']:,.2f}, "
                             f"Risk tier: {selected_case['risk_tier']}")
                from src.governance.autonomy_tiers import classify_autonomy_tier
                tier = classify_autonomy_tier(selected_case["amount_requested"], selected_case["risk_tier"])
                st.markdown(f"**Autonomy Tier:** `{tier.value}`")

        # Load actual results if available
        result_map = {r["case_id"]: r for r in agentic_results}

        if mode == "Rule-Based":
            from src.rule_engine.engine import process_case_rule_based
            result = process_case_rule_based(selected_case)
            render_trace(result.reasoning_trace, f"Rule-Based Trace — Case {selected_case['case_id']}")
            st.subheader("Decision")
            if result.correct:
                st.success(f"Decision: **{result.decision.value}** (Correct)")
            else:
                st.error(f"Decision: **{result.decision.value}** (Ground truth: {selected_case['outcome']})")

        elif mode in ["Agentic", "Governed"]:
            case_result = result_map.get(selected_case["case_id"])
            if case_result and case_result.get("reasoning_trace"):
                render_trace(case_result["reasoning_trace"], f"{mode} Trace — Case {selected_case['case_id']}")
                st.subheader("Decision")
                if case_result["correct"]:
                    st.success(f"Decision: **{case_result['decision']}** (Correct, confidence: {case_result.get('confidence', 0):.0%})")
                else:
                    st.error(f"Decision: **{case_result['decision']}** (Ground truth: {selected_case['outcome']}, confidence: {case_result.get('confidence', 0):.0%})")
            else:
                st.info(f"No {mode.lower()} results for this case. Run the pipeline first.")


# ══════════════════════════════════════════════════════════════════
# TAB 2: HITL EXPERIMENT
# ══════════════════════════════════════════════════════════════════

with tab_experiment:
    st.markdown(
        "**Procedural Literacy Study** — Review agent reasoning traces and make decisions. "
        "Measures whether humans can effectively oversee agentic AI."
    )

    # Initialize session state
    if "experiment_trials" not in st.session_state:
        st.session_state.experiment_trials = []
    if "seen_cases" not in st.session_state:
        st.session_state.seen_cases = set()
    if "current_experiment_case" not in st.session_state:
        st.session_state.current_experiment_case = None
    if "review_start_time" not in st.session_state:
        st.session_state.review_start_time = None

    # Participant setup
    st.subheader("Participant Setup")
    col_id, col_exp = st.columns(2)
    participant_id = col_id.text_input("Participant ID", value="P001")
    experience_level = col_exp.selectbox("Experience Level", ["novice", "intermediate", "expert"])

    st.divider()

    if not agentic_results:
        st.warning("No agentic results available. Run the pipeline first.")
    else:
        # Get unseen cases
        unseen = [r for r in agentic_results if r["case_id"] not in st.session_state.seen_cases]

        if not unseen:
            st.success("All cases reviewed!")
        else:
            # Present a case
            if st.session_state.current_experiment_case is None or st.button("Next Case"):
                import random
                st.session_state.current_experiment_case = random.choice(unseen)
                st.session_state.review_start_time = time.time()
                st.session_state.pop("submitted", None)
                st.rerun()

            case_r = st.session_state.current_experiment_case
            if case_r:
                case_info = cases_df[cases_df["case_id"] == case_r["case_id"]].iloc[0] if cases_df is not None else None

                st.subheader(f"Case: {case_r['case_id']}")

                # Case details
                if case_info is not None:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Amount", f"EUR {case_info['amount_requested']:,.0f}")
                    col2.metric("Risk Tier", case_info["risk_tier"])
                    col3.metric("Events", case_info["num_events"])
                    col4.metric("Offers", case_info["num_offers"])

                # Agent's proposal
                st.markdown(f"**Agent Decision:** `{case_r['decision']}` | "
                            f"**Confidence:** {case_r.get('confidence', 0):.0%}")

                st.divider()

                # Reasoning trace with trackable checkboxes
                st.subheader("Agent Reasoning Trace")
                trace = case_r.get("reasoning_trace", [])
                expanded_sections = []
                for i, entry in enumerate(trace):
                    key = f"trace_step_{i}"
                    if st.checkbox(f"Step {i+1}: {entry[:80]}...", key=key):
                        st.code(entry, language=None)
                        expanded_sections.append(f"step_{i}")

                st.divider()

                # Human review
                st.subheader("Your Review")
                human_action = st.radio(
                    "What do you decide?",
                    ["Approve Agent Decision", "Modify Decision", "Reject (Decline)"],
                    key="human_action",
                )

                human_final = case_r["decision"]
                if human_action == "Modify Decision":
                    human_final = st.selectbox(
                        "Correct decision:",
                        ["approved", "declined", "cancelled"],
                        key="human_final",
                    )
                elif human_action == "Reject (Decline)":
                    human_final = "declined"

                human_reasoning = st.text_area("Brief reasoning:", key="human_reasoning")

                if st.button("Submit Review", type="primary"):
                    elapsed = time.time() - (st.session_state.review_start_time or time.time())
                    ground_truth = case_info["outcome"] if case_info is not None else "unknown"

                    trial = {
                        "participant_id": participant_id,
                        "experience_level": experience_level,
                        "case_id": case_r["case_id"],
                        "agent_decision": case_r["decision"],
                        "agent_confidence": case_r.get("confidence", 0),
                        "human_decision": human_action.lower().replace(" ", "_"),
                        "human_final_decision": human_final,
                        "human_reasoning": human_reasoning,
                        "review_time_seconds": round(elapsed, 1),
                        "sections_expanded": expanded_sections,
                        "ground_truth": ground_truth,
                        "human_correct": human_final == ground_truth,
                        "agent_correct": case_r.get("correct", False),
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    }
                    st.session_state.experiment_trials.append(trial)
                    st.session_state.seen_cases.add(case_r["case_id"])
                    st.session_state.current_experiment_case = None

                    # Show result
                    st.divider()
                    st.markdown(f"**Ground Truth:** `{ground_truth}`")
                    if trial["human_correct"]:
                        st.success("Your decision was correct!")
                    else:
                        st.error(f"Incorrect. Ground truth was '{ground_truth}'.")
                    if trial["agent_correct"]:
                        st.info("The agent was also correct on this one.")
                    else:
                        st.warning(f"The agent was wrong (said '{case_r['decision']}').")

        # Experiment summary
        if st.session_state.experiment_trials:
            st.divider()
            st.subheader("Experiment Progress")

            from src.evaluation.hitl_experiment import compute_experiment_metrics, save_experiment_results
            metrics = compute_experiment_metrics(st.session_state.experiment_trials)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Cases Reviewed", metrics["n_trials"])
            col2.metric("Your Accuracy", f"{metrics['human_accuracy']:.0%}")
            col3.metric("Agent Accuracy", f"{metrics['agent_accuracy']:.0%}")
            col4.metric("Avg Review Time", f"{metrics['avg_review_time_seconds']:.0f}s")

            # Save button
            if st.button("Save Experiment Results"):
                save_path = Path(__file__).parent.parent.parent / "data" / "results" / "hitl_experiment.json"
                save_experiment_results(st.session_state.experiment_trials, save_path)
                st.success(f"Saved {len(st.session_state.experiment_trials)} trials to {save_path.name}")
