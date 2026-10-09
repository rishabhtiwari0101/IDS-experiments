# EXP_OOF_STACK_V1 — Sprint 6 Quality Review
## OOF Stacking + Logistic Regression Meta-Learner

```
Status:        READY_TO_FREEZE
Date:          2026-09-02
Experiment:    EXP_OOF_STACK_V1
Dataset:       UNSW-NB15
Sprint:        6 — OOF Stacking + LR Meta-Learner
Validation:    PASS  65/65 checks
Regression:    PASS  802/802 tests
```

---

## 1. H1 Seed Results

All three H1 seeds completed successfully on 2026-09-01.
Evaluation is **IN-SAMPLE** at the meta-learner level (see §5 Limitations).

| Seed | Macro-F1 | Weighted-F1 | Balanced Acc | OOF Runtime |
|------|----------|-------------|--------------|-------------|
| 42   | 0.946958 | 0.957246    | 0.954778     | 679.2 s     |
| 123  | 0.947290 | 0.957514    | 0.955103     | 628.9 s     |
| 2024 | 0.947476 | 0.957666    | 0.955264     | 683.8 s     |

**H1 Summary (3-seed mean ± std, ddof=1):**

```
mean Macro-F1 =  0.947242
std  Macro-F1 =  0.000263
```

Seed-to-seed variance is extremely low (CV ≈ 0.028 %), indicating high
numerical stability of the stacking pipeline across different random seeds.

---

## 2. Sprint 5 Reference Comparison

| Metric | Value | Label |
|--------|-------|-------|
| Sprint 5 RF CV Macro-F1 | **0.9508532** | Frozen Sprint 5 single-CV reference; not a matched 3-seed H1 baseline. |
| H1 Stacking mean Macro-F1 | **0.947242** | 3-seed H1 OOF mean (IN-SAMPLE meta evaluation) |
| Delta | **−0.003611** | Stacking below RF reference |

### Interpretation

**The Sprint 5 RF reference (0.9508532) and the H1 stacking mean (0.947242)
are NOT statistically matched quantities and MUST NOT be treated as such.**

Reasons they are not directly comparable:

1. **Different evaluation protocols**: The Sprint 5 RF reference is a single
   5-fold stratified CV score on the full TRAIN, evaluating the RF model
   alone. The H1 stacking mean is an in-sample evaluation of the meta-learner
   on the OOF matrix used to train it.

2. **In-sample meta-learner bias**: The meta-learner is evaluated on the same
   OOF predictions it was fitted on. No separate meta-learner holdout exists.
   This inflates apparent meta-learner performance relative to a true holdout.

3. **No statistical significance test is performed**: With only three seeds and
   mismatched evaluation protocols, any p-value would be meaningless. No
   significance test is claimed or implied.

**Conclusion: Stacking does NOT currently demonstrate improvement over the
Sprint 5 RF baseline under a rigorous matched comparison.** The delta of
−0.003611 is directionally negative, but the comparison is methodologically
unmatched and cannot support a strong directional claim in either direction.
True held-out evaluation on the development test set is deferred to a later
sprint.

---

## 3. OOF Protocol Verification

### 3.1 OOF Coverage

| Check | Result |
|-------|--------|
| Rows per seed | **162,395 / 162,395** (exact TRAIN size) |
| NaN in any meta-feature | 0 |
| Duplicate row_ids | 0 |
| OOF completeness | **PASS** — every TRAIN row has exactly one prediction |

### 3.2 Fold Protocol

| Parameter | Value |
|-----------|-------|
| Fold method | `StratifiedKFold` |
| n_splits | 5 |
| shuffle | True |
| random_state | **7** (OOF seed, fixed, independent of H1 seed) |
| Folds created | ONCE, reused identically for all 3 H1 seeds |
| Fold assignments bit-identical across seeds 42/123/2024 | **PASS** |
| Fold assignments match recomputed StratifiedKFold | **PASS** |

### 3.3 No-Self-Prediction

> **PASS** — zero self-prediction leakage across all 5 folds × 3 seeds.

For every fold, the held-out OOF indices are strictly disjoint from the
training indices used to fit the base models in that fold. No model ever
predicts a sample it was trained on.

---

## 4. Model Contracts

### 4.1 Meta-Feature Input

The meta-learner receives exactly four meta-features:

```
dt_attack_probability    — DT predict_proba()[:, 1]        range: [0, 1]
rf_attack_probability    — RF predict_proba()[:, 1]        range: [0, 1]
svm_decision_score       — LinearSVC decision_function()   range: unbounded real
nn_attack_probability    — IDSNet sigmoid(logit)            range: [0, 1]
```

`row_id` is present in `oof_predictions.csv` for provenance only and is
**excluded** from the meta-learner input (`row_id_excluded=True` in all
checkpoint metadata). All 3 meta-learner checkpoints verified:
`n_features_in_=4`.

### 4.2 Base-Model OOF Output Types

| Model | Column | Type | Validation |
|-------|--------|------|-----------|
| DT | `dt_attack_probability` | Probability [0, 1] | PASS — all values in [0, 1] |
| RF | `rf_attack_probability` | Probability [0, 1] | PASS — all values in [0, 1] |
| SVM | `svm_decision_score` | Decision function (unbounded) | PASS — column name confirms decision_function, not predict_proba |
| NN | `nn_attack_probability` | Probability [0, 1] via sigmoid | PASS — all values in [0, 1] |

### 4.3 NN OOF Training Configuration

| Parameter | Value | Source |
|-----------|-------|--------|
| `oof_fixed_epoch_count` | **18** | Frozen in `oof_runner.OOF_FIXED_EPOCH_COUNT` |
| Early stopping | None | Not used in OOF loop |
| OOF fold used as validation | No | OOF held-out fold is never seen during NN training |
| `oof_pos_weight` | **0.38096857859602873** | `44800 / 117595` (full-TRAIN constant) |
| Per-fold pos_weight recalculation | No | Full-TRAIN constant used across all folds |

### 4.4 Meta-Learner Configuration (Frozen)

```python
LogisticRegression(
    solver       = 'lbfgs',
    C            = 1.0,
    class_weight = 'balanced',
    max_iter     = 1000,
    random_state = <H1 seed>,   # 42 / 123 / 2024
)
```

No hyperparameter search was performed on the meta-learner. Configuration
is frozen from the Sprint 6 design decision.

---

## 5. Limitations (Mandatory)

### 5.1 Meta-Learner In-Sample Evaluation

> **H1 Macro-F1 is computed by evaluating the meta-learner on the same OOF
> matrix used to train it. No separate meta-learner holdout exists under the
> current data-isolation rules. This is in-sample evaluation at the
> meta-learner level and is NOT a fully held-out end-to-end generalisation
> estimate.**

This limitation is recorded in:
- Every `seed_*/metadata.json`
- Every `seed_*/metrics.json`
- `h1_summary.json`

### 5.2 Full-TRAIN SVM/NN Scaling

> **SVM/NN OOF predictions use scaling statistics computed on the full frozen
> TRAIN, including rows in the OOF held-out fold. This is a bounded,
> label-independent leakage channel accepted for feature-space consistency.**

The frozen Sprint 5 scalers (`svm_scaler.joblib`, `nn_scaler.joblib`) were
fitted on the entire TRAIN split. Using them inside the OOF loop means that
held-out OOF rows contribute to the scaling mean and variance. This is:
- **bounded**: the contribution of each row is O(1/N)
- **label-independent**: scaling statistics are computed without reference
  to the target label
- **accepted**: per the Sprint 6 design decision for feature-space consistency
  with the Sprint 5 single-model evaluation protocol

This limitation is recorded in all required artifacts (see §5.1).

---

## 6. Data Isolation

### 6.1 Dataset Access During Sprint 6

| Split | SHA-256 (first 16) | Sprint 6 Access |
|-------|--------------------|-----------------|
| `train.csv` | `4a259324e604f013...` | **ALLOWED** — read for OOF |
| `validation.csv` | `13caf21a076a33f5...` | **FORBIDDEN** — not accessed |
| `development_test.csv` | `04725e85732ab2fc...` | **FORBIDDEN** — not accessed |
| `protected_unseen_attack.csv` | `6ffd23479b575e43...` | **FORBIDDEN** — not accessed |
| `excluded_train_backdoor.csv` | `b3f6e7e60c9815a5...` | **FORBIDDEN** — not accessed |

All 5 dataset SHA-256 hashes verified on disk against Step 0 resolved values:
**PASS — all 5 match.**

TRAIN hash verified at runtime startup for every H1 seed run.

### 6.2 Sprint 5 Checkpoints Reused (Not Retrained)

The following Sprint 5 artifacts were **loaded from disk** in each H1 seed
run and were NOT refitted or modified:

| Checkpoint | Path |
|------------|------|
| `dt_final.joblib` | `results/checkpoints/EXP_BASE_MODELS_V1/dt/` |
| `rf_final.joblib` | `results/checkpoints/EXP_BASE_MODELS_V1/rf/` |
| `svm_final.joblib` | `results/checkpoints/EXP_BASE_MODELS_V1/svm/` |
| `nn_final.pt` | `results/checkpoints/EXP_BASE_MODELS_V1/nn/` |
| `svm_scaler.joblib` | `results/checkpoints/EXP_BASE_MODELS_V1/svm/` |
| `nn_scaler.joblib` | `results/checkpoints/EXP_BASE_MODELS_V1/nn/` |

Validation confirmed all Sprint 5 checkpoint directories and model files
exist: **PASS**.

---

## 7. Validation Results

### 7.1 Technical Validation (`validate_oof_stacking.py`)

```
Overall:            PASS
Total checks:       65
Passed:             65
Failed:             0
-------------------------------------------
  [OK  ] Artifact integrity        14/14
  [OK  ] Data isolation             9/9
  [OK  ] OOF coverage              30/30
  [OK  ] Self-prediction            3/3
  [OK  ] Fold protocol              8/8
  [OK  ] Model contracts           22/22
  [OK  ] Limitation texts           7/7
  [OK  ] H1 aggregation             5/5
```

Report saved: `results/stacking/EXP_OOF_STACK_V1/validation_report.json`

### 7.2 Full Regression Suite

```
802 passed in 32.17s   (all tests across full project test suite)
```

Includes:
- 111 Sprint 6 tests (`test_oof_runner.py`, `test_oof_stacking_leakage.py`,
  `test_meta_learner.py`)
- 691 earlier sprint tests (Sprints 1–5, unchanged)

---

## 8. Artifact Inventory and Provenance

### 8.1 OOF Run Artifacts

```
results/stacking/EXP_OOF_STACK_V1/
├── h1_summary.json               ← 3-seed aggregation, mean/std, limitation texts
├── runtime_report.json           ← benchmark timing
├── validation_report.json        ← 65/65 PASS  ← THIS DOCUMENT's source
├── quality_review.md             ← THIS DOCUMENT
├── seed_42/
│   ├── oof_predictions.csv       (162395 × 6: row_id + 4 meta-features + label)
│   ├── fold_assignments.csv      (162395 × 2: row_id + fold_idx)
│   ├── metrics.json              (macro_f1, limitation texts, meta_config)
│   └── metadata.json             (full provenance: SHA, epochs, pos_weight, ...)
├── seed_123/                     (same structure)
└── seed_2024/                    (same structure)
```

### 8.2 Meta-Learner Checkpoints

```
results/checkpoints/EXP_OOF_STACK_V1/
├── seed_42/
│   ├── meta_learner.joblib       (LogisticRegression, random_state=42)
│   └── metadata.json             (row_id_excluded=True, meta_feature_cols, ...)
├── seed_123/                     (same structure)
└── seed_2024/                    (same structure)
```

All 3 meta-learner checkpoints load successfully and produce valid predictions
with `n_features_in_=4`: **PASS**.

### 8.3 Source Code Committed

Git commit: `0443d6d` (Sprint 6 commit on branch `main`)

```
10 files changed, 2967 insertions(+)
  src/models/stacking/__init__.py
  src/models/stacking/oof_runner.py
  src/models/stacking/meta_learner.py
  src/models/stacking/artifacts.py
  scripts/run_oof_stacking.py
  scripts/run_oof_stacking_benchmark.py
  scripts/run_oof_h1_summary.py
  tests/test_oof_runner.py
  tests/test_oof_stacking_leakage.py
  tests/test_meta_learner.py
```

`validate_oof_stacking.py` is not committed (untracked, like `pyrightconfig.json`).

### 8.4 Feature Set

| Field | Value |
|-------|-------|
| `feature_set` | `EXP_MI_V1_1` |
| `feature_count` | `75` |
| Source | `results/feature_selection/EXP_MI_V1_1/selected_features.json` |
| Verified on disk | PASS — 75 features, `experiment_id=EXP_MI_V1_1` |

---

## 9. Runtime and Reproducibility

### 9.1 Runtime

| Phase | Duration |
|-------|----------|
| Benchmark (10k × 2-fold × 1 seed, GPU) | 7.8 s |
| Seed 42 full OOF (162k × 5-fold) | 679.2 s (~11.3 min) |
| Seed 123 full OOF | 628.9 s (~10.5 min) |
| Seed 2024 full OOF | 683.8 s (~11.4 min) |
| **Total H1 wall time** | **~33.2 min** |
| Meta-learner training (per seed) | < 0.3 s |

Hardware: NVIDIA GeForce RTX 3050 Laptop GPU, CUDA 11.8, PyTorch 2.7.1+cu118

### 9.2 Reproducibility

| Seed mechanism | Status |
|----------------|--------|
| Python `random.seed(S)` | Set before each fold |
| `numpy.random.seed(S)` | Set before each fold |
| `torch.manual_seed(S)` | Set before each fold |
| `torch.cuda.manual_seed_all(S)` | Set before each fold |
| CUDA determinism (`cudnn.deterministic=True`) | Enabled |
| OOF fold seed (`seed=7`) | Fixed, independent of H1 seed |
| Fold assignments bit-identical across seeds | PASS (verified) |

Rerunning any individual seed with the same H1 seed value will reproduce
the same OOF predictions (subject to CUDA determinism guarantees on the
same hardware).

---

## 10. Two Reporting Units Statement

> Two reporting units are used: **(a)** three-seed H1 stacking mean ± std
> (0.947242 ± 0.000263, IN-SAMPLE OOF meta evaluation); **(b)** frozen
> Sprint 5 single-CV base-model reference RF Macro-F1 = 0.9508532 (Frozen
> Sprint 5 single-CV reference; not a matched 3-seed H1 baseline). These
> are not statistically matched quantities.

---

## 11. Quality Gate Criteria

| Criterion | Requirement | Status |
|-----------|-------------|--------|
| All H1 seeds completed | 3/3 seeds with full artifacts | **PASS** |
| OOF coverage | 162,395 rows, 0 NaN, 0 duplicate | **PASS** |
| No-self-prediction | Zero leakage across all folds/seeds | **PASS** |
| Fold identity across seeds | Bit-identical | **PASS** |
| Data isolation | Forbidden splits not used | **PASS** |
| Sprint 5 checkpoints reused | Not retrained | **PASS** |
| Both limitation texts present everywhere | 7/7 artifacts | **PASS** |
| Sprint 5 RF label correct | Exact frozen label | **PASS** |
| No statistical significance claims | None found | **PASS** |
| Full regression suite | 802/802 | **PASS** |
| Technical validation | 65/65 | **PASS** |
| h1_summary.json mean/std correct | Verified | **PASS** |
| All meta-learner checkpoints loadable | 3/3 | **PASS** |
| validation_report.json generated | Exists | **PASS** |

---

## 12. Final Status

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   EXP_OOF_STACK_V1   QUALITY REVIEW STATUS              │
│                                                         │
│   READY_TO_FREEZE                                       │
│                                                         │
│   H1 Macro-F1:   0.947242 +/- 0.000263  (IN-SAMPLE)    │
│   Sprint 5 RF:   0.9508532              (reference)     │
│   Stacking vs RF: -0.003611  (NOT a matched comparison) │
│   Validation:    65/65 PASS                             │
│   Regression:    802/802 PASS                           │
│                                                         │
│   All quality gates met.                                │
│   Awaiting freeze commit and EXP_OOF_STACK_V1 tag.      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

All evidence reviewed in this document supports the `READY_TO_FREEZE` status.
No freeze commit or tag has been created. This step is deferred to the
explicit freeze instruction.
