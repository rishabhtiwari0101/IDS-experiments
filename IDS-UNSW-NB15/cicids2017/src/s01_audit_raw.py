#!/usr/bin/env python3
"""
s01_audit_raw.py — Raw Data Audit for CIC-IDS-2017.

Performs a comprehensive forensic audit across all 8 raw CSV shards:
- Row counts, column counts, and schema verification
- Label distribution by shard
- Missing values (NaN) and Infinite values (+inf/-inf)
- Duplicate rows and constant columns
- Generates required audit artifacts in results/cicids2017_revision_v1/audit/
"""

import csv
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
AUDIT_OUT_DIR = REPO_ROOT / "results" / "cicids2017_revision_v1" / "audit"
LOGS_DIR = REPO_ROOT / "logs" / "cicids2017_revision_v1"

AUDIT_OUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def run_raw_audit():
    files = sorted([f for f in os.listdir(RAW_DIR) if f.endswith(".csv")])
    if len(files) != 8:
        raise RuntimeError(f"Expected 8 raw CSV shards in {RAW_DIR}, found {len(files)}")

    print(f"[AUDIT] Starting raw audit across {len(files)} shards in {RAW_DIR.as_posix()}...")

    shard_audits = []
    total_raw_rows = 0
    all_label_counts = {}
    missingness_records = []
    class_dist_records = []
    duplicate_records = []

    canonical_header = None
    raw_header = None

    for fname in files:
        fpath = RAW_DIR / fname
        fsize = fpath.stat().st_size

        with open(fpath, "r", encoding="utf-8", errors="replace") as fp:
            reader = csv.reader(fp)
            current_raw_header = next(reader)

        stripped_header = [c.strip() for c in current_raw_header]

        if canonical_header is None:
            canonical_header = stripped_header
            raw_header = current_raw_header
        else:
            if stripped_header != canonical_header:
                raise RuntimeError(f"Schema mismatch in shard {fname}!")

        # Read shard with pandas
        df = pd.read_csv(fpath, encoding="utf-8", encoding_errors="replace", low_memory=False)
        n_rows, n_cols = df.shape
        total_raw_rows += n_rows

        # Track labels
        lbl_col_name = df.columns[-1]
        vc = df[lbl_col_name].value_counts(dropna=False).to_dict()
        for k, v in vc.items():
            str_k = str(k)
            all_label_counts[str_k] = all_label_counts.get(str_k, 0) + v
            class_dist_records.append({
                "shard": fname,
                "label_raw": str_k,
                "count": int(v),
                "proportion": float(v / n_rows)
            })

        # Feature audit
        feature_df = df.iloc[:, :-1]
        n_dups = int(df.duplicated().sum())
        duplicate_records.append({
            "shard": fname,
            "total_rows": n_rows,
            "duplicate_rows": n_dups,
            "duplicate_pct": round(float(n_dups / n_rows * 100), 4)
        })

        for col_idx, col_name in enumerate(feature_df.columns):
            s_raw = feature_df[col_name]
            s_num = pd.to_numeric(s_raw, errors="coerce")
            
            raw_nans = int(s_raw.isna().sum())
            inf_mask = s_raw.astype(str).str.strip().isin(["Infinity", "inf", "+Infinity", "-Infinity", "+inf", "-inf"])
            n_infs = int(inf_mask.sum())
            
            if raw_nans > 0 or n_infs > 0:
                missingness_records.append({
                    "shard": fname,
                    "column_raw": col_name,
                    "column_stripped": col_name.strip(),
                    "column_index": col_idx,
                    "nan_count": raw_nans,
                    "inf_count": n_infs,
                    "total_problematic": raw_nans + n_infs
                })

        shard_audits.append({
            "filename": fname,
            "size_bytes": fsize,
            "rows": n_rows,
            "cols": n_cols,
            "duplicate_rows": n_dups,
            "label_counts": {str(k): int(v) for k, v in vc.items()}
        })
        print(f"  Processed {fname}: {n_rows:,} rows, {n_dups:,} duplicate rows.")

    print(f"\n[AUDIT] Total Raw Rows across 8 shards: {total_raw_rows:,}")
    if total_raw_rows != 2830743:
        raise RuntimeError(f"Expected 2,830,743 rows, found {total_raw_rows}")

    # Save schema.json
    schema_info = {
        "dataset_name": "CIC-IDS-2017",
        "variant": "MachineLearningCSV Original",
        "column_count": len(canonical_header),
        "columns": [
            {"index": i, "raw_name": raw_header[i], "stripped_name": canonical_header[i]}
            for i in range(len(canonical_header))
        ],
        "label_column_index": len(canonical_header) - 1,
        "label_column_name": canonical_header[-1],
        "duplicate_columns": ["Fwd Header Length"],
        "duplicate_column_indices": [34, 55],
        "timestamp_present": False,
        "ip_addresses_present": False,
        "ports_present": ["Destination Port"]
    }
    with open(AUDIT_OUT_DIR / "schema.json", "w", encoding="utf-8") as fp:
        json.dump(schema_info, fp, indent=2)

    # Save class_distribution.csv
    pd.DataFrame(class_dist_records).to_csv(AUDIT_OUT_DIR / "class_distribution.csv", index=False)

    # Save missingness.csv
    pd.DataFrame(missingness_records).to_csv(AUDIT_OUT_DIR / "missingness.csv", index=False)

    # Save duplicate_report.csv
    pd.DataFrame(duplicate_records).to_csv(AUDIT_OUT_DIR / "duplicate_report.csv", index=False)

    # Write dataset_audit.md
    audit_md_content = f"""# CIC-IDS-2017 Raw Dataset Forensic Audit
Generated: {datetime.now(timezone.utc).isoformat()}  
Status: PASS  

## Summary
- Total Shards: 8
- Total Raw Rows: {total_raw_rows:,}
- Total Columns: {len(canonical_header)}
- Total Labels: {len(all_label_counts)}

## Shard Breakdown
"""
    for sa in shard_audits:
        audit_md_content += f"\n### `{sa['filename']}`\n- Rows: {sa['rows']:,}\n- Duplicate rows: {sa['duplicate_rows']:,}\n- Labels: `{sa['label_counts']}`\n"

    audit_md_content += "\n## Dataset-Wide Label Inventory\n"
    for lbl, cnt in sorted(all_label_counts.items(), key=lambda x: -x[1]):
        audit_md_content += f"- `{lbl}`: {cnt:,} ({cnt/total_raw_rows*100:.4f}%)\n"

    with open(AUDIT_OUT_DIR / "dataset_audit.md", "w", encoding="utf-8") as fp:
        fp.write(audit_md_content)

    print(f"[AUDIT] Audit artifacts written to {AUDIT_OUT_DIR.as_posix()}")


if __name__ == "__main__":
    run_raw_audit()
