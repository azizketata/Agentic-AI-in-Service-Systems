"""
Three-Mode Comparison Engine

Generates side-by-side comparison tables and charts data
for the Streamlit dashboard and paper figures.
"""

import pandas as pd

from src.data.schemas import CaseResult
from src.evaluation.metrics import compute_aggregate_metrics, results_to_dataframe


def build_comparison_table(
    rule_results: list[CaseResult],
    agentic_results: list[CaseResult],
    governed_results: list[CaseResult],
) -> pd.DataFrame:
    """
    Build a side-by-side comparison table of aggregate metrics.

    Returns DataFrame with metrics as rows and modes as columns.
    """
    rule_agg = compute_aggregate_metrics(rule_results)
    agentic_agg = compute_aggregate_metrics(agentic_results)
    governed_agg = compute_aggregate_metrics(governed_results)

    metrics = [
        ("Accuracy", "accuracy", ".1%"),
        ("Avg Steps", "avg_steps", ".1f"),
        ("Avg Processing Time (ms)", "avg_processing_time_ms", ".1f"),
        ("Avg Confidence", "avg_confidence", ".2f"),
        ("Avg Governance Events", "avg_governance_events", ".1f"),
        ("Human Intervention Rate", "human_intervention_rate", ".1%"),
        ("Violation Rate", "violation_rate", ".1%"),
    ]

    rows = []
    for label, key, fmt in metrics:
        rows.append({
            "Metric": label,
            "Rule-Based": _fmt(rule_agg.get(key), fmt),
            "Agentic": _fmt(agentic_agg.get(key), fmt),
            "Governed": _fmt(governed_agg.get(key), fmt),
        })

    return pd.DataFrame(rows)


def build_per_case_comparison(
    rule_results: list[CaseResult],
    agentic_results: list[CaseResult],
    governed_results: list[CaseResult],
) -> pd.DataFrame:
    """Build per-case comparison across all three modes."""
    rule_df = results_to_dataframe(rule_results).add_suffix("_rule")
    agentic_df = results_to_dataframe(agentic_results).add_suffix("_agentic")
    governed_df = results_to_dataframe(governed_results).add_suffix("_governed")

    # Merge on case_id
    merged = rule_df.rename(columns={"case_id_rule": "case_id"})
    merged = merged.merge(
        agentic_df.rename(columns={"case_id_agentic": "case_id"}),
        on="case_id",
        how="outer",
    )
    merged = merged.merge(
        governed_df.rename(columns={"case_id_governed": "case_id"}),
        on="case_id",
        how="outer",
    )

    return merged


def build_radar_chart_data(
    rule_results: list[CaseResult],
    agentic_results: list[CaseResult],
    governed_results: list[CaseResult],
) -> dict:
    """
    Build data for a radar chart comparing the three modes.

    Returns dict with categories and values per mode, normalized to 0-1.
    """
    rule_agg = compute_aggregate_metrics(rule_results)
    agentic_agg = compute_aggregate_metrics(agentic_results)
    governed_agg = compute_aggregate_metrics(governed_results)

    categories = ["Accuracy", "Efficiency", "Transparency", "Governance", "Human Effort"]

    def _score(agg: dict) -> list[float]:
        accuracy = agg.get("accuracy", 0)
        # Efficiency: inverse of steps (fewer = better), normalized
        max_steps = max(
            rule_agg.get("avg_steps", 1),
            agentic_agg.get("avg_steps", 1),
            governed_agg.get("avg_steps", 1),
        )
        efficiency = 1 - (agg.get("avg_steps", 0) / max_steps) if max_steps > 0 else 0
        # Transparency: governance events as proxy (more = more transparent)
        max_gov = max(
            rule_agg.get("avg_governance_events", 0),
            agentic_agg.get("avg_governance_events", 0),
            governed_agg.get("avg_governance_events", 1),
        )
        transparency = agg.get("avg_governance_events", 0) / max_gov if max_gov > 0 else 0
        # Governance: inverse of violation rate
        governance = 1 - agg.get("violation_rate", 0)
        # Human effort: intervention rate (lower = less effort)
        human_effort = 1 - agg.get("human_intervention_rate", 0)

        return [accuracy, efficiency, transparency, governance, human_effort]

    return {
        "categories": categories,
        "Rule-Based": _score(rule_agg),
        "Agentic": _score(agentic_agg),
        "Governed": _score(governed_agg),
    }


def _fmt(value, fmt: str) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{value:{fmt}}"
    except (ValueError, TypeError):
        return str(value)
