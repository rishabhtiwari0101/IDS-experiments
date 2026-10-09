#!/usr/bin/env python3
"""
revision_v5/publication_experiments/scripts/run_tost_analysis.py
---------------------------------------------------------------
Phase 4 / Analysis B3: Conservative Exact Paired-Equivalence Test for RF ± TTL (S4).
Blueprint reference: §8.1 (Req 2.3), §16 (S4), §18 Gate 4.

Key protocol requirements:
1. Zero-Training Guard: purely statistical hypothesis testing, strictly fits no models.
2. Paired-Input Provenance: Prefers per-row paired RF predictions keyed by the committed
   Backdoor row IDs (source-prefixed). Derives contingency counts:
   - A: both canonical (75-feat) and no-TTL (72-feat) alert
   - B: canonical only
   - C: no-TTL only
   - D: neither alerts
3. Assertions:
   - Asserts paired population count A + B + C + D == 583.
   - Asserts derived (A, B, C, D) == (582, 0, 0, 1) against tost.yaml and
     results/publication_experiments/EXP_STATS_ROBUSTNESS_V1/paired_tests/mcnemar_results.csv.
   - Fails loudly if mcnemar_results.csv, its required columns, or the RF row are missing.
   - Notes that detections equal correctness because all 583 evaluation rows are attacks.
4. Conservative Exact Paired-Equivalence Procedure:
   - Equivalence margin delta = 0.01 (proportion = 1 percentage point).
   - Test H0: q >= delta vs H1: q < delta with exact binomial test on discordant pairs X = B + C.
   - alpha = 0.05.
   - One-sided exact 95% Clopper-Pearson upper bound on q (and two-sided 95% CI).
   - Equivalence supported iff one-sided upper bound < delta.
5. Strict output paths inside results/publication_experiments/EXP_TOST_V1/:
   - tost_rf_equivalence.json
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
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import beta, binom
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
logger = logging.getLogger("run_tost_analysis")


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
# Main S4 Analysis Routine
# ---------------------------------------------------------------------------

def run_tost_analysis(config_path: Path) -> None:
    # 0. Execute Zero-Training Guard
    execute_zero_training_guard(Path(__file__).resolve())
    logger.info("=== STEP 0: Zero-Training Guard Passed ===")

    # 1. Load and Verify Config
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    out_rel = cfg.get("output_dir", "results/publication_experiments/EXP_TOST_V1")
    out_dir = NEW_ROOT / out_rel if not str(out_rel).startswith(str(NEW_ROOT)) else Path(out_rel)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not str(out_dir.resolve()).startswith(str(NEW_ROOT.resolve())):
        raise RuntimeError(f"Output directory {out_dir} is outside {NEW_ROOT}")
    logger.info(f"Outputs will be written strictly inside: {out_dir}")

    # Check git status of tost.yaml to ensure committed / unchanged
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain", str(config_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.stdout.strip():
            logger.warning(f"Git status reports uncommitted changes in config: {config_path}")
    except Exception as e:
        logger.debug(f"Git status check skipped: {e}")

    # 2. Load Paired Predictions
    logger.info("=== STEP 1: Loading Paired Predictions for Protected Backdoor ===")
    p_canon_rel = cfg["paired_predictions_input"]["canonical"]
    p_nottl_rel = cfg["paired_predictions_input"]["no_ttl"]
    canon_path = resolve_path(p_canon_rel)
    nottl_path = resolve_path(p_nottl_rel)

    if not canon_path.exists():
        raise FileNotFoundError(f"Canonical Backdoor predictions not found: {canon_path}")
    if not nottl_path.exists():
        raise FileNotFoundError(f"No-TTL Backdoor predictions not found: {nottl_path}")

    df_canon = pd.read_csv(canon_path)
    df_nottl = pd.read_csv(nottl_path)

    # 3. Align on Row Identity
    # In zero_day_backdoor_predictions.csv: source_row_uid is 'UNSW_NB15_testing-set.csv:<id>'
    # In predictions_protected_backdoor.csv: column is 'id' (integer)
    df_canon["join_id"] = df_canon["source_row_uid"].apply(lambda x: int(str(x).split(":")[-1]))
    df_nottl["join_id"] = df_nottl["id"].astype(int)

    merged = pd.merge(df_canon, df_nottl, on="join_id", suffixes=("_canon", "_nottl"))
    expected_n = int(cfg.get("expected_n", 583))
    assert len(merged) == expected_n, f"Expected {expected_n} paired rows, got {len(merged)}"

    # 4. Derive Contingency Counts for Random Forest
    c_pred = merged["rf_prediction"].values.astype(int)
    n_pred = merged["rf_pred"].values.astype(int)

    # NOTE ON CONTINGENCY CELL MEANINGS:
    # All N=583 rows in the protected Backdoor evaluation set are attacks (label == 1; benign count is 0).
    # Therefore, an alert / detection (prediction == 1) strictly equals a correct classification (True Positive),
    # and a non-alert (prediction == 0) strictly equals an incorrect classification (False Negative).
    # Consequently, alert agreement directly equals correctness agreement:
    #   A = (c_pred == 1 & n_pred == 1) <==> A_both_correct (both models correctly detect the attack)
    #   B = (c_pred == 1 & n_pred == 0) <==> B_canon_only   (canonical model correct only; no-TTL missed)
    #   C = (c_pred == 0 & n_pred == 1) <==> C_nottl_only   (no-TTL model correct only; canonical missed)
    #   D = (c_pred == 0 & n_pred == 0) <==> D_neither_correct (both models missed the attack)
    A = int(((c_pred == 1) & (n_pred == 1)).sum())
    B = int(((c_pred == 1) & (n_pred == 0)).sum())
    C = int(((c_pred == 0) & (n_pred == 1)).sum())
    D = int(((c_pred == 0) & (n_pred == 0)).sum())
    total_n = A + B + C + D

    assert total_n == expected_n, f"Contingency sum {total_n} != expected {expected_n}"
    logger.info(f"Derived Paired Contingency: A={A}, B={B}, C={C}, D={D} (Total={total_n})")

    # 5. Assert Against tost.yaml and mcnemar_results.csv
    logger.info("=== STEP 2: Asserting Contingency Counts Against Commit Baseline ===")
    assert_cfg = cfg.get("assert_contingency", {})
    assert A == assert_cfg.get("A", 582), f"Contingency A mismatch: {A} != {assert_cfg.get('A')}"
    assert B == assert_cfg.get("B", 0), f"Contingency B mismatch: {B} != {assert_cfg.get('B')}"
    assert C == assert_cfg.get("C", 0), f"Contingency C mismatch: {C} != {assert_cfg.get('C')}"
    assert D == assert_cfg.get("D", 1), f"Contingency D mismatch: {D} != {assert_cfg.get('D')}"

    # Cross-assert against mcnemar_results.csv (MUST fail loudly if file, columns, or RF row missing)
    mcnemar_path = resolve_path(cfg.get("aggregate_fallback_input", "results/publication_experiments/EXP_STATS_ROBUSTNESS_V1/paired_tests/mcnemar_results.csv"))
    if not mcnemar_path.exists():
        raise FileNotFoundError(f"mcnemar_results.csv not found at: {mcnemar_path}")

    df_mcnemar = pd.read_csv(mcnemar_path)
    actual_columns = df_mcnemar.columns.tolist()
    logger.info(f"Loaded mcnemar_results.csv. Actual columns: {actual_columns}")

    required_cols = ["model", "A_both_correct", "B_canon_only", "C_nottl_only", "D_neither_correct", "total_pairs"]
    missing_cols = [c for c in required_cols if c not in df_mcnemar.columns]
    if missing_cols:
        raise ValueError(
            f"mcnemar_results.csv is missing required columns: {missing_cols}. "
            f"Actual CSV columns present: {actual_columns}"
        )

    rf_row = df_mcnemar[df_mcnemar["model"] == "RF"]
    if len(rf_row) == 0:
        raise ValueError(
            f"mcnemar_results.csv is missing the 'RF' model row. "
            f"Models present in CSV: {df_mcnemar['model'].tolist()}. "
            f"Actual CSV columns present: {actual_columns}"
        )

    mc_A = int(rf_row["A_both_correct"].values[0])
    mc_B = int(rf_row["B_canon_only"].values[0])
    mc_C = int(rf_row["C_nottl_only"].values[0])
    mc_D = int(rf_row["D_neither_correct"].values[0])
    mc_total = int(rf_row["total_pairs"].values[0])

    if (A, B, C, D) != (mc_A, mc_B, mc_C, mc_D) or total_n != mc_total:
        raise AssertionError(
            f"McNemar contingency mismatch! Derived: (A={A}, B={B}, C={C}, D={D}, total={total_n}), "
            f"mcnemar_results: (A={mc_A}, B={mc_B}, C={mc_C}, D={mc_D}, total={mc_total}). "
            f"Actual CSV columns: {actual_columns}"
        )
    logger.info(f"PASS: Contingency counts match mcnemar_results.csv (RF) bit-for-bit: (A={mc_A}, B={mc_B}, C={mc_C}, D={mc_D}, total={mc_total})")

    # 6. Statistical Analysis: Conservative Exact Paired-Equivalence Test
    logger.info("=== STEP 3: Executing Conservative Exact Paired-Equivalence Procedure ===")
    delta = float(cfg.get("equivalence_margin", 0.01))
    alpha = float(cfg.get("alpha", 0.05))

    p_canonical = float((A + B) / total_n)
    p_no_ttl = float((A + C) / total_n)
    observed_delta = float((B - C) / total_n)
    discordant_count = B + C
    discordant_prop = float(discordant_count / total_n)

    # Exact binomial p-value: P(X <= B + C | N, q = delta)
    # For B = C = 0, this is (1 - delta)^N = (0.99)^583 = ~0.002853
    exact_p_value = float(binom.cdf(discordant_count, total_n, delta))

    # Clopper-Pearson exact confidence bounds on discordant proportion q
    # One-sided 95% upper bound: beta.ppf(1 - alpha, X + 1, N - X)
    q_ub_onesided = float(beta.ppf(1.0 - alpha, discordant_count + 1, total_n - discordant_count))

    # Two-sided 95% interval: [beta.ppf(alpha/2, ...), beta.ppf(1 - alpha/2, ...)]
    q_lb_twosided = float(beta.ppf(alpha / 2.0, discordant_count, total_n - discordant_count + 1)) if discordant_count > 0 else 0.0
    q_ub_twosided = float(beta.ppf(1.0 - alpha / 2.0, discordant_count + 1, total_n - discordant_count))

    # Equivalence Decision
    # Equivalence is supported iff the one-sided 95% upper bound < delta
    is_equivalent = bool(q_ub_onesided < delta and exact_p_value < alpha)

    conclusion = (
        f"Equivalence supported at margin delta={delta*100:.1f} pp (one-sided exact p={exact_p_value:.6f} < alpha={alpha}; "
        f"one-sided 95% Clopper-Pearson upper bound={q_ub_onesided*100:.3f}% < {delta*100:.1f}%)."
        if is_equivalent
        else f"Equivalence not supported at margin delta={delta} (p={exact_p_value:.6f} >= {alpha})."
    )

    logger.info(f"P(Canonical): {p_canonical:.6f}")
    logger.info(f"P(No-TTL):    {p_no_ttl:.6f}")
    logger.info(f"Observed Delta (B - C)/N: {observed_delta:.6f}")
    logger.info(f"Conservative Exact Equivalence p-value: {exact_p_value:.6f}")
    logger.info(f"One-sided 95% CP upper bound on q: {q_ub_onesided*100:.4f}% (Margin = {delta*100:.1f}%)")
    logger.info(f"Two-sided 95% CP interval on q: [{q_lb_twosided*100:.4f}%, {q_ub_twosided*100:.4f}%]")
    logger.info(f"Conclusion: {conclusion}")

    # 7. Write Output Artifacts
    logger.info("=== STEP 4: Writing Output Artifacts ===")
    out_file = out_dir / "tost_rf_equivalence.json"
    result_dict = {
        "experiment_id": cfg.get("experiment_id", "EXP_TOST_V1"),
        "model": "RF",
        "comparison": "75-feature (canonical) vs 72-feature (no-TTL)",
        "population": f"protected_backdoor N={total_n}",
        "equivalence_margin": delta,
        "margin_units": cfg.get("margin_units", "proportion"),
        "margin_status": cfg.get("margin_status", "specified after paired counts were observed (post-hoc); committed before S4 execution"),
        "materiality_reference_detections": int(cfg.get("materiality_reference_detections", 6)),
        "materiality_reference_rate": float(cfg.get("materiality_reference_rate", 0.0102916)),
        "A": A,
        "B": B,
        "C": C,
        "D": D,
        "p_canonical": p_canonical,
        "p_no_ttl": p_no_ttl,
        "observed_delta": observed_delta,
        "discordant_proportion_q_hat": discordant_prop,
        "alpha": alpha,
        "conservative_exact_p_value": exact_p_value,
        "q_upper_bound_one_sided_cp95": q_ub_onesided,
        "q_interval_two_sided_cp95": [q_lb_twosided, q_ub_twosided],
        "equivalence_conclusion": conclusion,
        "limitation": "Zero discordant pairs; margin specified post-hoc; Backdoor recall only.",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2)

    # 8. Write self_check.json
    self_check_file = out_dir / "self_check.json"
    self_check = {
        "experiment_id": cfg.get("experiment_id", "EXP_TOST_V1"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_training_guard": "PASS",
        "evaluation_population": "protected_backdoor",
        "total_pairs": total_n,
        "contingency_counts": {
            "A_both_correct": A,
            "B_canon_only": B,
            "C_nottl_only": C,
            "D_neither_correct": D,
        },
        "mcnemar_cross_check": {
            "source_file": str(mcnemar_path),
            "actual_csv_columns": actual_columns,
            "rf_row_found": True,
            "counts_match": bool((A, B, C, D) == (mc_A, mc_B, mc_C, mc_D)),
        },
        "exact_paired_equivalence": {
            "equivalence_margin_delta": delta,
            "alpha": alpha,
            "discordant_pairs": discordant_count,
            "discordant_rate": discordant_prop,
            "exact_p_value": exact_p_value,
            "one_sided_95_upper_bound": q_ub_onesided,
            "two_sided_95_interval": [q_lb_twosided, q_ub_twosided],
            "is_equivalent": is_equivalent,
        },
        "nan_inf_check": {
            "p_canonical": bool(not (np.isnan(p_canonical) or np.isinf(p_canonical))),
            "p_no_ttl": bool(not (np.isnan(p_no_ttl) or np.isinf(p_no_ttl))),
            "observed_delta": bool(not (np.isnan(observed_delta) or np.isinf(observed_delta))),
            "exact_p_value": bool(not (np.isnan(exact_p_value) or np.isinf(exact_p_value))),
            "q_ub_onesided": bool(not (np.isnan(q_ub_onesided) or np.isinf(q_ub_onesided))),
        },
        "overall_status": "PASS",
    }
    with open(self_check_file, "w", encoding="utf-8") as f:
        json.dump(self_check, f, indent=2)

    meta_file = out_dir / "metadata.json"
    metadata = {
        "experiment_id": cfg.get("experiment_id", "EXP_TOST_V1"),
        "blueprint_version": "5.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "population": "protected_backdoor",
        "sample_size": total_n,
        "model": "RF",
        "artifact_hashes": {
            "tost_rf_equivalence.json": compute_sha256(out_file),
            "self_check.json": compute_sha256(self_check_file),
        },
        "status": "PASS",
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("=== S4 Conservative Exact Paired-Equivalence Analysis Complete ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S4: Conservative Exact Paired-Equivalence Test for RF ± TTL")
    parser.add_argument(
        "--config",
        type=str,
        default="revision_v5/publication_experiments/configs/tost.yaml",
        help="Path to tost.yaml config",
    )
    args = parser.parse_args()
    run_tost_analysis(Path(args.config))
