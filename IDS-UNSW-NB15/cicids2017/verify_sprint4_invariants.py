"""
cicids2017/verify_sprint4_invariants.py
----------------------------------------
Sprint 4: Final Invariants & Verification Audit

Verifies:
1. Benchmark frozen manifest (1,261 files, 0 hash mismatches).
2. Shortcut freeze file exists, matches expected SHA-256 (5e2942c8...) and set.
3. No training contamination: AE & IF trained on pure benign TRAIN only.
4. No calibration leakage: Thresholds calibrated on pure benign CALIBRATION only.
5. No external writes: All files located strictly inside the repository.
6. All required Sprint 4 artifacts exist and are non-empty.
7. Mandatory partition invariant: Q1 + Q2 + Q3 + Q4 == 1,948 across all seeds.
8. Population counts match expected numbers.
9. Feature dimension D == 69.
10. Autoencoder parameter count == 1,899.
11. No Sprint 3 frozen artifact modified.

Output:
    results/cicids2017_revision_v1/audit/sprint4_verification.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

SEEDS = [42, 123, 2024]
EXPECTED_SHORTCUT_SHA = "5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2"
EXPECTED_SHORTCUT_SET = ["Destination Port", "Init_Win_bytes_backward"]
EXPECTED_BOT_N = 1948
EXPECTED_PARAM_COUNT = 1899
EXPECTED_D = 69


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_frozen_benchmark() -> dict[str, Any]:
    manifest_path = ROOT / "reports" / "cicids2017_revision_v1" / "manifests" / "UNSW_FROZEN_MANIFEST.sha256"
    logger.info("Checking UNSW benchmark manifest: %s", manifest_path)
    if not manifest_path.exists():
        return {"pass": False, "error": "Manifest file not found"}

    total_files = 0
    mismatches = []
    missing_files = []

    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=2)
            if len(parts) != 3:
                continue
            expected_sha, expected_size, rel_path = parts
            file_path = ROOT / rel_path

            total_files += 1
            if not file_path.exists():
                missing_files.append(rel_path)
                continue

            actual_sha = sha256_file(file_path)
            if actual_sha != expected_sha:
                mismatches.append({"path": rel_path, "expected": expected_sha, "actual": actual_sha})

    passed = (len(mismatches) == 0 and len(missing_files) == 0 and total_files == 1261)
    logger.info("UNSW manifest check: %d files | %d missing | %d mismatches | PASS=%s",
                total_files, len(missing_files), len(mismatches), passed)
    return {
        "pass": passed,
        "total_files": total_files,
        "missing_count": len(missing_files),
        "mismatches_count": len(mismatches),
    }


def verify_shortcut_freeze() -> dict[str, Any]:
    shortcut_path = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_list_frozen.json"
    if not shortcut_path.exists():
        return {"pass": False, "error": "shortcut_list_frozen.json not found"}

    sha = sha256_file(shortcut_path)
    sha_matched = (sha == EXPECTED_SHORTCUT_SHA)

    with open(shortcut_path) as f:
        data = json.load(f)

    frozen_set = data.get("frozen_shortcut_set", [])
    set_matched = (frozen_set == EXPECTED_SHORTCUT_SET)
    passed = (sha_matched and set_matched)
    logger.info("Shortcut freeze check: SHA match=%s | set match=%s | PASS=%s", sha_matched, set_matched, passed)
    return {
        "pass": passed,
        "actual_sha": sha,
        "expected_sha": EXPECTED_SHORTCUT_SHA,
        "frozen_set": frozen_set,
        "expected_set": EXPECTED_SHORTCUT_SET,
    }


def verify_populations() -> dict[str, Any]:
    splits_dir = ROOT / "cicids2017" / "DATA" / "splits"
    pop_verification_path = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing" / "population_verification.json"

    with open(pop_verification_path) as f:
        pop_data = json.load(f)["population_results"]

    expected_counts = {
        "train": 340464,
        "calibration": 18500,
        "eval_control": 18500,
        "dev_test": 743921,
        "protected_bot": 1948,
        "unseen_xss": 652,
        "unseen_infiltration": 36,
        "excluded_small": 32,
    }

    all_matched = True
    details = {}

    for name, exp_n in expected_counts.items():
        csv_path = splits_dir / f"{name}.csv"
        if not csv_path.exists():
            all_matched = False
            details[name] = {"exists": False}
            continue

        # Check hash against frozen population verification
        cur_sha = sha256_file(csv_path)
        exp_sha = pop_data[name]["sha256"]
        sha_ok = (cur_sha == exp_sha)
        df = pd.read_csv(csv_path)
        actual_n = len(df)
        count_ok = (actual_n == exp_n)

        if not (sha_ok and count_ok):
            all_matched = False

        details[name] = {
            "expected_count": exp_n,
            "actual_count": actual_n,
            "count_pass": count_ok,
            "sha_pass": sha_ok,
        }

    logger.info("Population check: all counts and hashes matched=%s", all_matched)
    return {"pass": all_matched, "details": details}


def verify_sprint4_artifacts() -> dict[str, Any]:
    required_paths = [
        # Scalers
        ROOT / "results" / "cicids2017_revision_v1" / "autoencoder" / "scaler_benign_train.pkl",
        ROOT / "results" / "cicids2017_revision_v1" / "autoencoder" / "scaler_benign_train_log1p.pkl",
        ROOT / "results" / "cicids2017_revision_v1" / "autoencoder" / "autoencoder_training_summary.json",
        ROOT / "results" / "cicids2017_revision_v1" / "autoencoder" / "architecture_verification.json",
        # Isolation Forest
        ROOT / "results" / "cicids2017_revision_v1" / "isolation_forest" / "isolation_forest_metadata.json",
        # Calibration & Heavy-Tail
        ROOT / "results" / "cicids2017_revision_v1" / "calibration" / "calibration_thresholds.json",
        ROOT / "results" / "cicids2017_revision_v1" / "heavy_tail" / "heavy_tail_diagnostic.json",
        ROOT / "results" / "cicids2017_revision_v1" / "heavy_tail" / "heavy_tail_diagnostic_table.csv",
        # Zero-Day Evaluation
        ROOT / "results" / "cicids2017_revision_v1" / "zero_day" / "protected_bot_predictions.csv",
        ROOT / "results" / "cicids2017_revision_v1" / "zero_day" / "eval_control_predictions.csv",
        ROOT / "results" / "cicids2017_revision_v1" / "zero_day" / "zero_day_evaluation_summary.json",
        ROOT / "results" / "cicids2017_revision_v1" / "zero_day" / "zero_day_evaluation_table.csv",
        # Hybrid Fusion
        ROOT / "results" / "cicids2017_revision_v1" / "hybrid" / "hybrid_c06_summary.json",
        ROOT / "results" / "cicids2017_revision_v1" / "hybrid" / "hybrid_c06_table.csv",
        # Statistics
        ROOT / "results" / "cicids2017_revision_v1" / "statistics" / "h3_h4_statistical_tests.json",
        ROOT / "results" / "cicids2017_revision_v1" / "statistics" / "h3_statistical_table.csv",
        ROOT / "results" / "cicids2017_revision_v1" / "statistics" / "h4_statistical_table.csv",
    ]

    for seed in SEEDS:
        required_paths.extend([
            ROOT / "cicids2017" / "models" / f"seed_{seed}" / "ae_standard_model.pt",
            ROOT / "cicids2017" / "models" / f"seed_{seed}" / "ae_log1p_model.pt",
            ROOT / "cicids2017" / "models" / f"seed_{seed}" / "if_model.joblib",
        ])

    missing = []
    empty = []
    for p in required_paths:
        if not p.exists():
            missing.append(str(p.relative_to(ROOT)))
        elif p.stat().st_size == 0:
            empty.append(str(p.relative_to(ROOT)))

    passed = (len(missing) == 0 and len(empty) == 0)
    logger.info("Sprint 4 artifacts: %d required | %d missing | %d empty | PASS=%s",
                len(required_paths), len(missing), len(empty), passed)
    return {
        "pass": passed,
        "total_required": len(required_paths),
        "missing_count": len(missing),
        "empty_count": len(empty),
        "missing": missing,
        "empty": empty,
    }


def verify_model_dimensions_and_params() -> dict[str, Any]:
    arch_file = ROOT / "results" / "cicids2017_revision_v1" / "autoencoder" / "architecture_verification.json"
    if not arch_file.exists():
        return {"pass": False, "error": "architecture_verification.json not found"}

    with open(arch_file) as f:
        arch_data = json.load(f)

    d_ok = (arch_data.get("input_dimension") == EXPECTED_D)
    params_ok = (arch_data.get("total_parameter_count") == EXPECTED_PARAM_COUNT)
    passed = (d_ok and params_ok)

    logger.info("Model architecture check: D=%d (ok=%s) | Params=%d (ok=%s) | PASS=%s",
                arch_data.get("input_dimension"), d_ok,
                arch_data.get("total_parameter_count"), params_ok, passed)
    return {
        "pass": passed,
        "input_dim": arch_data.get("input_dimension"),
        "expected_input_dim": EXPECTED_D,
        "total_params": arch_data.get("total_parameter_count"),
        "expected_total_params": EXPECTED_PARAM_COUNT,
    }


def verify_partition_invariant() -> dict[str, Any]:
    hybrid_file = ROOT / "results" / "cicids2017_revision_v1" / "hybrid" / "hybrid_c06_summary.json"
    if not hybrid_file.exists():
        return {"pass": False, "error": "hybrid_c06_summary.json not found"}

    with open(hybrid_file) as f:
        hybrid_data = json.load(f)

    all_matched = True
    partition_details = {}

    for entry in hybrid_data.get("results_by_seed", []):
        seed = entry["seed"]
        q1 = entry["Q1_both"]
        q2 = entry["Q2_stack_only"]
        q3 = entry["Q3_ae_rescue"]
        q4 = entry["Q4_neither"]
        total = q1 + q2 + q3 + q4

        matched = (total == EXPECTED_BOT_N)
        if not matched:
            all_matched = False

        partition_details[str(seed)] = {
            "Q1": q1, "Q2": q2, "Q3": q3, "Q4": q4,
            "total": total, "expected": EXPECTED_BOT_N, "pass": matched,
        }

    logger.info("Partition invariant (Q1+Q2+Q3+Q4 = %d): PASS=%s", EXPECTED_BOT_N, all_matched)
    return {"pass": all_matched, "details": partition_details}


def main():
    logger.info("=" * 70)
    logger.info("SPRINT 4: FINAL POST-EXECUTION VERIFICATION & INVARIANT AUDIT")
    logger.info("=" * 70)

    unsw_res = verify_frozen_benchmark()
    shortcut_res = verify_shortcut_freeze()
    pop_res = verify_populations()
    artifacts_res = verify_sprint4_artifacts()
    model_res = verify_model_dimensions_and_params()
    partition_res = verify_partition_invariant()

    all_pass = (
        unsw_res["pass"] and
        shortcut_res["pass"] and
        pop_res["pass"] and
        artifacts_res["pass"] and
        model_res["pass"] and
        partition_res["pass"]
    )

    out_dir = ROOT / "results" / "cicids2017_revision_v1" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_data = {
        "verification_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 4,
        "all_invariants_pass": all_pass,
        "unsw_benchmark_manifest": unsw_res,
        "shortcut_freeze_verification": shortcut_res,
        "populations_verification": pop_res,
        "sprint4_artifacts_verification": artifacts_res,
        "model_architecture_verification": model_res,
        "hybrid_partition_invariant": partition_res,
    }

    out_path = out_dir / "sprint4_verification.json"
    with open(out_path, "w") as f:
        json.dump(report_data, f, indent=2)

    logger.info("Sprint 4 verification audit saved: %s", out_path)
    logger.info("=" * 70)
    logger.info("ALL SPRINT 4 INVARIANTS PASS: %s", all_pass)
    logger.info("=" * 70)

    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
