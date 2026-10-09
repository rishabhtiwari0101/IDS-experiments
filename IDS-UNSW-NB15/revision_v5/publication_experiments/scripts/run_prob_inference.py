#!/usr/bin/env python3
"""
revision_v5/publication_experiments/scripts/run_prob_inference.py
----------------------------------------------------------------
Phase 1: Probability and Reconstruction-Error Inference (S1).
Blueprint reference: §6 (BATCH-A, S1), §16 (C2), §0 Rules 1, 6, 12, 14, 15.

Key responsibilities:
1. Load models read-only with strict zero-training guard.
2. Verify all checkpoint, split, and UID list SHA-256 hashes against populations.yaml.
3. Compute frozen inference for DT, RF, SVM, NN, Stacking (seeds 42, 123, 2024), and AE.
4. Verify stacking meta-feature column order against src.models.stacking.meta_learner.META_FEATURE_COLS.
5. Assert exact reproduction against frozen reference predictions:
   - Stacking Backdoor detections (seed 42, threshold >= 0.5) = 582 / 583
   - Stacking Benign Control FPR (seed 42, threshold >= 0.5) = 7100 / 37000 = 0.191892
   - Per-row prediction matches for all supervised models.
6. Regenerate AE calibration benign reconstruction errors from canonical ae_final.pt + ae_scaler.joblib,
   cross-checking against legacy validation_reconstruction_errors.csv within numerical tolerance.
7. Write all output artifacts strictly inside revision_v5/.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
import sklearn
import torch
import yaml

# ---------------------------------------------------------------------------
# Zero-Training Guard (DQ-01: Replicated from scripts/scan_ml_patterns.py)
# ---------------------------------------------------------------------------

# START_ZERO_TRAINING_GUARD_DEFINITION
PROHIBITED_PATTERNS = [
    "fit_" + "transform",
    "import " + "shap",
    "torch." + "optim",
    "." + "backward()",
    "model." + "train()",
    "Grid" + "Search",
    "Randomized" + "Search",
    "." + "fit(",
]


def execute_zero_training_guard(script_path: Path) -> None:
    """Verify that this script contains no prohibited ML training/tuning calls."""
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
                if pattern == "." + "fit(":
                    if "PreprocessingPipeline().fit(train_df)" in line and "ALLOWED_PREPROCESSING_OHE_FIT" in line:
                        continue
                raise RuntimeError(
                    f"ZERO-TRAINING GUARD VIOLATION: prohibited pattern '{pattern}' "
                    f"found at line {i} of {script_path}: {stripped}"
                )
# END_ZERO_TRAINING_GUARD_DEFINITION


# ---------------------------------------------------------------------------
# Setup Paths & Logger
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("run_prob_inference")


def find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "data" / "splits").exists() and (current / "results").exists():
            return current
        current = current.parent
    return Path.cwd()


REPO_ROOT = find_repo_root()
NEW_ROOT = REPO_ROOT / "revision_v5"

# Add REPO_ROOT to sys.path to load src modules
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.models.autoencoder.ae_model import Autoencoder
from src.models.base_models.neural_network import IDSNet
from src.models.stacking.meta_learner import META_FEATURE_COLS
from src.preprocessing.preprocessing_pipeline import PreprocessingPipeline


# ---------------------------------------------------------------------------
# Hashing & File Utilities
# ---------------------------------------------------------------------------

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_list_sha256(items: List[str]) -> str:
    content = "\n".join(items).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def make_source_row_uid(source_split: str, raw_id: Any) -> str:
    return f"{source_split}:{raw_id}"


def resolve_path(rel_path: str) -> Path:
    p1 = NEW_ROOT / rel_path
    if p1.exists():
        return p1
    p2 = REPO_ROOT / rel_path
    if p2.exists():
        return p2
    return p1


# ---------------------------------------------------------------------------
# Main Inference Pipeline
# ---------------------------------------------------------------------------

def run_prob_inference(config_path: Path) -> None:
    execute_zero_training_guard(Path(__file__).resolve())
    logger.info("=== STEP 0: Zero-Training Guard Passed ===")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    manifest_rel = config.get("populations_manifest", "publication_experiments/configs/populations.yaml")
    manifest_path = resolve_path(manifest_rel)
    logger.info(f"Loading populations manifest: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        pop_cfg = yaml.safe_load(f)

    # 1. Manifest completeness & UID assertions
    logger.info("=== STEP 1: Population Manifest & UID List Assertions ===")
    cal_cfg = pop_cfg["populations"]["calibration_benign"]
    if cal_cfg.get("path") is None or cal_cfg.get("row_uid_list") is None:
        raise ValueError("populations.calibration_benign not resolved in populations.yaml")

    source_status = cal_cfg.get("source_status")
    if source_status == "contaminated_sensitivity_only":
        raise RuntimeError("source_status is contaminated_sensitivity_only; cannot produce headline outputs")

    # Verify split file hashes
    for split_key, split_info in [
        ("dev_test", pop_cfg["populations"]["dev_test"]),
        ("backdoor", pop_cfg["populations"]["zero_day"]["backdoor"]),
    ]:
        p = resolve_path(split_info["path"])
        actual_sha = compute_sha256(p)
        expected_sha = split_info["sha256"]
        if actual_sha != expected_sha:
            raise AssertionError(f"Split hash mismatch for {split_key}: expected {expected_sha}, got {actual_sha}")
        logger.info(f"Verified split SHA-256 for {split_key}: {actual_sha[:16]}...")

    # Verify UID list file hashes
    uid_checks = [
        ("calibration_benign", cal_cfg["row_uid_list"], cal_cfg["row_uid_list_sha256"]),
        ("benign_control", pop_cfg["populations"]["zero_day"]["benign_control"]["row_uid_list"],
         pop_cfg["populations"]["zero_day"]["benign_control"]["row_uid_list_sha256"]),
        ("cal_control", pop_cfg["populations"]["zero_day"]["benign_control"]["tier_b_split"]["cal_control"]["row_uid_list"],
         pop_cfg["populations"]["zero_day"]["benign_control"]["tier_b_split"]["cal_control"]["row_uid_list_sha256"]),
        ("eval_control", pop_cfg["populations"]["zero_day"]["benign_control"]["tier_b_split"]["eval_control"]["row_uid_list"],
         pop_cfg["populations"]["zero_day"]["benign_control"]["tier_b_split"]["eval_control"]["row_uid_list_sha256"]),
    ]

    for uid_name, uid_rel, expected_sha in uid_checks:
        uid_path = resolve_path(uid_rel)
        if not uid_path.exists():
            raise FileNotFoundError(f"UID list not found: {uid_path}")
        with open(uid_path, "r", encoding="utf-8") as f:
            uids = json.load(f)
        actual_sha = compute_list_sha256(uids)
        if actual_sha != expected_sha:
            raise AssertionError(f"UID list hash mismatch for {uid_name}: expected {expected_sha}, got {actual_sha}")
        logger.info(f"Verified UID list SHA-256 for {uid_name}: {actual_sha[:16]}...")

    # Load UID lists
    with open(resolve_path(cal_cfg["row_uid_list"]), "r") as f:
        cal_uids = json.load(f)
    with open(resolve_path(pop_cfg["populations"]["zero_day"]["benign_control"]["row_uid_list"]), "r") as f:
        benign_ctrl_uids = json.load(f)
    with open(resolve_path(pop_cfg["populations"]["zero_day"]["benign_control"]["tier_b_split"]["cal_control"]["row_uid_list"]), "r") as f:
        cal_ctrl_uids = json.load(f)
    with open(resolve_path(pop_cfg["populations"]["zero_day"]["benign_control"]["tier_b_split"]["eval_control"]["row_uid_list"]), "r") as f:
        eval_ctrl_uids = json.load(f)

    # Assert UID prefix and disjoint subset properties
    cal_prefix = cal_uids[0].split(":")[0]
    expected_cal_prefix = "UNSW_NB15_training-set.csv"
    if cal_prefix != expected_cal_prefix:
        raise AssertionError(f"Calibration UID prefix mismatch: expected {expected_cal_prefix}, got {cal_prefix}")
    logger.info(f"Confirmed calibration UID prefix matches S0: {cal_prefix}")

    if len(cal_ctrl_uids) != 18500 or len(eval_ctrl_uids) != 18500:
        raise AssertionError(f"Tier B halves counts != 18500: got {len(cal_ctrl_uids)}, {len(eval_ctrl_uids)}")
    if not set(cal_ctrl_uids).isdisjoint(set(eval_ctrl_uids)):
        raise AssertionError("Tier B halves (cal_control, eval_control) are not disjoint!")
    if set(cal_ctrl_uids).union(set(eval_ctrl_uids)) != set(benign_ctrl_uids):
        raise AssertionError("Tier B halves union does not equal the 37,000 benign control set!")
    logger.info("PASS: Tier B halves confirmed disjoint subsets (18,500 each, union = 37,000)")

    benign_ctrl_uids_set = set(benign_ctrl_uids)

    # 2. Verify meta-feature order
    logger.info("=== STEP 2: Meta-Learner Feature Order Verification ===")
    expected_meta_cols = [
        "dt_attack_probability",
        "rf_attack_probability",
        "svm_decision_score",
        "nn_attack_probability",
    ]
    if META_FEATURE_COLS != expected_meta_cols:
        raise AssertionError(
            f"META_FEATURE_COLS in meta_learner.py mismatch: expected {expected_meta_cols}, got {META_FEATURE_COLS}"
        )
    logger.info(f"Verified stacking meta-feature column order: {META_FEATURE_COLS}")

    # 3. Output directory enforcement (writes only under revision_v5/)
    logger.info("=== STEP 3: Output Directory Enforcement ===")
    out_rel = config.get("output_dir", "results/publication_experiments/EXP_PROB_INFERENCE_V1")
    out_dir = NEW_ROOT / out_rel if not str(out_rel).startswith(str(NEW_ROOT)) else Path(out_rel)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not str(out_dir.resolve()).startswith(str(NEW_ROOT.resolve())):
        raise RuntimeError(f"Output directory {out_dir} is outside {NEW_ROOT}")
    logger.info(f"Outputs will be written strictly inside: {out_dir}")

    # 4. Load Models and Scalers Read-Only
    logger.info("=== STEP 4: Loading Model Checkpoints and Scalers ===")
    ckpt_cfg = config["checkpoints"]
    dt_model = joblib.load(resolve_path(ckpt_cfg["dt"]))
    rf_model = joblib.load(resolve_path(ckpt_cfg["rf"]))
    rf_model.n_jobs = 1  # Sequential backend prevents named pipe issues under Windows sandbox
    svm_model = joblib.load(resolve_path(ckpt_cfg["svm"]))
    svm_scaler = joblib.load(resolve_path(ckpt_cfg["svm_scaler"]))

    nn_scaler = joblib.load(resolve_path(ckpt_cfg["nn_scaler"]))
    nn_model = IDSNet(input_dim=75, hidden_sizes=[128, 64])
    nn_state = torch.load(resolve_path(ckpt_cfg["nn"]), map_location="cpu", weights_only=True)
    nn_model.load_state_dict(nn_state)
    nn_model.eval()

    ae_scaler = joblib.load(resolve_path(ckpt_cfg["ae_scaler"]))
    ae_model = Autoencoder(input_dim=75)
    ae_state = torch.load(resolve_path(ckpt_cfg["ae"]), map_location="cpu", weights_only=True)
    ae_model.load_state_dict(ae_state)
    ae_model.eval()

    multi_class_patched = False
    meta_learners = {}
    for seed in [42, 123, 2024]:
        meta = joblib.load(resolve_path(ckpt_cfg[f"meta_seed_{seed}"]))
        if not hasattr(meta, "multi_class"):
            meta.multi_class = "auto"
            multi_class_patched = True
        meta_learners[seed] = meta

    # 5. Preprocessing & Feature Extraction
    logger.info("=== STEP 5: Preprocessing Re-derived from TRAIN (Zero Training) ===")
    train_df = pd.read_csv(resolve_path("data/splits/train.csv"))
    pipe = PreprocessingPipeline().fit(train_df)  # ALLOWED_PREPROCESSING_OHE_FIT: OHE category mapping on TRAIN only

    feats_path = resolve_path(config["features"])
    with open(feats_path, "r", encoding="utf-8") as f:
        selected_features = json.load(f)["features"]
    if len(selected_features) != 75:
        raise ValueError(f"Expected 75 selected features, got {len(selected_features)}")

    # Helper scoring function
    def score_population(
        df_raw: pd.DataFrame,
        split_name: str,
        source_split_prefix: str,
        population_type: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
        enc = pipe.transform(df_raw, view="unscaled", split_name=split_name)

        # Assert feature names match selected_features.json
        missing_feats = [feat for feat in selected_features if feat not in enc.feature_names]
        if missing_feats:
            raise AssertionError(f"Missing features in encoded {split_name}: {missing_feats}")

        df_enc = pd.DataFrame(enc.X, columns=enc.feature_names)
        X = df_enc[selected_features].values.astype(np.float64)

        if "id" in df_raw.columns:
            uids = [make_source_row_uid(source_split_prefix, rid) for rid in df_raw["id"]]
        else:
            uids = [make_source_row_uid(source_split_prefix, i) for i in range(len(df_raw))]

        labels = df_raw["label"].values.astype(int)
        cats = df_raw["attack_cat"].values if "attack_cat" in df_raw.columns else ["Unknown"] * len(df_raw)

        # Supervised scores
        dt_prob = dt_model.predict_proba(X)[:, 1]
        rf_prob = rf_model.predict_proba(X)[:, 1]
        X_svm = svm_scaler.transform(X)
        svm_score = svm_model.decision_function(X_svm)
        X_nn = nn_scaler.transform(X)
        with torch.no_grad():
            nn_prob = torch.sigmoid(nn_model(torch.tensor(X_nn, dtype=torch.float32))).numpy().flatten()

        meta_X = np.column_stack([dt_prob, rf_prob, svm_score, nn_prob])
        stack_probs = {}
        for seed, meta in meta_learners.items():
            stack_probs[seed] = meta.predict_proba(meta_X)[:, 1]

        sup_df = pd.DataFrame({
            "row_uid": uids,
            "label": labels,
            "attack_cat": cats,
            "population_type": population_type,
            "dt_attack_probability": dt_prob,
            "rf_attack_probability": rf_prob,
            "svm_decision_score": svm_score,
            "nn_attack_probability": nn_prob,
            "stacking_attack_probability_seed42": stack_probs[42],
            "stacking_attack_probability_seed123": stack_probs[123],
            "stacking_attack_probability_seed2024": stack_probs[2024],
        })

        # AE scores
        X_ae = ae_scaler.transform(X)
        with torch.no_grad():
            recon = ae_model(torch.tensor(X_ae, dtype=torch.float32)).numpy()
        re = np.mean((X_ae - recon) ** 2, axis=1)

        ae_df = pd.DataFrame({
            "row_uid": uids,
            "label": labels,
            "attack_cat": cats,
            "population_type": population_type,
            "reconstruction_error": re,
        })

        return sup_df, ae_df, X

    # 6. Score Populations
    logger.info("=== STEP 6: Scoring Populations ===")

    # (a) DEV_TEST (81,749)
    logger.info("Scoring DEV_TEST (81,749 rows)...")
    dev_raw = pd.read_csv(resolve_path(pop_cfg["populations"]["dev_test"]["path"]))
    sup_dev, ae_dev, _ = score_population(
        dev_raw, "development_test", "UNSW_NB15_testing-set.csv", "DEV_TEST"
    )

    # (b) CALIBRATION_BENIGN (11,200) - prefix must match S0 (UNSW_NB15_training-set.csv)
    logger.info("Scoring CALIBRATION_BENIGN (11,200 rows)...")
    val_raw = pd.read_csv(resolve_path(cal_cfg["path"]))
    val_benign = val_raw[val_raw["label"] == 0].copy()
    sup_cal, ae_cal, _ = score_population(
        val_benign, "validation", cal_prefix, "CALIBRATION_BENIGN"
    )

    # Assert scored UID set equals committed calibration_benign list
    if set(sup_cal["row_uid"]) != set(cal_uids):
        raise AssertionError("Scored calibration_benign UID set does not equal committed UID list!")
    logger.info("PASS: Scored calibration_benign UID set matches committed list exactly (11,200 rows)")

    # (c) ZERO_DAY_BACKDOOR (583)
    logger.info("Scoring ZERO_DAY_BACKDOOR (583 rows)...")
    backdoor_raw = pd.read_csv(resolve_path(pop_cfg["populations"]["zero_day"]["backdoor"]["path"]))
    sup_backdoor, ae_backdoor, _ = score_population(
        backdoor_raw, "protected_unseen_attack", "UNSW_NB15_testing-set.csv", "ZERO_DAY_BACKDOOR"
    )

    # (d) BENIGN_CONTROL (extract from scored DEV_TEST)
    logger.info("Extracting BENIGN_CONTROL (37,000 rows)...")
    sup_benign_ctrl = sup_dev[sup_dev["row_uid"].isin(benign_ctrl_uids_set)].copy()
    ae_benign_ctrl = ae_dev[ae_dev["row_uid"].isin(benign_ctrl_uids_set)].copy()
    sup_benign_ctrl["population_type"] = "BENIGN_CONTROL"
    ae_benign_ctrl["population_type"] = "BENIGN_CONTROL"

    # Assert scored UID set equals committed benign_control list
    if set(sup_benign_ctrl["row_uid"]) != benign_ctrl_uids_set:
        raise AssertionError("Scored benign_control UID set does not equal committed UID list!")
    if not set(cal_ctrl_uids).issubset(set(sup_benign_ctrl["row_uid"])):
        raise AssertionError("cal_control is not a subset of scored benign_control!")
    if not set(eval_ctrl_uids).issubset(set(sup_benign_ctrl["row_uid"])):
        raise AssertionError("eval_control is not a subset of scored benign_control!")
    logger.info("PASS: Scored benign_control UID set matches committed list (37,000 rows), and halves are confirmed subsets")

    # Combine ZERO_DAY_COMBINED (37,583 rows)
    sup_zeroday = pd.concat([sup_backdoor, sup_benign_ctrl], ignore_index=True)
    ae_zeroday = pd.concat([ae_backdoor, ae_benign_ctrl], ignore_index=True)

    # (e) UNSEEN_FAMILIES for AE: derive by SLICING ae_dev, not re-transforming
    logger.info("Deriving UNSEEN_FAMILIES for AE by slicing ae_dev...")
    unseen_mask = ae_dev["attack_cat"].isin(["Worms", "Shellcode", "Analysis"])
    ae_unseen = ae_dev[unseen_mask].copy()
    ae_unseen["population_type"] = "UNSEEN_FAMILIES"

    # 7. Exact Reproduction Assertions
    logger.info("=== STEP 7: Asserting Exact Reproduction of Frozen References ===")

    # Load frozen references
    ref_backdoor = pd.read_csv(resolve_path("results/zero_day/EXP_ZERODAY_V1/predictions/zero_day_backdoor_predictions.csv"))
    ref_benign = pd.read_csv(resolve_path("results/zero_day/EXP_ZERODAY_V1/predictions/benign_control_predictions.csv"))

    # Assert Backdoor detections (seed 42 stacking >= 0.5)
    stack_42_backdoor_pred = (sup_backdoor["stacking_attack_probability_seed42"] >= 0.5).astype(int).values
    backdoor_stack_detections = int(stack_42_backdoor_pred.sum())
    if backdoor_stack_detections != 582:
        raise AssertionError(f"Backdoor stacking detections != 582: got {backdoor_stack_detections}")
    if not np.array_equal(stack_42_backdoor_pred, ref_backdoor["stacking_prediction"].values):
        raise AssertionError("Per-row mismatch on Backdoor stacking predictions vs frozen reference!")
    logger.info("PASS: Backdoor stacking detections = 582/583 and 100% per-row match")

    # Assert Benign Control FPs & FPR (seed 42 stacking >= 0.5)
    ref_benign_uids = ref_benign["source_row_uid"].tolist()
    sup_benign_aligned = sup_benign_ctrl.set_index("row_uid").loc[ref_benign_uids].reset_index()
    stack_42_benign_pred = (sup_benign_aligned["stacking_attack_probability_seed42"] >= 0.5).astype(int).values
    benign_fps = int(stack_42_benign_pred.sum())
    benign_fpr = benign_fps / len(stack_42_benign_pred)
    if benign_fps != 7100:
        raise AssertionError(f"Benign control stacking FPs != 7100: got {benign_fps}")
    if not np.isclose(benign_fpr, 0.1918918918918919, atol=1e-6):
        raise AssertionError(f"Benign control stacking FPR != 0.191892: got {benign_fpr:.6f}")
    if not np.array_equal(stack_42_benign_pred, ref_benign["stacking_prediction"].values):
        raise AssertionError("Per-row mismatch on Benign Control stacking predictions vs frozen reference!")
    logger.info("PASS: Benign Control stacking FPs = 7100/37000 (FPR = 0.191892) and 100% per-row match")

    # Assert Base Models per-row matches on Backdoor
    if not np.array_equal((sup_backdoor["dt_attack_probability"] >= 0.5).astype(int).values, ref_backdoor["dt_prediction"].values):
        raise AssertionError("DT per-row mismatch on Backdoor")
    if not np.array_equal((sup_backdoor["rf_attack_probability"] >= 0.5).astype(int).values, ref_backdoor["rf_prediction"].values):
        raise AssertionError("RF per-row mismatch on Backdoor")
    if not np.array_equal((sup_backdoor["svm_decision_score"] >= 0.0).astype(int).values, ref_backdoor["svm_prediction"].values):
        raise AssertionError("SVM per-row mismatch on Backdoor")
    if not np.array_equal((sup_backdoor["nn_attack_probability"] >= 0.5).astype(int).values, ref_backdoor["nn_prediction"].values):
        raise AssertionError("NN per-row mismatch on Backdoor")
    logger.info("PASS: All base models reproduce frozen Backdoor predictions 100% per-row")

    # Cross-check AE validation RE vs legacy file
    legacy_val_re_path = resolve_path("results/autoencoder/EXP_AE_V1/threshold/validation_reconstruction_errors.csv")
    if legacy_val_re_path.exists():
        legacy_val_df = pd.read_csv(legacy_val_re_path)
        legacy_re_vals = legacy_val_df["re_value"].values
        regen_re_vals = ae_cal["reconstruction_error"].values
        max_diff = float(np.max(np.abs(regen_re_vals - legacy_re_vals)))
        if max_diff > 1e-4:
            raise AssertionError(f"Regenerated AE validation RE max diff {max_diff} exceeds tolerance 1e-4")
        logger.info(f"PASS: Regenerated AE validation RE matches legacy within tolerance (max abs diff: {max_diff:.2e})")

    # Assert Unseen Family Counts
    unseen_counts = ae_unseen["attack_cat"].value_counts().to_dict()
    expected_unseen = {"Worms": 44, "Shellcode": 378, "Analysis": 677}
    for fam, cnt in expected_unseen.items():
        if unseen_counts.get(fam, 0) != cnt:
            raise AssertionError(f"Unseen family count mismatch for {fam}: expected {cnt}, got {unseen_counts.get(fam, 0)}")
    logger.info(f"PASS: Unseen family counts equal exactly {expected_unseen}")

    # 8. Write Output Files
    logger.info("=== STEP 8: Writing Output CSVs and Metadata ===")
    out_files = {
        "dev_test_probabilities.csv": sup_dev,
        "calibration_benign_probabilities.csv": sup_cal,
        "zeroday_probabilities.csv": sup_zeroday,
        "ae_dev_test_reconstruction_errors.csv": ae_dev,
        "ae_calibration_benign_reconstruction_errors.csv": ae_cal,
        "ae_zeroday_reconstruction_errors.csv": ae_zeroday,
        "ae_unseen_family_reconstruction_errors.csv": ae_unseen,
    }

    file_hashes = {}
    for fname, df in out_files.items():
        dest = out_dir / fname
        df.to_csv(dest, index=False)
        sha = compute_sha256(dest)
        file_hashes[fname] = sha
        logger.info(f"Wrote {dest.name} ({len(df)} rows, SHA: {sha[:16]}...)")

    # Self Check JSON
    self_check = {
        "experiment_id": "EXP_PROB_INFERENCE_V1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_training_guard": "PASS",
        "row_counts": {
            "dev_test": len(sup_dev),
            "calibration_benign": len(sup_cal),
            "zeroday_combined": len(sup_zeroday),
            "backdoor": len(sup_backdoor),
            "benign_control": len(sup_benign_ctrl),
            "unseen_families": len(ae_unseen),
        },
        "uid_set_assertions": {
            "calibration_benign_match": True,
            "benign_control_match": True,
            "cal_control_is_subset": True,
            "eval_control_is_subset": True,
            "tier_b_halves_disjoint": True,
            "tier_b_halves_union_equals_benign_control": True,
        },
        "nan_inf_check": {
            fname: bool(not df.isnull().values.any() and not np.isinf(df.select_dtypes(include=[np.number]).values).any())
            for fname, df in out_files.items()
        },
        "probability_range_check": {
            "dt_prob": bool((sup_dev["dt_attack_probability"].between(0, 1)).all()),
            "rf_prob": bool((sup_dev["rf_attack_probability"].between(0, 1)).all()),
            "nn_prob": bool((sup_dev["nn_attack_probability"].between(0, 1)).all()),
            "stack_42": bool((sup_dev["stacking_attack_probability_seed42"].between(0, 1)).all()),
        },
        "reproduction_assertions": {
            "backdoor_stack_detections": backdoor_stack_detections,
            "benign_control_stack_fps": benign_fps,
            "benign_control_stack_fpr": benign_fpr,
            "per_row_backdoor_match": True,
            "per_row_benign_control_match": True,
        },
        "unseen_family_counts": unseen_counts,
        "legacy_ae_validation_re_max_diff": max_diff if legacy_val_re_path.exists() else None,
        "overall_status": "PASS",
    }

    with open(out_dir / "self_check.json", "w", encoding="utf-8") as f:
        json.dump(self_check, f, indent=2)
    file_hashes["self_check.json"] = compute_sha256(out_dir / "self_check.json")

    # Metadata JSON
    metadata = {
        "experiment_id": "EXP_PROB_INFERENCE_V1",
        "blueprint_version": "5.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "manifest_path": str(manifest_path),
        "meta_feature_columns": META_FEATURE_COLS,
        "preprocessing": {
            "note": "Preprocessing is re-derived from TRAIN with no model or scaler fitted (OHE categories mapping only; zero training).",
            "feature_names_matched_selected_features": True,
            "feature_count": len(selected_features),
            "features_path": str(feats_path),
        },
        "environment": {
            "sklearn_version": sklearn.__version__,
            "multi_class_patch": "Applied multi_class='auto' patch to LogisticRegression meta-learners to support unpickling in scikit-learn",
            "rf_n_jobs": 1,
        },
        "output_directory": str(out_dir),
        "artifact_hashes": file_hashes,
    }

    with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    file_hashes["metadata.json"] = compute_sha256(out_dir / "metadata.json")

    logger.info("=== Probability Inference Complete: All Gates Passed ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1: Probability and RE Inference (S1)")
    parser.add_argument(
        "--config",
        type=str,
        default="revision_v5/publication_experiments/configs/prob_inference.yaml",
        help="Path to prob_inference.yaml",
    )
    args = parser.parse_args()
    run_prob_inference(Path(args.config))
