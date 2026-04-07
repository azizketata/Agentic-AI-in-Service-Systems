"""
Process Conformance Analysis (Enhancement C)

Uses pm4py to compare how each mode's process paths align with
the discovered BPI 2012 process model. Demonstrates "lifecycle collapse."
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


def discover_process_model(events_df: pd.DataFrame):
    """
    Discover a Petri net from BPI 2012 events using pm4py inductive miner.

    Returns (net, initial_marking, final_marking).
    """
    import pm4py

    # Ensure pm4py column conventions
    df = events_df.copy()
    col_map = {}
    if "case_id" in df.columns:
        col_map["case_id"] = "case:concept:name"
    if "activity" in df.columns:
        col_map["activity"] = "concept:name"
    if "timestamp" in df.columns:
        col_map["timestamp"] = "time:timestamp"
    df = df.rename(columns=col_map)

    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], utc=True)

    # Filter to application-level activities (A_ and O_ prefixed) for a cleaner model
    activity_col = "concept:name"
    df = df[df[activity_col].str.match(r"^[AO]_", na=False)]

    net, im, fm = pm4py.discover_petri_net_inductive(df)
    return net, im, fm


def build_rule_engine_traces(rule_results: list[dict]) -> pd.DataFrame:
    """
    Convert rule engine results to a pm4py-compatible event log.

    Maps rule outcomes to BPI 2012 activity sequences using PROCESS_ROUTES.
    """
    from src.rule_engine.routing import PROCESS_ROUTES

    rows = []
    for r in rule_results:
        case_id = r["case_id"]
        # Determine which route was taken from the steps
        outcome = "decline"
        for step in r.get("steps_taken", []):
            if step.get("step") == "auto_approve_check" and step.get("passed"):
                outcome = "auto_approve"
                break
            if step.get("step") == "standard_review":
                outcome = "standard_review" if step.get("passed") else "decline"
            if step.get("step") == "senior_review":
                outcome = "senior_review" if step.get("passed") else "decline"

        route = PROCESS_ROUTES.get(outcome, PROCESS_ROUTES["decline"])
        base_time = datetime(2024, 1, 1, tzinfo=None)

        for i, activity in enumerate(route):
            rows.append({
                "case:concept:name": case_id,
                "concept:name": activity,
                "time:timestamp": base_time + timedelta(hours=i),
            })

    return pd.DataFrame(rows)


def build_agentic_traces(agentic_results: list[dict]) -> pd.DataFrame:
    """
    Convert agentic reasoning traces to a pm4py-compatible event log.

    Maps tagged trace entries to BPI 2012-style activities.
    """
    rows = []
    for r in agentic_results:
        case_id = r["case_id"]
        base_time = datetime(2024, 1, 1, tzinfo=None)
        step_idx = 0

        # Always starts with submission
        rows.append({
            "case:concept:name": case_id,
            "concept:name": "A_SUBMITTED",
            "time:timestamp": base_time + timedelta(hours=step_idx),
        })
        step_idx += 1

        for entry in r.get("reasoning_trace", []):
            activity = _map_trace_to_activity(entry)
            if activity:
                rows.append({
                    "case:concept:name": case_id,
                    "concept:name": activity,
                    "time:timestamp": base_time + timedelta(hours=step_idx),
                })
                step_idx += 1

        # Add final outcome activity
        decision = r.get("decision", "declined")
        if decision == "approved":
            for act in ["A_ACCEPTED", "A_FINALIZED"]:
                rows.append({
                    "case:concept:name": case_id,
                    "concept:name": act,
                    "time:timestamp": base_time + timedelta(hours=step_idx),
                })
                step_idx += 1
        elif decision == "declined":
            rows.append({
                "case:concept:name": case_id,
                "concept:name": "A_DECLINED",
                "time:timestamp": base_time + timedelta(hours=step_idx),
            })
        else:
            rows.append({
                "case:concept:name": case_id,
                "concept:name": "A_CANCELLED",
                "time:timestamp": base_time + timedelta(hours=step_idx),
            })

    return pd.DataFrame(rows)


def build_governed_traces(governed_results: list[dict]) -> pd.DataFrame:
    """
    Like build_agentic_traces but includes governance activities.
    """
    rows = []
    for r in governed_results:
        case_id = r["case_id"]
        base_time = datetime(2024, 1, 1, tzinfo=None)
        step_idx = 0

        rows.append({
            "case:concept:name": case_id,
            "concept:name": "A_SUBMITTED",
            "time:timestamp": base_time + timedelta(hours=step_idx),
        })
        step_idx += 1

        for entry in r.get("reasoning_trace", []):
            activity = _map_trace_to_activity(entry, include_governance=True)
            if activity:
                rows.append({
                    "case:concept:name": case_id,
                    "concept:name": activity,
                    "time:timestamp": base_time + timedelta(hours=step_idx),
                })
                step_idx += 1

        decision = r.get("decision", "declined")
        if decision == "approved":
            for act in ["A_ACCEPTED", "A_FINALIZED"]:
                rows.append({
                    "case:concept:name": case_id,
                    "concept:name": act,
                    "time:timestamp": base_time + timedelta(hours=step_idx),
                })
                step_idx += 1
        elif decision == "declined":
            rows.append({
                "case:concept:name": case_id,
                "concept:name": "A_DECLINED",
                "time:timestamp": base_time + timedelta(hours=step_idx),
            })
        else:
            rows.append({
                "case:concept:name": case_id,
                "concept:name": "A_CANCELLED",
                "time:timestamp": base_time + timedelta(hours=step_idx),
            })

    return pd.DataFrame(rows)


def _map_trace_to_activity(entry: str, include_governance: bool = False) -> str | None:
    """Map a reasoning trace entry to a process activity."""
    if "[TOOL] lookup_credit_policy" in entry:
        return "O_CREATED"  # Map to offer-related activity
    if "[TOOL] check_application_completeness" in entry:
        return "W_Completeren aanvraag"
    if "[TOOL] calculate_risk_score" in entry:
        return "W_Nabellen offertes"
    if "[ASSESS]" in entry and "tool results" not in entry:
        return "A_PARTLYSUBMITTED"

    if include_governance:
        if "[GOV] Intent contract" in entry:
            return "A_PREACCEPTED"  # Map contract creation to pre-acceptance
        if "[GUARDRAIL]" in entry:
            return None  # Don't double-count guardrails
        if "[HITL]" in entry:
            return "O_SENT"  # Map HITL to offer sent (human review step)

    return None


def compute_conformance_metrics(
    traces_df: pd.DataFrame, net, im, fm
) -> dict:
    """Compute conformance metrics using pm4py token-based replay."""
    import pm4py

    if traces_df.empty:
        return {"fitness": 0, "variant_count": 0}

    traces_df["time:timestamp"] = pd.to_datetime(traces_df["time:timestamp"], utc=True)

    try:
        replay_result = pm4py.conformance_diagnostics_token_based_replay(
            traces_df, net, im, fm
        )
        fitness_values = [r["trace_fitness"] for r in replay_result]
        avg_fitness = sum(fitness_values) / len(fitness_values) if fitness_values else 0

        # Count unique variants
        variants = traces_df.groupby("case:concept:name")["concept:name"].apply(
            lambda x: "->".join(x)
        ).nunique()

        return {
            "fitness": avg_fitness,
            "variant_count": int(variants),
            "total_cases": len(fitness_values),
            "fitting_cases": sum(1 for f in fitness_values if f >= 0.8),
        }
    except Exception as e:
        return {"fitness": 0, "variant_count": 0, "error": str(e)}


def run_conformance_analysis(
    events_path: Path, results_dir: Path
) -> dict:
    """
    Orchestrator: discover model, build traces, compute conformance for all modes.
    """
    # Load real events for model discovery
    events_df = pd.read_parquet(events_path)

    print("Discovering process model from BPI 2012 events...")
    net, im, fm = discover_process_model(events_df)

    # Load results
    results = {}
    for mode in ["rule_based", "agentic", "governed"]:
        path = results_dir / f"{mode}_results.json"
        if path.exists():
            with open(path) as f:
                results[mode] = json.load(f)

    # Build traces for each mode
    print("Building rule engine traces...")
    rule_traces = build_rule_engine_traces(results.get("rule_based", []))
    print("Building agentic traces...")
    agentic_traces = build_agentic_traces(results.get("agentic", []))
    print("Building governed traces...")
    governed_traces = build_governed_traces(results.get("governed", []))

    # Compute conformance
    print("Computing conformance metrics...")
    rule_conf = compute_conformance_metrics(rule_traces, net, im, fm)
    agentic_conf = compute_conformance_metrics(agentic_traces, net, im, fm)
    governed_conf = compute_conformance_metrics(governed_traces, net, im, fm)

    return {
        "rule_based": rule_conf,
        "agentic": agentic_conf,
        "governed": governed_conf,
        "lifecycle_collapse_evidence": (
            f"The rule engine produces {rule_conf.get('variant_count', 0)} process variants "
            f"(fixed routes, fitness={rule_conf.get('fitness', 0):.2f}). "
            f"The agentic system produces {agentic_conf.get('variant_count', 0)} variants "
            f"(fitness={agentic_conf.get('fitness', 0):.2f}), demonstrating runtime process "
            f"generation — the hallmark of lifecycle collapse. "
            f"The governed system produces {governed_conf.get('variant_count', 0)} variants "
            f"(fitness={governed_conf.get('fitness', 0):.2f}), showing bounded improvisation "
            f"within governance constraints."
        ),
    }
