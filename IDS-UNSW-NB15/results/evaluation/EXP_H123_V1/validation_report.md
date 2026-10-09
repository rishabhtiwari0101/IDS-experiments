# Sprint 9 Validation Report — Final (Determinism + Provenance Closure)
**Experiment**: EXP_H123_V1
**Phase**: VALIDATION (Final — Determinism Closed)
**Correction Pass**: 2026-09-03

---

## 1. Validation Scope
**Status**: PASS

This report independently validates the Sprint 9 implementation and generated artifacts against `docs/sprint9_final_design.md` and locked DD-1 through DD-8 decisions. Validation is read-only on artifacts, cryptographic hashes, mathematical consistency, protocol isolation, and implementation code inspection. No frozen Sprint 1–8 artifacts were modified.

---

## 2. Upstream Integrity Result
**Status**: PASS

All 12 checkpoint SHA-256 hashes verified against `metadata.json checkpoint_sha256`.

| Set | Count | Status |
|-----|-------|--------|
| EXP_BASE_MODELS_V1 (6 files) | 6 | PASS |
| EXP_OOF_STACK_V1 (3 seeds) | 3 | PASS |
| EXP_AE_V1 (3 files) | 3 | PASS |
| **Total** | **12** | **PASS** |

---

## 3. Dataset Integrity Result
**Status**: PASS

All four dataset SHA-256 hashes verified. Canonical field name `protected_backdoor` confirmed in all artifacts.

| Dataset key | Status |
|-------------|--------|
| train | PASS |
| validation | PASS |
| development_test | PASS |
| protected_backdoor | PASS |

---

## 4. Feature Integrity Result
**Status**: PASS

- `feature_set = EXP_MI_V1_1` — confirmed in `config.yaml`
- `n_features = 75` — confirmed in `config.yaml` and runtime assertion
- Exact feature identity and ordering verified via `EXP_MI_V1_1/selected_features.json`

---

## 5. H1 Validation Result
**Status**: PASS

### 5.1 H1 Boundary Correction (Applied)

The implementation in `scripts/evaluate_sprint9.py` previously contained a defect:
```python
# DEFECTIVE (pre-correction):
elif diff < 0:
    h1_verdict = "NOT_SUPPORTED"
```

Corrected to implement the locked DD-7 rule exactly:
```python
# CORRECTED:
elif diff < -config["h1_epsilon"]:  # DD-7 LOCKED: NOT_SUPPORTED requires diff < -epsilon
    h1_verdict = "NOT_SUPPORTED"
```

The defect zone was `diff ∈ (-0.005, 0)`. The actual diff ≈ 0.01222799051528034 is outside this zone. The stored SUPPORTED verdict is correct and was not changed.

### 5.2 Locked Three-Way H1 Verdict Rule (DD-7)

```
diff = stacking_mean_macro_f1 - rf_dev_test_macro_f1

if diff > epsilon:      → SUPPORTED
elif diff < -epsilon:   → NOT_SUPPORTED
else:                   → INCONCLUSIVE

epsilon = 0.005 (LOCKED)
```

### 5.3 H1 Numerical Results (unchanged)

| Field | Stored Value | Determinism Rerun | Match |
|-------|-------------|-------------------|-------|
| seed_42 Macro-F1 | 0.8926091690431182 | 0.8926091690431182 | **exact** |
| seed_123 Macro-F1 | 0.8926186397931948 | 0.8926186397931948 | **exact** |
| seed_2024 Macro-F1 | 0.8936559437082856 | 0.8936559437082856 | **exact** |
| stacking_mean_macro_f1 | 0.8929612508481996 | 0.8929612508481996 | **exact** |
| stacking_std_macro_f1 (ddof=0) | 0.0004912372482943444 | 0.0004912372482943444 | **exact** |
| rf_dev_test_macro_f1 | 0.8807332603329192 | 0.8807332603329192 | **exact** |
| diff | 0.01222799051528034 | 0.01222799051528034 | **exact** |
| h1_verdict | SUPPORTED | SUPPORTED | **exact** |

### 5.4 H1 Standard Deviation (ddof Corrected)

The implementation uses `np.std(stacking_macro_f1s)` = **ddof=0 (population standard deviation)**.

| ddof | Value |
|------|-------|
| ddof=0 (population, numpy default) — **stored implementation** | **0.0004912372482943444** |
| ddof=1 (sample, alternative — not stored) | 0.000601640300485015 |

> **stacking_std_macro_f1 is reported for transparency only and does not participate in the locked H1 verdict function.**

---

## 6. H2 Validation Result
**Status**: PASS

- AE-only branch used exclusively; no C06 OR-fusion output used
- tau = 11.160062745213509 (matches frozen `threshold_calibration.json`)
- ae_val_flagged = 7 (T-AE-VAL-FPR-CONSISTENCY PASS, determinism rerun confirms)
- ae_val_fpr_recomputed = 7/11200 = 0.000625
- supported_threshold = 2 (literal locked value, DD-4)
- ae_detected_count = 0 → **H2 = NOT_SUPPORTED**

---

## 7. H3 Validation Result
**Status**: PASS

H3 is a re-presentation of frozen Sprint 8 evidence. No new inference was run.

- C01 detected = 582 / 583; C06 detected = 582 / 583
- fpr_delta = 0.000351 (0.0351 pp; within 2 pp fpr_cap)
- `c06_detected <= c01_detected` → **H3 = NOT_SUPPORTED**

---

## 8. T-DETERMINISTIC — Empirically Verified
**Status**: PASS (empirically verified)

A complete second evaluation run was performed using the corrected implementation at `scripts/run_determinism_check.py`, writing exclusively to `results/evaluation/EXP_H123_V1/determinism_check/`. The original artifacts were not overwritten.

**Second run inputs**: identical frozen checkpoints, identical datasets, identical config, identical seeds, identical preprocessing.

**Field-by-field comparison result (17 fields):**

| Field | Original | Rerun | Diff | Status |
|-------|----------|-------|------|--------|
| h1.stacking_macro_f1_seed_42 | 0.892609169… | identical | 0.0 | PASS |
| h1.stacking_macro_f1_seed_123 | 0.892618639… | identical | 0.0 | PASS |
| h1.stacking_macro_f1_seed_2024 | 0.893655943… | identical | 0.0 | PASS |
| h1.stacking_mean_macro_f1 | 0.892961250… | identical | 0.0 | PASS |
| h1.stacking_std_macro_f1 | 0.000491237… | identical | 0.0 | PASS |
| h1.rf_dev_test_macro_f1 | 0.880733260… | identical | 0.0 | PASS |
| h1.diff | 0.012227990… | identical | 0.0 | PASS |
| h1.h1_verdict | SUPPORTED | SUPPORTED | — | PASS |
| h1.epsilon | 0.005 | 0.005 | 0.0 | PASS |
| h2.ae_detected_count | 0 | 0 | — | PASS |
| h2.tau | 11.160062… | identical | 0.0 | PASS |
| h2.ae_val_fpr_recomputed | 0.000625 | 0.000625 | 0.0 | PASS |
| h2.h2_verdict | NOT_SUPPORTED | NOT_SUPPORTED | — | PASS |
| h3.c01_detected | 582 | 582 | — | PASS |
| h3.c06_detected | 582 | 582 | — | PASS |
| h3.fpr_delta | 0.000351 | 0.000351 | 0.0 | PASS |
| h3.h3_verdict | NOT_SUPPORTED | NOT_SUPPORTED | — | PASS |

**T-DETERMINISTIC = PASS (17/17 fields — all floating-point differences exactly zero)**

Artifacts: `results/evaluation/EXP_H123_V1/determinism_check/`

---

## 9. Provenance Split Disclosure

The original Sprint 9 result artifacts in `EXP_H123_V1/` were generated by the pre-correction implementation of `evaluate_sprint9.py`. A non-verdict-affecting H1 boundary defect (`elif diff < 0` instead of `elif diff < -epsilon`) was subsequently corrected. The observed diff (0.01222799051528034) lies outside the affected interval (-0.005, 0); the stored H1 verdict SUPPORTED is unchanged.

The subsequent deterministic verification run used the corrected implementation solely to verify reproducibility. This provenance is explicitly recorded in `metadata.json` under `provenance_note`.

---

## 10. Provenance Result
**Status**: PASS

- All 12 per-checkpoint provenance files present
- `metadata.json` all §11 required fields complete, no null values
- No placeholder hashes
- Provenance split disclosure added to `metadata.json`

---

## 11. Isolation Result
**Status**: PASS

- Protected Backdoor: 0 rows in TRAIN, 0 in VALIDATION
- `config.yaml` mtime precedes `dev_test_access` timestamp
- No threshold recalibrated; tau loaded from frozen artifact
- No fusion rule changed; H3 uses read-only frozen Sprint 8 evidence

---

## 12. Acceptance Criteria Result
**Status**: PASS

All criteria from §19 verified. See §14 static locked-value check below.

---

## 13. Final Design Approval Event

**Finding**: The human project owner provided an explicit, distinct approval of the Final Design document on **2026-09-03T20:59:24+05:30**:

> *"I explicitly approve docs/sprint9_final_design.md as the Final Design for Sprint 9."*

This approval is recorded in `docs/sprint9_final_design.md §21` (Final Design Approval Record).

Approval events are now fully distinct and separately recorded:

1. **Discussion / DD approval** — DD-1 through DD-8 approved 2026-09-02 (`docs/sprint9_discussion_v1.md §M/§N`)
2. **Final Design document approval** — 2026-09-03T20:59:24+05:30 (`docs/sprint9_final_design.md §21`)
3. **Freeze approval** — NOT YET OBTAINED (requires separate explicit "proceed to freeze" command)

The accurate lifecycle state is now:

```
FINAL DESIGN:   APPROVED — 2026-09-03
```

---

## 14. Individual Sprint 9 Test Results (§13 of Final Design)

| # | Test ID | Status | Evidence Source | Explanation |
|---|---------|--------|-----------------|-------------|
| 1 | T-CRITERION-PREREGISTERED | **PASS** | `runtime_report.json` vs `config.yaml` mtime | config.yaml written before dev_test_access |
| 2 | T-NO-RESULT-BACKWARD | **PASS** | `config.yaml` mtime < `runtime_report.json` end | config not modified after evaluation |
| 3 | T-FROZEN-UPSTREAM | **PASS** | 12 provenance JSON files; hashes match `metadata.json` | All 12 hashes verified at STEP 1 |
| 4 | T-NO-RETRAIN | **PASS** | Code inspection `evaluate_sprint9.py` | No `.fit()` on any model |
| 5 | T-75-FEATURES | **PASS** | `config.yaml` n_features=75; `selected_features.json` count=75 | Exact 75 EXP_MI_V1_1 features |
| 6 | T-SEED-SET | **PASS** | `config.yaml` h1_seeds=[42,123,2024] | Exact seed set, no others |
| 7 | T-TAU-PROVENANCE | **PASS** | `h2_results.json` tau=11.160062745213509 matches `threshold_calibration.json` | Exact match to frozen EXP_AE_V1 |
| 8 | T-H2-AE-ONLY | **PASS** | `h2_results.json` no C06 field; code uses `prot_re > tau` directly | AE reconstruction error only |
| 9 | T-H3-NO-RESELECT | **PASS** | `h3_results.json` c01=582, c06=582; matches EXP_FUSION_V1 frozen record | Read-only frozen evidence |
| 10 | T-PROT-ISOLATION | **PASS** | Backdoor accessed only after AE_VAL_FPR check; 0 rows in TRAIN/VALIDATION | Protected isolation maintained |
| 11 | T-DEV-TEST-ISOLATION | **PASS** | `runtime_report.json` dev_test_access > config.yaml mtime | Dev TEST not accessed before criteria locked |
| 12 | T-HASH-CONSISTENCY | **PASS** | `metadata.json` 4 dataset_sha256 fields; `protected_backdoor` canonical field confirmed | No mismatch |
| 13 | T-DETERMINISTIC | **PASS** | `determinism_check/comparison.json`: 17/17 fields, all float diffs = 0.0 | Empirically verified; second run with corrected implementation |
| 14 | T-PROVENANCE-COMPLETE | **PASS** | `metadata.json` all required §11 fields; no null values | All fields complete |
| 15 | T-AE-VAL-FPR-CONSISTENCY | **PASS** | `h2_results.json` ae_val_fpr_recomputed=0.000625=7/11200; confirmed by determinism rerun | Exact match; no HALT triggered |
| 16 | T-RF-PREDICTION-REUSE | **PASS** | Code inspection; determinism rerun uses `rf_preds` for baseline and `rf_prob` for meta-feature column, computed once | Single inference pass; same data path |

**Result: 16/16 PASS | 0 FAIL | 0 INCONCLUSIVE**

---

## 15. Static Locked-Value Check
**Status**: PASS

| Parameter | Locked Value | Verified |
|-----------|-------------|---------|
| epsilon | 0.005 | PASS |
| tau | 11.160062745213509 | PASS |
| supported_threshold | 2 | PASS |
| multiplier | 3 | PASS |
| fpr_cap | 0.02 | PASS |
| seeds | [42, 123, 2024] | PASS |
| n_features | 75 | PASS |
| n_validation | 11200 | PASS |
| n_dev_test | 81749 | PASS |
| n_prot | 583 | PASS |

DD-1 through DD-8: **all confirmed unchanged**.
H1/H2/H3 numerical results: **all unchanged**.
Dataset SHA-256 (4): **all unchanged**.
Checkpoint SHA-256 (12): **all unchanged**.
Feature set: **EXP_MI_V1_1, 75 features, unchanged**.

---

## 16. Final Validation Verdict

**Status**: PASS — ALL 16 TESTS PASS

16/16 required tests PASS. T-DETERMINISTIC is empirically verified via a complete second evaluation run. All stored H1/H2/H3 verdicts and numerical values are confirmed correct and unchanged. The H1 boundary code defect is corrected. The H1 std ddof is correctly labeled as ddof=0 (population). Provenance split is explicitly documented. Final Design explicitly approved by human project owner 2026-09-03T20:59:24+05:30 (recorded in `docs/sprint9_final_design.md §21`).

**Sprint 9 is ready for freeze pending only explicit human approval of "proceed to freeze."**

---

## Appendix — Files Created / Modified

| File | Change |
|------|--------|
| `scripts/evaluate_sprint9.py` | H1 boundary corrected: `diff < 0` → `diff < -epsilon` |
| `scripts/run_determinism_check.py` | New: determinism verification script |
| `tests/test_h1_verdict_boundary.py` | New: 9-case focused H1 boundary unit test |
| `results/evaluation/EXP_H123_V1/determinism_check/` | New directory with rerun artifacts and comparison |
| `results/evaluation/EXP_H123_V1/metadata.json` | Added `provenance_note` and `h1_std_ddof_note` |
| `results/evaluation/EXP_H123_V1/validation_report.md` | This document |
| `results/evaluation/EXP_H123_V1/validation_summary.json` | Updated to reflect 16/16 PASS and Final Design approval |
| `docs/sprint9_final_design.md` | Added §21 (Approval Record); updated lifecycle in §1 and §20 |
