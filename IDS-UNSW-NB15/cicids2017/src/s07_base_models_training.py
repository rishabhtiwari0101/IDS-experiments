"""
cicids2017/src/s07_base_models_training.py
-------------------------------------------
Sprint 3 — Step 3: Base Models Training (DT, RF, SVM, IDSNet)

Trains four base classifiers across seeds [42, 123, 2024] on the full TRAIN split.

Architecture:
  Decision Tree : criterion=entropy, class_weight=balanced
  Random Forest : n_estimators=300, criterion=gini, max_features=0.3, bootstrap=True, class_weight=balanced
  Linear SVM    : C=0.1, loss=squared_hinge, penalty=l2, class_weight=balanced, max_iter=2000
  IDSNet (MLP)  : Input(D)→Linear(128)→BN→ReLU→Dropout(0.3)→Linear(64)→BN→ReLU→Dropout(0.2)→Linear(1)
                  Adam, lr=0.001, weight_decay=1e-5, batch_size=256, epochs=18

INPUT DIMENSION: Dynamic — D = X_train.shape[1]. Never hardcoded.
POS_WEIGHT: pos_weight=None per the canonical CIC YAML (no loss-weight overriding).

LEAKAGE RULE: All models trained STRICTLY on TRAIN. DEV_TEST never touches fitting.

Output:
  cicids2017/models/seed_<SEED>/{dt, rf, svm, nn}_model.pkl/.pt
  results/cicids2017_revision_v1/supervised/training_metadata.json
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
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score,
    precision_score, recall_score,
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
OUT_DIR   = ROOT / "results" / "cicids2017_revision_v1" / "supervised"
MODEL_DIR = ROOT / "cicids2017" / "models"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT_DIR / "s07_training.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPLITS_DIR   = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR  = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
SEL_DIR      = ROOT / "results" / "cicids2017_revision_v1" / "feature_selection"
META_COLS    = {"Label", "shard_source", "label_clean", "attack_family", "row_uid"}
H1_SEEDS     = [42, 123, 2024]

# Canonical hyperparameters
DT_PARAMS    = {"criterion": "entropy", "max_depth": None, "min_samples_split": 2,
                "min_samples_leaf": 1, "class_weight": "balanced"}
RF_PARAMS    = {"n_estimators": 300, "criterion": "gini", "max_features": 0.3,
                "max_depth": None, "bootstrap": True, "class_weight": "balanced",
                "n_jobs": -1}
SVM_PARAMS   = {"C": 0.1, "loss": "squared_hinge", "penalty": "l2", "dual": "auto",
                "class_weight": "balanced", "max_iter": 2000}

# IDSNet training hyperparameters
NN_LR        = 0.001
NN_WD        = 1e-5
NN_BATCH     = 256
NN_EPOCHS    = 18
NN_POS_WEIGHT = None  # Canonical: no loss-weight per preregistered config (pos_weight=None)


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
# IDSNet Architecture (dynamic input dimension — NEVER hardcoded)
# ---------------------------------------------------------------------------

class IDSNet(nn.Module):
    """
    IDSNet: Input(D) → Linear(128) → BatchNorm → ReLU → Dropout(0.3)
                     → Linear(64)  → BatchNorm → ReLU → Dropout(0.2)
                     → Linear(1)

    Input dimension D is computed at runtime from X_train.shape[1].
    """

    def __init__(self, input_dim: int):
        super().__init__()
        assert input_dim >= 1, f"input_dim must be >= 1, got {input_dim}"
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
        return self.net(x).squeeze(-1)  # shape (batch,)


def train_idsnet(
    X_train: np.ndarray,
    y_train: np.ndarray,
    seed: int,
    device: torch.device,
) -> tuple[IDSNet, StandardScaler]:
    """Train IDSNet for NN_EPOCHS on TRAIN. Returns model and scaler."""
    set_all_seeds(seed)

    D = X_train.shape[1]
    logger.info("IDSNet | seed=%d | D=%d | epochs=%d | batch=%d | device=%s",
                seed, D, NN_EPOCHS, NN_BATCH, device)

    # Scale TRAIN only
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    X_t = torch.tensor(X_scaled, dtype=torch.float32)
    y_t = torch.tensor(y_train, dtype=torch.float32)

    dataset = TensorDataset(X_t, y_t)
    loader  = DataLoader(dataset, batch_size=NN_BATCH, shuffle=True,
                         worker_init_fn=lambda wid: np.random.seed(seed + wid))

    net = IDSNet(input_dim=D).to(device)

    # Loss: BCEWithLogitsLoss — pos_weight=None per canonical config
    if NN_POS_WEIGHT is not None:
        pw = torch.tensor([NN_POS_WEIGHT], dtype=torch.float32, device=device)
        criterion = nn.BCEWithLogitsLoss(pos_weight=pw)
    else:
        criterion = nn.BCEWithLogitsLoss()

    optimizer = torch.optim.Adam(net.parameters(), lr=NN_LR, weight_decay=NN_WD)

    t0 = time.perf_counter()
    epoch_losses = []
    for epoch in range(1, NN_EPOCHS + 1):
        net.train()
        total_loss = 0.0
        n_batches = 0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            logits = net(xb)
            loss   = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            n_batches  += 1
        avg_loss = total_loss / max(n_batches, 1)
        epoch_losses.append(avg_loss)
        if epoch % 6 == 0 or epoch == NN_EPOCHS:
            logger.info("  NN epoch %2d/%d | loss=%.6f", epoch, NN_EPOCHS, avg_loss)

    elapsed = time.perf_counter() - t0
    logger.info("IDSNet training done | %.2fs", elapsed)
    return net, scaler


def predict_idsnet(
    net: IDSNet,
    scaler: StandardScaler,
    X: np.ndarray,
    device: torch.device,
    threshold: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (y_pred_binary, y_proba)."""
    net.eval()
    X_sc = scaler.transform(X)
    X_t  = torch.tensor(X_sc, dtype=torch.float32).to(device)
    with torch.no_grad():
        logits = net(X_t).cpu().numpy()
    proba = 1.0 / (1.0 + np.exp(-logits))  # sigmoid
    pred  = (proba >= threshold).astype(np.int64)
    return pred, proba


# ---------------------------------------------------------------------------
# Metrics helper
# ---------------------------------------------------------------------------

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                    y_proba: np.ndarray | None = None) -> dict:
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
    logger.info("SPRINT 3 — STEP 3: BASE MODELS TRAINING")
    logger.info("=" * 70)

    run_ts = datetime.now(timezone.utc)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    # Load frozen feature schema
    with open(PREPROC_DIR / "feature_schema.json") as f:
        schema = json.load(f)
    feature_list = schema["feature_list"]
    D = schema["D_final"]

    # Load frozen selected features
    with open(SEL_DIR / "selected_features.json") as f:
        sel_json = json.load(f)
    selected_features = sel_json["selected_features"]
    k_star = sel_json["k_star"]
    sel_sha = sha256_file(SEL_DIR / "selected_features.json")

    logger.info("Frozen feature schema: D=%d", D)
    logger.info("Selected features: K*=%d  SHA-256=%s", k_star, sel_sha)

    # Load TRAIN
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
    logger.info("TRAIN: rows=%d  benign=%d  attack=%d  D=%d  K*=%d",
                len(y_full), n_benign, n_attack, D, k_star)

    # Build K*-selected feature matrix
    sel_idx = [feature_list.index(f) for f in selected_features]
    X_sel   = X_full[:, sel_idx]  # shape (n_train, K*)

    logger.info("X_sel shape: %s  (D=%d → K*=%d)", X_sel.shape, D, k_star)

    all_seed_results = {}
    model_artifacts  = {}

    for seed in H1_SEEDS:
        logger.info("-" * 60)
        logger.info("TRAINING SEED %d", seed)
        logger.info("-" * 60)
        seed_dir = MODEL_DIR / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)

        seed_results = {}

        # --- Decision Tree ---
        logger.info("[DT] seed=%d", seed)
        dt_params = {**DT_PARAMS, "random_state": seed}
        t0 = time.perf_counter()
        dt = DecisionTreeClassifier(**dt_params)
        dt.fit(X_sel, y_full)
        dt_time = time.perf_counter() - t0
        logger.info("[DT] fitted | %.2fs", dt_time)

        dt_path = seed_dir / "dt_model.pkl"
        with open(dt_path, "wb") as f:
            pickle.dump(dt, f)
        dt_hash = sha256_file(dt_path)

        y_dt_pred = dt.predict(X_sel)
        y_dt_prob = dt.predict_proba(X_sel)[:, 1]
        dt_train_m = compute_metrics(y_full, y_dt_pred)
        seed_results["dt"] = {"params": dt_params, "train_metrics": dt_train_m,
                               "artifact": str(dt_path.relative_to(ROOT)), "sha256": dt_hash,
                               "train_time_s": dt_time}

        # --- Random Forest ---
        logger.info("[RF] seed=%d", seed)
        rf_params = {**RF_PARAMS, "random_state": seed}
        t0 = time.perf_counter()
        rf = RandomForestClassifier(**rf_params)
        rf.fit(X_sel, y_full)
        rf_time = time.perf_counter() - t0
        logger.info("[RF] fitted | %.2fs", rf_time)

        rf_path = seed_dir / "rf_model.pkl"
        with open(rf_path, "wb") as f:
            pickle.dump(rf, f)
        rf_hash = sha256_file(rf_path)

        y_rf_pred = rf.predict(X_sel)
        y_rf_prob = rf.predict_proba(X_sel)[:, 1]
        rf_train_m = compute_metrics(y_full, y_rf_pred)
        seed_results["rf"] = {"params": rf_params, "train_metrics": rf_train_m,
                               "artifact": str(rf_path.relative_to(ROOT)), "sha256": rf_hash,
                               "train_time_s": rf_time}

        # --- Linear SVM ---
        logger.info("[SVM] seed=%d", seed)
        svm_params = {**SVM_PARAMS, "random_state": seed}
        svm_scaler = StandardScaler()
        X_svm = svm_scaler.fit_transform(X_sel)
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

        y_svm_pred  = svm.predict(X_svm)
        y_svm_score = svm.decision_function(X_svm)
        svm_train_m = compute_metrics(y_full, y_svm_pred)
        seed_results["svm"] = {"params": svm_params, "train_metrics": svm_train_m,
                                "artifact": str(svm_path.relative_to(ROOT)), "sha256": svm_hash,
                                "train_time_s": svm_time}

        # --- IDSNet ---
        logger.info("[NN] seed=%d", seed)
        net, nn_scaler = train_idsnet(X_sel, y_full, seed=seed, device=device)

        nn_path     = seed_dir / "nn_model.pt"
        nn_sc_path  = seed_dir / "nn_scaler.pkl"
        torch.save(net.state_dict(), nn_path)
        with open(nn_sc_path, "wb") as f:
            pickle.dump(nn_scaler, f)
        nn_hash = sha256_file(nn_path)

        y_nn_pred, y_nn_prob = predict_idsnet(net, nn_scaler, X_sel, device)
        nn_train_m = compute_metrics(y_full, y_nn_pred)
        seed_results["nn"] = {
            "params": {"lr": NN_LR, "wd": NN_WD, "batch": NN_BATCH, "epochs": NN_EPOCHS,
                       "pos_weight": NN_POS_WEIGHT, "input_dim": int(X_sel.shape[1])},
            "train_metrics": nn_train_m,
            "artifact": str(nn_path.relative_to(ROOT)), "sha256": nn_hash,
        }

        all_seed_results[str(seed)] = seed_results
        model_artifacts[str(seed)]  = {
            "seed_dir":   str(seed_dir.relative_to(ROOT)),
            "dt_sha256":  dt_hash,
            "rf_sha256":  rf_hash,
            "svm_sha256": svm_hash,
            "nn_sha256":  nn_hash,
        }
        logger.info("[Seed %d] DT macro_f1=%.4f  RF macro_f1=%.4f  SVM macro_f1=%.4f  NN macro_f1=%.4f",
                    seed, dt_train_m["macro_f1"], rf_train_m["macro_f1"],
                    svm_train_m["macro_f1"], nn_train_m["macro_f1"])

        # Memory cleanup
        del net
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # --- Save training metadata ---
    training_meta = {
        "creation_timestamp_utc": run_ts.isoformat(),
        "sprint": 3,
        "step": "s07_base_models_training",
        "seeds": H1_SEEDS,
        "k_star": k_star,
        "selected_features_sha256": sel_sha,
        "D_input": k_star,
        "train_rows": len(y_full),
        "n_benign": n_benign,
        "n_attack": n_attack,
        "device": str(device),
        "canonical_hyperparameters": {
            "DT": DT_PARAMS,
            "RF": RF_PARAMS,
            "SVM": SVM_PARAMS,
            "IDSNet": {
                "lr": NN_LR, "weight_decay": NN_WD, "batch_size": NN_BATCH,
                "epochs": NN_EPOCHS, "pos_weight": NN_POS_WEIGHT,
                "architecture": "Input(D)->Linear(128)->BN->ReLU->Dropout(0.3)->Linear(64)->BN->ReLU->Dropout(0.2)->Linear(1)",
                "input_dim": "DYNAMIC = X_train.shape[1]",
            },
        },
        "per_seed_results": all_seed_results,
        "model_artifacts": model_artifacts,
    }

    meta_path = OUT_DIR / "training_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(training_meta, f, indent=2)
    logger.info("Training metadata saved: %s", meta_path.name)

    # --- Summary ---
    logger.info("=" * 70)
    logger.info("STEP 3 SUMMARY (TRAIN IN-SAMPLE METRICS)")
    for seed in H1_SEEDS:
        r = all_seed_results[str(seed)]
        logger.info("  Seed %-5d | DT=%.4f  RF=%.4f  SVM=%.4f  NN=%.4f",
                    seed,
                    r["dt"]["train_metrics"]["macro_f1"],
                    r["rf"]["train_metrics"]["macro_f1"],
                    r["svm"]["train_metrics"]["macro_f1"],
                    r["nn"]["train_metrics"]["macro_f1"],
                    )
    logger.info("STEP 3: PASS")
    logger.info("=" * 70)

    print(f"\n[STEP 3 COMPLETE] Models trained for seeds {H1_SEEDS}")
    return training_meta


if __name__ == "__main__":
    main()
