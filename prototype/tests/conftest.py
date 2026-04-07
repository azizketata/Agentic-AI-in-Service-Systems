"""Shared test fixtures."""

import sys
from pathlib import Path

import pytest
import pandas as pd

# Add prototype root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_case() -> dict:
    """A representative loan application case for testing."""
    return {
        "case_id": "TEST_001",
        "amount_requested": 15000.0,
        "risk_tier": "medium",
        "outcome": "approved",
        "num_events": 20,
        "num_offers": 2,
        "case_duration_hours": 200.0,
    }


@pytest.fixture
def low_risk_case() -> dict:
    return {
        "case_id": "TEST_LOW",
        "amount_requested": 3000.0,
        "risk_tier": "low",
        "outcome": "approved",
        "num_events": 8,
        "num_offers": 1,
        "case_duration_hours": 50.0,
    }


@pytest.fixture
def high_risk_case() -> dict:
    return {
        "case_id": "TEST_HIGH",
        "amount_requested": 40000.0,
        "risk_tier": "high",
        "outcome": "declined",
        "num_events": 35,
        "num_offers": 3,
        "case_duration_hours": 800.0,
    }


@pytest.fixture
def over_limit_case() -> dict:
    return {
        "case_id": "TEST_OVER",
        "amount_requested": 60000.0,
        "risk_tier": "high",
        "outcome": "declined",
        "num_events": 5,
        "num_offers": 0,
        "case_duration_hours": 10.0,
    }


@pytest.fixture
def sample_cases_df(sample_case, low_risk_case, high_risk_case, over_limit_case) -> pd.DataFrame:
    """DataFrame of test cases covering all risk tiers."""
    return pd.DataFrame([sample_case, low_risk_case, high_risk_case, over_limit_case])


@pytest.fixture
def real_sample_df():
    """Load actual preprocessed sample if available."""
    sample_path = Path(__file__).parent.parent / "data" / "sample" / "sample_cases.parquet"
    if sample_path.exists():
        return pd.read_parquet(sample_path)
    pytest.skip("Sample data not available — run preprocessor first")
