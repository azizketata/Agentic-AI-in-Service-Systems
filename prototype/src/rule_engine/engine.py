"""
Rule-Based Engine Orchestrator (RPA Mode)

Processes loan applications using deterministic decision trees.
No LLM, no reasoning — pure if/else logic.
"""

import time

import pandas as pd

from src.common.types import LoanOutcome, ProcessingMode
from src.data.schemas import CaseResult
from src.rule_engine.decision_trees import evaluate_loan
from src.rule_engine.routing import get_expected_route


def process_case_rule_based(case: dict | pd.Series) -> CaseResult:
    """
    Process a single loan application case using the rule-based engine.

    Args:
        case: Dict or Series with keys: case_id, amount_requested, num_events,
              num_offers, case_duration_hours, outcome (ground truth)
    """
    start = time.perf_counter()

    if isinstance(case, pd.Series):
        case = case.to_dict()

    decision = evaluate_loan(
        amount=case["amount_requested"],
        num_events=case.get("num_events", 0),
        num_offers=case.get("num_offers", 0),
        case_duration_hours=case.get("case_duration_hours", 0),
    )

    elapsed_ms = (time.perf_counter() - start) * 1000
    expected_route = get_expected_route(decision.outcome)
    ground_truth = LoanOutcome(case["outcome"])

    reasoning_trace = [
        f"Rule engine: {step['step']} — {'PASS' if step.get('passed') else 'FAIL'}"
        for step in decision.steps
    ]
    reasoning_trace.append(f"Decision: {decision.outcome} -> {decision.final_decision}")
    reasoning_trace.append(f"Reason: {decision.reason}")

    return CaseResult(
        case_id=case["case_id"],
        mode=ProcessingMode.RULE_BASED.value,
        decision=decision.final_decision,
        confidence=decision.confidence,
        steps_taken=decision.steps,
        reasoning_trace=reasoning_trace,
        processing_time_ms=elapsed_ms,
        governance_events=[],
        human_interventions=0,
        contract_violations=0,
        correct=decision.final_decision == ground_truth,
    )


def process_batch_rule_based(cases_df: pd.DataFrame) -> list[CaseResult]:
    """Process a batch of cases through the rule engine."""
    results = []
    for _, case in cases_df.iterrows():
        result = process_case_rule_based(case)
        results.append(result)
    return results
