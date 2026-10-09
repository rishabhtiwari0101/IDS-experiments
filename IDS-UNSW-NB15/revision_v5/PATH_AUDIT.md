# PATH AUDIT — revision_v5

**Blueprint:** `IDS_UNSW_NB15_Implementation_Blueprint_FINAL_v5 (2).md` v5.0  
**Created:** 2026-09-28T05:27 UTC  
**Purpose:** For EVERY existing path the blueprint references, mark as EXISTS / MISSING / DIFFERENT_LOCATION. Read-only checks only. No files modified.

---

## Legend

| Status | Meaning |
|--------|---------|
| ✅ EXISTS | File found at the exact blueprint path |
| ❌ MISSING | File not found at any location |
| ⚠️ DIFFERENT_LOCATION | File found but at a different path than blueprint states |
| 🔍 NEEDS_VERIFY | Exists but content/structure needs further verification at S0 runtime |

---

## 1. Data Splits

| Blueprint Path | Status | Notes |
|----------------|--------|-------|
| `data/splits/development_test.csv` | ✅ EXISTS | 81,749 rows; benign=37,000; attack=44,749; SHA=`04725e85...` ✓ blueprint match |
| `data/splits/train.csv` | ✅ EXISTS | 162,395 rows; benign=44,800; attack=117,595; SHA=`4a259324...` |
| `data/splits/validation.csv` | ✅ EXISTS | 11,200 rows; ALL benign (label==0); SHA recorded in baseline |
| `data/splits/protected_unseen_attack.csv` | ✅ EXISTS | 583 rows (Backdoor); SHA=`6ffd2347...` ✓ blueprint match |
| `data/splits/train_val_split_metadata.json` | ✅ EXISTS | Metadata for TRAIN/VAL split |
| `data/splits/split_metadata.json` | ✅ EXISTS | SHA=`d48907e0...` |

**Partition-provenance arithmetic (blueprint S0 item 10):**
- TRAIN benign (44,800) + VAL benign (11,200) = **56,000** ✓
- DEV_TEST benign = **37,000** ✓ (= benign-control size)
- Arithmetic consistent with official UNSW-NB15 training/testing partition split

---

## 2. Model Checkpoints

| Blueprint Path | Status | Notes |
|----------------|--------|-------|
| `results/checkpoints/EXP_BASE_MODELS_V1/dt/dt_final.joblib` | ✅ EXISTS | Hash-verified in EXP_H123_V1 provenance |
| `results/checkpoints/EXP_BASE_MODELS_V1/rf/rf_final.joblib` | ✅ EXISTS | Hash-verified |
| `results/checkpoints/EXP_BASE_MODELS_V1/svm/svm_final.joblib` | ✅ EXISTS | Hash-verified |
| `results/checkpoints/EXP_BASE_MODELS_V1/svm/svm_scaler.joblib` | ✅ EXISTS | Hash-verified |
| `results/checkpoints/EXP_BASE_MODELS_V1/nn/nn_final.pt` | ✅ EXISTS | Hash-verified |
| `results/checkpoints/EXP_BASE_MODELS_V1/nn/nn_scaler.joblib` | ✅ EXISTS | Hash-verified |
| `results/checkpoints/EXP_BASE_MODELS_V1/nn/nn_architecture.json` | ✅ EXISTS | `input_dim=75, hidden_sizes=[128,64]` |
| `results/checkpoints/EXP_BASE_MODELS_V1/nn/nn_metadata.json` | ✅ EXISTS | `output_contract: "predict + sigmoid probability in [0,1]"` — confirms single sigmoid output |
| `results/checkpoints/EXP_BASE_MODELS_V1/dt/dt_metadata.json` | ✅ EXISTS | |
| `results/checkpoints/EXP_BASE_MODELS_V1/rf/rf_metadata.json` | ✅ EXISTS | |
| `results/checkpoints/EXP_BASE_MODELS_V1/svm/svm_metadata.json` | ✅ EXISTS | |
| `results/checkpoints/EXP_OOF_STACK_V1/seed_42/meta_learner.joblib` | ✅ EXISTS | Hash-verified |
| `results/checkpoints/EXP_OOF_STACK_V1/seed_123/meta_learner.joblib` | ✅ EXISTS | Hash-verified |
| `results/checkpoints/EXP_OOF_STACK_V1/seed_2024/meta_learner.joblib` | ✅ EXISTS | Hash-verified |
| `results/checkpoints/EXP_OOF_STACK_V1/seed_42/metadata.json` | ✅ EXISTS | |
| `results/checkpoints/EXP_OOF_STACK_V1/seed_123/metadata.json` | ✅ EXISTS | |
| `results/checkpoints/EXP_OOF_STACK_V1/seed_2024/metadata.json` | ✅ EXISTS | |
| `results/checkpoints/EXP_AE_V1/ae_final.pt` | ✅ EXISTS | Hash in EXP_H123_V1 provenance; canonical 75-feature checkpoint |
| `results/checkpoints/EXP_AE_V1/ae_scaler.joblib` | ✅ EXISTS | Hash in EXP_H123_V1 provenance |
| `results/checkpoints/EXP_AE_V1/ae_architecture.json` | ✅ EXISTS | Architecture: `75→12→6→12→75` |
| `results/checkpoints/EXP_AE_V1/ae_metadata.json` | ✅ EXISTS | `training_rows=40320, monitor_rows=4480, normal_train_total=44800` |
| `results/checkpoints/EXP_AE_V1/threshold_config.json` | ✅ EXISTS | `calibration_rows=11200`, `mean=0.2252`, `std=3.6449`, `τ=11.160063` |

---

## 3. Feature Selection

| Blueprint Path | Status | Notes |
|----------------|--------|-------|
| `results/feature_selection/EXP_MI_V1_1/selected_features.json` | ✅ EXISTS | `feature_count: 75` ✓; `feature_ordering` field present |
| `results/feature_selection/EXP_MI_V1_1/config.yaml` | ✅ EXISTS | |
| `results/feature_selection/EXP_MI_V1_1/feature_ranking.csv` | ✅ EXISTS | |
| `results/feature_selection/EXP_MI_V1_1/metadata.json` | ✅ EXISTS | |

---

## 4. Existing Evaluation Artifacts

| Blueprint Path | Status | Notes |
|----------------|--------|-------|
| `results/evaluation/EXP_H123_V1/h1_results.json` | ✅ EXISTS | Stacking Macro-F1 per seed (reference: mean=0.8930) |
| `results/evaluation/EXP_H123_V1/h2_results.json` | ✅ EXISTS | |
| `results/evaluation/EXP_H123_V1/h3_results.json` | ✅ EXISTS | |
| `results/evaluation/EXP_H123_V1/provenance/*.json` | ✅ EXISTS | All 10 provenance files including checkpoint hashes |
| `results/evaluation/EXP_H123_V1/metadata.json` | ✅ EXISTS | |

---

## 5. Zero-Day Artifacts (EXP_ZERODAY_V1)

| Blueprint Path | Status | Notes |
|----------------|--------|-------|
| `results/zero_day/EXP_ZERODAY_V1/metrics/zero_day_metrics.csv` | ✅ EXISTS | 8 rows; Stacking FPR=0.1919; Stacking detections=582; AE FPR=0.000514, AE TP=0 |
| `results/zero_day/EXP_ZERODAY_V1/metrics/preregistered_decisions.json` | ✅ EXISTS | Exists; Git evidence for timestamp to be checked in S0 |
| `results/zero_day/EXP_ZERODAY_V1/predictions/benign_control_predictions.csv` | ✅ EXISTS | 37,000 rows; columns: `source_row_uid, label, dt_prediction, rf_prediction, svm_prediction, nn_prediction` — **BINARY DECISIONS ONLY** (no probabilities) |
| `results/zero_day/EXP_ZERODAY_V1/predictions/combined_evaluation_predictions.csv` | ✅ EXISTS | 37,583 rows; binary decisions only (stacking_prediction column present) |
| `results/zero_day/EXP_ZERODAY_V1/predictions/zero_day_backdoor_predictions.csv` | ✅ EXISTS | 583 rows; includes `rf_prediction, rf_score, reconstruction_error, ae_flag` |
| `results/zero_day/EXP_ZERODAY_V1/preflight/hash_verification.json` | ✅ EXISTS | |
| `results/zero_day/EXP_ZERODAY_V1/preflight/population_manifest.json` | ✅ EXISTS | 🔍 Check for row_uid list |
| `results/zero_day/EXP_ZERODAY_V1/config.yaml` | ✅ EXISTS | |
| `results/zero_day/EXP_ZERODAY_V1/metadata.json` | ✅ EXISTS | |

**Per-row EXP_ZERODAY_V1 artifacts:** ✅ **EXIST** — `benign_control_predictions.csv` (37,000 rows) provides `source_row_uid` for benign-control identity. Binary decisions only; **no probability scores**. S1 must regenerate probabilities.

---

## 6. Publication Experiment Artifacts

| Blueprint Path | Status | Notes |
|----------------|--------|-------|
| `results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1/threshold/seed_42/threshold_sweep.csv` | ✅ EXISTS | CROSS-CHECK ONLY — 72-feature AE, not EXP_AE_V1 |
| `results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1/evaluations/seed_42/WORMS/predictions.csv` | ✅ EXISTS | Worms=44 rows ✓ (72-feat AE; cross-check only) |
| `results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1/evaluations/seed_42/SHELLCODE/predictions.csv` | ✅ EXISTS | Shellcode=378 rows ✓ |
| `results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1/evaluations/seed_42/ANALYSIS/predictions.csv` | ✅ EXISTS | Analysis=677 rows ✓ |
| `results/publication_experiments/EXP_STATS_ROBUSTNESS_V1/threshold_tradeoff/secondary_threshold_fpr_matrix.csv` | ✅ EXISTS | AE-only FPR matrix |
| `results/publication_experiments/EXP_STATS_ROBUSTNESS_V1/paired_tests/mcnemar_results.csv` | ✅ EXISTS | S4 fallback input |
| `results/publication_experiments/EXP_INTEGRATED_PUBLICATION_V1/integrated_statistics/ae_primary_summary.csv` | ✅ EXISTS | Worms CI [0%, 8.04%] for Req 2.4 |
| `results/autoencoder/EXP_AE_V1/threshold/validation_reconstruction_errors.csv` | ✅ EXISTS | CROSS-CHECK ONLY — legacy VAL RE file; S1 regenerates from ae_final.pt |
| `publication_experiments/stage_d/materiality_preregistration.json` | ✅ EXISTS | Timestamp 2026-09-08T16:47:34 UTC; post-hoc |
| `publication_experiments/stage_e/configs/stage_e.yaml` | ✅ EXISTS | |

---

## 7. Key Source Scripts

| Blueprint Path | Status | Notes |
|----------------|--------|-------|
| `scripts/verify_sprint12_freeze.py` | ✅ EXISTS | Gate 1 validation script |
| `scripts/validate_ae.py` | ✅ EXISTS | Gate 1: 21 AE checks |
| `scripts/validate_oof_stacking.py` | ✅ EXISTS | Gate 1: 24 OOF checks |
| `scripts/scan_ml_patterns.py` | ✅ EXISTS | Source for zero-training guard logic |
| `src/models/autoencoder/ae_trainer.py` | ✅ EXISTS | AE training code; docstring confirms 44,800 final refit |
| `src/models/base_models/neural_network.py` | ✅ EXISTS | NN source: `layers.append(nn.Linear(prev, 1))` — single output node ✓ |
| `src/models/stacking/meta_learner.py` | ✅ EXISTS | S1 must verify meta-feature column order here |
| `src/utils/zero_training_guard.py` | ❌ MISSING | Module does NOT exist in src/utils/; fallback = replicate scan_ml_patterns (see DECISIONS.md DQ-01) |

---

## 8. Per-Row RF Predictions (TOST input)

| Artifact | Status | Notes |
|----------|--------|-------|
| **Canonical RF per-row Backdoor:** `results/zero_day/EXP_ZERODAY_V1/predictions/zero_day_backdoor_predictions.csv` | ✅ EXISTS | 583 rows; `rf_prediction` (binary), `rf_score` columns |
| **No-TTL RF per-row Backdoor:** `results/publication_experiments/EXP_NO_TTL_V1/predictions/seed_42/predictions_protected_backdoor.csv` | ✅ EXISTS | 583 rows; `rf_pred` (binary), `rf_prob` columns |
| **Paired contingency (mcnemar_results.csv):** `results/publication_experiments/EXP_STATS_ROBUSTNESS_V1/paired_tests/mcnemar_results.csv` | ✅ EXISTS | Aggregate fallback for S4 |

**Per-row RF paired predictions:** ✅ AVAILABLE for Backdoor population. S4 can join on row identity. Columns differ (`source_row_uid` vs `id`); S4 must align. Row count = 583 in both files.

---

## 9. Unseen-Family Rows (Worms=44, Shellcode=378, Analysis=677)

| Source | Status | Notes |
|--------|--------|-------|
| `data/splits/development_test.csv` filtered by `attack_cat in ('Worms','Shellcode','Analysis')` | ✅ CONFIRMED | Counts: Worms=44 ✓, Shellcode=378 ✓, Analysis=677 ✓ |
| `results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1/evaluations/seed_*/WORMS/predictions.csv` | ✅ EXISTS | 44 rows; 72-feature AE — cross-check only |

**Unseen-family source determination:** Rows come from `development_test.csv`. Supervised models have seen these as attack training rows during OOF cross-validation (TRAIN includes attack rows). Therefore, **these are NOT zero-day for supervised models** — only for AE and IF (which train on benign only). Blueprint §6 BATCH-A confirms: "Per-family recall for AE and IF only."

**`populations.yaml` unseen_families.source** will be: `{path: data/splits/development_test.csv, filter: {attack_cat: [Worms, Shellcode, Analysis]}}`

---

## 10. Missing New Experiments (Expected MISSING — to be created in NEW_ROOT)

| Path (relative to revision_v5/) | Status | Blueprint producer |
|----------------------------------|--------|--------------------|
| `publication_experiments/configs/populations.yaml` | ❌ NOT YET CREATED | Manual (Phase 0) |
| `publication_experiments/configs/matched_fpr.yaml` | ❌ NOT YET CREATED | Manual (Phase 0) |
| `publication_experiments/configs/prob_inference.yaml` | ❌ NOT YET CREATED | Manual (Phase 0) |
| `publication_experiments/configs/tost.yaml` | ❌ NOT YET CREATED | Manual (Phase 0) |
| `publication_experiments/configs/mad.yaml` | ❌ NOT YET CREATED | Manual (Phase 0) |
| `publication_experiments/stage_f/configs/stage_f.yaml` | ❌ NOT YET CREATED | Manual (Phase 0) |
| `publication_experiments/scripts/phase0_discovery.py` | ❌ NOT YET CREATED | S0 |
| `publication_experiments/scripts/run_prob_inference.py` | ❌ NOT YET CREATED | S1 |
| `publication_experiments/scripts/run_roc_pr_analysis.py` | ❌ NOT YET CREATED | S2 |
| `publication_experiments/scripts/run_matched_fpr_analysis.py` | ❌ NOT YET CREATED | S3 |
| `publication_experiments/scripts/run_tost_analysis.py` | ❌ NOT YET CREATED | S4 |
| `publication_experiments/scripts/run_mad_threshold.py` | ❌ NOT YET CREATED | S5 |
| `publication_experiments/scripts/run_ae_threshold_ablation.py` | ❌ NOT YET CREATED | S6 |
| `publication_experiments/stage_f/scripts/run_isolation_forest.py` | ❌ NOT YET CREATED | S7 |
| `publication_experiments/scripts/run_alert_budget_analysis.py` | ❌ NOT YET CREATED | S8 |
| `publication_experiments/scripts/run_cross_consistency_check.py` | ❌ NOT YET CREATED | S9 |
| All result directories under `results/publication_experiments/EXP_PROB_INFERENCE_V1/` etc. | ❌ NOT YET CREATED | Experiment runs |

All of the above are EXPECTED to be missing at this stage — they will be created under `revision_v5/` during Phase 0 (configs) and later phases (scripts and results).

---

## 11. Summary Table (Key Audit Items)

| Item | Status |
|------|--------|
| All data splits present | ✅ |
| All model checkpoints present | ✅ |
| Feature count = 75 | ✅ |
| DEV_TEST SHA matches blueprint | ✅ |
| Backdoor SHA matches blueprint | ✅ |
| Validation split = 11,200 benign rows | ✅ |
| TRAIN benign = 44,800 | ✅ |
| TRAIN+VAL benign = 56,000 | ✅ |
| DEV_TEST benign = 37,000 | ✅ |
| `zero_day_metrics.csv` exists | ✅ |
| Per-row benign-control predictions exist (source_row_uid) | ✅ |
| Per-row RF predictions for TOST (canonical + no-TTL) | ✅ |
| Unseen families Worms=44, Shellcode=378, Analysis=677 in DEV_TEST | ✅ |
| `ae_primary_summary.csv` (Worms CI 8.04%) | ✅ |
| `validation_reconstruction_errors.csv` (legacy, cross-check only) | ✅ |
| `mcnemar_results.csv` | ✅ |
| `h1_results.json` (stacking Macro-F1) | ✅ |
| `preregistered_decisions.json` | ✅ |
| `materiality_preregistration.json` | ✅ |
| `src/utils/zero_training_guard.py` | ❌ MISSING (replicate from scan_ml_patterns.py) |
| New experiment directories under `revision_v5/` | ❌ (expected — to be created) |

---

*This audit is read-only. No files were modified in its preparation.*
