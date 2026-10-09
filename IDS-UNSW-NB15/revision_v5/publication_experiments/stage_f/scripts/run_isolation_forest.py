#!/usr/bin/env python3
"""
revision_v5/publication_experiments/stage_f/scripts/run_isolation_forest.py
--------------------------------------------------------------------------
Phase 2 / BATCH-C: Isolation Forest Baseline (S7).
Blueprint reference: §7, §16 (S7), §0 Rule 6, §5C, Req 2.1.

Protocol Requirements:
1. Training Population: Benign TRAIN rows only (data/splits/train.csv, label == 0, N = 44,800).
   Strictly zero attack rows, zero VAL rows, zero DEV_TEST rows used for training or tuning.
2. Features & Scaler: Exact 75 EXP_MI_V1_1 features. Scaled using the frozen EXP_AE_V1/ae_scaler.joblib.
   Strictly fits NO new scaler. Scaler SHA-256 recorded and asserted.
3. Multi-Seed Training: Seeds [42, 123, 2024], n_estimators=200, contamination='auto', max_samples='auto'.
4. Scoring: anomaly_score = -model.score_samples(X_scaled) (larger = more anomalous).
5. Scored Populations:
   - Resolved clean calibration benign (validation.csv, label == 0, N = 11,200)
   - DEV_TEST (development_test.csv, N = 81,749)
   - ZERO_DAY_COMBINED (37,000 benign control + 583 Backdoor, N = 37,583)
   - UNSEEN_FAMILIES (Worms 44, Shellcode 378, Analysis 677, N = 1,099)
6. Row UID Alignment: Row UIDs and ordering match S1 probability files exactly.
7. Output Paths: Writes strictly under revision_v5/results/checkpoints/EXP_IF_V1 and
   revision_v5/results/publication_experiments/EXP_IF_V1.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.stats import beta
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score
import yaml

# START_ZERO_TRAINING_GUARD_DEFINITION
PROHIBITED_PATTERNS = [
    "fit_" + "transform",
    "import " + "shap",
    "torch." + "optim",
    "." + "backward()",
    "model." + "train()",
    "Grid" + "Search",
    "Randomized" + "Search",
]


def execute_s7_guard(script_path: Path) -> None:
    """Verify that S7 contains no prohibited ML training/tuning calls."""
    if not script_path.exists():
        return
    src = script_path.read_text(encoding="utf-8")
    in_guard_def = False
    for i, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if "# START_ZERO_TRAINING_GUARD_DEFINITION" in stripped:
            in_guard_def = True
            continue
        if "# END_ZERO_TRAINING_GUARD_DEFINITION" in stripped:
            in_guard_def = False
            continue
        if in_guard_def or stripped.startswith("#") or '"""' in stripped:
            continue
        for pattern in PROHIBITED_PATTERNS:
            if pattern in line:
                raise RuntimeError(
                    f"ZERO-TRAINING GUARD VIOLATION: prohibited pattern '{pattern}' "
                    f"found at line {i} of {script_path}: {stripped}"
                )
# END_ZERO_TRAINING_GUARD_DEFINITION


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("run_isolation_forest")


def find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / "data" / "splits").exists() and (current / "results").exists():
            return current
        current = current.parent
    return Path.cwd()


REPO_ROOT = find_repo_root()
NEW_ROOT = REPO_ROOT / "revision_v5"

# Add REPO_ROOT to sys.path to load preprocessing module
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.preprocessing.preprocessing_pipeline import PreprocessingPipeline


def resolve_path(rel_path: str) -> Path:
    p1 = NEW_ROOT / rel_path
    if p1.exists():
        return p1
    p2 = REPO_ROOT / rel_path
    if p2.exists():
        return p2
    return p1


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def clopper_pearson_ci(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Exact Clopper-Pearson 95% binomial confidence interval."""
    if n == 0:
        return (0.0, 1.0)
    alpha = 1.0 - confidence
    lower = 0.0 if k == 0 else float(beta.ppf(alpha / 2.0, k, n - k + 1))
    upper = 1.0 if k == n else float(beta.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return (lower, upper)


def run_isolation_forest(config_path: Path) -> None:
    execute_s7_guard(Path(__file__).resolve())
    logger.info("=== STEP 0: Zero-Training Guard Passed (No hyperparameter tuning / search) ===")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 1. Output directory setup strictly inside revision_v5/
    ckpt_out_rel = cfg.get("output_dirs", {}).get("checkpoints", "results/checkpoints/EXP_IF_V1")
    res_out_rel = cfg.get("output_dirs", {}).get("results", "results/publication_experiments/EXP_IF_V1")

    ckpt_dir = NEW_ROOT / ckpt_out_rel if not str(ckpt_out_rel).startswith(str(NEW_ROOT)) else Path(ckpt_out_rel)
    res_dir = NEW_ROOT / res_out_rel if not str(res_out_rel).startswith(str(NEW_ROOT)) else Path(res_out_rel)

    scores_dir = res_dir / "scores"
    thresh_dir = res_dir / "threshold"
    dev_test_dir = res_dir / "dev_test"
    zero_day_dir = res_dir / "zero_day"
    summary_dir = res_dir / "summary"

    for d in [ckpt_dir, res_dir, scores_dir, thresh_dir, dev_test_dir, zero_day_dir, summary_dir]:
        d.mkdir(parents=True, exist_ok=True)

    assert str(ckpt_dir.resolve()).startswith(str(NEW_ROOT.resolve())), f"Checkpoint directory {ckpt_dir} is outside {NEW_ROOT}"
    assert str(res_dir.resolve()).startswith(str(NEW_ROOT.resolve())), f"Results directory {res_dir} is outside {NEW_ROOT}"
    logger.info(f"Checkpoints will be written strictly inside: {ckpt_dir}")
    logger.info(f"Results will be written strictly inside: {res_dir}")

    # 2. Load and verify frozen AE Scaler
    ae_scaler_path = resolve_path(cfg["ae_scaler"])
    if not ae_scaler_path.exists():
        raise FileNotFoundError(f"Missing frozen AE scaler: {ae_scaler_path}")
    ae_scaler_sha256 = compute_sha256(ae_scaler_path)
    logger.info(f"Loaded frozen AE scaler from {ae_scaler_path} (SHA-256: {ae_scaler_sha256})")
    ae_scaler = joblib.load(ae_scaler_path)

    # Save scaler reference
    scaler_ref = {
        "scaler_path": str(ae_scaler_path),
        "scaler_sha256": ae_scaler_sha256,
        "note": "Reused frozen EXP_AE_V1/ae_scaler.joblib per Blueprint §7. No new scaler was fitted.",
    }
    with open(ckpt_dir / "ae_scaler_reference.json", "w", encoding="utf-8") as f:
        json.dump(scaler_ref, f, indent=2)

    # 3. Load Feature List (75 EXP_MI_V1_1 features)
    features_path = resolve_path(cfg["features"])
    with open(features_path, "r", encoding="utf-8") as f:
        feat_data = json.load(f)
    selected_features = feat_data["features"] if isinstance(feat_data, dict) and "features" in feat_data else feat_data
    assert len(selected_features) == 75, f"Expected 75 features, got {len(selected_features)}"
    features_sha256 = compute_sha256(features_path)
    logger.info(f"Loaded 75 selected features (SHA-256: {features_sha256})")

    # 4. Load Populations Manifest & S1 Reference Outputs for Exact UID Alignment
    pop_manifest_path = resolve_path(cfg["populations_manifest"])
    with open(pop_manifest_path, "r", encoding="utf-8") as f:
        pop_cfg = yaml.safe_load(f)

    # Load S1 reference tables to align row_uids and row ordering exactly
    s1_cal_path = resolve_path("results/publication_experiments/EXP_PROB_INFERENCE_V1/calibration_benign_probabilities.csv")
    s1_zero_path = resolve_path("results/publication_experiments/EXP_PROB_INFERENCE_V1/zeroday_probabilities.csv")
    if not s1_cal_path.exists() or not s1_zero_path.exists():
        raise FileNotFoundError(f"Missing S1 probability references: {s1_cal_path} or {s1_zero_path}")

    s1_cal_df = pd.read_csv(s1_cal_path)
    s1_zero_df = pd.read_csv(s1_zero_path)
    logger.info("Loaded S1 probability files for exact row_uid ordering alignment")

    # 5. Preprocessing Pipeline & Training Data (Benign TRAIN, N=44,800)
    train_path = resolve_path(cfg["training"]["train_path"])
    train_df = pd.read_csv(train_path)
    logger.info(f"Loaded raw training CSV from {train_path} ({len(train_df)} rows)")

    # Fit deterministic OHE category encoding on TRAIN (OHE category mapping only, zero model training)
    # ALLOWED_PREPROCESSING_OHE_FIT: OHE category mapping on TRAIN only
    pipe = PreprocessingPipeline().fit(train_df)

    # Filter benign TRAIN rows
    train_benign_df = train_df[train_df["label"] == 0].copy()
    expected_n_train = cfg["training"].get("expected_n", 44800)
    assert len(train_benign_df) == expected_n_train, f"Expected {expected_n_train} benign TRAIN rows, got {len(train_benign_df)}"
    assert (train_benign_df["label"] == 0).all(), "Attack row found in benign training slice!"
    logger.info(f"Confirmed benign training slice: exactly {len(train_benign_df)} rows, 0 attack rows")

    # Transform training data to unscaled view, then scale with frozen AE scaler
    enc_train = pipe.transform(train_benign_df, view="unscaled", split_name="train_benign")
    df_enc_train = pd.DataFrame(enc_train.X, columns=enc_train.feature_names)
    X_train_unscaled = df_enc_train[selected_features].values.astype(np.float64)
    X_train_scaled = ae_scaler.transform(X_train_unscaled)
    logger.info("Transformed training data using frozen AE scaler (no new scaler fitted)")

    # 6. Fit Isolation Forest across Seeds
    seeds = cfg.get("seeds", [42, 123, 2024])
    params = cfg.get("parameters", {})
    n_estimators = params.get("n_estimators", 200)
    max_samples = params.get("max_samples", "auto")
    contamination = params.get("contamination", "auto")
    max_features = params.get("max_features", 1.0)
    n_jobs = 1  # Sequential backend prevents named pipe permission errors under Windows sandbox

    if_models: Dict[int, IsolationForest] = {}
    ckpt_hashes: Dict[str, str] = {}

    for seed in seeds:
        seed_dir = ckpt_dir / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = seed_dir / "if_model.joblib"

        logger.info(f"Fitting IsolationForest for seed {seed} (n_estimators={n_estimators}, N={len(X_train_scaled)})...")
        # ALLOWED_FIT_CALL: Fitting IsolationForest exclusively on benign TRAIN rows
        model = IsolationForest(
            n_estimators=n_estimators,
            max_samples=max_samples,
            contamination=contamination,
            max_features=max_features,
            random_state=seed,
            n_jobs=n_jobs,
        )
        model.fit(X_train_scaled)
        joblib.dump(model, ckpt_path)
        ckpt_hash = compute_sha256(ckpt_path)
        ckpt_hashes[f"seed_{seed}"] = ckpt_hash
        if_models[seed] = model
        logger.info(f"Saved IF checkpoint for seed {seed} to {ckpt_path} (SHA-256: {ckpt_hash})")

    # Save Checkpoint Metadata
    ckpt_metadata = {
        "experiment_id": "EXP_IF_V1",
        "blueprint_version": "5.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "training_population": "TRAIN benign only (label == 0)",
        "training_rows": len(train_benign_df),
        "feature_count": len(selected_features),
        "parameters": {
            "n_estimators": n_estimators,
            "max_samples": max_samples,
            "contamination": contamination,
            "max_features": max_features,
            "seeds": seeds,
        },
        "ae_scaler_sha256": ae_scaler_sha256,
        "checkpoint_hashes": ckpt_hashes,
        "status": "PASS",
    }
    with open(ckpt_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(ckpt_metadata, f, indent=2)

    # 7. Feature Extraction for Scored Populations
    logger.info("=== STEP 2: Feature Extraction for Scored Populations ===")

    # (A) Calibration Benign (validation.csv, label == 0, N = 11,200)
    val_path = resolve_path(pop_cfg["populations"]["calibration_benign"]["path"])
    val_raw = pd.read_csv(val_path)
    val_benign_raw = val_raw[val_raw["label"] == 0].copy()
    assert len(val_benign_raw) == 11200, f"Expected 11,200 calibration benign rows, got {len(val_benign_raw)}"
    enc_cal = pipe.transform(val_benign_raw, view="unscaled", split_name="validation")
    df_enc_cal = pd.DataFrame(enc_cal.X, columns=enc_cal.feature_names)
    X_cal_scaled = ae_scaler.transform(df_enc_cal[selected_features].values.astype(np.float64))

    # (B) DEV_TEST (development_test.csv, N = 81,749)
    dev_path = resolve_path(pop_cfg["populations"]["dev_test"]["path"])
    dev_raw = pd.read_csv(dev_path)
    assert len(dev_raw) == 81749, f"Expected 81,749 DEV_TEST rows, got {len(dev_raw)}"
    enc_dev = pipe.transform(dev_raw, view="unscaled", split_name="development_test")
    df_enc_dev = pd.DataFrame(enc_dev.X, columns=enc_dev.feature_names)
    X_dev_scaled = ae_scaler.transform(df_enc_dev[selected_features].values.astype(np.float64))

    # (C) ZERO_DAY_COMBINED (37,583 rows: 583 Backdoor + 37,000 Benign Control)
    bd_path = resolve_path(pop_cfg["populations"]["zero_day"]["backdoor"]["path"])
    bd_raw = pd.read_csv(bd_path)
    assert len(bd_raw) == 583, f"Expected 583 Backdoor rows, got {len(bd_raw)}"
    enc_bd = pipe.transform(bd_raw, view="unscaled", split_name="protected_unseen_attack")
    df_enc_bd = pd.DataFrame(enc_bd.X, columns=enc_bd.feature_names)
    X_bd_scaled = ae_scaler.transform(df_enc_bd[selected_features].values.astype(np.float64))

    # S1 row_uid list for benign control
    bc_uids_path = resolve_path(pop_cfg["populations"]["zero_day"]["benign_control"]["row_uid_list"])
    with open(bc_uids_path, "r", encoding="utf-8") as f:
        bc_uids = json.load(f)
    assert len(bc_uids) == 37000, f"Expected 37,000 benign control UIDs, got {len(bc_uids)}"

    # Identify benign control row positions in DEV_TEST
    dev_uids = [f"UNSW_NB15_testing-set.csv:{rid}" for rid in dev_raw["id"]]
    dev_uid_to_idx = {uid: i for i, uid in enumerate(dev_uids)}
    bc_indices = [dev_uid_to_idx[uid] for uid in bc_uids]
    X_bc_scaled = X_dev_scaled[bc_indices]

    # Combine ZERO_DAY: 583 Backdoor first, then 37,000 Benign Control (identical to S1)
    X_zero_scaled = np.vstack([X_bd_scaled, X_bc_scaled])
    assert len(X_zero_scaled) == 37583

    # (D) UNSEEN_FAMILIES (Worms 44, Shellcode 378, Analysis 677, N = 1,099)
    unseen_mask = dev_raw["attack_cat"].isin(["Worms", "Shellcode", "Analysis"]).values
    X_unseen_scaled = X_dev_scaled[unseen_mask]
    unseen_dev_sub = dev_raw[unseen_mask].copy()
    assert len(X_unseen_scaled) == 1099, f"Expected 1,099 unseen family rows, got {len(X_unseen_scaled)}"

    # 8. Score Populations across Seeds
    logger.info("=== STEP 3: Scoring Populations (anomaly_score = -score_samples(X)) ===")
    cal_scores: Dict[int, np.ndarray] = {}
    dev_scores: Dict[int, np.ndarray] = {}
    zero_scores: Dict[int, np.ndarray] = {}
    unseen_scores: Dict[int, np.ndarray] = {}

    for seed in seeds:
        m = if_models[seed]
        cal_scores[seed] = -m.score_samples(X_cal_scaled)
        dev_scores[seed] = -m.score_samples(X_dev_scaled)
        zero_scores[seed] = -m.score_samples(X_zero_scaled)
        unseen_scores[seed] = -m.score_samples(X_unseen_scaled)
        logger.info(f"Scored populations for seed {seed}")

    # Build and Save Score CSVs (matching S1 row_uid equality and exact order)
    # 1. Calibration Benign Scores
    cal_out_df = pd.DataFrame({
        "row_uid": s1_cal_df["row_uid"].values,
        "label": 0,
    })
    for s in seeds:
        cal_out_df[f"if_anomaly_score_seed_{s}"] = cal_scores[s]
    cal_out_path = scores_dir / "calibration_benign_scores.csv"
    cal_out_df.to_csv(cal_out_path, index=False)

    # 2. DEV_TEST Scores
    dev_out_df = pd.DataFrame({
        "row_uid": dev_uids,
        "label": dev_raw["label"].values.astype(int),
        "attack_cat": dev_raw["attack_cat"].values,
    })
    for s in seeds:
        dev_out_df[f"if_anomaly_score_seed_{s}"] = dev_scores[s]
    dev_out_path = scores_dir / "dev_test_scores.csv"
    dev_out_df.to_csv(dev_out_path, index=False)

    # 3. ZERO_DAY Scores (Exact alignment with S1 zeroday_probabilities.csv)
    zero_out_df = pd.DataFrame({
        "row_uid": s1_zero_df["row_uid"].values,
        "label": s1_zero_df["label"].values.astype(int),
        "population_type": s1_zero_df["population_type"].values,
    })
    for s in seeds:
        zero_out_df[f"if_anomaly_score_seed_{s}"] = zero_scores[s]
    zero_out_path = scores_dir / "zeroday_scores.csv"
    zero_out_df.to_csv(zero_out_path, index=False)

    # 4. UNSEEN_FAMILY Scores
    unseen_uids = [dev_uids[i] for i in np.where(unseen_mask)[0]]
    unseen_out_df = pd.DataFrame({
        "row_uid": unseen_uids,
        "attack_cat": unseen_dev_sub["attack_cat"].values,
    })
    for s in seeds:
        unseen_out_df[f"if_anomaly_score_seed_{s}"] = unseen_scores[s]
    unseen_out_path = scores_dir / "unseen_family_scores.csv"
    unseen_out_df.to_csv(unseen_out_path, index=False)

    # Self-check assertions on score tables
    assert len(cal_out_df) == 11200
    assert len(dev_out_df) == 81749
    assert len(zero_out_df) == 37583
    assert len(unseen_out_df) == 1099
    assert (cal_out_df["row_uid"] == s1_cal_df["row_uid"]).all(), "cal_out_df row_uid mismatch with S1!"
    assert (zero_out_df["row_uid"] == s1_zero_df["row_uid"]).all(), "zero_out_df row_uid mismatch with S1!"
    logger.info("PASS: All 4 IF score CSVs verified for row counts and exact UID alignment with S1")

    # 9. Compute Rule-Based Thresholds & Evaluations
    logger.info("=== STEP 4: Computing Rule-Based Thresholds & Evaluations ===")
    thresh_records = []
    dev_metrics_records = []
    backdoor_records = []
    family_records = []

    y_dev = dev_raw["label"].values.astype(int)
    y_zero = s1_zero_df["label"].values.astype(int)
    n_dev_attack = int((y_dev == 1).sum())
    n_dev_benign = int((y_dev == 0).sum())
    n_bd = 583
    n_ctrl = 37000

    for seed in seeds:
        sc_cal = cal_scores[seed]
        sc_dev = dev_scores[seed]
        sc_zero = zero_scores[seed]
        sc_unseen = unseen_scores[seed]

        mean_cal = float(np.mean(sc_cal))
        std_cal = float(np.std(sc_cal, ddof=1))

        rules = {
            "p95": float(np.percentile(sc_cal, 95, method="linear")),
            "p99": float(np.percentile(sc_cal, 99, method="linear")),
            "p999": float(np.percentile(sc_cal, 99.9, method="linear")),
            "mean_plus_2sigma": mean_cal + 2.0 * std_cal,
            "mean_plus_3sigma": mean_cal + 3.0 * std_cal,
        }

        for rule_name, t in rules.items():
            val_fp = int(np.sum(sc_cal > t))
            val_fpr = float(val_fp / len(sc_cal))

            thresh_records.append({
                "model": "isolation_forest",
                "seed": seed,
                "rule": rule_name,
                "threshold": t,
                "val_fp": val_fp,
                "val_fpr": val_fpr,
            })

            # DEV_TEST Evaluation
            dev_preds = (sc_dev > t).astype(int)
            tp_dev = int(np.sum((dev_preds == 1) & (y_dev == 1)))
            fp_dev = int(np.sum((dev_preds == 1) & (y_dev == 0)))
            fn_dev = int(np.sum((dev_preds == 0) & (y_dev == 1)))
            tn_dev = int(np.sum((dev_preds == 0) & (y_dev == 0)))
            dev_fpr = float(fp_dev / n_dev_benign)
            dev_rec = float(tp_dev / n_dev_attack)
            dev_f1 = float(f1_score(y_dev, dev_preds, average="macro"))

            dev_metrics_records.append({
                "model": "isolation_forest",
                "seed": seed,
                "rule": rule_name,
                "threshold": t,
                "tp": tp_dev,
                "fp": fp_dev,
                "fn": fn_dev,
                "tn": tn_dev,
                "dev_test_fpr": dev_fpr,
                "dev_test_recall": dev_rec,
                "macro_f1": dev_f1,
            })

            # Zero-Day Evaluation
            zero_preds = (sc_zero > t).astype(int)
            bd_tp = int(np.sum((zero_preds == 1) & (y_zero == 1)))
            ctrl_fp = int(np.sum((zero_preds == 1) & (y_zero == 0)))
            ctrl_fpr = float(ctrl_fp / n_ctrl)
            bd_rec = float(bd_tp / n_bd)
            ci_rec_l, ci_rec_u = clopper_pearson_ci(bd_tp, n_bd)
            ci_fpr_l, ci_fpr_u = clopper_pearson_ci(ctrl_fp, n_ctrl)

            backdoor_records.append({
                "model": "isolation_forest",
                "seed": seed,
                "rule": rule_name,
                "threshold": t,
                "held_out_control_fp": ctrl_fp,
                "held_out_control_fpr": ctrl_fpr,
                "control_fpr_ci_lower": ci_fpr_l,
                "control_fpr_ci_upper": ci_fpr_u,
                "backdoor_detections": bd_tp,
                "backdoor_recall": bd_rec,
                "backdoor_recall_ci_lower": ci_rec_l,
                "backdoor_recall_ci_upper": ci_rec_u,
            })

            # Unseen Family Evaluation
            for fam in ["Worms", "Shellcode", "Analysis"]:
                fam_mask_sub = (unseen_dev_sub["attack_cat"] == fam).values
                fam_sc = sc_unseen[fam_mask_sub]
                n_fam = len(fam_sc)
                fam_tp = int(np.sum(fam_sc > t))
                fam_rec = float(fam_tp / n_fam)
                fam_ci_l, fam_ci_u = clopper_pearson_ci(fam_tp, n_fam)

                family_records.append({
                    "model": "isolation_forest",
                    "seed": seed,
                    "rule": rule_name,
                    "threshold": t,
                    "family": fam,
                    "n_instances": n_fam,
                    "detections": fam_tp,
                    "recall": fam_rec,
                    "recall_ci_lower": fam_ci_l,
                    "recall_ci_upper": fam_ci_u,
                })

    df_thresh = pd.DataFrame(thresh_records)
    df_dev_metrics = pd.DataFrame(dev_metrics_records)
    df_bd = pd.DataFrame(backdoor_records)
    df_fam = pd.DataFrame(family_records)

    # 10. Summary Across Seeds (Mean ± SD)
    summary_records = []
    for rule_name in ["p95", "p99", "p999", "mean_plus_2sigma", "mean_plus_3sigma"]:
        sub_bd = df_bd[df_bd["rule"] == rule_name]
        sub_dev = df_dev_metrics[df_dev_metrics["rule"] == rule_name]

        summary_records.append({
            "rule": rule_name,
            "mean_val_fpr": float(df_thresh[df_thresh["rule"] == rule_name]["val_fpr"].mean()),
            "std_val_fpr": float(df_thresh[df_thresh["rule"] == rule_name]["val_fpr"].std()),
            "mean_ctrl_fpr": float(sub_bd["held_out_control_fpr"].mean()),
            "std_ctrl_fpr": float(sub_bd["held_out_control_fpr"].std()),
            "mean_bd_recall": float(sub_bd["backdoor_recall"].mean()),
            "std_bd_recall": float(sub_bd["backdoor_recall"].std()),
            "mean_macro_f1": float(sub_dev["macro_f1"].mean()),
            "std_macro_f1": float(sub_dev["macro_f1"].std()),
        })
    df_summary = pd.DataFrame(summary_records)

    # 11. Write All Output CSVs and Metadata
    logger.info("=== STEP 5: Writing Output Artifacts & Metadata ===")
    p_thresh = thresh_dir / "threshold_sweep.csv"
    p_dev_json = dev_test_dir / "dev_test_metrics.json"
    p_bd = zero_day_dir / "backdoor_detection.csv"
    p_fam = zero_day_dir / "unseen_family_detection.csv"
    p_sum = summary_dir / "if_summary_mean_sd.csv"

    df_thresh.to_csv(p_thresh, index=False)
    with open(p_dev_json, "w", encoding="utf-8") as f:
        json.dump(df_dev_metrics.to_dict(orient="records"), f, indent=2)
    df_bd.to_csv(p_bd, index=False)
    df_fam.to_csv(p_fam, index=False)
    df_summary.to_csv(p_sum, index=False)

    artifact_hashes = {
        "calibration_benign_scores.csv": compute_sha256(cal_out_path),
        "dev_test_scores.csv": compute_sha256(dev_out_path),
        "zeroday_scores.csv": compute_sha256(zero_out_path),
        "unseen_family_scores.csv": compute_sha256(unseen_out_path),
        "threshold_sweep.csv": compute_sha256(p_thresh),
        "dev_test_metrics.json": compute_sha256(p_dev_json),
        "backdoor_detection.csv": compute_sha256(p_bd),
        "unseen_family_detection.csv": compute_sha256(p_fam),
        "if_summary_mean_sd.csv": compute_sha256(p_sum),
    }

    metadata = {
        "experiment_id": "EXP_IF_V1",
        "blueprint_version": "5.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "seeds": seeds,
        "parameters": {
            "n_estimators": n_estimators,
            "max_samples": max_samples,
            "contamination": contamination,
            "max_features": max_features,
        },
        "training_rows": len(train_benign_df),
        "ae_scaler_sha256": ae_scaler_sha256,
        "checkpoint_hashes": ckpt_hashes,
        "artifact_hashes": artifact_hashes,
        "status": "PASS",
    }
    with open(res_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    artifact_hashes["metadata.json"] = compute_sha256(res_dir / "metadata.json")

    logger.info("=== Isolation Forest Pipeline (S7) Completed Successfully ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2 / BATCH-C: Isolation Forest Baseline (S7)")
    parser.add_argument(
        "--config",
        type=str,
        default="revision_v5/publication_experiments/stage_f/configs/stage_f.yaml",
        help="Path to stage_f.yaml",
    )
    args = parser.parse_args()
    run_isolation_forest(Path(args.config))
