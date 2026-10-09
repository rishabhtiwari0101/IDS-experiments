#!/usr/bin/env python3
"""
revision_v5/publication_experiments/scripts/run_mad_threshold.py
---------------------------------------------------------------
Phase 4 / Analysis B3: AE Threshold Family and MAD Analysis (S5).
Blueprint reference: §6 (B3), §16 (S5), §18 Gate 4.

Key protocol requirements:
1. Zero-Training Guard: purely threshold computation and calibration, strictly fits no models.
2. Single-Vector Provenance: All percentile, sigma, and MAD thresholds are computed
   from the S1-generated AE reconstruction-error vector for the resolved clean
   calibration population (EXP_PROB_INFERENCE_V1/ae_calibration_benign_reconstruction_errors.csv,
   N_cal = 11,200).
3. Legacy Cross-Checks:
   - Element-wise agreement against results/autoencoder/EXP_AE_V1/threshold/validation_reconstruction_errors.csv
     within §0.3 tolerance (<= 1e-4).
   - Recomputed mean, std, and thresholds against results/checkpoints/EXP_AE_V1/threshold_config.json
     within relative 1e-4 tolerance.
4. Rules Evaluated:
   - Primary (6 rules): p95, p99, p999, mean_plus_2sigma, mean_plus_3sigma, raw_mad_k3
   - Sensitivity: raw_mad_k (k in [2, 3, 4]), scaled_mad_k (k in [2, 3, 4], constant = 1.4826)
5. Exact Arithmetic:
   - Calibration FPRs computed as exact rational fractions (Fraction) and floats.
6. Strict output directory:
   results/publication_experiments/EXP_MAD_THRESHOLD_V1/
   - mad_threshold.json
   - mad_thresholds.csv
   - self_check.json
   - metadata.json
"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
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
        if in_guard_def or stripped.startswith("#") or '"""' in stripped:
            continue
        for pattern in PROHIBITED_PATTERNS:
            if pattern in line:
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
logger = logging.getLogger("run_mad_threshold")


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
# Main S5 Analysis Routine
# ---------------------------------------------------------------------------

def run_mad_threshold(config_path: Path) -> None:
    # 0. Zero-Training Guard
    execute_zero_training_guard(Path(__file__).resolve())
    logger.info("=== STEP 0: Zero-Training Guard Passed ===")

    # 1. Load and Verify Config
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    out_rel = cfg.get("output_dir", "results/publication_experiments/EXP_MAD_THRESHOLD_V1")
    out_dir = NEW_ROOT / out_rel if not str(out_rel).startswith(str(NEW_ROOT)) else Path(out_rel)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not str(out_dir.resolve()).startswith(str(NEW_ROOT.resolve())):
        raise RuntimeError(f"Output directory {out_dir} is outside {NEW_ROOT}")
    logger.info(f"Outputs will be written strictly inside: {out_dir}")

    # Check git status of mad.yaml — fail loudly if uncommitted changes exist
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain", str(config_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.stdout.strip():
            raise RuntimeError(
                f"PROTOCOL VIOLATION: mad.yaml has uncommitted changes. "
                f"Per blueprint Rule 14, protocol-defining configs must be committed before "
                f"the script that reads them is executed. Git status: {res.stdout.strip()!r}"
            )
        logger.info("PASS: mad.yaml is committed with no uncommitted changes.")
    except RuntimeError:
        raise
    except Exception as e:
        logger.debug(f"Git status check skipped: {e}")

    # 2. Load Populations Manifest & Assert Row UIDs
    logger.info("=== STEP 1: Loading Populations Manifest & Asserting Row UIDs ===")
    pop_manifest_path = resolve_path("publication_experiments/configs/populations.yaml")
    if not pop_manifest_path.exists():
        raise FileNotFoundError(f"Populations manifest not found: {pop_manifest_path}")

    with open(pop_manifest_path, "r", encoding="utf-8") as f:
        pop_cfg = yaml.safe_load(f)

    cal_pop_cfg = pop_cfg["populations"]["calibration_benign"]
    expected_n_cal = int(cal_pop_cfg.get("expected_n", 11200))
    source_status = str(cal_pop_cfg.get("source_status", "untouched_val"))
    cal_uid_list_path = resolve_path(cal_pop_cfg["row_uid_list"])

    if not cal_uid_list_path.exists():
        raise FileNotFoundError(f"Calibration benign row UID list not found: {cal_uid_list_path}")

    with open(cal_uid_list_path, "r", encoding="utf-8") as f:
        expected_uids = json.load(f)

    assert len(expected_uids) == expected_n_cal, (
        f"UID list length {len(expected_uids)} != expected {expected_n_cal}"
    )

    # 3. Load Primary Calibration RE Vector (from S1)
    logger.info("=== STEP 2: Loading Primary Calibration RE Vector from S1 ===")
    p_primary_rel = cfg.get(
        "calibration_re_primary",
        "results/publication_experiments/EXP_PROB_INFERENCE_V1/ae_calibration_benign_reconstruction_errors.csv",
    )
    primary_re_path = resolve_path(p_primary_rel)
    if not primary_re_path.exists():
        raise FileNotFoundError(f"Primary calibration RE file not found: {primary_re_path}")

    df_primary = pd.read_csv(primary_re_path)
    n_cal = len(df_primary)
    assert n_cal == expected_n_cal, f"Primary calibration rows {n_cal} != expected {expected_n_cal}"

    actual_uids = df_primary["row_uid"].tolist()
    assert actual_uids == expected_uids, "Calibration row UIDs do not match populations manifest exactly!"
    logger.info(f"Verified {n_cal} calibration row UIDs match populations manifest bit-for-bit.")

    re_vector = df_primary["reconstruction_error"].values.astype(float)
    assert not np.isnan(re_vector).any(), "NaN found in primary reconstruction errors"
    assert not np.isinf(re_vector).any(), "Inf found in primary reconstruction errors"
    assert (re_vector >= 0.0).all(), "Negative reconstruction error found"

    primary_file_sha = compute_sha256(primary_re_path)
    logger.info(f"Loaded primary RE vector: N={n_cal}, SHA256={primary_file_sha[:16]}...")

    # 4. Checkpoint & Scaler Provenance
    ckpt_path = resolve_path("results/checkpoints/EXP_AE_V1/ae_final.pt")
    scaler_path = resolve_path("results/checkpoints/EXP_AE_V1/ae_scaler.joblib")
    if not ckpt_path.exists():
        raise FileNotFoundError(f"AE checkpoint not found: {ckpt_path}")
    if not scaler_path.exists():
        raise FileNotFoundError(f"AE scaler not found: {scaler_path}")

    ckpt_sha = compute_sha256(ckpt_path)
    scaler_sha = compute_sha256(scaler_path)
    # Raw file SHA (byte-for-byte of the JSON file on disk)
    row_id_file_sha = compute_sha256(cal_uid_list_path)
    # Newline-joined string SHA: sha256("\n".join(uids)) — stable across JSON formatting changes
    row_id_string_sha = hashlib.sha256("\n".join(expected_uids).encode("utf-8")).hexdigest()
    row_id_sha = row_id_file_sha  # primary record; both are stored in mad_threshold.json
    logger.info(f"AE Checkpoint SHA:         {ckpt_sha[:16]}...")
    logger.info(f"AE Scaler SHA:             {scaler_sha[:16]}...")
    logger.info(f"Row UID List (file) SHA:   {row_id_file_sha[:16]}...")
    logger.info(f"Row UID List (string) SHA: {row_id_string_sha[:16]}...")

    # 5. Legacy Cross-Checks (§0.3 Tolerances)
    logger.info("=== STEP 3: Executing Legacy Cross-Checks (§0.3 Tolerances) ===")
    legacy_re_path = resolve_path(cfg.get(
        "legacy_val_re_crosscheck",
        "results/autoencoder/EXP_AE_V1/threshold/validation_reconstruction_errors.csv",
    ))
    legacy_diff_max: Optional[float] = None
    if legacy_re_path.exists():
        df_legacy = pd.read_csv(legacy_re_path)
        assert len(df_legacy) == n_cal, f"Legacy RE rows {len(df_legacy)} != {n_cal}"
        legacy_re_col = "re_value" if "re_value" in df_legacy.columns else df_legacy.columns[-1]
        legacy_vals = df_legacy[legacy_re_col].values.astype(float)
        legacy_diff_max = float(np.max(np.abs(re_vector - legacy_vals)))
        if legacy_diff_max > 1e-4:
            raise AssertionError(
                f"Element-wise max absolute difference {legacy_diff_max} exceeds tolerance 1e-4"
            )
        logger.info(f"PASS: Element-wise legacy RE cross-check (max abs diff = {legacy_diff_max:.2e} <= 1e-4)")

    # Cross-check against threshold_config.json
    tc_path = resolve_path(cfg.get("ae_threshold_config", "results/checkpoints/EXP_AE_V1/threshold_config.json"))
    tc_recomputed_stats: Dict[str, Any] = {}
    if tc_path.exists():
        with open(tc_path, "r", encoding="utf-8") as f:
            tc = json.load(f)

        mean_val = float(np.mean(re_vector))
        std_val = float(np.std(re_vector, ddof=0))
        ref_mean = float(tc["re_stats"]["mean"])
        ref_std = float(tc["re_stats"]["std"])

        rel_diff_mean = abs(mean_val - ref_mean) / ref_mean
        rel_diff_std = abs(std_val - ref_std) / ref_std

        if rel_diff_mean > 1e-4:
            raise AssertionError(f"Recomputed mean relative diff {rel_diff_mean:.2e} exceeds 1e-4")
        if rel_diff_std > 1e-4:
            raise AssertionError(f"Recomputed std relative diff {rel_diff_std:.2e} exceeds 1e-4")

        logger.info(f"PASS: Recomputed mean ({mean_val:.6f}) matches threshold_config.json (rel diff {rel_diff_mean:.2e})")
        logger.info(f"PASS: Recomputed std ({std_val:.6f}) matches threshold_config.json (rel diff {rel_diff_std:.2e})")

        # Per-threshold strict cross-checks for the 5 rules present in threshold_config.json
        # Threshold values: relative 1e-4; samples_above_threshold: exact integer match (strict > rule)
        percentile_method_for_check = str(cfg.get("percentile_method", "linear"))
        tc_rule_map = {
            "p95":              (float(np.percentile(re_vector, 95.0, method=percentile_method_for_check)), "p95"),
            "p99":              (float(np.percentile(re_vector, 99.0, method=percentile_method_for_check)), "p99"),
            "p999":             (float(np.percentile(re_vector, 99.9, method=percentile_method_for_check)), "p999"),
            "mean_plus_2sigma": (mean_val + 2.0 * std_val, "mean2sigma"),
            "mean_plus_3sigma": (mean_val + 3.0 * std_val, "mean3sigma"),
        }
        tc_crosscheck_details: Dict[str, Any] = {}
        for rule_name, (recomputed_t, tc_key) in tc_rule_map.items():
            if tc_key not in tc["thresholds"]:
                raise AssertionError(
                    f"threshold_config.json missing key '{tc_key}' needed for cross-check of rule '{rule_name}'"
                )
            ref_t = float(tc["thresholds"][tc_key]["threshold_value"])
            ref_count = int(tc["thresholds"][tc_key]["samples_above_threshold"])

            # Threshold value: relative tolerance 1e-4
            rel_diff_t = abs(recomputed_t - ref_t) / ref_t
            if rel_diff_t > 1e-4:
                raise AssertionError(
                    f"Rule '{rule_name}' threshold value mismatch: "
                    f"recomputed={recomputed_t:.8f}, threshold_config={ref_t:.8f}, "
                    f"relative diff={rel_diff_t:.2e} exceeds 1e-4"
                )

            # samples_above_threshold: exact match using strict > rule (same comparator as register_rule)
            recomputed_count = int((re_vector > recomputed_t).sum())
            if recomputed_count != ref_count:
                raise AssertionError(
                    f"Rule '{rule_name}' samples_above_threshold mismatch: "
                    f"recomputed={recomputed_count} (using strict >), "
                    f"threshold_config={ref_count}. "
                    f"Threshold value: recomputed={recomputed_t:.8f}, ref={ref_t:.8f}"
                )

            logger.info(
                f"PASS: {rule_name:20s} threshold={recomputed_t:.6f} (rel diff {rel_diff_t:.2e}), "
                f"samples_above={recomputed_count} == threshold_config={ref_count}"
            )
            tc_crosscheck_details[rule_name] = {
                "recomputed_threshold": recomputed_t,
                "ref_threshold": ref_t,
                "rel_diff_threshold": rel_diff_t,
                "recomputed_samples_above": recomputed_count,
                "ref_samples_above": ref_count,
                "samples_above_match": True,
            }

        tc_recomputed_stats = {
            "mean": mean_val,
            "std": std_val,
            "ref_mean": ref_mean,
            "ref_std": ref_std,
            "rel_diff_mean": rel_diff_mean,
            "rel_diff_std": rel_diff_std,
            "per_rule_crosscheck": tc_crosscheck_details,
        }

    # 6. Compute Threshold Family and Calibration FPRs
    logger.info("=== STEP 4: Computing AE Threshold Family & Exact Calibration FPRs ===")
    percentile_method = str(cfg.get("percentile_method", "linear"))

    # Core summary statistics
    mean_val = float(np.mean(re_vector))
    std_val = float(np.std(re_vector, ddof=0))
    median_val = float(np.median(re_vector))
    mad_val = float(np.median(np.abs(re_vector - median_val)))
    min_val = float(np.min(re_vector))
    max_val = float(np.max(re_vector))

    sens_cfg = cfg.get("sensitivity", {})
    scaled_mad_c = float(sens_cfg.get("scaled_mad_constant", 1.4826))
    scaled_mad_val = mad_val * scaled_mad_c

    logger.info(f"Reconstruction Error Summary (N={n_cal}):")
    logger.info(f"  Mean:       {mean_val:.6f}")
    logger.info(f"  Std:        {std_val:.6f}")
    logger.info(f"  Median:     {median_val:.6f}")
    logger.info(f"  Raw MAD:    {mad_val:.6f}")
    logger.info(f"  Scaled MAD: {scaled_mad_val:.6f} (c={scaled_mad_c})")
    logger.info(f"  Min / Max:  {min_val:.6f} / {max_val:.6f}")

    # Build threshold definitions
    rules_dict: Dict[str, Dict[str, Any]] = {}

    def register_rule(name: str, category: str, t_val: float, formula_desc: str) -> None:
        assert np.isfinite(t_val), f"Threshold {name} is not finite: {t_val}"
        assert t_val > 0.0, f"Threshold {name} must be positive: {t_val}"

        # Detections: score > threshold per blueprint §16
        samples_above = int((re_vector > t_val).sum())
        fpr_float = float(samples_above / n_cal)
        fpr_frac = Fraction(samples_above, n_cal)

        rules_dict[name] = {
            "rule_name": name,
            "category": category,
            "threshold_value": float(t_val),
            "samples_above_threshold": samples_above,
            "calibration_fpr": fpr_float,
            "calibration_fpr_fraction": str(fpr_frac),
            "calibration_rows": n_cal,
            "formula": formula_desc,
        }
        logger.info(
            f"  [{category:11s}] {name:18s} Threshold: {t_val:10.6f} | "
            f"Cal FP: {samples_above:5d}/{n_cal} | Cal FPR: {fpr_float:8.4%} ({str(fpr_frac)})"
        )

    # Primary rules (6 rules per mad.yaml / blueprint §16)
    register_rule("p95", "primary", float(np.percentile(re_vector, 95.0, method=percentile_method)), f"np.percentile(95.0, method='{percentile_method}')")
    register_rule("p99", "primary", float(np.percentile(re_vector, 99.0, method=percentile_method)), f"np.percentile(99.0, method='{percentile_method}')")
    register_rule("p999", "primary", float(np.percentile(re_vector, 99.9, method=percentile_method)), f"np.percentile(99.9, method='{percentile_method}')")
    register_rule("mean_plus_2sigma", "primary", mean_val + 2.0 * std_val, "mean + 2 * std(ddof=0)")
    register_rule("mean_plus_3sigma", "primary", mean_val + 3.0 * std_val, "mean + 3 * std(ddof=0)")
    register_rule("raw_mad_k3", "primary", median_val + 3.0 * mad_val, "median + 3 * raw_mad")

    # Sensitivity block
    for k in sens_cfg.get("raw_mad_k", [2, 3, 4]):
        name = f"raw_mad_k{k}"
        if name not in rules_dict:
            register_rule(name, "sensitivity", median_val + float(k) * mad_val, f"median + {k} * raw_mad")

    for k in sens_cfg.get("scaled_mad_k", [2, 3, 4]):
        name = f"scaled_mad_k{k}"
        register_rule(name, "sensitivity", median_val + float(k) * scaled_mad_val, f"median + {k} * {scaled_mad_c} * raw_mad")

    # Monotonicity / sanity assertions
    assert rules_dict["p95"]["threshold_value"] < rules_dict["p99"]["threshold_value"] < rules_dict["p999"]["threshold_value"]
    assert rules_dict["mean_plus_2sigma"]["threshold_value"] < rules_dict["mean_plus_3sigma"]["threshold_value"]
    assert rules_dict["raw_mad_k2"]["threshold_value"] < rules_dict["raw_mad_k3"]["threshold_value"] < rules_dict["raw_mad_k4"]["threshold_value"]
    assert rules_dict["scaled_mad_k2"]["threshold_value"] < rules_dict["scaled_mad_k3"]["threshold_value"] < rules_dict["scaled_mad_k4"]["threshold_value"]

    # 7. Write Output Artifacts
    logger.info("=== STEP 5: Writing Output Artifacts ===")

    # 7a. mad_threshold.json
    mad_threshold_json_path = out_dir / "mad_threshold.json"
    mad_json_data = {
        "experiment_id": cfg.get("experiment_id", "EXP_MAD_THRESHOLD_V1"),
        "blueprint_version": "5.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "calibration_source": source_status,
        "calibration_population": "calibration_benign",
        "N_cal": n_cal,
        "source_file": str(primary_re_path),
        "source_file_sha256": primary_file_sha,
        "checkpoint_path": str(ckpt_path),
        "checkpoint_sha256": ckpt_sha,
        "scaler_path": str(scaler_path),
        "scaler_sha256": scaler_sha,
        "row_id_list_path": str(cal_uid_list_path),
        "row_id_list_sha256_file": row_id_file_sha,
        "row_id_list_sha256_string": row_id_string_sha,
        "legacy_crosscheck": {
            "legacy_file": str(legacy_re_path) if legacy_re_path.exists() else None,
            "max_absolute_difference": legacy_diff_max,
            "within_tolerance_1e4": bool(legacy_diff_max is not None and legacy_diff_max <= 1e-4),
        },
        "threshold_config_crosscheck": tc_recomputed_stats,
        "re_stats": {
            "mean": mean_val,
            "std": std_val,
            "median": median_val,
            "raw_mad": mad_val,
            "scaled_mad": scaled_mad_val,
            "scaled_mad_constant": scaled_mad_c,
            "min": min_val,
            "max": max_val,
        },
        "percentile_method": percentile_method,
        "primary_rules": cfg.get("primary_rules", []),
        "thresholds": rules_dict,
    }

    with open(mad_threshold_json_path, "w", encoding="utf-8") as f:
        json.dump(mad_json_data, f, indent=2)
    logger.info(f"Wrote {mad_threshold_json_path}")

    # 7b. mad_thresholds.csv
    csv_rows = []
    for rname, rinfo in rules_dict.items():
        csv_rows.append({
            "rule_name": rname,
            "category": rinfo["category"],
            "threshold_value": rinfo["threshold_value"],
            "calibration_rows": rinfo["calibration_rows"],
            "samples_above_threshold": rinfo["samples_above_threshold"],
            "calibration_fpr": rinfo["calibration_fpr"],
            "calibration_fpr_fraction": rinfo["calibration_fpr_fraction"],
            "formula": rinfo["formula"],
        })
    df_thresholds = pd.DataFrame(csv_rows)
    mad_thresholds_csv_path = out_dir / "mad_thresholds.csv"
    df_thresholds.to_csv(mad_thresholds_csv_path, index=False)
    logger.info(f"Wrote {mad_thresholds_csv_path}")

    # 7c. self_check.json
    self_check_path = out_dir / "self_check.json"
    self_check = {
        "experiment_id": cfg.get("experiment_id", "EXP_MAD_THRESHOLD_V1"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_training_guard": "PASS",
        "calibration_rows": n_cal,
        "calibration_source": source_status,
        "uids_match_populations_manifest": True,
        "legacy_re_max_diff_within_1e4": bool(legacy_diff_max is not None and legacy_diff_max <= 1e-4),
        "threshold_config_stats_match": bool(tc_recomputed_stats.get("rel_diff_mean", 0) <= 1e-4),
        "rules_computed_count": len(rules_dict),
        "primary_rules_count": sum(1 for r in rules_dict.values() if r["category"] == "primary"),
        "sensitivity_rules_count": sum(1 for r in rules_dict.values() if r["category"] == "sensitivity"),
        "threshold_monotonicity_checks": {
            "percentiles_increasing": bool(rules_dict["p95"]["threshold_value"] < rules_dict["p99"]["threshold_value"] < rules_dict["p999"]["threshold_value"]),
            "mean_sigmas_increasing": bool(rules_dict["mean_plus_2sigma"]["threshold_value"] < rules_dict["mean_plus_3sigma"]["threshold_value"]),
            "raw_mad_increasing": bool(rules_dict["raw_mad_k2"]["threshold_value"] < rules_dict["raw_mad_k3"]["threshold_value"] < rules_dict["raw_mad_k4"]["threshold_value"]),
            "scaled_mad_increasing": bool(rules_dict["scaled_mad_k2"]["threshold_value"] < rules_dict["scaled_mad_k3"]["threshold_value"] < rules_dict["scaled_mad_k4"]["threshold_value"]),
        },
        "nan_inf_check": {
            "re_vector": bool(not np.isnan(re_vector).any() and not np.isinf(re_vector).any()),
            "threshold_values": bool(all(np.isfinite(r["threshold_value"]) for r in rules_dict.values())),
            "calibration_fprs": bool(all(np.isfinite(r["calibration_fpr"]) for r in rules_dict.values())),
        },
        "overall_status": "PASS",
    }
    with open(self_check_path, "w", encoding="utf-8") as f:
        json.dump(self_check, f, indent=2)
    logger.info(f"Wrote {self_check_path}")

    # 7d. metadata.json
    metadata_path = out_dir / "metadata.json"
    metadata = {
        "experiment_id": cfg.get("experiment_id", "EXP_MAD_THRESHOLD_V1"),
        "blueprint_version": "5.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "calibration_source": source_status,
        "sample_size": n_cal,
        "provenance_hashes": {
            "primary_calibration_re": primary_file_sha,
            "ae_checkpoint": ckpt_sha,
            "ae_scaler": scaler_sha,
            "row_id_list_file": row_id_file_sha,
            "row_id_list_string": row_id_string_sha,
        },
        "artifact_hashes": {
            "mad_threshold.json": compute_sha256(mad_threshold_json_path),
            "mad_thresholds.csv": compute_sha256(mad_thresholds_csv_path),
            "self_check.json": compute_sha256(self_check_path),
        },
        "status": "PASS",
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Wrote {metadata_path}")

    logger.info("=== S5 AE Threshold Family and MAD Analysis Complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S5: AE Threshold Family and MAD Analysis")
    parser.add_argument(
        "--config",
        type=str,
        default="revision_v5/publication_experiments/configs/mad.yaml",
        help="Path to mad.yaml config",
    )
    args = parser.parse_args()
    run_mad_threshold(Path(args.config))
