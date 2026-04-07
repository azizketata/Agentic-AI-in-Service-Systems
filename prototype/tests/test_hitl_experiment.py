"""Tests for HITL experiment data model."""

import pytest
from src.evaluation.hitl_experiment import compute_experiment_metrics, ExperimentTrial


@pytest.fixture
def sample_trials():
    return [
        {
            "participant_id": "P1", "experience_level": "expert",
            "case_id": "C1", "agent_decision": "approved", "agent_confidence": 0.9,
            "human_decision": "approve_agent_decision", "human_final_decision": "approved",
            "human_reasoning": "Looks correct", "review_time_seconds": 30,
            "sections_expanded": ["step_0", "step_1"], "ground_truth": "approved",
            "human_correct": True, "agent_correct": True,
        },
        {
            "participant_id": "P1", "experience_level": "expert",
            "case_id": "C2", "agent_decision": "approved", "agent_confidence": 0.85,
            "human_decision": "modify", "human_final_decision": "declined",
            "human_reasoning": "Should be declined", "review_time_seconds": 45,
            "sections_expanded": ["step_0", "step_1", "step_2"], "ground_truth": "declined",
            "human_correct": True, "agent_correct": False,
        },
        {
            "participant_id": "P2", "experience_level": "novice",
            "case_id": "C3", "agent_decision": "declined", "agent_confidence": 0.7,
            "human_decision": "approve_agent_decision", "human_final_decision": "declined",
            "human_reasoning": "Agree", "review_time_seconds": 15,
            "sections_expanded": [], "ground_truth": "approved",
            "human_correct": False, "agent_correct": False,
        },
    ]


class TestExperimentMetrics:
    def test_basic_metrics(self, sample_trials):
        metrics = compute_experiment_metrics(sample_trials)
        assert metrics["n_trials"] == 3
        assert metrics["n_participants"] == 2
        assert metrics["human_accuracy"] == pytest.approx(2 / 3)
        assert metrics["agent_accuracy"] == pytest.approx(1 / 3)

    def test_agreement_rate(self, sample_trials):
        metrics = compute_experiment_metrics(sample_trials)
        # P1-C1: human=approved, agent=approved (agree)
        # P1-C2: human=declined, agent=approved (disagree)
        # P2-C3: human=declined, agent=declined (agree)
        assert metrics["agreement_rate"] == pytest.approx(2 / 3)

    def test_correction_rate(self, sample_trials):
        metrics = compute_experiment_metrics(sample_trials)
        assert metrics["correction_rate"] == pytest.approx(1 / 3)

    def test_avg_review_time(self, sample_trials):
        metrics = compute_experiment_metrics(sample_trials)
        assert metrics["avg_review_time_seconds"] == 30.0

    def test_by_participant(self, sample_trials):
        metrics = compute_experiment_metrics(sample_trials)
        assert "P1" in metrics["by_participant"]
        assert metrics["by_participant"]["P1"]["accuracy"] == 1.0
        assert metrics["by_participant"]["P2"]["accuracy"] == 0.0

    def test_empty_trials(self):
        assert compute_experiment_metrics([]) == {}


class TestExperimentTrial:
    def test_trial_to_dict(self):
        trial = ExperimentTrial(
            participant_id="P1", experience_level="expert",
            case_id="C1", agent_decision="approved", agent_confidence=0.9,
            human_decision="approve", human_final_decision="approved",
            human_reasoning="Looks good", review_time_seconds=30,
        )
        d = trial.to_dict()
        assert d["participant_id"] == "P1"
        assert d["case_id"] == "C1"
        assert isinstance(d["sections_expanded"], list)
