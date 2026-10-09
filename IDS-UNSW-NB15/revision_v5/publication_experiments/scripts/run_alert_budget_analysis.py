#!/usr/bin/env python3
"""
revision_v5/publication_experiments/scripts/run_alert_budget_analysis.py
------------------------------------------------------------------------
Phase 4 / Analysis B5: Alert Budget Analysis (S8).
Blueprint reference: SS16 (S8), SS18 Gate 4.

Inputs (read-only):
  - matched_fpr_tier_b.csv  (from S3, EXP_MATCHED_FPR_V1)
  - headline_tier_decision.json (from S3, EXP_MATCHED_FPR_V1)

Computation:
  For every (model, seed, nominal_budget) cell in the Tier B table:
    alerts_per_10k_benign = (eval_fp / n_eval_benign) * 10000

  where eval_fp is the realized false-positive count on the Tier B eval half
  (n_eval_benign = 18,500 throughout).  This is a deterministic rescaling --
  no statistical fitting, no threshold recomputation.

  The tie_unattainable flag is carried verbatim from the source table.
  The shift_affected flag is carried verbatim from the source table.

Output columns (alert_budget_table.csv):
  model, seed, model_key, nominal_budget, nominal_budget_str,
  n_eval_benign, eval_fp, alerts_per_10k_benign,
  realized_control_fpr, realized_control_fpr_fraction,
  recall, f2,
  tie_unattainable, shift_affected

Additionally produces:
  - alert_budget_summary.json  -- per-budget mean/min/max across non-tie models
  - self_check.json
  - metadata.json

Zero-Training Guard: no ML fitting or threshold computation performed.
All outputs strictly inside revision_v5/.
"""

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


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
                    f"ZERO-TRAINING GUARD VIOLATION: prohibited pattern {pattern!r} "
                    f"found at line {i} of {script_path}: {stripped}"
                )
# END_ZERO_TRAINING_GUARD_DEFINITION


# ---------------------------------------------------------------------------
# Setup Paths and Logger
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("run_alert_budget_analysis")


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
    with open(filepath, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Normalization base for alert rate
ALERTS_PER_N: int = 10_000  # alerts per 10,000 benign flows

# Expected eval-half benign count from Tier B table (cross-checked at runtime)
EXPECTED_N_EVAL_BENIGN: int = 18_500

# Expected budgets in the Tier B table (nominal FPR as float)
EXPECTED_BUDGETS = [0.001, 0.005, 0.01, 0.05]
EXPECTED_BUDGET_STRS = ["1/1000", "1/200", "1/100", "1/20"]

# Models that never have a seed (single-run in S3)
SEEDLESS_MODELS = {"dt", "rf", "svm", "nn", "ae"}


# ---------------------------------------------------------------------------
# Main S8 Analysis Routine
# ---------------------------------------------------------------------------

def run_alert_budget_analysis() -> None:
    # 0. Zero-Training Guard
    execute_zero_training_guard(Path(__file__).resolve())
    logger.info("=== STEP 0: Zero-Training Guard Passed ===")

    # Output directory -- strictly inside revision_v5/
    out_dir = NEW_ROOT / "results/publication_experiments/EXP_ALERT_BUDGET_V1"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not str(out_dir.resolve()).startswith(str(NEW_ROOT.resolve())):
        raise RuntimeError(f"Output directory {out_dir} is outside {NEW_ROOT}")
    logger.info(f"Outputs will be written strictly inside: {out_dir}")

    # 1. Load Tier B matched-FPR table from S3
    logger.info("=== STEP 1: Loading S3 Tier B matched-FPR table ===")
    s3_dir = resolve_path("results/publication_experiments/EXP_MATCHED_FPR_V1")
    if not s3_dir.exists():
        raise FileNotFoundError(
            f"EXP_MATCHED_FPR_V1 directory not found: {s3_dir}. "
            "Run S3 (run_matched_fpr_analysis.py) first."
        )

    tier_b_path = s3_dir / "matched_fpr_tier_b.csv"
    if not tier_b_path.exists():
        raise FileNotFoundError(f"matched_fpr_tier_b.csv not found: {tier_b_path}")
    sha_tier_b = compute_sha256(tier_b_path)

    headline_path = s3_dir / "headline_tier_decision.json"
    if not headline_path.exists():
        raise FileNotFoundError(f"headline_tier_decision.json not found: {headline_path}")
    sha_headline = compute_sha256(headline_path)

    df = pd.read_csv(tier_b_path)
    logger.info(f"Loaded matched_fpr_tier_b.csv: {len(df)} rows, SHA256={sha_tier_b[:16]}...")

    with open(headline_path, "r", encoding="utf-8") as fh:
        headline = json.load(fh)
    logger.info(f"Loaded headline_tier_decision.json: SHA256={sha_headline[:16]}...")

    # 2. Validate required columns
    logger.info("=== STEP 2: Validating required columns ===")
    required_cols = [
        "model", "seed", "model_key", "nominal_budget", "nominal_budget_str",
        "n_eval_benign", "eval_fp", "realized_control_fpr",
        "recall", "f2", "tie_unattainable", "shift_affected",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise AssertionError(
            f"matched_fpr_tier_b.csv is missing required columns: {missing}. "
            f"Available: {list(df.columns)}"
        )
    logger.info(f"PASS: All {len(required_cols)} required columns present.")

    # 3. Cross-check structural expectations
    logger.info("=== STEP 3: Cross-checking table structure ===")

    # n_eval_benign must be uniformly EXPECTED_N_EVAL_BENIGN throughout
    n_eval_unique = df["n_eval_benign"].unique().tolist()
    if n_eval_unique != [EXPECTED_N_EVAL_BENIGN]:
        raise AssertionError(
            f"n_eval_benign is not uniformly {EXPECTED_N_EVAL_BENIGN}: "
            f"found {n_eval_unique}."
        )
    logger.info(f"PASS: n_eval_benign uniformly {EXPECTED_N_EVAL_BENIGN} throughout.")

    # Budgets present
    actual_budgets = sorted(df["nominal_budget"].unique().tolist())
    if actual_budgets != sorted(EXPECTED_BUDGETS):
        raise AssertionError(
            f"Unexpected budgets in tier_b: expected {sorted(EXPECTED_BUDGETS)}, "
            f"got {actual_budgets}."
        )
    logger.info(f"PASS: Budgets verified: {actual_budgets}")

    # eval_fp non-negative integers
    if (df["eval_fp"] < 0).any():
        raise AssertionError("eval_fp contains negative values.")
    logger.info("PASS: eval_fp all non-negative.")

    # Headline tier decision must be 'B'
    if headline.get("headline_tier") != "B":
        raise AssertionError(
            f"headline_tier_decision.json headline_tier is not 'B': got {headline.get('headline_tier')!r}."
        )
    logger.info("PASS: headline_tier_decision.json headline_tier is 'B'.")

    # Calibration tier should be 'B' throughout
    if not df["calibration_tier"].eq("B").all():
        raise AssertionError(
            "Not all rows have calibration_tier == 'B' in matched_fpr_tier_b.csv."
        )
    logger.info("PASS: All rows have calibration_tier='B'.")

    # 4. Compute alerts_per_10k_benign
    logger.info("=== STEP 4: Computing alerts_per_10k_benign ===")
    # Exact rational representation for the record
    df = df.copy()
    df["alerts_per_10k_benign"] = (df["eval_fp"] / df["n_eval_benign"]) * ALERTS_PER_N
    df["realized_control_fpr_fraction"] = df.apply(
        lambda r: str(Fraction(int(r["eval_fp"]), int(r["n_eval_benign"])).limit_denominator(100000)),
        axis=1,
    )

    # Verify: alerts_per_10k_benign == realized_control_fpr * 10000
    fp_from_fpr = df["realized_control_fpr"] * ALERTS_PER_N
    max_diff = float((df["alerts_per_10k_benign"] - fp_from_fpr).abs().max())
    if max_diff > 1e-6:
        raise AssertionError(
            f"alerts_per_10k_benign inconsistent with realized_control_fpr * {ALERTS_PER_N}: "
            f"max abs diff = {max_diff:.2e}"
        )
    logger.info(
        f"PASS: alerts_per_10k_benign consistent with realized_control_fpr * {ALERTS_PER_N} "
        f"(max diff {max_diff:.2e})."
    )

    logger.info(
        f"Computed alerts_per_10k_benign for {len(df)} (model, seed, budget) cells."
    )

    # 5. Build output table
    logger.info("=== STEP 5: Building output table ===")
    out_cols = [
        "model", "seed", "model_key", "nominal_budget", "nominal_budget_str",
        "n_eval_benign", "eval_fp", "alerts_per_10k_benign",
        "realized_control_fpr", "realized_control_fpr_fraction",
        "recall", "f2",
        "tie_unattainable", "shift_affected",
    ]
    df_out = df[[c for c in out_cols if c in df.columns]].copy()
    df_out = df_out.sort_values(
        ["nominal_budget", "model", "seed"], na_position="first"
    ).reset_index(drop=True)

    # 6. Per-budget summary (mean/min/max alerts_per_10k, excluding tie_unattainable cells)
    logger.info("=== STEP 6: Computing per-budget summary (non-tie cells) ===")
    summary: Dict[str, Any] = {}
    for budget in EXPECTED_BUDGETS:
        budget_str = df_out.loc[df_out["nominal_budget"] == budget, "nominal_budget_str"].iloc[0]
        subset = df_out[(df_out["nominal_budget"] == budget) & (~df_out["tie_unattainable"])]
        tie_subset = df_out[(df_out["nominal_budget"] == budget) & (df_out["tie_unattainable"])]
        alerts = subset["alerts_per_10k_benign"].values
        summary[budget_str] = {
            "nominal_budget": budget,
            "nominal_budget_str": budget_str,
            "n_cells_total": int((df_out["nominal_budget"] == budget).sum()),
            "n_cells_tie_unattainable": int(len(tie_subset)),
            "n_cells_non_tie": int(len(subset)),
            "alerts_per_10k_mean": float(np.mean(alerts)) if len(alerts) > 0 else None,
            "alerts_per_10k_min": float(np.min(alerts)) if len(alerts) > 0 else None,
            "alerts_per_10k_max": float(np.max(alerts)) if len(alerts) > 0 else None,
        }
        logger.info(
            f"  Budget {budget_str}: {len(subset)} non-tie cells, "
            f"alerts/10k mean={summary[budget_str]['alerts_per_10k_mean']:.2f} "
            f"[{summary[budget_str]['alerts_per_10k_min']:.2f}, "
            f"{summary[budget_str]['alerts_per_10k_max']:.2f}]"
        )

    # 7. Write output artifacts
    logger.info("=== STEP 7: Writing output artifacts ===")

    budget_csv_path = out_dir / "alert_budget_table.csv"
    df_out.to_csv(budget_csv_path, index=False)
    logger.info(f"Wrote {budget_csv_path}")

    summary_json_path = out_dir / "alert_budget_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    logger.info(f"Wrote {summary_json_path}")

    self_check_path = out_dir / "self_check.json"
    self_check = {
        "experiment_id": "EXP_ALERT_BUDGET_V1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_training_guard": "PASS",
        "source_s3_tier_b_sha256": sha_tier_b,
        "source_headline_sha256": sha_headline,
        "n_rows_processed": len(df_out),
        "n_eval_benign_uniform": EXPECTED_N_EVAL_BENIGN,
        "alert_normalization_base": ALERTS_PER_N,
        "alerts_fp_fpr_consistency_max_diff": max_diff,
        "budgets_verified": actual_budgets,
        "tie_unattainable_carried": True,
        "shift_affected_carried": True,
        "per_budget_summary": summary,
        "overall_status": "PASS",
    }
    with open(self_check_path, "w", encoding="utf-8") as fh:
        json.dump(self_check, fh, indent=2)
    logger.info(f"Wrote {self_check_path}")

    metadata_path = out_dir / "metadata.json"
    metadata = {
        "experiment_id": "EXP_ALERT_BUDGET_V1",
        "blueprint_version": "5.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "provenance_hashes": {
            "matched_fpr_tier_b_csv": sha_tier_b,
            "headline_tier_decision_json": sha_headline,
        },
        "artifact_hashes": {
            "alert_budget_table.csv": compute_sha256(budget_csv_path),
            "alert_budget_summary.json": compute_sha256(summary_json_path),
            "self_check.json": compute_sha256(self_check_path),
        },
        "status": "PASS",
    }
    with open(metadata_path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)
    logger.info(f"Wrote {metadata_path}")

    logger.info("=== S8 Alert Budget Analysis Complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S8: Alert Budget Analysis")
    # No mandatory config -- all inputs resolved from S3 outputs.
    parser.parse_args()
    run_alert_budget_analysis()
