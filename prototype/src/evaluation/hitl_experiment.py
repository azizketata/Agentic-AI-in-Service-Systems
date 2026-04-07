"""
Interactive HITL Experiment (Enhancement D)

Data model and metrics for the procedural literacy preservation study.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ExperimentTrial:
    participant_id: str
    experience_level: str  # novice, intermediate, expert
    case_id: str
    agent_decision: str
    agent_confidence: float
    human_decision: str  # approve, modify, reject
    human_final_decision: str  # approved, declined, cancelled
    human_reasoning: str
    review_time_seconds: float
    sections_expanded: list[str] = field(default_factory=list)
    ground_truth: str = ""
    human_correct: bool = False
    agent_correct: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


def compute_experiment_metrics(trials: list[dict]) -> dict:
    """Compute aggregate metrics from experiment trials."""
    if not trials:
        return {}

    n = len(trials)
    human_correct = sum(1 for t in trials if t.get("human_correct", False))
    agent_correct = sum(1 for t in trials if t.get("agent_correct", False))
    agreed = sum(
        1 for t in trials
        if t.get("human_final_decision") == t.get("agent_decision")
    )
    modified = sum(1 for t in trials if t.get("human_decision") == "modify")
    times = [t.get("review_time_seconds", 0) for t in trials]
    sections = [len(t.get("sections_expanded", [])) for t in trials]

    participants = {}
    for t in trials:
        pid = t.get("participant_id", "unknown")
        if pid not in participants:
            participants[pid] = {"correct": 0, "total": 0, "times": []}
        participants[pid]["total"] += 1
        if t.get("human_correct"):
            participants[pid]["correct"] += 1
        participants[pid]["times"].append(t.get("review_time_seconds", 0))

    by_participant = {
        pid: {
            "accuracy": d["correct"] / d["total"] if d["total"] > 0 else 0,
            "avg_review_time": sum(d["times"]) / len(d["times"]) if d["times"] else 0,
            "n_trials": d["total"],
        }
        for pid, d in participants.items()
    }

    return {
        "n_trials": n,
        "n_participants": len(participants),
        "human_accuracy": human_correct / n,
        "agent_accuracy": agent_correct / n,
        "agreement_rate": agreed / n,
        "correction_rate": modified / n,
        "avg_review_time_seconds": sum(times) / n if times else 0,
        "avg_sections_expanded": sum(sections) / n if sections else 0,
        "by_participant": by_participant,
    }


def save_experiment_results(trials: list[dict], output_path: Path) -> None:
    """Save experiment trials to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(trials, f, indent=2, default=str)


def load_experiment_results(input_path: Path) -> list[dict]:
    """Load previously saved experiment results."""
    if not input_path.exists():
        return []
    with open(input_path) as f:
        return json.load(f)
