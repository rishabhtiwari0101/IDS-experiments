"""
cicids2017/src/s13_train_isolation_forest.py
---------------------------------------------
Sprint 4 — Step 3: Isolation Forest Baseline

Requirements:
- Algorithm: sklearn.ensemble.IsolationForest
- Parameters: n_estimators=200, contamination='auto', max_samples='auto', max_features=1.0
- Seeds: [42, 123, 2024]
- Training population: Benign TRAIN rows ONLY (label_clean == 'BENIGN', N = 44,800)
- Features: Exact 69 clean features, transformed by the frozen benign TRAIN scaler
- Model checkpoints saved to: cicids2017/models/seed_<SEED>/if_model.joblib
- Metadata saved to: results/cicids2017_revision_v1/isolation_forest/if_training_metadata.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# Setup Logging & Directories
OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "isolation_forest"
MODEL_DIR = ROOT / "cicids2017" / "models"
SPLITS_DIR = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
AE_DIR = ROOT / "results" / "cicids2017_revision_v1" / "autoencoder"

OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT_DIR / "s13_isolation_forest.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

SEEDS = [42, 123, 2024]
N_ESTIMATORS = 200
CONTAMINATION = "auto"
MAX_SAMPLES = "auto"
MAX_FEATURES = 1.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    logger.info("=" * 70)
    logger.info("SPRINT 4 — STEP 3: ISOLATION FOREST TRAINING")
    logger.info("=" * 70)

    # 1. Load feature schema
    with open(PREPROC_DIR / "feature_schema.json") as f:
        schema = json.load(f)
    feature_list = schema["feature_list"]
    D = len(feature_list)
    logger.info("Feature count: %d", D)

    # 2. Load frozen benign TRAIN scaler
    scaler_path = AE_DIR / "scaler_benign_train.pkl"
    if not scaler_path.exists():
        logger.error("Scaler not found: %s. Run s12_train_autoencoder.py first!", scaler_path)
        sys.exit(1)

    scaler_sha = sha256_file(scaler_path)
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)
    logger.info("Loaded benign TRAIN scaler: %s (SHA-256: %s)", scaler_path.name, scaler_sha)

    # 3. Load TRAIN dataset and filter to benign rows only
    train_path = SPLITS_DIR / "train.csv"
    train_df = pd.read_csv(train_path)
    benign_mask = (train_df["label_clean"] == "BENIGN")
    benign_train_df = train_df[benign_mask].copy()
    n_benign = len(benign_train_df)
    logger.info("Benign TRAIN rows: %d", n_benign)
    assert n_benign > 0, "No benign rows found in TRAIN!"

    X_benign_raw = benign_train_df[feature_list].to_numpy(dtype=np.float64)
    assert X_benign_raw.shape == (n_benign, D)

    # Scale using the benign TRAIN scaler
    X_benign_scaled = scaler.transform(X_benign_raw)

    ckpt_records = {}

    for seed in SEEDS:
        logger.info("-" * 50)
        logger.info("Training IsolationForest | seed=%d | n_estimators=%d...", seed, N_ESTIMATORS)
        logger.info("-" * 50)

        t0 = time.perf_counter()
        model = IsolationForest(
            n_estimators=N_ESTIMATORS,
            max_samples=MAX_SAMPLES,
            contamination=CONTAMINATION,
            max_features=MAX_FEATURES,
            random_state=seed,
            n_jobs=-1,
        )
        model.fit(X_benign_scaled)
        train_time = time.perf_counter() - t0

        # Save model
        seed_dir = MODEL_DIR / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        model_path = seed_dir / "if_model.joblib"
        joblib.dump(model, model_path)
        model_sha = sha256_file(model_path)

        logger.info("Seed %d complete | train_time=%.2fs | SHA-256: %s",
                    seed, train_time, model_sha)

        ckpt_records[str(seed)] = {
            "model_path": str(model_path.relative_to(ROOT)),
            "sha256": model_sha,
            "train_time_seconds": round(train_time, 3),
        }

    # Save overall metadata
    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 4,
        "step": "s13_train_isolation_forest",
        "training_population": "TRAIN benign only (label_clean == 'BENIGN')",
        "training_rows": n_benign,
        "feature_count": D,
        "parameters": {
            "n_estimators": N_ESTIMATORS,
            "max_samples": MAX_SAMPLES,
            "contamination": CONTAMINATION,
            "max_features": MAX_FEATURES,
            "seeds": SEEDS,
            "n_jobs": -1,
        },
        "scaler_path": str(scaler_path.relative_to(ROOT)),
        "scaler_sha256": scaler_sha,
        "checkpoints": ckpt_records,
    }

    meta_path = OUT_DIR / "isolation_forest_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    with open(OUT_DIR / "if_training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("=" * 70)
    logger.info("STEP 3: PASS — ISOLATION FOREST MODELS TRAINED ACROSS SEEDS %s", SEEDS)
    logger.info("Metadata saved: %s", meta_path)
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
