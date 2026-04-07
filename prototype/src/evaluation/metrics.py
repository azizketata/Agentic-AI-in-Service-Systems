"""
Evaluation Metrics

Computes metrics for comparing the three processing modes.
"""

import pandas as pd

from src.common.types import ProcessingMode
from src.data.schemas import CaseResult


def compute_case_metrics(result: CaseResult) -> dict:
    """Compute metrics for a single case result."""
    return {
        "case_id": result.case_id,
        "mode": result.mode,
        "correct": result.correct,
        "confidence": result.confidence,
        "num_steps": len(result.steps_taken),
        "processing_time_ms": result.processing_time_ms,
        "num_reasoning_entries": len(result.reasoning_trace),
        "governance_events": len(result.governance_events),
        "human_interventions": result.human_interventions,
        "contract_violations": result.contract_violations,
        "decision": result.decision.value if result.decision else None,
    }


def compute_aggregate_metrics(results: list[CaseResult]) -> dict:
    """Compute aggregate metrics for a batch of results."""
    if not results:
        return {}

    n = len(results)
    correct = sum(1 for r in results if r.correct)
    total_steps = sum(len(r.steps_taken) for r in results)
    total_time = sum(r.processing_time_ms for r in results)
    total_governance = sum(len(r.governance_events) for r in results)
    total_hitl = sum(r.human_interventions for r in results)
    total_violations = sum(r.contract_violations for r in results)

    confidences = [r.confidence for r in results if r.confidence is not None]

    return {
        "mode": results[0].mode,
        "total_cases": n,
        "accuracy": correct / n,
        "avg_steps": total_steps / n,
        "avg_processing_time_ms": total_time / n,
        "avg_confidence": sum(confidences) / len(confidences) if confidences else None,
        "total_governance_events": total_governance,
        "avg_governance_events": total_governance / n,
        "total_human_interventions": total_hitl,
        "human_intervention_rate": total_hitl / n,
        "total_contract_violations": total_violations,
        "violation_rate": total_violations / n,
    }


def results_to_dataframe(results: list[CaseResult]) -> pd.DataFrame:
    """Convert a list of CaseResults to a DataFrame of per-case metrics."""
    rows = [compute_case_metrics(r) for r in results]
    return pd.DataFrame(rows)
