"""Shared case selector widget for Streamlit pages."""

from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parent.parent)); import path_setup

import streamlit as st
import pandas as pd


def render_case_selector(cases_df: pd.DataFrame) -> dict | None:
    """
    Render a case selector sidebar widget.

    Returns the selected case as a dict, or None if no data.
    """
    if cases_df is None or cases_df.empty:
        st.sidebar.warning("No case data loaded. Run the preprocessor first.")
        return None

    st.sidebar.subheader("Select Case")

    # Filter options
    outcome_filter = st.sidebar.multiselect(
        "Filter by outcome",
        options=sorted(cases_df["outcome"].unique()),
        default=sorted(cases_df["outcome"].unique()),
    )
    tier_filter = st.sidebar.multiselect(
        "Filter by risk tier",
        options=sorted(cases_df["risk_tier"].unique()),
        default=sorted(cases_df["risk_tier"].unique()),
    )

    filtered = cases_df[
        (cases_df["outcome"].isin(outcome_filter))
        & (cases_df["risk_tier"].isin(tier_filter))
    ]

    if filtered.empty:
        st.sidebar.warning("No cases match filters.")
        return None

    # Case picker
    case_options = filtered["case_id"].tolist()
    selected_id = st.sidebar.selectbox(
        "Case ID",
        options=case_options,
        format_func=lambda x: f"{x} (EUR {filtered[filtered['case_id']==x]['amount_requested'].values[0]:,.0f})",
    )

    selected = filtered[filtered["case_id"] == selected_id].iloc[0].to_dict()

    # Show case summary
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Amount:** EUR {selected['amount_requested']:,.2f}")
    st.sidebar.markdown(f"**Risk Tier:** {selected['risk_tier']}")
    st.sidebar.markdown(f"**Outcome:** {selected['outcome']}")
    st.sidebar.markdown(f"**Events:** {selected['num_events']}")

    return selected
