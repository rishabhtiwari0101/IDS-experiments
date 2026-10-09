# Sprint 5 Quality Review — EXP_BASE_MODELS_V1

**Date:** 2026-09-01
**Updated:** 2026-09-01 (pre-freeze documentation fixes applied)
**Status:** READY_TO_FREEZE

---

## Executive Summary

All 20 quality review steps completed. All three previously-noted issues have been
resolved. No retraining was performed. No model configurations were changed.

The experiment is **READY_TO_FREEZE**.

---

## Pre-Freeze Documentation Fixes Applied

| Issue | Description | Resolution |
|-------|-------------|-----------|
| 1 | `feature_set`/`feature_count` absent from checkpoint metadata | Added to all 4 `*_metadata.json` files |
| 2 | `EXP_BASE_MODELS_V1` absent from experiment registry | Entry added with `status=IMPLEMENTED` |
| 3 | `metadata.json` absent from results directory | Created from existing artifacts |

**No retraining. No config changes. No model weights modified.**

---

## 1. Baseline Results

| Model | Baseline Mean Macro-F1 | Std       | Spec Match |
|-------|------------------------|-----------|------------|
| DT    | 0.9374720              | 0.0018130 | YES (0.937472) |
| RF    | 0.9498716              | 0.0025702 | YES (0.949872) |
| SVM   | 0.9202731              | 0.0019113 | YES (0.920273) |
| NN    | 0.9242676              | 0.0049165 | YES (0.924268) |

---

## 2. Tuning Results — Baseline vs Selected

| Model | Baseline   | Selected   | Abs Imp    | Rel Imp  | Selected = Tuning Best |
|-------|-----------|-----------|-----------|---------|------------------------|
| DT    | 0.9374720 | 0.9388952 | +0.0014233 | +0.1518% | YES |
| RF    | 0.9498716 | 0.9508532 | +0.0009816 | +0.1033% | YES |
| SVM   | 0.9202731 | 0.9202929 | +0.0000199 | +0.0022% | YES |
| NN    | 0.9242676 | 0.9242676 | +0.0000000 | +0.0000% | YES (baseline = tuning grid member) |

Values confirmed directly from CSV; none manually entered.

---

## 3. Grid Size Verification

| Model | Declared | Actual Rows | Unique Configs | Match |
|-------|----------|-------------|----------------|-------|
| DT    | 24       | 24          | 24             | YES |
| RF    | 24       | 24          | 24             | YES |
| SVM   | 4        | 4           | 4              | YES |
| NN    | 8        | 8           | 8              | YES |

---

## 4. Fold Coverage

| Model | Baseline Folds | Duplicates | Status |
|-------|---------------|------------|--------|
| DT    | [0,1,2,3,4]   | 0          | OK |
| RF    | [0,1,2,3,4]   | 0          | OK |
| SVM   | [0,1,2,3,4]   | 0          | OK |
| NN    | [0,1,2,3,4]   | 0          | OK |

**Fold-level F1 values (baseline phase):**

| Model | Fold 0  | Fold 1  | Fold 2  | Fold 3  | Fold 4  | Range   |
|-------|---------|---------|---------|---------|---------|---------|
| DT    | 0.93735 | 0.93493 | 0.93831 | 0.93985 | 0.93692 | 0.00492 |
| RF    | 0.94871 | 0.94880 | 0.94935 | 0.95440 | 0.94811 | 0.00629 |
| SVM   | 0.91911 | 0.92032 | 0.91856 | 0.92347 | 0.91991 | 0.00491 |
| NN    | 0.92206 | 0.92539 | 0.92300 | 0.93201 | 0.91888 | 0.01313 |

No suspicious identical folds. All ranges are natural variation.
Stored `std_macro_f1` uses ddof=1 (pandas/numpy default). Confirmed.

---

## 5. Primary Metric Verification

Macro-F1 is the ONLY model-selection metric. Confirmed in `comparator.py`: only
`mean_macro_f1` and `std_macro_f1` are accessed in the selection logic.
Descriptive columns (`weighted_f1`, `balanced_accuracy`, `precision_macro`,
`recall_macro`, `fpr`, `specificity`) are never used for selection.

---

## 6. Comparator Verification

Source: [`comparator.py`](../../../src/models/base_models/comparator.py)

Tolerance: `_F1_TOLERANCE = 1e-6` ✓

| Step | Criterion | Direction | Implementation |
|------|-----------|-----------|----------------|
| 1 | mean Macro-F1 | Higher wins | `f1_a > f1_b + 1e-6` |
| 2 | std Macro-F1 | Lower wins | `std_a < std_b - 1e-6` |
| 3 | Model simplicity | Per-model | `_simplicity_compare()` |
| 4 | Serialised config | Lexicographic | `json.dumps(sort_keys=True)` |

**DT:** max_depth {5<10<20<None} → min_samples_leaf → gini<entropy  
**RF:** n_estimators → max_depth {10<20<None} → min_samples_leaf → sqrt<0.3  
**SVM:** C ascending (0.01<0.1<1.0<10.0)  
**NN:** param_count ↑ → weight_decay (larger preferred) → lr (smaller preferred)  

Dictionary insertion order: neutralised by `sort_keys=True` in Step 4. ✓

---

## 7. NN Diagnostics

**Selected:** `hidden_sizes=[128,64], lr=0.001, weight_decay=0.0001`

| Metric | Expected | Actual | Match |
|--------|---------|--------|-------|
| best_epochs | [18,17,21,26,16] | [18,17,21,26,16] | YES |
| median | 18 | 18 | YES |
| std | ~4.0373 | 4.03732584763727 | YES |
| range | 10 | 10 | YES |
| range/median | ~0.5556 | 0.5555555... | YES |
| diagnostic_flag | false | false | YES |
| final_epoch_count | 18 | 18 | YES |

Non-selected configs with `diagnostic_flag=true` (training variability warnings):

| Config | range/median | flag |
|--------|-------------|------|
| [128,64] lr=0.001 wd=0.001 | 2.000 | true (non-selected) |
| [256,128] lr=0.001 wd=0.0001 | 1.524 | true (non-selected) |
| [256,128] lr=0.001 wd=0.001 | 1.118 | true (non-selected) |

These warnings belong to REJECTED configurations only. Selected NN is clean. ✓

---

## 8. NN pos_weight

| Item | Value |
|------|-------|
| Formula | N_normal / N_attack = 44800 / 117595 |
| Expected | 0.38096858 |
| Stored (`nn_metadata.json`) | 0.38096857859602873 |
| Match (tol 1e-8) | YES |
| Per-fold? | NO — hardcoded constant in `neural_network.py` |

---

## 9. Preprocessing Audit

| Model | Representation | Scaler | CV contract | Refit contract |
|-------|---------------|--------|-------------|----------------|
| DT | Encoded + unscaled | None | No scaler | No scaler |
| RF | Encoded + unscaled | None | No scaler | No scaler |
| SVM | Encoded + scaled | StandardScaler | fit on inner_train only | fit on full TRAIN |
| NN | Encoded + scaled | StandardScaler | fit on inner_train only | fit on full TRAIN |

From metadata:
- `svm_metadata.json`: `"StandardScaler fitted on full frozen TRAIN"` ✓
- `nn_metadata.json`: `"StandardScaler fitted on full frozen TRAIN"` ✓

No Sprint 2 or Sprint 4 scaler reused. OHE `handle_unknown=ignore`. ✓

---

## 10. Checkpoint Audit (Post-Fix)

All four checkpoint `*_metadata.json` files now contain `feature_set` and `feature_count`:

| Model | feature_set | feature_count | train_sha256 OK | model_type OK |
|-------|------------|--------------|-----------------|---------------|
| DT    | EXP_MI_V1_1 | 75          | YES             | YES |
| RF    | EXP_MI_V1_1 | 75          | YES             | YES |
| SVM   | EXP_MI_V1_1 | 75          | YES             | YES |
| NN    | EXP_MI_V1_1 | 75          | YES             | YES |

| Model | Files Complete | Loadable | Features | Key Contract |
|-------|---------------|----------|----------|-------------|
| DT | ✓ | ✓ | n_features_in_=75 | — |
| RF | ✓ | ✓ | n_features_in_=75 | predict_proba present |
| SVM | ✓ (+ scaler) | ✓ | scaler n_features=75 | predict_proba ABSENT, decision_function PRESENT |
| NN | ✓ (+ scaler + arch) | ✓ | input_dim=75 | final_epoch_count=18 |

---

## 11. Checkpoint Prediction Sanity

`validate_base_models.py` — 38/38 PASS (re-verified after pre-freeze fixes):

| Model | macro_f1 | Both classes | Structural |
|-------|----------|-------------|-----------|
| DT    | 1.0000   | YES         | OK |
| RF    | 1.0000   | YES         | OK |
| SVM   | 0.8998   | YES         | OK |
| NN    | 0.9200   | YES         | OK |

Note: DT/RF macro_f1=1.0 on 100 TRAIN-reference rows is expected behaviour
(in-distribution structural sanity check, not a performance claim).

---

## 12. Data Isolation

No forbidden file accessed in any experimental phase. Confirmed by:
- Source code inspection (no `read_csv` of forbidden files)
- 29 adversarial leakage tests PASS
- 2 runtime LEAKAGE checks in validation script PASS

---

## 13. Protected Data Integrity

| File | SHA-256 | Registry Match | Status |
|------|---------|---------------|--------|
| protected_unseen_attack.csv | `6ffd23479b575e438ad90678268f40f674a663c2b9507aaf65089623397a9d91` | YES | UNCHANGED |
| development_test.csv | `04725e85732ab2fc6d9eaaa6105418b22b083b5c651067e7b0785464f414e508` | YES | UNCHANGED |

---

## 14. Registry (Post-Fix)

| Experiment | Status |
|-----------|--------|
| EXP_DATA_ACQUISITION_AUDIT | FROZEN ✓ |
| EXP_UNSEEN_RESERVATION | FROZEN ✓ |
| EXP_PREPROCESSING_V1 | FROZEN ✓ |
| EXP_TRAIN_VAL_SPLIT_V1 | FROZEN ✓ |
| EXP_MI_V1_1 | FROZEN ✓ |
| EXP_BASE_MODELS_V1 | **IMPLEMENTED** ✓ |

`EXP_BASE_MODELS_V1` now present in `experiment_registry.json` with full provenance
(feature_set, feature_count, TRAIN hash, selected configs, artifact paths, checkpoint paths).

---

## 15. Result Plausibility

| Rank | Model | Mean Macro-F1 | Std      |
|------|-------|--------------|----------|
| 1    | RF    | 0.9508532    | 0.002000 |
| 2    | DT    | 0.9388952    | 0.002023 |
| 3    | NN    | 0.9242676    | 0.004917 |
| 4    | SVM   | 0.9202929    | 0.001703 |

Expected ordering: RF > DT > NN > SVM ✓

No impossible values, no identical folds, no unexplained jumps, no missing stds.

---

## 16. Runtime Report

| Phase | Model | Runtime |
|-------|-------|---------|
| Baseline | DT | 9.42 s |
| Baseline | RF | 31.22 s |
| Baseline | SVM | 79.32 s |
| Baseline | NN | 284.21 s (GPU) |
| Refit | DT | 2.45 s |
| Refit | SVM | 14.62 s |
| Refit | NN | 57.57 s (GPU) |

Benchmark estimated total tuning: 90.75 min (within 120-min threshold). ✓  
Environment: Python 3.11.9, PyTorch 2.7.1+cu118, scikit-learn 1.9.0, CUDA available.

---

## 17. Warning Audit

- **Category A (test fixture):** None.
- **Category B/C (production/model-training):** 3 non-selected NN configs with `diagnostic_flag=true` due to `range/median > 1.0`. These belong to rejected configurations. No action required.
- **Category D (convergence):** SVM `max_iter=5000` set to prevent `ConvergenceWarning`. No convergence failures observed.

---

## 18. Reproducibility Audit

| Model | Reproducibility | Guarantee |
|-------|---------------|-----------|
| DT | Fully deterministic | `random_state=42` |
| RF | Fully deterministic | `random_state=42`, joblib-parallel seed fixed |
| SVM | Fully deterministic | `random_state=42` |
| NN | Seeded, not fully deterministic | Python/NumPy/PyTorch/CUDA seeds set; cuDNN benchmarking not disabled (documented policy) |

---

## 19. Test Count Reconciliation (Issue 4)

**Total: 691 passed / 0 failed / 0 skipped**

Exact per-file breakdown (from `pytest --collect-only`):

| Category | Test File | Count |
|----------|-----------|-------|
| **Sprint 1–2: Data & Preprocessing** | test_canonicalization.py | 11 |
| | test_cleaning.py | 25 |
| | test_encoding.py | 21 |
| | test_hashing.py | 10 |
| | test_loader.py | 10 |
| | test_overlap.py | 6 |
| | test_preprocessing_leakage.py | 21 |
| | test_preprocessing_pipeline.py | 34 |
| | test_processed_dataset.py | 20 |
| | test_protected_unseen_attack.py | 13 |
| | test_scaling.py | 19 |
| | test_schema_audit.py | 22 |
| | test_schema_validator.py | 10 |
| | test_withheld_candidate.py | 12 |
| **Sprint 1–2 Subtotal** | | **234** |
| **Sprint 3: Split Protocol** | test_split_leakage.py | 20 |
| | test_split_protocol.py | 54 |
| **Sprint 3 Subtotal** | | **74** |
| **Sprint 4: Feature Selection** | test_k_selector.py | 25 |
| | test_mi_leakage.py | 16 |
| | test_mi_selector.py | 62 |
| | test_mi_v1_1.py | 45 |
| **Sprint 4 Subtotal** | | **148** |
| **Sprint 5: Base Models** | test_base_models_leakage.py | 29 |
| | test_base_models_preprocessing.py | 27 |
| | test_comparator.py | 31 |
| | test_decision_tree.py | 32 |
| | test_linear_svc.py | 31 |
| | test_neural_network.py | 44 |
| | test_random_forest.py | 27 |
| | test_validation_preprocessing_contract.py | 14 |
| **Sprint 5 Subtotal** | | **235** |
| **Grand Total** | | **691** |

**Arithmetic check:** 234 + 74 + 148 + 235 = **691** ✓

**Note on previous quality review:** The prior breakdown of "Sprint 1–4 ≈ 470 / Sprint 5 base model tests = 221 / validation regression = 22" used imprecise rounding and double-counted the 14 validation regression tests (which are part of the Sprint 5 total). Corrected above.

---

## 20. Remaining Issues

**All three pre-freeze issues have been resolved.**

| Issue | Status |
|-------|--------|
| 1 — `feature_set`/`feature_count` in checkpoint metadata | **RESOLVED** |
| 2 — `EXP_BASE_MODELS_V1` in experiment registry | **RESOLVED** |
| 3 — `metadata.json` in results directory | **RESOLVED** |

No remaining issues.

---

## Statements

- **No retraining was performed.** No model was retrained at any point during the pre-freeze fix.
- **No model configuration was changed.** Selected hyperparameters are identical to what was determined during the tuning phase.
- **No model weights were modified.** All checkpoint files (`*.joblib`, `*.pt`) are unchanged from the refit step.
- **Validation remains 38/38 PASS.** Re-verified after documentation fixes.
- **Test suite remains 691/691 PASS.** Re-verified after documentation fixes.

---

## Final Recommendation

**STATUS: READY_TO_FREEZE**

All documentation issues resolved. All verification checks pass.
The freeze step (freeze commit + `EXP_BASE_MODELS_V1` tag + registry `status=FROZEN`) may proceed.
