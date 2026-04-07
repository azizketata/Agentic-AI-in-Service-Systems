"""Reusable chart builders using Plotly."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def radar_chart(data: dict, title: str = "Mode Comparison") -> go.Figure:
    """Build a radar chart comparing the three modes."""
    categories = data["categories"]

    fig = go.Figure()

    colors = {
        "Rule-Based": "#636EFA",
        "Agentic": "#EF553B",
        "Governed": "#00CC96",
    }

    for mode in ["Rule-Based", "Agentic", "Governed"]:
        if mode in data:
            values = data[mode] + [data[mode][0]]  # Close the polygon
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill="toself",
                name=mode,
                line=dict(color=colors.get(mode, "#888")),
                opacity=0.6,
            ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        title=title,
        height=500,
    )
    return fig


def comparison_bar_chart(
    comparison_df: pd.DataFrame,
    metric_col: str = "Metric",
    title: str = "Metric Comparison",
) -> go.Figure:
    """Build a grouped bar chart from the comparison table."""
    fig = go.Figure()

    colors = {
        "Rule-Based": "#636EFA",
        "Agentic": "#EF553B",
        "Governed": "#00CC96",
    }

    for mode in ["Rule-Based", "Agentic", "Governed"]:
        if mode in comparison_df.columns:
            # Try to convert to numeric for charting
            values = []
            for v in comparison_df[mode]:
                try:
                    values.append(float(str(v).replace("%", "").replace("N/A", "0")))
                except ValueError:
                    values.append(0)

            fig.add_trace(go.Bar(
                x=comparison_df[metric_col],
                y=values,
                name=mode,
                marker_color=colors.get(mode, "#888"),
            ))

    fig.update_layout(
        barmode="group",
        title=title,
        xaxis_title="Metric",
        yaxis_title="Value",
        height=450,
    )
    return fig


def timeline_chart(events: list[dict], title: str = "Event Timeline") -> go.Figure:
    """Build a timeline visualization of process events."""
    if not events:
        return go.Figure().update_layout(title="No events to display")

    df = pd.DataFrame(events)

    fig = px.scatter(
        df,
        x="timestamp" if "timestamp" in df.columns else df.index,
        y="activity" if "activity" in df.columns else "event_type",
        color="activity" if "activity" in df.columns else "event_type",
        title=title,
        height=400,
    )
    fig.update_traces(marker=dict(size=10))
    return fig


def failure_type_pie(failure_summary: dict, title: str = "Failure Type Distribution") -> go.Figure:
    """Pie chart of agentic failure types."""
    by_type = failure_summary.get("by_type", {})
    labels = {
        "cancelled_blind_spot": "Cancelled Blind Spot",
        "false_approval": "False Approval",
        "false_decline": "False Decline",
        "other": "Other",
    }
    fig = go.Figure(data=[go.Pie(
        labels=[labels.get(k, k) for k in by_type.keys()],
        values=list(by_type.values()),
        marker=dict(colors=["#FFA15A", "#EF553B", "#636EFA", "#888"]),
        hole=0.3,
        textinfo="label+value+percent",
    )])
    fig.update_layout(title=title, height=350)
    return fig


def confidence_histogram(
    wrong_cases: list[dict],
    correct_cases: list[dict],
    title: str = "Confidence Distribution: Correct vs Wrong",
) -> go.Figure:
    """Overlaid histogram of confidence for correct vs wrong predictions."""
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=[c.get("confidence", 0) for c in correct_cases],
        name="Correct", opacity=0.6, marker_color="#00CC96",
        xbins=dict(start=0, end=1, size=0.05),
    ))
    fig.add_trace(go.Histogram(
        x=[c.get("confidence", 0) for c in wrong_cases],
        name="Wrong", opacity=0.6, marker_color="#EF553B",
        xbins=dict(start=0, end=1, size=0.05),
    ))
    fig.update_layout(
        barmode="overlay", title=title,
        xaxis_title="Confidence", yaxis_title="Count",
        height=350,
    )
    return fig


def tier_distribution_pie(tier_counts: dict) -> go.Figure:
    """Pie chart of autonomy tier distribution."""
    fig = go.Figure(data=[go.Pie(
        labels=list(tier_counts.keys()),
        values=list(tier_counts.values()),
        marker=dict(colors=["#00CC96", "#FFA15A", "#EF553B"]),
        hole=0.3,
    )])
    fig.update_layout(title="Autonomy Tier Distribution", height=350)
    return fig
