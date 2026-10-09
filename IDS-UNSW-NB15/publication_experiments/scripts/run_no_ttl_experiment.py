"""
publication_experiments/scripts/run_no_ttl_experiment.py
--------------------------------------------------------
Stage B Execution Script: EXP_NO_TTL_V1 Controlled Feature-Ablation Experiment.

SCIENTIFIC OBJECTIVE:
    Determine how supervised IDS performance changes when the exact three
    TTL-related features ({sttl, ct_state_ttl, dttl}) are removed while
    all other canonical methodology is strictly preserved.

    Terminology: Controlled feature-ablation experiment (NOT definitive causal proof).

METHODOLOGICAL SPECIFICATION:
    - 72 features (canonical 75 minus {sttl, ct_state_ttl, dttl})
    - Seeds: [42, 123, 2024]
    - Base learners: DT, RF, LinearSVC, IDSNet (input_dim=72)
    - Stacking: 5-fold OOF (seed=7) -> LogisticRegression meta-learner (C=1.0)
    - Primary paired test: Canonical seed-42 <-> No-TTL seed-42 on row 'id'
    - Protected Backdoor: 583 flows evaluated strictly after models are frozen
    - Output isolation: All writes strictly under results/publication_experiments/EXP_NO_TTL_V1/
    - Frozen canonical artifacts: 0 bytes modified

Usage:
    python publication_experiments/scripts/run_no_ttl_experiment.py [--config CONFIG] [--seed SEED]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import yaml

# ── Resolve repository root ────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.models.base_models.neural_network import IDSNet
from src.preprocessing.preprocessing_pipeline import PreprocessingPipeline
from publication_experiments.utils.feature_adapter import (
    load_no_ttl_features,
    hash_feature_list,
    EXPECTED_NO_TTL_COUNT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("EXP_NO_TTL_V1")

# ── Frozen Hyperparameters (strictly identical to canonical Sprint 5/6) ───
OOF_SEED: int = 7
OOF_N_SPLITS: int = 5
NN_EPOCHS: int = 18
NN_BATCH_SIZE: int = 256
NN_LR: float = 0.001
NN_WEIGHT_DECAY: float = 0.0001
OOF_POS_WEIGHT: float = 44_800 / 117_595  # 0.38096857859602873

DT_CONFIG: dict[str, Any] = {
    "criterion": "entropy",
    "max_depth": None,
    "min_samples_leaf": 1,
    "class_weight": "balanced",
}

RF_CONFIG: dict[str, Any] = {
    "n_estimators": 300,
    "criterion": "gini",
    "max_depth": None,
    "min_samples_leaf": 1,
    "max_features": 0.3,
    "class_weight": "balanced",
    "n_jobs": -1,
}

SVM_CONFIG: dict[str, Any] = {
    "C": 0.1,
    "class_weight": "balanced",
    "max_iter": 5000,
}

META_CONFIG: dict[str, Any] = {
    "solver": "lbfgs",
    "C": 1.0,
    "class_weight": "balanced",
    "max_iter": 1000,
}

CANONICAL_HASHES = {
    "train": "4a259324e604f013287a5de5fe49c46bf19418d815b550c5d1a5820b569ac41c",
    "validation": "13caf21a076a33f50243f48f404b7e7525969f71d4b9d7c0f3768aef23589180",
    "dev_test": "04725e85732ab2fc6d9eaaa6105418b22b083b5c651067e7b0785464f414e508",
    "protected_backdoor": "6ffd23479b575e438ad90678268f40f674a663c2b9507aaf65089623397a9d91",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def set_all_seeds(seed: int) -> None:
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def train_idsnet_fold(
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    seed: int,
    device: torch.device,
    epochs: int = NN_EPOCHS,
) -> IDSNet:
    """Train 72-dimensional IDSNet for fixed epoch count."""
    set_all_seeds(seed)
    net = IDSNet(input_dim=72, hidden_sizes=[128, 64]).to(device)
    pos_weight = torch.tensor([OOF_POS_WEIGHT], dtype=torch.float32, device=device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.Adam(net.parameters(), lr=NN_LR, weight_decay=NN_WEIGHT_DECAY)

    ds = TensorDataset(torch.tensor(X_tr, dtype=torch.float32), torch.tensor(y_tr, dtype=torch.float32))
    loader = DataLoader(ds, batch_size=NN_BATCH_SIZE, shuffle=True)

    for epoch in range(1, epochs + 1):
        net.train()
        for bx, by in loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            logits = net(bx)
            loss = criterion(logits, by)
            loss.backward()
            optimizer.step()

    net.eval()
    return net


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Compute binary classification and diagnostic metrics."""
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))

    n = len(y_true)
    attack_prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    attack_rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    attack_f1 = float(2 * attack_prec * attack_rec / (attack_prec + attack_rec)) if (attack_prec + attack_rec) > 0 else 0.0

    benign_prec = float(tn / (tn + fn)) if (tn + fn) > 0 else 0.0
    benign_rec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    benign_f1 = float(2 * benign_prec * benign_rec / (benign_prec + benign_rec)) if (benign_prec + benign_rec) > 0 else 0.0

    macro_prec = float((attack_prec + benign_prec) / 2)
    macro_rec = float((attack_rec + benign_rec) / 2)
    macro_f1 = float((attack_f1 + benign_f1) / 2)

    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    bal_acc = float((attack_rec + (tn / (tn + fp) if (tn + fp) > 0 else 0.0)) / 2)
    acc = float((tp + tn) / n) if n > 0 else 0.0
    det_rate = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0

    return {
        "n": n,
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "detection_rate": det_rate,
        "benign_fpr": fpr,
        "accuracy": acc,
        "balanced_accuracy": bal_acc,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "macro_f1": macro_f1,
        "attack_precision": attack_prec,
        "attack_recall": attack_rec,
        "attack_f1": attack_f1,
        "benign_precision": benign_prec,
        "benign_recall": benign_rec,
        "benign_f1": benign_f1,
    }


def run_exact_mcnemar(y_true: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray) -> dict[str, Any]:
    """
    Construct 2x2 contingency table and run exact McNemar test.
    A = canonical correct / B = no-ttl correct
    """
    corr_a = (pred_a == y_true)
    corr_b = (pred_b == y_true)

    # Contingency table
    # Both correct
    n11 = int(np.sum(corr_a & corr_b))
    # A correct, B incorrect
    n10 = int(np.sum(corr_a & ~corr_b))
    # A incorrect, B correct
    n01 = int(np.sum(~corr_a & corr_b))
    # Both incorrect
    n00 = int(np.sum(~corr_a & ~corr_b))

    discordant = n10 + n01
    if discordant == 0:
        p_val = 1.0
        statistic = 0.0
    else:
        # Exact binomial test on discordant pairs
        binom = stats.binomtest(min(n10, n01), discordant, p=0.5, alternative="two-sided")
        p_val = float(binom.pvalue)
        statistic = float((abs(n10 - n01) - 1) ** 2 / discordant) if discordant > 0 else 0.0

    odds_ratio = float(n10 / n01) if n01 > 0 else (float("inf") if n10 > 0 else 1.0)

    return {
        "n_total": len(y_true),
        "contingency_table": {
            "canonical_corr_nottl_corr": n11,
            "canonical_corr_nottl_miss": n10,
            "canonical_miss_nottl_corr": n01,
            "canonical_miss_nottl_miss": n00,
        },
        "discordant_pairs": discordant,
        "statistic": statistic,
        "p_value": p_val,
        "odds_ratio": odds_ratio,
        "significant_at_05": p_val < 0.05,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Stage B EXP_NO_TTL_V1 Experiment")
    parser.add_argument(
        "--config",
        type=str,
        default="publication_experiments/configs/no_ttl.yaml",
        help="Path to experiment config",
    )
    parser.add_argument("--seed", type=int, default=None, help="Run single seed only")
    args = parser.parse_args()

    t_start = time.perf_counter()
    logger.info("=" * 70)
    logger.info("STAGE B: EXP_NO_TTL_V1 NO-TTL CONTROLLED FEATURE ABLATION")
    logger.info("=" * 70)

    # ── 1. Load config and verify output isolation ─────────────────────────
    config_path = REPO_ROOT / args.config
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    out_base = REPO_ROOT / cfg["output"]["base"]
    checkpoints_dir = REPO_ROOT / cfg["output"]["checkpoints"]
    scalers_dir = REPO_ROOT / cfg["output"]["scalers"]
    predictions_dir = REPO_ROOT / cfg["output"]["predictions"]
    metrics_dir = REPO_ROOT / cfg["output"]["metrics"]
    comparison_dir = REPO_ROOT / cfg["output"]["comparison"]
    logs_dir = REPO_ROOT / cfg["output"]["logs"]

    for d in [out_base, checkpoints_dir, scalers_dir, predictions_dir, metrics_dir, comparison_dir, logs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Programmatic write-safety guard
    for p in [checkpoints_dir, scalers_dir, predictions_dir, metrics_dir, comparison_dir, logs_dir]:
        assert str(p).replace("\\", "/").startswith(str(REPO_ROOT / "results/publication_experiments").replace("\\", "/")), (
            f"FATAL: Destination path {p} violates publication isolation!"
        )

    # ── 2. Pre-run Hash Verification ───────────────────────────────────────
    logger.info("Verifying canonical dataset hashes before running...")
    for split_key, expected_hash in CANONICAL_HASHES.items():
        actual = sha256_file(REPO_ROOT / cfg["data"][split_key])
        assert actual == expected_hash, f"Hash mismatch on {split_key}: {actual} != {expected_hash}"
    logger.info("All canonical datasets verified clean and frozen.")

    # ── 3. Load Feature Representation ─────────────────────────────────────
    features_manifest_path = REPO_ROOT / cfg["features"]["output_path"]
    no_ttl_features = load_no_ttl_features(features_manifest_path)
    assert len(no_ttl_features) == EXPECTED_NO_TTL_COUNT, f"Expected 72 features, got {len(no_ttl_features)}"
    for f in cfg["features"]["removed"]:
        assert f not in no_ttl_features, f"Forbidden feature {f} present in No-TTL feature set!"
    feature_hash = hash_feature_list(no_ttl_features)
    logger.info("Loaded 72 No-TTL features. Feature SHA-256: %s", feature_hash)

    # ── 4. Load Datasets and Fit Pipeline ───────────────────────────────────
    logger.info("Loading train.csv...")
    train_df = pd.read_csv(REPO_ROOT / cfg["data"]["train"])
    dev_test_df = pd.read_csv(REPO_ROOT / cfg["data"]["dev_test"])
    backdoor_df = pd.read_csv(REPO_ROOT / cfg["data"]["protected_backdoor"])

    logger.info("Fitting PreprocessingPipeline on TRAIN...")
    pipeline = PreprocessingPipeline(experiment_id="EXP_NO_TTL_V1")
    pipeline.fit(train_df)

    logger.info("Transforming TRAIN, DEV_TEST, and PROTECTED_BACKDOOR to unscaled feature space...")
    train_enc = pipeline.transform(train_df, view="unscaled", split_name="train")
    dev_enc = pipeline.transform(dev_test_df, view="unscaled", split_name="dev_test")
    backdoor_enc = pipeline.transform(backdoor_df, view="unscaled", split_name="protected_backdoor")

    # Extract 72 No-TTL columns
    train_feat_df = pd.DataFrame(train_enc.X, columns=train_enc.feature_names)
    dev_feat_df = pd.DataFrame(dev_enc.X, columns=dev_enc.feature_names)
    backdoor_feat_df = pd.DataFrame(backdoor_enc.X, columns=backdoor_enc.feature_names)

    X_train_unscaled = train_feat_df[no_ttl_features].values.astype(np.float32)
    X_dev_unscaled = dev_feat_df[no_ttl_features].values.astype(np.float32)
    X_backdoor_unscaled = backdoor_feat_df[no_ttl_features].values.astype(np.float32)

    y_train = train_df["label"].values.astype(np.int64)
    y_dev = dev_test_df["label"].values.astype(np.int64)
    y_backdoor = backdoor_df["label"].values.astype(np.int64)

    dev_ids = dev_test_df["id"].values
    backdoor_ids = backdoor_df["id"].values

    assert X_train_unscaled.shape == (162395, 72)
    assert X_dev_unscaled.shape == (81749, 72)
    assert X_backdoor_unscaled.shape == (583, 72)
    logger.info("Feature extraction verified: TRAIN (162395, 72), DEV (81749, 72), BACKDOOR (583, 72).")

    # ── 5. Fit 72-feature StandardScaler on TRAIN ─────────────────────────
    logger.info("Fitting fresh 72-feature StandardScaler on TRAIN...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_unscaled).astype(np.float32)
    X_dev_scaled = scaler.transform(X_dev_unscaled).astype(np.float32)
    X_backdoor_scaled = scaler.transform(X_backdoor_unscaled).astype(np.float32)

    scaler_path = scalers_dir / "supervised_scaler_72.joblib"
    joblib.dump(scaler, scaler_path)
    logger.info("Saved 72-feature scaler to %s (mean=%s...)", scaler_path, scaler.mean_[:3])

    # ── 6. OOF Folds Preparation ──────────────────────────────────────────
    skf = StratifiedKFold(n_splits=OOF_N_SPLITS, shuffle=True, random_state=OOF_SEED)
    folds = [(train_idx.copy(), oof_idx.copy()) for train_idx, oof_idx in skf.split(y_train, y_train)]
    logger.info("Created 5-fold StratifiedKFold (seed=%d, sizes=%s)", OOF_SEED, [len(o) for _, o in folds])

    seeds = [args.seed] if args.seed is not None else cfg["seeds"]
    logger.info("Executing seeds: %s", seeds)

    device_str = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_str)
    logger.info("Computing on device: %s (%s)", device_str, torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")

    seed_dev_results: dict[int, dict[str, Any]] = {}
    seed_backdoor_results: dict[int, dict[str, Any]] = {}
    seed_oof_results: dict[int, dict[str, Any]] = {}

    for seed in seeds:
        t_seed_start = time.perf_counter()
        logger.info("-" * 60)
        logger.info("PROCESSING SEED %d", seed)
        logger.info("-" * 60)

        seed_ckpt_dir = checkpoints_dir / f"seed_{seed}"
        seed_pred_dir = predictions_dir / f"seed_{seed}"
        seed_metric_dir = metrics_dir / f"seed_{seed}"
        for d in [seed_ckpt_dir, seed_pred_dir, seed_metric_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # ── 6.1 OOF Training Loop ─────────────────────────────────────────
        logger.info("Starting 5-fold OOF generation for seed %d...", seed)
        dt_oof = np.full(len(y_train), np.nan, dtype=np.float64)
        rf_oof = np.full(len(y_train), np.nan, dtype=np.float64)
        svm_oof = np.full(len(y_train), np.nan, dtype=np.float64)
        nn_oof = np.full(len(y_train), np.nan, dtype=np.float64)

        for fold_idx, (tr_idx, oof_idx) in enumerate(folds):
            logger.info("Seed %d | Fold %d/5 (tr=%d, oof=%d)", seed, fold_idx + 1, len(tr_idx), len(oof_idx))
            X_tr_u = X_train_unscaled[tr_idx]
            y_tr = y_train[tr_idx]
            X_tr_s = X_train_scaled[tr_idx]

            # DT
            dt = DecisionTreeClassifier(**DT_CONFIG, random_state=seed)
            dt.fit(X_tr_u, y_tr)
            dt_oof[oof_idx] = dt.predict_proba(X_train_unscaled[oof_idx])[:, 1]

            # RF
            rf = RandomForestClassifier(**RF_CONFIG, random_state=seed)
            rf.fit(X_tr_u, y_tr)
            rf_oof[oof_idx] = rf.predict_proba(X_train_unscaled[oof_idx])[:, 1]

            # SVM
            svm = LinearSVC(**SVM_CONFIG, random_state=seed)
            svm.fit(X_tr_s, y_tr)
            svm_oof[oof_idx] = svm.decision_function(X_train_scaled[oof_idx])

            # NN (18 epochs)
            net = train_idsnet_fold(X_tr_s, y_tr, seed, device, epochs=NN_EPOCHS)
            with torch.no_grad():
                logits = net(torch.tensor(X_train_scaled[oof_idx], dtype=torch.float32, device=device))
                nn_oof[oof_idx] = torch.sigmoid(logits).cpu().numpy().flatten()

        assert not np.isnan(dt_oof).any(), "NaN in DT OOF predictions!"
        assert not np.isnan(rf_oof).any(), "NaN in RF OOF predictions!"
        assert not np.isnan(svm_oof).any(), "NaN in SVM OOF predictions!"
        assert not np.isnan(nn_oof).any(), "NaN in NN OOF predictions!"

        oof_df = pd.DataFrame({
            "row_id": np.arange(len(y_train), dtype=np.int64),
            "dt_attack_probability": dt_oof,
            "rf_attack_probability": rf_oof,
            "svm_decision_score": svm_oof,
            "nn_attack_probability": nn_oof,
            "label": y_train,
        })
        oof_df.to_csv(seed_pred_dir / "oof_predictions.csv", index=False)

        # ── 6.2 Train Meta-Learner ────────────────────────────────────────
        meta_X_train = np.column_stack([dt_oof, rf_oof, svm_oof, nn_oof])
        meta_learner = LogisticRegression(**META_CONFIG, random_state=seed)
        meta_learner.fit(meta_X_train, y_train)

        joblib.dump(meta_learner, seed_ckpt_dir / "meta_learner.joblib")
        logger.info("Meta-learner trained for seed %d. Intercept: %.4f, Coefs: %s",
                    seed, float(meta_learner.intercept_[0]), meta_learner.coef_[0].tolist())

        # ── 6.3 Refit Base Models on Full TRAIN ───────────────────────────
        logger.info("Refitting final base models on complete TRAIN for seed %d...", seed)
        final_dt = DecisionTreeClassifier(**DT_CONFIG, random_state=seed)
        final_dt.fit(X_train_unscaled, y_train)
        joblib.dump(final_dt, seed_ckpt_dir / "dt_final.joblib")

        final_rf = RandomForestClassifier(**RF_CONFIG, random_state=seed)
        final_rf.fit(X_train_unscaled, y_train)
        joblib.dump(final_rf, seed_ckpt_dir / "rf_final.joblib")

        final_svm = LinearSVC(**SVM_CONFIG, random_state=seed)
        final_svm.fit(X_train_scaled, y_train)
        joblib.dump(final_svm, seed_ckpt_dir / "svm_final.joblib")

        final_nn = train_idsnet_fold(X_train_scaled, y_train, seed, device, epochs=NN_EPOCHS)
        torch.save(final_nn.state_dict(), seed_ckpt_dir / "nn_final.pt")

        # ── 6.4 Inference on DEV TEST ─────────────────────────────────────
        logger.info("Running DEV TEST inference for seed %d...", seed)
        dt_prob_dev = final_dt.predict_proba(X_dev_unscaled)[:, 1]
        dt_pred_dev = (dt_prob_dev >= 0.5).astype(int)

        rf_prob_dev = final_rf.predict_proba(X_dev_unscaled)[:, 1]
        rf_pred_dev = (rf_prob_dev >= 0.5).astype(int)

        svm_dec_dev = final_svm.decision_function(X_dev_scaled)
        svm_pred_dev = final_svm.predict(X_dev_scaled)

        with torch.no_grad():
            nn_logits_dev = final_nn(torch.tensor(X_dev_scaled, dtype=torch.float32, device=device))
            nn_prob_dev = torch.sigmoid(nn_logits_dev).cpu().numpy().flatten()
        nn_pred_dev = (nn_prob_dev >= 0.5).astype(int)

        meta_X_dev = np.column_stack([dt_prob_dev, rf_prob_dev, svm_dec_dev, nn_prob_dev])
        stack_prob_dev = meta_learner.predict_proba(meta_X_dev)[:, 1]
        stack_pred_dev = (stack_prob_dev >= 0.5).astype(int)

        dev_preds_df = pd.DataFrame({
            "id": dev_ids,
            "true_label": y_dev,
            "dt_pred": dt_pred_dev,
            "dt_prob": dt_prob_dev,
            "rf_pred": rf_pred_dev,
            "rf_prob": rf_prob_dev,
            "svm_pred": svm_pred_dev,
            "svm_score": svm_dec_dev,
            "nn_pred": nn_pred_dev,
            "nn_prob": nn_prob_dev,
            "stacking_pred": stack_pred_dev,
            "stacking_prob": stack_prob_dev,
        })
        dev_preds_df.to_csv(seed_pred_dir / "predictions_dev_test.csv", index=False)

        # Compute and record DEV TEST metrics
        dev_metrics = {
            "DT": compute_metrics(y_dev, dt_pred_dev),
            "RF": compute_metrics(y_dev, rf_pred_dev),
            "SVM": compute_metrics(y_dev, svm_pred_dev),
            "NN": compute_metrics(y_dev, nn_pred_dev),
            "Stacking": compute_metrics(y_dev, stack_pred_dev),
        }
        with open(seed_metric_dir / "metrics_dev_test.json", "w", encoding="utf-8") as f:
            json.dump(dev_metrics, f, indent=2)

        # ── 6.5 Inference on PROTECTED BACKDOOR ───────────────────────────
        logger.info("Running PROTECTED BACKDOOR inference for seed %d...", seed)
        dt_prob_bk = final_dt.predict_proba(X_backdoor_unscaled)[:, 1]
        dt_pred_bk = (dt_prob_bk >= 0.5).astype(int)

        rf_prob_bk = final_rf.predict_proba(X_backdoor_unscaled)[:, 1]
        rf_pred_bk = (rf_prob_bk >= 0.5).astype(int)

        svm_dec_bk = final_svm.decision_function(X_backdoor_scaled)
        svm_pred_bk = final_svm.predict(X_backdoor_scaled)

        with torch.no_grad():
            nn_logits_bk = final_nn(torch.tensor(X_backdoor_scaled, dtype=torch.float32, device=device))
            nn_prob_bk = torch.sigmoid(nn_logits_bk).cpu().numpy().flatten()
        nn_pred_bk = (nn_prob_bk >= 0.5).astype(int)

        meta_X_bk = np.column_stack([dt_prob_bk, rf_prob_bk, svm_dec_bk, nn_prob_bk])
        stack_prob_bk = meta_learner.predict_proba(meta_X_bk)[:, 1]
        stack_pred_bk = (stack_prob_bk >= 0.5).astype(int)

        bk_preds_df = pd.DataFrame({
            "id": backdoor_ids,
            "true_label": y_backdoor,
            "dt_pred": dt_pred_bk,
            "dt_prob": dt_prob_bk,
            "rf_pred": rf_pred_bk,
            "rf_prob": rf_prob_bk,
            "svm_pred": svm_pred_bk,
            "svm_score": svm_dec_bk,
            "nn_pred": nn_pred_bk,
            "nn_prob": nn_prob_bk,
            "stacking_pred": stack_pred_bk,
            "stacking_prob": stack_prob_bk,
        })
        bk_preds_df.to_csv(seed_pred_dir / "predictions_protected_backdoor.csv", index=False)

        bk_metrics = {
            "total_backdoor_rows": len(y_backdoor),
            "DT": {"detected": int(dt_pred_bk.sum()), "detection_rate": float(dt_pred_bk.mean()), "missed": int(len(y_backdoor) - dt_pred_bk.sum())},
            "RF": {"detected": int(rf_pred_bk.sum()), "detection_rate": float(rf_pred_bk.mean()), "missed": int(len(y_backdoor) - rf_pred_bk.sum())},
            "SVM": {"detected": int(svm_pred_bk.sum()), "detection_rate": float(svm_pred_bk.mean()), "missed": int(len(y_backdoor) - svm_pred_bk.sum())},
            "NN": {"detected": int(nn_pred_bk.sum()), "detection_rate": float(nn_pred_bk.mean()), "missed": int(len(y_backdoor) - nn_pred_bk.sum())},
            "Stacking": {"detected": int(stack_pred_bk.sum()), "detection_rate": float(stack_pred_bk.mean()), "missed": int(len(y_backdoor) - stack_pred_bk.sum())},
        }
        with open(seed_metric_dir / "metrics_protected_backdoor.json", "w", encoding="utf-8") as f:
            json.dump(bk_metrics, f, indent=2)

        seed_dev_results[seed] = dev_metrics
        seed_backdoor_results[seed] = bk_metrics
        logger.info(
            "Seed %d complete in %.1fs | Stacking Macro-F1=%.4f, Backdoor=%d/583 (%.2f%%)",
            seed, time.perf_counter() - t_seed_start,
            dev_metrics["Stacking"]["macro_f1"],
            bk_metrics["Stacking"]["detected"],
            bk_metrics["Stacking"]["detection_rate"] * 100,
        )

    # ── 7. Primary Paired Comparison (Canonical Seed 42 <-> No-TTL Seed 42) ──
    logger.info("=" * 70)
    logger.info("EXECUTING CANONICAL VS NO-TTL COMPARISON")
    logger.info("=" * 70)

    # Load canonical Backdoor predictions
    canon_bk_path = REPO_ROOT / "results/zero_day/EXP_ZERODAY_V1/predictions/zero_day_backdoor_predictions.csv"
    canon_bk_df = pd.read_csv(canon_bk_path)
    # Extract integer ID from 'UNSW_NB15_testing-set.csv:246'
    canon_bk_df["id"] = canon_bk_df["source_row_uid"].apply(lambda s: int(s.split(":")[-1]))

    # Load canonical DEV TEST predictions
    canon_dev_stack_path = REPO_ROOT / "results/final_reproducibility/EXP_FINAL_REPRO_V1/stacking/predictions_dev_test.csv"
    canon_dev_stack_df = pd.read_csv(canon_dev_stack_path)
    canon_dev_stack_df["id"] = canon_dev_stack_df["source_row_uid"].apply(lambda s: int(s.split(":")[-1]))

    canon_dev_base_path = REPO_ROOT / "results/final_reproducibility/EXP_FINAL_REPRO_V1/base_models/predictions_dev_test.csv"
    canon_dev_base_df = pd.read_csv(canon_dev_base_path)
    canon_dev_base_df["id"] = canon_dev_base_df["source_row_uid"].apply(lambda s: int(s.split(":")[-1]))

    # Compare for seed 42
    nottl_bk_42_df = pd.read_csv(predictions_dir / "seed_42/predictions_protected_backdoor.csv")
    nottl_dev_42_df = pd.read_csv(predictions_dir / "seed_42/predictions_dev_test.csv")

    # Merge on ID
    merged_bk = pd.merge(
        canon_bk_df[["id", "label", "stacking_prediction", "rf_prediction", "dt_prediction", "svm_prediction", "nn_prediction"]],
        nottl_bk_42_df[["id", "stacking_pred", "rf_pred", "dt_pred", "svm_pred", "nn_pred"]],
        on="id",
        suffixes=("_canonical", "_nottl"),
    )
    assert len(merged_bk) == 583, f"Backdoor ID merge failure: expected 583 rows, got {len(merged_bk)}"

    merged_dev = pd.merge(
        canon_dev_stack_df[["id", "true_label", "stack_pred_seed_42"]],
        nottl_dev_42_df[["id", "stacking_pred", "rf_pred", "dt_pred", "svm_pred", "nn_pred"]],
        on="id",
    )
    canon_base_sub = canon_dev_base_df[["id", "dt_pred", "rf_pred", "svm_pred", "nn_pred"]].copy()
    canon_base_sub.columns = ["id", "canon_dt_pred", "canon_rf_pred", "canon_svm_pred", "canon_nn_pred"]
    merged_dev = pd.merge(merged_dev, canon_base_sub, on="id")
    assert len(merged_dev) == 81749, f"DEV TEST ID merge failure: expected 81749 rows, got {len(merged_dev)}"

    # Paired McNemar Tests and Comparison Records
    comparison_records = []
    mcnemar_tests = {}

    model_specs = [
        ("Stacking (Seed 42)", "Stacking", "stacking_prediction", "stacking_pred", "stack_pred_seed_42", "stacking_pred"),
        ("Random Forest (Seed 42)", "RF", "rf_prediction", "rf_pred", "canon_rf_pred", "rf_pred"),
        ("Decision Tree (Seed 42)", "DT", "dt_prediction", "dt_pred", "canon_dt_pred", "dt_pred"),
        ("Linear SVC (Seed 42)", "SVM", "svm_prediction", "svm_pred", "canon_svm_pred", "svm_pred"),
        ("Neural Network (Seed 42)", "NN", "nn_prediction", "nn_pred", "canon_nn_pred", "nn_pred"),
    ]

    for display_name, key, bk_c_col, bk_nt_col, dev_c_col, dev_nt_col in model_specs:
        mcn_bk = run_exact_mcnemar(
            merged_bk["label"].values,
            merged_bk[bk_c_col].values,
            merged_bk[bk_nt_col].values,
        )
        mcn_dev = run_exact_mcnemar(
            merged_dev["true_label"].values,
            merged_dev[dev_c_col].values,
            merged_dev[dev_nt_col].values,
        )
        mcnemar_tests[f"{key}_backdoor"] = mcn_bk
        mcnemar_tests[f"{key}_dev_test"] = mcn_dev

        c_bk_det = int(merged_bk[bk_c_col].sum())
        nt_bk_det = int(merged_bk[bk_nt_col].sum())
        c_dev_f1 = f1_score(y_dev, merged_dev[dev_c_col].values, average="macro")
        nt_dev_f1 = seed_dev_results[42][key]["macro_f1"]
        c_dev_fpr = float(np.sum((y_dev == 0) & (merged_dev[dev_c_col].values == 1)) / 37000)
        nt_dev_fpr = seed_dev_results[42][key]["benign_fpr"]

        comparison_records.append({
            "model": display_name,
            "canonical_backdoor_detected": f"{c_bk_det}/583 ({c_bk_det/583:.2%})",
            "nottl_backdoor_detected": f"{nt_bk_det}/583 ({nt_bk_det/583:.2%})",
            "delta_backdoor_detected": nt_bk_det - c_bk_det,
            "delta_backdoor_rate": float((nt_bk_det - c_bk_det) / 583),
            "canonical_dev_macro_f1": c_dev_f1,
            "nottl_dev_macro_f1": nt_dev_f1,
            "delta_dev_macro_f1": nt_dev_f1 - c_dev_f1,
            "canonical_dev_fpr": c_dev_fpr,
            "nottl_dev_fpr": nt_dev_fpr,
            "delta_dev_fpr": nt_dev_fpr - c_dev_fpr,
            "mcnemar_backdoor_p_value": mcn_bk["p_value"],
            "mcnemar_dev_p_value": mcn_dev["p_value"],
        })

    comp_df = pd.DataFrame(comparison_records)
    comp_df.to_csv(comparison_dir / "canonical_vs_no_ttl_comparison.csv", index=False)

    comparison_payload = {
        "paired_seed_mapping": {"primary": "canonical_seed_42 <-> nottl_seed_42", "key": "id"},
        "mcnemar_tests": mcnemar_tests,
        "comparison_table": comparison_records,
    }
    with open(comparison_dir / "canonical_vs_no_ttl_comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison_payload, f, indent=2)

    # ── 8. Multi-Seed Aggregation ──────────────────────────────────────────
    multi_seed_summary = {}
    if len(seeds) > 1:
        for model in ["Stacking", "RF", "DT", "SVM", "NN"]:
            macro_f1s = [seed_dev_results[s][model]["macro_f1"] for s in seeds]
            bk_dets = [seed_backdoor_results[s][model]["detected"] for s in seeds]
            bk_rates = [seed_backdoor_results[s][model]["detection_rate"] for s in seeds]
            dev_fprs = [seed_dev_results[s][model]["benign_fpr"] for s in seeds]

            multi_seed_summary[model] = {
                "dev_macro_f1_mean": float(np.mean(macro_f1s)),
                "dev_macro_f1_std": float(np.std(macro_f1s)),
                "backdoor_detected_mean": float(np.mean(bk_dets)),
                "backdoor_detected_std": float(np.std(bk_dets)),
                "backdoor_rate_mean": float(np.mean(bk_rates)),
                "dev_fpr_mean": float(np.mean(dev_fprs)),
                "dev_fpr_std": float(np.std(dev_fprs)),
                "per_seed_macro_f1": {s: seed_dev_results[s][model]["macro_f1"] for s in seeds},
                "per_seed_backdoor_detected": {s: seed_backdoor_results[s][model]["detected"] for s in seeds},
            }
        with open(metrics_dir / "multi_seed_summary.json", "w", encoding="utf-8") as f:
            json.dump(multi_seed_summary, f, indent=2)

    # ── 9. Post-run Safety Verification ────────────────────────────────────
    logger.info("Performing post-run safety verification...")
    for split_key, expected_hash in CANONICAL_HASHES.items():
        actual = sha256_file(REPO_ROOT / cfg["data"][split_key])
        assert actual == expected_hash, f"FATAL: {split_key} was modified during run!"
    logger.info("Post-run safety verification: Canonical datasets remained 100% untouched.")

    # ── 10. Save config_used.yaml and metadata.json ───────────────────────
    with open(out_base / "config_used.yaml", "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, indent=2)

    metadata = {
        "experiment_id": "EXP_NO_TTL_V1",
        "parent_experiment": "EXP_MI_V1_1",
        "canonical_commit": "f694e19",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": time.perf_counter() - t_start,
        "feature_count": 72,
        "feature_hash": feature_hash,
        "removed_features": cfg["features"]["removed"],
        "seeds": seeds,
        "paired_comparison_mapping": "canonical_seed_42 <-> nottl_seed_42",
        "canonical_prediction_provenance": "zero_day_backdoor_predictions.csv (seed 42)",
        "output_paths": {
            "checkpoints": str(checkpoints_dir),
            "scalers": str(scalers_dir),
            "predictions": str(predictions_dir),
            "metrics": str(metrics_dir),
            "comparison": str(comparison_dir),
        },
        "multi_seed_summary": multi_seed_summary,
        "seed_42_headline_results": {
            "stacking_backdoor": seed_backdoor_results.get(42, {}).get("Stacking"),
            "stacking_dev_test": seed_dev_results.get(42, {}).get("Stacking"),
            "rf_backdoor": seed_backdoor_results.get(42, {}).get("RF"),
            "rf_dev_test": seed_dev_results.get(42, {}).get("RF"),
        },
        "scientific_interpretation": (
            "Controlled feature ablation: performance changes observed after removing {sttl, ct_state_ttl, dttl} "
            "provide empirical evidence regarding model dependence on TTL features. "
            "This is a controlled ablation experiment, not automatic causal proof."
        ),
        "status": "STAGE_B_COMPLETE",
    }
    with open(out_base / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("=" * 70)
    logger.info("STAGE B COMPLETE! Total runtime: %.1fs", time.perf_counter() - t_start)
    logger.info("Results saved under: %s", out_base)
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
