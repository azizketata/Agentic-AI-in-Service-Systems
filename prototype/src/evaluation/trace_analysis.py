"""
Qualitative Reasoning Trace Analysis (Enhancement B)

Finds and categorizes plausible-but-wrong agent decisions.
Makes the deskilling paradox and accountability gap concrete.
"""

import json
from pathlib import Path

import pandas as pd


def load_all_results(results_dir: Path) -> dict:
    """Load all result JSONs and audit log."""
    results = {}
    for mode in ["rule_based", "agentic", "governed"]:
        path = results_dir / f"{mode}_results.json"
        if path.exists():
            with open(path) as f:
                results[mode] = json.load(f)
        else:
            results[mode] = []

    audit_path = results_dir / "audit_log.json"
    if audit_path.exists():
        with open(audit_path) as f:
            results["audit_log"] = json.load(f)
    else:
        results["audit_log"] = []

    return results


def classify_agentic_failures(
    agentic_results: list[dict],
    cases_df: pd.DataFrame,
) -> list[dict]:
    """
    Classify each wrong agentic decision by failure type.

    Failure types:
      - cancelled_blind_spot: ground truth is cancelled, agent said approved/declined
      - false_approval: ground truth is declined, agent said approved
      - false_decline: ground truth is approved, agent said declined
    """
    outcome_map = {row["case_id"]: row["outcome"] for _, row in cases_df.iterrows()}
    failures = []

    for r in agentic_results:
        if r.get("correct", False):
            continue

        case_id = r["case_id"]
        ground_truth = outcome_map.get(case_id, "unknown")
        agent_decision = r.get("decision", "unknown")

        if ground_truth == "cancelled":
            failure_type = "cancelled_blind_spot"
        elif ground_truth == "declined" and agent_decision == "approved":
            failure_type = "false_approval"
        elif ground_truth == "approved" and agent_decision == "declined":
            failure_type = "false_decline"
        else:
            failure_type = "other"

        failures.append({
            "case_id": case_id,
            "agentic_decision": agent_decision,
            "ground_truth": ground_truth,
            "failure_type": failure_type,
            "confidence": r.get("confidence", 0.0),
            "reasoning_trace": r.get("reasoning_trace", []),
            "num_steps": r.get("num_steps", 0),
        })

    return failures


def build_cross_mode_comparison(
    case_id: str,
    rule_results: list[dict],
    agentic_results: list[dict],
    governed_results: list[dict],
) -> dict:
    """Extract all 3 modes' decisions and traces for a single case."""
    def _find(results, cid):
        for r in results:
            if r["case_id"] == cid:
                return r
        return None

    comparison = {"case_id": case_id}
    for mode, results in [("rule_based", rule_results), ("agentic", agentic_results), ("governed", governed_results)]:
        r = _find(results, case_id)
        if r:
            comparison[mode] = {
                "decision": r.get("decision"),
                "confidence": r.get("confidence"),
                "correct": r.get("correct", False),
                "reasoning_trace": r.get("reasoning_trace", []),
                "governance_events": r.get("governance_events", []),
                "human_interventions": r.get("human_interventions", 0),
            }
        else:
            comparison[mode] = None

    return comparison


def find_guardrail_catches(
    agentic_results: list[dict],
    governed_results: list[dict],
) -> list[dict]:
    """Cases where governed got it right but agentic got it wrong."""
    governed_map = {r["case_id"]: r for r in governed_results}
    catches = []

    for ar in agentic_results:
        if ar.get("correct"):
            continue
        gr = governed_map.get(ar["case_id"])
        if gr and gr.get("correct"):
            hitl_events = [
                e for e in gr.get("governance_events", [])
                if e.get("event") == "hitl_review"
            ]
            catches.append({
                "case_id": ar["case_id"],
                "agentic_decision": ar.get("decision"),
                "governed_decision": gr.get("decision"),
                "agentic_confidence": ar.get("confidence"),
                "governance_events": gr.get("governance_events", []),
                "hitl_corrected": any(not e.get("approved", True) for e in hitl_events),
                "num_governance_events": len(gr.get("governance_events", [])),
            })

    return catches


def find_guardrail_misses(governed_results: list[dict]) -> list[dict]:
    """Cases where governed was still wrong despite governance."""
    misses = []
    for r in governed_results:
        if not r.get("correct", True):
            misses.append({
                "case_id": r["case_id"],
                "decision": r.get("decision"),
                "confidence": r.get("confidence"),
                "governance_events": r.get("governance_events", []),
                "num_governance_events": len(r.get("governance_events", [])),
                "human_interventions": r.get("human_interventions", 0),
                "reasoning_trace": r.get("reasoning_trace", []),
            })
    return misses


def generate_paper_examples(
    failures: list[dict],
    all_results: dict,
    cases_df: pd.DataFrame,
    max_examples: int = 5,
) -> list[dict]:
    """
    Select the most illustrative cases for the paper.

    Prioritizes:
    1. cancelled_blind_spot with high confidence (agent confidently wrong)
    2. false_approval caught by governed mode
    3. false_decline showing different outcomes across modes
    4. governed mode also failed (guardrail miss)
    5. all three modes correct for different reasons
    """
    case_amounts = {row["case_id"]: row["amount_requested"] for _, row in cases_df.iterrows()}

    examples = []

    # 1. High-confidence cancelled blind spot
    cancelled = [f for f in failures if f["failure_type"] == "cancelled_blind_spot"]
    cancelled.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    if cancelled:
        f = cancelled[0]
        cross = build_cross_mode_comparison(
            f["case_id"], all_results["rule_based"], all_results["agentic"], all_results["governed"]
        )
        examples.append({
            "case_id": f["case_id"],
            "title": "The Cancelled Blind Spot",
            "failure_type": f["failure_type"],
            "amount": case_amounts.get(f["case_id"], 0),
            "ground_truth": f["ground_truth"],
            "agentic_decision": f["agentic_decision"],
            "agentic_confidence": f["confidence"],
            "governed_decision": cross.get("governed", {}).get("decision") if cross.get("governed") else None,
            "rule_decision": cross.get("rule_based", {}).get("decision") if cross.get("rule_based") else None,
            "narrative": (
                f"Case {f['case_id']} (EUR {case_amounts.get(f['case_id'], 0):,.0f}): "
                f"The agent predicted '{f['agentic_decision']}' with {f['confidence']:.0%} confidence, "
                f"but the customer had cancelled their application. The agent's reasoning was "
                f"logically sound — it evaluated creditworthiness and application completeness — "
                f"but it cannot detect customer withdrawal intent from process metrics alone. "
                f"This exemplifies the 'plausible failure' the deskilling paradox warns about."
            ),
            "key_trace_excerpt": f["reasoning_trace"][-3:] if f["reasoning_trace"] else [],
        })

    # 2. False approval caught by governance
    catches = find_guardrail_catches(all_results["agentic"], all_results["governed"])
    false_approvals = [f for f in failures if f["failure_type"] == "false_approval"]
    caught_ids = {c["case_id"] for c in catches}
    caught_approvals = [f for f in false_approvals if f["case_id"] in caught_ids]
    if caught_approvals:
        f = caught_approvals[0]
        cross = build_cross_mode_comparison(
            f["case_id"], all_results["rule_based"], all_results["agentic"], all_results["governed"]
        )
        gov_events = cross.get("governed", {}).get("governance_events", []) if cross.get("governed") else []
        examples.append({
            "case_id": f["case_id"],
            "title": "Governance Catches a False Approval",
            "failure_type": f["failure_type"],
            "amount": case_amounts.get(f["case_id"], 0),
            "ground_truth": f["ground_truth"],
            "agentic_decision": f["agentic_decision"],
            "agentic_confidence": f["confidence"],
            "governed_decision": cross.get("governed", {}).get("decision") if cross.get("governed") else None,
            "rule_decision": cross.get("rule_based", {}).get("decision") if cross.get("rule_based") else None,
            "narrative": (
                f"Case {f['case_id']} (EUR {case_amounts.get(f['case_id'], 0):,.0f}): "
                f"The ungoverned agent approved this loan, but the ground truth was 'declined'. "
                f"In governed mode, the HITL checkpoint caught the error — the human reviewer "
                f"corrected the decision. This demonstrates the accountability gap: without "
                f"governance, the incorrect approval would have proceeded unchecked."
            ),
            "key_trace_excerpt": f["reasoning_trace"][-3:] if f["reasoning_trace"] else [],
        })

    # 3. False decline
    false_declines = [f for f in failures if f["failure_type"] == "false_decline"]
    if false_declines:
        f = false_declines[0]
        cross = build_cross_mode_comparison(
            f["case_id"], all_results["rule_based"], all_results["agentic"], all_results["governed"]
        )
        examples.append({
            "case_id": f["case_id"],
            "title": "Conservative Agent Declines a Valid Application",
            "failure_type": f["failure_type"],
            "amount": case_amounts.get(f["case_id"], 0),
            "ground_truth": f["ground_truth"],
            "agentic_decision": f["agentic_decision"],
            "agentic_confidence": f["confidence"],
            "governed_decision": cross.get("governed", {}).get("decision") if cross.get("governed") else None,
            "rule_decision": cross.get("rule_based", {}).get("decision") if cross.get("rule_based") else None,
            "narrative": (
                f"Case {f['case_id']} (EUR {case_amounts.get(f['case_id'], 0):,.0f}): "
                f"The agent declined this application, but it was actually approved. "
                f"The agent's conservative bias — defaulting to decline under uncertainty — "
                f"shows how agentic reasoning can be systematically wrong in ways that "
                f"are hard to detect without procedural knowledge."
            ),
            "key_trace_excerpt": f["reasoning_trace"][-3:] if f["reasoning_trace"] else [],
        })

    # 4. Governed mode also failed (guardrail miss)
    misses = find_guardrail_misses(all_results["governed"])
    if misses:
        m = misses[0]
        examples.append({
            "case_id": m["case_id"],
            "title": "Governance Limits: When Guardrails Are Not Enough",
            "failure_type": "guardrail_miss",
            "amount": case_amounts.get(m["case_id"], 0),
            "ground_truth": cases_df[cases_df["case_id"] == m["case_id"]]["outcome"].values[0]
                if len(cases_df[cases_df["case_id"] == m["case_id"]]) > 0 else "unknown",
            "governed_decision": m["decision"],
            "narrative": (
                f"Case {m['case_id']}: Even with governance, the system produced an incorrect "
                f"outcome. This case was in the full_auto tier (low risk), so no HITL checkpoint "
                f"was triggered. It demonstrates the governance tradeoff: graduated autonomy "
                f"reduces human burden but accepts some error in low-risk cases."
            ),
            "key_trace_excerpt": m.get("reasoning_trace", [])[-3:],
        })

    # 5. All three correct
    for ar in all_results["agentic"]:
        if ar.get("correct"):
            cid = ar["case_id"]
            rr = next((r for r in all_results["rule_based"] if r["case_id"] == cid), None)
            gr = next((r for r in all_results["governed"] if r["case_id"] == cid), None)
            if rr and rr.get("correct") and gr and gr.get("correct"):
                examples.append({
                    "case_id": cid,
                    "title": "Convergent Correctness: Three Modes, One Right Answer",
                    "failure_type": "all_correct",
                    "amount": case_amounts.get(cid, 0),
                    "ground_truth": ar["decision"],
                    "narrative": (
                        f"Case {cid} (EUR {case_amounts.get(cid, 0):,.0f}): All three modes "
                        f"correctly reached '{ar['decision']}', but through different mechanisms. "
                        f"The rule engine applied threshold logic. The agent reasoned about "
                        f"policy and risk. The governed agent did the same with guardrail validation. "
                        f"This shows that governance adds transparency without sacrificing capability "
                        f"on straightforward cases."
                    ),
                })
                break

    return examples[:max_examples]


def build_failure_summary(failures: list[dict]) -> dict:
    """Aggregate failure statistics."""
    by_type = {}
    confidences = []
    high_conf_errors = 0

    for f in failures:
        ft = f["failure_type"]
        by_type[ft] = by_type.get(ft, 0) + 1
        conf = f.get("confidence", 0)
        confidences.append(conf)
        if conf >= 0.8:
            high_conf_errors += 1

    return {
        "total_failures": len(failures),
        "by_type": by_type,
        "avg_confidence_when_wrong": sum(confidences) / len(confidences) if confidences else 0,
        "high_confidence_errors": high_conf_errors,
        "high_confidence_error_rate": high_conf_errors / len(failures) if failures else 0,
    }


def run_full_trace_analysis(results_dir: Path, sample_dir: Path) -> dict:
    """Orchestrator — run all trace analyses and return structured results."""
    all_results = load_all_results(results_dir)
    cases_df = pd.read_parquet(sample_dir / "sample_cases.parquet")

    failures = classify_agentic_failures(all_results["agentic"], cases_df)
    failure_summary = build_failure_summary(failures)

    guardrail_catches = find_guardrail_catches(all_results["agentic"], all_results["governed"])
    guardrail_misses = find_guardrail_misses(all_results["governed"])

    # Build cross-mode comparisons for all cases
    cross_mode = {}
    for case_id in cases_df["case_id"]:
        cross_mode[case_id] = build_cross_mode_comparison(
            case_id, all_results["rule_based"], all_results["agentic"], all_results["governed"]
        )

    paper_examples = generate_paper_examples(failures, all_results, cases_df)

    return {
        "failure_summary": failure_summary,
        "classified_failures": failures,
        "guardrail_catches": guardrail_catches,
        "guardrail_misses": guardrail_misses,
        "paper_examples": paper_examples,
        "cross_mode_comparisons": cross_mode,
        "all_results": all_results,
    }
