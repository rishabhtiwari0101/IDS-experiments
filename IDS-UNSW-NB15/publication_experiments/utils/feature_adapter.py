"""
publication_experiments/utils/feature_adapter.py
--------------------------------------------------
No-TTL Feature Adapter for EXP_NO_TTL_V1 and EXP_AE_UNSEEN_FAMILY_V1.

REUSE POLICY:
  - Loads canonical feature list from EXP_MI_V1_1/selected_features.json
  - Removes exactly {sttl, ct_state_ttl, dttl}
  - Provides column-subsetting utilities for DataFrames

DO NOT DUPLICATE:
  - Feature selection (MI selection) — reused from EXP_MI_V1_1 artifact
  - Scaler fitting — reused from src.preprocessing.scaling
  - Data loading — reused from src.preprocessing.loader

This module ONLY handles the No-TTL column subset mapping.
It does NOT implement any ML, training, or evaluation logic.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────

CANONICAL_FEATURE_COUNT = 75
REMOVED_TTL_FEATURES: list[str] = ["sttl", "ct_state_ttl", "dttl"]
EXPECTED_NO_TTL_COUNT = 72  # 75 - 3


# ── Core adapter ─────────────────────────────────────────────────────────


def load_canonical_features(
    selected_features_path: str | Path = (
        "results/feature_selection/EXP_MI_V1_1/selected_features.json"
    ),
) -> list[str]:
    """
    Load the canonical 75 MI-selected features from EXP_MI_V1_1 artifact.

    REUSE: reads from the frozen canonical feature-selection output.
    Does NOT re-run MI selection.

    Returns
    -------
    list[str]
        Ordered list of 75 canonical feature names.

    Raises
    ------
    FileNotFoundError
        If the canonical features file does not exist.
    ValueError
        If the loaded feature count does not equal 75.
    """
    path = Path(selected_features_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Canonical features file not found: {path}\n"
            f"Expected at: results/feature_selection/EXP_MI_V1_1/selected_features.json"
        )

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    features = data["features"]
    if len(features) != CANONICAL_FEATURE_COUNT:
        raise ValueError(
            f"Expected {CANONICAL_FEATURE_COUNT} canonical features, "
            f"got {len(features)} from {path}"
        )

    logger.info("Loaded %d canonical features from %s", len(features), path)
    return features


def compute_no_ttl_features(
    canonical_features: list[str],
    removed: list[str] | None = None,
) -> list[str]:
    """
    Remove exactly the TTL features from the canonical 75-feature list.

    Parameters
    ----------
    canonical_features : list[str]
        The 75 canonical MI-selected features (ordered).
    removed : list[str], optional
        Features to remove. Defaults to REMOVED_TTL_FEATURES.
        Override only for testing purposes.

    Returns
    -------
    list[str]
        Ordered 72-feature list with TTL features removed.

    Raises
    ------
    ValueError
        If any feature in `removed` is not found in canonical_features,
        or if the resulting count is not 72.
    """
    if removed is None:
        removed = REMOVED_TTL_FEATURES

    # Verify all removed features actually exist in canonical set
    not_found = [f for f in removed if f not in canonical_features]
    if not_found:
        raise ValueError(
            f"Features to remove not found in canonical list: {not_found}\n"
            f"Cannot proceed — HARD STOP."
        )

    no_ttl = [f for f in canonical_features if f not in set(removed)]

    if len(no_ttl) != EXPECTED_NO_TTL_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_NO_TTL_COUNT} No-TTL features after removing "
            f"{len(removed)} TTL features, got {len(no_ttl)}."
        )

    # Verify none of the removed features remain
    remaining_ttl = [f for f in removed if f in no_ttl]
    if remaining_ttl:
        raise ValueError(
            f"CRITICAL: Removed features still present in no_ttl list: {remaining_ttl}"
        )

    logger.info(
        "No-TTL features: %d canonical - %d removed = %d final",
        len(canonical_features), len(removed), len(no_ttl),
    )
    return no_ttl


def verify_no_ttl_features(no_ttl_features: list[str]) -> dict[str, Any]:
    """
    Programmatic verification that no TTL feature remains.

    Returns
    -------
    dict
        Verification report with pass/fail for each assertion.
    """
    checks = {}
    for ttl_feat in REMOVED_TTL_FEATURES:
        present = ttl_feat in no_ttl_features
        checks[f"{ttl_feat}_absent"] = not present
        if present:
            logger.error("VERIFICATION FAIL: %s still present in No-TTL features!", ttl_feat)

    checks["feature_count_eq_72"] = (len(no_ttl_features) == EXPECTED_NO_TTL_COUNT)
    checks["all_pass"] = all(checks.values())

    if not checks["all_pass"]:
        failed = [k for k, v in checks.items() if not v]
        raise ValueError(f"No-TTL feature verification FAILED: {failed}")

    logger.info("No-TTL feature verification: ALL PASS")
    return checks


def hash_feature_list(features: list[str]) -> str:
    """
    Compute a deterministic SHA-256 fingerprint of an ordered feature list.

    Uses JSON serialisation for determinism across environments.

    Returns
    -------
    str
        64-character lowercase hex SHA-256 digest.
    """
    serialised = json.dumps(features, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def select_no_ttl_columns(
    df: pd.DataFrame,
    no_ttl_features: list[str],
) -> pd.DataFrame:
    """
    Subset a DataFrame to only the 72 No-TTL feature columns.

    Parameters
    ----------
    df : pd.DataFrame
        Encoded DataFrame (full or partial column set).
    no_ttl_features : list[str]
        The 72-element No-TTL feature list.

    Returns
    -------
    pd.DataFrame
        Subset with exactly the 72 No-TTL columns in canonical order.

    Raises
    ------
    ValueError
        If any No-TTL feature is missing from the DataFrame.
    """
    missing = [f for f in no_ttl_features if f not in df.columns]
    if missing:
        raise ValueError(
            f"No-TTL features missing from DataFrame: {missing[:5]}... "
            f"({len(missing)} total missing). "
            f"Ensure encoding has been applied before column subsetting."
        )

    # Verify TTL features are NOT being included
    ttl_present = [f for f in REMOVED_TTL_FEATURES if f in df.columns]
    if ttl_present:
        logger.debug(
            "TTL features present in source DataFrame (will be excluded): %s",
            ttl_present,
        )

    subset = df[no_ttl_features].copy()
    assert subset.shape[1] == EXPECTED_NO_TTL_COUNT, (
        f"Column subset produced {subset.shape[1]} columns, expected {EXPECTED_NO_TTL_COUNT}"
    )
    return subset


def build_and_save_no_ttl_feature_file(
    output_path: str | Path,
    canonical_features_path: str | Path = (
        "results/feature_selection/EXP_MI_V1_1/selected_features.json"
    ),
) -> dict[str, Any]:
    """
    Build the No-TTL feature list, verify it, hash it, and save to JSON.

    This is the SINGLE authoritative source of the 72-feature No-TTL list.
    All experiments must load from this file rather than recomputing.

    Parameters
    ----------
    output_path : str | Path
        Where to save no_ttl_features.json.
    canonical_features_path : str | Path
        Path to canonical EXP_MI_V1_1 selected_features.json.

    Returns
    -------
    dict
        The full feature manifest saved to disk.
    """
    canonical_features = load_canonical_features(canonical_features_path)
    no_ttl_features = compute_no_ttl_features(canonical_features)
    verification = verify_no_ttl_features(no_ttl_features)
    feature_hash = hash_feature_list(no_ttl_features)

    manifest: dict[str, Any] = {
        "experiment_id": "EXP_NO_TTL_V1",
        "canonical_feature_source": str(canonical_features_path),
        "canonical_feature_count": CANONICAL_FEATURE_COUNT,
        "removed_features": REMOVED_TTL_FEATURES,
        "removed_feature_count": len(REMOVED_TTL_FEATURES),
        "final_feature_count": len(no_ttl_features),
        "features": no_ttl_features,
        "feature_hash_sha256": feature_hash,
        "verification": verification,
        "feature_ordering": "canonical MI-score-descending order with TTL features omitted",
        "note": (
            "Exact canonical 75-feature ordering is preserved. "
            "Only sttl (index 1), ct_state_ttl (index 3), dttl (index 4) removed. "
            "No additional feature selection or reordering applied."
        ),
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info("No-TTL feature manifest saved to %s", output_path)
    logger.info("Feature hash: %s", feature_hash)
    return manifest


def load_no_ttl_feature_file(path: str | Path) -> list[str]:
    """
    Load the 72 No-TTL features from a previously saved manifest file.

    Verifies count and absence of TTL features on load.

    Returns
    -------
    list[str]
        The 72-element No-TTL feature list.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"No-TTL feature file not found: {path}\n"
            f"Run build_and_save_no_ttl_feature_file() first (Stage A dry-run)."
        )

    with open(path, encoding="utf-8") as f:
        manifest = json.load(f)

    features = manifest["features"]
    verify_no_ttl_features(features)
    return features


# Alias for backward compatibility
load_no_ttl_features = load_no_ttl_feature_file

