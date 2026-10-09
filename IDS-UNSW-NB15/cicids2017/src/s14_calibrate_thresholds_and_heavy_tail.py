"""
cicids2017/src/s14_calibrate_thresholds_and_heavy_tail.py
---------------------------------------------------------
Sprint 4 — Step 4: Calibration & Heavy-Tail Diagnostic

Requirements:
- Input population: CALIBRATION ONLY (calibration.csv, N = 18,500 pure benign flows)
- Zero protected or unseen data may influence thresholds
- Evaluates:
    - Standard AE (seeds 42, 123, 2024)
    - Log1p AE (seeds 42, 123, 2024)
    - Isolation Forest (seeds 42, 123, 2024)
- Thresholds calculated on CALIBRATION:
    - mu + 3*sigma
    - p95, p99, p99.9
    - raw_mad_k3: median + 3 * raw_mad
    - scaled_mad_k3: median + 3 * 1.4826 * raw_mad
- Heavy-tail diagnostic:
    - sigma vs trimmed sigma (excluding top 1%)
    - p99
    - mu + 3*sigma
    - diagnostic ratio: (mu + 3*sigma) / p99
- Artifacts saved under:
    results/cicids2017_revision_v1/calibration/
    results/cicids2017_revision_v1/heavy_tail/
"""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from cicids2017.src.s12_train_autoencoder import Autoencoder, INPUT_DIM

# Setup Logging & Directories
CALIB_OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "calibration"
HT_OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "heavy_tail"
MODEL_DIR = ROOT / "cicids2017" / "models"
SPLITS_DIR = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
AE_DIR = ROOT / "results" / "cicids2017_revision_v1" / "autoencoder"

CALIB_OUT_DIR.mkdir(parents=True, exist_ok=True)
HT_OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(CALIB_OUT_DIR / "s14_calibration.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

SEEDS = [42, 123, 2024]
BATCH_SIZE = 256
SCALED_MAD_CONSTANT = 1.4826


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_threshold_suite(errors: np.ndarray) -> dict:
    n = len(errors)
    mean_val = float(np.mean(errors))
    std_val = float(np.std(errors, ddof=0))
    median_val = float(np.median(errors))
    mad_val = float(np.median(np.abs(errors - median_val)))
    scaled_mad_val = mad_val * SCALED_MAD_CONSTANT

    p95 = float(np.percentile(errors, 95.0))
    p99 = float(np.percentile(errors, 99.0))
    p999 = float(np.percentile(errors, 99.9))

    mu_plus_3sigma = mean_val + 3.0 * std_val
    raw_mad_k3 = median_val + 3.0 * mad_val
    scaled_mad_k3 = median_val + 3.0 * scaled_mad_val

    def make_entry(rule_name: str, thresh: float, formula: str):
        n_fp = int((errors > thresh).sum())
        fpr = float(n_fp / n)
        return {
            "rule": rule_name,
            "threshold_value": thresh,
            "formula": formula,
            "calibration_fps": n_fp,
            "calibration_fpr": fpr,
            "calibration_total": n,
        }

    thresholds = {
        "mu_plus_3sigma": make_entry("mu_plus_3sigma", mu_plus_3sigma, "mean + 3*std(ddof=0)"),
        "p95": make_entry("p95", p95, "percentile(95.0)"),
        "p99": make_entry("p99", p99, "percentile(99.0)"),
        "p999": make_entry("p999", p999, "percentile(99.9)"),
        "raw_mad_k3": make_entry("raw_mad_k3", raw_mad_k3, "median + 3*raw_mad"),
        "scaled_mad_k3": make_entry("scaled_mad_k3", scaled_mad_k3, "median + 3*1.4826*raw_mad"),
    }

    stats = {
        "mean": mean_val,
        "std": std_val,
        "median": median_val,
        "raw_mad": mad_val,
        "scaled_mad": scaled_mad_val,
        "min": float(np.min(errors)),
        "max": float(np.max(errors)),
        "p50": median_val,
        "p95": p95,
        "p99": p99,
        "p999": p999,
    }

    return {"stats": stats, "thresholds": thresholds}


def compute_heavy_tail_metrics(errors: np.ndarray, model_label: str, seed: int) -> dict:
    n = len(errors)
    mean_full = float(np.mean(errors))
    std_full = float(np.std(errors, ddof=0))
    p99 = float(np.percentile(errors, 99.0))
    mu3sigma = mean_full + 3.0 * std_full
    ratio = float(mu3sigma / p99) if p99 > 0 else float("nan")

    # Trim top 1% extreme reconstruction errors
    trimmed_cutoff = float(np.percentile(errors, 99.0))
    trimmed_errors = errors[errors <= trimmed_cutoff]
    std_trimmed = float(np.std(trimmed_errors, ddof=0))
    std_reduction_pct = float(100.0 * (std_full - std_trimmed) / std_full) if std_full > 0 else 0.0

    return {
        "model_label": model_label,
        "seed": seed,
        "n_samples": n,
        "mean": mean_full,
        "sigma_full": std_full,
        "sigma_trimmed_p99": std_trimmed,
        "sigma_reduction_pct": std_reduction_pct,
        "p99": p99,
        "mu_plus_3sigma": mu3sigma,
        "diagnostic_ratio": ratio,
        "heavy_tail_inflated": bool(ratio > 1.5),
    }


def main():
    logger.info("=" * 70)
    logger.info("SPRINT 4 — STEP 4: THRESHOLD CALIBRATION & HEAVY-TAIL DIAGNOSTIC")
    logger.info("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    # 1. Load feature schema
    with open(PREPROC_DIR / "feature_schema.json") as f:
        schema = json.load(f)
    feature_list = schema["feature_list"]
    D = len(feature_list)

    # 2. Load log1p qualifying features
    with open(PREPROC_DIR / "log1p_sensitivity_metadata.json") as f:
        log1p_meta = json.load(f)
    heavy_tail_features = log1p_meta["qualifying_features"]
    heavy_tail_indices = [feature_list.index(f) for f in heavy_tail_features]

    # 3. Load CALIBRATION data (pure benign)
    calib_path = SPLITS_DIR / "calibration.csv"
    logger.info("Loading CALIBRATION dataset: %s", calib_path)
    calib_df = pd.read_csv(calib_path)
    n_calib = len(calib_df)
    logger.info("CALIBRATION rows: %d (all pure benign)", n_calib)
    assert (calib_df["label_clean"] == "BENIGN").all(), "Non-benign rows found in CALIBRATION!"

    X_calib_raw = calib_df[feature_list].to_numpy(dtype=np.float64)

    # Load frozen scalers
    std_scaler_path = AE_DIR / "scaler_benign_train.pkl"
    with open(std_scaler_path, "rb") as f:
        std_scaler = pickle.load(f)

    log1p_scaler_path = AE_DIR / "scaler_benign_train_log1p.pkl"
    with open(log1p_scaler_path, "rb") as f:
        log1p_scaler = pickle.load(f)

    # Pre-transform CALIBRATION for Standard and Log1p
    X_calib_std = std_scaler.transform(X_calib_raw)

    X_calib_log1p_raw = X_calib_raw.copy()
    for idx in heavy_tail_indices:
        X_calib_log1p_raw[:, idx] = np.log1p(np.maximum(0.0, X_calib_log1p_raw[:, idx]))
    X_calib_log1p = log1p_scaler.transform(X_calib_log1p_raw)

    t_calib_std = torch.tensor(X_calib_std, dtype=torch.float32)
    t_calib_log1p = torch.tensor(X_calib_log1p, dtype=torch.float32)

    loader_std = DataLoader(TensorDataset(t_calib_std), batch_size=BATCH_SIZE, shuffle=False)
    loader_log1p = DataLoader(TensorDataset(t_calib_log1p), batch_size=BATCH_SIZE, shuffle=False)

    ae_calib_results = {"standard": {}, "log1p": {}}
    if_calib_results = {}
    heavy_tail_records = []

    # =======================================================================
    # 4. Standard AE Calibration & Heavy-Tail Diagnostic
    # =======================================================================
    logger.info("-" * 70)
    logger.info("Calibrating STANDARD Autoencoders across seeds %s...", SEEDS)
    logger.info("-" * 70)

    for seed in SEEDS:
        ckpt_path = MODEL_DIR / f"seed_{seed}" / "ae_standard_model.pt"
        model = Autoencoder(input_dim=D).to(device)
        model.load_state_dict(torch.load(ckpt_path, map_location=device))
        model.eval()

        re_list = []
        with torch.no_grad():
            for (xb,) in loader_std:
                xb = xb.to(device)
                re_b = model.reconstruction_error(xb)
                re_list.append(re_b.cpu().numpy())
        re_errors = np.concatenate(re_list, axis=0)

        suite = compute_threshold_suite(re_errors)
        ae_calib_results["standard"][str(seed)] = suite

        ht = compute_heavy_tail_metrics(re_errors, "AE_Standard", seed)
        heavy_tail_records.append(ht)

        logger.info("  [AE Standard Seed %d] mu=%.6f, sigma=%.6f, p99=%.6f, mu+3sigma=%.6f, Ratio=%.3f",
                    seed, suite["stats"]["mean"], suite["stats"]["std"],
                    suite["stats"]["p99"], suite["thresholds"]["mu_plus_3sigma"]["threshold_value"],
                    ht["diagnostic_ratio"])

    # =======================================================================
    # 5. Log1p Sensitivity AE Calibration & Heavy-Tail Diagnostic
    # =======================================================================
    logger.info("-" * 70)
    logger.info("Calibrating LOG1P SENSITIVITY Autoencoders across seeds %s...", SEEDS)
    logger.info("-" * 70)

    for seed in SEEDS:
        ckpt_path = MODEL_DIR / f"seed_{seed}" / "ae_log1p_model.pt"
        model = Autoencoder(input_dim=D).to(device)
        model.load_state_dict(torch.load(ckpt_path, map_location=device))
        model.eval()

        re_list = []
        with torch.no_grad():
            for (xb,) in loader_log1p:
                xb = xb.to(device)
                re_b = model.reconstruction_error(xb)
                re_list.append(re_b.cpu().numpy())
        re_errors = np.concatenate(re_list, axis=0)

        suite = compute_threshold_suite(re_errors)
        ae_calib_results["log1p"][str(seed)] = suite

        ht = compute_heavy_tail_metrics(re_errors, "AE_Log1p", seed)
        heavy_tail_records.append(ht)

        logger.info("  [AE Log1p Seed %d] mu=%.6f, sigma=%.6f, p99=%.6f, mu+3sigma=%.6f, Ratio=%.3f",
                    seed, suite["stats"]["mean"], suite["stats"]["std"],
                    suite["stats"]["p99"], suite["thresholds"]["mu_plus_3sigma"]["threshold_value"],
                    ht["diagnostic_ratio"])

    # =======================================================================
    # 6. Isolation Forest Calibration
    # =======================================================================
    logger.info("-" * 70)
    logger.info("Calibrating ISOLATION FOREST across seeds %s...", SEEDS)
    logger.info("-" * 70)

    for seed in SEEDS:
        ckpt_path = MODEL_DIR / f"seed_{seed}" / "if_model.joblib"
        if_model = joblib.load(ckpt_path)

        # Anomaly score = -score_samples(X) (higher = more anomalous)
        if_scores = -if_model.score_samples(X_calib_std)

        suite = compute_threshold_suite(if_scores)
        if_calib_results[str(seed)] = suite

        logger.info("  [IF Seed %d] mean=%.6f, sigma=%.6f, p99=%.6f, mu+3sigma=%.6f",
                    seed, suite["stats"]["mean"], suite["stats"]["std"],
                    suite["stats"]["p99"], suite["thresholds"]["mu_plus_3sigma"]["threshold_value"])

    # =======================================================================
    # 7. Save Calibration Results & Heavy-Tail Diagnostic
    # =======================================================================
    calib_summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 4,
        "calibration_rows": n_calib,
        "seeds": SEEDS,
        "scaled_mad_constant": SCALED_MAD_CONSTANT,
        "autoencoder_thresholds": ae_calib_results,
        "isolation_forest_thresholds": if_calib_results,
    }
    calib_path = CALIB_OUT_DIR / "calibration_thresholds.json"
    with open(calib_path, "w") as f:
        json.dump(calib_summary, f, indent=2)
    logger.info("Calibration thresholds saved: %s", calib_path)

    # Save heavy-tail diagnostic JSON and CSV
    ht_df = pd.DataFrame(heavy_tail_records)
    ht_csv_path = HT_OUT_DIR / "heavy_tail_diagnostic_table.csv"
    ht_df.to_csv(ht_csv_path, index=False)

    ht_summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "diagnostic_table": heavy_tail_records,
        "ratio_formula": "(mu + 3*sigma) / p99",
        "interpretation": "A ratio > 1.5 indicates extreme tail inflation of sigma, pushing the mu+3sigma threshold far past the 99th percentile and suppressing detection sensitivity.",
    }
    ht_json_path = HT_OUT_DIR / "heavy_tail_diagnostic.json"
    with open(ht_json_path, "w") as f:
        json.dump(ht_summary, f, indent=2)
    logger.info("Heavy-tail diagnostic saved: %s and %s", ht_json_path.name, ht_csv_path.name)

    logger.info("=" * 70)
    logger.info("STEP 4: PASS — THRESHOLD CALIBRATION & HEAVY-TAIL DIAGNOSTIC COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
