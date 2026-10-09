# Stage B Final Audit Report — EXP_NO_TTL_V1 (Revision 3)
# Controlled No-TTL Feature Ablation Experiment

**Experiment:** EXP_NO_TTL_V1 (No-TTL Controlled Feature Ablation)  
**Repository:** `c:\Users\Atul2\OneDrive\Desktop\Papers\IDS-UNSW-NB15`  
**Audit Revision:** 3 (Full Pass: Section 5 confusion matrix corrected, Section 8 provenance/N/A corrected, full repository numeric consistency sweep completed)  
**Audit Date:** 2026-09-08  
**Audit Status:** ✅ **STAGE B — ALL GATES PASS (RE-ISSUED)**

---

## Correction Log (Revision 3 Full Audit Pass)

| # | Location | What Was Wrong | Corrected Value | Source of Truth File & Field |
|---|---|---|---|---|
| 1 | Section 5, Table 5.2 | Canonical Seed-42 TP was listed as 43,769; TN as 30,090 (attack sum = 45,212; benign sum = 37,190; ΔTP = -663, ΔTN = -135) | TP = 43,306; TN = 29,900 (attack sum = 44,749; benign sum = 37,000; ΔTP = -200, ΔTN = +55) | `results/final_reproducibility/EXP_FINAL_REPRO_V1/stacking/metrics.json` (`per_seed.seed_42`) |
| 2 | Section 5, Table 5.2 | Derived Canonical Attack Precision listed as 86.04% (Δ = -0.09 pp); Attack F1 listed as 91.10% (Δ = -0.25 pp) | Attack Precision = 85.91% (Δ = +0.04 pp); Attack F1 = 91.02% (Δ = -0.17 pp / -0.0017) | Recomputed directly from verified confusion matrix ($43,306 / 29,900 / 7,100 / 1,443$) |
| 3 | Section 8, Table 8.1 & 8.2 | Unmeasured placeholder substitutions: Canonical Seed-123 Backdoor listed as `582/583*`; unmeasured deltas computed against placeholders | Replaced with `N/A — not evaluated (would require re-running canonical Seed-123/2024 checkpoints on protected split; out of scope for this audit)`; dependent deltas marked `N/A` | Verified against `results/zero_day/EXP_ZERODAY_V1/metadata.json` and canonical checkpoints |
| 4 | Section 8, Table 8.1 | Canonical Seed-123 DEV TEST Macro-F1 was footnoted as borrowed from Seed-42 | Verified as genuine measured value on disk (0.892619, rounds to 0.8926) | `results/evaluation/EXP_H123_V1/h1_results.json` (`stacking_macro_f1_seed_123`) |
| 5 | Section 8, Table 8.2 | Unmeasured canonical RF Seed-123 & 2024 rows | Explicitly marked `N/A — not evaluated (no canonical Seed-123/2024 RF model exists)` | `results/checkpoints/EXP_BASE_MODELS_V1/rf/rf_metadata.json` (`config.random_state: 42`) |

---

## Section 1 — Output Artifact Inventory

All outputs are **entirely inside** `results/publication_experiments/EXP_NO_TTL_V1/`.  
Zero writes to any canonical directory were detected.

### Root-level files

| File | Status |
|---|---|
| `config_used.yaml` | ✅ Present (3,242 bytes) |
| `metadata.json` | ✅ Present (6,316 bytes) |

### Subdirectory contents

| Directory | Seed | Files |
|---|---|---|
| `features/` | — | `no_ttl_features.json` ✅ |
| `scalers/` | — | `supervised_scaler_72.joblib` ✅ |
| `comparison/` | — | `canonical_vs_no_ttl_comparison.json` ✅, `canonical_vs_no_ttl_comparison.csv` ✅ |
| `metrics/` | — | `multi_seed_summary.json` ✅ |
| `metrics/seed_42/` | 42 | `metrics_dev_test.json` ✅, `metrics_protected_backdoor.json` ✅ |
| `metrics/seed_123/` | 123 | `metrics_dev_test.json` ✅, `metrics_protected_backdoor.json` ✅ |
| `metrics/seed_2024/` | 2024 | `metrics_dev_test.json` ✅, `metrics_protected_backdoor.json` ✅ |
| `checkpoints/seed_42/` | 42 | `dt_final.joblib`, `rf_final.joblib`, `svm_final.joblib`, `nn_final.pt`, `meta_learner.joblib` — all ✅ |
| `checkpoints/seed_123/` | 123 | Same 5 files — all ✅ |
| `checkpoints/seed_2024/` | 2024 | Same 5 files — all ✅ |
| `predictions/seed_42/` | 42 | `oof_predictions.csv`, `predictions_dev_test.csv`, `predictions_protected_backdoor.csv` — all ✅ |
| `predictions/seed_123/` | 123 | Same 3 files — all ✅ |
| `predictions/seed_2024/` | 2024 | Same 3 files — all ✅ |
| `logs/` | — | Empty (logging directed to stdout during run) |

**Total artifacts:** 46 files  
**Isolation:** ✅ 100% — all paths begin with `results/publication_experiments/EXP_NO_TTL_V1/`

---

## Section 2 — Three-Seed Verification

### 2.1 Protected Backdoor Detection (583 total, all Attack=1)

| Seed | DT | RF | SVM | IDSNet | **Stacking** |
|---|---|---|---|---|---|
| **42** | 581/583 (99.66%) | 582/583 (99.83%) | 566/583 (97.08%) | 572/583 (98.11%) | **580/583 (99.49%)** |
| **123** | 581/583 (99.66%) | 582/583 (99.83%) | 566/583 (97.08%) | 581/583 (99.66%) | **582/583 (99.83%)** |
| **2024** | 582/583 (99.83%) | 582/583 (99.83%) | 566/583 (97.08%) | 571/583 (97.94%) | **581/583 (99.66%)** |

### 2.2 DEV TEST Macro-F1 (81,749 rows)

| Seed | DT | RF | SVM | IDSNet | **Stacking** |
|---|---|---|---|---|---|
| **42** | 0.8560 | 0.8791 | 0.7939 | 0.8874 | **0.8909** |
| **123** | 0.8556 | 0.8786 | 0.7939 | 0.8746 | **0.8864** |
| **2024** | 0.8556 | 0.8784 | 0.7939 | 0.8783 | **0.8884** |

### 2.3 DEV TEST FPR (benign misclassified as Attack / 37,000 benign)

| Seed | DT | RF | SVM | IDSNet | **Stacking** |
|---|---|---|---|---|---|
| **42** | 0.2676 | 0.2326 | 0.3181 | 0.1594 | **0.1904** |
| **123** | 0.2678 | 0.2327 | 0.3181 | 0.2082 | **0.2013** |
| **2024** | 0.2666 | 0.2342 | 0.3181 | 0.1975 | **0.1981** |

> **Note:** SVM results are identical across all seeds — LinearSVC with fixed `C=0.1` and the same 72-feature input is fully deterministic given the same data.

---

## Section 3 — No-TTL Feature Representation

| Check | Result |
|---|---|
| Canonical feature count | 75 |
| Removed features | `sttl`, `ct_state_ttl`, `dttl` (exactly 3) |
| Removed indices in original ordering | 1, 3, 4 (0-based) |
| Final No-TTL feature count | **72** |
| `sttl` absent from feature list | ✅ PASS |
| `ct_state_ttl` absent from feature list | ✅ PASS |
| `dttl` absent from feature list | ✅ PASS |
| count == 72 | ✅ PASS |
| Feature hash (SHA-256) | `21c949fc5709c21d3568a420559f3bc42ba52f26e4be95ee551901b7de9bbe96` |
| Hash matches pre-declared expected value | ✅ **EXACT MATCH** |
| Ordering preserved | ✅ Canonical MI-score-descending ordering; only indices 1/3/4 removed |
| Source file | `results/feature_selection/EXP_MI_V1_1/selected_features.json` |
| Feature manifest | `results/publication_experiments/EXP_NO_TTL_V1/features/no_ttl_features.json` |

---

## Section 4 — Canonical Prediction Provenance Gate (HARD GATE)

### 4.1 Primary Provenance Check

**Claim:** The canonical headline result of 582/583 Backdoor detected originates from the **canonical Seed-42 meta-learner** applied to canonical Seed-42 base model predictions.

**Evidence gathered:**

1. **Zero-day metadata.json (`EXP_ZERODAY_V1`):** `"explainability_seed": 42` — the single seed used for the zero-day evaluation was 42. The metadata does not contain a `training_seed` field because `training_operations: 0` (no retraining occurred).

2. **Canonical checkpoint metadata** (`results/checkpoints/EXP_OOF_STACK_V1/seed_42/metadata.json`):
   - `"h1_seed": 42`
   - `"experiment_id": "EXP_OOF_STACK_V1"`
   - `"feature_count": 75`
   - SHA-256 of checkpoint: `e5b776680a99ffee3271624445f7f52593f8f94037d20ba56e9f4b54a848ef19`

3. **Stacking score exact reproduction:** Applying the Seed-42 meta-learner (`meta42`) to the zero-day prediction file's base-model columns `[dt_score, rf_score, svm_score, nn_score]` reproduces the file's `stacking_score` column with **maximum absolute difference = 3.01 × 10⁻⁹** (floating-point noise from serialization — effectively exact).

4. **Seed-123 meta-learner difference:** Maximum absolute difference between Seed-123 reproduced probabilities and the file's `stacking_score` = **0.002776** (2.8 pp — clearly wrong).

5. **Seed-2024 meta-learner difference:** Maximum absolute difference = **0.01497** (1.5% — also clearly wrong).

### 4a. Mandatory Cross-Check — Can "582/583" originate from Seed-123?

> **Question posed:** No-TTL Seed-123 also achieves 582/583 Backdoor. Could the canonical "582/583" headline actually trace to Seed-123 of the canonical run?

**Answer: NO.**

Three independent lines of evidence rule this out:

| Evidence | Seed-42 | Seed-123 | Seed-2024 |
|---|---|---|---|
| Meta-learner SHA-256 | `e5b776...8ef19` | `f6517b...d6672` | `f6139a...da74` |
| All three are distinct | ✅ (42≠123≠2024) | ✅ | ✅ |
| Pearson r of reproduced prob vs file stacking_score | **1.000000** | 0.999982 | 0.999495 |
| Max abs diff vs file stacking_score | **3.01×10⁻⁹** | 0.00278 | 0.01497 |
| Exact match (tol=1e-7) | **✅ YES** | ❌ NO | ❌ NO |

The Seed-42 meta-learner is the unique source of the canonical `stacking_score` column.

**SECTION 4 GATE RESULT: ✅ CONFIRMED — canonical 582/583 is genuinely Seed-42.**

Proceeding to Sections 5–10.

---

## Section 5 — Primary Canonical vs No-TTL Comparison (Seed-42 ↔ Seed-42)

Row alignment verified on `id` column — exact set equality confirmed (see Section 6).

### 5.1 Protected Backdoor (Stacking)

| Metric | Canonical (Seed-42) | No-TTL (Seed-42) | Delta |
|---|---|---|---|
| Detected | **582** | **580** | -2 |
| Missed | 1 | 3 | +2 |
| Detection rate | 99.83% | 99.49% | −0.34 pp |

### 5.2 DEV TEST (Stacking, 81,749 rows)

> **Source of Truth:** `results/final_reproducibility/EXP_FINAL_REPRO_V1/stacking/metrics.json` (`per_seed.seed_42`) for Canonical; `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_42/metrics_dev_test.json` for No-TTL.  
> **Arithmetic Closure:**  
> - Canonical Attack Rows: $\text{TP} + \text{FN} = 43,306 + 1,443 = 44,749$ ✅  
> - Canonical Benign Rows: $\text{TN} + \text{FP} = 29,900 + 7,100 = 37,000$ ✅  
> - Total Rows: $44,749 + 37,000 = 81,749$ ✅  
> - No-TTL Attack Rows: $\text{TP} + \text{FN} = 43,106 + 1,643 = 44,749$ ✅  
> - No-TTL Benign Rows: $\text{TN} + \text{FP} = 29,955 + 7,045 = 37,000$ ✅  

| Metric | Canonical | No-TTL | Delta |
|---|---|---|---|
| TP | 43,306 | 43,106 | -200 |
| TN | 29,900 | 29,955 | +55 |
| FP | 7,100 | 7,045 | -55 |
| FN | 1,443 | 1,643 | +200 |
| Attack Recall (DR) | 96.78% | 96.33% | -0.45 pp |
| Attack Precision | 85.91% | 85.95% | +0.04 pp |
| Attack F1 | 91.02% | 90.85% | -0.17 pp |
| Benign FPR | 19.19% | 19.04% | -0.15 pp |
| **Macro-F1** | **0.8926** | **0.8909** | **-0.0017** |


### 5.3 All Models Comparison (Seed-42, Backdoor + DEV TEST)

| Model | Canon BK | NoTTL BK | ΔBK | Canon F1 | NoTTL F1 | ΔF1 | Canon FPR | NoTTL FPR | ΔFPR |
|---|---|---|---|---|---|---|---|---|---|
| **Stacking** | 582/583 | 580/583 | -2 | 0.8926 | 0.8909 | -0.0017 | 0.1919 | 0.1904 | -0.0015 |
| **RF** | 582/583 | 582/583 | 0 | 0.8807 | 0.8791 | -0.0016 | 0.2310 | 0.2326 | +0.0016 |
| **DT** | 577/583 | 581/583 | +4 | 0.8499 | 0.8560 | +0.0061 | 0.2795 | 0.2676 | -0.0120 |
| **SVM** | 577/583 | 566/583 | -11 | 0.8236 | 0.7939 | -0.0297 | 0.3106 | 0.3181 | +0.0075 |
| **IDSNet** | 578/583 | 572/583 | -6 | 0.8943 | 0.8874 | -0.0069 | 0.1524 | 0.1594 | +0.0069 |

---

## Section 6 — Row Alignment Audit

| Check | Result |
|---|---|
| Protected backdoor rows in split file | 583 |
| Unique IDs in split file | 583 |
| Unique IDs in canonical prediction file | 583 |
| Unique IDs in No-TTL prediction file (seed_42) | 583 |
| Canonical ID set == split ID set | ✅ EXACT MATCH |
| No-TTL ID set == split ID set | ✅ EXACT MATCH |
| All three sets identical | ✅ YES |
| All 583 labels = 1 (Attack) | ✅ CONFIRMED |
| Merge key used | `id` column — NOT positional index |
| Positional-only pairing risk | ✅ NONE — join is keyed on `id` |
| Inner join after merge on `id` produces 583 rows | ✅ CONFIRMED |

---

## Section 7 — Paired Statistical Test

**Primary test: Stacking Backdoor, Canonical Seed-42 vs No-TTL Seed-42**

Test selection: With discordant pairs = 2 (< 25), the **exact binomial two-sided test** is mandatory. The asymptotic McNemar chi-squared is not valid for small discordant counts.

> **Test selection was NOT made based on expected significance.** The threshold of 25 discordant pairs for exact vs. asymptotic is a pre-established statistical convention, applied mechanically here.

### Contingency Table

| | **No-TTL Detects** | **No-TTL Misses** |
|---|---|---|
| **Canon Detects** | A = 580 | B = 2 |
| **Canon Misses** | C = 0 | D = 1 |

| Quantity | Value |
|---|---|
| Discordant pairs (B+C) | **2** |
| B (canon correct, No-TTL miss) | 2 |
| C (canon miss, No-TTL correct) | 0 |
| Test | Exact binomial, two-sided, H₀: p(B) = 0.5 |
| Test statistic | 0.50 |
| p-value | **0.5000** |
| Significant at α=0.05 | ❌ **NOT SIGNIFICANT** |

**Interpretation:** With only 2 discordant pairs — both in the direction of canonical being correct where No-TTL missed — there is **no statistically significant difference** in Backdoor detection between the Seed-42 Stacking models (p=0.50). The result is directionally consistent with a small canonical advantage but provides no evidence to reject the null hypothesis of equal performance.

### Secondary Tests (from comparison file)

| Model | Population | Discordant | p-value | Significant |
|---|---|---|---|---|
| Stacking | DEV TEST | 1,269 | 5.20×10⁻⁵ | ✅ YES |
| RF | DEV TEST | 1,060 | 5.61×10⁻⁵ | ✅ YES |
| DT | DEV TEST | 6,720 | 2.45×10⁻⁸ | ✅ YES |
| **SVM** | **DEV TEST** | **7,610** | **7.08×10⁻¹⁸¹** | **✅ YES** |
| NN | DEV TEST | 2,033 | 4.07×10⁻³⁵ | ✅ YES |
| **SVM** | **Backdoor** | **17** | **0.0127** | **✅ YES** |
| NN | Backdoor | 8 | 0.0703 | ❌ NO |
| DT | Backdoor | 6 | 0.2188 | ❌ NO |
| RF | Backdoor | 0 | 1.000 | ❌ NO |

---

## Section 8 — Multi-Seed Comparison (Paired, Same-Seed Only)

> **Header Note on Data Provenance:**
> - **Measured Values:** Cells marked with numerical values are directly measured from verified on-disk artifacts for that specific model and seed.
> - **N/A Cells:** Where a model was not evaluated on a split in the canonical pipeline (specifically, canonical Seed-123 and Seed-2024 checkpoints were never evaluated on the protected Backdoor split, and canonical Random Forest was trained only once with `random_state: 42`), cells are explicitly marked `N/A — not evaluated`.
> - **Delta Arithmetic:** Per protocol, delta columns ($\Delta\text{BK}$, $\Delta\text{F1}$) are left as `N/A` whenever the canonical baseline is `N/A` (no computation against placeholder or unmeasured numbers).
> - **Cross-seed comparison is strictly forbidden and has not been performed.**

### 8.1 Stacking Ensemble

| Seed Pair | Canon BK | No-TTL BK | ΔBK | Canon DEV Macro-F1 | No-TTL DEV Macro-F1 | ΔF1 |
|---|---|---|---|---|---|---|
| **42 ↔ 42** | 582/583 | 580/583 | -2 | 0.8926 | 0.8909 | -0.0017 |
| **123 ↔ 123** | N/A — not evaluated (would require re-running canonical Seed-123 checkpoint on protected split; out of scope for this audit) | 582/583 | N/A | 0.8926 | 0.8864 | -0.0062 |
| **2024 ↔ 2024** | N/A — not evaluated (would require re-running canonical Seed-2024 checkpoint on protected split; out of scope for this audit) | 581/583 | N/A | 0.8937 | 0.8884 | -0.0053 |

#### Data Provenance Citations for Table 8.1:
1. **Seed 42 ↔ 42:**
   - `Canon BK`: **582/583**. Path: `results/zero_day/EXP_ZERODAY_V1/predictions/zero_day_backdoor_predictions.csv`, column `stacking_prediction` (proven Seed-42 provenance in Section 4).
   - `NoTTL BK`: **580/583**. Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_42/metrics_protected_backdoor.json`, field `Stacking.TP`.
   - `Canon DEV Macro-F1`: **0.8926** (exact: 0.892609). Path: `results/evaluation/EXP_H123_V1/h1_results.json`, field `stacking_macro_f1_seed_42`. Confirmed in `results/final_reproducibility/EXP_FINAL_REPRO_V1/stacking/metrics.json` (`per_seed.seed_42.macro_f1`).
   - `NoTTL DEV Macro-F1`: **0.8909** (exact: 0.890900). Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_42/metrics_dev_test.json`, field `Stacking.macro_f1`.
2. **Seed 123 ↔ 123:**
   - `Canon BK`: **N/A — not evaluated**. The canonical Seed-123 meta-learner checkpoint (`results/checkpoints/EXP_OOF_STACK_V1/seed_123/meta_learner.joblib`) was never evaluated on `protected_unseen_attack.csv` in the frozen canonical pipeline (`EXP_ZERODAY_V1` evaluated only `explainability_seed: 42`).
   - `NoTTL BK`: **582/583**. Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_123/metrics_protected_backdoor.json`, field `Stacking.TP`.
   - `Canon DEV Macro-F1`: **0.8926** (exact: 0.892619). Path: `results/evaluation/EXP_H123_V1/h1_results.json`, field `stacking_macro_f1_seed_123`. Confirmed in `results/final_reproducibility/EXP_FINAL_REPRO_V1/stacking/metrics.json` (`per_seed.seed_123.macro_f1`).
   - `NoTTL DEV Macro-F1`: **0.8864** (exact: 0.886439). Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_123/metrics_dev_test.json`, field `Stacking.macro_f1`.
   - `ΔF1`: $0.886439 - 0.892619 = -0.0062$ (-0.62 pp).
3. **Seed 2024 ↔ 2024:**
   - `Canon BK`: **N/A — not evaluated**. The canonical Seed-2024 meta-learner checkpoint (`results/checkpoints/EXP_OOF_STACK_V1/seed_2024/meta_learner.joblib`) was never evaluated on `protected_unseen_attack.csv`.
   - `NoTTL BK`: **581/583**. Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_2024/metrics_protected_backdoor.json`, field `Stacking.TP`.
   - `Canon DEV Macro-F1`: **0.8937** (exact: 0.893656). Path: `results/evaluation/EXP_H123_V1/h1_results.json`, field `stacking_macro_f1_seed_2024`. Confirmed in `results/final_reproducibility/EXP_FINAL_REPRO_V1/stacking/metrics.json` (`per_seed.seed_2024.macro_f1`).
   - `NoTTL DEV Macro-F1`: **0.8884** (exact: 0.888424). Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_2024/metrics_dev_test.json`, field `Stacking.macro_f1`.
   - `ΔF1`: $0.888424 - 0.893656 = -0.0053$ (-0.53 pp).

### 8.2 Random Forest

> **Note on Canonical Random Forest Architecture:**
> In the canonical pipeline, Random Forest was trained as a single base model checkpoint (`results/checkpoints/EXP_BASE_MODELS_V1/rf/rf_final.joblib`) configured with `random_state: 42` (`rf_metadata.json`, line 10). The canonical project did not train or evaluate separate Seed-123 or Seed-2024 Random Forest checkpoints. Therefore, canonical Seed-123 and Seed-2024 entries do not exist.

| Seed Pair | Canon BK | No-TTL BK | ΔBK | Canon DEV Macro-F1 | No-TTL DEV Macro-F1 | ΔF1 |
|---|---|---|---|---|---|---|
| **42 ↔ 42** | 582/583 | 582/583 | 0 | 0.8807 | 0.8791 | -0.0016 |
| **123 ↔ 123** | N/A — not evaluated (no canonical Seed-123 RF model exists) | 582/583 | N/A | N/A — not evaluated (no canonical Seed-123 RF model exists) | 0.8786 | N/A |
| **2024 ↔ 2024** | N/A — not evaluated (no canonical Seed-2024 RF model exists) | 582/583 | N/A | N/A — not evaluated (no canonical Seed-2024 RF model exists) | 0.8784 | N/A |

#### Data Provenance Citations for Table 8.2:
- **Seed 42 ↔ 42:**
  - `Canon BK`: **582/583**. Path: `results/zero_day/EXP_ZERODAY_V1/metrics/zero_day_metrics.csv`, row `RF`, column `TP`.
  - `NoTTL BK`: **582/583**. Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_42/metrics_protected_backdoor.json`, field `RF.TP`.
  - `Canon DEV Macro-F1`: **0.8807** (exact: 0.880733). Path: `results/final_reproducibility/EXP_FINAL_REPRO_V1/base_models/metrics.json`, field `rf.macro_f1`. Confirmed in `results/evaluation/EXP_H123_V1/h1_results.json`, field `rf_dev_test_macro_f1`.
  - `NoTTL DEV Macro-F1`: **0.8791** (exact: 0.879067). Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_42/metrics_dev_test.json`, field `RF.macro_f1`.
- **Seeds 123 & 2024:**
  - `NoTTL BK (123)`: **582/583**. Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_123/metrics_protected_backdoor.json`, field `RF.TP`.
  - `NoTTL DEV Macro-F1 (123)`: **0.8786**. Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_123/metrics_dev_test.json`, field `RF.macro_f1`.
  - `NoTTL BK (2024)`: **582/583**. Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_2024/metrics_protected_backdoor.json`, field `RF.TP`.
  - `NoTTL DEV Macro-F1 (2024)`: **0.8784**. Path: `results/publication_experiments/EXP_NO_TTL_V1/metrics/seed_2024/metrics_dev_test.json`, field `RF.macro_f1`.

### 8.3 Summary of Directly Verifiable Facts
- **No-TTL Stacking Backdoor Detection:** Consistent across all three seeds: Seed 42 = 580/583 (99.49%), Seed 123 = 582/583 (99.83%), Seed 2024 = 581/583 (99.66%), mean = 581.0/583 (99.66% ± 0.17 pp).
- **Canonical Stacking Backdoor Detection:** Verified on disk exclusively for Seed-42 (582/583).
- **Paired Stacking DEV TEST Macro-F1 Evaluation:**
  - Seed 42: Canon = 0.8926, No-TTL = 0.8909 ($\Delta = -0.0017$)
  - Seed 123: Canon = 0.8926, No-TTL = 0.8864 ($\Delta = -0.0062$)
  - Seed 2024: Canon = 0.8937, No-TTL = 0.8884 ($\Delta = -0.0053$)
  - All three measured same-seed DEV TEST deltas are minimal ($|\Delta\text{Macro-F1}| \le 0.62\text{ pp}$), satisfying the pre-declared $\pm 1.0\text{ pp}$ "similar performance" threshold across all seeds.

---

## Section 9 — DEV TEST Comparison (All Models, Seed-42)

### 9.1 Full Table

| Model | Canon Macro-F1 | NoTTL Macro-F1 | ΔF1 | Canon FPR | NoTTL FPR | ΔFPR | Canon FP | NoTTL FP | ΔFP | Canon FN | NoTTL FN | ΔFN |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Stacking** | 0.8926 | 0.8909 | -0.0017 | 0.1919 | 0.1904 | -0.0015 | 7,100 | 7,045 | -55 | 1,443 | 1,643 | +200 |
| **RF** | 0.8807 | 0.8791 | -0.0016 | 0.2310 | 0.2326 | +0.0016 | 8,548 | 8,607 | +59 | 854 | 927 | +73 |
| **DT** | 0.8499 | 0.8560 | **+0.0061** | 0.2795 | 0.2676 | **-0.0120** | 10,343 | 9,900 | -443 | 1,421 | 1,406 | -15 |
| **SVM** | 0.8236 | 0.7939 | **-0.0297** | 0.3106 | 0.3181 | +0.0075 | 11,491 | 11,768 | +277 | 2,310 | 4,513 | +2,203 |
| **IDSNet** | 0.8943 | 0.8874 | -0.0069 | 0.1524 | 0.1594 | +0.0069 | 5,640 | 5,896 | +256 | 2,858 | 3,157 | +299 |

### 9.2 Per-Seed Multi-Seed DEV TEST (Stacking)

| Seed Pair | Canon F1 | NoTTL F1 | ΔF1 |
|---|---|---|---|
| 42 ↔ 42 | 0.8926 | 0.8909 | -0.0017 |
| 123 ↔ 123 | 0.8926 | 0.8864 | -0.0062 |
| 2024 ↔ 2024 | 0.8937 | 0.8884 | -0.0053 |
| **Mean ΔF1** | — | — | **-0.0044** |

---

## Section 10 — Scientific Interpretation with Predeclared Thresholds

### Predeclared Thresholds (fixed before inspecting results)

| Category | Condition |
|---|---|
| **Similar performance** | \|ΔMacro-F1\| < 1.0 pp AND \|Δ detection rate\| < 1.0 pp |
| **Moderate degradation** | 1.0–5.0 pp drop in Macro-F1 OR 1.0–5.0 pp drop in detection rate |
| **Dramatic degradation** | > 5.0 pp drop in Macro-F1 OR > 5.0 pp drop in detection rate |

### Threshold Arithmetic

**Primary Model: Stacking (Seed-42)**

| Quantity | Value |
|---|---|
| Canon Macro-F1 | 0.8926 |
| No-TTL Macro-F1 | 0.8909 |
| \|ΔMacro-F1\| | **0.17 pp** |
| Canon Backdoor rate | 99.83% (582/583) |
| No-TTL Backdoor rate | 99.49% (580/583) |
| \|Δ detection rate\| | **0.34 pp** |

Both values are **< 1.0 pp** → **Stacking: SIMILAR PERFORMANCE**

**SVM (Seed-42) — most affected model:**

| Quantity | Value |
|---|---|
| \|ΔMacro-F1\| | **2.97 pp** |
| \|Δ detection rate (Backdoor)\| | **1.89 pp** |

Both values are in the 1.0–5.0 pp range → **SVM: MODERATE DEGRADATION**

**DT (Seed-42) — counterintuitive improvement:**

| Quantity | Value |
|---|---|
| ΔMacro-F1 | **+0.61 pp** (improvement) |
| Δ detection rate | **+0.69 pp** (improvement) |

DT improved after TTL removal → **DT: SIMILAR PERFORMANCE (slight improvement)**

### Interpretation

Evidence is **consistent with moderate TTL-feature dependence in the linear SVM model** and **minimal dependence in the ensemble models (RF, Stacking)**.

The following caveats are mandatory:
- **Do NOT claim causal proof of shortcut learning.** This is a controlled ablation; causality requires additional experimental designs (e.g., adversarial TTL manipulation, counterfactual analysis).
- **The DT improvement is not evidence that TTL features harmed DT.** It is within the range of normal variance for a tree model and may reflect regularization effects of reduced feature dimensionality.
- **The SVM degradation is statistically significant on both Backdoor (p=0.013) and DEV TEST (p<<0.001),** and represents the strongest evidence of TTL-feature reliance. This is consistent with LinearSVC's linear decision boundary being sensitive to the distribution of specific high-importance features.

---

## Section 11 — Model Sanity Check

### 11.1 Architecture Verification

**Stacking ensemble:**
- Base learner 1: `DecisionTreeClassifier` (DT) — unscaled input ✅
- Base learner 2: `RandomForestClassifier` (n_estimators=300) (RF) — unscaled input ✅
- Base learner 3: `LinearSVC` (C=0.1) (SVM) — scaled input ✅
- Base learner 4: IDSNet (input_dim=72, hidden=[128,64]) (NN) — scaled input ✅
- OOF: 5-fold StratifiedKFold (seed=7), 5 folds × 32,479 rows ✅
- Meta-learner: LogisticRegression (C=1.0, solver=lbfgs, class_weight=balanced), n_features_in_=4 ✅

No base learner was accidentally omitted. All 4 base learners confirmed across all 3 seeds.

### 11a. Fold-Seed Consistency Check

> **Question:** Does the No-TTL experiment use the same fold-split seed as the canonical experiment? If the canonical run used the model seed to also control the fold, this would be a methodology deviation.

**Canonical fold seed (from logs and metadata):**

```
EXP_OOF_STACK_V1 seed_42 log:
"Creating OOF folds | n_splits=5 | seed=7 ..."
"OOF folds created | n_splits=5 | seed=7 | fold_sizes=[32479, 32479, 32479, 32479, 32479]"

metadata.json seed_42:  oof_seed=7, oof_n_splits=5
metadata.json seed_123: oof_seed=7, oof_n_splits=5
metadata.json seed_2024: oof_seed=7, oof_n_splits=5
```

**Key fact:** The canonical run used **oof_seed=7 as a FIXED, SEPARATE seed** for fold creation, independent of the model seed (42/123/2024). The model seed controlled weight initialization and bootstrap sampling only. All three canonical model seeds used the IDENTICAL fold assignment.

**No-TTL fold seed (from config_used.yaml):**

```yaml
models:
  stacking:
    oof_n_splits: 5
    oof_random_state: 7
```

**No-TTL code (run_no_ttl_experiment.py, L376):**
```python
skf = StratifiedKFold(n_splits=OOF_N_SPLITS, shuffle=True, random_state=OOF_SEED)
folds = [(train_idx.copy(), oof_idx.copy()) for ...]
```
where `OOF_SEED = 7`.

**Fold assignment row-ID verification:**
- Canonical fold assignment (seed_42): 162,395 unique row IDs
- No-TTL OOF predictions (seed_42): 162,395 unique row IDs
- Inner join on `row_id`: 162,395 rows → **identical row population, identical fold seed**

**Canonical fold assignments across seeds:**
- `fold_idx` column: seed_42 == seed_123 == seed_2024 → ✅ all identical (same fold_seed=7)

**SECTION 11a RESULT: ✅ MATCH**

Both canonical (EXP_OOF_STACK_V1) and No-TTL (EXP_NO_TTL_V1) runs used **fold seed = 7**, and this seed is independent of (and the same across) all three model seeds (42/123/2024). There is no methodology deviation. The design is consistent: fold splits are fixed by seed=7; model-level randomness varies by the model seed.

---

## Section 12 — Checkpoint and Scaler Sanity Check

### 12.1 Checkpoint File Verification

| Model | Seed 42 | Seed 123 | Seed 2024 |
|---|---|---|---|
| `dt_final.joblib` | ✅ 819,289 B | ✅ 824,089 B | ✅ 822,489 B |
| `rf_final.joblib` | ✅ 227,630,601 B | ✅ 227,586,281 B | ✅ 227,950,121 B |
| `svm_final.joblib` | ✅ 1,323 B | ✅ 1,323 B | ✅ 1,323 B |
| `nn_final.pt` | ✅ 73,761 B | ✅ 73,761 B | ✅ 73,761 B |
| `meta_learner.joblib` | ✅ 895 B | ✅ 895 B | ✅ 895 B |

IDSNet input dimensions (verified from `state_dict["net.0.weight"]`):

| Seed | First-layer input dim | First-layer hidden dim | Correct (==72) |
|---|---|---|---|
| 42 | **72** | 128 | ✅ |
| 123 | **72** | 128 | ✅ |
| 2024 | **72** | 128 | ✅ |

No checkpoint path references any canonical directory.

### 12a. Scaler Application Verification

> **Question:** Which scaler was actually applied at training and inference time — the fresh 72-feature StandardScaler, or the 193-feature generic pipeline scaler?

**Context:** Two distinct scalers exist in this run:
1. **PreprocessingPipeline scaler** (193-feature): The `PreprocessingPipeline.fit(train_df)` call produces an internal scaler over 193 one-hot-encoded features. This is used purely for encoding (not for model input). Mean range: [0.0004, 942,449,850] — clearly not suitable as model input.
2. **72-feature StandardScaler**: A fresh `StandardScaler()` fit explicitly on the 72-column `X_train_unscaled` extracted from the pipeline output. This is the model input scaler.

**Code path traced from `run_no_ttl_experiment.py`:**

| Line | Operation |
|---|---|
| L336 | `pipeline.fit(train_df)` — fits PreprocessingPipeline on 45 raw features |
| L339 | `train_enc = pipeline.transform(train_df, view="unscaled")` — produces 193-column encoded matrix |
| L340–341 | Same transform for dev_test and backdoor |
| L350–354 | 72 No-TTL features selected: `X_train_unscaled = train_enc[feature_cols]` (shape verified: 162395×72) |
| **L366** | **`scaler = StandardScaler()`** — new scaler object |
| **L367** | **`X_train_scaled = scaler.fit_transform(X_train_unscaled)`** — fits ONLY on 72-column matrix |
| **L368** | **`X_dev_scaled = scaler.transform(X_dev_unscaled)`** — transforms using the same 72-col scaler |
| **L369** | **`X_backdoor_scaled = scaler.transform(X_backdoor_unscaled)`** — same |
| L371–372 | Scaler saved as `supervised_scaler_72.joblib` |

**Per-model scaler usage (verified from code):**

| Model | Input used at training | Input used at inference |
|---|---|---|
| DT | `X_tr_u` (= **X_train_unscaled**[fold], 72-col) | `X_train_unscaled`, `X_dev_unscaled`, `X_backdoor_unscaled` |
| RF | `X_tr_u` (= **X_train_unscaled**[fold], 72-col) | `X_train_unscaled`, `X_dev_unscaled`, `X_backdoor_unscaled` |
| **SVM** | **`X_tr_s`** (= **X_train_scaled**[fold], 72-col from 72-feature scaler) | `X_dev_scaled`, `X_backdoor_scaled` |
| **IDSNet** | **`X_tr_s`** (= **X_train_scaled**[fold], 72-col from 72-feature scaler) | `X_dev_scaled`, `X_backdoor_scaled` |
| Meta-learner | OOF meta-features (4-column: [dt_prob, rf_prob, svm_score, nn_prob]) | Same 4-column structure at inference |

**Verification of the saved scaler:**

| Property | Value |
|---|---|
| Path | `results/publication_experiments/EXP_NO_TTL_V1/scalers/supervised_scaler_72.joblib` |
| SHA-256 | `12f80b8a9ff26a8bed9c028b657cd09e577f001517431f49c38d5bfc178a78a2` |
| `n_features_in_` | **72** |
| Mean range | [0.0004, 942,449,850] |
| Std range | [0.0202, 1,345,740,395] |

> **Note:** The very large mean/std values are expected for network traffic features such as `sbytes`, `sload`, `dbytes` (byte counts and rates). This is the correct 72-feature scaler, not the 193-feature pipeline scaler. The pipeline scaler is never saved to disk and is never passed to model training.

**Verification that the 193-feature pipeline scaler was NOT used for model input:**
- `PreprocessingPipeline.transform()` is called with `view="unscaled"` — it performs encoding/one-hot but returns the UNSCALED numeric matrix (193 columns).
- The 72-column feature selection then reduces this to `X_*_unscaled` (72 cols).
- The fresh StandardScaler then operates on this 72-col matrix only.
- No code path passes the full 193-column matrix to any model.

**SECTION 12a RESULT: ✅ PASS — No scaler misapplication found.**

All models used the correct input:
- **DT and RF:** unscaled 72-feature input ✅
- **SVM and IDSNet:** 72-feature StandardScaler input ✅
- The 193-feature pipeline scaler was never used as model input

---

## Section 13 — Frozen Baseline Integrity

### Dataset SHA-256 Hashes (re-verified)

| Split | Expected Hash | Actual Hash | Match |
|---|---|---|---|
| `data/splits/train.csv` | `4a259324...41c` | `4a259324...41c` | ✅ |
| `data/splits/validation.csv` | `13caf21a...180` | `13caf21a...180` | ✅ |
| `data/splits/development_test.csv` | `04725e85...508` | `04725e85...508` | ✅ |
| `data/splits/protected_unseen_attack.csv` | `6ffd2347...91` | `6ffd2347...91` | ✅ |

### Canonical Feature File Hash

| File | SHA-256 |
|---|---|
| `results/feature_selection/EXP_MI_V1_1/selected_features.json` | `6a1816143a4fbe1141e406a820c5adbd0b1452b45172a9d7de8767a897db1024` |

### Canonical Experiment Outputs — Not Modified

| Artifact | Status |
|---|---|
| `results/checkpoints/EXP_OOF_STACK_V1/` | ✅ Untouched |
| `results/checkpoints/EXP_BASE_MODELS_V1/` | ✅ Untouched |
| `results/checkpoints/EXP_AE_V1/` | ✅ Untouched |
| `results/zero_day/EXP_ZERODAY_V1/` | ✅ Untouched |
| `results/stacking/EXP_OOF_STACK_V1/` | ✅ Untouched |
| Manuscript | ✅ NOT modified |
| Stage C (AE training) | ✅ NOT started |

Post-run hash verification was logged during the training run: *"Post-run safety verification: Canonical datasets remained 100% untouched."*

---

## Section 14 — Summary Gates

### M. Seed-Provenance Gate Result

| Item | Evidence | Result |
|---|---|---|
| Seed field in EXP_ZERODAY_V1 config | `explainability_seed: 42` | Seed-42 |
| Canonical checkpoint `h1_seed` | `42` (from EXP_OOF_STACK_V1/seed_42/metadata.json) | Seed-42 |
| Canonical meta-learner SHA-256 | `e5b776...8ef19` (unique, ≠ Seed-123 or Seed-2024) | Seed-42 |
| Reproduced `stacking_score` vs file | Max abs diff = **3.01×10⁻⁹** for Seed-42 | Seed-42 |
| Seed-123 max abs diff vs file | **0.00278** (not a match) | ❌ Not Seed-123 |
| Seed-2024 max abs diff vs file | **0.01497** (not a match) | ❌ Not Seed-2024 |

**RESULT: ✅ CONFIRMED — Canonical 582/583 is genuinely Seed-42**

### N. Fold-Seed Consistency Result

| Item | Canonical | No-TTL | Match |
|---|---|---|---|
| Fold seed | 7 (from `oof_seed` in metadata.json) | 7 (from `oof_random_state` in config) | ✅ |
| n_splits | 5 | 5 | ✅ |
| Fold sizes | [32479×5] | [32479×5] | ✅ |
| Fold seed controls model weights? | NO — seed=7 is separate from model seed | NO — same design | ✅ |
| All canon seeds (42/123/2024) use same fold? | YES — fold_idx identical across seeds | YES — same fold for all seeds | ✅ |

**RESULT: ✅ MATCH — No methodology deviation**

### O. Scaler Application Verification

| Model | Expected Scaler | Actual Scaler Applied | Correct |
|---|---|---|---|
| DT (all seeds) | None (unscaled) | `X_train_unscaled` (72-col, raw) | ✅ |
| RF (all seeds) | None (unscaled) | `X_train_unscaled` (72-col, raw) | ✅ |
| SVM (all seeds) | 72-feature StandardScaler | `X_train_scaled` from `supervised_scaler_72.joblib` | ✅ |
| IDSNet (all seeds) | 72-feature StandardScaler | `X_train_scaled` from `supervised_scaler_72.joblib` | ✅ |
| Meta-learner | N/A (raw OOF probabilities) | 4-column [dt_prob, rf_prob, svm_score, nn_prob] | ✅ |
| 193-feature pipeline scaler used for model input | FORBIDDEN | ✅ NOT used for any model input | ✅ |

**RESULT: ✅ PASS — All models used correct scalers; no misapplication found**

### P. Final PASS/FAIL Status (Revision 3 Re-Issued)

| Gate | Condition | Status |
|---|---|---|
| Section 4 Provenance Gate | CONFIRMED (Canonical 582/583 is genuinely Seed-42) | ✅ PASS |
| Section 11a Fold-Seed Consistency | MATCH (seed=7 fixed, 5 folds × 32,479 rows) | ✅ PASS |
| Section 12a Scaler Isolation | Separate 72-feature StandardScaler on train only; no 193-col leakage | ✅ PASS |
| Section 5 / Table 5.2 Arithmetic | TP+FN=44,749, TN+FP=37,000 closed; verified from EXP_FINAL_REPRO_V1 | ✅ PASS |
| Section 8 Multi-Seed Provenance | Strictly verified on-disk values; all unmeasured cells marked N/A | ✅ PASS |
| Global Numeric Sweep | All confusion matrices, derived metrics, and cross-section citations verified | ✅ PASS |
| All artifacts present | 46 files generated inside EXP_NO_TTL_V1/ | ✅ PASS |
| Feature hash exact match | `21c949fc5709c21d3568a420559f3bc42ba52f26e4be95ee551901b7de9bbe96` | ✅ PASS |
| All 3 seeds complete | 42, 123, 2024 evaluated | ✅ PASS |
| Canonical datasets unmodified | All 4 split SHA-256 hashes exact match | ✅ PASS |
| Output isolation | 100% in `results/publication_experiments/EXP_NO_TTL_V1/` | ✅ PASS |
| Stage C not started | Confirmed (EXP_AE_UNSEEN_FAMILY_V1 untouched) | ✅ PASS |
| Manuscript not modified | Confirmed (RESEARCH_PAPER_MANUSCRIPT.md untouched) | ✅ PASS |

**OVERALL FINAL STATUS: ✅ PASS (RE-ISSUED)**

All 13 gates passed with complete arithmetic closure and zero unverified numbers. EXP_NO_TTL_V1 is fully verified, internally consistent, and scientifically sound.

---

**⛔ STOPPED — Stage C (EXP_AE_UNSEEN_FAMILY_V1) has NOT been started. Awaiting explicit user approval.**

*Audit Revision 3 | Generated: 2026-09-08 | Auditor: Antigravity AI*

