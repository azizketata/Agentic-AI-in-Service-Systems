"""
Centralized path setup for Streamlit pages.

Works both locally and on Streamlit Cloud by resolving
the prototype root from the app directory location.
"""

import sys
from pathlib import Path

# Resolve prototype root (parent of app/)
_app_dir = Path(__file__).parent.resolve()
_prototype_root = _app_dir.parent.resolve()

# Add both to sys.path if not already present
for p in [str(_prototype_root), str(_app_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

PROTOTYPE_ROOT = _prototype_root
APP_DIR = _app_dir
DATA_DIR = _prototype_root / "data"
CONFIG_DIR = _prototype_root / "config"

# Dataset configurations
DATASETS = {
    "BPI 2012 — Loan Applications": {
        "key": "bpi2012",
        "domain": "Financial Services",
        "results_dir": DATA_DIR / "results",
        "sample_dir": DATA_DIR / "sample",
        "outcomes": ["approved", "declined", "cancelled"],
        "description": "13,087 loan applications from a Dutch bank",
    },
    "Sepsis Cases — Healthcare": {
        "key": "sepsis",
        "domain": "Healthcare",
        "results_dir": DATA_DIR / "results_sepsis",
        "sample_dir": DATA_DIR / "sample_sepsis",
        "outcomes": ["discharged", "returned"],
        "description": "1,050 sepsis patient pathways from a hospital",
    },
}

# Default (backwards compatible)
RESULTS_DIR = DATA_DIR / "results"
SAMPLE_DIR = DATA_DIR / "sample"


def get_dataset_selector():
    """Render dataset selector in sidebar and return (results_dir, sample_dir, dataset_info)."""
    import streamlit as st

    st.sidebar.markdown("---")
    st.sidebar.subheader("Dataset")
    dataset_name = st.sidebar.selectbox(
        "Select dataset",
        options=list(DATASETS.keys()),
        key="dataset_selector",
    )
    ds = DATASETS[dataset_name]

    # Check if data exists
    sample_exists = (ds["sample_dir"] / "sample_cases.parquet").exists()
    results_exist = (ds["results_dir"] / "rule_based_results.json").exists()

    if not sample_exists:
        st.sidebar.warning(f"Sample data not found for {dataset_name}")
    if not results_exist:
        st.sidebar.warning(f"Pipeline results not found for {dataset_name}")

    st.sidebar.caption(ds["description"])

    return ds["results_dir"], ds["sample_dir"], ds
