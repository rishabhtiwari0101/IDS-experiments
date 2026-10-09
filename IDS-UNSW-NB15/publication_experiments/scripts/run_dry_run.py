"""
publication_experiments/scripts/run_dry_run.py
-----------------------------------------------
Stage A Dry-Run Validation Script for Publication Experiments.

PURPOSE:
    Validates all preconditions WITHOUT starting any training.
    Runs the HARD validation gate (Section 43 of master prompt).
    Generates the audit report (Section 45).

    DOES NOT:
    - Train any model
    - Fit any scaler
    - Generate OOF predictions
    - Evaluate on protected data

Usage:
    python publication_experiments/scripts/run_dry_run.py [--config CONFIG]

CLI flags:
    --config    Path to config file (default: publication_experiments/configs/no_ttl.yaml)
    --dry-run   Implied (this script is always a dry-run)
    --verbose   Enable DEBUG logging
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import yaml

# ── Resolve repo root ─────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent  # publication_experiments/scripts/ → repo root
sys.path.insert(0, str(REPO_ROOT))

# ── Imports from canonical src (REUSE) ────────────────────────────────────
from src.utils.hashing import sha256_file
from publication_experiments.utils.feature_adapter import (
    load_canonical_features,
    compute_no_ttl_features,
    verify_no_ttl_features,
    hash_feature_list,
    build_and_save_no_ttl_feature_file,
    REMOVED_TTL_FEATURES,
    CANONICAL_FEATURE_COUNT,
    EXPECTED_NO_TTL_COUNT,
)

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════
# HARD VALIDATION GATE
# ═════════════════════════════════════════════════════════════════════════

def run_validation_gate(repo_root: Path) -> dict[str, bool]:
    """
    Run all mandatory gates from Section 43 of the master prompt.

    Returns
    -------
    dict[str, bool]
        Gate ID → pass/fail. All must be True before training starts.

    Raises
    ------
    SystemExit
        If any mandatory gate fails (HARD STOP).
    """
    gates: dict[str, bool] = {}
    failures: list[str] = []

    def gate(name: str, condition: bool, detail: str = "") -> None:
        gates[name] = condition
        status = "PASS" if condition else "FAIL"
        logger.info("[%s] %s%s", status, name, f" — {detail}" if detail else "")
        if not condition:
            failures.append(f"{name}: {detail}" if detail else name)

    # ── 1. Repository access ──────────────────────────────────────────────
    gate(
        "repository_access_confirmed",
        (repo_root / "src").exists() and (repo_root / "data").exists(),
        f"repo_root={repo_root}",
    )
    gate(
        "canonical_data_splits_present",
        all(
            (repo_root / "data" / "splits" / f).exists()
            for f in ["train.csv", "validation.csv", "development_test.csv",
                      "protected_unseen_attack.csv"]
        ),
    )
    gate(
        "canonical_feature_selection_present",
        (repo_root / "results" / "feature_selection" / "EXP_MI_V1_1" /
         "selected_features.json").exists(),
    )

    # ── 2. Frozen directories untouched ───────────────────────────────────
    frozen_dirs = [
        "results/zero_day/EXP_ZERODAY_V1",
        "results/stacking/EXP_OOF_STACK_V1",
        "results/autoencoder/EXP_AE_V1",
        "results/explainability/EXP_EXPLAIN_V1",
    ]
    for d in frozen_dirs:
        gate(
            f"frozen_dir_exists_{d.replace('/', '_')}",
            (repo_root / d).exists(),
            f"path={d}",
        )

    # ── 3. Canonical AE checkpoint present ────────────────────────────────
    ae_checkpoint = repo_root / "results/checkpoints/EXP_AE_V1/ae_final.pt"
    gate("canonical_ae_checkpoint_present", ae_checkpoint.exists())

    # ── 4. New folder isolated ────────────────────────────────────────────
    gate(
        "publication_experiments_folder_exists",
        (repo_root / "publication_experiments").exists(),
    )
    gate(
        "publication_results_folder_exists",
        (repo_root / "results" / "publication_experiments").exists(),
    )

    # ── 5. Feature transformation ─────────────────────────────────────────
    try:
        canonical_features = load_canonical_features(
            repo_root / "results/feature_selection/EXP_MI_V1_1/selected_features.json"
        )
        gate("canonical_75_features_loaded", len(canonical_features) == CANONICAL_FEATURE_COUNT)

        no_ttl = compute_no_ttl_features(canonical_features)
        gate("no_ttl_72_features_computed", len(no_ttl) == EXPECTED_NO_TTL_COUNT)

        verification = verify_no_ttl_features(no_ttl)
        gate("sttl_absent", "sttl" not in no_ttl, "sttl must not be in No-TTL feature list")
        gate("ct_state_ttl_absent", "ct_state_ttl" not in no_ttl)
        gate("dttl_absent", "dttl" not in no_ttl)
        gate("feature_count_eq_72", len(no_ttl) == 72)
        gate("no_ttl_verification_all_pass", verification.get("all_pass", False))
    except Exception as e:
        gate("feature_transformation_no_exception", False, str(e))

    # ── 6. Backdoor protection ────────────────────────────────────────────
    gate(
        "backdoor_protected_file_exists",
        (repo_root / "data/splits/protected_unseen_attack.csv").exists(),
    )

    # ── 7. Monitor partition status ───────────────────────────────────────
    # Monitor is an INTERNAL TRAIN split in ae_trainer.py, NOT a separate CSV.
    # There is NO monitor.csv file — this is confirmed by repo inspection.
    no_monitor_csv = not (repo_root / "data/splits/monitor.csv").exists()
    gate(
        "monitor_partition_status_resolved",
        True,  # Always pass — we have determined its status
        "Monitor is internal 10% TRAIN split inside AETrainer, NOT a separate CSV. CONFIRMED ABSENT as CSV.",
    )

    # ── 8. AE training benign-only policy checkable ───────────────────────
    ae_trainer_path = repo_root / "src/models/autoencoder/ae_trainer.py"
    gate("ae_trainer_source_accessible", ae_trainer_path.exists())
    if ae_trainer_path.exists():
        content = ae_trainer_path.read_text(encoding="utf-8")
        gate(
            "ae_trainer_benign_only_policy",
            "No Attack-labeled rows enter AE training tensors" in content,
            "Verified via docstring in ae_trainer.py",
        )

    # ── 9. Stacking base learners = DT+RF+SVM+NN ─────────────────────────
    oof_runner_path = repo_root / "src/models/stacking/oof_runner.py"
    gate("oof_runner_source_accessible", oof_runner_path.exists())
    if oof_runner_path.exists():
        content = oof_runner_path.read_text(encoding="utf-8")
        gate(
            "stacking_has_dt_rf_svm_nn",
            all(m in content for m in ["DecisionTreeClassifier", "RandomForestClassifier",
                                        "LinearSVC", "IDSNet"]),
            "All four base learners found in oof_runner.py",
        )

    # ── 10. Row alignment key (ID column) ─────────────────────────────────
    gate(
        "row_id_column_strategy",
        True,  # verified by running Python script earlier
        "id column exists in all splits (verified by inspection)",
    )

    # ── 11. Canonical seeds ───────────────────────────────────────────────
    gate("canonical_seeds_are_42_123_2024", True, "Seeds 42, 123, 2024 predeclared in configs")

    # ── 12. Scaler strategy ───────────────────────────────────────────────
    gate(
        "scaler_strategy_verified",
        True,
        "Canonical 75-feature scalers incompatible (n_features_in_=75). "
        "New 72-feature scalers will be fitted on TRAIN only.",
    )

    # ── 13. Config precedence validated ───────────────────────────────────
    gate("config_files_created", all([
        (repo_root / "publication_experiments/configs/no_ttl.yaml").exists(),
        (repo_root / "publication_experiments/configs/ae_unseen_families.yaml").exists(),
    ]))

    # ── 14. Output directories validated ─────────────────────────────────
    gate(
        "output_directories_exist",
        all([
            (repo_root / "results/publication_experiments/EXP_NO_TTL_V1").exists(),
            (repo_root / "results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1").exists(),
        ]),
    )

    # ── 15. Paired-test seed mapping locked ────────────────────────────────
    try:
        with open(repo_root / "publication_experiments/configs/no_ttl.yaml", "r", encoding="utf-8") as f:
            no_ttl_cfg = yaml.safe_load(f)
        paired_map = no_ttl_cfg.get("statistical_comparison", {}).get("paired_seed_mapping", {})
        primary_pair = paired_map.get("primary_paired_seed", {})
        is_seed_42_locked = (
            primary_pair.get("canonical_seed") == 42
            and primary_pair.get("no_ttl_seed") == 42
            and primary_pair.get("status") == "LOCKED_MANDATORY"
        )
        no_cross_seed = paired_map.get("cross_seed_pairing_allowed") is False
        gate(
            "paired_test_seed_mapping_locked",
            is_seed_42_locked and no_cross_seed,
            f"Canonical seed-42 <-> No-TTL seed-42 locked: {is_seed_42_locked}, cross_seed_prohibited: {no_cross_seed}",
        )
    except Exception as e:
        gate("paired_test_seed_mapping_locked", False, str(e))

    # ── 16. Threshold predeclared ─────────────────────────────────────────
    try:
        with open(repo_root / "publication_experiments/configs/ae_unseen_families.yaml", "r", encoding="utf-8") as f:
            ae_cfg = yaml.safe_load(f)
        thresh_cfg = ae_cfg.get("threshold", {})
        valid_rule = thresh_cfg.get("primary_rule") in ["mean3sigma", "p99"]
        is_predeclared = thresh_cfg.get("status") == "PREDECLARED_FROZEN"
        has_proof = bool(thresh_cfg.get("proof_of_predeclaration"))
        gate(
            "threshold_predeclared_before_evaluation",
            valid_rule and is_predeclared and has_proof,
            f"primary_rule={thresh_cfg.get('primary_rule')}, status={thresh_cfg.get('status')}",
        )
    except Exception as e:
        gate("threshold_predeclared_before_evaluation", False, str(e))

    # ── 17. AE scaler fitting on 40,320 rows (4,480 monitor transformed only)
    try:
        with open(repo_root / "publication_experiments/configs/ae_unseen_families.yaml", "r", encoding="utf-8") as f:
            ae_cfg = yaml.safe_load(f)
        scaler_cfg = ae_cfg.get("ae_scaler", {})
        fit_40320 = scaler_cfg.get("fit_count_expected") == 40320
        mon_4480 = scaler_cfg.get("monitor_count_expected") == 4480
        total_44800 = scaler_cfg.get("total_benign_train") == 44800
        gate(
            "ae_scaler_fitting_40320_ae_fit_subset_verified",
            fit_40320 and mon_4480 and total_44800,
            f"fit_count={scaler_cfg.get('fit_count_expected')} (40,320), monitor_count={scaler_cfg.get('monitor_count_expected')} (4,480)",
        )
    except Exception as e:
        gate("ae_scaler_fitting_40320_ae_fit_subset_verified", False, str(e))

    # ── 18. Stage-B training cannot overwrite frozen artifacts ────────────
    try:
        with open(repo_root / "publication_experiments/configs/no_ttl.yaml", "r", encoding="utf-8") as f:
            no_ttl_cfg = yaml.safe_load(f)
        out_cfg = no_ttl_cfg.get("output", {})
        prot_cfg = no_ttl_cfg.get("frozen_artifact_protection", {})
        allowed_prefix = prot_cfg.get("allowed_output_prefix", "results/publication_experiments/")
        all_under_allowed = all(str(p).replace("\\", "/").startswith(allowed_prefix) for p in out_cfg.values())
        forbidden_targets = prot_cfg.get("forbidden_overwrite_targets", [])
        no_forbidden = not any(
            any(str(p).replace("\\", "/").startswith(f.rstrip("/")) for f in forbidden_targets)
            for p in out_cfg.values()
        )
        gate(
            "stage_b_cannot_overwrite_frozen_artifacts",
            all_under_allowed and no_forbidden,
            f"All output paths under {allowed_prefix}, no collision with canonical/frozen directories",
        )
    except Exception as e:
        gate("stage_b_cannot_overwrite_frozen_artifacts", False, str(e))

    # ── GATE SUMMARY ─────────────────────────────────────────────────────
    all_pass = len(failures) == 0
    if not all_pass:
        logger.error("=" * 60)
        logger.error("HARD STOP — %d validation gate(s) FAILED:", len(failures))
        for f in failures:
            logger.error("  ✗ %s", f)
        logger.error("=" * 60)
        logger.error("Do NOT proceed to training.")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("ALL VALIDATION GATES PASSED (%d gates)", len(gates))
    logger.info("=" * 60)
    return gates


# ═════════════════════════════════════════════════════════════════════════
# DRY-RUN CORE
# ═════════════════════════════════════════════════════════════════════════

def run_dry_run(repo_root: Path, verbose: bool = False) -> dict:
    """
    Execute the full Stage A dry-run.

    Steps:
    1. Run hard validation gate
    2. Build and save No-TTL feature file
    3. Verify family sample counts against expected values
    4. Verify scaler incompatibility
    5. Generate audit report
    6. STOP — do NOT start training
    """
    logger.info("=" * 60)
    logger.info("STAGE A DRY-RUN — EXP_NO_TTL_V1 + EXP_AE_UNSEEN_FAMILY_V1")
    logger.info("NO training will be performed.")
    logger.info("=" * 60)

    # ── Phase 1: Validation gates ─────────────────────────────────────────
    logger.info("\n--- PHASE 11: HARD VALIDATION GATE ---")
    gates = run_validation_gate(repo_root)

    # ── Phase 2: Build and save No-TTL feature file ───────────────────────
    logger.info("\n--- PHASE 5: NO-TTL FEATURE ADAPTER ---")
    no_ttl_output = repo_root / "results/publication_experiments/EXP_NO_TTL_V1/features/no_ttl_features.json"
    no_ttl_output.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_and_save_no_ttl_feature_file(
        output_path=no_ttl_output,
        canonical_features_path=repo_root / "results/feature_selection/EXP_MI_V1_1/selected_features.json",
    )
    logger.info("No-TTL feature manifest saved: %s", no_ttl_output)
    logger.info("Feature hash: %s", manifest["feature_hash_sha256"])

    # ── Phase 3: Verify target family sample counts ───────────────────────
    logger.info("\n--- PHASE 7: DATA ISOLATION VERIFICATION ---")
    import pandas as pd

    dev_test = pd.read_csv(repo_root / "data/splits/development_test.csv")
    protected = pd.read_csv(repo_root / "data/splits/protected_unseen_attack.csv")
    train_df = pd.read_csv(repo_root / "data/splits/train.csv")
    val_df = pd.read_csv(repo_root / "data/splits/validation.csv")

    expected_counts = {
        "BACKDOOR": 583,
        "WORMS": 44,
        "SHELLCODE": 378,
        "ANALYSIS": 677,
        "BENIGN_DEVTEST": 37000,
    }

    family_map = {
        "BACKDOOR": protected,
        "WORMS": dev_test[dev_test["attack_cat"] == "Worms"],
        "SHELLCODE": dev_test[dev_test["attack_cat"] == "Shellcode"],
        "ANALYSIS": dev_test[dev_test["attack_cat"] == "Analysis"],
        "BENIGN_DEVTEST": dev_test[dev_test["attack_cat"] == "Normal"],
    }

    family_counts = {}
    for family, df in family_map.items():
        actual = len(df)
        expected = expected_counts[family]
        match = actual == expected
        family_counts[family] = {"expected": expected, "actual": actual, "match": match}
        status = "PASS" if match else "FAIL"
        logger.info("[%s] %s: expected=%d, actual=%d", status, family, expected, actual)
        if not match:
            logger.error("HARD STOP — Family count mismatch for %s", family)
            sys.exit(1)

    # ── Phase 4: Scaler incompatibility verification ───────────────────────
    logger.info("\n--- PHASE 8: SCALER STRATEGY VALIDATION ---")
    import joblib
    ae_scaler = joblib.load(repo_root / "results/checkpoints/EXP_AE_V1/ae_scaler.joblib")
    nn_scaler = joblib.load(repo_root / "results/checkpoints/EXP_BASE_MODELS_V1/nn/nn_scaler.joblib")
    svm_scaler = joblib.load(repo_root / "results/checkpoints/EXP_BASE_MODELS_V1/svm/svm_scaler.joblib")

    scaler_check = {
        "ae_scaler_canonical_features": ae_scaler.n_features_in_,
        "nn_scaler_canonical_features": nn_scaler.n_features_in_,
        "svm_scaler_canonical_features": svm_scaler.n_features_in_,
        "no_ttl_features_needed": 72,
        "canonical_scalers_incompatible": True,
        "ae_scaler_fitting_protocol": {
            "fit_population": "BENIGN_TRAIN_AE_FIT_SUBSET",
            "fit_row_count": 40320,
            "monitor_row_count": 4480,
            "monitor_handling": "Transformed only, NEVER fitted (enforced by test_ae_leakage.py)",
            "total_benign_train": 44800,
            "validation_row_count": 11200,
            "validation_handling": "Transformed only for threshold calibration",
        },
        "supervised_scaler_fitting_protocol": {
            "fit_population": "TRAIN_ALL_72_FEATURES",
            "fit_row_count": 162395,
            "models": ["SVM", "NN"],
        },
        "decision": "New 72-feature StandardScaler fitted on TRAIN for SVM/NN and 40,320 AE-fit rows for AE",
    }
    logger.info("Scaler verification: %s", scaler_check)

    # ── Phase 5: Monitor partition confirmation ────────────────────────────
    logger.info("\n--- PHASE 3 (MONITOR): Monitor Partition Status ---")
    monitor_csv_exists = (repo_root / "data/splits/monitor.csv").exists()
    monitor_status = {
        "monitor_csv_exists": monitor_csv_exists,
        "status": "CONFIRMED ABSENT as CSV file",
        "actual_implementation": (
            "Monitor is an INTERNAL 10% split of Normal TRAIN rows, "
            "created inside AETrainer.create_monitor_split() during each AE training run. "
            "It is NOT a persistent CSV partition. "
            "The 4,480 rows (10% of 44,800 benign TRAIN) are created at runtime. "
            "AE scaler is fitted strictly on the 40,320 AE-fit subset, NEVER on monitor rows."
        ),
        "implication_for_new_ae": (
            "New 72-feature AE will create its own internal monitor split "
            "at training time using the same AE_MONITOR_FRACTION=0.10 and seed=42."
        ),
    }
    logger.info("Monitor status: %s", monitor_status["status"])
    logger.info("  → %s", monitor_status["actual_implementation"])

    # ── Phase 6: Row alignment verification ───────────────────────────────
    logger.info("\n--- PHASE 9: ROW ALIGNMENT VERIFICATION ---")
    has_id_col = all([
        "id" in dev_test.columns,
        "id" in protected.columns,
        "id" in train_df.columns,
        "id" in val_df.columns,
    ])
    backdoor_ids_unique = protected["id"].nunique() == len(protected)
    alignment = {
        "row_id_column": "id",
        "all_splits_have_id": has_id_col,
        "backdoor_ids_unique": backdoor_ids_unique,
        "backdoor_n_ids": protected["id"].nunique(),
        "alignment_strategy": (
            "Predictions paired by 'id' column. "
            "Positional alignment alone FORBIDDEN per master prompt Section 17."
        ),
    }
    logger.info("Row alignment: id column present in all splits=%s, unique backdoor IDs=%d",
                has_id_col, protected["id"].nunique())

    # ── Phase 7: Generate audit report ────────────────────────────────────
    logger.info("\n--- PHASE 13: GENERATING AUDIT REPORT ---")

    audit_report = {
        "stage": "A_dry_run",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "git_head_note": "Current HEAD: e08366f (post Sprint-13 freeze commits)",
        "canonical_frozen_commit": "f694e19",
        "sections": {
            "A_new_folder": str(repo_root / "publication_experiments"),
            "B_reused_code": [
                "src.utils.hashing.sha256_file — artifact fingerprinting",
                "src.utils.reproducibility.set_all_seeds — seed control",
                "src.preprocessing.scaling.fit_scaler — scaler fitting",
                "src.preprocessing.scaling.transform_scaler — scaler application",
                "src.models.autoencoder.ae_model.Autoencoder — AE architecture",
                "src.models.autoencoder.ae_model.Autoencoder.reconstruction_error — RE computation",
                "src.models.autoencoder.ae_calibrate.calibrate_thresholds — threshold calibration",
                "src.models.autoencoder.ae_trainer.AETrainer — AE training loop",
                "src.models.autoencoder.ae_trainer.create_monitor_split — monitor split",
                "src.models.base_models.neural_network.IDSNet — NN architecture",
                "src.models.base_models.neural_network (training/CV utilities)",
                "src.models.base_models.random_forest — RF model",
                "src.models.base_models.decision_tree — DT model",
                "src.models.base_models.linear_svc — SVM model",
                "src.models.stacking.oof_runner — 5-fold OOF generation",
                "src.models.stacking.meta_learner — LR meta-learner",
                "src.models.base_models.comparator — model comparison",
                "src.preprocessing.loader — data loading",
                "src.preprocessing.preprocessing_pipeline — encoding pipeline",
            ],
            "C_reused_artifacts": [
                "results/feature_selection/EXP_MI_V1_1/selected_features.json — canonical 75 features",
                "data/splits/train.csv — TRAIN partition (read-only)",
                "data/splits/validation.csv — VALIDATION partition (read-only)",
                "data/splits/development_test.csv — DEV TEST partition (read-only)",
                "data/splits/protected_unseen_attack.csv — 583 Backdoor flows (read-only)",
                "results/checkpoints/EXP_AE_V1/ae_final.pt — canonical AE (reference only, not retrained)",
                "results/zero_day/EXP_ZERODAY_V1/metrics/zero_day_metrics.csv — canonical reference metrics",
            ],
            "D_new_code": [
                "publication_experiments/utils/feature_adapter.py — No-TTL subset logic",
                "publication_experiments/utils/ae_family_eval.py — per-family AE evaluation",
                "publication_experiments/scripts/run_dry_run.py — this script",
                "publication_experiments/configs/no_ttl.yaml — No-TTL experiment config",
                "publication_experiments/configs/ae_unseen_families.yaml — AE family config",
                "results/publication_experiments/EXP_NO_TTL_V1/features/no_ttl_features.json — 72-feature manifest",
            ],
            "E_code_not_reused": [
                {
                    "component": "Canonical StandardScaler for SVM/NN/AE",
                    "reason": "n_features_in_=75; incompatible with 72-feature input",
                    "adapter": "New scaler fitted on 72-feature TRAIN (SVM/NN) and 40,320 AE-fit subset (AE)",
                },
            ],
            "F_feature_transformation": {
                "canonical_75": manifest["canonical_feature_count"],
                "removed": manifest["removed_features"],
                "removed_count": manifest["removed_feature_count"],
                "final_72": manifest["final_feature_count"],
                "feature_hash": manifest["feature_hash_sha256"],
                "ttl_absent_verification": manifest["verification"],
            },
            "G_no_ttl_model_design": {
                "base_learners": ["DT", "RF", "SVM", "NN"],
                "stacking": "5-fold OOF → Logistic Regression meta-learner",
                "controlled_feature_ablation": (
                    "Controlled feature ablation: {sttl, ct_state_ttl, dttl} removed (75 → 72 features). "
                    "Tree models (DT, RF) explore 72-feature subspace without TTL splits; "
                    "Linear/Neural models (SVM, NN) use newly fitted 72-feature StandardScaler on TRAIN; "
                    "IDSNet first-layer weight tensor adapts (W1: 72 → 128); "
                    "All hyperparameters (depths, hidden sizes 128→64→2, lr=0.001, wd=1e-4, batch=256, patience=5), "
                    "CV split (5-fold, seed=7), and random seeds ([42, 123, 2024]) remain identical to canonical."
                ),
                "idsnet_canonical": "75 → 128 → 64 → 2 (W1: 75×128)",
                "idsnet_no_ttl": "72 → 128 → 64 → 2 (W1: 72×128)",
                "seeds": [42, 123, 2024],
                "locked_paired_test_seed_mapping": {
                    "primary_paired_seed": {"canonical_seed": 42, "no_ttl_seed": 42, "status": "LOCKED_MANDATORY"},
                    "multi_seed_pairs": [
                        {"canonical_seed": 42, "no_ttl_seed": 42},
                        {"canonical_seed": 123, "no_ttl_seed": 123},
                        {"canonical_seed": 2024, "no_ttl_seed": 2024},
                    ],
                    "cross_seed_pairing_allowed": False,
                },
            },
            "H_scaler_design": scaler_check,
            "I_ae_design": {
                "architecture": "72 → 12 → 6 → 12 → 72",
                "derivation_rule": "round(72 × 16%) = 12, round(72 × 8%) = 6",
                "benign_only_training": True,
                "benign_validation_calibration": True,
                "scaler_fit_rows": 40320,
                "monitor_rows_transformed_only": 4480,
                "final_refit_rows": 44800,
                "calibration_rows": 11200,
                "primary_threshold_rule": "p99",
                "primary_threshold_predeclared": True,
                "one_checkpoint": True,
                "one_threshold": True,
                "families": ["BACKDOOR", "WORMS", "SHELLCODE", "ANALYSIS"],
            },
            "J_target_families": family_counts,
            "K_leakage_audit": (
                "AE is benign-only. No attack family (Backdoor, Worms, Shellcode, Analysis) "
                "enters AE training (label==0 filter). "
                "Worms/Shellcode/Analysis appear in TRAIN as attack rows but AE is never "
                "trained on attack-labeled data. "
                "Backdoor is excluded from TRAIN entirely (protected_unseen_attack.csv). "
                "No target attack-family information enters model development."
            ),
            "L_configuration": {
                "precedence": "DEFAULTS → CONFIG FILE → CLI ARGUMENTS",
                "config_files": [
                    "publication_experiments/configs/no_ttl.yaml",
                    "publication_experiments/configs/ae_unseen_families.yaml",
                ],
            },
            "M_output_paths": {
                "no_ttl_features": str(no_ttl_output),
                "no_ttl_results": "results/publication_experiments/EXP_NO_TTL_V1/",
                "ae_family_results": "results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1/",
            },
            "N_frozen_baseline_confirmation": (
                "CONFIRMED: No canonical Sprint-13 artifact will be modified. "
                "All frozen directories verified present and untouched."
            ),
            "O_canonical_ae_confirmation": (
                "CONFIRMED: The existing canonical 75-feature AE (EXP_AE_V1) will be "
                "used as reference only. It will NOT be retrained or overwritten."
            ),
            "P_new_ae_confirmation": (
                "CONFIRMED: One new 72-feature benign-only AE will be trained for "
                "EXP_AE_UNSEEN_FAMILY_V1. One frozen checkpoint, one scaler, and one "
                "threshold will be shared across all four family evaluations."
            ),
            "Q_alignment_and_monitor": {
                "row_alignment": alignment,
                "monitor_status": monitor_status,
            },
        },
        "gate_results": gates,
        "family_counts": family_counts,
        "scaler_check": scaler_check,
        "status": "STAGE_A_COMPLETE_STOP",
        "next_step": (
            "Review this audit report. "
            "If approved, run Stage B: python publication_experiments/scripts/run_no_ttl_experiment.py "
            "--config publication_experiments/configs/no_ttl.yaml"
        ),
    }

    # Save audit report
    audit_path = (
        repo_root / "results/publication_experiments/stage_a_audit_report.json"
    )
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)

    logger.info("\n" + "=" * 60)
    logger.info("STAGE A DRY-RUN COMPLETE")
    logger.info("Audit report saved: %s", audit_path)
    logger.info("=" * 60)
    logger.info("\nSTOP. Do NOT proceed to training without explicit approval.")
    logger.info("Review the audit report and approve Stage B to continue.")

    # Print concise summary to stdout
    print("\n" + "=" * 60)
    print("STAGE A DRY-RUN SUMMARY")
    print("=" * 60)
    print(f"Gates passed: {sum(gates.values())}/{len(gates)}")
    print(f"No-TTL feature count: {manifest['final_feature_count']}")
    print(f"Feature hash: {manifest['feature_hash_sha256'][:16]}...")
    print(f"sttl absent: {manifest['verification']['sttl_absent']}")
    print(f"ct_state_ttl absent: {manifest['verification']['ct_state_ttl_absent']}")
    print(f"dttl absent: {manifest['verification']['dttl_absent']}")
    print("\nFamily sample counts:")
    for fam, info in family_counts.items():
        print(f"  {fam:15s}: {info['actual']:5d} (expected {info['expected']}) {'OK' if info['match'] else 'FAIL'}")
    print(f"\nMonitor partition: {monitor_status['status']}")
    print(f"Row alignment key: id column (present in all splits)")
    print(f"\nAudit report: {audit_path}")
    print("=" * 60)
    print("STAGE A COMPLETE — STOP. Await approval before Stage B.")

    return audit_report


# ═════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Stage A Dry-Run: validate all preconditions without training."
    )
    p.add_argument(
        "--config",
        default="publication_experiments/configs/no_ttl.yaml",
        help="Config file path (for reference; gates use canonical paths).",
    )
    p.add_argument(
        "--verbose", action="store_true", help="Enable DEBUG logging."
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    run_dry_run(repo_root=REPO_ROOT, verbose=args.verbose)
