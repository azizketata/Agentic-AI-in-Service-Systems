"""Tests for the evaluation engine."""

import pytest

from src.common.types import LoanOutcome, ProcessingMode
from src.data.schemas import CaseResult
from src.evaluation.metrics import compute_case_metrics, compute_aggregate_metrics, results_to_dataframe
from src.evaluation.comparison import build_comparison_table, build_radar_chart_data


@pytest.fixture
def mock_results():
    """Create mock results for all three modes."""
    cases = [
        ("C1", LoanOutcome.APPROVED, True, 0.9),
        ("C2", LoanOutcome.DECLINED, True, 0.85),
        ("C3", LoanOutcome.DECLINED, False, 0.6),
        ("C4", LoanOutcome.APPROVED, True, 0.95),
    ]

    def make_results(mode, hitl=0, violations=0):
        results = []
        for case_id, decision, correct, conf in cases:
            results.append(CaseResult(
                case_id=case_id,
                mode=mode,
                decision=decision,
                confidence=conf,
                steps_taken=[{"step": "s1"}, {"step": "s2"}],
                reasoning_trace=["trace1", "trace2"],
                processing_time_ms=100.0,
                governance_events=[{"e": 1}] if mode == "governed" else [],
                human_interventions=hitl,
                contract_violations=violations,
                correct=correct,
            ))
        return results

    return {
        "rule": make_results("rule_based"),
        "agentic": make_results("agentic"),
        "governed": make_results("governed", hitl=1, violations=0),
    }


class TestMetrics:
    def test_compute_case_metrics_not_empty(self, mock_results):
        result = mock_results["rule"][0]
        metrics = compute_case_metrics(result)
        assert metrics["case_id"] == "C1"
        assert metrics["mode"] == "rule_based"
        assert metrics["correct"] is True
        assert metrics["num_steps"] == 2
        assert metrics["confidence"] == 0.9

    def test_compute_aggregate_metrics(self, mock_results):
        agg = compute_aggregate_metrics(mock_results["rule"])
        assert agg["total_cases"] == 4
        assert agg["accuracy"] == 0.75  # 3/4 correct
        assert agg["avg_steps"] == 2.0
        assert agg["avg_confidence"] is not None
        assert agg["avg_confidence"] > 0

    def test_aggregate_empty_list(self):
        assert compute_aggregate_metrics([]) == {}

    def test_results_to_dataframe(self, mock_results):
        df = results_to_dataframe(mock_results["rule"])
        assert len(df) == 4
        assert "case_id" in df.columns
        assert "correct" in df.columns
        assert "num_steps" in df.columns
        assert df["num_steps"].sum() > 0, "Steps should not all be zero"

    def test_governed_has_governance_events(self, mock_results):
        agg = compute_aggregate_metrics(mock_results["governed"])
        assert agg["total_human_interventions"] == 4  # 1 per case * 4 cases
        assert agg["human_intervention_rate"] == 1.0


class TestComparison:
    def test_comparison_table_structure(self, mock_results):
        table = build_comparison_table(
            mock_results["rule"],
            mock_results["agentic"],
            mock_results["governed"],
        )
        assert "Metric" in table.columns
        assert "Rule-Based" in table.columns
        assert "Agentic" in table.columns
        assert "Governed" in table.columns
        assert len(table) >= 5, "Should have at least 5 metric rows"

    def test_comparison_table_no_empty_values(self, mock_results):
        table = build_comparison_table(
            mock_results["rule"],
            mock_results["agentic"],
            mock_results["governed"],
        )
        for col in ["Rule-Based", "Agentic", "Governed"]:
            for val in table[col]:
                assert val != "", f"Empty value in {col}"
                assert val is not None, f"None value in {col}"

    def test_radar_chart_data_structure(self, mock_results):
        data = build_radar_chart_data(
            mock_results["rule"],
            mock_results["agentic"],
            mock_results["governed"],
        )
        assert "categories" in data
        assert "Rule-Based" in data
        assert "Agentic" in data
        assert "Governed" in data
        assert len(data["categories"]) == 5
        assert len(data["Rule-Based"]) == 5
        # All values should be between 0 and 1
        for mode in ["Rule-Based", "Agentic", "Governed"]:
            for val in data[mode]:
                assert 0 <= val <= 1, f"Radar value {val} out of range for {mode}"
