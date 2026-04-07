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
RESULTS_DIR = DATA_DIR / "results"
SAMPLE_DIR = DATA_DIR / "sample"
CONFIG_DIR = _prototype_root / "config"
