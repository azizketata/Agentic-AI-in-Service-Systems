"""
Rule-Based Engine for Sepsis Clinical Triage (RPA Baseline)

Deterministic decision logic for predicting patient outcomes.
"""

import time
from dataclasses import dataclass, field

import pandas as pd

from src.common.types import ProcessingMode
from src.data.schemas import CaseResult


@dataclass
class SepsisRuleDecision:
    outcome: str  # "discharged" or "returned"
    reason: str = ""
    confidence: float = 1.0
    steps: list[dict] = field(default_factory=list)


def evaluate_sepsis_patient(
    age: float,
    infection_suspected: bool,
    sirs_criteria: bool,
    hypotension: bool,
    organ_dysfunction: bool,
    has_antibiotics: bool,
    num_events: int,
    lab_test_count: int,
    case_duration_hours: float,
) -> SepsisRuleDecision:
    """Deterministic sepsis patient outcome prediction."""
    steps = []

    # Step 1: Critical flags
    critical_flags = sum([hypotension, organ_dysfunction])
    steps.append({"step": "critical_flags", "value": critical_flags, "passed": critical_flags == 0})

    if critical_flags >= 2:
        return SepsisRuleDecision(
            outcome="returned",
            reason=f"Multiple critical flags ({critical_flags}): high risk of ER return",
            steps=steps,
        )

    # Step 2: Age risk
    steps.append({"step": "age_check", "value": age, "passed": age < 75})

    # Step 3: Treatment adequacy
    adequate_treatment = has_antibiotics if infection_suspected else True
    steps.append({"step": "treatment_check", "adequate": adequate_treatment, "passed": adequate_treatment})

    # Step 4: Lab monitoring
    adequate_labs = lab_test_count >= 3
    steps.append({"step": "lab_monitoring", "count": lab_test_count, "passed": adequate_labs})

    # Step 5: Combined decision
    risk_factors = sum([
        age >= 75,
        not adequate_treatment,
        not adequate_labs,
        sirs_criteria,
        hypotension,
        organ_dysfunction,
        case_duration_hours > 300,
    ])

    steps.append({"step": "risk_assessment", "risk_factors": risk_factors, "passed": risk_factors <= 2})

    if risk_factors > 2:
        return SepsisRuleDecision(
            outcome="returned",
            reason=f"{risk_factors} risk factors present: predicting ER return",
            steps=steps,
        )
    else:
        return SepsisRuleDecision(
            outcome="discharged",
            reason=f"Only {risk_factors} risk factors: predicting successful discharge",
            steps=steps,
        )


def process_sepsis_case_rule_based(case: dict | pd.Series) -> CaseResult:
    """Process a single sepsis case through the rule engine."""
    start = time.perf_counter()

    if isinstance(case, pd.Series):
        case = case.to_dict()

    decision = evaluate_sepsis_patient(
        age=case.get("age", case.get("amount_requested", 0)),
        infection_suspected=case.get("infection_suspected", False),
        sirs_criteria=case.get("sirs_criteria", False),
        hypotension=case.get("hypotension", False),
        organ_dysfunction=case.get("organ_dysfunction", False),
        has_antibiotics=case.get("has_antibiotics", False),
        num_events=case.get("num_events", 0),
        lab_test_count=case.get("lab_test_count", case.get("num_offers", 0)),
        case_duration_hours=case.get("case_duration_hours", 0),
    )

    elapsed_ms = (time.perf_counter() - start) * 1000
    ground_truth = case["outcome"]

    reasoning_trace = [
        f"Rule engine: {step['step']} — {'PASS' if step.get('passed') else 'FAIL'}"
        for step in decision.steps
    ]
    reasoning_trace.append(f"Decision: {decision.outcome}")
    reasoning_trace.append(f"Reason: {decision.reason}")

    return CaseResult(
        case_id=case["case_id"],
        mode=ProcessingMode.RULE_BASED.value,
        decision=None,  # Will be set below
        confidence=decision.confidence,
        steps_taken=decision.steps,
        reasoning_trace=reasoning_trace,
        processing_time_ms=elapsed_ms,
        correct=decision.outcome == ground_truth,
    )


def process_sepsis_batch_rule_based(cases_df: pd.DataFrame) -> list[CaseResult]:
    """Process a batch of sepsis cases."""
    results = []
    for _, case in cases_df.iterrows():
        result = process_sepsis_case_rule_based(case)
        # Store decision as string (not LoanOutcome enum)
        result_dict = result.model_dump()
        result_dict["decision"] = evaluate_sepsis_patient(
            age=case.get("age", case.get("amount_requested", 0)),
            infection_suspected=case.get("infection_suspected", False),
            sirs_criteria=case.get("sirs_criteria", False),
            hypotension=case.get("hypotension", False),
            organ_dysfunction=case.get("organ_dysfunction", False),
            has_antibiotics=case.get("has_antibiotics", False),
            num_events=case.get("num_events", 0),
            lab_test_count=case.get("lab_test_count", case.get("num_offers", 0)),
            case_duration_hours=case.get("case_duration_hours", 0),
        ).outcome
        results.append(result_dict)
    return results
