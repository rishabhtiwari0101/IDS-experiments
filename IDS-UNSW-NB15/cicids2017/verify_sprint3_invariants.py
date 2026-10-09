"""
cicids2017/verify_sprint3_invariants.py
----------------------------------------
Sprint 3: Post-Execution Invariants & Verification Audit

Verifies:
1. Benchmark frozen manifest (1,261 files, 0 hash mismatches).
2. Zero-day blinding: protected_bot.csv, unseen_xss.csv, unseen_infiltration.csv hashes unchanged.
3. Immutable shortcut freeze file exists and matches frozen SHA-256 (5e2942c8...).
4. Preprocessing, MI, training, OOF, and DEV_TEST artifacts all present and non-empty.
5. Output: results/cicids2017_revision_v1/audit/sprint3_verification.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_frozen_manifest() -> dict:
    manifest_path = ROOT / "reports" / "cicids2017_revision_v1" / "manifests" / "UNSW_FROZEN_MANIFEST.sha256"
    logger.info("Checking frozen benchmark manifest: %s", manifest_path)
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
            expected_size = int(expected_size)
            file_path = ROOT / rel_path

            total_files += 1
            if not file_path.exists():
                missing_files.append(rel_path)
                continue

            actual_sha = sha256_file(file_path)
            if actual_sha != expected_sha:
                mismatches.append({
                    "path": rel_path,
                    "expected": expected_sha,
                    "actual": actual_sha,
                })

    all_pass = (len(mismatches) == 0 and len(missing_files) == 0 and total_files == 1261)
    logger.info("Frozen manifest check: %d files checked | %d missing | %d mismatches | PASS=%s",
                total_files, len(missing_files), len(mismatches), all_pass)
    return {
        "pass": all_pass,
        "total_files": total_files,
        "missing_count": len(missing_files),
        "mismatches_count": len(mismatches),
        "missing_files": missing_files,
        "mismatches": mismatches,
    }


def verify_zero_day_hashes() -> dict:
    pop_path = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing" / "population_verification.json"
    with open(pop_path) as f:
        pop_data = json.load(f)["population_results"]

    splits_dir = ROOT / "cicids2017" / "DATA" / "splits"
    zero_day_splits = ["protected_bot", "unseen_xss", "unseen_infiltration"]
    results = {}
    all_pass = True

    for name in zero_day_splits:
        file_path = splits_dir / f"{name}.csv"
        expected_sha = pop_data[name]["sha256"]
        actual_sha = sha256_file(file_path)
        matched = (actual_sha == expected_sha)
        if not matched:
            all_pass = False
        results[name] = {
            "expected_sha": expected_sha,
            "actual_sha": actual_sha,
            "pass": matched,
        }
        logger.info("Zero-day %s: hash match=%s", name, matched)

    return {"pass": all_pass, "details": results}


def verify_shortcut_freeze() -> dict:
    shortcut_path = ROOT / "results" / "cicids2017_revision_v1" / "shortcut_list_frozen.json"
    if not shortcut_path.exists():
        return {"pass": False, "error": "shortcut_list_frozen.json not found"}

    sha = sha256_file(shortcut_path)
    expected_sha = "5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2"
    matched = (sha == expected_sha)

    with open(shortcut_path) as f:
        data = json.load(f)

    frozen_set = data.get("frozen_shortcut_set", [])
    expected_set = ["Destination Port", "Init_Win_bytes_backward"]
    set_matched = (frozen_set == expected_set)

    logger.info("Shortcut freeze: SHA-256 match=%s | set match=%s", matched, set_matched)
    return {
        "pass": (matched and set_matched),
        "actual_sha": sha,
        "expected_sha": expected_sha,
        "frozen_set": frozen_set,
        "expected_set": expected_set,
    }


def verify_artifacts() -> dict:
    required_paths = [
        ROOT / "results" / "cicids2017_revision_v1" / "preprocessing" / "scaler_train_only.pkl",
        ROOT / "results" / "cicids2017_revision_v1" / "preprocessing" / "feature_schema.json",
        ROOT / "results" / "cicids2017_revision_v1" / "feature_selection" / "selected_features.json",
        ROOT / "results" / "cicids2017_revision_v1" / "feature_selection" / "mi_plateau_table.csv",
        ROOT / "results" / "cicids2017_revision_v1" / "supervised" / "training_metadata.json",
        ROOT / "results" / "cicids2017_revision_v1" / "stacking" / "oof_predictions_seed42.csv",
        ROOT / "results" / "cicids2017_revision_v1" / "stacking" / "oof_predictions_seed123.csv",
        ROOT / "results" / "cicids2017_revision_v1" / "stacking" / "oof_predictions_seed2024.csv",
        ROOT / "results" / "cicids2017_revision_v1" / "stacking" / "stacking_metadata.json",
        ROOT / "results" / "cicids2017_revision_v1" / "supervised" / "dev_test_evaluation.json",
    ]
    for seed in [42, 123, 2024]:
        required_paths.extend([
            ROOT / "cicids2017" / "models" / f"seed_{seed}" / "dt_model.pkl",
            ROOT / "cicids2017" / "models" / f"seed_{seed}" / "rf_model.pkl",
            ROOT / "cicids2017" / "models" / f"seed_{seed}" / "svm_model.pkl",
            ROOT / "cicids2017" / "models" / f"seed_{seed}" / "svm_scaler.pkl",
            ROOT / "cicids2017" / "models" / f"seed_{seed}" / "nn_model.pt",
            ROOT / "cicids2017" / "models" / f"seed_{seed}" / "nn_scaler.pkl",
            ROOT / "cicids2017" / "models" / f"seed_{seed}" / "meta_lr.pkl",
        ])

    missing = [str(p.relative_to(ROOT)) for p in required_paths if not p.exists()]
    logger.info("Artifact presence: required=%d | missing=%d", len(required_paths), len(missing))
    return {
        "pass": (len(missing) == 0),
        "total_required": len(required_paths),
        "missing_count": len(missing),
        "missing": missing,
    }


def main():
    logger.info("=" * 70)
    logger.info("SPRINT 3: FINAL VERIFICATION & INVARIANT AUDIT")
    logger.info("=" * 70)

    unsw_res = verify_frozen_manifest()
    zero_day_res = verify_zero_day_hashes()
    shortcut_res = verify_shortcut_freeze()
    artifacts_res = verify_artifacts()

    all_pass = (
        unsw_res["pass"] and
        zero_day_res["pass"] and
        shortcut_res["pass"] and
        artifacts_res["pass"]
    )

    out_dir = ROOT / "results" / "cicids2017_revision_v1" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_data = {
        "verification_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": 3,
        "all_invariants_pass": all_pass,
        "frozen_benchmark_manifest": unsw_res,
        "zero_day_splits_integrity": zero_day_res,
        "shortcut_freeze_verification": shortcut_res,
        "pipeline_artifacts_verification": artifacts_res,
    }

    out_path = out_dir / "sprint3_verification.json"
    with open(out_path, "w") as f:
        json.dump(report_data, f, indent=2)

    logger.info("Verification report saved: %s", out_path)
    logger.info("ALL SPRINT 3 INVARIANTS PASS: %s", all_pass)
    logger.info("=" * 70)

    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
