"""Tests for the data layer — schemas, loader, preprocessor."""

from pathlib import Path

import pandas as pd
import pytest

from src.data.schemas import LoanApplication, CaseResult, ProcessEvent
from src.common.types import LoanOutcome, RiskTier


class TestSchemas:
    def test_loan_application_creation(self, sample_case):
        app = LoanApplication(
            case_id=sample_case["case_id"],
            amount_requested=sample_case["amount_requested"],
            risk_tier=RiskTier(sample_case["risk_tier"]),
            ground_truth_outcome=LoanOutcome(sample_case["outcome"]),
            num_events=sample_case["num_events"],
            num_offers=sample_case["num_offers"],
        )
        assert app.case_id == "TEST_001"
        assert app.amount_requested == 15000.0
        assert app.risk_tier == RiskTier.MEDIUM
        assert app.ground_truth_outcome == LoanOutcome.APPROVED

    def test_loan_application_activity_sequence(self):
        app = LoanApplication(
            case_id="X",
            amount_requested=1000,
            risk_tier=RiskTier.LOW,
            ground_truth_outcome=LoanOutcome.APPROVED,
            events=[
                ProcessEvent(activity="A_SUBMITTED", timestamp="2024-01-01T00:00:00"),
                ProcessEvent(activity="A_ACCEPTED", timestamp="2024-01-02T00:00:00"),
            ],
        )
        assert app.activity_sequence == ["A_SUBMITTED", "A_ACCEPTED"]

    def test_case_result_creation(self):
        result = CaseResult(
            case_id="X",
            mode="rule_based",
            decision=LoanOutcome.APPROVED,
            confidence=1.0,
            correct=True,
        )
        assert result.correct is True
        assert result.decision == LoanOutcome.APPROVED
        assert result.human_interventions == 0
        assert result.contract_violations == 0

    def test_case_result_empty_traces(self):
        result = CaseResult(case_id="X", mode="agentic")
        assert result.steps_taken == []
        assert result.reasoning_trace == []
        assert result.governance_events == []


class TestPreprocessedData:
    def test_sample_cases_exist(self, real_sample_df):
        assert len(real_sample_df) > 0, "Sample cases should not be empty"

    def test_sample_cases_have_required_columns(self, real_sample_df):
        required = ["case_id", "amount_requested", "risk_tier", "outcome", "num_events"]
        for col in required:
            assert col in real_sample_df.columns, f"Missing column: {col}"

    def test_sample_cases_outcomes_are_valid(self, real_sample_df):
        valid_outcomes = {"approved", "declined", "cancelled"}
        actual = set(real_sample_df["outcome"].unique())
        assert actual.issubset(valid_outcomes), f"Unexpected outcomes: {actual - valid_outcomes}"

    def test_sample_cases_risk_tiers_are_valid(self, real_sample_df):
        valid_tiers = {"low", "medium", "high"}
        actual = set(real_sample_df["risk_tier"].unique())
        assert actual.issubset(valid_tiers), f"Unexpected tiers: {actual - valid_tiers}"

    def test_sample_cases_amounts_positive(self, real_sample_df):
        assert (real_sample_df["amount_requested"] > 0).all(), "All amounts should be positive"

    def test_sample_is_stratified(self, real_sample_df):
        """Sample should have cases across different outcomes and tiers."""
        assert len(real_sample_df["outcome"].unique()) >= 2, "Sample should cover multiple outcomes"
        assert len(real_sample_df["risk_tier"].unique()) >= 2, "Sample should cover multiple tiers"
