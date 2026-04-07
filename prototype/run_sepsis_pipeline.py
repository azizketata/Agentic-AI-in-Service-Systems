"""
Sepsis Pipeline Runner — Process sepsis cases through all three modes.

Usage: python run_sepsis_pipeline.py [--sample-size N]
"""

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

from src.common.llm import get_llm
from src.agent.sepsis_tools import ALL_SEPSIS_TOOLS
from src.agent.sepsis_prompts import SEPSIS_SYSTEM_PROMPT, SEPSIS_ASSESSMENT_TEMPLATE
from src.governance.autonomy_tiers import classify_autonomy_tier
from src.governance.intent_contract import create_intent_contract
from src.governance.guardrails import run_all_guardrails, any_guardrail_blocked
from src.governance.hitl import simulate_hitl_response, create_hitl_request, should_trigger_hitl
from src.governance.autonomy_tiers import get_hitl_points
from src.governance.audit_logger import AuditLog

RESULTS_DIR = Path(__file__).parent / "data" / "results_sepsis"


def run_rule_based(cases_df: pd.DataFrame) -> list[dict]:
    """Process all cases through the sepsis rule engine."""
    from src.rule_engine.sepsis_engine import evaluate_sepsis_patient

    print(f"\n{'='*60}")
    print("MODE 1: RULE-BASED (Clinical Rules Baseline)")
    print(f"{'='*60}")

    results = []
    start = time.perf_counter()

    for _, case in cases_df.iterrows():
        c = case.to_dict()
        decision = evaluate_sepsis_patient(
            age=c.get("age", c.get("amount_requested", 0)),
            infection_suspected=c.get("infection_suspected", False),
            sirs_criteria=c.get("sirs_criteria", False),
            hypotension=c.get("hypotension", False),
            organ_dysfunction=c.get("organ_dysfunction", False),
            has_antibiotics=c.get("has_antibiotics", False),
            num_events=c.get("num_events", 0),
            lab_test_count=c.get("lab_test_count", c.get("num_offers", 0)),
            case_duration_hours=c.get("case_duration_hours", 0),
        )
        traces = [f"Rule: {s['step']} — {'PASS' if s.get('passed') else 'FAIL'}" for s in decision.steps]
        traces.append(f"Decision: {decision.outcome} — {decision.reason}")

        results.append({
            "case_id": c["case_id"],
            "mode": "rule_based",
            "decision": decision.outcome,
            "confidence": 1.0,
            "num_steps": len(decision.steps),
            "steps_taken": decision.steps,
            "reasoning_trace": traces,
            "processing_time_ms": 0,
            "governance_events": [],
            "human_interventions": 0,
            "contract_violations": 0,
            "correct": decision.outcome == c["outcome"],
        })

    elapsed = time.perf_counter() - start
    correct = sum(1 for r in results if r["correct"])
    print(f"Processed {len(results)} cases in {elapsed:.1f}s")
    print(f"Accuracy: {correct}/{len(results)} ({correct/len(results):.1%})")
    return results


def run_agentic(cases_df: pd.DataFrame) -> list[dict]:
    """Process all cases through ungoverned sepsis agent."""
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

    print(f"\n{'='*60}")
    print("MODE 2: AGENTIC (Ungoverned Clinical Agent)")
    print(f"{'='*60}")

    llm = get_llm().bind_tools(ALL_SEPSIS_TOOLS)
    tool_map = {t.name: t for t in ALL_SEPSIS_TOOLS}
    results = []

    for i, (_, case) in enumerate(cases_df.iterrows()):
        c = case.to_dict()
        print(f"  [{i+1}/{len(cases_df)}] Case {c['case_id']} (age={c.get('age', '?')}, {c['risk_tier']})...", end=" ", flush=True)

        start = time.perf_counter()
        traces = []
        try:
            prompt = SEPSIS_ASSESSMENT_TEMPLATE.format(**c)
            messages = [SystemMessage(content=SEPSIS_SYSTEM_PROMPT), HumanMessage(content=prompt)]
            traces.append(f"[ASSESS] Sent case {c['case_id']} to LLM")

            # ReAct loop (max 5 iterations)
            for step in range(5):
                response = llm.invoke(messages)
                messages.append(response)

                if isinstance(response, AIMessage) and response.tool_calls:
                    for tc in response.tool_calls:
                        if tc["name"] in tool_map:
                            result = tool_map[tc["name"]].invoke(tc["args"])
                            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
                            traces.append(f"[TOOL] {tc['name']}({tc['args']}) -> {str(result)[:150]}")
                else:
                    break

            # Parse decision
            content = response.content if isinstance(response.content, str) else str(response.content)
            decision = _parse_sepsis_decision(content)
            confidence = _parse_confidence(content)
            traces.append(f"[DECIDE] Decision: {decision}, Confidence: {confidence}")

            elapsed_ms = (time.perf_counter() - start) * 1000
            correct = decision == c["outcome"]
            status = "OK" if correct else "WRONG"
            print(f"{status} ({decision} vs {c['outcome']}) [{elapsed_ms:.0f}ms]")

            results.append({
                "case_id": c["case_id"], "mode": "agentic", "decision": decision,
                "confidence": confidence, "num_steps": len(traces),
                "steps_taken": [{"step": f"s{i}"} for i in range(len(traces))],
                "reasoning_trace": traces, "processing_time_ms": elapsed_ms,
                "governance_events": [], "human_interventions": 0,
                "contract_violations": 0, "correct": correct,
            })
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            print(f"ERROR: {e}")
            results.append({
                "case_id": c["case_id"], "mode": "agentic", "decision": "discharged",
                "confidence": 0, "num_steps": 0, "steps_taken": [],
                "reasoning_trace": [f"Error: {e}"], "processing_time_ms": elapsed_ms,
                "governance_events": [], "human_interventions": 0,
                "contract_violations": 0, "correct": "discharged" == c["outcome"],
            })

    correct = sum(1 for r in results if r["correct"])
    print(f"\nAgentic accuracy: {correct}/{len(results)} ({correct/len(results):.1%})")
    return results


def run_governed(cases_df: pd.DataFrame) -> list[dict]:
    """Process all cases through governed sepsis agent."""
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

    print(f"\n{'='*60}")
    print("MODE 3: GOVERNED (Clinical Agent + Governance)")
    print(f"{'='*60}")

    llm = get_llm().bind_tools(ALL_SEPSIS_TOOLS)
    tool_map = {t.name: t for t in ALL_SEPSIS_TOOLS}
    audit_log = AuditLog()
    results = []

    for i, (_, case) in enumerate(cases_df.iterrows()):
        c = case.to_dict()
        print(f"  [{i+1}/{len(cases_df)}] Case {c['case_id']} (age={c.get('age', '?')}, {c['risk_tier']})...", end=" ", flush=True)

        start = time.perf_counter()
        traces = []
        gov_events = []

        try:
            # DP1: Intent contract
            tier = classify_autonomy_tier(c.get("age", 0), c["risk_tier"])
            contract = create_intent_contract(c["case_id"], c.get("age", 0), tier.value)
            traces.append(f"[GOV] Intent contract created. Autonomy tier: {tier.value}")
            gov_events.append({"event": "contract_created", "tier": tier.value})

            # Agent reasoning (same as ungoverned)
            prompt = SEPSIS_ASSESSMENT_TEMPLATE.format(**c)
            messages = [SystemMessage(content=SEPSIS_SYSTEM_PROMPT), HumanMessage(content=prompt)]
            traces.append(f"[ASSESS] Sent case {c['case_id']} to LLM")

            for step in range(5):
                response = llm.invoke(messages)
                messages.append(response)
                if isinstance(response, AIMessage) and response.tool_calls:
                    for tc in response.tool_calls:
                        if tc["name"] in tool_map:
                            result = tool_map[tc["name"]].invoke(tc["args"])
                            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
                            traces.append(f"[TOOL] {tc['name']}({tc['args']}) -> {str(result)[:150]}")
                else:
                    break

            content = response.content if isinstance(response.content, str) else str(response.content)
            decision = _parse_sepsis_decision(content)
            confidence = _parse_confidence(content)
            traces.append(f"[DECIDE] Decision: {decision}, Confidence: {confidence}")

            # DP3: Guardrail check
            guardrail_results = run_all_guardrails(
                contract, "make_decision", len(traces), confidence, c.get("age", 0)
            )
            blocked = any_guardrail_blocked(guardrail_results)
            for gr in guardrail_results:
                status = "PASS" if gr.allowed else "BLOCK"
                traces.append(f"[GUARDRAIL] {gr.guardrail_name}: {status} -- {gr.reason}")
            gov_events.append({"event": "guardrail_check", "blocked": blocked})

            # DP2 + DP4: HITL based on tier
            hitl_points = get_hitl_points(tier)
            needs_hitl = should_trigger_hitl(tier.value, "final_decision", hitl_points) or blocked
            hitl_count = 0

            if needs_hitl:
                req = create_hitl_request(c["case_id"], "final_decision", decision, traces, confidence, tier.value)
                resp = simulate_hitl_response(req, c["outcome"])
                hitl_count = 1
                traces.append(f"[HITL] Human review: {resp.human_decision} -- {resp.feedback}")
                gov_events.append({"event": "hitl_review", "decision": resp.human_decision, "approved": resp.approved})
                if resp.modified_action:
                    decision = resp.modified_action
                    traces.append(f"[HITL] Decision overridden to: {decision}")

            elapsed_ms = (time.perf_counter() - start) * 1000
            correct = decision == c["outcome"]
            status_str = "OK" if correct else "WRONG"
            print(f"{status_str} ({decision} vs {c['outcome']}) [tier={tier.value}, hitl={hitl_count}] [{elapsed_ms:.0f}ms]")

            results.append({
                "case_id": c["case_id"], "mode": "governed", "decision": decision,
                "confidence": confidence, "num_steps": len(traces),
                "steps_taken": [{"step": f"s{i}"} for i in range(len(traces))],
                "reasoning_trace": traces, "processing_time_ms": elapsed_ms,
                "governance_events": gov_events, "human_interventions": hitl_count,
                "contract_violations": 1 if blocked else 0, "correct": correct,
            })
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            print(f"ERROR: {e}")
            results.append({
                "case_id": c["case_id"], "mode": "governed", "decision": "discharged",
                "confidence": 0, "num_steps": 0, "steps_taken": [],
                "reasoning_trace": [f"Error: {e}"], "processing_time_ms": elapsed_ms,
                "governance_events": [], "human_interventions": 0,
                "contract_violations": 0, "correct": "discharged" == c["outcome"],
            })

    correct = sum(1 for r in results if r["correct"])
    print(f"\nGoverned accuracy: {correct}/{len(results)} ({correct/len(results):.1%})")

    # Save audit log
    audit_path = RESULTS_DIR / "audit_log.json"
    with open(audit_path, "w") as f:
        f.write(audit_log.to_json())

    return results


def _parse_sepsis_decision(content: str) -> str:
    upper = content.upper()
    if "DECISION: DISCHARGED" in upper or "DECISION:DISCHARGED" in upper:
        return "discharged"
    elif "DECISION: RETURNED" in upper or "DECISION:RETURNED" in upper:
        return "returned"
    elif "DISCHARGED" in upper and "RETURNED" not in upper:
        return "discharged"
    elif "RETURNED" in upper:
        return "returned"
    return "discharged"


def _parse_confidence(content: str) -> float:
    match = re.search(r"CONFIDENCE:\s*([\d.]+)", content, re.IGNORECASE)
    if match:
        try:
            return min(1.0, max(0.0, float(match.group(1))))
        except ValueError:
            pass
    return 0.5


def save_results(results: list[dict], mode: str):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{mode}_results.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Saved {len(results)} results to {path}")


def main():
    sample_size = 100
    for i, arg in enumerate(sys.argv):
        if arg == "--sample-size" and i + 1 < len(sys.argv):
            sample_size = int(sys.argv[i + 1])

    sample_dir = Path(__file__).parent / "data" / "sample_sepsis"
    cases_df = pd.read_parquet(sample_dir / "sample_cases.parquet")

    if sample_size < len(cases_df):
        cases_df = cases_df.head(sample_size)

    print(f"Processing {len(cases_df)} sepsis cases")
    print(f"Outcomes: {cases_df['outcome'].value_counts().to_dict()}")
    print(f"Risk tiers: {cases_df['risk_tier'].value_counts().to_dict()}")

    rule_results = run_rule_based(cases_df)
    save_results(rule_results, "rule_based")

    agentic_results = run_agentic(cases_df)
    save_results(agentic_results, "agentic")

    governed_results = run_governed(cases_df)
    save_results(governed_results, "governed")

    print(f"\n{'='*60}")
    print("FINAL SUMMARY (SEPSIS)")
    print(f"{'='*60}")
    for mode, results in [("Rule-Based", rule_results), ("Agentic", agentic_results), ("Governed", governed_results)]:
        correct = sum(1 for r in results if r["correct"])
        n = len(results)
        print(f"  {mode:12s}: {correct}/{n} ({correct/n:.1%}) accuracy")


if __name__ == "__main__":
    main()
