#!/usr/bin/env python3
"""
s02_clean_and_preprocess.py — Data Cleaning and Preprocessing for CIC-IDS-2017.

Executes the locked Sprint 2 cleaning protocol:
1. Header normalization: Strip whitespace and resolve duplicate 'Fwd Header Length' (col 55).
2. Label normalization: Resolve encoding corruption in Web Attack labels and map to families.
3. Numeric cleaning in exact order:
   Step 1: Replace +/- inf with NaN.
   Step 2: Drop rows with NaN.
   Step 3: Drop exact duplicate rows.
   Step 4: Identify feature-identical rows with conflicting labels.
   Step 5: Drop conflicting duplicate rows.
   Step 6: Assign persistent row_uid (CIC_XXXXXXX).
4. Feature policy: Drop 8 globally constant zero-variance columns; retain Destination Port.
5. Saves processed dataset to cicids2017/DATA/processed/
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent
CIC_ROOT = SRC_DIR.parent
REPO_ROOT = CIC_ROOT.parent

RAW_DIR = CIC_ROOT / "DATA" / "raw"
PROCESSED_DIR = CIC_ROOT / "DATA" / "processed"
AUDIT_DIR = CIC_ROOT / "DATA" / "audit"
LOGS_DIR = REPO_ROOT / "logs" / "cicids2017_revision_v1"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 8 globally constant zero-variance columns across all 2.83M rows
GLOBAL_CONSTANT_FEATURES = [
    "Bwd Avg Packets/Bulk",
    "Bwd PSH Flags",
    "Bwd Avg Bulk Rate",
    "Bwd URG Flags",
    "Fwd Avg Bulk Rate",
    "Fwd Avg Bytes/Bulk",
    "Fwd Avg Packets/Bulk",
    "Bwd Avg Bytes/Bulk",
]

# Attack family mapping
FAMILY_MAPPING = {
    "BENIGN": "BENIGN",
    "DoS Hulk": "DoS",
    "DoS GoldenEye": "DoS",
    "DoS slowloris": "DoS",
    "DoS Slowhttptest": "DoS",
    "DDoS": "DDoS",
    "PortScan": "PortScan",
    "FTP-Patator": "Brute Force",
    "SSH-Patator": "Brute Force",
    "Web Attack Brute Force": "Web Attack",
    "Web Attack XSS": "Web Attack",
    "Web Attack Sql Injection": "Web Attack",
    "Bot": "Bot",
    "Infiltration": "Infiltration",
    "Heartbleed": "Heartbleed",
}


def normalize_label(val: str) -> str:
    s = str(val).strip()
    # Resolve corrupted non-ASCII en-dash
    if "Web Attack" in s:
        if "Brute" in s:
            return "Web Attack Brute Force"
        elif "XSS" in s:
            return "Web Attack XSS"
        elif "Sql" in s or "SQL" in s:
            return "Web Attack Sql Injection"
    return s


def run_cleaning_pipeline():
    print("[CLEANING] Starting Sprint 2 cleaning and preprocessing pipeline...")
    raw_files = sorted([f for f in os.listdir(RAW_DIR) if f.endswith(".csv")])
    if len(raw_files) != 8:
        raise RuntimeError(f"Expected 8 raw shards in {RAW_DIR}, found {len(raw_files)}")

    dfs = []
    shard_stats = []
    total_raw_rows = 0

    for fname in raw_files:
        fpath = RAW_DIR / fname
        df = pd.read_csv(fpath, encoding="utf-8", encoding_errors="replace", low_memory=False)
        n_raw = len(df)
        total_raw_rows += n_raw

        # 1. Normalize column names (strip whitespace)
        df.columns = [c.strip() for c in df.columns]

        # 2. Resolve duplicate 'Fwd Header Length' deterministically
        # Drop the second occurrence (col index 55)
        seen = set()
        drop_col_idx = None
        for idx, col in enumerate(df.columns):
            if col in seen:
                drop_col_idx = idx
            seen.add(col)
        if drop_col_idx is not None:
            df = df.iloc[:, [i for i in range(len(df.columns)) if i != drop_col_idx]]

        # Record daily shard tag for day-stratification and audit
        df["shard_source"] = fname

        dfs.append(df)
        shard_stats.append({"shard": fname, "raw_rows": n_raw})
        print(f"  Ingested {fname}: {n_raw:,} rows.")

    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"\n[CLEANING] Total raw combined rows: {len(combined_df):,}")

    # Label column
    lbl_col = "Label"
    raw_label_counts = combined_df[lbl_col].value_counts().to_dict()

    # Normalize labels
    combined_df["label_clean"] = combined_df[lbl_col].apply(normalize_label)
    combined_df["attack_family"] = combined_df["label_clean"].map(FAMILY_MAPPING)

    if combined_df["attack_family"].isna().any():
        unmapped = combined_df[combined_df["attack_family"].isna()]["label_clean"].unique()
        raise RuntimeError(f"Unmapped labels found: {unmapped}")

    # Identify feature columns
    non_feature_cols = ["Label", "label_clean", "attack_family", "shard_source"]
    feature_cols = [c for c in combined_df.columns if c not in non_feature_cols]

    # Convert features to numeric
    for col in feature_cols:
        combined_df[col] = pd.to_numeric(combined_df[col], errors="coerce")

    # Step 1: Detect and replace +/- Inf with NaN
    inf_mask = np.isinf(combined_df[feature_cols].values).any(axis=1)
    n_inf_rows = int(inf_mask.sum())
    print(f"[CLEANING] Step 1: Identified {n_inf_rows:,} rows with Infinite values (+/- inf).")
    combined_df[feature_cols] = combined_df[feature_cols].replace([np.inf, -np.inf], np.nan)

    # Step 2: Drop rows with NaN
    nan_mask = combined_df[feature_cols].isna().any(axis=1)
    n_nan_rows = int(nan_mask.sum())
    print(f"[CLEANING] Step 2: Identified {n_nan_rows:,} rows containing NaN (including converted Infs).")
    clean_numeric_df = combined_df[~nan_mask].copy()
    n_after_nan = len(clean_numeric_df)
    print(f"  Remaining after NaN removal: {n_after_nan:,}")

    # Step 3: Remove exact duplicate rows (across all features + label_clean)
    all_content_cols = feature_cols + ["label_clean"]
    dup_mask = clean_numeric_df.duplicated(subset=all_content_cols)
    n_exact_dups = int(dup_mask.sum())
    print(f"[CLEANING] Step 3: Identified {n_exact_dups:,} exact duplicate rows.")
    dedup_df = clean_numeric_df[~dup_mask].copy()
    n_after_dedup = len(dedup_df)
    print(f"  Remaining after exact deduplication: {n_after_dedup:,}")

    # Step 4 & 5: Identify and remove feature-identical rows with conflicting labels.
    # Note on Issue 1 verification:
    # Because Step 3 eliminated duplicate copies of exact matches across (feature_cols + [label_clean]),
    # every row in dedup_df has a unique (features, label) tuple.
    # Consequently, any row in dedup_df that shares feature_cols with another row MUST have a conflicting label.
    # Exactly 1,394 rows (697 pairs with 2 conflicting labels) are removed; 0 same-label duplicates are dropped here.
    feat_conflict_mask = dedup_df.duplicated(subset=feature_cols, keep=False)
    n_conflict_rows = int(feat_conflict_mask.sum())
    print(f"[CLEANING] Step 4 & 5: Identified {n_conflict_rows:,} feature-identical rows with conflicting labels.")
    final_df = dedup_df[~feat_conflict_mask].copy()
    n_final_cleaned = len(final_df)
    print(f"  Remaining after conflicting label removal: {n_final_cleaned:,}")

    # Step 6: Assign persistent deterministic row_uid
    final_df.sort_values(by=["shard_source", "label_clean"] + feature_cols[:3], inplace=True)
    final_df.reset_index(drop=True, inplace=True)
    final_df["row_uid"] = [f"CIC_{i+1:07d}" for i in range(n_final_cleaned)]

    # Feature Policy: Drop the 8 globally constant zero-variance features
    print(f"[CLEANING] Dropping {len(GLOBAL_CONSTANT_FEATURES)} globally constant zero-variance features:")
    for gf in GLOBAL_CONSTANT_FEATURES:
        print(f"  - {gf}")
    final_df.drop(columns=GLOBAL_CONSTANT_FEATURES, inplace=True)

    # Retain Destination Port
    if "Destination Port" not in final_df.columns:
        raise RuntimeError("Destination Port was inadvertently dropped!")
    print("[CLEANING] Destination Port retained for shortcut-learning analysis.")

    # Save cleaned processed dataset as CSV
    out_csv = PROCESSED_DIR / "cleaned_cicids2017.csv"
    print(f"\n[CLEANING] Saving cleaned dataset to {out_csv.as_posix()}...")
    final_df.to_csv(out_csv, index=False)

    # Save cleaning audit log
    audit_data = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_raw_rows": total_raw_rows,
        "step1_infinite_rows": n_inf_rows,
        "step2_nan_rows_removed": n_nan_rows,
        "rows_after_nan_removal": n_after_nan,
        "step3_exact_duplicates_removed": n_exact_dups,
        "rows_after_exact_dedup": n_after_dedup,
        "step4_5_conflicting_label_duplicates_removed": n_conflict_rows,
        "step6_final_cleaned_rows": n_final_cleaned,
        "features_retained_count": len([c for c in final_df.columns if c not in ["Label", "label_clean", "attack_family", "shard_source", "row_uid"]]),
        "global_constant_features_dropped": GLOBAL_CONSTANT_FEATURES,
        "cleaned_label_distribution": {str(k): int(v) for k, v in final_df["label_clean"].value_counts().items()},
        "cleaned_family_distribution": {str(k): int(v) for k, v in final_df["attack_family"].value_counts().items()}
    }

    with open(AUDIT_DIR / "cleaning_audit.json", "w", encoding="utf-8") as fp:
        json.dump(audit_data, fp, indent=2)

    print(f"[CLEANING] Complete. Final Cleaned Rows: {n_final_cleaned:,}")
    print(f"[CLEANING] Cleaning audit written to {(AUDIT_DIR / 'cleaning_audit.json').as_posix()}")


if __name__ == "__main__":
    run_cleaning_pipeline()
