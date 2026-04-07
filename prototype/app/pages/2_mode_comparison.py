"""Page 2: Mode Comparison — Side-by-side three-mode results with real data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # prototype root
sys.path.insert(0, str(Path(__file__).parent.parent))         # app dir

import streamlit as st
import pandas as pd
import json

from components.charts import radar_chart, comparison_bar_chart

st.set_page_config(page_title="Mode Comparison", layout="wide")
st.title("Mode Comparison")
st.markdown("Compare Rule-Based, Agentic, and Governed processing results.")


@st.cache_data
def load_results():
    results_dir = Path(__file__).parent.parent.parent / "data" / "results"
    results = {}
    for mode in ["rule_based", "agentic", "governed"]:
        path = results_dir / f"{mode}_results.json"
        if path.exists():
            with open(path) as f:
                results[mode] = json.load(f)
    return results


@st.cache_data
def load_cases():
    sample_dir = Path(__file__).parent.parent.parent / "data" / "sample"
    cases = pd.read_parquet(sample_dir / "sample_cases.parquet")
    from src.governance.autonomy_tiers import classify_autonomy_tier
    cases["autonomy_tier"] = cases.apply(
        lambda r: classify_autonomy_tier(r["amount_requested"], r["risk_tier"]).value, axis=1
    )
    return cases


results = load_results()
cases_df = load_cases()

if not results or len(results) < 3:
    st.warning("Not all results available. Run the full pipeline first.")
    st.stop()

n = len(results["rule_based"])

# ── Summary Metrics Row ─────────────────────────────────────────
st.subheader("Headline Results")
col1, col2, col3 = st.columns(3)

for col, mode_key, label, color in [
    (col1, "rule_based", "Rule-Based", "normal"),
    (col2, "agentic", "Agentic", "normal"),
    (col3, "governed", "Governed", "normal"),
]:
    r = results[mode_key]
    correct = sum(1 for x in r if x["correct"])
    with col:
        st.metric(f"{label} Accuracy", f"{correct}/{n} ({correct/n:.1%})")

st.divider()

# ── Detailed Comparison Table ───────────────────────────────────
st.subheader("Detailed Comparison")

rows = []
for mode_key, label in [("rule_based", "Rule-Based"), ("agentic", "Agentic"), ("governed", "Governed")]:
    r = results[mode_key]
    correct = sum(1 for x in r if x["correct"])
    confs = [x.get("confidence", 0) or 0 for x in r]
    steps = [x.get("num_steps", 0) for x in r]
    times = [x.get("processing_time_ms", 0) for x in r]
    gov = sum(len(x.get("governance_events", [])) for x in r)
    hitl = sum(x.get("human_interventions", 0) for x in r)

    rows.append({
        "Mode": label,
        "Accuracy": f"{correct/n:.1%}",
        "Avg Confidence": f"{sum(confs)/n:.2f}",
        "Avg Steps": f"{sum(steps)/n:.1f}",
        "Avg Time": f"{sum(times)/n:.0f}ms",
        "Governance Events": gov,
        "HITL Interventions": hitl,
    })

st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

st.divider()

# ── Radar Chart (real data) ─────────────────────────────────────
st.subheader("Multi-Dimensional Comparison")

radar_data = {"categories": ["Accuracy", "Efficiency", "Transparency", "Governance", "Low Human Effort"]}
for mode_key, label in [("rule_based", "Rule-Based"), ("agentic", "Agentic"), ("governed", "Governed")]:
    r = results[mode_key]
    accuracy = sum(1 for x in r if x["correct"]) / n
    steps = sum(x.get("num_steps", 0) for x in r) / n
    max_steps = max(sum(x.get("num_steps", 0) for x in results[m]) / n for m in results)
    efficiency = 1 - (steps / max_steps) if max_steps > 0 else 0
    gov = sum(len(x.get("governance_events", [])) for x in r)
    max_gov = max(sum(len(x.get("governance_events", [])) for x in results[m]) for m in results) or 1
    transparency = gov / max_gov
    violations = sum(x.get("contract_violations", 0) for x in r)
    governance_score = 1 - (violations / n)
    hitl = sum(x.get("human_interventions", 0) for x in r) / n
    human_effort = 1 - min(hitl, 1)
    radar_data[label] = [accuracy, efficiency, transparency, governance_score, human_effort]

fig = radar_chart(radar_data)
st.plotly_chart(fig, width="stretch")

st.divider()

# ── Per-Tier Accuracy ───────────────────────────────────────────
st.subheader("Accuracy by Autonomy Tier")
st.markdown("The key governance finding: HITL checkpoints eliminate errors in supervised and restricted tiers.")

import plotly.express as px

tier_data = []
for tier in ["full_auto", "supervised", "restricted"]:
    tier_ids = set(cases_df[cases_df["autonomy_tier"] == tier]["case_id"])
    n_tier = len(tier_ids)
    for mode_key, label in [("rule_based", "Rule-Based"), ("agentic", "Agentic"), ("governed", "Governed")]:
        correct = sum(1 for r in results[mode_key] if r["case_id"] in tier_ids and r["correct"])
        tier_data.append({
            "Tier": tier.replace("_", " ").title(),
            "Mode": label,
            "Accuracy": correct / n_tier if n_tier > 0 else 0,
        })

fig_tier = px.bar(
    pd.DataFrame(tier_data), x="Tier", y="Accuracy", color="Mode",
    barmode="group", text_auto=".0%",
    color_discrete_map={"Rule-Based": "#636EFA", "Agentic": "#EF553B", "Governed": "#00CC96"},
)
fig_tier.update_layout(yaxis_tickformat=".0%", height=450)
st.plotly_chart(fig_tier, width="stretch")
