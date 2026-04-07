"""Tests for conformance analysis trace building."""

import pytest
import pandas as pd

from src.evaluation.conformance import (
    build_rule_engine_traces,
    build_agentic_traces,
    build_governed_traces,
)


@pytest.fixture
def rule_results():
    return [
        {
            "case_id": "C1",
            "decision": "approved",
            "steps_taken": [
                {"step": "amount_check", "passed": True},
                {"step": "viability_check", "passed": True},
                {"step": "auto_approve_check", "passed": True},
            ],
        },
        {
            "case_id": "C2",
            "decision": "declined",
            "steps_taken": [
                {"step": "amount_check", "passed": False},
            ],
        },
    ]


@pytest.fixture
def agentic_results():
    return [
        {
            "case_id": "C1",
            "decision": "approved",
            "reasoning_trace": [
                "[ASSESS] Sent case C1 to LLM for evaluation",
                "[TOOL] lookup_credit_policy({'amount': 5000}) -> POLICY: Small loan",
                "[TOOL] check_application_completeness({'num_events': 10}) -> COMPLETE",
                "[TOOL] calculate_risk_score({'amount': 5000}) -> RISK: LOW",
                "[DECIDE] Decision: approved, Confidence: 0.9",
            ],
        },
    ]


@pytest.fixture
def governed_results():
    return [
        {
            "case_id": "C1",
            "decision": "approved",
            "reasoning_trace": [
                "[GOV] Intent contract created. Autonomy tier: supervised",
                "[ASSESS] Sent case C1 to LLM for evaluation",
                "[TOOL] lookup_credit_policy({'amount': 5000}) -> POLICY: Small loan",
                "[TOOL] check_application_completeness({'num_events': 10}) -> COMPLETE",
                "[DECIDE] Decision: approved, Confidence: 0.9",
                "[GUARDRAIL] confidence_gate: PASS",
                "[HITL] Human review: approve",
            ],
        },
    ]


class TestRuleEngineTraces:
    def test_builds_traces(self, rule_results):
        df = build_rule_engine_traces(rule_results)
        assert not df.empty
        assert "case:concept:name" in df.columns
        assert "concept:name" in df.columns
        assert "time:timestamp" in df.columns

    def test_traces_have_activities(self, rule_results):
        df = build_rule_engine_traces(rule_results)
        activities = df["concept:name"].unique()
        assert "A_SUBMITTED" in activities

    def test_both_cases_present(self, rule_results):
        df = build_rule_engine_traces(rule_results)
        cases = df["case:concept:name"].unique()
        assert len(cases) == 2


class TestAgenticTraces:
    def test_builds_traces(self, agentic_results):
        df = build_agentic_traces(agentic_results)
        assert not df.empty
        assert len(df) >= 3  # At least submitted + some tools + outcome

    def test_starts_with_submitted(self, agentic_results):
        df = build_agentic_traces(agentic_results)
        first_activity = df.sort_values("time:timestamp").iloc[0]["concept:name"]
        assert first_activity == "A_SUBMITTED"

    def test_ends_with_outcome(self, agentic_results):
        df = build_agentic_traces(agentic_results)
        last_activities = df.sort_values("time:timestamp").tail(2)["concept:name"].tolist()
        assert "A_ACCEPTED" in last_activities or "A_FINALIZED" in last_activities


class TestGovernedTraces:
    def test_builds_traces(self, governed_results):
        df = build_governed_traces(governed_results)
        assert not df.empty

    def test_has_governance_activities(self, governed_results):
        df = build_governed_traces(governed_results)
        activities = df["concept:name"].tolist()
        # Governance activities should be mapped to BPI 2012 activities
        assert "A_PREACCEPTED" in activities  # GOV contract -> mapped to preaccepted

    def test_more_activities_than_agentic(self, agentic_results, governed_results):
        agentic_df = build_agentic_traces(agentic_results)
        governed_df = build_governed_traces(governed_results)
        # Governed should have at least as many activities (governance adds steps)
        assert len(governed_df) >= len(agentic_df)
