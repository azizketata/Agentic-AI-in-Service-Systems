"""Tests for qualitative trace analysis."""

import pytest
from pathlib import Path

from src.evaluation.trace_analysis import (
    classify_agentic_failures,
    build_cross_mode_comparison,
    find_guardrail_catches,
    find_guardrail_misses,
    build_failure_summary,
)


@pytest.fixture
def agentic_results():
    return [
        {"case_id": "C1", "decision": "approved", "correct": False, "confidence": 0.9, "reasoning_trace": ["t1"], "num_steps": 3},
        {"case_id": "C2", "decision": "declined", "correct": True, "confidence": 0.85, "reasoning_trace": ["t2"], "num_steps": 3},
        {"case_id": "C3", "decision": "approved", "correct": False, "confidence": 0.8, "reasoning_trace": ["t3"], "num_steps": 3},
        {"case_id": "C4", "decision": "declined", "correct": False, "confidence": 0.75, "reasoning_trace": ["t4"], "num_steps": 3},
    ]


@pytest.fixture
def governed_results():
    return [
        {"case_id": "C1", "decision": "declined", "correct": True, "governance_events": [{"event": "hitl_review", "approved": False}], "human_interventions": 1},
        {"case_id": "C2", "decision": "declined", "correct": True, "governance_events": [], "human_interventions": 0},
        {"case_id": "C3", "decision": "cancelled", "correct": True, "governance_events": [{"event": "hitl_review", "approved": False}], "human_interventions": 1},
        {"case_id": "C4", "decision": "declined", "correct": False, "governance_events": [{"event": "guardrail_check", "blocked": True}], "human_interventions": 0},
    ]


@pytest.fixture
def cases_df():
    import pandas as pd
    return pd.DataFrame([
        {"case_id": "C1", "outcome": "declined", "amount_requested": 10000, "risk_tier": "medium"},
        {"case_id": "C2", "outcome": "declined", "amount_requested": 5000, "risk_tier": "low"},
        {"case_id": "C3", "outcome": "cancelled", "amount_requested": 8000, "risk_tier": "medium"},
        {"case_id": "C4", "outcome": "approved", "amount_requested": 15000, "risk_tier": "medium"},
    ])


class TestClassifyFailures:
    def test_classifies_false_approval(self, agentic_results, cases_df):
        failures = classify_agentic_failures(agentic_results, cases_df)
        fa = [f for f in failures if f["failure_type"] == "false_approval"]
        assert len(fa) == 1
        assert fa[0]["case_id"] == "C1"

    def test_classifies_cancelled_blind_spot(self, agentic_results, cases_df):
        failures = classify_agentic_failures(agentic_results, cases_df)
        cbs = [f for f in failures if f["failure_type"] == "cancelled_blind_spot"]
        assert len(cbs) == 1
        assert cbs[0]["case_id"] == "C3"

    def test_classifies_false_decline(self, agentic_results, cases_df):
        failures = classify_agentic_failures(agentic_results, cases_df)
        fd = [f for f in failures if f["failure_type"] == "false_decline"]
        assert len(fd) == 1
        assert fd[0]["case_id"] == "C4"

    def test_skips_correct_cases(self, agentic_results, cases_df):
        failures = classify_agentic_failures(agentic_results, cases_df)
        assert all(f["case_id"] != "C2" for f in failures)

    def test_total_failures(self, agentic_results, cases_df):
        failures = classify_agentic_failures(agentic_results, cases_df)
        assert len(failures) == 3


class TestGuardrailEffectiveness:
    def test_finds_catches(self, agentic_results, governed_results):
        catches = find_guardrail_catches(agentic_results, governed_results)
        assert len(catches) >= 1
        assert all(c["case_id"] in ["C1", "C3"] for c in catches)

    def test_finds_misses(self, governed_results):
        misses = find_guardrail_misses(governed_results)
        assert len(misses) == 1
        assert misses[0]["case_id"] == "C4"


class TestFailureSummary:
    def test_summary_counts(self, agentic_results, cases_df):
        failures = classify_agentic_failures(agentic_results, cases_df)
        summary = build_failure_summary(failures)
        assert summary["total_failures"] == 3
        assert summary["by_type"]["false_approval"] == 1
        assert summary["by_type"]["cancelled_blind_spot"] == 1
        assert summary["by_type"]["false_decline"] == 1

    def test_avg_confidence(self, agentic_results, cases_df):
        failures = classify_agentic_failures(agentic_results, cases_df)
        summary = build_failure_summary(failures)
        assert 0 < summary["avg_confidence_when_wrong"] <= 1.0

    def test_empty_failures(self):
        summary = build_failure_summary([])
        assert summary["total_failures"] == 0


class TestCrossMode:
    def test_builds_comparison(self, agentic_results, governed_results):
        rule_results = [{"case_id": "C1", "decision": "declined", "correct": True, "confidence": 1.0, "reasoning_trace": []}]
        comp = build_cross_mode_comparison("C1", rule_results, agentic_results, governed_results)
        assert comp["case_id"] == "C1"
        assert comp["rule_based"]["decision"] == "declined"
        assert comp["agentic"]["decision"] == "approved"
        assert comp["governed"]["decision"] == "declined"
