# Quality Review — EXP_FUSION_V1 (Sprint 8)

**Experiment ID**: EXP_FUSION_V1
**Sprint**: 8
**Status**: IMPLEMENTED — AWAITING FREEZE APPROVAL
**Date**: 2026-09-02

---

## Primary Hypotheses

### H-FUSION

> The selected fusion configuration (C06 — OR + mean+3sigma) achieves higher
> Development TEST Macro-F1 than C01 (Supervised-only baseline) without
> exceeding the 5% Normal-VALIDATION FPR gate.

**Verdict: H-FUSION = FALSE**

| Metric | C06 (Selected) | C01 (Baseline) | Direction |
|--------|---------------|----------------|-----------|
| Dev TEST Macro-F1 | 0.892440 | 0.892609 | C01 wins by 0.000169 |
| Dev TEST Recall | 0.967753 | 0.967753 | Equal |
| Dev TEST FPR | 0.192243 | 0.191892 | C01 lower by 0.000351 |
| Validation FPR | 0.047500 | 0.047054 | C01 lower (both pass gate) |
| Protected Backdoor | 582/583 | 582/583 | Equal |

**Primary Conclusion**: The selected C06 operating point did not improve over
the C01 supervised-only baseline. C06 added 0 additional true-positive
detections versus C01. C06 Macro-F1 was marginally lower than C01. C06
therefore produces H-FUSION = FALSE.

> [!NOTE]
> **Scope of conclusion**: This finding is limited to the C06 operating
> point (OR + mean+3sigma, τ = 11.160). It does not imply that the AE branch
> has no possible utility at other operating points. At this threshold, the AE
> component is nearly inert (see §C06 Near-Null Interpretation). Exploratory
> results (informational only) at more aggressive thresholds are documented
> separately below.

### H-PROT-BACKDOOR

> The selected fusion configuration (C06) detects a higher proportion of
> Protected Backdoor rows than C01.

**Verdict: H-PROT-BACKDOOR = FALSE**

| | C06 | C01 |
|-|-----|-----|
| Detected | 582/583 | 582/583 |
| Detection Rate | 99.83% | 99.83% |
| Difference | 0 rows | — |

> [!CAUTION]
> OD-7 mandatory caveat: **1 row = 1/583 = 0.1716 percentage points.** Small
> differences of 0–1 rows must not be over-interpreted as strong
> generalisation evidence. Both configurations detect the same 582 rows; the
> single missed row is identical for C06 and C01.

---

## Primary Quality Statement

> **PRIMARY CONCLUSION**: "The selected C06 operating point did not improve
> over the C01 supervised-only baseline."
>
> **Exploratory observation** (informational only, no backward influence):
> "Exploratory all-11 results indicate that more aggressive OR thresholds
> (C02/C03) produced slightly higher attack recall, but with materially higher
> false-positive rates and lower Macro-F1. These observations are informational
> only and do not alter the primary frozen result."

---

## Selection Provenance (Canonical — DO NOT MODIFY)

| Field | Value |
|-------|-------|
| Selection method | OD-4 Option A + OD-4b conservative-first |
| FPR gate | 5% |
| Passing configs | 9 / 11 |
| Rule priority applied | OR |
| Within-rule priority applied | Conservative-first (largest τ) |
| **Selected config** | **C06** |
| Rule | Supervised OR AE |
| Threshold | mean+3sigma |
| τ value | 11.160062745213509 |
| Validation FPR | 0.047500 (4.75%) |
| Outlier-influenced | **YES** |
| Fallback triggered | No |
| Only baseline passed | No |

> [!WARNING]
> **C06 is outlier_influenced = TRUE.** The mean+3sigma threshold
> (τ = 11.160) is influenced by the two extreme Normal validation rows
> (row_id 10737, RE≈269.09; row_id 10731, RE≈269.03).
> These are legitimate RST/FIN TCP structural artefacts, NOT removed.
> Because of these outliers σ is very large, so τ_mean+3sigma > τ_p99.9.
> This means C06 effectively has a higher threshold than p99.9, allowing
> fewer AE alerts overall.

---

## C06 Near-Null Interpretation

At the selected mean+3sigma threshold (τ = 11.160), the AE component is
**nearly inert**: the OR rule only fires on rows whose reconstruction error
exceeds 11.160. In the Development TEST split, this adds exactly 13
additional false-positive alerts (7113 vs C01's 7100) and 0 additional
true-positive detections. This explains why C06 produces almost identical
predictions to C01.

This near-null result was anticipated in the Final Design (§12 / OD-4b
rationale). It does **not** support the conclusion that the AE branch has
no possible utility. The exploratory results (below) show that more
aggressive OR thresholds (C02, C03) produced measurably higher attack
recall, albeit at higher FPR cost.

---

## Validation FPR — All 11 Configurations

| Config | Rule | Threshold | τ | Val FPR | Gate | Sub FPR (RST/FIN) | delta_vs_C01 |
|--------|------|-----------|---|---------|------|--------------------|--------------|
| C01 | supervised_only | — | — | 4.71% | PASS | 5.0857% | 0.0000% |
| C02 | OR | p95 | 0.5674 | 9.29% | **FAIL** | 9.8071% | +4.7214% |
| C03 | OR | p99 | 1.5122 | 5.59% | **FAIL** | 5.8816% | +0.7959% |
| C04 | OR | mean+2sigma | 7.5151 | 4.89% | PASS | 5.3285% | +0.2428% |
| C05 | OR | p99.9 | 10.6969 | 4.79% | PASS | 5.2206% | +0.1349% |
| **C06** | **OR** | **mean+3sigma** | **11.1601** | **4.75%** | **PASS** | **5.1531%** | **+0.0674%** |
| C07 | AND | p95 | 0.5674 | 0.42% | PASS | 0.3912% | −4.6945% |
| C08 | AND | p99 | 1.5122 | 0.12% | PASS | 0.1619% | −4.9238% |
| C09 | AND | mean+2sigma | 7.5151 | 0.02% | PASS | 0.0270% | −5.0587% |
| C10 | AND | p99.9 | 10.6969 | 0.02% | PASS | 0.0270% | −5.0587% |
| C11 | AND | mean+3sigma | 11.1601 | 0.02% | PASS | 0.0270% | −5.0587% |

`delta_vs_C01 = subgroup_fpr(config) − subgroup_fpr(C01)` per OD-8.
RST/FIN subgroup size: 7,413 rows (of 11,200 Normal VALIDATION rows).

---

## Approved Decision Audit

| OD | Decision | Applied |
|----|----------|---------|
| OD-1a | LR.predict() at frozen 0.5, EXP_OOF_STACK_V1 seed-42 | ✅ |
| OD-2a | RE > τ strict (RE ≤ τ → Normal) | ✅ |
| OD-3 | 5% FPR gate on Normal-only VALIDATION | ✅ |
| OD-4 | Option A: gate-only, do not rank passing configs by FPR | ✅ |
| OD-4b | Conservative-first: mean+3sigma > p99.9 > mean+2sigma > p99 > p95 | ✅ |
| OD-5 | C01 fallback — NOT triggered (9/11 passed gate) | ✅ |
| OD-6 | Macro-F1 primary metric | ✅ |
| OD-7 | Counts + rate + n=583 caveat (1 row = 0.1716 pp) | ✅ |
| OD-8 | RST/FIN subgroup FPR + delta_vs_C01 per config | ✅ |
| OD-9 | 11 unique configurations C01–C11 | ✅ |
| OD-10 | H-FUSION / H-PROT-BACKDOOR naming | ✅ |

---

## Leakage / Isolation Test Summary

| Test | Status |
|------|--------|
| T-S6-CANONICAL-CHECKPOINT | PASS — seed-42 meta-learner loaded from EXP_OOF_STACK_V1/seed_42 |
| T-CANDIDATE-COUNT | PASS — 11 configs |
| T-CANDIDATE-IDS | PASS — C01..C11 |
| T-CANDIDATE-DETERMINISTIC | PASS |
| T-75-FEATURES | PASS |
| T-THRESHOLD-MATCH | PASS — τ values match EXP_AE_V1 threshold_config.json |
| T-SIGMA-CAUTION | PASS — C04/C06/C09/C11 flagged outlier_influenced=True |
| T-AE-STRICT | PASS — RE == τ classified as Normal (flag=0) |
| T-VAL-NORMAL | PASS — 11,200 rows, all label=0 |
| T-VAL-FPR-ONLY | PASS — AssertionError raised on non-zero label input |
| Focused fusion isolation tests | **29/29 PASS** |
| Full regression suite | **907/907 PASS** |

---

## Exploratory All-11 Analysis — INFORMATIONAL ONLY

> [!IMPORTANT]
> The following is **INFORMATIONAL ONLY, POST-HOC, NO BACKWARD INFLUENCE**.
> It does NOT affect the primary H-FUSION or H-PROT-BACKDOOR verdicts.
> The selected configuration remains C06. No OD decision is altered.

### Development TEST — All 11 (EXPLORATORY)

| Config | Rule | Threshold | Macro-F1 | Recall | FPR | TP | FP | TN | FN | Outlier |
|--------|------|-----------|----------|--------|-----|----|----|----|----|---------|
| C01 | supervised_only | — | 0.8926 | 0.9678 | 19.19% | 43306 | 7100 | 29900 | 1443 | No |
| C02 | OR | p95 | 0.8768 | 0.9697 | 22.68% | 43393 | 8390 | 28610 | 1356 | No |
| C03 | OR | p99 | 0.8893 | 0.9686 | 19.98% | 43344 | 7392 | 29608 | 1405 | No |
| C04 | OR | mean+2sigma | 0.8921 | 0.9678 | 19.29% | 43306 | 7136 | 29864 | 1443 | **Yes** |
| C05 | OR | p99.9 | 0.8924 | 0.9678 | 19.23% | 43306 | 7115 | 29885 | 1443 | No |
| **C06** | **OR** | **mean+3sigma** | **0.8924** | **0.9678** | **19.22%** | **43306** | **7113** | **29887** | **1443** | **Yes** |
| C07 | AND | p95 | 0.5502 | 0.2669 | 1.90% | 11942 | 703 | 36297 | 32807 | No |
| C08 | AND | p99 | 0.3611 | 0.0475 | 0.57% | 2125 | 212 | 36788 | 42624 | No |
| C09 | AND | mean+2sigma | 0.3393 | 0.0254 | 0.05% | 1138 | 18 | 36982 | 43611 | **Yes** |
| C10 | AND | p99.9 | 0.3258 | 0.0129 | 0.02% | 576 | 6 | 36994 | 44173 | No |
| C11 | AND | mean+3sigma | 0.3257 | 0.0128 | 0.02% | 575 | 6 | 36994 | 44174 | **Yes** |

**Informational observations** (no backward influence on selection or verdicts):

- C02 and C03 achieved slightly higher attack recall than C01 (96.97% and 96.86%
  vs 96.78%), but incurred materially higher Development TEST FPR (22.68% and
  19.98% vs 19.19%) and lower Macro-F1 (0.877 and 0.889 vs 0.893).
- OR configurations C04–C06 cluster tightly around C01 in all metrics; their
  AE signal is effectively inert at these conservative thresholds.
- AND configurations achieve very low FPR but catastrophically low recall
  (<27%), confirming AND fusion is unsuitable for this detection task.
- These observations do not alter the frozen C06 selection or either primary
  hypothesis verdict.

### Protected Backdoor — All 11 (EXPLORATORY)

| Config | Rule | Threshold | Detected | Missed | Rate |
|--------|------|-----------|----------|--------|------|
| C01 | supervised_only | — | 582 | 1 | 99.83% |
| C02 | OR | p95 | 582 | 1 | 99.83% |
| C03 | OR | p99 | 582 | 1 | 99.83% |
| C04 | OR | mean+2sigma | 582 | 1 | 99.83% |
| C05 | OR | p99.9 | 582 | 1 | 99.83% |
| **C06** | **OR** | **mean+3sigma** | **582** | **1** | **99.83%** |
| C07 | AND | p95 | 38 | 545 | 6.52% |
| C08 | AND | p99 | 24 | 559 | 4.12% |
| C09 | AND | mean+2sigma | 19 | 564 | 3.26% |
| C10 | AND | p99.9 | 0 | 583 | 0.00% |
| C11 | AND | mean+3sigma | 0 | 583 | 0.00% |

AND configurations detect virtually none of the protected backdoor attacks
because they require the AE to flag the same rows the supervised model already
misclassifies — a structural failure mode of AND fusion. OR configurations
maintain near-perfect detection inherited from the supervised branch.

---

## Mandatory Limitations

### Validation Reuse Limitation

> [!WARNING]
> **VALIDATION is reused for Sprint 7 AE threshold calibration AND Sprint 8
> fusion-rule selection. Both are selection-stage uses, not final held-out
> evaluation. This reuse is within the frozen data-isolation rules but is
> an explicit limitation and must appear in metadata.json, quality_review.md,
> and the final report.**

The fixed evaluation sequence is:

```
VALIDATION selection → freeze ONE config → Development TEST → Protected Backdoor
```

Development TEST and Protected Backdoor results never feed backward into
configuration selection. This is a fixed invariant, not subject to override.

### Scaler-Space Limitation (MANDATORY)

> AE operates in a Normal-TRAIN-scaled feature space distinct from the
> full-TRAIN-scaled space used by DT/RF/SVM/NN. Sprint 8 fusion must
> account for this representation difference when combining the AE
> reconstruction error with the supervised branch outputs.

Sprint 8 fusion combines binary outputs (LR.predict() and AE RE > τ). The
binary flag approach sidesteps arithmetic combination of the incompatible
feature spaces. This limitation is an accepted scope constraint.

### Single-Seed AE Limitation (MANDATORY)

> Sprint 7 uses a single AE training seed (42). No multi-seed stability
> estimate exists for AE reconstruction error or threshold values. This
> is an accepted scope limitation and not a null result.

### Outlier-Influenced Threshold (C06, C04, C09, C11)

Thresholds τ_mean+2sigma and τ_mean+3sigma are influenced by the two extreme
Normal VALIDATION rows (row_id 10737, RE≈269.09; row_id 10731, RE≈269.03).
These are legitimate RST/FIN TCP structural artefacts and were NOT filtered.
`outlier_influenced = True` is set in all affected config records.

### n=583 Protected Backdoor Caveat

**1 row = 1/583 = 0.1716 percentage points.** Differences of 0–1 rows between
configurations correspond to ≤ 0.1716 pp and must not be over-interpreted as
strong generalisation evidence.

---

## Approved Upstream Experiments

| Experiment | Freeze Status |
|------------|---------------|
| EXP_MI_V1_1 | FROZEN |
| EXP_BASE_MODELS_V1 | FROZEN |
| EXP_OOF_STACK_V1 | FROZEN |
| EXP_AE_V1 | FROZEN |

---

## Data Integrity Verification

| Split | SHA-256 (first 16 hex chars) | Rows | Label Distribution |
|-------|------------------------------|------|-------------------|
| train.csv | `4a259324e604f013` | 162,395 | Mixed (Normal + Attack) |
| validation.csv | `13caf21a076a33f5` | 11,200 | 100% Normal (label=0) |
| development_test.csv | `04725e85732ab2fc` | 81,749 | attack=44,749 / normal=37,000 |
| protected_unseen_attack.csv | `6ffd23479b575e43` | 583 | 100% Attack (label=1) |

All four hashes were verified by T-HASH during implementation. Full SHA-256 values:

- `train.csv`: `4a259324e604f013287a5de5fe49c46bf19418d815b550c5d1a5820b569ac41c`
- `validation.csv`: `13caf21a076a33f50243f48f404b7e7525969f71d4b9d7c0f3768aef23589180`
- `development_test.csv`: `04725e85732ab2fc6d9eaaa6105418b22b083b5c651067e7b0785464f414e508`
- `protected_unseen_attack.csv`: `6ffd23479b575e438ad90678268f40f674a663c2b9507aaf65089623397a9d91`

---

## Proposed Freeze Commit Message

*(Documentation only — commit NOT yet created)*

```
Sprint 8: 2×2 Fusion evaluation (EXP_FUSION_V1) — H-FUSION=FALSE,
H-PROT-BACKDOOR=FALSE. Selected config C06 (OR+mean+3sigma) shows no
measurable improvement over C01 baseline; outlier-influenced threshold
renders AE component near-inert at selected operating point. Exploratory
analysis (informational only) shows more aggressive OR thresholds
(p95/p99) yield marginally higher attack recall at substantially higher
FPR cost.
```

---

## Final Status

```
IMPLEMENTATION:   COMPLETE
TEST:             COMPLETE  (single-shot, non-repeatable)
VALIDATE:         COMPLETE  (verdicts issued above)
FREEZE:           NOT STARTED — AWAITING HUMAN APPROVAL
```

Selected configuration: **C06** (OR + mean+3sigma, τ = 11.160062745213509)
Focused fusion tests: **29/29 PASS**
Full regression suite: **907/907 PASS**
