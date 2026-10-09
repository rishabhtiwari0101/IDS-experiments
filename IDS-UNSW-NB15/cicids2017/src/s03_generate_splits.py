#!/usr/bin/env python3
"""
s03_generate_splits.py — Leakage-Controlled Partition Splitter for CIC-IDS-2017.

Implements the locked pre-registration split protocol:
- Reads configuration from configs/cicids2017_revision_v1.yaml
- Isolates protected and unseen populations:
    * PROTECTED_BOT (Bot)
    * UNSEEN_XSS (Web Attack XSS)
    * UNSEEN_INFILTRATION (Infiltration)
    * EXCLUDED_SMALL (Web Attack Sql Injection, Heartbleed)
- Isolates pure benign evaluation controls:
    * CALIBRATION (min 18,500 benign flows, stratified by daily shard)
    * EVAL_CONTROL (min 18,500 benign flows, disjoint, stratified by daily shard)
- Splits development pool into TRAIN (70%) and DEV_TEST (30%) via STRATIFIED_ROW_FALLBACK
- Verifies pairwise disjointness and exact row conservation
- Saves 8 partition CSVs into cicids2017/DATA/splits/
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit, train_test_split
import yaml

SRC_DIR = Path(__file__).resolve().parent
CIC_ROOT = SRC_DIR.parent
REPO_ROOT = CIC_ROOT.parent

CONFIG_PATH = REPO_ROOT / "configs" / "cicids2017_revision_v1.yaml"
PROCESSED_FILE = CIC_ROOT / "DATA" / "processed" / "cleaned_cicids2017.csv"
SPLITS_DIR = CIC_ROOT / "DATA" / "splits"
AUDIT_DIR = CIC_ROOT / "DATA" / "audit"
LOGS_DIR = REPO_ROOT / "logs" / "cicids2017_revision_v1"

SPLITS_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_split_pipeline():
    config = load_config()
    split_seed = int(config["split_seed"])
    cal_size = int(config["populations"]["min_calibration_benign"])
    eval_ctrl_size = int(config["populations"]["min_eval_control_benign"])
    target_train_benign = int(config["populations"]["target_train_benign"])
    train_benign_subsample_seed = int(config["populations"]["train_benign_subsample_seed"])

    print(f"[SPLIT] Loading cleaned dataset from {PROCESSED_FILE.as_posix()}...")
    df = pd.read_csv(PROCESSED_FILE, encoding="utf-8", low_memory=False)
    n_total = len(df)
    print(f"[SPLIT] Ingested {n_total:,} cleaned rows.")

    # 1. Separate Isolated Zero-Day & Unseen Populations
    print("[SPLIT] Step 1: Isolating zero-day, unseen, and excluded-small populations...")
    bot_df = df[df["label_clean"] == "Bot"].copy()
    xss_df = df[df["label_clean"] == "Web Attack XSS"].copy()
    infil_df = df[df["label_clean"] == "Infiltration"].copy()
    excl_df = df[df["label_clean"].isin(["Web Attack Sql Injection", "Heartbleed"])].copy()

    n_bot = len(bot_df)
    n_xss = len(xss_df)
    n_infil = len(infil_df)
    n_excl = len(excl_df)

    print(f"  PROTECTED_BOT: {n_bot:,} flows.")
    print(f"  UNSEEN_XSS: {n_xss:,} flows.")
    print(f"  UNSEEN_INFILTRATION: {n_infil:,} flows.")
    print(f"  EXCLUDED_SMALL: {n_excl:,} flows.")

    if n_bot < 200:
        raise RuntimeError(f"G12 Blocker: Cleaned Bot count is {n_bot} (< 200 required)!")

    # Exclude isolated rows from remaining pool
    isolated_uids = set(bot_df["row_uid"]).union(xss_df["row_uid"]).union(infil_df["row_uid"]).union(excl_df["row_uid"])
    dev_pool = df[~df["row_uid"].isin(isolated_uids)].copy()
    print(f"  Remaining development pool: {len(dev_pool):,} flows.")

    # 2. Extract Pure Benign Controls (CALIBRATION & EVAL_CONTROL)
    print(f"[SPLIT] Step 2: Sampling CALIBRATION ({cal_size:,}) and EVAL_CONTROL ({eval_ctrl_size:,})...")
    benign_pool = dev_pool[dev_pool["label_clean"] == "BENIGN"].copy()
    known_attacks = dev_pool[dev_pool["label_clean"] != "BENIGN"].copy()
    print(f"  Total Benign flows in dev pool: {len(benign_pool):,}")
    print(f"  Total Known Attack flows: {len(known_attacks):,}")

    # Stratified sampling of benign controls by daily shard
    # First draw CALIBRATION
    sss_cal = StratifiedShuffleSplit(n_splits=1, train_size=cal_size, random_state=split_seed)
    cal_idx, rem_benign_idx = next(sss_cal.split(benign_pool, benign_pool["shard_source"]))

    cal_df = benign_pool.iloc[cal_idx].copy()
    rem_benign_1 = benign_pool.iloc[rem_benign_idx].copy()

    # Next draw EVAL_CONTROL from remaining benign pool
    sss_eval = StratifiedShuffleSplit(n_splits=1, train_size=eval_ctrl_size, random_state=split_seed + 1)
    eval_idx, final_rem_benign_idx = next(sss_eval.split(rem_benign_1, rem_benign_1["shard_source"]))

    eval_ctrl_df = rem_benign_1.iloc[eval_idx].copy()
    rem_dev_benign_df = rem_benign_1.iloc[final_rem_benign_idx].copy()

    print(f"  CALIBRATION benign flows: {len(cal_df):,}")
    print(f"  EVAL_CONTROL benign flows: {len(eval_ctrl_df):,}")
    print(f"  Remaining benign flows for train/dev_test: {len(rem_dev_benign_df):,}")

    # 3. Assemble Core Development Pool for TRAIN / DEV_TEST Split
    print("[SPLIT] Step 3: Splitting core development pool into TRAIN (70%) and DEV_TEST (30%)...")
    core_dev_df = pd.concat([rem_dev_benign_df, known_attacks], ignore_index=True)
    
    # Create compound stratification key: shard + label
    core_dev_df["strat_key"] = core_dev_df["shard_source"] + "___" + core_dev_df["label_clean"]
    
    # Check strata with very few rows (singletons)
    vc = core_dev_df["strat_key"].value_counts()
    singletons = vc[vc < 2].index.tolist()
    if singletons:
        core_dev_df.loc[core_dev_df["strat_key"].isin(singletons), "strat_key"] = "RARE_STRATUM"

    raw_train_df, dev_test_df = train_test_split(
        core_dev_df,
        test_size=0.30,
        random_state=split_seed,
        stratify=core_dev_df["strat_key"]
    )
    raw_train_df = raw_train_df.drop(columns=["strat_key"]).copy()
    dev_test_df = dev_test_df.drop(columns=["strat_key"]).copy()

    # Issue 2 Resolution: Stratified subsampling of TRAIN benign flows to target_train_benign (44,800)
    train_candidate_benign = raw_train_df[raw_train_df["label_clean"] == "BENIGN"].copy()
    train_known_attacks = raw_train_df[raw_train_df["label_clean"] != "BENIGN"].copy()
    n_candidate_benign = len(train_candidate_benign)

    if n_candidate_benign > target_train_benign:
        print(f"[SPLIT] Subsampling TRAIN benign from {n_candidate_benign:,} to target {target_train_benign:,}...")
        sss_sub = StratifiedShuffleSplit(
            n_splits=1,
            train_size=target_train_benign,
            random_state=train_benign_subsample_seed
        )
        sub_idx, unselected_idx = next(sss_sub.split(train_candidate_benign, train_candidate_benign["shard_source"]))
        train_benign_df = train_candidate_benign.iloc[sub_idx].copy()
        unselected_benign_df = train_candidate_benign.iloc[unselected_idx].copy()
        n_unselected_benign = len(unselected_benign_df)
    else:
        train_benign_df = train_candidate_benign
        unselected_benign_df = pd.DataFrame()
        n_unselected_benign = 0

    train_df = pd.concat([train_benign_df, train_known_attacks], ignore_index=True)
    train_df.sort_values(by=["shard_source", "label_clean", "row_uid"], inplace=True)
    train_df.reset_index(drop=True, inplace=True)

    print(f"  TRAIN partition: {len(train_df):,} flows ({len(train_benign_df):,} Benign + {len(train_known_attacks):,} Attacks).")
    print(f"  Explicitly logged removals (unselected benign): {n_unselected_benign:,} flows.")
    print(f"  DEV_TEST partition: {len(dev_test_df):,} flows ({len(dev_test_df[dev_test_df['label_clean'] == 'BENIGN']):,} Benign + {len(dev_test_df[dev_test_df['label_clean'] != 'BENIGN']):,} Attacks).")

    # 4. Invariant Verification
    print("\n[SPLIT] Step 4: Programmatic Invariant Verification...")
    pop_dict = {
        "TRAIN": train_df,
        "DEV_TEST": dev_test_df,
        "CALIBRATION": cal_df,
        "EVAL_CONTROL": eval_ctrl_df,
        "PROTECTED_BOT": bot_df,
        "UNSEEN_XSS": xss_df,
        "UNSEEN_INFILTRATION": infil_df,
        "EXCLUDED_SMALL": excl_df
    }

    # Invariant 1: Pairwise Disjointness
    pop_names = list(pop_dict.keys())
    for i in range(len(pop_names)):
        for j in range(i + 1, len(pop_names)):
            p1, p2 = pop_names[i], pop_names[j]
            overlap = set(pop_dict[p1]["row_uid"]).intersection(set(pop_dict[p2]["row_uid"]))
            if len(overlap) > 0:
                raise RuntimeError(f"Invariant 1 Violated: Overlap between {p1} and {p2} ({len(overlap)} rows)!")
    print("  PASS: Invariant 1 (All 8 populations pairwise disjoint by row_uid).")

    # Invariant 2: Benign Disjointness
    benign_train = set(train_df[train_df["label_clean"] == "BENIGN"]["row_uid"])
    benign_dev = set(dev_test_df[dev_test_df["label_clean"] == "BENIGN"]["row_uid"])
    benign_cal = set(cal_df["row_uid"])
    benign_eval = set(eval_ctrl_df["row_uid"])
    if benign_train.intersection(benign_dev) or benign_train.intersection(benign_cal) or benign_train.intersection(benign_eval):
        raise RuntimeError("Invariant 2 Violated: Benign flow collision!")
    print("  PASS: Invariant 2 (Benign flows strictly disjoint across TRAIN, DEV_TEST, CALIBRATION, EVAL_CONTROL).")

    # Invariant 3: Zero Zero-Day in TRAIN
    forbidden_labels = {"Bot", "Web Attack XSS", "Infiltration", "Web Attack Sql Injection", "Heartbleed"}
    train_labels = set(train_df["label_clean"])
    leaked = forbidden_labels.intersection(train_labels)
    if leaked:
        raise RuntimeError(f"Invariant 3 Violated: Zero-day leaked into TRAIN: {leaked}")
    print("  PASS: Invariant 3 (Zero protected or unseen families enter TRAIN).")

    # Invariant 7: Conservation Accounting
    sum_pop_rows = sum(len(p) for p in pop_dict.values())
    total_accounted = sum_pop_rows + n_unselected_benign
    if total_accounted != n_total:
        raise RuntimeError(f"Invariant 7 Violated: Conservation failure! Cleaned={n_total:,}, Accounted={total_accounted:,} (Populations={sum_pop_rows:,}, Removals={n_unselected_benign:,})")
    print(f"  PASS: Invariant 7 (Exact row conservation: {sum_pop_rows:,} assigned + {n_unselected_benign:,} logged removals == {n_total:,}).")

    # 5. Save Splits as CSV files
    print(f"\n[SPLIT] Step 5: Writing 8 partition CSV files to {SPLITS_DIR.as_posix()}...")
    file_map = {
        "train.csv": train_df,
        "dev_test.csv": dev_test_df,
        "calibration.csv": cal_df,
        "eval_control.csv": eval_ctrl_df,
        "protected_bot.csv": bot_df,
        "unseen_xss.csv": xss_df,
        "unseen_infiltration.csv": infil_df,
        "excluded_small.csv": excl_df
    }

    manifest_records = []
    for fname, p_df in file_map.items():
        out_path = SPLITS_DIR / fname
        p_df.to_csv(out_path, index=False)
        fsize = out_path.stat().st_size
        print(f"  Saved {fname}: {len(p_df):,} rows ({fsize/(1024*1024):.2f} MB).")
        manifest_records.append({
            "population_name": fname.replace(".csv", "").upper(),
            "filename": fname,
            "rows": len(p_df),
            "size_bytes": fsize,
            "class_distribution": {str(k): int(v) for k, v in p_df["label_clean"].value_counts().items()},
            "shard_distribution": {str(k): int(v) for k, v in p_df["shard_source"].value_counts().items()}
        })

    # Save unselected benign uids for complete audit trail
    if n_unselected_benign > 0:
        unselected_audit_file = AUDIT_DIR / "unselected_train_benign_uids.json"
        with open(unselected_audit_file, "w", encoding="utf-8") as fp:
            json.dump({
                "count": n_unselected_benign,
                "target_train_benign": target_train_benign,
                "subsample_seed": train_benign_subsample_seed,
                "uids": unselected_benign_df["row_uid"].tolist()
            }, fp)
        print(f"  Saved unselected benign audit to {unselected_audit_file.as_posix()}")

    # Save split audit log
    with open(AUDIT_DIR / "split_audit.json", "w", encoding="utf-8") as fp:
        json.dump({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "split_seed": split_seed,
            "train_benign_subsample_seed": train_benign_subsample_seed,
            "target_train_benign": target_train_benign,
            "explicitly_logged_removals_count": n_unselected_benign,
            "split_method": "STRATIFIED_ROW_FALLBACK",
            "fallback_reason": "Timestamp column absent in official MachineLearningCSV package",
            "total_cleaned_rows": n_total,
            "total_assigned_population_rows": sum_pop_rows,
            "populations": manifest_records
        }, fp, indent=2)

    print(f"[SPLIT] Split generation complete. Audit written to {(AUDIT_DIR / 'split_audit.json').as_posix()}")


if __name__ == "__main__":
    run_split_pipeline()
