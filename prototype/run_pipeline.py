"""
Pipeline Runner — Process all sample cases through the three modes.

Usage: python run_pipeline.py [--rule-only] [--sample-size N]
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd

from src.common.types import LoanOutcome, ProcessingMode
from src.data.schemas import CaseResult
from src.rule_engine.engine import process_case_rule_based, process_batch_rule_based


RESULTS_DIR = Path(__file__).parent / "data" / "results"


def run_rule_based(cases_df: pd.DataFrame) -> list[dict]:
    """Process all cases through the rule-based engine."""
    print(f"\n{'='*60}")
    print("MODE 1: RULE-BASED (RPA Baseline)")
    print(f"{'='*60}")

    start = time.perf_counter()
    results = process_batch_rule_based(cases_df)
    elapsed = time.perf_counter() - start

    correct = sum(1 for r in results if r.correct)
    print(f"Processed {len(results)} cases in {elapsed:.1f}s")
    print(f"Accuracy: {correct}/{len(results)} ({correct/len(results):.1%})")

    return [_result_to_dict(r) for r in results]


def run_agentic(cases_df: pd.DataFrame) -> list[dict]:
    """Process all cases through the ungoverned agent."""
    from src.agent.graph import build_ungoverned_graph, create_initial_state

    print(f"\n{'='*60}")
    print("MODE 2: AGENTIC (Ungoverned LangGraph Agent)")
    print(f"{'='*60}")

    graph = build_ungoverned_graph()
    results = []

    for i, (_, case) in enumerate(cases_df.iterrows()):
        case_dict = case.to_dict()
        print(f"  [{i+1}/{len(cases_df)}] Case {case_dict['case_id']} "
              f"(EUR {case_dict['amount_requested']:,.0f}, {case_dict['risk_tier']})...", end=" ")

        start = time.perf_counter()
        try:
            initial_state = create_initial_state(case_dict)
            config = {"configurable": {"thread_id": f"agentic_{case_dict['case_id']}"}, "recursion_limit": 15}
            final_state = graph.invoke(initial_state, config)

            elapsed_ms = (time.perf_counter() - start) * 1000
            ground_truth = LoanOutcome(case_dict["outcome"])
            decision_str = final_state.get("decision", "declined")

            try:
                decision = LoanOutcome(decision_str)
            except ValueError:
                decision = LoanOutcome.DECLINED

            result = CaseResult(
                case_id=case_dict["case_id"],
                mode=ProcessingMode.AGENTIC.value,
                decision=decision,
                confidence=final_state.get("confidence"),
                steps_taken=final_state.get("steps_taken", []),
                reasoning_trace=final_state.get("reasoning_trace", []),
                processing_time_ms=elapsed_ms,
                governance_events=[],
                human_interventions=0,
                contract_violations=0,
                correct=decision == ground_truth,
            )
            status = "OK" if result.correct else "WRONG"
            print(f"{status} ({decision.value} vs {ground_truth.value}) [{elapsed_ms:.0f}ms]")

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            print(f"ERROR: {e}")
            result = CaseResult(
                case_id=case_dict["case_id"],
                mode=ProcessingMode.AGENTIC.value,
                decision=LoanOutcome.DECLINED,
                confidence=0.0,
                steps_taken=[],
                reasoning_trace=[f"Error: {str(e)}"],
                processing_time_ms=elapsed_ms,
                correct=LoanOutcome.DECLINED == LoanOutcome(case_dict["outcome"]),
            )

        results.append(result)

    correct = sum(1 for r in results if r.correct)
    print(f"\nAgentic accuracy: {correct}/{len(results)} ({correct/len(results):.1%})")

    return [_result_to_dict(r) for r in results]


def run_governed(cases_df: pd.DataFrame) -> list[dict]:
    """Process all cases through the governed agent."""
    from src.agent.governed_graph import build_governed_graph
    from src.agent.graph import create_initial_state
    from src.governance.audit_logger import audit_log

    print(f"\n{'='*60}")
    print("MODE 3: GOVERNED (Agent + Guardrails + HITL)")
    print(f"{'='*60}")

    graph = build_governed_graph()
    results = []

    for i, (_, case) in enumerate(cases_df.iterrows()):
        case_dict = case.to_dict()
        print(f"  [{i+1}/{len(cases_df)}] Case {case_dict['case_id']} "
              f"(EUR {case_dict['amount_requested']:,.0f}, {case_dict['risk_tier']})...", end=" ")

        start = time.perf_counter()
        try:
            initial_state = create_initial_state(case_dict)
            config = {"configurable": {"thread_id": f"governed_{case_dict['case_id']}"}, "recursion_limit": 20}
            final_state = graph.invoke(initial_state, config)

            elapsed_ms = (time.perf_counter() - start) * 1000
            ground_truth = LoanOutcome(case_dict["outcome"])
            decision_str = final_state.get("decision", "declined")

            try:
                decision = LoanOutcome(decision_str)
            except ValueError:
                decision = LoanOutcome.DECLINED

            gov_events = final_state.get("governance_events", [])
            hitl_count = sum(1 for e in gov_events if e.get("event") == "hitl_review")
            violations = sum(
                1 for e in gov_events
                if e.get("event") == "guardrail_check" and e.get("blocked")
            )

            result = CaseResult(
                case_id=case_dict["case_id"],
                mode=ProcessingMode.GOVERNED.value,
                decision=decision,
                confidence=final_state.get("confidence"),
                steps_taken=final_state.get("steps_taken", []),
                reasoning_trace=final_state.get("reasoning_trace", []),
                processing_time_ms=elapsed_ms,
                governance_events=gov_events,
                human_interventions=hitl_count,
                contract_violations=violations,
                correct=decision == ground_truth,
            )
            tier = final_state.get("autonomy_tier", "?")
            status = "OK" if result.correct else "WRONG"
            print(f"{status} ({decision.value} vs {ground_truth.value}) "
                  f"[tier={tier}, hitl={hitl_count}] [{elapsed_ms:.0f}ms]")

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            print(f"ERROR: {e}")
            result = CaseResult(
                case_id=case_dict["case_id"],
                mode=ProcessingMode.GOVERNED.value,
                decision=LoanOutcome.DECLINED,
                confidence=0.0,
                steps_taken=[],
                reasoning_trace=[f"Error: {str(e)}"],
                processing_time_ms=elapsed_ms,
                correct=LoanOutcome.DECLINED == LoanOutcome(case_dict["outcome"]),
            )

        results.append(result)

    correct = sum(1 for r in results if r.correct)
    print(f"\nGoverned accuracy: {correct}/{len(results)} ({correct/len(results):.1%})")

    # Save audit log
    audit_path = RESULTS_DIR / "audit_log.json"
    with open(audit_path, "w") as f:
        f.write(audit_log.to_json())
    print(f"Audit log saved: {len(audit_log.entries)} entries")

    return [_result_to_dict(r) for r in results]


def _result_to_dict(r: CaseResult) -> dict:
    """Convert CaseResult to JSON-serializable dict."""
    return {
        "case_id": r.case_id,
        "mode": r.mode,
        "decision": r.decision.value if r.decision else None,
        "confidence": r.confidence,
        "num_steps": len(r.steps_taken),
        "steps_taken": r.steps_taken,
        "reasoning_trace": r.reasoning_trace,
        "processing_time_ms": r.processing_time_ms,
        "governance_events": r.governance_events,
        "human_interventions": r.human_interventions,
        "contract_violations": r.contract_violations,
        "correct": r.correct,
    }


def save_results(results: list[dict], mode: str):
    """Save results to JSON."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{mode}_results.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Saved {len(results)} results to {path}")


def main():
    rule_only = "--rule-only" in sys.argv
    sample_size = 101  # default

    for arg in sys.argv:
        if arg.startswith("--sample-size"):
            sample_size = int(sys.argv[sys.argv.index(arg) + 1])

    # Load sample cases
    sample_dir = Path(__file__).parent / "data" / "sample"
    cases_df = pd.read_parquet(sample_dir / "sample_cases.parquet")

    if sample_size < len(cases_df):
        cases_df = cases_df.head(sample_size)

    print(f"Processing {len(cases_df)} cases")
    print(f"Outcomes: {cases_df['outcome'].value_counts().to_dict()}")
    print(f"Risk tiers: {cases_df['risk_tier'].value_counts().to_dict()}")

    # Mode 1: Rule-based
    rule_results = run_rule_based(cases_df)
    save_results(rule_results, "rule_based")

    if rule_only:
        print("\n--rule-only flag set, skipping agent modes.")
        return

    # Mode 2: Agentic
    agentic_results = run_agentic(cases_df)
    save_results(agentic_results, "agentic")

    # Mode 3: Governed
    governed_results = run_governed(cases_df)
    save_results(governed_results, "governed")

    # Summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    for mode, results in [("Rule-Based", rule_results), ("Agentic", agentic_results), ("Governed", governed_results)]:
        correct = sum(1 for r in results if r["correct"])
        n = len(results)
        avg_time = sum(r["processing_time_ms"] for r in results) / n
        print(f"  {mode:12s}: {correct}/{n} ({correct/n:.1%}) accuracy, {avg_time:.0f}ms avg")


if __name__ == "__main__":
    main()
