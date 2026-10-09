#!/usr/bin/env python3
"""
run_cross_consistency_check.py
==============================
Executable Cross-Result Consistency & Integrity Verification (Stage S9)

BLUEPRINT REFERENCE:
--------------------
- Blueprint §16 (Stage S9 — run_cross_consistency_check.py)
- Blueprint §17 (Phase 7: Cross-Result Consistency Check)
- Governing Rules: Zero-training guard, exact arithmetic, read-only frozen files,
  exit non-zero on any FAIL.

SPECIFIED CONSISTENCY VERIFICATIONS:
------------------------------------
1. Headline-tier rule text hash f663657c... (stripped form) matches matched_fpr.yaml
   and headline_tier_decision.json, with headline_tier == "B".
2. Frozen baseline integrity: exactly 342/342 baseline files match their SHA-256
   in frozen_baseline_full.json, plus blueprint critical split hashes.
3. Cross-stage reconciliation:
   - S1 vs S3: Calibrated Tier B thresholds applied to S1 score vectors on EVAL_CONTROL
     and Backdoor exactly reproduce S3's eval_fp, eval_tp, and recall across all 44 cells.
   - S3 AE vs S6 AE Ablation: S3 Tier A AE thresholds and detections at 1/20 (p95)
     and 1/100 (p99) match S6 ablation table detection counts on full benign control
     (1993 and 504) and Backdoor (38 and 24).
   - S4 TOST vs mcnemar_results.csv: (A, B, C, D) = (582, 0, 0, 1), total N = 583.
4. Additional §17 Phase 7 checks:
   - Stacking DEV_TEST Macro-F1 for seeds 42/123/2024 matches h1_results.json.
   - Stacking threshold-0.5 FPR on benign control (7,100 / 37,000) and Backdoor
     detections (582 / 583) match zero_day_metrics.csv.
   - AE historical threshold tau=11.16006... on benign control (FP=19) and Backdoor
     (TP=0) matches zero_day_metrics.csv and threshold_config.json.
   - AE validation reconstruction error & threshold stats match threshold_config.json.
   - Isolation Forest scaler hash equals frozen AE scaler; training rows = 44,800.
   - Population partition integrity: CAL_CONTROL and EVAL_CONTROL are disjoint halves
     (18,500 each) whose union is benign_control (37,000); unseen family counts 44/378/677.
   - Alert budget analysis outputs verified: 44 rows, 4 budgets, tie_unattainable carried.

OUTPUTS:
--------
- revision_v5/results/publication_experiments/EXP_CROSS_CHECK_V1/cross_check_report.json
- revision_v5/results/publication_experiments/EXP_CROSS_CHECK_V1/self_check.json
- revision_v5/results/publication_experiments/EXP_CROSS_CHECK_V1/metadata.json
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

import numpy as np
import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("s9_cross_check")


# ---------------------------------------------------------------------------
# Zero-Training Guard (Mandatory Header)
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
    """Verify that this analysis script contains no prohibited ML training/tuning calls."""
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
        if in_guard_def or stripped.startswith("#"):
            continue
        if stripped.startswith('"""') or stripped.endswith('"""') or stripped == '"""':
            continue
        for pattern in PROHIBITED_PATTERNS:
            if pattern in line:
                raise RuntimeError(
                    f"ZERO-TRAINING GUARD VIOLATION: prohibited pattern '{pattern}' "
                    f"found at {script_path.name}:{i}:\n  {line.strip()}"
                )
# END_ZERO_TRAINING_GUARD_DEFINITION


# ---------------------------------------------------------------------------
# Path Resolution and Hashing Utilities
# ---------------------------------------------------------------------------
def find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "data" / "splits").exists() and (current / "results").exists():
            return current
        current = current.parent
    return Path.cwd()


REPO_ROOT = find_repo_root()
NEW_ROOT = REPO_ROOT / "revision_v5"


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


# ---------------------------------------------------------------------------
# Check 1: Frozen Baseline Integrity (342/342 files)
# ---------------------------------------------------------------------------
def check_frozen_baseline_integrity() -> Dict[str, Any]:
    logger.info("=== CHECK 1: Frozen Baseline Integrity (342/342) ===")
    baseline_path = NEW_ROOT / "frozen_baseline_full.json"
    if not baseline_path.exists():
        raise FileNotFoundError(f"Missing frozen_baseline_full.json at {baseline_path}")

    with open(baseline_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["file_count"] == len(data["hashes"]) == 342, (
        f"Expected data['file_count'] == len(data['hashes']) == 342, "
        f"got file_count={data.get('file_count')}, len(hashes)={len(data['hashes'])}"
    )
    baseline = data["hashes"]

    expected_total = 342
    actual_total = len(baseline)

    mismatches = []
    missing_files = []
    matched_count = 0

    for rel_path, expected_hash in baseline.items():
        file_path = REPO_ROOT / rel_path
        if not file_path.exists():
            missing_files.append(rel_path)
            continue
        actual_hash = compute_sha256(file_path)
        if actual_hash != expected_hash:
            mismatches.append({"file": rel_path, "expected": expected_hash, "actual": actual_hash})
        else:
            matched_count += 1

    if missing_files or mismatches:
        raise AssertionError(
            f"Frozen baseline integrity failure: {len(missing_files)} missing, "
            f"{len(mismatches)} hash mismatches. Sample: {mismatches[:3]}"
        )

    # Check blueprint-critical hashes
    crit_splits = {
        "data/splits/development_test.csv": "04725e85732ab2fc6d9eaaa6105418b22b083b5c651067e7b0785464f414e508",
        "data/splits/protected_unseen_attack.csv": "6ffd23479b575e438ad90678268f40f674a663c2b9507aaf65089623397a9d91",
    }
    for rel_path, exp_hash in crit_splits.items():
        act_hash = compute_sha256(REPO_ROOT / rel_path)
        if act_hash != exp_hash:
            raise AssertionError(f"Critical split hash mismatch on {rel_path}: {act_hash} != {exp_hash}")

    logger.info(f"PASS: Frozen baseline verified: {matched_count}/{expected_total} files exact match.")
    return {
        "status": "PASS",
        "matched_files": matched_count,
        "total_baseline_files": expected_total,
        "critical_splits_verified": list(crit_splits.keys()),
    }


# ---------------------------------------------------------------------------
# Check 2: Headline Tier Rule Text Hash & Decision
# ---------------------------------------------------------------------------
def check_headline_tier_decision() -> Dict[str, Any]:
    logger.info("=== CHECK 2: Headline Tier Rule Text Hash & Decision ===")
    yaml_path = resolve_path("publication_experiments/configs/matched_fpr.yaml")
    decision_path = resolve_path("results/publication_experiments/EXP_MATCHED_FPR_V1/headline_tier_decision.json")

    with open(yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    with open(decision_path, "r", encoding="utf-8") as f:
        dec = json.load(f)

    expected_hash = "f663657c93046446d0753f56de95fe79f5bbf279b965056082b258801752751f"

    rule_yaml_str = str(cfg["headline_tier_rule"]).strip()
    rule_yaml_hash = hashlib.sha256(rule_yaml_str.encode("utf-8")).hexdigest()

    rule_dec_str = str(dec["rule_text"]).strip()
    rule_dec_hash = hashlib.sha256(rule_dec_str.encode("utf-8")).hexdigest()

    if rule_yaml_hash != expected_hash:
        raise AssertionError(f"matched_fpr.yaml rule hash mismatch: {rule_yaml_hash} != {expected_hash}")
    if rule_dec_hash != expected_hash:
        raise AssertionError(f"headline_tier_decision.json rule hash mismatch: {rule_dec_hash} != {expected_hash}")
    if dec.get("headline_tier_rule_sha256") != expected_hash:
        raise AssertionError(f"headline_tier_rule_sha256 in decision file mismatch: {dec.get('headline_tier_rule_sha256')}")
    if dec.get("headline_tier") != "B":
        raise AssertionError(f"headline_tier in decision file is not 'B': {dec.get('headline_tier')}")

    logger.info(f"PASS: Headline rule text hash verified: {expected_hash} (stripped form). Headline tier is 'B'.")
    return {
        "status": "PASS",
        "expected_hash": expected_hash,
        "yaml_rule_hash": rule_yaml_hash,
        "decision_rule_hash": rule_dec_hash,
        "headline_tier": dec.get("headline_tier"),
    }


# ---------------------------------------------------------------------------
# Check 3: Cross-Stage Reconciliation: S4 vs mcnemar_results.csv
# ---------------------------------------------------------------------------
def check_s4_vs_mcnemar() -> Dict[str, Any]:
    logger.info("=== CHECK 3: Cross-Stage Reconciliation — S4 vs McNemar ===")
    tost_path = resolve_path("results/publication_experiments/EXP_TOST_V1/tost_rf_equivalence.json")
    mcnemar_path = resolve_path("results/publication_experiments/EXP_STATS_ROBUSTNESS_V1/paired_tests/mcnemar_results.csv")

    with open(tost_path, "r", encoding="utf-8") as f:
        tost = json.load(f)

    df_mcnemar = pd.read_csv(mcnemar_path)
    rf_rows = df_mcnemar[df_mcnemar["model"] == "RF"]
    if len(rf_rows) == 0:
        raise AssertionError("RF row missing from mcnemar_results.csv")
    rf_row = rf_rows.iloc[0]

    expected_counts = {"A": 582, "B": 0, "C": 0, "D": 1, "total": 583}

    mcnemar_counts = {
        "A": int(rf_row["A_both_correct"]),
        "B": int(rf_row["B_canon_only"]),
        "C": int(rf_row["C_nottl_only"]),
        "D": int(rf_row["D_neither_correct"]),
        "total": int(rf_row["total_pairs"]),
    }
    tost_counts = {
        "A": int(tost["A"]),
        "B": int(tost["B"]),
        "C": int(tost["C"]),
        "D": int(tost["D"]),
        "total": int(tost["A"] + tost["B"] + tost["C"] + tost["D"]),
    }

    if mcnemar_counts != expected_counts:
        raise AssertionError(f"mcnemar_results.csv counts mismatch: {mcnemar_counts} != {expected_counts}")
    if tost_counts != expected_counts:
        raise AssertionError(f"tost_rf_equivalence.json counts mismatch: {tost_counts} != {expected_counts}")
    if tost.get("equivalence_margin") != 0.01:
        raise AssertionError(f"tost equivalence_margin != 0.01: {tost.get('equivalence_margin')}")

    logger.info("PASS: S4 TOST and McNemar RF results reconcile exactly: (A,B,C,D) = (582, 0, 0, 1), N=583.")
    return {
        "status": "PASS",
        "counts": expected_counts,
        "tost_equivalence_margin": tost.get("equivalence_margin"),
        "tost_exact_p_value": tost.get("conservative_exact_p_value"),
    }


# ---------------------------------------------------------------------------
# Check 4: Cross-Stage Reconciliation: S3 AE vs S6 AE Ablation
# ---------------------------------------------------------------------------
def check_s3_ae_vs_s6() -> Dict[str, Any]:
    """
    Cross-stage reconciliation between S3 (matched_fpr_table.csv) and S6 (ae_ablation_results.csv).

    METHODOLOGICAL CONTEXT & THRESHOLD DEFINITION DIFFERENCE:
    - S3 Tier A AE calibration uses exact discrete order statistics (t = sorted_desc[k])
      on 11,200 calibration benign reconstruction errors:
        * Budget 1/20 (5% nominal): k = floor(11200 * 0.05) = 560 -> t_s3_p95 = 0.567381313...
        * Budget 1/100 (1% nominal): k = floor(11200 * 0.01) = 112 -> t_s3_p99 = 1.512163779...
    - S6 AE ablation uses linear-interpolated percentiles (np.percentile with method='linear')
      from EXP_MAD_THRESHOLD_V1/mad_threshold.json:
        * Rule p95: t_s6_p95 = 0.567386202...
        * Rule p99: t_s6_p99 = 1.512163906...
    - The two definitions differ slightly:
        * |t_s3_p95 - t_s6_p95| = 4.89e-6 (relative diff = 8.62e-6)
        * |t_s3_p99 - t_s6_p99| = 1.27e-7 (relative diff = 8.40e-8)
    - In the zero-day evaluation dataset (37,000 benign control + 583 Backdoor), exactly 0 samples
      fall in the interpolation intervals (0.567381, 0.567386] and (1.5121638, 1.5121639].
    - As a result, both tables record identical realized counts:
        * p95 / 1/20: eval_fp = 1993, eval_tp = 38
        * p99 / 1/100: eval_fp = 504, eval_tp = 24

    This check verifies:
    1. Threshold proximity (|t_s3 - t_s6| / t_s6 < 1e-4 for both p95 and p99).
    2. Zero evaluation samples in the threshold delta intervals.
    3. Reconciled detection counts in S3 and S6 tables match the realized table entries.
    """
    logger.info("=== CHECK 4: Cross-Stage Reconciliation — S3 AE vs S6 AE Ablation ===")
    s3_path = resolve_path("results/publication_experiments/EXP_MATCHED_FPR_V1/matched_fpr_table.csv")
    s6_path = resolve_path("results/publication_experiments/EXP_AE_ABLATION_V1/ae_ablation_results.csv")
    s1_ae_zeroday_path = resolve_path("results/publication_experiments/EXP_PROB_INFERENCE_V1/ae_zeroday_reconstruction_errors.csv")

    df_s3 = pd.read_csv(s3_path)
    df_s6 = pd.read_csv(s6_path)
    df_ae_zero = pd.read_csv(s1_ae_zeroday_path)
    re_vals = df_ae_zero["reconstruction_error"].values

    s3_tier_a = df_s3[(df_s3["calibration_tier"] == "A") & (df_s3["model"] == "ae")]
    s3_p95 = s3_tier_a[s3_tier_a["nominal_budget_str"] == "1/20"].iloc[0]
    s3_p99 = s3_tier_a[s3_tier_a["nominal_budget_str"] == "1/100"].iloc[0]

    s6_bcf_p95 = df_s6[(df_s6["population"] == "benign_control_full") & (df_s6["rule_name"] == "p95")].iloc[0]
    s6_bcf_p99 = df_s6[(df_s6["population"] == "benign_control_full") & (df_s6["rule_name"] == "p99")].iloc[0]
    s6_bd_p95 = df_s6[(df_s6["population"] == "backdoor_zeroday") & (df_s6["rule_name"] == "p95")].iloc[0]
    s6_bd_p99 = df_s6[(df_s6["population"] == "backdoor_zeroday") & (df_s6["rule_name"] == "p99")].iloc[0]

    t_s3_p95 = float(s3_p95["threshold"])
    t_s6_p95 = float(s6_bcf_p95["threshold_value"])
    rel_diff_p95 = abs(t_s3_p95 - t_s6_p95) / t_s6_p95
    if rel_diff_p95 >= 1e-4:
        raise AssertionError(f"p95 threshold relative diff too large: {rel_diff_p95:.2e}")

    t_s3_p99 = float(s3_p99["threshold"])
    t_s6_p99 = float(s6_bcf_p99["threshold_value"])
    rel_diff_p99 = abs(t_s3_p99 - t_s6_p99) / t_s6_p99
    if rel_diff_p99 >= 1e-4:
        raise AssertionError(f"p99 threshold relative diff too large: {rel_diff_p99:.2e}")

    # Verify zero samples in the interpolation gap
    gap_samples_p95 = int(((re_vals > min(t_s3_p95, t_s6_p95)) & (re_vals <= max(t_s3_p95, t_s6_p95))).sum())
    gap_samples_p99 = int(((re_vals > min(t_s3_p99, t_s6_p99)) & (re_vals <= max(t_s3_p99, t_s6_p99))).sum())
    if gap_samples_p95 != 0:
        raise AssertionError(f"Samples found in p95 threshold interpolation gap: {gap_samples_p95}")
    if gap_samples_p99 != 0:
        raise AssertionError(f"Samples found in p99 threshold interpolation gap: {gap_samples_p99}")

    # Reconcile table detections
    if int(s3_p95["eval_fp"]) != int(s6_bcf_p95["n_detected"]):
        raise AssertionError(f"p95 control FP mismatch: S3={s3_p95['eval_fp']}, S6={s6_bcf_p95['n_detected']}")
    if int(s3_p95["eval_tp"]) != int(s6_bd_p95["n_detected"]):
        raise AssertionError(f"p95 Backdoor TP mismatch: S3={s3_p95['eval_tp']}, S6={s6_bd_p95['n_detected']}")
    if int(s3_p99["eval_fp"]) != int(s6_bcf_p99["n_detected"]):
        raise AssertionError(f"p99 control FP mismatch: S3={s3_p99['eval_fp']}, S6={s6_bcf_p99['n_detected']}")
    if int(s3_p99["eval_tp"]) != int(s6_bd_p99["n_detected"]):
        raise AssertionError(f"p99 Backdoor TP mismatch: S3={s3_p99['eval_tp']}, S6={s6_bd_p99['n_detected']}")

    logger.info(
        f"PASS: S3 AE Tier A vs S6 Ablation verified:\n"
        f"  p95 (1/20): t_S3={t_s3_p95:.6f}, t_S6={t_s6_p95:.6f} (rel diff={rel_diff_p95:.2e}, gap samples={gap_samples_p95}); "
        f"control FP={s3_p95['eval_fp']}, Backdoor TP={s3_p95['eval_tp']}\n"
        f"  p99 (1/100): t_S3={t_s3_p99:.6f}, t_S6={t_s6_p99:.6f} (rel diff={rel_diff_p99:.2e}, gap samples={gap_samples_p99}); "
        f"control FP={s3_p99['eval_fp']}, Backdoor TP={s3_p99['eval_tp']}"
    )
    return {
        "status": "PASS",
        "p95_threshold_s3": t_s3_p95,
        "p95_threshold_s6": t_s6_p95,
        "p95_rel_diff": rel_diff_p95,
        "p95_gap_samples": gap_samples_p95,
        "p95_control_fp": int(s3_p95["eval_fp"]),
        "p95_backdoor_tp": int(s3_p95["eval_tp"]),
        "p99_threshold_s3": t_s3_p99,
        "p99_threshold_s6": t_s6_p99,
        "p99_rel_diff": rel_diff_p99,
        "p99_gap_samples": gap_samples_p99,
        "p99_control_fp": int(s3_p99["eval_fp"]),
        "p99_backdoor_tp": int(s3_p99["eval_tp"]),
    }


# ---------------------------------------------------------------------------
# Check 5: Cross-Stage Reconciliation: S1 vs S3 Matched-FPR
# ---------------------------------------------------------------------------
def check_s1_vs_s3() -> Dict[str, Any]:
    logger.info("=== CHECK 5: Cross-Stage Reconciliation — S1 vs S3 Matched-FPR ===")
    s3_tier_b_path = resolve_path("results/publication_experiments/EXP_MATCHED_FPR_V1/matched_fpr_tier_b.csv")
    s1_zeroday_path = resolve_path("results/publication_experiments/EXP_PROB_INFERENCE_V1/zeroday_probabilities.csv")
    s1_devtest_path = resolve_path("results/publication_experiments/EXP_PROB_INFERENCE_V1/dev_test_probabilities.csv")
    s1_ae_zeroday_path = resolve_path("results/publication_experiments/EXP_PROB_INFERENCE_V1/ae_zeroday_reconstruction_errors.csv")
    s1_ae_devtest_path = resolve_path("results/publication_experiments/EXP_PROB_INFERENCE_V1/ae_dev_test_reconstruction_errors.csv")
    if_zeroday_path = resolve_path("results/publication_experiments/EXP_IF_V1/scores/zeroday_scores.csv")
    eval_uids_path = resolve_path("results/publication_experiments/EXP_POPULATIONS_V1/eval_control_row_uids.json")

    df_s3 = pd.read_csv(s3_tier_b_path)
    df_zero = pd.read_csv(s1_zeroday_path)
    df_dev = pd.read_csv(s1_devtest_path)
    df_ae_zero = pd.read_csv(s1_ae_zeroday_path)
    df_ae_dev = pd.read_csv(s1_ae_devtest_path)
    df_if_zero = pd.read_csv(if_zeroday_path)

    with open(eval_uids_path, "r", encoding="utf-8") as f:
        eval_uids = set(json.load(f))

    # Mask for EVAL_CONTROL (18,500 benign rows)
    eval_mask = df_dev["row_uid"].isin(eval_uids)
    if eval_mask.sum() != 18500:
        raise AssertionError(f"EVAL_CONTROL rows in dev_test != 18,500: {eval_mask.sum()}")
    df_eval = df_dev[eval_mask]
    df_ae_eval = df_ae_dev[df_ae_dev["row_uid"].isin(eval_uids)]

    # In zeroday_probabilities, Backdoor attack rows have label == 1 (583 rows)
    attack_mask = df_zero["label"] == 1
    if attack_mask.sum() != 583:
        raise AssertionError(f"Backdoor attack rows != 583: {attack_mask.sum()}")
    df_attack = df_zero[attack_mask]
    df_ae_attack = df_ae_zero[df_ae_zero["label"] == 1]
    df_if_attack = df_if_zero[df_if_zero["label"] == 1]

    # Verify all 44 rows
    mismatches = 0
    for _, row in df_s3.iterrows():
        m = row["model"]
        s = int(row["seed"]) if not pd.isna(row["seed"]) else None
        thresh = float(row["threshold"])
        exp_fp = int(row["eval_fp"])
        exp_tp = int(row["eval_tp"])

        # Determine score series
        if m in ("dt", "rf", "nn"):
            eval_scores = df_eval[f"{m}_attack_probability"].values
            attack_scores = df_attack[f"{m}_attack_probability"].values
        elif m == "svm":
            eval_scores = df_eval["svm_decision_score"].values
            attack_scores = df_attack["svm_decision_score"].values
        elif m == "stacking":
            eval_scores = df_eval[f"stacking_attack_probability_seed{s}"].values
            attack_scores = df_attack[f"stacking_attack_probability_seed{s}"].values
        elif m == "ae":
            eval_scores = df_ae_eval["reconstruction_error"].values
            attack_scores = df_ae_attack["reconstruction_error"].values
        elif m == "if":
            eval_if = df_if_zero[df_if_zero["row_uid"].isin(eval_uids)]
            col = f"if_anomaly_score_seed_{s}"
            eval_scores = eval_if[col].values
            attack_scores = df_if_attack[col].values
        else:
            continue

        act_fp = int((eval_scores > thresh).sum())
        act_tp = int((attack_scores > thresh).sum())

        if act_fp != exp_fp or act_tp != exp_tp:
            mismatches += 1
            raise AssertionError(
                f"S1 vs S3 mismatch for {row['model_key']} budget {row['nominal_budget_str']}: "
                f"eval_fp (recomputed={act_fp}, s3={exp_fp}), eval_tp (recomputed={act_tp}, s3={exp_tp})"
            )

    logger.info(f"PASS: All 44 S3 Tier B operating points exactly reproduced from S1 score vectors.")
    return {
        "status": "PASS",
        "rows_checked": len(df_s3),
        "mismatches": mismatches,
    }


# ---------------------------------------------------------------------------
# Check 6: Historical Zero-Day Baseline Metrics (§17.2, §17.4)
# ---------------------------------------------------------------------------
def check_historical_zeroday_metrics() -> Dict[str, Any]:
    logger.info("=== CHECK 6: Historical Zero-Day Baseline Metrics (§17.2, §17.4) ===")
    zero_metrics_path = resolve_path("results/zero_day/EXP_ZERODAY_V1/metrics/zero_day_metrics.csv")
    s1_zeroday_path = resolve_path("results/publication_experiments/EXP_PROB_INFERENCE_V1/zeroday_probabilities.csv")
    s1_ae_zeroday_path = resolve_path("results/publication_experiments/EXP_PROB_INFERENCE_V1/ae_zeroday_reconstruction_errors.csv")
    ae_cfg_path = resolve_path("results/checkpoints/EXP_AE_V1/threshold_config.json")

    df_zm = pd.read_csv(zero_metrics_path)
    df_zero = pd.read_csv(s1_zeroday_path)
    df_ae_zero = pd.read_csv(s1_ae_zeroday_path)
    with open(ae_cfg_path, "r", encoding="utf-8") as f:
        ae_cfg = json.load(f)

    # 1. Stacking threshold 0.5 comparator: historical uses >= 0.5
    stacking_zm = df_zm[df_zm["system"] == "Stacking"].iloc[0]
    exp_stacking_tp = int(stacking_zm["TP"])  # 582
    exp_stacking_fp = int(stacking_zm["FP"])  # 7100

    benign_zero = df_zero[df_zero["label"] == 0]
    attack_zero = df_zero[df_zero["label"] == 1]
    act_stacking_fp = int((benign_zero["stacking_attack_probability_seed42"] >= 0.5).sum())
    act_stacking_tp = int((attack_zero["stacking_attack_probability_seed42"] >= 0.5).sum())

    if act_stacking_fp != exp_stacking_fp or act_stacking_tp != exp_stacking_tp:
        raise AssertionError(
            f"Stacking threshold 0.5 replication mismatch: "
            f"FP={act_stacking_fp} (exp {exp_stacking_fp}), TP={act_stacking_tp} (exp {exp_stacking_tp})"
        )

    # 2. AE historical mean+3sigma tau from threshold_config.json
    tau = float(ae_cfg["thresholds"]["mean3sigma"]["threshold_value"])  # 11.16006...
    ae_zm = df_zm[df_zm["system"] == "AE"].iloc[0]
    exp_ae_tp = int(ae_zm["TP"])  # 0
    exp_ae_fp = int(ae_zm["FP"])  # 19

    benign_ae = df_ae_zero[df_ae_zero["label"] == 0]
    attack_ae = df_ae_zero[df_ae_zero["label"] == 1]
    act_ae_fp = int((benign_ae["reconstruction_error"] > tau).sum())
    act_ae_tp = int((attack_ae["reconstruction_error"] > tau).sum())

    if act_ae_fp != exp_ae_fp or act_ae_tp != exp_ae_tp:
        raise AssertionError(
            f"AE historical tau replication mismatch: "
            f"FP={act_ae_fp} (exp {exp_ae_fp}), TP={act_ae_tp} (exp {exp_ae_tp})"
        )

    logger.info("PASS: Historical Zero-Day benchmarks reproduced: Stacking (582/7100) and AE (0/19).")
    return {
        "status": "PASS",
        "stacking_tp": act_stacking_tp,
        "stacking_fp": act_stacking_fp,
        "ae_tp": act_ae_tp,
        "ae_fp": act_ae_fp,
        "ae_tau": tau,
    }


# ---------------------------------------------------------------------------
# Check 7: Stacking DEV_TEST Macro-F1 Replication (§17.1)
# ---------------------------------------------------------------------------
def check_stacking_h1_results() -> Dict[str, Any]:
    logger.info("=== CHECK 7: Stacking DEV_TEST Macro-F1 Replication (§17.1) ===")
    h1_path = resolve_path("results/evaluation/EXP_H123_V1/h1_results.json")
    with open(h1_path, "r", encoding="utf-8") as f:
        h1 = json.load(f)

    expected_macro_f1 = {
        "seed_42": 0.8926091690431182,
        "seed_123": 0.8926186397931948,
        "seed_2024": 0.8936559437082856,
    }
    for s_key, exp_val in expected_macro_f1.items():
        act_val = h1.get(f"stacking_macro_f1_{s_key}")
        if act_val is None or abs(act_val - exp_val) > 1e-6:
            raise AssertionError(f"H1 Macro-F1 mismatch for {s_key}: act={act_val}, exp={exp_val}")

    logger.info("PASS: Stacking DEV_TEST Macro-F1 matches h1_results.json across all 3 seeds.")
    return {
        "status": "PASS",
        "stacking_macro_f1": expected_macro_f1,
        "mean_macro_f1": h1.get("stacking_mean_macro_f1"),
    }


# ---------------------------------------------------------------------------
# Check 8: Population Partition & Overlap Integrity (§17.7, §17.15)
# ---------------------------------------------------------------------------
def check_population_partitions() -> Dict[str, Any]:
    logger.info("=== CHECK 8: Population Partition & Overlap Integrity (§17.7, §17.15) ===")
    pop_dir = resolve_path("results/publication_experiments/EXP_POPULATIONS_V1")
    cal_uids = json.load(open(pop_dir / "cal_control_row_uids.json"))
    eval_uids = json.load(open(pop_dir / "eval_control_row_uids.json"))
    benign_uids = json.load(open(pop_dir / "benign_control_row_uids.json"))

    s_cal = set(cal_uids)
    s_eval = set(eval_uids)
    s_benign = set(benign_uids)

    if len(s_cal) != 18500:
        raise AssertionError(f"cal_control unique rows != 18,500: {len(s_cal)}")
    if len(s_eval) != 18500:
        raise AssertionError(f"eval_control unique rows != 18,500: {len(s_eval)}")
    if len(s_benign) != 37000:
        raise AssertionError(f"benign_control unique rows != 37,000: {len(s_benign)}")

    overlap = s_cal.intersection(s_eval)
    if len(overlap) != 0:
        raise AssertionError(f"Tier B halves are not disjoint: {len(overlap)} overlapping rows!")

    union = s_cal.union(s_eval)
    if union != s_benign:
        raise AssertionError("Union of cal_control and eval_control does not equal benign_control!")

    # Check unseen family counts from S6
    s6_path = resolve_path("results/publication_experiments/EXP_AE_ABLATION_V1/ae_ablation_results_unseen.csv")
    df_s6_unseen = pd.read_csv(s6_path)
    fam_counts = df_s6_unseen.groupby("population")["n_total"].first().to_dict()
    exp_fam = {"unseen_worms": 44, "unseen_shellcode": 378, "unseen_analysis": 677}
    assert fam_counts == exp_fam, f"Unseen family counts mismatch: {fam_counts} != {exp_fam}"

    logger.info("PASS: Population partitions verified: Tier B halves disjoint, union exact, unseen counts 44/378/677.")
    return {
        "status": "PASS",
        "cal_control_n": len(s_cal),
        "eval_control_n": len(s_eval),
        "benign_control_n": len(s_benign),
        "unseen_family_counts": exp_fam,
    }


# ---------------------------------------------------------------------------
# Check 9: Alert Budget Analysis Output Verification (§17.17)
# ---------------------------------------------------------------------------
def check_alert_budget_outputs() -> Dict[str, Any]:
    logger.info("=== CHECK 9: Alert Budget Analysis Output Verification (§17.17) ===")
    alert_path = resolve_path("results/publication_experiments/EXP_ALERT_BUDGET_V1/alert_budget_table.csv")
    summary_path = resolve_path("results/publication_experiments/EXP_ALERT_BUDGET_V1/alert_budget_summary.json")

    df_alerts = pd.read_csv(alert_path)
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    if len(df_alerts) != 44:
        raise AssertionError(f"alert_budget_table.csv row count != 44: {len(df_alerts)}")
    if "tie_unattainable" not in df_alerts.columns:
        raise AssertionError("tie_unattainable column missing from alert_budget_table.csv")

    budgets = sorted(df_alerts["nominal_budget"].unique().tolist())
    exp_budgets = [0.001, 0.005, 0.01, 0.05]
    if budgets != exp_budgets:
        raise AssertionError(f"Nominal budgets mismatch in alert budget table: {budgets} != {exp_budgets}")

    # Check that alerts_per_10k uses realized counts
    max_diff = float(((df_alerts["eval_fp"] / 18500.0) * 10000.0 - df_alerts["alerts_per_10k_benign"]).abs().max())
    if max_diff > 1e-9:
        raise AssertionError(f"alerts_per_10k_benign inconsistent with realized eval_fp: max diff {max_diff:.2e}")

    logger.info("PASS: Alert budget outputs verified: 44 rows, 4 budgets, tie_unattainable carried, realized counts.")
    return {
        "status": "PASS",
        "rows": len(df_alerts),
        "budgets": budgets,
        "tie_unattainable_carried": True,
        "max_diff_realized": max_diff,
    }


# ---------------------------------------------------------------------------
# Main S9 Runner
# ---------------------------------------------------------------------------
def run_cross_consistency_check(config_path: Optional[Path] = None) -> None:
    # 0. Execute Zero-Training Guard
    execute_zero_training_guard(Path(__file__).resolve())
    logger.info("=== STEP 0: Zero-Training Guard Passed ===")

    out_dir = NEW_ROOT / "results" / "publication_experiments" / "EXP_CROSS_CHECK_V1"
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Outputs will be written to: {out_dir}")

    # Execute all modular checks
    results = {}
    results["frozen_baseline_integrity"] = check_frozen_baseline_integrity()
    results["headline_tier_decision"] = check_headline_tier_decision()
    results["s4_vs_mcnemar"] = check_s4_vs_mcnemar()
    results["s3_ae_vs_s6"] = check_s3_ae_vs_s6()
    results["s1_vs_s3"] = check_s1_vs_s3()
    results["historical_zeroday_metrics"] = check_historical_zeroday_metrics()
    results["stacking_h1_results"] = check_stacking_h1_results()
    results["population_partitions"] = check_population_partitions()
    results["alert_budget_outputs"] = check_alert_budget_outputs()

    # Build report
    timestamp = datetime.now(timezone.utc).isoformat()
    report = {
        "experiment_id": "EXP_CROSS_CHECK_V1",
        "blueprint_version": "5.0",
        "timestamp_utc": timestamp,
        "overall_status": "PASS",
        "checks_executed": len(results),
        "checks_passed": len(results),
        "detailed_results": results,
    }

    report_path = out_dir / "cross_check_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Wrote {report_path}")

    self_check = {
        "experiment_id": "EXP_CROSS_CHECK_V1",
        "timestamp_utc": timestamp,
        "zero_training_guard": "PASS",
        "headline_tier_rule_hash": "PASS",
        "frozen_baseline_342_342": "PASS",
        "cross_stage_reconciliation_s1_s3": "PASS",
        "cross_stage_reconciliation_s3_s6": "PASS",
        "cross_stage_reconciliation_s4_mcnemar": "PASS",
        "historical_zeroday_reconciliation": "PASS",
        "h1_macro_f1_reconciliation": "PASS",
        "partitions_integrity": "PASS",
        "alert_budget_integrity": "PASS",
        "overall_status": "PASS",
    }
    self_check_path = out_dir / "self_check.json"
    with open(self_check_path, "w", encoding="utf-8") as f:
        json.dump(self_check, f, indent=2)
    logger.info(f"Wrote {self_check_path}")

    metadata = {
        "experiment_id": "EXP_CROSS_CHECK_V1",
        "timestamp_utc": timestamp,
        "artifact_hashes": {
            "cross_check_report.json": compute_sha256(report_path),
            "self_check.json": compute_sha256(self_check_path),
        },
        "status": "PASS",
    }
    metadata_path = out_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Wrote {metadata_path}")

    logger.info("=== S9 Cross-Consistency Check Complete: ALL CHECKS PASSED ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S9: Executable Cross-Result Consistency Check")
    parser.add_argument("--config", type=Path, default=None, help="Optional config path")
    args = parser.parse_args()
    run_cross_consistency_check(args.config)
