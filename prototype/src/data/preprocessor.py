"""
BPI Challenge 2012 Data Preprocessor

Transforms raw XES event log into:
1. Case-level features (parquet) — amount, outcome, risk tier, duration, event counts
2. Event-level data (parquet) — all events with case enrichment
3. Stratified sample (~100 cases) — balanced across outcomes and risk tiers

Run: python -m src.data.preprocessor
"""

from pathlib import Path

import pandas as pd
import yaml

from src.data.loader import load_bpi2012_xes
from src.common.types import RiskTier, LoanOutcome


def _load_settings() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def _determine_outcome(case_events: pd.DataFrame) -> LoanOutcome:
    """Determine loan outcome from the final application-level events."""
    activities = set(case_events["concept:name"].values)

    if "A_APPROVED" in activities or "A_ACTIVATED" in activities or "A_REGISTERED" in activities:
        return LoanOutcome.APPROVED
    elif "A_DECLINED" in activities:
        return LoanOutcome.DECLINED
    else:
        return LoanOutcome.CANCELLED


def _assign_risk_tier(amount: float, settings: dict) -> RiskTier:
    """Assign risk tier based on loan amount thresholds."""
    tiers = settings["risk_tiers"]
    if amount <= tiers["low_max"]:
        return RiskTier.LOW
    elif amount <= tiers["medium_max"]:
        return RiskTier.MEDIUM
    else:
        return RiskTier.HIGH


def preprocess(raw_df: pd.DataFrame, settings: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process raw event log into case-level and event-level DataFrames.

    Returns:
        (cases_df, events_df)
    """
    case_col = "case:concept:name"
    activity_col = "concept:name"
    time_col = "time:timestamp"

    # Ensure timestamps are datetime
    raw_df[time_col] = pd.to_datetime(raw_df[time_col], utc=True)

    # Extract AMOUNT_REQ (loan amount) — it's a case-level attribute
    amount_col = "AMOUNT_REQ"
    if amount_col not in raw_df.columns:
        # Try alternative column name
        for col in raw_df.columns:
            if "amount" in col.lower():
                amount_col = col
                break

    cases = []
    for case_id, group in raw_df.groupby(case_col):
        group_sorted = group.sort_values(time_col)

        amount = group_sorted[amount_col].iloc[0] if amount_col in group_sorted.columns else 0.0
        amount = float(amount) if pd.notna(amount) else 0.0

        outcome = _determine_outcome(group_sorted)
        risk_tier = _assign_risk_tier(amount, settings)

        start_time = group_sorted[time_col].min()
        end_time = group_sorted[time_col].max()
        duration_hours = (end_time - start_time).total_seconds() / 3600

        num_offers = group_sorted[activity_col].str.startswith("O_").sum()

        cases.append({
            "case_id": str(case_id),
            "amount_requested": amount,
            "risk_tier": risk_tier.value,
            "outcome": outcome.value,
            "num_events": len(group_sorted),
            "num_offers": int(num_offers),
            "case_duration_hours": round(duration_hours, 2),
            "start_time": start_time,
            "end_time": end_time,
        })

    cases_df = pd.DataFrame(cases)

    # Enrich events with case-level info
    events_df = raw_df.copy()
    events_df = events_df.rename(columns={
        case_col: "case_id",
        activity_col: "activity",
        time_col: "timestamp",
    })
    if "org:resource" in events_df.columns:
        events_df = events_df.rename(columns={"org:resource": "resource"})
    if "lifecycle:transition" in events_df.columns:
        events_df = events_df.rename(columns={"lifecycle:transition": "lifecycle"})

    return cases_df, events_df


def create_stratified_sample(
    cases_df: pd.DataFrame, sample_size: int = 100
) -> pd.DataFrame:
    """
    Create a stratified sample balanced across outcomes and risk tiers.

    Stratifies by (outcome, risk_tier) and samples proportionally,
    ensuring at least 2 cases per stratum.
    """
    strata_col = cases_df["outcome"] + "_" + cases_df["risk_tier"]
    cases_df = cases_df.copy()
    cases_df["_stratum"] = strata_col

    strata_counts = cases_df["_stratum"].value_counts()
    total = len(cases_df)

    sampled = []
    for stratum, count in strata_counts.items():
        n = max(2, round(sample_size * count / total))
        n = min(n, count)
        stratum_sample = cases_df[cases_df["_stratum"] == stratum].sample(
            n=n, random_state=42
        )
        sampled.append(stratum_sample)

    sample_df = pd.concat(sampled).drop(columns=["_stratum"])
    return sample_df.reset_index(drop=True)


def run_preprocessing():
    """Main preprocessing pipeline."""
    settings = _load_settings()
    base_dir = Path(__file__).parent.parent.parent

    print("Loading BPI 2012 XES file...")
    raw_df = load_bpi2012_xes()

    print(f"Raw events: {len(raw_df):,}")
    print("Preprocessing...")
    cases_df, events_df = preprocess(raw_df, settings)
    print(f"Cases: {len(cases_df):,}")
    print(f"Outcome distribution:\n{cases_df['outcome'].value_counts().to_string()}")
    print(f"Risk tier distribution:\n{cases_df['risk_tier'].value_counts().to_string()}")

    # Save processed data
    processed_dir = base_dir / settings["data"]["processed_dir"]
    processed_dir.mkdir(parents=True, exist_ok=True)

    cases_df.to_parquet(processed_dir / "cases.parquet", index=False)
    events_df.to_parquet(processed_dir / "events.parquet", index=False)
    print(f"Saved to {processed_dir}")

    # Create stratified sample
    sample_size = settings["data"]["sample_size"]
    sample_df = create_stratified_sample(cases_df, sample_size)
    print(f"\nStratified sample: {len(sample_df)} cases")
    print(f"Sample outcome distribution:\n{sample_df['outcome'].value_counts().to_string()}")

    sample_dir = base_dir / settings["data"]["sample_dir"]
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample_df.to_parquet(sample_dir / "sample_cases.parquet", index=False)

    # Also save sample events for the agent to work with
    sample_case_ids = set(sample_df["case_id"].values)
    sample_events = events_df[events_df["case_id"].isin(sample_case_ids)]
    sample_events.to_parquet(sample_dir / "sample_events.parquet", index=False)
    print(f"Sample events: {len(sample_events):,}")
    print(f"Saved sample to {sample_dir}")


if __name__ == "__main__":
    run_preprocessing()
