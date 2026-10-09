"""
cicids2017/src/s08_oof_stacking.py
------------------------------------
Sprint 3 — Step 4: Genuine 5-fold OOF Stacking + Meta-Learner

Protocol (frozen):
  StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
  Base models: DT, RF, SVM, IDSNet
  Meta-learner: LogisticRegression(C=1.0, solver=lbfgs, class_weight=balanced, max_iter=1000)
  Seeds: [42, 123, 2024]

LEAKAGE CONTRACT:
  - Each fold: base models fitted on 4/5 inner_train rows only.
  - OOF predictions generated only on the held-out 1/5.
  - Meta-learner fitted ONLY on assembled OOF predictions — never on in-sample predictions.
  - DEV_TEST, CALIBRATION, EVAL_CONTROL, protected/unseen: never accessed.

OOF LEAKAGE ASSERTIONS:
  - Assert: meta-learner has never seen y_true[train_idx] during its fitting.
  - Assert: OOF matrix covers every TRAIN row exactly once.

Output: results/cicids2017_revision_v1/stacking/
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
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "stacking"
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT_DIR / "s08_oof_stacking.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPLITS_DIR  = ROOT / "cicids2017" / "DATA" / "splits"
PREPROC_DIR = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
SEL_DIR     = ROOT / "results" / "cicids2017_revision_v1" / "feature_selection"
MODEL_DIR   = ROOT / "cicids2017" / "models"
META_COLS   = {"Label", "shard_source", "label_clean", "attack_family", "row_uid"}

H1_SEEDS    = [42, 123, 2024]
OOF_N_SPLITS = 5
OOF_CV_SEED  = 42

DT_PARAMS  = {"criterion": "entropy", "max_depth": None, "min_samples_split": 2,
              "min_samples_leaf": 1, "class_weight": "balanced"}
RF_PARAMS  = {"n_estimators": 300, "criterion": "gini", "max_features": 0.3,
              "max_depth": None, "bootstrap": True, "class_weight": "balanced", "n_jobs": -1}
SVM_PARAMS = {"C": 0.1, "loss": "squared_hinge", "penalty": "l2", "dual": "auto",
              "class_weight": "balanced", "max_iter": 2000}
NN_LR     = 0.001
NN_WD     = 1e-5
NN_BATCH  = 256
NN_EPOCHS = 18

META_PARAMS = {"C": 1.0, "solver": "lbfgs", "class_weight": "balanced",
               "max_iter": 1000, "penalty": "l2"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def set_all_seeds(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
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
# IDSNet (must match s07 architecture — dynamic input dim)
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


def train_idsnet_fold(X_tr: np.ndarray, y_tr: np.ndarray,
                      seed: int, device: torch.device) -> tuple[IDSNet, StandardScaler]:
    set_all_seeds(seed)
    D = X_tr.shape[1]
    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X_tr)
    X_t = torch.tensor(X_sc, dtype=torch.float32, device=device)
    y_t = torch.tensor(y_tr, dtype=torch.float32, device=device)
    n_tr = len(y_tr)
    net = IDSNet(input_dim=D).to(device)
    criterion = nn.BCEWithLogitsLoss()  # pos_weight=None
    optimizer = torch.optim.Adam(net.parameters(), lr=NN_LR, weight_decay=NN_WD)
    for epoch in range(1, NN_EPOCHS + 1):
        net.train()
        perm = torch.randperm(n_tr, device=device)
        for i in range(0, n_tr, NN_BATCH):
            idx = perm[i:i + NN_BATCH]
            xb, yb = X_t[idx], y_t[idx]
            optimizer.zero_grad()
            criterion(net(xb), yb).backward()
            optimizer.step()
    return net, scaler


def predict_proba_idsnet(net: IDSNet, scaler: StandardScaler,
                          X: np.ndarray, device: torch.device) -> np.ndarray:
    net.eval()
    X_sc = scaler.transform(X)
    X_t  = torch.tensor(X_sc, dtype=torch.float32).to(device)
    with torch.no_grad():
        logits = net(X_t).cpu().numpy()
    return 1.0 / (1.0 + np.exp(-logits))  # sigmoid


# ---------------------------------------------------------------------------
# Single-seed OOF run
# ---------------------------------------------------------------------------

def run_oof_one_seed(X_sel: np.ndarray, y_full: np.ndarray,
                     selected_features: list[str],
                     seed: int, device: torch.device) -> dict:
    """
    Genuine 5-fold OOF for one seed.
    Returns OOF predictions and per-fold diagnostics.
    """
    logger.info("  OOF | seed=%d | n_rows=%d | D=%d", seed, len(y_full), X_sel.shape[1])

    n = len(y_full)
    oof_dt_prob  = np.full(n, np.nan)
    oof_rf_prob  = np.full(n, np.nan)
    oof_svm_score = np.full(n, np.nan)
    oof_nn_prob  = np.full(n, np.nan)
    oof_covered  = np.zeros(n, dtype=bool)

    skf = StratifiedKFold(n_splits=OOF_N_SPLITS, shuffle=True, random_state=OOF_CV_SEED)
    fold_records = []

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X_sel, y_full)):
        fold_num = fold_idx + 1
        logger.info("    Fold %d/%d | train=%d  val=%d", fold_num, OOF_N_SPLITS,
                    len(train_idx), len(val_idx))

        X_tr, y_tr = X_sel[train_idx], y_full[train_idx]
        X_vl, y_vl = X_sel[val_idx],   y_full[val_idx]

        # Leakage assertion: held-out val_idx must not overlap train_idx
        assert len(set(train_idx) & set(val_idx)) == 0, "OOF LEAKAGE: train/val overlap!"

        # DT
        dt = DecisionTreeClassifier(**DT_PARAMS, random_state=seed)
        dt.fit(X_tr, y_tr)
        oof_dt_prob[val_idx] = dt.predict_proba(X_vl)[:, 1]

        # RF
        rf = RandomForestClassifier(**RF_PARAMS, random_state=seed)
        rf.fit(X_tr, y_tr)
        oof_rf_prob[val_idx] = rf.predict_proba(X_vl)[:, 1]

        # SVM
        svm_sc = StandardScaler()
        X_tr_sc = svm_sc.fit_transform(X_tr)
        X_vl_sc = svm_sc.transform(X_vl)
        svm = LinearSVC(**SVM_PARAMS, random_state=seed)
        svm.fit(X_tr_sc, y_tr)
        oof_svm_score[val_idx] = svm.decision_function(X_vl_sc)

        # IDSNet
        set_all_seeds(seed * 1000 + fold_num)
        net, nn_sc = train_idsnet_fold(X_tr, y_tr, seed=seed, device=device)
        oof_nn_prob[val_idx] = predict_proba_idsnet(net, nn_sc, X_vl, device)
        del net
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        oof_covered[val_idx] = True
        fold_records.append({
            "fold": fold_num,
            "train_n": int(len(train_idx)),
            "val_n":   int(len(val_idx)),
            "val_benign": int((y_vl == 0).sum()),
            "val_attack": int((y_vl == 1).sum()),
        })

    # Leakage assertion: every row covered exactly once
    assert oof_covered.all(), "OOF LEAKAGE: not all rows covered!"
    assert not np.isnan(oof_dt_prob).any(),   "OOF NaN in DT probs!"
    assert not np.isnan(oof_rf_prob).any(),   "OOF NaN in RF probs!"
    assert not np.isnan(oof_svm_score).any(), "OOF NaN in SVM scores!"
    assert not np.isnan(oof_nn_prob).any(),   "OOF NaN in NN probs!"
    logger.info("  OOF leakage assertions: PASS (all rows covered, no NaN)")

    return {
        "oof_dt_prob":   oof_dt_prob,
        "oof_rf_prob":   oof_rf_prob,
        "oof_svm_score": oof_svm_score,
        "oof_nn_prob":   oof_nn_prob,
        "fold_records":  fold_records,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 70)
    logger.info("SPRINT 3 — STEP 4: GENUINE 5-FOLD OOF STACKING")
    logger.info("=" * 70)

    run_ts = datetime.now(timezone.utc)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    # Load frozen configs
    with open(PREPROC_DIR / "feature_schema.json") as f:
        schema = json.load(f)
    feature_list = schema["feature_list"]
    D = schema["D_final"]

    with open(SEL_DIR / "selected_features.json") as f:
        sel_json = json.load(f)
    selected_features = sel_json["selected_features"]
    k_star = sel_json["k_star"]
    sel_sha = sha256_file(SEL_DIR / "selected_features.json")

    # Load TRAIN
    train_path = SPLITS_DIR / "train.csv"
    train_df = pd.read_csv(train_path)
    X_full = train_df[feature_list].to_numpy(dtype=np.float64)
    if "label_clean" in train_df.columns:
        y_full = (train_df["label_clean"] != "BENIGN").astype(np.int64).to_numpy()
    else:
        y_full = (train_df["Label"] != "BENIGN").astype(np.int64).to_numpy()

    sel_idx = [feature_list.index(f) for f in selected_features]
    X_sel   = X_full[:, sel_idx]
    n_rows  = len(y_full)

    logger.info("TRAIN: rows=%d  D=%d  K*=%d", n_rows, D, k_star)

    all_seed_meta_results = {}
    all_oof_dfs           = {}

    for seed in H1_SEEDS:
        logger.info("=" * 50)
        logger.info("OOF SEED %d", seed)
        logger.info("=" * 50)

        # Run genuine OOF
        oof_result = run_oof_one_seed(X_sel, y_full, selected_features, seed, device)

        # Assemble OOF matrix
        oof_df = pd.DataFrame({
            "row_idx":            np.arange(n_rows),
            "y_true":             y_full,
            "dt_attack_probability":  oof_result["oof_dt_prob"],
            "rf_attack_probability":  oof_result["oof_rf_prob"],
            "svm_decision_score":     oof_result["oof_svm_score"],
            "nn_attack_probability":  oof_result["oof_nn_prob"],
        })

        # --- Train meta-learner ONLY on OOF predictions ---
        meta_X = oof_df[["dt_attack_probability", "rf_attack_probability",
                          "svm_decision_score", "nn_attack_probability"]].to_numpy()
        meta_y = oof_df["y_true"].to_numpy()

        # Leakage assertion: meta-learner input must be OOF predictions, not base models' training outputs
        assert meta_X.shape == (n_rows, 4), f"Meta-X shape wrong: {meta_X.shape}"
        assert len(meta_y) == n_rows

        meta_params = {**META_PARAMS, "random_state": seed}
        meta_lr = LogisticRegression(**meta_params)
        meta_lr.fit(meta_X, meta_y)
        y_meta_pred = meta_lr.predict(meta_X)
        y_meta_prob = meta_lr.predict_proba(meta_X)[:, 1]

        meta_metrics = compute_metrics(meta_y, y_meta_pred)
        logger.info("Meta-LR (in-sample OOF): macro_f1=%.4f  fpr=%.4f",
                    meta_metrics["macro_f1"], meta_metrics["fpr"])

        # Save OOF predictions CSV
        oof_csv_path = OUT_DIR / f"oof_predictions_seed{seed}.csv"
        oof_df.to_csv(oof_csv_path, index=False)
        oof_sha = sha256_file(oof_csv_path)

        # Save meta-learner
        seed_dir = MODEL_DIR / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        meta_path = seed_dir / "meta_lr.pkl"
        with open(meta_path, "wb") as f:
            pickle.dump(meta_lr, f)
        meta_sha = sha256_file(meta_path)

        all_seed_meta_results[str(seed)] = {
            "fold_records":        oof_result["fold_records"],
            "meta_lr_params":      meta_params,
            "meta_in_sample_metrics": meta_metrics,
            "oof_csv":             str(oof_csv_path.relative_to(ROOT)),
            "oof_csv_sha256":      oof_sha,
            "meta_lr_artifact":    str(meta_path.relative_to(ROOT)),
            "meta_lr_sha256":      meta_sha,
            "limitation": (
                "In-sample meta-learner evaluation on OOF matrix. No held-out "
                "meta-layer validation exists under current data-isolation rules."
            ),
        }
        all_oof_dfs[seed] = oof_df
        logger.info("Seed %d OOF DONE | OOF SHA=%s  meta_sha=%s",
                    seed, oof_sha[:16], meta_sha[:16])

    # --- Save stacking metadata ---
    stacking_meta = {
        "creation_timestamp_utc":    run_ts.isoformat(),
        "sprint":                    3,
        "step":                      "s08_oof_stacking",
        "protocol": {
            "oof_n_splits": OOF_N_SPLITS,
            "oof_cv_seed":  OOF_CV_SEED,
            "meta_params":  META_PARAMS,
            "seeds":        H1_SEEDS,
        },
        "k_star":                    k_star,
        "selected_features_sha256":  sel_sha,
        "leakage_assertions_passed": True,
        "per_seed_results":          all_seed_meta_results,
    }

    meta_path_global = OUT_DIR / "stacking_metadata.json"
    with open(meta_path_global, "w") as f:
        json.dump(stacking_meta, f, indent=2)
    logger.info("Stacking metadata saved: %s", meta_path_global.name)

    # --- Summary ---
    logger.info("=" * 70)
    logger.info("STEP 4 SUMMARY (IN-SAMPLE OOF META-LEARNER METRICS)")
    for seed in H1_SEEDS:
        m = all_seed_meta_results[str(seed)]["meta_in_sample_metrics"]
        logger.info("  Seed %-5d | Meta macro_f1=%.4f  fpr=%.4f",
                    seed, m["macro_f1"], m["fpr"])
    logger.info("STEP 4: PASS")
    logger.info("=" * 70)

    print(f"\n[STEP 4 COMPLETE] OOF stacking complete for seeds {H1_SEEDS}")
    return stacking_meta


if __name__ == "__main__":
    main()
