"""Page 1: Process Overview — Case table, distributions, event timeline."""

from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parent.parent)); import path_setup

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Process Overview", layout="wide")
st.title("Process Overview")

results_dir, sample_dir, ds_info = path_setup.get_dataset_selector()
st.markdown(f"Exploring **{ds_info['domain']}** dataset: {ds_info['description']}")


@st.cache_data
def load_data(sample_path: str):
    try:
        sp = Path(sample_path)
        cases = pd.read_parquet(sp / "sample_cases.parquet")
        events = pd.read_parquet(sp / "sample_events.parquet")
        return cases, events
    except FileNotFoundError:
        return None, None


cases_df, events_df = load_data(str(sample_dir))

if cases_df is None:
    st.warning("No data found. Run the preprocessor for this dataset first.")
    st.stop()

# Summary metrics
st.subheader("Dataset Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Cases", len(cases_df))
col2.metric("Total Events", len(events_df) if events_df is not None else "N/A")
col3.metric("Avg Amount/Age", f"{cases_df['amount_requested'].mean():,.0f}")
col4.metric("Avg Duration", f"{cases_df['case_duration_hours'].mean():,.0f}h")

st.divider()

# Distributions
col_left, col_right = st.columns(2)

with col_left:
    fig_outcome = px.pie(
        cases_df, names="outcome", title="Outcome Distribution",
        color_discrete_sequence=["#00CC96", "#EF553B", "#FFA15A"],
        hole=0.3,
    )
    st.plotly_chart(fig_outcome, width="stretch")

with col_right:
    fig_tier = px.pie(
        cases_df, names="risk_tier", title="Risk Tier Distribution",
        color_discrete_sequence=["#00CC96", "#FFA15A", "#EF553B"],
        hole=0.3,
    )
    st.plotly_chart(fig_tier, width="stretch")

# Amount distribution
fig_amount = px.histogram(
    cases_df, x="amount_requested", color="outcome",
    title="Distribution by Outcome",
    nbins=30, barmode="overlay", opacity=0.7,
)
st.plotly_chart(fig_amount, width="stretch")

# Case table
st.subheader("Case Table")
display_cols = [c for c in ["case_id", "amount_requested", "risk_tier", "outcome", "num_events", "num_offers", "case_duration_hours"] if c in cases_df.columns]
st.dataframe(
    cases_df[display_cols].sort_values("amount_requested", ascending=False),
    width="stretch",
    height=400,
)
