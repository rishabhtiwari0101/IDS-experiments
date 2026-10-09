"""
cicids2017/run_all.py
---------------------
Sprint 7 — Master Reproducibility Pipeline Runner.

Orchestrates the entire CIC-IDS-2017 revision experimental pipeline in exact
preregistered sequential order from Sprint 2 to Sprint 6.

Supports:
  --dry-run              Verifies existence and dependency readiness of all stages without executing.
  --eval-only            Executes only evaluation, benchmarking, tables, and figures stages.
  --from-step <step_id>  Resumes execution from a specific step (e.g. s23).
  --step <step_id>       Executes a single specified step.
  --log-dir <dir>        Custom log directory (defaults to logs/cicids2017_revision_v1).
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "cicids2017" / "src"
CONFIG_PATH = ROOT / "configs" / "cicids2017_revision_v1.yaml"
DEFAULT_LOG_DIR = ROOT / "logs" / "cicids2017_revision_v1"

# The 25 canonical ordered pipeline stages
PIPELINE_STAGES = [
    {
        "id": "s01",
        "name": "Audit Raw PCAP Shards",
        "script": "s01_audit_raw.py",
        "category": "data_preparation",
        "is_training": False,
        "description": "Verifies official UNB raw machine learning CSV release shards and hashes.",
    },
    {
        "id": "s02",
        "name": "Clean and Preprocess",
        "script": "s02_clean_and_preprocess.py",
        "category": "data_preparation",
        "is_training": False,
        "description": "Removes infinites, NaNs, exact duplicates, and conflicting-label flows.",
    },
    {
        "id": "s03",
        "name": "Generate Population Splits",
        "script": "s03_generate_splits.py",
        "category": "data_preparation",
        "is_training": False,
        "description": "Generates 8 population splits using stratified row fallback.",
    },
    {
        "id": "s04",
        "name": "Verify Splits & Invariants",
        "script": "s04_verify_splits_and_invariants.py",
        "category": "evaluation",
        "is_training": False,
        "description": "Formally verifies row UID pairwise disjointness and conservation accounting.",
    },
    {
        "id": "s05",
        "name": "Preflight and Preprocessing",
        "script": "s05_preflight_and_preprocessing.py",
        "category": "preprocessing",
        "is_training": False,
        "description": "Standardizes numeric flow features and fits scalers strictly on TRAIN.",
    },
    {
        "id": "s06",
        "name": "Mutual Information Selection",
        "script": "s06_mutual_information.py",
        "category": "feature_selection",
        "is_training": True,
        "description": "Computes mutual information on TRAIN and establishes K*=69 feature subset.",
    },
    {
        "id": "s07",
        "name": "Base Models Training",
        "script": "s07_base_models_training.py",
        "category": "model_training",
        "is_training": True,
        "description": "Trains DT, RF, Linear SVC, and IDSNet (MLP) across seeds [42, 123, 2024].",
    },
    {
        "id": "s08",
        "name": "OOF Stacking Training",
        "script": "s08_oof_stacking.py",
        "category": "model_training",
        "is_training": True,
        "description": "Performs 5-fold cross-validation within TRAIN to fit meta-learner logistic regression.",
    },
    {
        "id": "s09",
        "name": "TreeSHAP Shortcut Freeze",
        "script": "s09_treeshap_shortcut_freeze.py",
        "category": "shortcut_freeze",
        "is_training": False,
        "description": "Computes TreeSHAP attributions and freezes shortcut features before zero-day eval.",
    },
    {
        "id": "s10",
        "name": "Evaluate DEV_TEST",
        "script": "s10_evaluate_dev_test.py",
        "category": "evaluation",
        "is_training": False,
        "description": "Evaluates base and stacking models on 743,921 DEV_TEST flows.",
    },
    {
        "id": "s12",
        "name": "Train Autoencoder",
        "script": "s12_train_autoencoder.py",
        "category": "model_training",
        "is_training": True,
        "description": "Trains Standard and Log1p Autoencoders on 44,800 benign TRAIN flows.",
    },
    {
        "id": "s13",
        "name": "Train Isolation Forest",
        "script": "s13_train_isolation_forest.py",
        "category": "model_training",
        "is_training": True,
        "description": "Trains Isolation Forest on 44,800 benign TRAIN flows.",
    },
    {
        "id": "s14",
        "name": "Calibrate Thresholds & Heavy Tail",
        "script": "s14_calibrate_thresholds_and_heavy_tail.py",
        "category": "calibration",
        "is_training": False,
        "description": "Computes parametric, scaled-MAD, and empirical quantile thresholds on CALIBRATION.",
    },
    {
        "id": "s15",
        "name": "Evaluate Zero-Day Attacks",
        "script": "s15_evaluate_zero_day.py",
        "category": "evaluation",
        "is_training": False,
        "description": "Evaluates all supervised and unsupervised models on Bot, XSS, and Infiltration.",
    },
    {
        "id": "s16",
        "name": "Hybrid Fusion & Hypotheses",
        "script": "s16_hybrid_fusion_and_hypotheses.py",
        "category": "evaluation",
        "is_training": False,
        "description": "Evaluates OR/AND fusions (C01-C06) and tests formal statistical hypotheses H1-H4.",
    },
    {
        "id": "s17",
        "name": "Train Ablated Base Models",
        "script": "s17_train_ablated_base_models.py",
        "category": "model_training",
        "is_training": True,
        "description": "Trains ablated models (D=67) after removing the two frozen shortcuts.",
    },
    {
        "id": "s18",
        "name": "Ablated OOF Stacking",
        "script": "s18_ablated_oof_stacking.py",
        "category": "model_training",
        "is_training": True,
        "description": "Trains ablated stacking ensemble (D=67) across 5 folds.",
    },
    {
        "id": "s19",
        "name": "Evaluate Shortcut Ablation",
        "script": "s19_evaluate_shortcut_ablation.py",
        "category": "evaluation",
        "is_training": False,
        "description": "Performs TOST equivalence testing (|Delta| < 0.01) on Random Forest Macro-F1.",
    },
    {
        "id": "s20",
        "name": "TreeSHAP Ablation Shift",
        "script": "s20_treeshap_ablation_shift.py",
        "category": "evaluation",
        "is_training": False,
        "description": "Analyzes feature attribution redistribution following shortcut removal.",
    },
    {
        "id": "s21",
        "name": "Train FT-Transformer CIC",
        "script": "s21_train_ft_transformer_cic.py",
        "category": "model_training",
        "is_training": True,
        "description": "Trains and evaluates FT-Transformer on CIC-IDS-2017 (Full and Ablated).",
    },
    {
        "id": "s22",
        "name": "Train FT-Transformer UNSW",
        "script": "s22_train_ft_transformer_unsw.py",
        "category": "model_training",
        "is_training": True,
        "description": "Trains and evaluates modern FT-Transformer baseline on frozen UNSW-NB15 (K=50).",
    },
    {
        "id": "s23",
        "name": "Matched-FPR Analysis",
        "script": "s23_matched_fpr_analysis.py",
        "category": "evaluation",
        "is_training": False,
        "description": "Calibrates models across 4 nominal false-alarm budgets (0.1%, 0.5%, 1%, 5%).",
    },
    {
        "id": "s24",
        "name": "Deployment Benchmark",
        "script": "s24_deployment_benchmark.py",
        "category": "evaluation",
        "is_training": False,
        "description": "Benchmarks local inference latency and throughput across 1k, 10k, and 100k flows.",
    },
    {
        "id": "s25",
        "name": "Cross-Dataset Master Table",
        "script": "s25_cross_dataset_table.py",
        "category": "reporting",
        "is_training": False,
        "description": "Synthesizes 15 comparative dimensions between UNSW-NB15 and CIC-IDS-2017.",
    },
    {
        "id": "s26",
        "name": "Generate Publication Figures",
        "script": "s26_generate_figures.py",
        "category": "reporting",
        "is_training": False,
        "description": "Generates publication Figures 1-4 in 300 DPI PNG and vector PDF formats.",
    },
]


def setup_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "pipeline_run.log"

    logger = logging.getLogger("run_all")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def parse_args():
    parser = argparse.ArgumentParser(description="CIC-IDS-2017 Master Reproducibility Pipeline Runner")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and validate stages without executing.")
    parser.add_argument("--eval-only", action="store_true", help="Run only evaluation/benchmarking/reporting stages.")
    parser.add_argument("--from-step", type=str, default=None, help="Resume pipeline from specified step ID (e.g. s23).")
    parser.add_argument("--step", type=str, default=None, help="Execute only a single specified step ID (e.g. s26).")
    parser.add_argument("--log-dir", type=str, default=str(DEFAULT_LOG_DIR), help="Log output directory.")
    return parser.parse_args()


def filter_stages(args) -> list[dict]:
    stages = list(PIPELINE_STAGES)

    if args.step:
        target = args.step.lower()
        stages = [s for s in stages if s["id"].lower() == target]
        if not stages:
            raise ValueError(f"Unknown step ID: {args.step}. Available: {[s['id'] for s in PIPELINE_STAGES]}")
        return stages

    if args.from_step:
        target = args.from_step.lower()
        idx = next((i for i, s in enumerate(stages) if s["id"].lower() == target), None)
        if idx is None:
            raise ValueError(f"Unknown from-step ID: {args.from_step}. Available: {[s['id'] for s in PIPELINE_STAGES]}")
        stages = stages[idx:]

    if args.eval_only:
        stages = [s for s in stages if not s["is_training"]]

    return stages


def main():
    args = parse_args()
    log_dir = Path(args.log_dir).resolve()
    logger = setup_logger(log_dir)

    logger.info("=" * 75)
    logger.info("CIC-IDS-2017 MASTER PIPELINE RUNNER (run_all.py)")
    logger.info("=" * 75)
    logger.info("Repository Root: %s", ROOT)
    logger.info("Config Path:     %s", CONFIG_PATH)
    logger.info("Log Directory:   %s", log_dir)
    logger.info("Mode:            %s", "DRY-RUN (Inspection Only)" if args.dry_run else ("EVAL-ONLY" if args.eval_only else "FULL PIPELINE"))

    # Verify config exists
    if not CONFIG_PATH.exists():
        logger.error("Configuration file missing: %s", CONFIG_PATH)
        sys.exit(1)

    try:
        stages = filter_stages(args)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info("Selected Pipeline Stages: %d stages", len(stages))
    for i, st in enumerate(stages, 1):
        mode_badge = "[EVAL/REPORT]" if not st["is_training"] else "[TRAINING]"
        logger.info("  %2d. [%-3s] %-12s %-32s (%s)", i, st["id"], mode_badge, st["name"], st["script"])

    if args.dry_run:
        logger.info("-" * 75)
        logger.info("VALIDATING STAGES IN DRY-RUN MODE...")
        all_scripts_exist = True
        for st in stages:
            script_path = SRC_DIR / st["script"]
            exists = script_path.exists()
            status = "FOUND" if exists else "MISSING"
            if not exists:
                all_scripts_exist = False
                logger.error("  [!] Script missing: %s (%s)", st["script"], script_path)
            else:
                logger.info("  [OK] %-3s: %-32s -> %s", st["id"], st["script"], status)

        logger.info("-" * 75)
        if all_scripts_exist:
            logger.info("DRY-RUN RESULT: PASS — All %d stages are present and validated.", len(stages))
            sys.exit(0)
        else:
            logger.error("DRY-RUN RESULT: FAIL — One or more scripts are missing.")
            sys.exit(1)

    # Execution Mode
    logger.info("-" * 75)
    logger.info("EXECUTING PIPELINE STAGES...")
    start_time = time.perf_counter()

    for i, st in enumerate(stages, 1):
        script_path = SRC_DIR / st["script"]
        logger.info("=" * 75)
        logger.info("STAGE %d/%d: [%s] %s", i, len(stages), st["id"], st["name"])
        logger.info("Script: %s", script_path)
        logger.info("Description: %s", st["description"])
        logger.info("-" * 75)

        if not script_path.exists():
            logger.error("Script file does not exist: %s", script_path)
            sys.exit(1)

        t_stage_start = time.perf_counter()
        cmd = [sys.executable, str(script_path)]

        # Execute synchronously
        result = subprocess.run(cmd, cwd=ROOT, capture_output=False)
        t_stage_elapsed = time.perf_counter() - t_stage_start

        if result.returncode != 0:
            logger.error("STAGE FAILED: [%s] %s exited with code %d (Elapsed: %.2fs)",
                         st["id"], st["script"], result.returncode, t_stage_elapsed)
            logger.error("Pipeline aborted to protect invariant integrity.")
            sys.exit(result.returncode)

        logger.info("STAGE PASSED: [%s] completed in %.2fs", st["id"], t_stage_elapsed)

    total_elapsed = time.perf_counter() - start_time
    logger.info("=" * 75)
    logger.info("ALL %d PIPELINE STAGES COMPLETED SUCCESSFULLY in %.2fs (%.2fm)",
                len(stages), total_elapsed, total_elapsed / 60.0)
    logger.info("=" * 75)


if __name__ == "__main__":
    main()
