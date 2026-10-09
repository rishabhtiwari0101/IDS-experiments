# DOC-07: Calibration Source and Leakage Audit Report

**Date:** 2026-09-28  
**Experiment ID:** EXP_DISCOVERY_V1  
**Blueprint:** `IDS_UNSW_NB15_Implementation_Blueprint_FINAL_v5 (2).md` (§0 Rule 1, Rule 13, Rule 15; §16 S0; §17 Phase 0)  
**Artifact:** `results/publication_experiments/EXP_DISCOVERY_V1/phase0_discovery.json`

---

## 1. Executive Summary & Calibration Source Classification

- **Resolved Calibration Status:** `source_status: untouched_val`
- **Calibration Split Path:** `data/splits/validation.csv` (11,200 rows, all Normal `label == 0`, SHA-256: `13caf21a076a33f50243f48f404b7e7525969f71d4b9d7c0f3768aef23589180`)
- **Tier A Eligibility:** **ELIGIBLE** (Clean untouched VAL; Rule 1/13 satisfied).
- **Tier B Eligibility:** **ELIGIBLE** (Clean DEV_TEST; no benign DEV_TEST rows used in development or selection of any scored model).

Both calibration tiers are fully eligible for headline consideration. Per Rule 15 and the pre-committed `headline_tier_rule`, the final headline tier will be determined by the partition-shift diagnostic in S3.

---

## 2. VAL-Usage Audit (Tier A Headline Eligibility)

An exhaustive static audit of all training scripts, trainers, and metadata was executed by `phase0_discovery.py` (S0):

1. **Supervised Base Models (DT, RF, SVM, NN):**
   - Trained exclusively on `data/splits/train.csv` (162,395 rows, SHA-256: `4a259324e604f013287a5de5fe49c46bf19418d815b550c5d1a5820b569ac41c`).
   - `validation.csv` was not loaded or used for hyperparameter search, early stopping, or model selection.
2. **OOF Stacking Ensemble (Meta-Learners Seeds 42, 123, 2024):**
   - 5-fold cross-validation operated strictly on `train.csv` rows.
   - Access policy recorded in `EXP_OOF_STACK_V1` metadata: `validation.csv` marked `FORBIDDEN`.
   - Meta-learners were fit on TRAIN OOF predictions only.
3. **Autoencoder (AE):**
   - `ae_metadata.json` confirms training used a 40,320 / 4,480 partition of `train.csv` (Normal rows) for early stopping.
   - `validation.csv` was NOT used for weight updates or early stopping; it was used solely for post-training threshold calibration (`EXP_AE_V1/threshold_config.json`).
4. **Feature Selection (`EXP_MI_V1_1`):**
   - `metadata.json` confirms `input_train_file: data/splits/train.csv` (162,395 rows). `validation.csv` was never accessed.
5. **Preprocessing Pipeline (`PreprocessingPipeline`):**
   - Fitted on `train.csv` only.

**Conclusion:** `validation.csv` is completely untouched by model development, satisfying Rule 1 and Rule 13 requirements for clean headline calibration.

---

## 3. DEV_TEST-Usage Audit (Tier B Headline Eligibility)

The audit verified whether any benign DEV_TEST rows influenced the development or selection of any scored model:
- `development_test.csv` was declared `FORBIDDEN` across all upstream sprint training pipelines.
- Supervised models were trained on TRAIN only.
- OOF cross-validation and meta-learner fitting were performed on TRAIN only.
- Feature selection was performed on TRAIN only.
- All fitted scalers were fitted on TRAIN (or Normal TRAIN subsets) only.

**Conclusion:** DEV_TEST is clean of model development influence. Tier B is eligible for headline consideration.

---

## 4. Feature Selection & Scaler Leakage Audit (Non-Blocking Evidence)

| Pipeline Component | Training Input | Rows | Status |
|-------------------|----------------|------|--------|
| MI Feature Selection (`EXP_MI_V1_1`) | `data/splits/train.csv` | 162,395 | **PASS** (TRAIN only) |
| Base Model Preprocessing & Scalers | `data/splits/train.csv` | 162,395 | **PASS** (TRAIN only) |
| AE Feature Scaler (`ae_scaler.joblib`) | Normal TRAIN AE-fit subset | 40,320 | **PASS** (TRAIN Normal subset only) |

---

## 5. AE Checkpoint Fit Provenance (S0-A8)

- **Phase 1 (Early Stopping):** Fit on Normal AE-fit subset (40,320 rows) monitored on Normal monitor subset (4,480 rows) with seed 42, triggering early stopping at `best_epoch = 133`.
- **Phase 2 (Final Refit):** `trainer.final_refit(X_normal_train_scaled, best_epoch)` trained on **ALL 44,800 Normal TRAIN rows** for exactly 133 epochs without early stopping, using the scaler fit on the 40,320 subset.
- **Frozen Weights:** `results/checkpoints/EXP_AE_V1/ae_final.pt` contains the weights from the Phase-2 44,800-row refit, confirming blueprint §16 line 648.

---

## 6. Historical Reproducibility & Exceedance Rates (DQ-06)

At frozen threshold $\tau = 11.160062745213509$ (`mean + 3*sigma`):
- **VAL Calibration Exceedances:** 7 / 11,200 = 0.000625 (0.0625%)
- **DEV_TEST Benign Control Exceedances:** 19 / 37,000 = 0.000514 (0.0514%)
- **Exceedance Count Reproduction:** Both counts reproduced exactly by S0 (`7` and `19`, exact integer match $\pm 0$).
- **Conclusion:** No discrepancy: 19/37000 = 0.051% vs 7/11200 = 0.0625%; counts too small to infer partition shift.

---

## 7. Population Disjointness & Overlap Matrix

Every population was indexed by stable source-prefixed row IDs (`UNSW_NB15_training-set.csv:<id>` or `UNSW_NB15_testing-set.csv:<id>`):
- `train`: 162,395 unique row IDs
- `calibration_benign` (VAL): 11,200 unique row IDs
- `dev_test`: 81,749 unique row IDs
- `protected_backdoor`: 583 unique row IDs
- `benign_control`: 37,000 unique row IDs (exact subset of `dev_test`)
- `unseen_families` (Worms, Shellcode, Analysis): 1,099 unique row IDs (exact subset of `dev_test`)

**Forbidden Overlap Results:**
- `train` vs `calibration_benign`: 0 overlap
- `train` vs `dev_test`: 0 overlap
- `train` vs `backdoor`: 0 overlap
- `calibration_benign` vs `dev_test`: 0 overlap
- `calibration_benign` vs `backdoor`: 0 overlap
- `dev_test` vs `backdoor`: 0 overlap
- `backdoor` vs `unseen_families`: 0 overlap

**Tier B Control Split Results:**
- `cal_control`: 18,500 rows (SHA-256: `e95728c95299c21ad026b27434cc483d9b8fe7ddfb7563f0e0137decd76c7395`)
- `eval_control`: 18,500 rows (SHA-256: `25628d10faad090908ea4a149e1e5c3fa074c3df711b3a36bf0c865a0a0a0210`)
- Disjoint: **True**
- Union equals benign control: **True**
