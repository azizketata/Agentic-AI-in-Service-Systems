"""
Sepsis Cases Data Preprocessor

Transforms Sepsis Cases XES event log into the same schema
as the BPI 2012 preprocessor for cross-dataset analysis.

Outcomes mapped to clinical decisions:
  - discharged: patient released (Release A/B/C/D/E) without returning to ER
  - returned: patient returned to ER (bad outcome — treatment was insufficient)
  - ongoing: no clear endpoint in the data

Run: python -m src.data.sepsis_preprocessor
"""

from pathlib import Path

import pandas as pd
import yaml


def _load_settings() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_sepsis_xes(xes_path: str | Path | None = None) -> pd.DataFrame:
    """Load Sepsis Cases XES file."""
    import pm4py

    if xes_path is None:
        xes_path = Path(__file__).parent.parent.parent / "data" / "raw" / "Sepsis Cases - Event Log.xes"

    xes_path = Path(xes_path)
    if not xes_path.exists():
        raise FileNotFoundError(
            f"Sepsis XES file not found at {xes_path}. "
            "Download from https://data.4tu.nl/articles/dataset/Sepsis_Cases_-_Event_Log/12707639"
        )

    log = pm4py.read_xes(str(xes_path))
    return pm4py.convert_to_dataframe(log)


def _determine_sepsis_outcome(case_events: pd.DataFrame) -> str:
    """Determine patient outcome from activities."""
    activities = set(case_events["concept:name"].values)

    if "Return ER" in activities:
        return "returned"
    elif any(a.startswith("Release") for a in activities):
        return "discharged"
    else:
        return "ongoing"


def _assign_sepsis_risk_tier(
    age: float,
    infection_suspected: bool,
    sirs_criteria: bool,
    hypotension: bool,
    organ_dysfunction: bool,
) -> str:
    """Assign clinical risk tier based on patient attributes."""
    risk_score = 0
    if age >= 75:
        risk_score += 2
    elif age >= 60:
        risk_score += 1
    if infection_suspected:
        risk_score += 1
    if sirs_criteria:
        risk_score += 1
    if hypotension:
        risk_score += 2
    if organ_dysfunction:
        risk_score += 2

    if risk_score <= 2:
        return "low"
    elif risk_score <= 4:
        return "medium"
    else:
        return "high"


def preprocess_sepsis(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process raw Sepsis event log into case-level and event-level DataFrames."""
    case_col = "case:concept:name"
    activity_col = "concept:name"
    time_col = "time:timestamp"

    raw_df[time_col] = pd.to_datetime(raw_df[time_col], utc=True)

    cases = []
    for case_id, group in raw_df.groupby(case_col):
        group_sorted = group.sort_values(time_col)

        outcome = _determine_sepsis_outcome(group_sorted)

        # Extract case-level clinical attributes (first event has them)
        first = group_sorted.iloc[0]
        age = float(first.get("Age", 0)) if pd.notna(first.get("Age")) else 0
        infection = bool(first.get("InfectionSuspected", False))
        sirs = bool(first.get("SIRSCriteria2OrMore", False))
        hypotension = bool(first.get("Hypotensie", False))
        organ_dysf = bool(first.get("DisfuncOrg", False))

        risk_tier = _assign_sepsis_risk_tier(age, infection, sirs, hypotension, organ_dysf)

        start_time = group_sorted[time_col].min()
        end_time = group_sorted[time_col].max()
        duration_hours = (end_time - start_time).total_seconds() / 3600

        # Count key clinical activities
        has_antibiotics = (group_sorted[activity_col] == "IV Antibiotics").any()
        has_iv_liquid = (group_sorted[activity_col] == "IV Liquid").any()
        has_icu = (group_sorted[activity_col] == "Admission IC").any()
        lab_tests = group_sorted[activity_col].isin(["Leucocytes", "CRP", "LacticAcid"]).sum()

        cases.append({
            "case_id": str(case_id),
            "amount_requested": age,  # Reuse field name for compatibility (= patient age)
            "risk_tier": risk_tier,
            "outcome": outcome,
            "num_events": len(group_sorted),
            "num_offers": int(lab_tests),  # Reuse field name (= number of lab tests)
            "case_duration_hours": round(duration_hours, 2),
            "start_time": start_time,
            "end_time": end_time,
            # Sepsis-specific
            "age": age,
            "infection_suspected": infection,
            "sirs_criteria": sirs,
            "hypotension": hypotension,
            "organ_dysfunction": organ_dysf,
            "has_antibiotics": has_antibiotics,
            "has_iv_liquid": has_iv_liquid,
            "has_icu": has_icu,
            "lab_test_count": int(lab_tests),
        })

    cases_df = pd.DataFrame(cases)

    # Enrich events
    events_df = raw_df.copy()
    events_df = events_df.rename(columns={
        case_col: "case_id",
        activity_col: "activity",
        time_col: "timestamp",
    })

    return cases_df, events_df


def create_sepsis_sample(
    cases_df: pd.DataFrame, sample_size: int = 100
) -> pd.DataFrame:
    """Create a stratified sample balanced across outcomes and risk tiers."""
    cases_df = cases_df.copy()
    # Filter out 'ongoing' cases (no clear outcome)
    cases_df = cases_df[cases_df["outcome"] != "ongoing"]

    strata_col = cases_df["outcome"] + "_" + cases_df["risk_tier"]
    cases_df["_stratum"] = strata_col

    strata_counts = cases_df["_stratum"].value_counts()
    total = len(cases_df)

    sampled = []
    for stratum, count in strata_counts.items():
        n = max(2, round(sample_size * count / total))
        n = min(n, count)
        stratum_sample = cases_df[cases_df["_stratum"] == stratum].sample(n=n, random_state=42)
        sampled.append(stratum_sample)

    sample_df = pd.concat(sampled).drop(columns=["_stratum"])
    return sample_df.reset_index(drop=True)


def run_sepsis_preprocessing():
    """Main preprocessing pipeline for Sepsis dataset."""
    base_dir = Path(__file__).parent.parent.parent

    print("Loading Sepsis Cases XES file...")
    raw_df = load_sepsis_xes()

    print(f"Raw events: {len(raw_df):,}")
    print("Preprocessing...")
    cases_df, events_df = preprocess_sepsis(raw_df)
    print(f"Cases: {len(cases_df):,}")
    print(f"Outcome distribution:\n{cases_df['outcome'].value_counts().to_string()}")
    print(f"Risk tier distribution:\n{cases_df['risk_tier'].value_counts().to_string()}")

    # Save processed data
    processed_dir = base_dir / "data" / "processed_sepsis"
    processed_dir.mkdir(parents=True, exist_ok=True)

    cases_df.to_parquet(processed_dir / "cases.parquet", index=False)
    events_df.to_parquet(processed_dir / "events.parquet", index=False)
    print(f"Saved to {processed_dir}")

    # Create stratified sample
    sample_df = create_sepsis_sample(cases_df, 100)
    print(f"\nStratified sample: {len(sample_df)} cases")
    print(f"Sample outcome distribution:\n{sample_df['outcome'].value_counts().to_string()}")

    sample_dir = base_dir / "data" / "sample_sepsis"
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample_df.to_parquet(sample_dir / "sample_cases.parquet", index=False)

    # Save sample events
    sample_case_ids = set(sample_df["case_id"].values)
    sample_events = events_df[events_df["case_id"].isin(sample_case_ids)]
    sample_events.to_parquet(sample_dir / "sample_events.parquet", index=False)
    print(f"Sample events: {len(sample_events):,}")
    print(f"Saved sample to {sample_dir}")


if __name__ == "__main__":
    run_sepsis_preprocessing()
