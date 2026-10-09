"""
cicids2017/src/s17_train_ablated_base_models.py
------------------------------------------------
Sprint 5 — Part A, Step 1: Ablated Base Models Training

Trains DT, RF, SVM, IDSNet on the ABLATED feature set (K*=69 minus the 2
frozen shortcuts ["Destination Port", "Init_Win_bytes_backward"] → D_ablated=67).

INVARIANTS:
  - Shortcut SHA-256 verified against the frozen record before any training.
  - TRAIN is the only split used for fitting.
  - Ablated scaler is refitted on the 67-dim ablated space only.
  - Models saved to cicids2017/models/ablated/seed_<SEED>/
  - Hyperparameters are IDENTICAL to Sprint 3 canonical config.

Output:
  cicids2017/models/ablated/seed_<SEED>/{dt, rf, svm, nn}_model.pkl/.pt
  results/cicids2017_revision_v1/ablation/s17_ablated_training_metadata.json
"""

from __future__ import annotations

import gc
import hashlib
import json
import logging
import os
import pickle
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
OUT_DIR   = ROOT / "results" / "cicids2017_revision_v1" / "ablation"
MODEL_DIR = ROOT / "cicids2017" / "models" / "ablated"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT_DIR / "s17_ablated_training.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPLITS_DIR   = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR  = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
SEL_DIR      = ROOT / "results" / "cicids2017_revision_v1" / "feature_selection"
SHORTCUT_FILE = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_list_frozen.json"

H1_SEEDS = [42, 123, 2024]

# FROZEN SHORTCUT SHA-256 — must match exactly
EXPECTED_SHORTCUT_SHA256 = "5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2"

# Canonical hyperparameters (IDENTICAL to Sprint 3 s07)
DT_PARAMS  = {"criterion": "entropy", "max_depth": None, "min_samples_split": 2,
               "min_samples_leaf": 1, "class_weight": "balanced"}
RF_PARAMS  = {"n_estimators": 300, "criterion": "gini", "max_features": 0.3,
               "max_depth": None, "bootstrap": True, "class_weight": "balanced",
               "n_jobs": -1}
SVM_PARAMS = {"C": 0.1, "loss": "squared_hinge", "penalty": "l2", "dual": "auto",
              "class_weight": "balanced", "max_iter": 2000}

NN_LR       = 0.001
NN_WD       = 1e-5
NN_BATCH    = 256
NN_EPOCHS   = 18
NN_POS_WEIGHT = None  # Canonical: no loss-weight


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
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# ---------------------------------------------------------------------------
# IDSNet Architecture (IDENTICAL to s07)
# ---------------------------------------------------------------------------

class IDSNet(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        assert input_dim >= 1
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def train_idsnet(
    X_train: np.ndarray,
    y_train: np.ndarray,
    seed: int,
    device: torch.device,
) -> tuple[IDSNet, StandardScaler]:
    set_all_seeds(seed)
    D = X_train.shape[1]
    logger.info("IDSNet | seed=%d | D=%d | epochs=%d | batch=%d | device=%s",
                seed, D, NN_EPOCHS, NN_BATCH, device)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    X_t = torch.tensor(X_scaled, dtype=torch.float32)
    y_t = torch.tensor(y_train, dtype=torch.float32)
    dataset = TensorDataset(X_t, y_t)
    loader  = DataLoader(dataset, batch_size=NN_BATCH, shuffle=True,
                         worker_init_fn=lambda wid: np.random.seed(seed + wid))

    net = IDSNet(input_dim=D).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(net.parameters(), lr=NN_LR, weight_decay=NN_WD)

    t0 = time.perf_counter()
    for epoch in range(1, NN_EPOCHS + 1):
        net.train()
        total_loss = 0.0
        n_batches = 0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(net(xb), yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1
        if epoch % 6 == 0 or epoch == NN_EPOCHS:
            logger.info("  NN epoch %2d/%d | loss=%.6f", epoch, NN_EPOCHS, total_loss / max(n_batches, 1))
    logger.info("IDSNet training done | %.2fs", time.perf_counter() - t0)
    return net, scaler


def predict_idsnet(net, scaler, X, device, threshold=0.5):
    net.eval()
    X_sc = scaler.transform(X)
    X_t = torch.tensor(X_sc, dtype=torch.float32).to(device)
    with torch.no_grad():
        logits = net(X_t).cpu().numpy()
    proba = 1.0 / (1.0 + np.exp(-logits))
    pred  = (proba >= threshold).astype(np.int64)
    return pred, proba


def compute_metrics(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)
    fpr = fp / (fp + tn) if (fp + tn) > 0 else float("nan")
    return {
        "macro_f1":  float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall":    float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_attack": float(f1_score(y_true, y_pred, average="binary", zero_division=0)),
        "fpr":       float(fpr),
        "confusion_matrix": cm.tolist(),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 70)
    logger.info("SPRINT 5 — STEP 1: ABLATED BASE MODELS TRAINING (D=67)")
    logger.info("=" * 70)

    run_ts = datetime.now(timezone.utc)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    # --- Preflight: verify shortcut freeze SHA-256 ---
    if not SHORTCUT_FILE.exists():
        logger.error("shortcut_list_frozen.json NOT FOUND: %s", SHORTCUT_FILE)
        sys.exit(1)
    actual_sha = sha256_file(SHORTCUT_FILE)
    if actual_sha != EXPECTED_SHORTCUT_SHA256:
        logger.error("SHORTCUT SHA-256 MISMATCH!")
        logger.error("  Expected: %s", EXPECTED_SHORTCUT_SHA256)
        logger.error("  Actual:   %s", actual_sha)
        sys.exit(1)
    logger.info("Shortcut freeze SHA-256 verified: PASS (%s)", actual_sha[:16])

    # Load frozen shortcut set
    with open(SHORTCUT_FILE) as f:
        sc_json = json.load(f)
    frozen_shortcuts = sc_json["frozen_shortcut_set"]
    logger.info("Frozen shortcut set: %s", frozen_shortcuts)

    # --- Load frozen feature schema ---
    with open(PREPROC_DIR / "feature_schema.json") as f:
        schema = json.load(f)
    feature_list = schema["feature_list"]
    D = schema["D_final"]

    # --- Load selected features ---
    with open(SEL_DIR / "selected_features.json") as f:
        sel_json = json.load(f)
    selected_features = sel_json["selected_features"]
    k_star = sel_json["k_star"]

    # --- Build ablated feature list ---
    ablated_features = [f for f in selected_features if f not in frozen_shortcuts]
    D_ablated = len(ablated_features)
    removed_count = k_star - D_ablated

    assert removed_count == len(frozen_shortcuts), \
        f"Expected to remove {len(frozen_shortcuts)} shortcuts, removed {removed_count}"
    assert D_ablated == k_star - len(frozen_shortcuts), \
        f"D_ablated={D_ablated} != {k_star} - {len(frozen_shortcuts)}"

    logger.info("D_full=%d  K*=%d  shortcuts_removed=%d  D_ablated=%d",
                D, k_star, removed_count, D_ablated)
    logger.info("Removed shortcuts: %s", frozen_shortcuts)

    # --- Load TRAIN ---
    train_path = SPLITS_DIR / "train.csv"
    logger.info("Loading TRAIN: %s", train_path)
    train_df = pd.read_csv(train_path)

    X_full = train_df[feature_list].to_numpy(dtype=np.float64)
    if "label_clean" in train_df.columns:
        y_full = (train_df["label_clean"] != "BENIGN").astype(np.int64).to_numpy()
    else:
        y_full = (train_df["Label"] != "BENIGN").astype(np.int64).to_numpy()

    n_benign = int((y_full == 0).sum())
    n_attack = int((y_full == 1).sum())
    logger.info("TRAIN: rows=%d  benign=%d  attack=%d", len(y_full), n_benign, n_attack)

    # Build ablated feature matrix
    abl_idx = [feature_list.index(f) for f in ablated_features]
    X_abl   = X_full[:, abl_idx]
    logger.info("X_abl shape: %s", X_abl.shape)

    all_seed_results = {}
    model_artifacts  = {}

    for seed in H1_SEEDS:
        logger.info("-" * 60)
        logger.info("ABLATED TRAINING SEED %d", seed)
        logger.info("-" * 60)
        seed_dir = MODEL_DIR / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        seed_results = {}

        # --- Decision Tree ---
        dt_params = {**DT_PARAMS, "random_state": seed}
        t0 = time.perf_counter()
        dt = DecisionTreeClassifier(**dt_params)
        dt.fit(X_abl, y_full)
        dt_time = time.perf_counter() - t0
        logger.info("[DT] fitted | %.2fs", dt_time)
        dt_path = seed_dir / "dt_model.pkl"
        with open(dt_path, "wb") as f:
            pickle.dump(dt, f)
        dt_hash = sha256_file(dt_path)
        dt_train_m = compute_metrics(y_full, dt.predict(X_abl))
        seed_results["dt"] = {"params": dt_params, "train_metrics": dt_train_m,
                               "artifact": str(dt_path.relative_to(ROOT)), "sha256": dt_hash,
                               "train_time_s": dt_time}

        # --- Random Forest ---
        rf_params = {**RF_PARAMS, "random_state": seed}
        t0 = time.perf_counter()
        rf = RandomForestClassifier(**rf_params)
        rf.fit(X_abl, y_full)
        rf_time = time.perf_counter() - t0
        logger.info("[RF] fitted | %.2fs", rf_time)
        rf_path = seed_dir / "rf_model.pkl"
        with open(rf_path, "wb") as f:
            pickle.dump(rf, f)
        rf_hash = sha256_file(rf_path)
        rf_train_m = compute_metrics(y_full, rf.predict(X_abl))
        seed_results["rf"] = {"params": rf_params, "train_metrics": rf_train_m,
                               "artifact": str(rf_path.relative_to(ROOT)), "sha256": rf_hash,
                               "train_time_s": rf_time}

        # --- Linear SVM ---
        svm_params = {**SVM_PARAMS, "random_state": seed}
        svm_scaler = StandardScaler()
        X_svm = svm_scaler.fit_transform(X_abl)
        t0 = time.perf_counter()
        svm = LinearSVC(**svm_params)
        svm.fit(X_svm, y_full)
        svm_time = time.perf_counter() - t0
        logger.info("[SVM] fitted | %.2fs", svm_time)
        svm_path   = seed_dir / "svm_model.pkl"
        scaler_path = seed_dir / "svm_scaler.pkl"
        with open(svm_path, "wb") as f:
            pickle.dump(svm, f)
        with open(scaler_path, "wb") as f:
            pickle.dump(svm_scaler, f)
        svm_hash = sha256_file(svm_path)
        svm_train_m = compute_metrics(y_full, svm.predict(X_svm))
        seed_results["svm"] = {"params": svm_params, "train_metrics": svm_train_m,
                                "artifact": str(svm_path.relative_to(ROOT)), "sha256": svm_hash,
                                "train_time_s": svm_time}

        # --- IDSNet ---
        net, nn_scaler = train_idsnet(X_abl, y_full, seed=seed, device=device)
        nn_path    = seed_dir / "nn_model.pt"
        nn_sc_path = seed_dir / "nn_scaler.pkl"
        torch.save(net.state_dict(), nn_path)
        with open(nn_sc_path, "wb") as f:
            pickle.dump(nn_scaler, f)
        nn_hash = sha256_file(nn_path)
        y_nn_pred, _ = predict_idsnet(net, nn_scaler, X_abl, device)
        nn_train_m = compute_metrics(y_full, y_nn_pred)
        seed_results["nn"] = {
            "params": {"lr": NN_LR, "wd": NN_WD, "batch": NN_BATCH, "epochs": NN_EPOCHS,
                       "pos_weight": NN_POS_WEIGHT, "input_dim": D_ablated},
            "train_metrics": nn_train_m,
            "artifact": str(nn_path.relative_to(ROOT)), "sha256": nn_hash,
        }

        logger.info("[Seed %d] DT=%.4f  RF=%.4f  SVM=%.4f  NN=%.4f",
                    seed, dt_train_m["macro_f1"], rf_train_m["macro_f1"],
                    svm_train_m["macro_f1"], nn_train_m["macro_f1"])

        all_seed_results[str(seed)] = seed_results
        model_artifacts[str(seed)] = {
            "seed_dir":   str(seed_dir.relative_to(ROOT)),
            "dt_sha256":  dt_hash,
            "rf_sha256":  rf_hash,
            "svm_sha256": svm_hash,
            "nn_sha256":  nn_hash,
        }

        del net
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # --- Save metadata ---
    meta = {
        "creation_timestamp_utc": run_ts.isoformat(),
        "sprint": 5,
        "step": "s17_train_ablated_base_models",
        "seeds": H1_SEEDS,
        "k_star_original": k_star,
        "frozen_shortcuts": frozen_shortcuts,
        "shortcut_sha256_verified": EXPECTED_SHORTCUT_SHA256,
        "D_ablated": D_ablated,
        "ablated_features": ablated_features,
        "train_rows": len(y_full),
        "n_benign": n_benign,
        "n_attack": n_attack,
        "device": str(device),
        "canonical_hyperparameters": {
            "DT": DT_PARAMS, "RF": RF_PARAMS, "SVM": SVM_PARAMS,
            "IDSNet": {"lr": NN_LR, "wd": NN_WD, "batch": NN_BATCH,
                       "epochs": NN_EPOCHS, "pos_weight": NN_POS_WEIGHT,
                       "architecture": "Input(D_ablated)->Linear(128)->BN->ReLU->Dropout(0.3)"
                                       "->Linear(64)->BN->ReLU->Dropout(0.2)->Linear(1)"},
        },
        "per_seed_results": all_seed_results,
        "model_artifacts": model_artifacts,
    }
    meta_path = OUT_DIR / "s17_ablated_training_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info("Metadata saved: %s", meta_path)

    logger.info("=" * 70)
    logger.info("STEP 1 SUMMARY (ABLATED TRAIN IN-SAMPLE METRICS)")
    for seed in H1_SEEDS:
        r = all_seed_results[str(seed)]
        logger.info("  Seed %-5d | DT=%.4f  RF=%.4f  SVM=%.4f  NN=%.4f",
                    seed,
                    r["dt"]["train_metrics"]["macro_f1"],
                    r["rf"]["train_metrics"]["macro_f1"],
                    r["svm"]["train_metrics"]["macro_f1"],
                    r["nn"]["train_metrics"]["macro_f1"])
    logger.info("STEP 1 (ABLATED TRAINING): PASS")
    logger.info("=" * 70)
    print(f"\n[S17 COMPLETE] Ablated models trained (D={D_ablated}) for seeds {H1_SEEDS}")
    return meta


if __name__ == "__main__":
    main()
