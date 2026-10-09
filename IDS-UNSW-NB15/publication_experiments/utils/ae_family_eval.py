"""
publication_experiments/utils/ae_family_eval.py
-------------------------------------------------
AE Unseen Attack-Family Evaluation utilities for EXP_AE_UNSEEN_FAMILY_V1.

DESIGN PRINCIPLES (from master prompt):
  - ONE AE checkpoint shared across all four families
  - ONE scaler (benign-only StandardScaler, 72 features)
  - ONE threshold (calibrated on benign VALIDATION only)
  - Four SEPARATE family evaluation outputs
  - Same benign DEV-TEST reference for FPR across all families

REUSE:
  - src.models.autoencoder.ae_model.Autoencoder  (architecture, reconstruction_error)
  - src.models.autoencoder.ae_calibrate.calibrate_thresholds  (threshold computation)
  - src.models.autoencoder.ae_trainer.AETrainer  (training — for new 72-dim AE)
  - src.utils.hashing  (artifact fingerprinting)
  - src.utils.reproducibility.set_all_seeds

NEW CODE HERE:
  - Family isolation audit (verifies AE training ∩ target family = 0)
  - Per-family metrics computation
  - Family comparison report
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Supported target families ─────────────────────────────────────────────

SUPPORTED_FAMILIES: list[str] = ["BACKDOOR", "WORMS", "SHELLCODE", "ANALYSIS"]

# Worms N=44 is below canonical supervised eligibility threshold (50)
# Flag for reporting purposes — do NOT block evaluation
SMALL_N_FAMILIES: set[str] = {"WORMS"}
SMALL_N_THRESHOLD = 50


# ── Family metrics dataclass ──────────────────────────────────────────────


@dataclass
class FamilyEvalResult:
    """Per-family AE evaluation result."""

    family: str
    target_count: int
    detected_count: int
    missed_count: int
    detection_rate: float          # detected / target_count
    benign_val_fpr: float          # from threshold calibration (fixed for all families)
    benign_devtest_fp: int         # false positives on common benign DEV-TEST reference
    benign_devtest_n: int          # total benign DEV-TEST reference rows
    benign_devtest_fpr: float      # benign_devtest_fp / benign_devtest_n
    threshold_rule: str
    threshold_value: float
    ae_training_rows: int
    feature_count: int
    architecture: str
    experiment_id: str
    ae_checkpoint_hash: str
    small_n_warning: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def detection_fraction_str(self) -> str:
        return f"{self.detected_count}/{self.target_count}"

    def summary_line(self) -> str:
        warn = " [SMALL-N WARNING]" if self.small_n_warning else ""
        return (
            f"{self.family:10s}: {self.detection_fraction_str:10s} "
            f"= {self.detection_rate:.2%}  FPR={self.benign_devtest_fpr:.4%}{warn}"
        )


# ── Target-family isolation audit ─────────────────────────────────────────


def audit_family_isolation(
    family: str,
    target_ids: np.ndarray,
    ae_train_ids: np.ndarray,
    ae_val_ids: np.ndarray,
) -> dict[str, Any]:
    """
    Verify that target-family IDs have zero overlap with AE training and
    validation sets.

    Implements the requirement from Section 30 of the master prompt:
        target family ∩ AE TRAIN = 0
        target family ∩ AE VALIDATION = 0

    Parameters
    ----------
    family : str
        Family name (for reporting).
    target_ids : np.ndarray
        IDs of target-family evaluation rows.
    ae_train_ids : np.ndarray
        IDs of rows used for AE training (benign TRAIN subset).
    ae_val_ids : np.ndarray
        IDs of rows used for AE threshold calibration (benign VALIDATION).

    Returns
    -------
    dict
        Audit report. 'all_pass' must be True before evaluation proceeds.

    Raises
    ------
    ValueError
        If any overlap is detected (HARD STOP per master prompt).
    """
    target_set = set(target_ids.tolist())
    train_set = set(ae_train_ids.tolist())
    val_set = set(ae_val_ids.tolist())

    train_overlap = target_set & train_set
    val_overlap = target_set & val_set

    report = {
        "family": family,
        "target_count": len(target_set),
        "ae_train_count": len(train_set),
        "ae_val_count": len(val_set),
        "target_in_ae_train": len(train_overlap),
        "target_in_ae_val": len(val_overlap),
        "all_pass": len(train_overlap) == 0 and len(val_overlap) == 0,
    }

    if train_overlap:
        raise ValueError(
            f"HARD STOP — Family isolation FAIL for {family}: "
            f"{len(train_overlap)} target IDs found in AE training data!\n"
            f"Overlapping IDs (first 5): {list(train_overlap)[:5]}"
        )

    if val_overlap:
        raise ValueError(
            f"HARD STOP — Family isolation FAIL for {family}: "
            f"{len(val_overlap)} target IDs found in AE validation data!\n"
            f"Overlapping IDs (first 5): {list(val_overlap)[:5]}"
        )

    logger.info(
        "Family isolation audit PASS for %s: "
        "0 train overlap, 0 val overlap (target_n=%d)",
        family, len(target_set),
    )
    return report


# ── Per-family metrics computation ────────────────────────────────────────


def compute_family_metrics(
    family: str,
    family_re: np.ndarray,
    benign_devtest_re: np.ndarray,
    threshold: float,
    threshold_rule: str,
    benign_val_fpr: float,
    ae_training_rows: int,
    feature_count: int,
    architecture: str,
    experiment_id: str,
    ae_checkpoint_hash: str,
) -> FamilyEvalResult:
    """
    Compute detection and FPR metrics for one attack family.

    Parameters
    ----------
    family : str
        Target family name.
    family_re : np.ndarray
        Reconstruction errors for target-family flows.
    benign_devtest_re : np.ndarray
        Reconstruction errors for the common benign DEV-TEST reference set.
    threshold : float
        The single frozen threshold (same for all families).
    threshold_rule : str
        Threshold rule name (e.g., "p99").
    benign_val_fpr : float
        FPR on benign VALIDATION from threshold calibration.
    ae_training_rows : int
        Number of benign rows used for AE training.
    feature_count : int
        AE input/output feature count (72).
    architecture : str
        AE architecture string (e.g., "72→12→6→12→72").
    experiment_id : str
        Experiment ID string.
    ae_checkpoint_hash : str
        SHA-256 hash of the AE checkpoint file.

    Returns
    -------
    FamilyEvalResult
    """
    detected = int((family_re > threshold).sum())
    total = len(family_re)
    missed = total - detected
    detection_rate = detected / total if total > 0 else 0.0

    benign_fp = int((benign_devtest_re > threshold).sum())
    benign_n = len(benign_devtest_re)
    benign_fpr = benign_fp / benign_n if benign_n > 0 else 0.0

    small_n = family in SMALL_N_FAMILIES or total < SMALL_N_THRESHOLD

    if small_n:
        logger.warning(
            "Family %s has N=%d samples (below threshold %d). "
            "Interpret results with caution — do not over-generalise.",
            family, total, SMALL_N_THRESHOLD,
        )

    return FamilyEvalResult(
        family=family,
        target_count=total,
        detected_count=detected,
        missed_count=missed,
        detection_rate=detection_rate,
        benign_val_fpr=benign_val_fpr,
        benign_devtest_fp=benign_fp,
        benign_devtest_n=benign_n,
        benign_devtest_fpr=benign_fpr,
        threshold_rule=threshold_rule,
        threshold_value=threshold,
        ae_training_rows=ae_training_rows,
        feature_count=feature_count,
        architecture=architecture,
        experiment_id=experiment_id,
        ae_checkpoint_hash=ae_checkpoint_hash,
        small_n_warning=small_n,
    )


# ── Cross-family comparison report ────────────────────────────────────────


def build_family_comparison_report(
    results: list[FamilyEvalResult],
    threshold_rule: str,
    threshold_value: float,
    canonical_ae_backdoor_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a cross-family comparison report from individual FamilyEvalResults.

    Parameters
    ----------
    results : list[FamilyEvalResult]
        One result per evaluated family.
    threshold_rule : str
        The threshold rule used (same for all families).
    threshold_value : float
        The threshold value (same for all families).
    canonical_ae_backdoor_result : dict, optional
        Reference to canonical 75-feature AE Backdoor result for comparison.
        Should NOT be mixed with new 72-feature results in primary analysis.

    Returns
    -------
    dict
        Serialisable comparison report.
    """
    report: dict[str, Any] = {
        "experiment_id": "EXP_AE_UNSEEN_FAMILY_V1",
        "threshold_rule": threshold_rule,
        "threshold_value": threshold_value,
        "shared_ae_policy": "ONE AE checkpoint, ONE scaler, ONE threshold across all families",
        "families": {},
        "summary": {},
    }

    for r in results:
        report["families"][r.family] = r.to_dict()

    # Summary table rows
    report["summary"]["detection_rates"] = {
        r.family: {
            "fraction": r.detection_fraction_str,
            "percent": round(r.detection_rate * 100, 2),
            "small_n_warning": r.small_n_warning,
        }
        for r in results
    }

    report["summary"]["benign_devtest_fpr"] = {
        r.family: round(r.benign_devtest_fpr * 100, 4)
        for r in results
    }

    if canonical_ae_backdoor_result:
        report["canonical_ae_reference"] = {
            "note": (
                "Canonical 75-feature AE result — DIFFERENT feature representation. "
                "Do NOT directly compare detection rates with new 72-feature AE results."
            ),
            "data": canonical_ae_backdoor_result,
        }

    return report


# ── Save family results ───────────────────────────────────────────────────


def save_family_results(
    result: FamilyEvalResult,
    target_ids: np.ndarray,
    isolation_audit: dict[str, Any],
    output_dir: str | Path,
) -> None:
    """
    Save all artifacts for one family evaluation to its output directory.

    Saves:
        metrics.json       — FamilyEvalResult as dict
        target_ids.json    — row IDs evaluated
        isolation_audit.json — leakage verification report
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2)

    with open(output_dir / "target_ids.json", "w", encoding="utf-8") as f:
        json.dump({"family": result.family, "ids": target_ids.tolist()}, f, indent=2)

    with open(output_dir / "isolation_audit.json", "w", encoding="utf-8") as f:
        json.dump(isolation_audit, f, indent=2)

    logger.info(
        "Saved %s family results: %s (detection=%s)",
        result.family, output_dir, result.detection_fraction_str,
    )
