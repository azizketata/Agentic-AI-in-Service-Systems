from pathlib import Path

import pandas as pd
import yaml


def _load_settings() -> dict:
    config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_bpi2012_xes(xes_path: str | Path | None = None) -> pd.DataFrame:
    """Load BPI Challenge 2012 XES file into a pandas DataFrame."""
    import pm4py

    if xes_path is None:
        settings = _load_settings()
        xes_path = Path(__file__).parent.parent.parent / settings["data"]["raw_xes"]

    xes_path = Path(xes_path)
    if not xes_path.exists():
        raise FileNotFoundError(
            f"BPI 2012 XES file not found at {xes_path}. "
            "Download it from https://data.4tu.nl/articles/dataset/BPI_Challenge_2012/12689204 "
            "and place it in prototype/data/raw/"
        )

    log = pm4py.read_xes(str(xes_path))
    df = pm4py.convert_to_dataframe(log)
    return df


def load_processed_cases(processed_dir: str | Path | None = None) -> pd.DataFrame:
    """Load preprocessed case-level data from parquet."""
    if processed_dir is None:
        settings = _load_settings()
        processed_dir = Path(__file__).parent.parent.parent / settings["data"]["processed_dir"]

    cases_path = Path(processed_dir) / "cases.parquet"
    if not cases_path.exists():
        raise FileNotFoundError(
            f"Processed cases not found at {cases_path}. "
            "Run: python -m src.data.preprocessor"
        )
    return pd.read_parquet(cases_path)


def load_sample_cases(sample_dir: str | Path | None = None) -> pd.DataFrame:
    """Load the stratified sample of ~100 cases."""
    if sample_dir is None:
        settings = _load_settings()
        sample_dir = Path(__file__).parent.parent.parent / settings["data"]["sample_dir"]

    sample_path = Path(sample_dir) / "sample_cases.parquet"
    if not sample_path.exists():
        raise FileNotFoundError(
            f"Sample cases not found at {sample_path}. "
            "Run: python -m src.data.preprocessor"
        )
    return pd.read_parquet(sample_path)
