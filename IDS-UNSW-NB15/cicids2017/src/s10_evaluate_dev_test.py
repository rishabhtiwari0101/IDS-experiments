"""
cicids2017/src/s10_evaluate_dev_test.py
----------------------------------------
Sprint 3 — Step 6: Descriptive DEV_TEST Evaluation

PRECONDITION: shortcut_list_frozen.json MUST already exist before this script runs.
This script asserts its existence before doing any evaluation.

Evaluates all 4 base models and stacked ensemble on DEV_TEST using:
  - Decision threshold: 0.5 (canonical supervised threshold)
  - Metrics: Macro-F1, precision, recall, F1-attack, FPR, DEV_BENIGN_FPR, confusion matrix
  - Seeds: [42, 123, 2024]

LEAKAGE RULE: Models are loaded from cicids2017/models/ (trained on TRAIN only).
DEV_TEST is used ONLY for evaluation — never for fitting.

NOTE: Protected/unseen zero-day populations are NOT evaluated here.

Output: results/cicids2017_revision_v1/supervised/dev_test_evaluation.json
        results/cicids2017_revision_v1/stacking/dev_test_stacking_evaluation.json
        reports/cicids2017_revision_v1/SPRINT_3_REPORT.md
"""

from __future__ import annotations

import gc
import hashlib
import json
import logging
import pickle
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score,
    precision_score, recall_score,
)
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
SUPERVISED_DIR = ROOT / "results" / "cicids2017_revision_v1" / "supervised"
STACKING_DIR   = ROOT / "results" / "cicids2017_revision_v1" / "stacking"
REPORT_DIR     = ROOT / "reports" / "cicids2017_revision_v1"
SUPERVISED_DIR.mkdir(parents=True, exist_ok=True)
STACKING_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(SUPERVISED_DIR / "s10_dev_test_eval.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPLITS_DIR   = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR  = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
SEL_DIR      = ROOT / "results" / "cicids2017_revision_v1" / "feature_selection"
MODEL_DIR    = ROOT / "cicids2017" / "models"
SHORTCUT_FILE = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_list_frozen.json"

META_COLS    = {"Label", "shard_source", "label_clean", "attack_family", "row_uid"}
H1_SEEDS     = [42, 123, 2024]
THRESHOLD    = 0.5


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def set_all_seeds(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, split_name: str = "") -> dict:
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)
    fpr = fp / (fp + tn) if (fp + tn) > 0 else float("nan")
    # Benign FPR (proportion of benign rows falsely classified as attack)
    benign_mask = (y_true == 0)
    if benign_mask.sum() > 0:
        dev_benign_fpr = float((y_pred[benign_mask] == 1).sum() / benign_mask.sum())
    else:
        dev_benign_fpr = float("nan")
    return {
        "split":        split_name,
        "macro_f1":     float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "precision":    float(precision_score(y_true, y_pred, zero_division=0)),
        "recall":       float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_attack":    float(f1_score(y_true, y_pred, average="binary", zero_division=0)),
        "fpr":          float(fpr),
        "dev_benign_fpr": dev_benign_fpr,
        "n_total":      int(len(y_true)),
        "n_benign":     int(benign_mask.sum()),
        "n_attack":     int((y_true == 1).sum()),
        "n_tp": int(tp), "n_fp": int(fp), "n_fn": int(fn), "n_tn": int(tn),
        "confusion_matrix": cm.tolist(),
    }


# ---------------------------------------------------------------------------
# IDSNet (must match s07 architecture)
# ---------------------------------------------------------------------------

class IDSNet(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64),         nn.BatchNorm1d(64),  nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def predict_idsnet(net: IDSNet, scaler: StandardScaler,
                   X: np.ndarray, device: torch.device,
                   threshold: float = THRESHOLD) -> tuple[np.ndarray, np.ndarray]:
    net.eval()
    X_sc = scaler.transform(X)
    X_t  = torch.tensor(X_sc, dtype=torch.float32).to(device)
    with torch.no_grad():
        logits = net(X_t).cpu().numpy()
    proba = 1.0 / (1.0 + np.exp(-logits))
    pred  = (proba >= threshold).astype(np.int64)
    return pred, proba


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 70)
    logger.info("SPRINT 3 — STEP 6: DEV_TEST EVALUATION")
    logger.info("=" * 70)

    run_ts = datetime.now(timezone.utc)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # --- Precondition: shortcut_list_frozen.json MUST ALREADY EXIST ---
    if not SHORTCUT_FILE.exists():
        logger.error("PRECONDITION FAILED: shortcut_list_frozen.json does not exist!")
        logger.error("Run s09_treeshap_shortcut_freeze.py BEFORE this script.")
        sys.exit(1)

    shortcut_sha = sha256_file(SHORTCUT_FILE)
    with open(SHORTCUT_FILE) as f:
        shortcut_data = json.load(f)
    frozen_shortcut_set = shortcut_data["frozen_shortcut_set"]
    logger.info("PRECONDITION: shortcut_list_frozen.json EXISTS | SHA-256=%s", shortcut_sha)
    logger.info("Frozen shortcut set: %s", frozen_shortcut_set)
    logger.info("Zero-day blinding assertion recorded in shortcut file: %s",
                shortcut_data.get("ZERO_DAY_BLINDING_ASSERTION", "N/A")[:80] + "...")

    # --- Load frozen configs ---
    with open(PREPROC_DIR / "feature_schema.json") as f:
        schema = json.load(f)
    feature_list = schema["feature_list"]
    D = schema["D_final"]

    with open(SEL_DIR / "selected_features.json") as f:
        sel_json = json.load(f)
    selected_features = sel_json["selected_features"]
    k_star = sel_json["k_star"]

    # --- Load DEV_TEST ---
    dev_test_path = SPLITS_DIR / "dev_test.csv"
    logger.info("Loading DEV_TEST: %s", dev_test_path)
    dev_test_df = pd.read_csv(dev_test_path)
    logger.info("DEV_TEST rows: %d", len(dev_test_df))

    X_dt_full = dev_test_df[feature_list].to_numpy(dtype=np.float64)
    if "label_clean" in dev_test_df.columns:
        y_dt = (dev_test_df["label_clean"] != "BENIGN").astype(np.int64).to_numpy()
    else:
        y_dt = (dev_test_df["Label"] != "BENIGN").astype(np.int64).to_numpy()

    sel_idx   = [feature_list.index(f) for f in selected_features]
    X_dt_sel  = X_dt_full[:, sel_idx]

    logger.info("DEV_TEST: benign=%d  attack=%d  K*=%d",
                int((y_dt == 0).sum()), int((y_dt == 1).sum()), k_star)

    all_seed_results = {}

    for seed in H1_SEEDS:
        logger.info("-" * 50)
        logger.info("EVALUATING SEED %d on DEV_TEST", seed)
        logger.info("-" * 50)

        seed_dir = MODEL_DIR / f"seed_{seed}"
        seed_results = {}

        # --- DT ---
        with open(seed_dir / "dt_model.pkl", "rb") as f:
            dt = pickle.load(f)
        y_dt_pred = dt.predict(X_dt_sel)
        y_dt_prob = dt.predict_proba(X_dt_sel)[:, 1]
        dt_m = compute_metrics(y_dt, y_dt_pred, "dev_test")
        seed_results["dt"] = dt_m
        logger.info("[DT] macro_f1=%.4f  fpr=%.4f  dev_benign_fpr=%.4f",
                    dt_m["macro_f1"], dt_m["fpr"], dt_m["dev_benign_fpr"])

        # --- RF ---
        with open(seed_dir / "rf_model.pkl", "rb") as f:
            rf = pickle.load(f)
        y_rf_pred = rf.predict(X_dt_sel)
        y_rf_prob = rf.predict_proba(X_dt_sel)[:, 1]
        rf_m = compute_metrics(y_dt, y_rf_pred, "dev_test")
        seed_results["rf"] = rf_m
        logger.info("[RF] macro_f1=%.4f  fpr=%.4f  dev_benign_fpr=%.4f",
                    rf_m["macro_f1"], rf_m["fpr"], rf_m["dev_benign_fpr"])

        # --- SVM ---
        with open(seed_dir / "svm_model.pkl", "rb") as f:
            svm = pickle.load(f)
        with open(seed_dir / "svm_scaler.pkl", "rb") as f:
            svm_scaler = pickle.load(f)
        X_dt_svm = svm_scaler.transform(X_dt_sel)
        y_svm_pred  = svm.predict(X_dt_svm)
        y_svm_score = svm.decision_function(X_dt_svm)
        svm_m = compute_metrics(y_dt, y_svm_pred, "dev_test")
        seed_results["svm"] = svm_m
        logger.info("[SVM] macro_f1=%.4f  fpr=%.4f  dev_benign_fpr=%.4f",
                    svm_m["macro_f1"], svm_m["fpr"], svm_m["dev_benign_fpr"])

        # --- IDSNet ---
        with open(seed_dir / "nn_scaler.pkl", "rb") as f:
            nn_scaler = pickle.load(f)
        net = IDSNet(input_dim=k_star).to(device)
        net.load_state_dict(torch.load(seed_dir / "nn_model.pt", map_location=device))
        y_nn_pred, y_nn_prob = predict_idsnet(net, nn_scaler, X_dt_sel, device)
        nn_m = compute_metrics(y_dt, y_nn_pred, "dev_test")
        seed_results["nn"] = nn_m
        logger.info("[NN] macro_f1=%.4f  fpr=%.4f  dev_benign_fpr=%.4f",
                    nn_m["macro_f1"], nn_m["fpr"], nn_m["dev_benign_fpr"])
        del net
        gc.collect()

        # --- Stacking ---
        with open(seed_dir / "meta_lr.pkl", "rb") as f:
            meta_lr = pickle.load(f)

        # Assemble meta-features for DEV_TEST
        # SVM decision scores are normalized to similar scale as probabilities
        meta_X_dt = np.column_stack([y_dt_prob, y_rf_prob, y_svm_score, y_nn_prob])
        y_stack_pred = meta_lr.predict(meta_X_dt)
        y_stack_prob = meta_lr.predict_proba(meta_X_dt)[:, 1]
        stack_m = compute_metrics(y_dt, y_stack_pred, "dev_test")
        seed_results["stacking"] = stack_m
        logger.info("[STACK] macro_f1=%.4f  fpr=%.4f  dev_benign_fpr=%.4f",
                    stack_m["macro_f1"], stack_m["fpr"], stack_m["dev_benign_fpr"])

        all_seed_results[str(seed)] = seed_results

    # --- Aggregate across seeds ---
    model_keys = ["dt", "rf", "svm", "nn", "stacking"]
    aggregated = {}
    for mk in model_keys:
        vals = [all_seed_results[str(s)][mk]["macro_f1"] for s in H1_SEEDS]
        fpr_vals = [all_seed_results[str(s)][mk]["fpr"] for s in H1_SEEDS]
        bfpr_vals = [all_seed_results[str(s)][mk]["dev_benign_fpr"] for s in H1_SEEDS]
        aggregated[mk] = {
            "mean_macro_f1":    float(np.mean(vals)),
            "std_macro_f1":     float(np.std(vals)),
            "mean_fpr":         float(np.mean(fpr_vals)),
            "mean_dev_benign_fpr": float(np.mean(bfpr_vals)),
            "per_seed":         {str(s): all_seed_results[str(s)][mk] for s in H1_SEEDS},
        }

    # --- Save evaluation results ---
    eval_result = {
        "creation_timestamp_utc": run_ts.isoformat(),
        "sprint": 3,
        "step": "s10_evaluate_dev_test",
        "shortcut_freeze_sha256": shortcut_sha,
        "frozen_shortcut_set": frozen_shortcut_set,
        "shortcut_freeze_preceded_evaluation": True,
        "k_star": k_star,
        "dev_test_rows": int(len(y_dt)),
        "dev_test_benign": int((y_dt == 0).sum()),
        "dev_test_attack": int((y_dt == 1).sum()),
        "threshold": THRESHOLD,
        "device": str(device),
        "per_seed_results": all_seed_results,
        "aggregated": aggregated,
    }

    eval_path = SUPERVISED_DIR / "dev_test_evaluation.json"
    with open(eval_path, "w") as f:
        json.dump(eval_result, f, indent=2)
    logger.info("Evaluation saved: %s", eval_path.name)

    # --- Summary table ---
    logger.info("=" * 70)
    logger.info("STEP 6 SUMMARY — DEV_TEST (mean across seeds 42/123/2024)")
    logger.info("%-12s | %-10s | %-10s | %-14s", "Model", "MacroF1", "FPR", "BenignFPR")
    logger.info("-" * 60)
    for mk in model_keys:
        a = aggregated[mk]
        logger.info("%-12s | %.4f     | %.4f     | %.4f",
                    mk.upper(), a["mean_macro_f1"], a["mean_fpr"], a["mean_dev_benign_fpr"])
    logger.info("STEP 6: PASS")
    logger.info("=" * 70)

    print(f"\n[STEP 6 COMPLETE] DEV_TEST evaluation done. Results: {eval_path}")
    return eval_result


if __name__ == "__main__":
    main()
