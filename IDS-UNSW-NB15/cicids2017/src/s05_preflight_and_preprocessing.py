"""
cicids2017/src/s05_preflight_and_preprocessing.py
---------------------------------------------------
Sprint 3 — Step 1: Mandatory Preflight + TRAIN-Only Preprocessing

Tasks:
  A. Mandatory preflight: Resolve Fwd Header Length / Fwd Header Length.1 duplicate.
  B. Verify Sprint 2 population counts from actual split files.
  C. Fit StandardScaler on TRAIN only.
  D. Compute log1p sensitivity metadata (for Sprint 4 AE — no transform applied here).
  E. Serialize frozen feature schema, scaler artifact, and all metadata.

LEAKAGE RULE: StandardScaler is NEVER fit on anything other than TRAIN rows.

Storage: ALL output goes to results/cicids2017_revision_v1/preprocessing/
"""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.preprocessing.scaling import fit_scaler, get_scaler_metadata

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
OUT_DIR = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = ROOT / "results" / "cicids2017_revision_v1" / "preprocessing"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUT_DIR / "s05_preprocessing.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SPLITS_DIR = ROOT / "cicids2017" / "DATA" / "splits"
META_COLS  = {"Label", "shard_source", "label_clean", "attack_family", "row_uid"}

EXPECTED_POPULATIONS = {
    "train":                  340_464,
    "dev_test":               743_921,
    "calibration":             18_500,
    "eval_control":            18_500,
    "protected_bot":            1_948,
    "unseen_xss":                 652,
    "unseen_infiltration":         36,
    "excluded_small":              32,
}

CANDIDATE_SHORTCUT_POOL = [
    "Destination Port",
    "Init_Win_bytes_forward",
    "Init_Win_bytes_backward",
    "Flow Duration",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Section A: Mandatory Feature Schema Preflight
# ---------------------------------------------------------------------------

def preflight_feature_schema(train_df: pd.DataFrame) -> dict:
    """
    Resolve Fwd Header Length / Fwd Header Length.1 duplicate.

    Decision rule:
      - If both columns are value-for-value identical (np.array_equal):
        -> Drop 'Fwd Header Length.1' (the pandas duplicate-renamed one).
        -> Retain 'Fwd Header Length' (the original).
        -> Document decision and reason.
      - If they differ:
        -> Retain both.
        -> Document and log a warning.
    """
    logger.info("=== SECTION A: MANDATORY PREFLIGHT — FEATURE SCHEMA ===")

    all_cols = list(train_df.columns)
    feat_cols_raw = [c for c in all_cols if c not in META_COLS]

    has_fhl   = "Fwd Header Length"   in feat_cols_raw
    has_fhl1  = "Fwd Header Length.1" in feat_cols_raw

    logger.info("Total columns in train.csv: %d", len(all_cols))
    logger.info("Meta columns: %s", sorted(META_COLS & set(all_cols)))
    logger.info("Raw feature columns (before duplicate resolution): %d", len(feat_cols_raw))
    logger.info("'Fwd Header Length' present: %s", has_fhl)
    logger.info("'Fwd Header Length.1' present: %s", has_fhl1)

    duplicate_decision = "N/A"
    dropped_columns    = []

    if has_fhl and has_fhl1:
        arr_a = train_df["Fwd Header Length"].to_numpy()
        arr_b = train_df["Fwd Header Length.1"].to_numpy()

        # --- Value equality check ---
        if np.array_equal(arr_a, arr_b):
            identical = True
            duplicate_decision = "IDENTICAL_DROP_DOT1"
            dropped_columns    = ["Fwd Header Length.1"]
            logger.info(
                "DUPLICATE RESOLUTION: 'Fwd Header Length' and 'Fwd Header Length.1' "
                "are BYTE-FOR-BYTE IDENTICAL (max abs diff = 0)."
            )
            logger.info(
                "DECISION: Drop 'Fwd Header Length.1' (pandas-auto-renamed duplicate). "
                "Retain 'Fwd Header Length'. This is deterministic and methodologically "
                "justified — both columns carry identical information."
            )
        else:
            identical = False
            max_diff = float(np.nanmax(np.abs(arr_a - arr_b)))
            duplicate_decision = "NOT_IDENTICAL_RETAIN_BOTH"
            logger.warning(
                "DUPLICATE COLUMNS ARE NOT IDENTICAL: max_abs_diff = %.6f. "
                "Retaining both columns.", max_diff
            )
    else:
        identical = None
        if not has_fhl:
            logger.info("'Fwd Header Length' NOT present.")
        if not has_fhl1:
            logger.info("'Fwd Header Length.1' NOT present.")

    # Apply the decision
    feat_cols_final = [c for c in feat_cols_raw if c not in dropped_columns]

    logger.info("Final predictive feature count: D = %d", len(feat_cols_final))
    logger.info("Features (first 10): %s", feat_cols_final[:10])

    # Verify shortcut candidate pool is present
    missing_candidates = [c for c in CANDIDATE_SHORTCUT_POOL if c not in feat_cols_final]
    if missing_candidates:
        logger.error("MISSING SHORTCUT CANDIDATES: %s — STOPPING", missing_candidates)
        raise ValueError(f"Missing shortcut candidates: {missing_candidates}")
    else:
        logger.info("All 4 shortcut candidates present: %s", CANDIDATE_SHORTCUT_POOL)

    return {
        "total_columns_in_train_csv": len(all_cols),
        "raw_feature_columns":        len(feat_cols_raw),
        "has_fwd_header_length":      has_fhl,
        "has_fwd_header_length_dot1": has_fhl1,
        "duplicate_identical":        identical,
        "duplicate_decision":         duplicate_decision,
        "dropped_columns":            dropped_columns,
        "D_final":                    len(feat_cols_final),
        "feature_list":               feat_cols_final,
        "shortcut_candidates_verified": CANDIDATE_SHORTCUT_POOL,
    }


# ---------------------------------------------------------------------------
# Section B: Sprint 2 Population Verification
# ---------------------------------------------------------------------------

def verify_populations() -> dict:
    """Read-only count check of all 8 split files."""
    logger.info("=== SECTION B: SPRINT 2 POPULATION VERIFICATION ===")

    results = {}
    all_pass = True

    for split_name, expected in EXPECTED_POPULATIONS.items():
        fpath = SPLITS_DIR / f"{split_name}.csv"
        if not fpath.exists():
            logger.error("MISSING: %s", fpath)
            all_pass = False
            results[split_name] = {"expected": expected, "actual": None, "pass": False}
            continue

        df = pd.read_csv(fpath)
        actual = len(df)
        passed = (actual == expected)
        if not passed:
            all_pass = False
            logger.error("MISMATCH %s: expected=%d actual=%d", split_name, expected, actual)
        else:
            logger.info("OK %s: %d rows", split_name, actual)

        # Label distribution for TRAIN
        label_dist = {}
        if "label_clean" in df.columns:
            label_dist = df["label_clean"].value_counts().to_dict()
        elif "Label" in df.columns:
            label_dist = df["Label"].value_counts().to_dict()

        results[split_name] = {
            "expected": expected,
            "actual":   actual,
            "pass":     passed,
            "sha256":   sha256_file(fpath),
            "label_distribution": {str(k): int(v) for k, v in label_dist.items()},
        }

    logger.info("Population verification: %s", "PASS" if all_pass else "FAIL")
    return {"population_results": results, "all_pass": all_pass}


# ---------------------------------------------------------------------------
# Section C: TRAIN-Only StandardScaler
# ---------------------------------------------------------------------------

def fit_train_scaler(train_df: pd.DataFrame, feature_list: list[str]) -> dict:
    """
    Fit StandardScaler on TRAIN only. Never fit on any other split.
    """
    logger.info("=== SECTION C: FIT STANDARDSCALER ON TRAIN ONLY ===")
    logger.info("TRAIN rows: %d | Features: %d", len(train_df), len(feature_list))

    X_train = train_df[feature_list].to_numpy(dtype=np.float64)

    t0 = time.perf_counter()
    fitted_scaler = fit_scaler(X_train, feature_list)
    elapsed = time.perf_counter() - t0

    logger.info("Scaler fitted in %.2fs", elapsed)
    logger.info("  mean range:  [%.4f, %.4f]", fitted_scaler.train_mean.min(), fitted_scaler.train_mean.max())
    logger.info("  scale range: [%.4f, %.4f]", fitted_scaler.train_scale.min(), fitted_scaler.train_scale.max())

    # Serialize scaler artifact
    scaler_path = OUT_DIR / "scaler_train_only.pkl"
    with open(scaler_path, "wb") as f:
        pickle.dump(fitted_scaler, f)

    scaler_hash = sha256_file(scaler_path)
    logger.info("Scaler saved: %s | SHA-256: %s", scaler_path.name, scaler_hash)

    meta = get_scaler_metadata(fitted_scaler)
    meta["n_train_rows"]         = len(train_df)
    meta["fit_duration_seconds"] = elapsed
    meta["scaler_artifact_path"] = str(scaler_path.relative_to(ROOT))
    meta["scaler_artifact_sha256"] = scaler_hash

    return {
        "fitted_scaler":  fitted_scaler,
        "scaler_path":    scaler_path,
        "scaler_sha256":  scaler_hash,
        "scaler_metadata": meta,
    }


# ---------------------------------------------------------------------------
# Section D: Log1p Sensitivity Metadata (Sprint 4 AE prep — no transform)
# ---------------------------------------------------------------------------

def compute_log1p_sensitivity(train_df: pd.DataFrame, feature_list: list[str]) -> dict:
    """
    Identify features meeting the preregistered heavy-tail rule:
      skewness > 5.0 AND min >= 0.0
    No transform is applied here. This metadata is for Sprint 4 AE only.
    """
    logger.info("=== SECTION D: LOG1P SENSITIVITY METADATA ===")

    records = []
    for feat in feature_list:
        col = train_df[feat]
        skewness = float(col.skew())
        col_min  = float(col.min())
        qualifies = (skewness > 5.0) and (col_min >= 0.0)
        records.append({
            "feature":   feat,
            "skewness":  round(skewness, 6),
            "min_value": round(col_min, 6),
            "qualifies_for_log1p": qualifies,
        })

    qualified = [r for r in records if r["qualifies_for_log1p"]]
    logger.info("Log1p-qualifying features (skew>5 AND min>=0): %d / %d",
                len(qualified), len(feature_list))
    for r in qualified:
        logger.info("  %s  skew=%.3f  min=%.3f", r["feature"], r["skewness"], r["min_value"])

    return {
        "rule": "skewness > 5.0 AND min_value >= 0.0",
        "applied_to": "TRAIN only",
        "total_features": len(feature_list),
        "qualifying_count": len(qualified),
        "qualifying_features": [r["feature"] for r in qualified],
        "all_records": records,
        "note": "No log1p transform applied in Sprint 3. This is a Sprint 4 AE input only.",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 70)
    logger.info("SPRINT 3 — STEP 1: PREFLIGHT & PREPROCESSING")
    logger.info("=" * 70)

    run_ts = datetime.now(timezone.utc)

    # Load TRAIN
    train_path = SPLITS_DIR / "train.csv"
    logger.info("Loading TRAIN: %s", train_path)
    train_df = pd.read_csv(train_path)

    # --- A: Feature schema preflight ---
    preflight = preflight_feature_schema(train_df)
    feature_list = preflight["feature_list"]
    D = preflight["D_final"]

    # --- B: Population verification ---
    pop_check = verify_populations()
    if not pop_check["all_pass"]:
        logger.error("POPULATION VERIFICATION FAILED — STOPPING")
        sys.exit(1)

    # --- C: TRAIN-only scaler ---
    scaler_result = fit_train_scaler(train_df, feature_list)

    # --- D: Log1p sensitivity metadata ---
    log1p_meta = compute_log1p_sensitivity(train_df, feature_list)

    # --- Compute TRAIN label counts for pos_weight reference ---
    # label_clean contains string class names e.g. 'BENIGN', 'DoS Hulk', etc.
    if "label_clean" in train_df.columns:
        train_label_binary = (train_df["label_clean"] != "BENIGN").astype(int)
    else:
        train_label_binary = (train_df["Label"] != "BENIGN").astype(int)

    n_benign = int((train_label_binary == 0).sum())
    n_attack = int((train_label_binary == 1).sum())
    pos_weight_ref = n_benign / n_attack if n_attack > 0 else None
    logger.info("TRAIN label counts: benign=%d  attack=%d  pos_weight_ref=%.6f",
                n_benign, n_attack, pos_weight_ref or 0.0)

    # --- Freeze feature schema JSON ---
    feature_schema = {
        "creation_timestamp_utc": run_ts.isoformat(),
        "sprint": 3,
        "step": "s05_preflight_and_preprocessing",

        # Mandatory preflight
        "preflight": {
            "total_columns_in_train_csv":    preflight["total_columns_in_train_csv"],
            "raw_feature_columns_before_dedup": preflight["raw_feature_columns"],
            "fwd_header_length_present":     preflight["has_fwd_header_length"],
            "fwd_header_length_dot1_present":preflight["has_fwd_header_length_dot1"],
            "duplicate_byte_identical":      preflight["duplicate_identical"],
            "duplicate_decision":            preflight["duplicate_decision"],
            "dropped_columns":               preflight["dropped_columns"],
            "explanation": (
                "Both 'Fwd Header Length' and 'Fwd Header Length.1' were present. "
                "np.array_equal confirmed they are byte-for-byte identical. "
                "'Fwd Header Length.1' is a pandas automatic rename of the duplicate "
                "header in the raw CIC CSV. Dropped deterministically. "
                "The single retained column is 'Fwd Header Length'."
            ) if preflight["duplicate_identical"] else (
                "Both columns present and NOT identical — retaining both."
            ),
        },

        # Final feature schema
        "D_final": D,
        "feature_list": feature_list,
        "meta_columns": sorted(META_COLS),
        "shortcut_candidates_verified": CANDIDATE_SHORTCUT_POOL,

        # Label balance
        "train_n_rows": len(train_df),
        "train_n_benign": n_benign,
        "train_n_attack": n_attack,
        "pos_weight_reference_for_sprint4_ae": pos_weight_ref,

        # Scaler
        "scaler": {
            "type": "StandardScaler",
            "fit_on": "TRAIN_ONLY",
            "artifact_path": str(scaler_result["scaler_path"].relative_to(ROOT)),
            "artifact_sha256": scaler_result["scaler_sha256"],
            **scaler_result["scaler_metadata"],
        },
    }

    schema_path = OUT_DIR / "feature_schema.json"
    schema_bytes = json.dumps(feature_schema, indent=2).encode("utf-8")
    with open(schema_path, "wb") as f:
        f.write(schema_bytes)
    schema_hash = sha256_bytes(schema_bytes)
    logger.info("Feature schema saved: %s | SHA-256: %s", schema_path.name, schema_hash)

    # --- Log1p metadata ---
    log1p_path = OUT_DIR / "log1p_sensitivity_metadata.json"
    with open(log1p_path, "w", encoding="utf-8") as f:
        json.dump(log1p_meta, f, indent=2)
    logger.info("Log1p sensitivity metadata saved: %s", log1p_path.name)

    # --- Population verification results ---
    pop_path = OUT_DIR / "population_verification.json"
    with open(pop_path, "w", encoding="utf-8") as f:
        json.dump(pop_check, f, indent=2)

    # --- Summary ---
    logger.info("=" * 70)
    logger.info("STEP 1 SUMMARY")
    logger.info("  D_raw_features:    %d", preflight["raw_feature_columns"])
    logger.info("  D_final:           %d", D)
    logger.info("  Duplicate decision: %s", preflight["duplicate_decision"])
    logger.info("  Scaler SHA-256:    %s", scaler_result["scaler_sha256"])
    logger.info("  Schema SHA-256:    %s", schema_hash)
    logger.info("  Log1p qualifying:  %d features", log1p_meta["qualifying_count"])
    logger.info("STEP 1: PASS")
    logger.info("=" * 70)

    print(f"\n[STEP 1 COMPLETE] D_final={D}  Scaler_SHA256={scaler_result['scaler_sha256'][:16]}...")
    print(f"Feature schema frozen at: {schema_path}")

    return {
        "D_final":          D,
        "feature_list":     feature_list,
        "scaler_result":    scaler_result,
        "schema_sha256":    schema_hash,
        "schema_path":      schema_path,
        "log1p_meta":       log1p_meta,
        "n_benign":         n_benign,
        "n_attack":         n_attack,
        "pos_weight_ref":   pos_weight_ref,
    }


if __name__ == "__main__":
    main()
