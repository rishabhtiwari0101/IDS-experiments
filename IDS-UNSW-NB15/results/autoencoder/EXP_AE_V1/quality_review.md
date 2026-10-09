# Sprint 7 — EXP_AE_V1 Quality Review (Revised)
## Benign-Only Autoencoder

```
Experiment:       EXP_AE_V1
Sprint:           7
Status:           READY_TO_FREEZE
Validation:       78/78 PASS
Regression:       878/878 PASS
AE Unit Tests:    76/76 PASS
Date (retrain):   2026-09-02
Device:           NVIDIA GeForce RTX 3050 Laptop GPU (CUDA 11.8)
PyTorch:          2.7.1+cu118
```

---

## Revision History

| Version | Change | Rationale |
|---------|--------|-----------|
| v1 (initial) | max_epochs = 100 | Original design decision |
| **v2 (this document)** | **max_epochs = 100 → 150** | **Decision 4 (Revised) — see §3** |

---

## 1. Frozen Upstream Integrity

| Artifact | Expected SHA (first 16) | Verified |
|----------|------------------------|---------|
| TRAIN SHA-256 | `4a259324e604f013...` | PASS |
| VALIDATION SHA-256 | `13caf21a076a33f5...` | PASS |
| EXP_MI_V1_1 feature count | 75 | PASS |
| EXP_BASE_MODELS_V1 | FROZEN | PASS |
| EXP_OOF_STACK_V1 | FROZEN (commit `c946fa65`, tag `EXP_OOF_STACK_V1`) | PASS |

All Sprint 1–6 frozen decisions preserved exactly.

---

## 2. Design Decisions Preserved (All Unchanged from Final Design)

| Parameter | Value | Status |
|-----------|-------|--------|
| seed | 42 | UNCHANGED |
| feature_set | EXP_MI_V1_1 | UNCHANGED |
| feature_count | 75 | UNCHANGED |
| monitor split | 90/10, seed=42 | UNCHANGED |
| ae_fit rows | 40,320 | UNCHANGED |
| monitor rows | 4,480 | UNCHANGED |
| scaler | StandardScaler on AE-fit only | UNCHANGED |
| architecture | 75→12→6→12→75 | UNCHANGED |
| activation (hidden) | ReLU | UNCHANGED |
| activation (output) | Linear (none) | UNCHANGED |
| loss | MSELoss | UNCHANGED |
| optimizer | Adam | UNCHANGED |
| learning_rate | 0.001 | UNCHANGED |
| weight_decay | 0.0001 | UNCHANGED |
| batch_size | 256 | UNCHANGED |
| patience | 5 | UNCHANGED |
| threshold candidates | p95, p99, p99.9, mean+2σ, mean+3σ | UNCHANGED |
| primary threshold | DEFERRED TO SPRINT 8 | UNCHANGED |
| **max_epochs** | ~~100~~ → **150** | **REVISED (Decision 4)** |

---

## 3. Decision 4 (Revised) — max_epochs 100 → 150

> **"Decision 4 (Revised): max_epochs raised from 100 to 150, based on the
> EXP_AE_V1 diagnostic showing early stopping at epoch 138 with best_epoch=133
> under the same seed, architecture, monitor split, scaler, and training
> configuration. Rationale: the 100-epoch run reached the maximum epoch while
> monitor MSE was still decreasing; the 300-epoch diagnostic reached its best
> at epoch 133 and triggered patience at epoch 138."**

### Diagnostic Evidence Summary

| Metric | 100-ep run | 300-ep diagnostic | 150-ep official |
|--------|-----------|-------------------|----------------|
| best_epoch | 100 (= max_epochs) | **133** | **133** |
| best_monitor_mse | 0.173667 | 0.171159 | **0.171159** |
| Early stop triggered | NO | YES (ep 138) | YES (ep 138) |
| Monitor drop ep96→100 | 0.00065 (0.37%) | — | — |
| Improvement vs 100-ep | — | −0.002508 (−1.44%) | −0.002508 |

The 300-epoch diagnostic used the identical scaler (loaded from checkpoint), identical
monitor split indices, and identical seed. The official 150-epoch run independently
reproduced the same best_epoch=133 and best_monitor_mse=0.171159, confirming the
diagnostic prediction exactly.

---

## 4. Official Training Results (150-epoch Run)

| Property | Value |
|----------|-------|
| Phase-1 training (138 epochs to early stop) | 111.4 s |
| Phase-2 final refit (133 epochs, 44,800 rows) | 78.2 s |
| best_epoch | **133** |
| final_epoch_count | **133** |
| best_monitor_mse | **0.171159** |
| Early stopping | Fired at epoch 138 (patience=5 after ep133) |
| Total runtime | 197.1 s (~3.3 min) |

---

## 5. Normal-Only AE Training

| Check | Result |
|-------|--------|
| AE trains on label == 0 rows only | VERIFIED |
| Normal TRAIN rows used | 44,800 |
| Attack TRAIN rows used | **0** |
| Normal VALIDATION rows (calibration only) | 11,200 |
| Attack VALIDATION rows used | **0** |
| test_zero_attack_rows_in_ae_training_batch | PASS |
| test_ae_fit_subset_is_normal_only | PASS |
| test_monitor_subset_is_normal_only | PASS |

---

## 6. Zero Attack Rows in AE Training Tensors

> **Canonical leakage invariant**: Zero Attack-labeled rows were supplied
> to `AETrainer.fit()` at any point during training.

Verified by all three leakage test methods + runtime assertion.

---

## 7. Fixed Monitor Split

| Property | Value |
|----------|-------|
| AE-fit count | 40,320 rows |
| Monitor count | 4,480 rows |
| Split seed | 42 |
| Disjoint (ae_fit ∩ monitor = ∅) | VERIFIED |
| Split indices | Identical to the 100-epoch run (same seed=42 determinism) |

The monitor_split_indices.csv was regenerated identically under seed=42.

---

## 8. Scaler Population

| Property | Value |
|----------|-------|
| Scaler type | `sklearn.preprocessing.StandardScaler` |
| Fit population | Normal AE-fit subset: **40,320 rows** |
| NOT fitted on | Attack TRAIN, monitor, VALIDATION, dev test, protected, excluded |
| Feature dimension | 75 (mean_ length = 75, scale_ length = 75) — PASS |

---

## 9. Architecture (Unchanged)

| Layer | In | Out | Activation |
|-------|-----|-----|-----------|
| Encoder FC1 | 75 | 12 | ReLU |
| Encoder FC2 | 12 | 6 | ReLU |
| Decoder FC1 | 6 | 12 | ReLU |
| Decoder FC2 | 12 | 75 | Linear (none) |

- BatchNorm: **NO** — PASS
- Dropout: **NO** — PASS
- Total parameters: **2,049** — PASS

---

## 10. Threshold Calibration

| Property | Value |
|----------|-------|
| Calibration data | Normal VALIDATION: 11,200 rows |
| AE mode during calibration | `model.eval()` + `torch.no_grad()` |
| Weight updates during calibration | NONE |
| Attack rows in calibration | 0 |

---

## 11. Five Threshold Candidates (Official 150-Epoch Results)

All thresholds computed from the **official 150-epoch model** applied to Normal
VALIDATION reconstruction errors (11,200 rows, label==0).

| Threshold Rule | τ value | n_above | FPR on Normal VAL |
|---------------|---------|---------|-------------------|
| **p95** | **0.567386** | 560 | 5.00% |
| **p99** | **1.512164** | 112 | 1.00% |
| **p99.9** | **10.696876** | 12 | 0.11% |
| mean + 2σ | 7.515109 | 23 | 0.21% |
| mean + 3σ | 11.160063 | 7 | 0.06% |

Monotonicity: p95 ≤ p99 ≤ p99.9 — PASS

FPR sanity: p95≈5% ✓ | p99≈1% ✓ | p99.9≈0.1% ✓

### Threshold Caution — mean+2σ and mean+3σ

> [!WARNING]
> **p95/p99/p99.9 are percentile-based thresholds computed from the Normal
> VALIDATION distribution. They are robust to outliers.**
>
> **mean+2σ and mean+3σ are strongly affected by the two extreme high-RE
> Normal VALIDATION rows (row_id 10737, RE≈269.09; row_id 10731, RE≈269.03 —
> see §13). These must be treated as outlier-inflated/cautious alternatives.**
>
> Sanity tail counts are approximate priors only. Actual threshold values and
> counts come from the saved Normal VALIDATION reconstruction-error distribution.

---

## 12. Reconstruction Error Distribution (Normal VAL — Official 150-Epoch Model)

| Statistic | 100-ep run | **150-ep (official)** |
|-----------|-----------|----------------------|
| mean | 0.234215 | **0.225201** |
| std | 3.646701 | **3.644954** |
| min | 0.011123 | **0.009684** |
| max | 269.089355 | **269.161896** |
| p50 | 0.071288 | **0.065888** |
| p95 | 0.585220 | **0.567386** |
| p99 | 1.740880 | **1.512164** |
| p99.9 | 10.725732 | **10.696876** |

The distribution remains right-skewed (median ≈ 0.066, mean ≈ 0.225). Additional
training improved reconstruction quality: p50 dropped 7.6% (0.071 → 0.066) and
p99 dropped 13.1% (1.741 → 1.512).

RE definition: `RE(x) = mean((x − x̂)²)` over 75 features. Mean, not sum — PASS.

---

## 13. Outlier Row Analysis (Corrected)

> [!IMPORTANT]
> **Corrected outlier row IDs**: The top-2 extreme Normal VALIDATION rows are
> **row_id 10737 (RE≈269.09)** and **row_id 10731 (RE≈269.03)**, as confirmed
> by the diagnostic script. An earlier (pre-diagnostic) reference to "row_id 2629"
> was incorrect and has been expunged from all artifacts.

### Structural Pattern of Extreme Rows

| Property | Extreme rows (top-20 by RE) | Bulk (p25–p75 RE) |
|----------|---------------------------|-------------------|
| proto | tcp (20/20) | mixed |
| state | **RST (17), FIN (3)** | mixed |
| service | `-` (14), `ssh` (4), `pop3` (2) | mixed |
| sbytes (median) | 258 | 1,684 |
| dbytes (median) | 86 | 2,393 |
| sload (median) | 14,925 | 395,639 |
| spkts (median) | 6 | 16 |
| dpkts (median) | 2 | 18 |

**Pattern**: All 20 extreme-RE rows are short, aborted TCP sessions (RST/FIN),
with very low byte counts and few packets. They are labeled Normal (attack_cat = Normal,
label = 0) and are not mislabeled. These rows are **not deleted, clipped, or filtered**.

**Top-2 RE contribution**: top-2 rows account for ~20.5% of total sum(RE).

> [!NOTE]
> **Sprint 8 Fusion Note**:
> "The AE's reconstruction error is elevated for short/aborted-connection Normal
> traffic, a structurally distinct sub-population. Sprint 8 fusion logic should
> be aware this may contribute to false positives for legitimately
> anomalous-but-benign connection patterns."

---

## 14. Comparison: 100-Epoch vs 150-Epoch Official Thresholds

| Threshold | 100-ep τ | 150-ep τ | Change |
|-----------|---------|---------|--------|
| p95 | 0.585220 | **0.567386** | −3.1% |
| p99 | 1.740880 | **1.512164** | −13.1% |
| p99.9 | 10.725732 | **10.696876** | −0.3% |
| mean+2σ | 7.527617 | **7.515109** | −0.2% |
| mean+3σ | 11.174318 | **11.160063** | −0.1% |

p95 and p99 thresholds tightened meaningfully with better reconstruction.
p99.9/sigma thresholds are dominated by the 2 extreme outlier rows and changed minimally.

---

## 15. Data Isolation

| Boundary | Status |
|----------|--------|
| development_test.csv not opened | PASS |
| protected_unseen_attack.csv not opened | PASS |
| excluded_train_backdoor.csv not opened | PASS |
| VALIDATION not used for AE weight fitting | PASS |
| VALIDATION used only for threshold calibration | PASS |
| TRAIN hash verified at startup | PASS |
| VALIDATION hash verified | PASS |

---

## 16. Reproducibility

| Mechanism | Value |
|-----------|-------|
| `random.seed` | 42 |
| `numpy.random.seed` | 42 |
| `torch.manual_seed` | 42 |
| `torch.cuda.manual_seed_all` | 42 |
| `cudnn.deterministic` | True |
| `cudnn.benchmark` | False |
| DataLoader generator seed | 42 |
| Monitor split seed | 42 |
| Test: same seed → same RE | PASS |

---

## 17. Mandatory Limitation Statements

### Statement 1 — Scaler-Space / Fusion Limitation

> **"AE operates in a Normal-TRAIN-scaled feature space distinct from the
> full-TRAIN-scaled space used by DT/RF/SVM/NN. Sprint 8 fusion must account
> for this representation difference when combining the AE reconstruction error
> with the supervised branch outputs."**

Present in: `ae_metadata.json` ✓ | `metadata.json` ✓ | `threshold_config.json` ✓

### Statement 2 — Single-Seed Limitation

> **"Sprint 7 uses a single AE training seed (42). No multi-seed stability
> estimate exists for AE reconstruction error or threshold values. This is
> an accepted scope limitation and not a null result."**

Present in: `ae_metadata.json` ✓ | `metadata.json` ✓ | `threshold_config.json` ✓

### Statement 3 — Threshold Sanity Priors

> **"Threshold sanity counts are approximate priors only. Actual threshold
> values and counts are computed from the saved Normal VALIDATION
> reconstruction-error distribution."**

Present in: `threshold_config.json` ✓

### Statement 4 — Primary Threshold Deferred

> **"Primary threshold selection is deferred to Sprint 8."**

`primary_threshold = "DEFERRED_TO_SPRINT_8"` in all threshold artifacts — PASS

---

## 18. Artifacts

### Results (`results/autoencoder/EXP_AE_V1/`)

| File | Status | Notes |
|------|--------|-------|
| `config.yaml` | ✓ | max_epochs=150 |
| `metadata.json` | ✓ | decision_4_revision + outlier_note + threshold_caution |
| `runtime_report.json` | ✓ | best_epoch=133, 197.1s |
| `monitor/monitor_split_indices.csv` | ✓ | 44,800 rows, identical to 100-ep run |
| `monitor/monitor_metadata.json` | ✓ | |
| `training/training_history.csv` | ✓ | 138 epochs logged |
| `training/epoch_diagnostics.json` | ✓ | best_epoch=133 |
| `threshold/validation_reconstruction_errors.csv` | ✓ | 11,200 rows (150-ep model) |
| `threshold/threshold_sweep.csv` | ✓ | 5 rows |
| `threshold/threshold_calibration.json` | ✓ | 5 candidates |

### Checkpoints (`results/checkpoints/EXP_AE_V1/`)

| File | Status | Notes |
|------|--------|-------|
| `ae_final.pt` | ✓ | 150-ep official weights (best_epoch=133) |
| `ae_scaler.joblib` | ✓ | Same as 100-ep (seed deterministic) |
| `ae_architecture.json` | ✓ | |
| `ae_metadata.json` | ✓ | decision_4_revision + outlier_note + threshold_caution |
| `threshold_config.json` | ✓ | |

---

## 19. Test Results

| Test file | Tests | Result |
|-----------|-------|--------|
| `test_ae_architecture.py` | 21 | ✅ 21/21 PASS |
| `test_ae_leakage.py` | 24 | ✅ 24/24 PASS |
| `test_ae_threshold.py` | 31 | ✅ 31/31 PASS |
| **AE-specific total** | **76** | **✅ 76/76** |
| `validate_ae.py` | 78 checks | ✅ 78/78 PASS |
| Full regression suite | 878 | ✅ 878/878 PASS |

---

## 20. Non-Goals (Confirmed Not Performed)

- Sprint 1–6 artifacts: NOT modified ✓
- Sprint 5 base models: NOT retrained ✓
- Sprint 6 stacking/meta-learner: NOT rerun ✓
- 2×2 fusion: NOT performed (Sprint 8) ✓
- Outlier rows removed/clipped: NOT done ✓
- Primary threshold selected: NOT done (deferred Sprint 8) ✓
- Freeze commit / tag: NOT created (awaiting human approval) ✓
- 300-epoch diagnostic saved as official artifact: NOT done ✓

---

## Overall Assessment

```
STATUS:               READY_TO_FREEZE
Validation checks:    78/78 PASS
Regression tests:     878/878 PASS
AE unit tests:        76/76 PASS

Decision 4 (Revised): max_epochs 100 → 150 (approved)
Official best_epoch:  133 (early stop ep 138, patience=5)
Diagnostic confirmed: 300-ep run converged at same ep133/0.171159

RE p50 (typical row): 0.066  — good reconstruction
RE p99:               1.512  — 13% tighter than 100-ep run
Extreme outliers:     row_id 10737 (RE~269), row_id 10731 (RE~269)
                      Short/aborted TCP sessions (RST/FIN), label=Normal
                      NOT mislabeled. Sprint 8 note documented.

mean+2sigma/mean+3sigma: outlier-inflated, treat as cautious alternatives
p95/p99/p99.9:           robust percentile thresholds, recommended for Sprint 8

Primary threshold:    DEFERRED TO SPRINT 8

Limitations:
  1. AE scaling space differs from supervised models (fusion note required)
  2. Single seed = 42 (no multi-seed stability estimate)
  3. Threshold primary selection deferred to Sprint 8
```
