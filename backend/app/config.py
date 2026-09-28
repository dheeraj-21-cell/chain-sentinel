import os
from pathlib import Path

# Resolve base data directory
_env_data_dir = os.getenv("DATA_DIR")
if _env_data_dir:
    DATA_DIR = Path(_env_data_dir)
elif Path("/data").is_dir():
    DATA_DIR = Path("/data")
else:
    DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
FEATURES_DATA_DIR = DATA_DIR / "features"
GROUND_TRUTH_DATA_DIR = DATA_DIR / "ground_truth"
EVIDENCE_DATA_DIR = DATA_DIR / "evidence"

# Resolve base models directory
_env_models_dir = os.getenv("MODELS_DIR")
if _env_models_dir:
    MODELS_DIR = Path(_env_models_dir)
elif Path("/models").is_dir():
    MODELS_DIR = Path("/models")
else:
    MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
FEATURES_DATA_DIR.mkdir(parents=True, exist_ok=True)
GROUND_TRUTH_DATA_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

