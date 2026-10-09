# Sprint 4 MI Protocol Amendment — v1.0 → v1.1

## Amendment ID

`EXP_MI_V1_1`

## Date

2026-08-31

## Author

Experiment governance: human approval required and received.

## Reason for Amendment

The initial Sprint 4 MI experiment (`EXP_MI_V1`, protocol v1.0) completed
successfully with K candidate grid `{10, 20, 30, 40, 50}`.

The post-selection sanity check returned:

```
STATUS: REVIEW_REQUIRED
CONDITION: MONOTONIC
```

Mean inner-CV macro-F1 was monotonically non-decreasing across the
entire candidate grid:

| K  | Mean Macro-F1 |
|----|---------------|
| 10 | 0.824852      |
| 20 | 0.864436      |
| 30 | 0.897442      |
| 40 | 0.916198      |
| 50 | 0.919560      |

Per protocol, a monotonic sanity flag requires human review before
freezing. Automatic freeze was blocked.

**Human decision:** Extend the K grid once before final MI selection,
to allow the evaluator to find a meaningful plateau or diminishing-returns
boundary.

## Protocol Change

| Field | v1.0 | v1.1 |
|---|---|---|
| `candidate_k` | [10,20,30,40,50] | [10,20,30,40,50,75,100,150] |
| Experiment ID | EXP_MI_V1 | EXP_MI_V1_1 |
| All other parameters | — | **UNCHANGED** |

## What Is NOT Changed

- MI estimator: `mutual_info_classif`
- n_neighbors: `3`
- random_state: `42`
- CV method: `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`
- Evaluator: `LogisticRegression(solver=liblinear, C=1.0, max_iter=1000, class_weight=balanced, random_state=42)`
- Evaluator scaling: `StandardScaler` fitted on inner_train ONLY
- Selection metric: `macro_f1`
- Tie-break: smaller K
- Data: frozen `data/splits/train.csv` ONLY
- Feature representation: encoded + unscaled
- Target: `label` (binary 0=Normal, 1=Attack)
- Leakage boundaries: unchanged
- AE shared-feature decision: unchanged

## Timing

This amendment was made **before** rerunning the expanded K-selection
experiment. No TEST, outer VALIDATION, protected Backdoor, or archived
Backdoor data were observed or used in making this amendment decision.

The decision was based solely on the monotonic sanity flag produced by
the training-only inner-CV results.

This is **not** performance tuning on TEST.

## Original v1.0 Results Preserved

The original results are preserved intact at:

```
results/feature_selection/EXP_MI_V1/
```

These are not overwritten or deleted.

## Sanity Check Policy for v1.1

If the expanded K grid `{10,20,30,40,50,75,100,150}` still produces a
monotonically non-decreasing mean macro-F1 curve through K=150:

- Return `REVIEW_REQUIRED` again.
- **Do NOT automatically add K=175 or K=193.**
- Stop for another human decision.

If the curve establishes a meaningful non-monotonic point:

- Select K using the existing highest-mean-macro-F1 rule (smaller K on tie).
- Proceed to final refit and freeze.
