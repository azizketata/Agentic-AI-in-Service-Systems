"""Tests for the rule-based engine."""

import pytest

from src.rule_engine.decision_trees import evaluate_loan, RuleDecision
from src.rule_engine.routing import get_expected_route, PROCESS_ROUTES
from src.rule_engine.engine import process_case_rule_based, process_batch_rule_based
from src.common.types import LoanOutcome


class TestDecisionTrees:
    def test_auto_approve_small_loan(self):
        result = evaluate_loan(amount=3000, num_events=10, num_offers=1, case_duration_hours=100)
        assert result.outcome == "auto_approve"
        assert result.final_decision == LoanOutcome.APPROVED
        assert result.confidence == 1.0

    def test_decline_over_limit(self):
        result = evaluate_loan(amount=60000, num_events=10, num_offers=1, case_duration_hours=100)
        assert result.outcome == "decline"
        assert result.final_decision == LoanOutcome.DECLINED

    def test_decline_zero_amount(self):
        result = evaluate_loan(amount=0, num_events=5, num_offers=0, case_duration_hours=10)
        assert result.final_decision == LoanOutcome.DECLINED

    def test_standard_review_with_offers(self):
        result = evaluate_loan(amount=15000, num_events=20, num_offers=2, case_duration_hours=200)
        assert result.outcome == "standard_review"
        assert result.final_decision == LoanOutcome.APPROVED

    def test_standard_review_no_offers_declines(self):
        result = evaluate_loan(amount=15000, num_events=20, num_offers=0, case_duration_hours=200)
        assert result.outcome == "standard_review"
        assert result.final_decision == LoanOutcome.DECLINED

    def test_senior_review_high_value(self):
        result = evaluate_loan(amount=35000, num_events=15, num_offers=2, case_duration_hours=500)
        assert result.outcome == "senior_review"
        assert result.final_decision is not None

    def test_steps_are_recorded(self):
        result = evaluate_loan(amount=3000, num_events=5, num_offers=1, case_duration_hours=50)
        assert len(result.steps) >= 3, "Should have at least 3 decision steps"
        assert all("step" in s for s in result.steps)

    def test_deterministic(self):
        """Same input should always give the same output."""
        r1 = evaluate_loan(amount=20000, num_events=15, num_offers=1, case_duration_hours=300)
        r2 = evaluate_loan(amount=20000, num_events=15, num_offers=1, case_duration_hours=300)
        assert r1.outcome == r2.outcome
        assert r1.final_decision == r2.final_decision


class TestRouting:
    def test_all_routes_exist(self):
        for outcome in ["auto_approve", "standard_review", "senior_review", "decline", "incomplete"]:
            route = get_expected_route(outcome)
            assert len(route) > 0, f"Route for {outcome} should not be empty"

    def test_all_routes_start_with_submitted(self):
        for outcome, route in PROCESS_ROUTES.items():
            assert route[0] == "A_SUBMITTED", f"Route {outcome} should start with A_SUBMITTED"

    def test_unknown_outcome_returns_incomplete(self):
        route = get_expected_route("unknown_outcome")
        assert route == PROCESS_ROUTES["incomplete"]


class TestEngine:
    def test_process_single_case(self, sample_case):
        result = process_case_rule_based(sample_case)
        assert result.case_id == "TEST_001"
        assert result.mode == "rule_based"
        assert result.decision is not None
        assert result.confidence == 1.0
        assert result.processing_time_ms >= 0
        assert len(result.reasoning_trace) > 0, "Reasoning trace should not be empty"
        assert len(result.steps_taken) > 0, "Steps should not be empty"

    def test_process_low_risk_case(self, low_risk_case):
        result = process_case_rule_based(low_risk_case)
        assert result.decision == LoanOutcome.APPROVED
        assert result.correct is True

    def test_process_over_limit_case(self, over_limit_case):
        result = process_case_rule_based(over_limit_case)
        assert result.decision == LoanOutcome.DECLINED
        assert result.correct is True

    def test_batch_processing(self, sample_cases_df):
        results = process_batch_rule_based(sample_cases_df)
        assert len(results) == len(sample_cases_df)
        assert all(r.mode == "rule_based" for r in results)
        assert all(r.decision is not None for r in results)
        assert all(len(r.reasoning_trace) > 0 for r in results), "All results should have traces"

    def test_no_empty_outputs(self, sample_cases_df):
        """Critical: ensure no result has empty decision or trace."""
        results = process_batch_rule_based(sample_cases_df)
        for r in results:
            assert r.decision is not None, f"Case {r.case_id} has None decision"
            assert r.reasoning_trace, f"Case {r.case_id} has empty reasoning trace"
            assert r.steps_taken, f"Case {r.case_id} has empty steps"
