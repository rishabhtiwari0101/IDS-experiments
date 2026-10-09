# IMPLEMENTATION BLUEPRINT — IDS-UNSW-NB15 Research Compliance

> **Version:** 5.0 — Final Execution Blueprint (partition-shift hardening)  
> **Date:** 2026-09-28  
> **Purpose:** Dependency-aware execution blueprint for implementing all 18 subrequirements from `Changes for research paper.pdf`, incorporating the methodological corrections identified during review of Versions 1.0–4.0 and the final execution-readiness audit.  
> **Status:** Planning-only. No repository experiments, models, or manuscript files have been modified by preparation of this document.  
> **Supersedes:** Version 4.0, Version 3.0, Version 2.0, and Version 1.0

---

### Changelog v4.0 → v5.0 (what was fixed and why)

| # | Fix | Where |
|---|-----|-------|
| C1 | **Major:** VAL-calibrated thresholds may not deliver the nominal FPR on the evaluation control because VAL and the control most likely come from different official UNSW-NB15 partitions. Added a **two-tier calibration design** (Tier A = VAL-calibrated; Tier B = disjoint control-split-calibrated), a **committed headline-tier decision rule**, and a **partition-shift diagnostic**. | Rules 1, 15; §0.1–0.3; §5–§6; §16; §17; Gates 1, 4, 6, 8; R37–R41; §22 |
| C2 | Alert-budget analysis (Req 1.4) now reports **recall** (with CI) under each review-budget scenario, not only alert counts and PPV. | §6 B4; S8; M13; S9 check 17 |
| C3 | Table II (M4) mixed populations (DEV_TEST Macro-F1 vs zero-day PR-AUC/F2). Column groups are now population-labelled with prevalence; F2/PPV are never compared across tiers. | §0.2; M4; R39 |
| C4 | Req 4.3 second-dataset decision is now explicit and recorded (DOC-08) and Limitations are specified (M17). | §5F; §13; M17 |
| C5 | Threshold index `k` computed in exact arithmetic (hardening; float `floor` is not guaranteed safe for every `N_cal`). | §0.1; R38 |
| C6 | Version-label inconsistency (header 4.0 vs footer 3.0) fixed. | Header; footer |

---

## 0. Governing Methodological Rules

The following rules are **controlling protocol constraints**. Where any later section conflicts with them, this section takes precedence.

1. **Calibration and evaluation are separated, with an explicit calibration-source branch.** Phase 0 must first determine whether the 11,200 benign VAL rows were untouched by model development. If VAL benign rows were not used for early stopping, hyperparameter/model selection, meta-learner fitting, or any fitted preprocessing/feature-selection decision, they are the primary calibration population. If VAL was used in model development, the headline analysis must instead use a documented calibration-only benign population that was not used for model development (either an independently untouched benign set or a demonstrably unused subset available from the original data-generation protocol). A merely random split of an already-used VAL set does **not** restore independence and is sensitivity-only. Thresholds selected on rows that are themselves scored in the reported evaluation population are **oracle / test-tuned analyses** and are excluded from headline claims. A threshold selected on a *disjoint, committed* calibration subset of the benign control (Tier B, Rule 15) is not oracle for the rows it is evaluated on, because calibration and evaluation rows never overlap.
2. **Meta-learner seeds are calibrated independently.** Seeds 42, 123, and 2024 each receive their own thresholds. A threshold from one seed is never reused for another.
3. **Every requested FPR is a budget, not a promise.** Ties and discrete scores may prevent exact attainment. Every table reports the achieved calibration FPR and the achieved held-out FPR with a Clopper–Pearson 95% CI, and recall with a Clopper–Pearson 95% CI. The calibration population size is read from the resolved manifest, so the threshold index is always computed from the actual `N_cal`.
4. **Frozen AE inference is allowed and required where evidence is missing.** The EXP_AE_V1 checkpoint and frozen AE scaler may be run in inference mode to export reconstruction-error dumps. No AE retraining, refitting, or parameter updates.
5. **AE ablation rules come from one AE model and one resolved calibration-error vector.** All percentile, sigma, and MAD thresholds in the final AE ablation are computed from the same S1-generated AE reconstruction-error vector for the resolved clean calibration population. When `source_status=untouched_val`, that vector is the regenerated EXP_AE_V1 validation reconstruction-error vector. Nothing is imported from EXP_AE_UNSEEN_FAMILY_V1.
6. **Isolation Forest uses three seeds and the frozen AE scaling domain.** IF is trained independently for seeds 42, 123, 2024 on benign TRAIN only and reuses the frozen `EXP_AE_V1/ae_scaler.joblib`. No new scaler is fitted.
7. **Equivalence analysis uses one declared margin and a conservative exact paired procedure.** The margin lives in a committed config before S4 runs. Use one numeric value everywhere. Because the paired counts were already known when the margin was chosen, the manuscript must describe the margin as specified after the paired data were observed (post-hoc), not as pre-registered. Use the conservative exact discordant-proportion procedure in §8; the Wilson/normal approximation from Version 1.0 is prohibited.
8. **Preregistration claims are evidence-constrained.** "Predeclared" may be used only where Git history or contemporaneous records show the criterion preceded the relevant result. Anything created after results were available is described as post-hoc, regardless of filename.
9. **Conclusion language is result-contingent.** The manuscript is not pre-committed to "neither paradigm is deployable." The conclusion is written after constrained-FPR results exist and states what the evidence shows, including the possibility that calibrated stacking retains high recall.
10. **Venue formatting is deferred** until a venue is explicitly selected (Phase 9). Experiments are venue-agnostic.
11. **Symmetric protocol.** Every scored model — DT, RF, SVM, NN, Stacking (×3 seeds), AE, Isolation Forest (×3 seeds) — passes through the same threshold rule (§0.1), the same four FPR budgets (0.1%, 0.5%, 1%, 5%), the same **resolved clean calibration population**, and the same held-out zero-day evaluation populations. The AE and IF are not evaluated under a different protocol from the supervised models. Default-threshold metrics remain reference-only and are never substituted for the common matched-FPR comparison.
12. **Single source of truth for populations and references.** All scripts read populations from one shared manifest (`publication_experiments/configs/populations.yaml`) that includes row-identity lists and hashes. Expected metric values are always read from frozen artifact files; only population sizes and protocol constants may be written into scripts or configs.
13. **Calibration-population integrity and provenance.** Phase 0 audits use of VAL for early stopping, hyperparameter/model selection, meta-learner fitting, feature selection, and fitted preprocessing/scalers. If VAL is untouched by model development, the full 11,200-row benign VAL set may be used for headline calibration. If VAL was used during model development, the headline calibration population must come from a demonstrably unused benign population; an after-the-fact random split of contaminated VAL is not considered an independent calibration set. If no clean calibration population can be established, matched-FPR results may still be produced as development-contaminated sensitivity analyses, but they are not clean headline operating-point claims. M16 discloses the audit outcome.
14. **Protocol-defining configs are committed to Git before the script that reads them is executed.** This applies to populations, calibration source, calibration rules and budgets, seeds, metric definitions, curve-aggregation rules, the TOST margin, and MAD k values.

15. **Two calibration tiers; partition shift is measured, not assumed.** Arithmetic that must be corroborated in Phase 0 (S0 item 10): TRAIN benign (44,800) + VAL benign (11,200) = 56,000, the benign count of the official UNSW-NB15 *training* partition; the 37,000-row benign control equals the benign count of DEV_TEST (81,749 − 44,749 attack rows), i.e. the official *testing* partition (Backdoor held out separately). If confirmed, Tier-A calibration rows and the evaluation control come from **different official partitions**, which are commonly reported to differ in distribution, so a VAL-derived threshold can realize an FPR on the control that differs systematically from the nominal budget (not merely by sampling noise). Every matched-FPR result is therefore produced under two tiers:
    - **Tier A (VAL-calibrated):** calibration on the resolved clean calibration population (Rules 1 and 13); evaluation on the full 37,000-row benign control + 583 Backdoor (`ZERO_DAY_COMBINED`).
    - **Tier B (control-split-calibrated):** the 37,000-row benign control is split **once** into disjoint `CAL_CONTROL` (18,500) and `EVAL_CONTROL` (18,500) using a `split_seed` declared in `populations.yaml`; thresholds are calibrated on `CAL_CONTROL` only; evaluation uses `EVAL_CONTROL` + 583 Backdoor (`ZERO_DAY_EVAL_HALF`). Backdoor labels/scores are never used for calibration. Split lists and SHA-256 hashes are committed before S3 runs.
    - **Headline-tier decision rule (declared here; the identical text is committed in `matched_fpr.yaml` before S3 runs):** a (model, seed, budget) cell is *shift-affected* if the nominal budget lies outside the Clopper–Pearson 95% CI of the realized Tier-A held-out control FPR. If **no** cell is shift-affected, Tier A is the headline tier and Tier B is a robustness table. If **any** cell is shift-affected, **Tier B is the headline tier** for all matched-FPR recall/F2 claims, and Tier A is reported alongside as the *partition-shifted operating point*; the realized-vs-nominal gap is then presented as a finding. Tiers are never mixed within one comparison table. S3 writes the outcome to `headline_tier_decision.json`.
    - **Eligibility:** Tier A requires the Rule 1/13 VAL-usage audit outcome (`untouched_val` or `alternate_clean_source`). Tier B requires a clean DEV_TEST-usage audit, i.e. evidence that benign DEV_TEST rows did not influence the development or selection of any scored model. If Tier B is not clean it is labelled sensitivity-only and disclosed (M16). The Rule 13 contaminated-sensitivity fallback applies only if **neither** tier is eligible.
    - **Prevalence:** F2 and PPV depend on prevalence and are never compared across tiers (Tier A: 583/37,583 ≈ 1.55%; Tier B: 583/19,083 ≈ 3.06%). Recall and FPR (with CIs) are the cross-tier comparable quantities.
    - **Threshold-free metrics** (ROC-AUC, PR-AUC (AP)) are computed once on the full `ZERO_DAY_COMBINED` population and are tier-independent.

### 0.1 Threshold rule (defined once, used everywhere)

- Score direction: larger = more attack-like. DT/RF/NN/Stacking: attack probability. SVM: raw decision score. AE: reconstruction error. IF: `-score_samples()`.
- Alert rule: an alert is raised iff `score > t` (strict).
- Budget calibration for budget `b` on the **resolved calibration population** of size `N_cal`: sort benign scores descending; `k = floor(b × N_cal)` computed in **exact arithmetic** (for example `fractions.Fraction(str(b)) * N_cal`, or `floor(round(b × N_cal, 9))`), never a raw floating-point `floor`; `t = sorted_desc[k]` (0-indexed). This guarantees at most `k` calibration scores strictly exceed `t`. When `N_cal = 11,200` (Tier A with full VAL), the indices are 11 / 56 / 112 / 560 for 0.1% / 0.5% / 1% / 5%; when `N_cal = 18,500` (Tier B), they are 18 / 92 / 185 / 925. Never hardcode those indices when the calibration population changes; S3 asserts the computed `k` against an independent exact-arithmetic reference.
- Ties can only lower the realized FPR; the realized FPR is always reported.
- The new matched-FPR analyses use the declared strict alert rule `score > t`. Historical threshold-0.5 reproducibility checks must use the comparator implemented by the frozen EXP_ZERODAY_V1 reference so a comparator difference is not mistaken for a population or preprocessing mismatch.
- Rule-based AE/IF thresholds (p95, p99, p999, mean+2σ, mean+3σ, MAD) use `numpy.percentile(method="linear")` for percentiles and are reported with their own achieved calibration FPR. They are a separate, clearly labelled family from the budget-matched thresholds above.

### 0.2 Metric and aggregation definitions

- **PR-AUC:** `sklearn.metrics.average_precision_score` (Average Precision), reported under the manuscript label **PR-AUC (AP)**.
- **F2:** `sklearn.metrics.fbeta_score(..., beta=2)` computed at each common matched-FPR operating point (0.1%, 0.5%, 1%, 5%) for **every model and every applicable seed**. The **headline matched-FPR F2 is computed on the headline tier's evaluation population** (Tier A: `ZERO_DAY_COMBINED`; Tier B: `ZERO_DAY_EVAL_HALF` = `EVAL_CONTROL` + Backdoor), using the same held-out population and threshold as the recall analysis, with the population's prevalence stated (Rule 15). Any DEV_TEST F2 is reference/descriptive unless separately specified. Default-threshold F2 is reference-only.
- **Seed handling:** never pool prediction scores or labels across seeds to create a pooled ROC or PR curve. Plot one curve per seed for seeded models, or designate seed 42 as the main-figure representative while retaining all seed curves in artifacts/supplement. Report ROC-AUC and PR-AUC per seed plus mean ± SD.
- **Model-difference uncertainty:** cross-model statements remain descriptive unless a paired uncertainty analysis is added. A paired bootstrap for stacking vs. AE Backdoor recall at 1% FPR is an optional secondary analysis.

### 0.3 Global tolerances

| Quantity | Reference source | Tolerance |
|----------|------------------|-----------|
| Stacking DEV_TEST Macro-F1 (each seed) | `results/evaluation/EXP_H123_V1/h1_results.json` | ±1e-6 |
| Stacking threshold-0.5 FPR on the benign control | `zero_day_metrics.csv` | ±1e-3 absolute; FP-count difference also reported |
| Stacking threshold-0.5 Backdoor detections | `zero_day_metrics.csv` | exact integer match |
| AE mean, std, τ (mean+3σ) recomputed from the S1-generated AE calibration RE vector | `EXP_AE_V1/threshold_config.json` | relative 1e-4 when untouched-VAL is active; otherwise the frozen τ is historical reference only |
| AE τ applied to zero-day REs → Backdoor detections | `zero_day_metrics.csv` (AE row) | exact integer match |
| Row-identity hashes (benign control, `CAL_CONTROL`, `EVAL_CONTROL`, unseen families) | `populations.yaml` | exact |

---

## 1. Executive Summary

The project requires the following new work before the manuscript can be revised on a fully compliant evidence base:

| Class | Count | Description |
|-------|-------|-------------|
| **Frozen inference (no training)** | 1 coordinated run (S1) | Supervised scores (DT, RF, SVM, NN, Stacking ×3 seeds) and AE reconstruction errors on VAL benign, DEV_TEST, zero-day, and unseen-family populations |
| **New model training** | 1 experiment (S7) | Isolation Forest, benign-only, 3 seeds |
| **New analysis** | 6 scripts | Matched-FPR (all models), ROC/PR/F2, alert budget, AE threshold family + MAD, AE ablation table, TOST |
| **Support scripts** | 2 | Phase-0 discovery (S0), cross-result consistency check (S9) |
| **Paper-only factual corrections** | 4 | NN architecture (M1), AE training count (M2), Worms CI in Abstract/Conclusion (M9, M10) |
| **Manuscript scientific corrections** | 17 | M1–M17 (§20) |
| **Presentation / reproducibility requirements** | 8 | Requirements 3.1–3.5 and 4.1–4.3 |

**Key facts confirmed in this blueprint:**

- NN architecture is `75 → 128 → 64 → 1` (binary sigmoid), not `75 → 128 → 64 → 2`. The paper is wrong. Checkpoint metadata and source code agree with each other.
- AE training: 40,320 rows for the early-stopping phase; the final refit uses all 44,800 benign TRAIN rows (best_epoch = 133). The paper mentions only 40,320.
- The canonical AE threshold τ = 11.160063 (mean+3σ) is the EXP_AE_V1 frozen threshold. EXP_AE_UNSEEN_FAMILY_V1 values come from separately calibrated re-runs and are not the same model.
- Stacking probabilities on DEV_TEST and zero-day populations **do not exist**; `combined_evaluation_predictions.csv` stores binary decisions only. New frozen inference is required, and the same run exports AE reconstruction errors.
- All base-model and meta-learner checkpoints exist and are hash-verified.
- Python 3.11 with a `.venv` environment. Commands run from the project root in PowerShell using the exact repository-relative script paths in §16–§17.
- Populations (VAL benign, DEV_TEST, benign control, Tier-B `CAL_CONTROL`/`EVAL_CONTROL` halves, Backdoor, unseen families) are defined once in `populations.yaml` with row-identity hashes and shared by S1, S3, S6, S7, and S9.
- **Partition-shift risk (v5.0):** the split-size arithmetic indicates VAL comes from the official training partition and the evaluation control from the official testing partition. Matched-FPR results are therefore produced under two calibration tiers with a pre-committed headline rule (Rule 15); Phase 0 corroborates the arithmetic and S3 measures the shift.

---

## 2. Verified Requirement Inventory

### Section 1: Core Methodological Issue (19.19% FPR / Asymmetric Comparison)

| ID | Requirement | Implemented | Executed | Artifact | Validated | Reported | Status |
|----|------------|-------------|----------|----------|-----------|---------|--------|
| 1.1 | ROC + PR curves for stacking (C01) on matched population | NO | NO | NO | NO | NO | **MISSING** |
| 1.2 | Stacking zero-day recall at FPR budgets 0.1%, 0.5%, 1%, 5% | NO | NO | NO | NO | NO | **MISSING** |
| 1.3 | PR-AUC and F2-score as headline metrics (all models) | NO | NO | NO | NO | NO | **MISSING** |
| 1.4 | Cost-sensitive / alert-budget framing in Discussion | NO | NO | NO | NO | NO | **MISSING** |
| 1.5 | Explicit distinction: 19.19% threshold-0.5 FPR is uncalibrated; evaluate constrained-FPR recall on held-out control | NO | NO | PARTIAL* | NO | PARTIAL | **PARTIAL** |
| 1.6 | Result-contingent conclusion framing based on constrained-FPR evidence; do not precommit outcome | NO | NO | NO | NO | NO | **MISSING** |

*AE FPR data at constrained thresholds exists in `secondary_threshold_fpr_matrix.csv`; stacking equivalent does not. The existing stacking 19.19% value is a threshold-0.5 reference only; new constrained-FPR headline results must use independent calibration and held-out evaluation.

### Section 2: Methodological Gaps

| ID | Requirement | Implemented | Executed | Artifact | Validated | Reported | Status |
|----|------------|-------------|----------|----------|-----------|---------|--------|
| 2.1 | ≥1 additional unsupervised baseline (Isolation Forest preferred) | NO | NO | NO | NO | NO | **MISSING** |
| 2.2 | Robust-threshold ablation (percentile/MAD) + zero-day recall under those thresholds | PARTIAL** | PARTIAL | PARTIAL | PARTIAL | PARTIAL | **PARTIAL** |
| 2.3 | TOST equivalence test for RF (B=0, C=0 McNemar is non-informative) | NO | NO | NO | NO | NO | **MISSING** |
| 2.4 | Worms 8.04% CI upper bound in Abstract and Conclusion (not just Results/Limitations) | N/A | DONE | YES | YES | PARTIAL | **PARTIAL** |

**Percentile/sigma thresholds in the legacy evidence exist for the EXP_AE_UNSEEN_FAMILY_V1 re-run AEs, which are not the canonical calibration model. The final ablation is therefore recomputed from the S1-generated AE reconstruction-error vector for the resolved clean calibration population (S5/S6); when untouched VAL is active, this is the regenerated EXP_AE_V1 validation RE vector. MAD is new.

### Section 3: Presentation and Writing Style

| ID | Requirement | Implemented | Executed | Artifact | Validated | Reported | Status |
|----|------------|-------------|----------|----------|-----------|---------|--------|
| 3.1 | Academic register throughout Results/Discussion (15+ informal phrases) | N/A | N/A | N/A | N/A | NO | **MISSING** |
| 3.2 | Move Eq.(5) Δσ² ≈ πM² to §VI.A.2 | N/A | N/A | N/A | N/A | NO | **MISSING** |
| 3.3 | Author affiliation format (remove "B.E. Student(s)") | N/A | N/A | N/A | N/A | NO | **MISSING** |
| 3.4 | Email typo: `gamil.com` → `gmail.com` | N/A | N/A | N/A | N/A | NO | **MISSING** |
| 3.5 | Rebuild Tables II, III, IV in the selected venue's template | N/A | N/A | N/A | N/A | PARTIAL | **PARTIAL** |

### Section 4: Reproducibility and Scope

| ID | Requirement | Implemented | Executed | Artifact | Validated | Reported | Status |
|----|------------|-------------|----------|----------|-----------|---------|--------|
| 4.1 | Code/data availability statement with repository link | N/A | N/A | N/A | N/A | NO | **MISSING** |
| 4.2 | Pre-registration document as supplementary, or remove "pre-registered" language | YES*** | YES | YES | PARTIAL | PARTIAL | **PARTIAL** |
| 4.3 | Second dataset or strengthened Limitations | N/A | N/A | N/A | N/A | PARTIAL | **PARTIAL** |

***Preregistration artifacts exist, but `materiality_preregistration.json` is timestamped 2026-09-08, seven days after the stacking experiment ran (2026-09-01). The status of `preregistered_decisions.json` (H2) must be established from Git history, not assumed. The requirement cannot be satisfied by fabricating a retroactive preregistration: use "predeclared" only where Git evidence shows the criterion preceded the result, and describe everything else as post-hoc (Rule 8).

**Verified totals: 12 MISSING, 6 PARTIAL, 0 DONE**

---

## 3. Dependency Graph

```
FREEZE POINT (all models / splits locked)
│
├── PHASE 0: S0 phase0_discovery  ──►  resolves (a) unseen-family source, (b) VAL-usage audit and calibration branch,
│                                       (c) benign-control row-ID list + hash, (d) AE calibration-RE provenance,
│                                       (e) population disjointness/row-ID integrity, (f) Git evidence
│        └─► populations.yaml completed and COMMITTED (incl. Tier-B CAL/EVAL control split lists + hashes; skeleton with `split_seed` committed BEFORE S0)
│
├── BATCH-A: S1 run_prob_inference  (frozen inference only)
│     Input : frozen checkpoints, populations.yaml
│     Output: supervised score files (DEV_TEST, resolved clean calibration population, zero-day)
│             AE reconstruction-error files (DEV_TEST, resolved clean calibration population, zero-day, unseen families)
│
├── BATCH-C: S7 run_isolation_forest  (3 seeds; only new model training)
│     Input : TRAIN benign, frozen AE scaler, populations.yaml
│     Output: per-row IF scores on the resolved clean calibration population, DEV_TEST, zero-day, unseen families; rule-based summaries
│
├── TOST: S4 run_tost_analysis  (independent; needs committed tost.yaml)
│
├── AE THRESHOLD FAMILY: S5 → S6      (needs S1 AE dumps)
│
├── MATCHED-FPR: S3                   (needs S1 + S7; all models; Tier A + Tier B; partition-shift diagnostic; headline-tier decision)
│
├── ROC/PR/F2: S2  and  ALERT BUDGET: S8   (need S1 + S7 + S3)
│
├── CONSISTENCY: S9 run_cross_consistency_check  (needs everything above)
│
└── MANUSCRIPT (only after S9 passes)
      ├── M1–M17, requirements 3.1–3.5, 4.1–4.3
      └── venue selection precedes table/template work
```

---

## 4. Reusable Existing Evidence

The following artifacts **require no new computation** and can be directly used for manuscript reporting:

| Artifact | Path | Used For | Notes |
|----------|------|----------|-------|
| AE threshold sweep (EXP_AE_UNSEEN_FAMILY_V1) | `results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1/threshold/seed_42/threshold_sweep.csv` | Background / cross-check only | **Do not use as the source of final EXP_AE_V1 ablation thresholds**; it comes from a different AE run |
| AE detection sweep per family per threshold | `results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1/` (detection_sweep.csv or equivalent) | Cross-check only | Different AE run than EXP_AE_V1; not a source of final numbers |
| Secondary threshold FPR matrix | `results/publication_experiments/EXP_STATS_ROBUSTNESS_V1/threshold_tradeoff/secondary_threshold_fpr_matrix.csv` | Req 1.5, 2.2 | AE only, not stacking |
| McNemar results | `results/publication_experiments/EXP_STATS_ROBUSTNESS_V1/paired_tests/mcnemar_results.csv` | Req 2.3 (fallback input to equivalence analysis) | Data exists; only TOST computation missing |
| Worms 8.04% CI | `results/publication_experiments/EXP_INTEGRATED_PUBLICATION_V1/integrated_statistics/ae_primary_summary.csv` | Req 2.4 | Only needs manuscript reporting |
| Zero-day threshold-0.5 stacking reference | `results/zero_day/EXP_ZERODAY_V1/metrics/zero_day_metrics.csv` | Req 1.5 validation reference | Existing value is an uncalibrated threshold-0.5 reference; use for reproducibility check, not as a deployment operating point |
| Stacking Macro-F1 per seed (DEV_TEST) | `results/evaluation/EXP_H123_V1/h1_results.json` | Req 1.3 (F1 already exists, F2 does not) | F2 requires BATCH-A probabilities |
| Preregistration decisions JSON | `results/zero_day/EXP_ZERODAY_V1/metrics/preregistered_decisions.json` | Req 4.2 | Call "predeclared" only if Git evidence shows the criterion preceded the result; otherwise describe as post-hoc |
| Materiality preregistration | `publication_experiments/stage_d/materiality_preregistration.json` | Req 4.2 | Post-hoc: must disclaim timing in paper |
| AE architecture JSON | `results/checkpoints/EXP_AE_V1/ae_architecture.json` | Architecture verification | Confirms 75→12→6→12→75 |
| NN architecture JSON | `results/checkpoints/EXP_BASE_MODELS_V1/nn/nn_architecture.json` | Architecture discrepancy resolution | Confirms hidden_sizes=[128,64], no output dim key |
| NN metadata | `results/checkpoints/EXP_BASE_MODELS_V1/nn/nn_metadata.json` | Architecture discrepancy | `output_contract: "predict + sigmoid probability in [0,1]"` — confirms single sigmoid output |
| AE metadata | `results/checkpoints/EXP_AE_V1/ae_metadata.json` | AE training count | `training_rows: 40320, monitor_rows: 4480, normal_train_total: 44800` |
| AE threshold config | `results/checkpoints/EXP_AE_V1/threshold_config.json` | Historical AE calibration reference | Used as a provenance/cross-check when untouched VAL is active; the final ablation thresholds are computed from the S1-generated AE calibration RE vector |
| Checkpoint SHA hashes | `results/evaluation/EXP_H123_V1/provenance/*.json` | Provenance gate | All model hashes verified |

---

## 5. New Work Required

### 5A. Code (New Scripts)

| Script ID | Path | Purpose | Inputs | Outputs |
|-----------|------|---------|--------|---------|
| S0 | `publication_experiments/scripts/phase0_discovery.py` | Read-only discovery: hashes, unseen-family source, VAL-usage and DEV_TEST-usage audits, partition-provenance check, benign-control row-uid list, Tier-B CAL/EVAL control split lists, AE VAL RE source, Git evidence for preregistration files | Repo, frozen artifacts | `results/publication_experiments/EXP_PHASE0_V1/phase0_discovery.json` |
| S1 | `publication_experiments/scripts/run_prob_inference.py` | Frozen inference for supervised models and AE | Checkpoints, `populations.yaml` | Score files (see §6), `metadata.json`, `self_check.json` |
| S2 | `publication_experiments/scripts/run_roc_pr_analysis.py` | ROC, PR, PR-AUC, F2 for all models (incl. AE, IF) | S1 + S7 score files | ROC/PR CSVs, summaries, figures |
| S3 | `publication_experiments/scripts/run_matched_fpr_analysis.py` | Tier A and Tier B matched-FPR evaluation for **all** models at 0.1/0.5/1/5%, partition-shift diagnostic, headline-tier decision | S1 + S7 score files | `matched_fpr_table.csv`, cross-model comparison CSV, `partition_shift_diagnostic.csv`, `headline_tier_decision.json` |
| S4 | `publication_experiments/scripts/run_tost_analysis.py` | Conservative exact paired-equivalence test for RF ± TTL | Paired contingency (A, B, C, D), `tost.yaml` | `tost_rf_equivalence.json` |
| S5 | `publication_experiments/scripts/run_mad_threshold.py` | AE threshold family (p95, p99, p999, mean+2σ, mean+3σ, MAD) from one VAL RE vector | EXP_AE_V1 VAL REs | `mad_threshold.json` |
| S6 | `publication_experiments/scripts/run_ae_threshold_ablation.py` | Unified AE ablation table | S5 output + S1 AE dumps | `ae_threshold_ablation_table.csv` |
| S7 | `publication_experiments/stage_f/scripts/run_isolation_forest.py` | Train, calibrate, and score IF (3 seeds) | TRAIN benign, frozen AE scaler, `populations.yaml` | Per-seed models, per-row scores, rule-based summaries |
| S8 | `publication_experiments/scripts/run_alert_budget_analysis.py` | Standardized alert-burden, prevalence-sensitivity, and recall-under-review-budget tables (headline tier) | `matched_fpr_table.csv`, `headline_tier_decision.json` | `alert_budget_table.csv` |
| S9 | `publication_experiments/scripts/run_cross_consistency_check.py` | Executable cross-result checks (§17 Phase 7) | All artifacts + frozen references | `cross_check_report.json` (non-zero exit on any FAIL) |

### 5B. Inference Runs (all inside S1 unless noted)

| ID | Model | Population | Output | Required for |
|----|-------|------------|--------|--------------|
| INF-01 | DT, RF, SVM, NN, Meta ×3 | DEV_TEST (N = 81,749) | Score per row | Req 1.1, 1.3 |
| INF-02 | DT, RF, SVM, NN, Meta ×3 | Resolved clean benign calibration population | Calibration score per row | Seed-specific calibration |
| INF-03 | DT, RF, SVM, NN, Meta ×3 | ZERO_DAY_COMBINED (N = 37,583) | Score per row | Req 1.1–1.5 |
| INF-04 | AE (EXP_AE_V1) | DEV_TEST | Reconstruction error | AE ROC/PR |
| INF-05 | AE (EXP_AE_V1) | ZERO_DAY_COMBINED | Reconstruction error | AE ROC/PR, matched FPR |
| INF-06 | AE (EXP_AE_V1) | Resolved clean benign calibration population | Reconstruction error | AE threshold family, calibration |
| INF-07 | AE (EXP_AE_V1) | Unseen families (Worms 44, Shellcode 378, Analysis 677) | Reconstruction error | Req 2.2 per-family recall |
| INF-08 | (no new inference) | Tier-B `CAL_CONTROL` / `EVAL_CONTROL` (18,500 each) | Scores taken from the `benign_control` rows of INF-03 / INF-05 and split by the committed row-ID lists | Tier-B calibration / evaluation |

IF scoring on the same populations is performed by S7 (see §7).

### 5C. Training (New Models)

| ID | Model | Training population | Calibration population | Required for |
|----|-------|---------------------|------------------------|--------------|
| TRAIN-IF | Isolation Forest ×3 seeds | TRAIN benign only (44,800 rows, EXP_MI_V1_1 features) | Resolved clean benign calibration population | Req 2.1 |

### 5D. Calibration

| ID | Purpose | Input | Method | Required for |
|----|---------|-------|--------|--------------|
| CAL-FPR-A | Tier-A budget-matched thresholds for every model (DT, RF, SVM, NN, Stacking ×3, AE, IF ×3) | Scores on resolved clean benign calibration population | §0.1 order-statistic rule at 0.1/0.5/1/5%; seed-specific | Req 1.2, 1.5, 2.1 |
| CAL-FPR-B | Tier-B budget-matched thresholds for the same models | Scores on `CAL_CONTROL` only (18,500 rows) | Same §0.1 rule; seed-specific; evaluated on `EVAL_CONTROL` + Backdoor | Req 1.2, 1.5, 2.1 |
| CAL-AE-RULES | AE rule-based threshold family | S1-generated AE REs on resolved clean benign calibration population (validation REs when untouched VAL is eligible) | p95, p99, p999, mean+2σ, mean+3σ, raw MAD k=3 (primary); raw/scaled MAD k ∈ {2,3,4} (sensitivity) | Req 2.2 |
| CAL-IF-RULES | IF rule-based threshold family | IF scores on resolved clean benign calibration population | p95, p99, p999, mean+2σ, mean+3σ | Req 2.1 |

### 5E. Statistical Analysis

**STAT-EQUIV — conservative exact paired-equivalence test on the discordant proportion for RF with vs. without TTL features.**

- Population: Protected Backdoor, N = 583.
- Paired data: A = 582 (both detect), B = 0 (canonical only), C = 0 (no-TTL only), D = 1 (both miss).
- Null hypothesis (non-equivalence): the absolute paired difference in detection rate is at least δ. Alternative: it is smaller than δ.
- Formal margin: `δ = 0.01` (proportion; 1 percentage point), declared in `tost.yaml`.
- Separate materiality reference: 6/583 = 0.0102916. Recorded for context only; not substituted for δ.
- Conservative exact paired-equivalence procedure in §8.1.

### 5F. Documentation / Provenance

| ID | Item | Required for |
|----|------|--------------|
| DOC-01 | EXP_PROB_INFERENCE_V1 `metadata.json` (IDs, timestamps, hashes, features, population counts, row-identity hashes) | Req 4.1 |
| DOC-02 | EXP_IF_V1 `metadata.json` | Req 4.1 |
| DOC-03 | AE threshold-family provenance (`mad_threshold.json`) | Req 2.2, 4.1 |
| DOC-04 | TOST result JSON with declared margin and provenance | Req 2.3 |
| DOC-05 | README / evidence-ledger section for new experiments | Req 4.1 |
| DOC-06 | `docs/DOC_PREREGISTRATION_TIMING.md` — experiment/document timestamps, Git evidence, final wording decision | Req 4.2 |
| DOC-07 | `EXP_PHASE0_V1/phase0_discovery.json` and a short human decision log (VAL-overlap decision, DEV_TEST-usage decision, partition-provenance finding, unseen-family source, Tier-B eligibility) | Rules 12, 13, 15 |
| DOC-08 | `docs/DOC_SCOPE_DECISION.md` — recorded decision on a second dataset (default: out of scope for this revision), rationale, and the Limitations content required by M17 | Req 4.3 |

### 5G. Scientific Manuscript Corrections

See §20 for the complete list (M1–M17) with evidence prerequisites.

---

## 6. Coordinated Experiment Plan

### BATCH-A: EXP_PROB_INFERENCE_V1 — Single Coordinated Frozen-Inference Run (S1)

**Purpose:** Produce every score file needed downstream. Inference only: no fitting, no threshold selection, no parameter updates.

```
Populations (from populations.yaml):
  - DEV_TEST                 N = 81,749
  - CALIBRATION_BENIGN       N = N_cal     (resolved clean calibration source; source and filter from populations.yaml)
  - ZERO_DAY_COMBINED        N = 37,583   (583 Backdoor + 37,000 benign control; benign rows identified
                                           by the committed row-uid list, hash-verified)
  - UNSEEN_FAMILIES          Worms 44, Shellcode 378, Analysis 677 (source resolved in Phase 0)
  - (Tier B) CAL_CONTROL / EVAL_CONTROL   N = 18,500 / 18,500   (disjoint halves of the 37,000 benign control;
                                           scores are taken from ZERO_DAY_COMBINED, no extra inference)

Supervised models:
  DT, RF      : predict_proba[:,1]
  SVM         : decision_function()  (LinearSVC; raw score)
  NN          : sigmoid(logit)
  Meta (seeds 42/123/2024): predict_proba[:,1] on [dt, rf, svm_score, nn] in exact training order

AE (EXP_AE_V1 checkpoint + frozen AE scaler): reconstruction_error per row

Output files (results/publication_experiments/EXP_PROB_INFERENCE_V1/):
  dev_test_probabilities.csv
  calibration_benign_probabilities.csv
  zeroday_probabilities.csv
  ae_dev_test_reconstruction_errors.csv
  ae_calibration_benign_reconstruction_errors.csv
  ae_zeroday_reconstruction_errors.csv
  ae_unseen_family_reconstruction_errors.csv
  metadata.json
  self_check.json

Supervised columns:
  row_uid, label, attack_cat (where available), population_type,
  dt_attack_probability, rf_attack_probability, svm_decision_score, nn_attack_probability,
  stacking_attack_probability_seed42, stacking_attack_probability_seed123, stacking_attack_probability_seed2024

AE columns:
  row_uid, label, attack_cat, population_type, reconstruction_error
```

**Implementation constraints:**

- SVM uses `decision_function()` only (no `predict_proba`). SVM ROC/PR uses the raw score.
- Meta-feature order: `[dt_attack_probability, rf_attack_probability, svm_decision_score, nn_attack_probability]`, verified against `meta_learner.py`.
- Supervised scalers (SVM, NN) and the AE scaler are different objects; never mix them.
- No fit, no backward pass, no optimizer, no threshold tuning. The zero-training guard is mandatory.
- `self_check.json` (hard-fail on violation): row counts, no NaN/inf, probability ranges, row-uid hashes match `populations.yaml`, unseen-family counts equal 44/378/677.

### BATCH-C: EXP_IF_V1 — Isolation Forest (S7)

See §7. Runs after S1 because it consumes the same population manifest and row-identity lists. It writes per-row IF scores for every population so that S2 and S3 can treat IF exactly like every other model.

### BATCH-B: Analysis Scripts (read saved score files only)

**B1 — Matched-FPR (S3), all models, run after S1 and S7**

- Tier-A calibration input: the **resolved clean benign calibration score files** (supervised, AE, IF). The calibration source and actual `N_cal` are read from `populations.yaml`. Tier-A evaluation input: the held-out 37,000-row benign control and 583 Backdoor rows; AE and IF also on the unseen families.
- Tier-B calibration input: `CAL_CONTROL` scores only (N = 18,500). Tier-B evaluation input: `EVAL_CONTROL` + 583 Backdoor (`ZERO_DAY_EVAL_HALF`); AE and IF also on the unseen families. Row-ID lists and hashes come from `populations.yaml`.
- **Partition-shift diagnostic (Rule 15):** for every model, seed, and budget write `partition_shift_diagnostic.csv` with nominal budget, Tier-A calibration FPR, Tier-A realized control FPR, realized/nominal ratio, Clopper–Pearson 95% CI, and the `shift_affected` flag; also the two-sample Kolmogorov–Smirnov statistic between the calibration-benign score distribution and the control-benign score distribution (descriptive), and the default-threshold FPR on calibration vs. control for probability models (0.5) and for the frozen AE τ. Then apply the committed `headline_tier_rule` and write `headline_tier_decision.json`.
- Models: DT, RF, SVM, NN, Stacking (seeds 42/123/2024, each calibrated independently), AE, IF (seeds 42/123/2024, each calibrated independently).
- Budgets: 0.1%, 0.5%, 1%, 5%, using the §0.1 order-statistic rule with the actual resolved `N_cal`.
- Report (one row per model × seed × budget × `calibration_tier`): threshold, calibration FPR, held-out FPR (+ Clopper–Pearson 95% CI), FP, TP, recall (+ CI), **F2**, Backdoor detections, evaluation-population prevalence; F2 is computed at each of the same four budgets for every model. Report mean ± SD across seeds for Stacking and IF.
- Per-family recall for AE and IF only. Supervised models may have seen these families during training, so they are not zero-day for them.
- Optional **oracle** columns (thresholds picked on the evaluation control) are permitted only as a labelled sensitivity analysis.
- Calibration resolution warning: at 0.1%, `k = floor(0.001 × N_cal)` calibration rows determine the threshold. When `N_cal = 11,200`, `k = 11` (Tier B: `N_cal = 18,500`, `k = 18`); the realized held-out FPR can deviate from nominal through sampling noise, which is why CIs are mandatory, **and** through systematic partition shift, which is what the diagnostic above separates from noise.
- DEV_TEST Macro-F1 at matched-FPR thresholds is a Tier-A-only, descriptive reference (Tier-B calibration rows are part of DEV_TEST and therefore not held out there).

**B2 — ROC / PR / PR-AUC / F2 (S2), run after S3**

- For every model × applicable population: ROC curve, ROC-AUC, PR curve, and PR-AUC using `average_precision_score`.
- **F2 headline metric:** compute F2 at the same four matched-FPR budgets (0.1%, 0.5%, 1%, 5%) for **every model**, using the thresholds generated by S3 for the headline tier (§0 Rule 15). Default-threshold F2 (0.5 for probability models; 0.0 for the SVM decision score) is retained only as a reference metric and is not the cross-model headline.
- Argmax-F2 is oracle/test-tuned unless an independent labelled calibration set exists; label it accordingly and exclude it from headline claims.
- AUC/AP values are reported as computed; an AE AUC below 0.5 is retained as observed and is not clipped. **Headline ROC-AUC and PR-AUC are computed on `ZERO_DAY_COMBINED`** (threshold-free, tier-independent); PR-AUC/precision depend on prevalence, so the prevalence of each scored population is stated (zero-day: 583/37,583 ≈ 1.55%).
- **Curve aggregation:** do not pool predictions across seeds. Plot one ROC curve and one PR curve per seed for seeded models, or use seed 42 as the designated main curve with all seed curves retained in the artifact/supplement; report ROC-AUC and PR-AUC per seed plus mean ± SD. The aggregation rule is fixed before S2 execution.
- **Main figure:** a ROC panel and a directly adjacent PR panel for the zero-day population, showing AE, stacking, and IF curves with the headline tier's matched-FPR operating points marked (the other tier's points appear in a supplementary figure). The PR panel is required; a PR-AUC-only panel is insufficient.

**B3 — AE Threshold Family and Ablation (S5 → S6)**

- All six primary rules are computed from the **S1-generated AE reconstruction-error vector for the resolved clean calibration population**, using `ae_final.pt` + frozen AE scaler. When `source_status=untouched_val`, this is the regenerated EXP_AE_V1 validation RE vector. The legacy saved RE file is a cross-check only and is never the primary source. When both exist under the untouched-VAL branch, they must agree within the declared tolerance; the source file hash, checkpoint hash, scaler hash, and row-identity hash are recorded.
- Apply frozen thresholds to EXP_AE_V1 zero-day REs; report Backdoor, Worms, Shellcode, and Analysis recall, the achieved calibration FPR, and the achieved held-out control FPR.
- MAD with heavy-tailed errors can produce a low threshold and high FPR. Report the achieved FPR honestly and compare rules at matched FPR through S3, so the ablation does not merely show FPR changing.

**B4 — Alert Budget (S8), run after S3**

- Alerts per 100,000 and 1,000,000 benign flows for each achieved held-out FPR: `alerts = benign_flows × FPR`.
- FPR required for a review budget `B` alerts at `F` flows: `FPR = B / F` (formula only; `F` is a user-supplied scenario parameter).
- **Achievable recall under a review budget (Req 1.4):** for each scenario `(B alerts/day, F flows/day)` listed in `alert_budget.yaml`, compute `FPR* = B / F` and report each model's recall (with Clopper–Pearson CI, Backdoor zero-day population, headline tier) at the **largest common budget ≤ FPR\*** (no interpolation between calibrated budgets). If `FPR* < 0.1%`, report "below the smallest calibrated budget". All scenario values are user-supplied and labelled illustrative.
- PPV sensitivity: `PPV = R·π / (R·π + FPR·(1 − π))` for prevalence values π in a configured list that includes the observed zero-day prevalence 1.55%. The other values are labelled illustrative.
- No enterprise flows/day is inferred from the UNSW-NB15 lab capture.

**B5 — TOST (S4), independent**

- Exact procedure in §8.1; margin from committed `tost.yaml`.

---

## 7. Isolation Forest — Complete Implementation Specification

### Required by

Req 2.1: at least one additional unsupervised baseline.

### Scope

IF is evaluated on the same populations as the AE, in the same 75-feature EXP_MI_V1_1 space, using the frozen `EXP_AE_V1/ae_scaler.joblib`.

> **Critical protocol constraint:** IF is trained only on benign TRAIN rows. It must not use attack labels for training, threshold selection, or model fitting.

### Training population

- File: `data/splits/train.csv`, rows with `label == 0` only, N = 44,800.
- Features: EXP_MI_V1_1 (75 features), exact order from `selected_features.json`.
- Preprocessing: load the frozen AE scaler; do not fit a new one. (Tree-based splits are invariant to per-feature affine scaling, so this is for protocol parity and to avoid a second scaler artifact.) The scaler SHA-256 is recorded and asserted.

### Multi-seed configuration

Same fixed configuration for seeds 42, 123, 2024. No hyperparameter search.

| Parameter | Value |
|-----------|-------|
| `n_estimators` | 200 |
| `max_samples` | `"auto"` |
| `contamination` | `"auto"` |
| `max_features` | 1.0 |
| `n_jobs` | -1 |
| `random_state` | 42 / 123 / 2024 |

### Scoring and rule-based thresholds (per seed)

1. Score the resolved clean calibration benign population with `score_samples()`; negate so larger = more anomalous.
2. Rule-based thresholds on the resolved calibration benign distribution: p95, p99, p999, mean+2σ, mean+3σ (`numpy.percentile`, linear). Report the exact achieved calibration FPR of each. Do not claim Gaussian FPRs for the sigma rules.
3. Apply thresholds to DEV_TEST and to zero-day; report the achieved held-out control FPR.
4. Budget-matched thresholds (0.1/0.5/1/5%) are produced by S3 using the §0.1 rule on the same resolved calibration scores.
5. Summarize seeds as mean ± SD.

### Populations scored (all per seed, per row)

1. **Resolved clean calibration benign population** — calibration only.
2. **DEV_TEST (81,749)** — per-threshold predictions, Macro-F1, per-class metrics.
3. **ZERO_DAY_COMBINED (37,583)** — Backdoor detection and benign-control FPR; row identity taken from `populations.yaml`.
4. **Unseen families** — Worms 44, Shellcode 378, Analysis 677 (source resolved in Phase 0; counts asserted).

### Artifacts to produce

| Artifact | Path | Contents |
|----------|------|----------|
| IF model checkpoints | `results/checkpoints/EXP_IF_V1/seed_{42,123,2024}/if_model.joblib` | Fitted IF per seed |
| Scaler reference | `results/checkpoints/EXP_IF_V1/ae_scaler_reference.json` | Source path and SHA-256 of the frozen AE scaler |
| Checkpoint metadata | `results/checkpoints/EXP_IF_V1/metadata.json` | Seeds, n_estimators, training rows, feature set, scaler hash, git commit |
| Calibration scores | `results/publication_experiments/EXP_IF_V1/scores/calibration_benign_scores.csv` | source-prefixed row_uid, seed, anomaly_score from the resolved clean calibration population |
| DEV_TEST scores | `results/publication_experiments/EXP_IF_V1/scores/dev_test_scores.csv` | row_uid, label, attack_cat, seed, anomaly_score |
| Zero-day scores | `results/publication_experiments/EXP_IF_V1/scores/zeroday_scores.csv` | row_uid, label, population_type, seed, anomaly_score |
| Unseen-family scores | `results/publication_experiments/EXP_IF_V1/scores/unseen_family_scores.csv` | row_uid, attack_cat, seed, anomaly_score |
| Rule-based thresholds | `results/publication_experiments/EXP_IF_V1/threshold/threshold_sweep.csv` | rule, threshold, val_fpr, seed |
| DEV_TEST predictions and metrics | `results/publication_experiments/EXP_IF_V1/dev_test/dev_test_predictions.csv`, `dev_test_metrics.json` | Per-rule flags; TP/FP/TN/FN, Macro-F1, FPR per seed and rule |
| Zero-day and family detection | `results/publication_experiments/EXP_IF_V1/zero_day/backdoor_detection.csv`, `unseen_family_detection.csv` | Per-rule detection rates and held-out control FPR |
| Seed summary | `results/publication_experiments/EXP_IF_V1/summary/if_summary_mean_sd.csv` | Mean ± SD across seeds |
| Metadata | `results/publication_experiments/EXP_IF_V1/metadata.json` | Seeds, feature count, training rows, population hashes, scaler hash, timestamps |

The cross-model comparison (AE vs IF vs stacking at common budgets) is produced by S3, not S7, so all models go through one identical code path.

---

## 8. Statistical Testing — Complete Specification

### 8.1 Conservative exact paired-equivalence test on the discordant proportion for RF (Req 2.3)

**Question:** Is the RF zero-day Backdoor detection rate equivalent with and without TTL features (canonical 75-feature vs. 72-feature no-TTL representation)?

**Population:** Protected Backdoor, N = 583.

**Paired data:** A = 582 (both detect), B = 0 (canonical only), C = 0 (no-TTL only), D = 1 (both miss). Hence p_canonical = p_no_ttl = 582/583 = 0.998285 and the observed paired difference is exactly 0.

**Why McNemar alone is inconclusive:** with B = C = 0 there is no observed discordance, so McNemar cannot support or refute a difference. An equivalence analysis can still ask whether finite-sample uncertainty is small enough to stay inside a declared margin.

### Paired-input provenance

S4 must prefer the actual per-row RF prediction files for the protected Backdoor population. It constructs a paired table keyed by the **source-prefixed row ID** and derives:

- `A`: both canonical and no-TTL models alert,
- `B`: canonical only,
- `C`: no-TTL only,
- `D`: neither alerts.

S4 asserts that the paired row-ID set is exactly the committed 583-row Backdoor population and that `A + B + C + D = 583`. If per-row paired RF predictions are genuinely unavailable, S4 may consume the existing aggregate contingency as a fallback, but must record the fallback source, its artifact hash, and the same 583-row total. An aggregate table is never accepted without this identity/total validation.

**Conservative exact procedure**

1. Read the margin δ from the committed `tost.yaml` (`0.01`, a proportion). It must have been committed before S4 runs.
2. Let `q = (B + C) / N` be the discordant-pair proportion. For paired binary outcomes, `abs(d) ≤ q`, where d is the paired difference in detection rates.
3. Test H0: `q ≥ δ` against H1: `q < δ` with the exact binomial test on the discordant count `X = B + C` ~ Binomial(N, q). The one-sided p-value is `P(X ≤ B + C | N, q = δ)`; for B = C = 0 this is `(1 − δ)^N = 0.99^583 ≈ 0.0029`. Rejecting H0 implies `abs(d) < δ`, which is sufficient to reject both one-sided non-equivalence conditions (`d ≥ δ` and `d ≤ −δ`). The procedure is conservative and sufficient for paired equivalence. Report the result as the conservative exact paired-equivalence p-value; do not describe it as a textbook two-test TOST implementation.
4. α = 0.05. Report the one-sided exact 95% Clopper–Pearson upper bound on q (about 0.51% for 0/583) and, for information, the two-sided exact 95% interval (about [0, 0.63%]). The equivalence decision uses the one-sided bound (equivalently, the 90% two-sided interval). Equivalence is supported iff that upper bound is below δ.
5. Do not use Wilson or normal-approximation intervals.

**Required limitations statement in the manuscript**

- The margin δ = 1 percentage point was specified after the paired counts were observed; it is a post-hoc margin, not a pre-registered one.
- The Backdoor detection rate is saturated (≈ 99.8%), so a 1 pp margin is easy to satisfy. The result establishes equivalence of Backdoor recall only; it says nothing about DEV_TEST behavior or other families.
- Zero discordant pairs give a zero observed difference but do not prove identical population behavior.

**Optional secondary check (only if paired RF ± TTL DEV_TEST predictions already exist):** a paired bootstrap 95% CI for the Macro-F1 difference, reported descriptively. Not required for compliance.

**Output artifact:** `results/publication_experiments/EXP_TOST_V1/tost_rf_equivalence.json`

```json
{
  "experiment_id": "EXP_TOST_V1",
  "model": "RF",
  "comparison": "75-feature (canonical) vs 72-feature (no-TTL)",
  "population": "protected_backdoor N=583",
  "equivalence_margin": 0.01,
  "margin_units": "proportion",
  "margin_status": "specified after paired counts were observed (post-hoc); committed before S4 execution",
  "materiality_reference_detections": 6,
  "materiality_reference_rate": 0.0102916,
  "A": 582, "B": 0, "C": 0, "D": 1,
  "p_canonical": 0.998285,
  "p_no_ttl": 0.998285,
  "observed_delta": 0.0,
  "discordant_proportion_q_hat": 0.0,
  "alpha": 0.05,
  "conservative_exact_p_value": "<computed>",
  "q_upper_bound_one_sided_cp95": "<computed>",
  "q_interval_two_sided_cp95": ["<computed>", "<computed>"],
  "equivalence_conclusion": "<computed from exact test>",
  "limitation": "Zero discordant pairs; margin specified post-hoc; Backdoor recall only.",
  "timestamp_utc": "<runtime>"
}
```

### 8.2 Existing Statistical Evidence (No New Analysis Required)

| Test | Result | Location | Status |
|------|--------|----------|--------|
| McNemar DT | p=0.219 (N.S.) | `mcnemar_results.csv` | Done — reportable |
| McNemar SVM | p=0.0127 raw, p=0.0636 Holm | `mcnemar_results.csv` | Done — reportable |
| McNemar NN | p=0.070 raw, p=0.281 Holm | `mcnemar_results.csv` | Done — reportable |
| McNemar Stacking | p=0.500, Holm=1.0 | `mcnemar_results.csv` | Done — reportable |
| Worms CP 95% CI | [0.00%, 8.04%] | `ae_primary_summary.csv` | Done — needs manuscript reporting |
| Backdoor CP 95% CI | [99.05%, 100.00%] | `confidence_intervals/stage_b_confidence_intervals.csv` | Done |
| H1 stacking > RF | diff=0.0122 > ε=0.005 | `h1_results.json` | Done |

> Any final manuscript p-value or equivalence statement must be copied from the generated artifact, not hardcoded into the blueprint.

---

## 9. Worms / Rare-Class CI Evidence

### Current state

- Worms CI upper bound 8.04% exists in `ae_primary_summary.csv`
- Present in §V.D (Results) and §VII (Limitations)
- **Absent from Abstract and Conclusion**

### What is required

**Req 2.4:** Report CI consistently in Abstract/Conclusion.

**New computation required:** None. The value is already computed.

**Manuscript action:**
1. In **Abstract**: Replace or augment "the same null recall across three additional unseen attack families (Worms, Shellcode, Analysis)" with "0/44 Worms (95% upper bound: 8.04%), 0/378 Shellcode (95% upper bound: 0.97%), 0/677 Analysis (95% upper bound: 0.54%)"
2. In **Conclusion §VIII**: Add one sentence reporting Worms 8.04% CI alongside the other family zero-recall results.

**Evidence prerequisite:** `ae_primary_summary.csv` — already verified.

---

## 10. Preregistration / Materiality — Complete Specification

### What exists

| Artifact | Observed timestamp | Interpretation |
|----------|--------------------|----------------|
| `preregistered_decisions.json` | 2026-09-04 | Exists and is associated with EXP_ZERODAY_V1. **Do not call it authentic/pre-registered without version-control evidence showing its contents/criterion existed before the relevant results.** |
| `materiality_preregistration.json` | 2026-09-08T16:47:34 UTC | Post-hoc relative to stacking experiment on 2026-09-01; must not be described as a pre-registration of that experiment |

### Required terminology

Use **"predeclared"** only for criteria that can be demonstrated, from Git history or contemporaneous records, to have preceded the relevant result generation.

Use **"post-hoc" / "specified after the run"** for the materiality document created on 2026-09-08.

### Required evidence check

Before manuscript wording is finalized:

1. Run `git log --stat` / `git log --follow` for the relevant JSON files and the code/config defining the H2 criteria.
2. Record the earliest commit timestamp containing the actual criterion, not merely the file name or current file timestamp.
3. Compare that timestamp with the start/result timestamp of the relevant experiment.
4. Only then decide whether the criterion can be called predeclared.

### Recommended manuscript language

> "Decision criteria are described as predeclared only where contemporaneous experiment records or version-control history demonstrate that they preceded the relevant result. The Stage-D materiality document (`PREREG_STAGE_D_MATERIALITY_V1`) was created on 2026-09-08, after the 2026-09-01 stacking run; accordingly, that materiality specification is reported transparently as post-hoc rather than as a preregistration."

### Do NOT

- Alter timestamps.
- Backdate files.
- Claim the materiality thresholds were defined before results if the evidence does not show that.
- Use "pre-registered" as a synonym for "documented later."

### Required artifact

`docs/DOC_PREREGISTRATION_TIMING.md` must contain the experiment timestamp, file/commit evidence, interpretation, and final wording decision.

---

## 11. Architecture Discrepancy — Resolution

### Evidence

| Source | Architecture | Output |
|--------|-------------|--------|
| Submitted paper §III.E | `75 → 128 → 64 → 2` | "2 output classes" (implied softmax) |
| `nn_architecture.json` checkpoint | `input_dim=75, hidden_sizes=[128,64]` | No output dimension specified |
| `nn_metadata.json` checkpoint | `output_contract: "predict + sigmoid probability in [0,1]"` | **Single sigmoid output** |
| `neural_network.py` source | `layers.append(nn.Linear(prev, 1))` | **1 output node** |

### Resolution

The NN implements **binary classification with a single sigmoid output** (`75 → 128 → 64 → 1`), not a 2-class softmax head. The manuscript description must therefore be corrected.

**This is not a different model or a different experiment — it is the same model with a wrong description in the manuscript.**

**Manuscript correction:**

Replace: "PyTorch MLP with architecture 75 → 128 → 64 → 2, ReLU activations"  
With: "PyTorch MLP with architecture 75 → 128 → 64 → 1, ReLU activations in hidden layers and sigmoid activation on the output (binary cross-entropy loss), trained with AdamW"

**Evidence prerequisite:** `nn_architecture.json`, `nn_metadata.json` — already verified. No new experiments needed.

---

## 12. AE Sample-Count Discrepancy — Resolution

### Evidence

| Source | Number | Context |
|--------|--------|---------|
| Paper §III.F | "40,320 normal flows from TRAIN" | How it reads: all training data |
| `ae_metadata.json` | `training_rows: 40320, monitor_rows: 4480, normal_train_total: 44800` | Early-stopping phase |
| `ae_trainer.py` docstring | "Final refit: Train on ALL 44,800 Normal TRAIN rows for best_epoch epochs" | Final refit |

### Resolution

Both numbers correspond to different training stages:
- 40,320 rows: early-stopping training subset (90% of 44,800 benign)
- 44,800 rows: final refit (all benign TRAIN rows)
- The submitted checkpoint (`ae_final.pt`) was produced by the **final refit on 44,800 rows** at `best_epoch=133`

The paper statement "40,320 normal flows" describes only the early-stopping phase. The deployed model was trained on 44,800. The paper is technically incomplete (not wrong — 40,320 was used to find best_epoch, and the final model then trained on all 44,800).

**Manuscript correction:**

Replace: "trained exclusively on 40,320 normal flows from TRAIN"  
With: "trained using a 40,320/4,480 early-stopping split to determine optimal epoch (133 epochs), then refitted on all 44,800 Normal TRAIN flows for the final model checkpoint"

**Evidence prerequisite:** `ae_metadata.json` — already verified.

---

## 13. Requirement-to-Implementation Matrix

| Req | Status | What is missing | Path | Key artifacts | Gates | Manuscript |
|-----|--------|-----------------|------|---------------|-------|------------|
| 1.1 | MISSING | ROC/PR curves for stacking, with full AE and IF curves overlaid | S1 → S7 → S3 → S2 | ROC/PR CSVs, overlaid figure | 3, 4, 6 | New figure, §V.F |
| 1.2 | MISSING | Stacking zero-day recall at 0.1/0.5/1/5% FPR (two-tier: VAL-calibrated and control-split-calibrated, held-out) | S1 → S7 → S3 | `matched_fpr_table.csv` | 3, 4 | New table, §V.F |
| 1.3 | MISSING | PR-AUC and F2 for all models incl. AE and IF | S1 → S7 → S3 → S2 | `prauc_summary.json`, `f2_summary.json` | 4, 6 | Table II |
| 1.4 | MISSING | Alert-budget framing | S3 → S8 | `alert_budget_table.csv` | 4, 6 | §VI.D |
| 1.5 | PARTIAL | Explicit distinction between the uncalibrated 0.5 threshold and constrained-FPR operating points, with held-out evidence | S3 | `matched_fpr_table.csv` | 4, 6 | §V.F, §VI |
| 1.6 | MISSING | Result-contingent conclusion | After S3/S2/S7 | — | 8 | §VIII |
| 2.1 | MISSING | Isolation Forest baseline (3 seeds) | S1 → S7 → S3 → S2 | EXP_IF_V1, cross-model table | 2, 3, 4 | §III.D, §V.E |
| 2.2 | PARTIAL | Canonical EXP_AE_V1 threshold family, MAD, per-family recall | S1 → S5 → S6 | `mad_threshold.json`, `ae_threshold_ablation_table.csv` | 4, 6 | §V.D table |
| 2.3 | MISSING | Conservative exact paired-equivalence test | S4 | `tost_rf_equivalence.json` | 5 | §III.F, §V.C |
| 2.4 | PARTIAL | Worms CI in Abstract and Conclusion | Manuscript | — | 6, 8 | Abstract, §VIII |
| 3.1 | MISSING | Academic register | After all evidence | — | 8 | §V, §VI |
| 3.2 | MISSING | Move Eq. (5) | Manuscript | — | 8 | §VI.A.2 |
| 3.3 | MISSING | Author affiliation format | Manuscript, after venue selection | — | 8 | Author block |
| 3.4 | MISSING | Email typo | Manuscript | — | 8 | gamil → gmail |
| 3.5 | PARTIAL | Rebuild Tables II–IV | After final data and venue selection | — | 8 | Tables |
| 4.1 | MISSING | Code/data availability statement | After all experiments | README, DOC-05 | 9 | Availability section |
| 4.2 | PARTIAL | Evidence-backed "predeclared" vs. post-hoc wording; supplementary document | S0 → DOC-06 | `DOC_PREREGISTRATION_TIMING.md` | 7 | Table III, §III |
| 4.3 | PARTIAL | Recorded scope decision (`DOC_SCOPE_DECISION.md`: second dataset out of scope for this revision unless the author overrides) + strengthened Limitations | Phase 8 (DOC-08) → Phase 9 | `DOC_SCOPE_DECISION.md` | 8 | §VII (M17) |

---

## 14. Master Experiment Inventory

| Exp ID | Type | Purpose | Models | Train? | Infer? | Consumed by |
|--------|------|---------|--------|--------|--------|-------------|
| EXP_PHASE0_V1 | Discovery (read-only w.r.t. frozen artifacts) | Resolve populations, VAL/DEV_TEST-usage audits, partition provenance, Tier-B split lists, Git evidence | — | NO | NO | Populations manifest, DOC-06 |
| EXP_PROB_INFERENCE_V1 | Frozen inference | Supervised scores and AE reconstruction errors | DT, RF, SVM, NN, Meta ×3, AE | NO | YES | S2, S3, S5, S6, S9 |
| EXP_IF_V1 | Training + inference | Isolation Forest baseline, 3 seeds | IF ×3 | YES | YES | S2, S3, S9 |
| EXP_TOST_V1 | Analysis | Conservative exact paired-equivalence test for RF ± TTL | RF | NO | NO | Req 2.3 |
| EXP_MAD_THRESHOLD_V1 | Calibration | AE threshold family + MAD | AE | NO | NO | S6 |
| EXP_AE_ABLATION_V1 | Analysis | Unified AE ablation table | AE | NO | NO | Req 2.2 |
| EXP_MATCHED_FPR_V1 | Analysis | two-tier (Tier A VAL-calibrated, Tier B control-split-calibrated) held-out matched-FPR for all models; shift diagnostic; alert budget | All models | NO | NO | Req 1.2, 1.4, 1.5, 2.1 |
| EXP_ROC_PR_V1 | Analysis | ROC, PR, PR-AUC, F2 | All models | NO | NO | Req 1.1, 1.3 |
| EXP_CROSSCHECK_V1 | Validation | Executable consistency checks (S9) | — | NO | NO | Gate 6, Phase 7 |

---

## 15. Master Artifact Inventory

### Existing Artifacts (Reusable)

| Artifact | Path | Status | Used For |
|----------|------|--------|---------|
| DT checkpoint | `results/checkpoints/EXP_BASE_MODELS_V1/dt/dt_final.joblib` | EXISTS, hash-verified | EXP_PROB_INFERENCE_V1 |
| RF checkpoint | `results/checkpoints/EXP_BASE_MODELS_V1/rf/rf_final.joblib` | EXISTS, hash-verified | EXP_PROB_INFERENCE_V1 |
| SVM checkpoint | `results/checkpoints/EXP_BASE_MODELS_V1/svm/svm_final.joblib` | EXISTS, hash-verified | EXP_PROB_INFERENCE_V1 |
| SVM scaler | `results/checkpoints/EXP_BASE_MODELS_V1/svm/svm_scaler.joblib` | EXISTS, hash-verified | EXP_PROB_INFERENCE_V1 |
| NN checkpoint | `results/checkpoints/EXP_BASE_MODELS_V1/nn/nn_final.pt` | EXISTS, hash-verified | EXP_PROB_INFERENCE_V1 |
| NN scaler | `results/checkpoints/EXP_BASE_MODELS_V1/nn/nn_scaler.joblib` | EXISTS, hash-verified | EXP_PROB_INFERENCE_V1 |
| Meta-learner seed 42 | `results/checkpoints/EXP_OOF_STACK_V1/seed_42/meta_learner.joblib` | EXISTS, hash-verified | EXP_PROB_INFERENCE_V1 |
| Meta-learner seed 123 | `results/checkpoints/EXP_OOF_STACK_V1/seed_123/meta_learner.joblib` | EXISTS, hash-verified | EXP_PROB_INFERENCE_V1 |
| Meta-learner seed 2024 | `results/checkpoints/EXP_OOF_STACK_V1/seed_2024/meta_learner.joblib` | EXISTS, hash-verified | EXP_PROB_INFERENCE_V1 |
| AE checkpoint | `results/checkpoints/EXP_AE_V1/ae_final.pt` | EXISTS, hash-verified | Frozen inference for DEV_TEST/VAL/zero-day reconstruction-error dumps; no retraining |
| AE scaler | `results/checkpoints/EXP_AE_V1/ae_scaler.joblib` | EXISTS | EXP_AE_V1 inference + EXP_IF_V1 (reused frozen scaler) |
| AE threshold config | `results/checkpoints/EXP_AE_V1/threshold_config.json` | EXISTS | EXP_MAD_THRESHOLD_V1 |
| DEV_TEST split | `data/splits/development_test.csv` | EXISTS, SHA verified | EXP_PROB_INFERENCE_V1, EXP_IF_V1 |
| TRAIN split | `data/splits/train.csv` | EXISTS, SHA verified | EXP_IF_V1 |
| VAL split | `data/splits/validation.csv` | EXISTS, SHA verified | EXP_IF_V1 |
| Protected backdoor | `data/splits/protected_unseen_attack.csv` | EXISTS, SHA verified | EXP_PROB_INFERENCE_V1, EXP_IF_V1 |
| Feature list | `results/feature_selection/EXP_MI_V1_1/selected_features.json` | EXISTS | All inference experiments |
| AE threshold sweep (seed 42, unseen-family re-run) | `results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1/threshold/seed_42/threshold_sweep.csv` | EXISTS | Cross-check only; not the final canonical ablation source |
| AE detection sweep | `results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1/` | EXISTS (verify specific file) | Cross-check only |
| Secondary threshold FPR matrix | `results/publication_experiments/EXP_STATS_ROBUSTNESS_V1/threshold_tradeoff/secondary_threshold_fpr_matrix.csv` | EXISTS | Req 1.5, AE comparison in matched-FPR |
| McNemar results CSV | `results/publication_experiments/EXP_STATS_ROBUSTNESS_V1/paired_tests/mcnemar_results.csv` | EXISTS | EXP_TOST_V1 input |
| Worms CI summary | `results/publication_experiments/EXP_INTEGRATED_PUBLICATION_V1/integrated_statistics/ae_primary_summary.csv` | EXISTS | Req 2.4 manuscript |
| Val reconstruction errors | `results/autoencoder/EXP_AE_V1/threshold/validation_reconstruction_errors.csv` | VERIFY / CROSS-CHECK ONLY | S1 regenerates canonical validation REs from `ae_final.pt`; this legacy file is never the primary source |
| H1 results | `results/evaluation/EXP_H123_V1/h1_results.json` | EXISTS | Stacking Macro-F1 (0.8930 mean) provenance |

### New Artifacts to Create

| Artifact | Path | Producer | Contents | Validation |
|----------|------|----------|----------|------------|
| Phase-0 discovery | `results/publication_experiments/EXP_PHASE0_V1/phase0_discovery.json` | S0 | Hashes, unseen-family source, VAL-usage audit, benign-control row-uid list + hash, AE VAL RE source, Git evidence | Gate 1 |
| Population manifest | `publication_experiments/configs/populations.yaml` | Manual (from S0) | Paths, expected counts, row-uid lists and SHA-256 (incl. Tier-B `CAL_CONTROL`/`EVAL_CONTROL`, `split_seed`) | Gate 1 |
| DEV_TEST scores | `results/publication_experiments/EXP_PROB_INFERENCE_V1/dev_test_probabilities.csv` | S1 | N = 81,749 rows × 7 supervised score columns | Gate 3, 4 |
| Calibration benign scores | `.../EXP_PROB_INFERENCE_V1/calibration_benign_probabilities.csv` | S1 | N = `N_cal` rows from the resolved calibration manifest | Gate 3 |
| Zero-day scores | `.../EXP_PROB_INFERENCE_V1/zeroday_probabilities.csv` | S1 | N = 37,583 rows (583 + 37,000) | Gate 3, 4 |
| AE DEV_TEST REs | `.../EXP_PROB_INFERENCE_V1/ae_dev_test_reconstruction_errors.csv` | S1 | N = 81,749 | Gate 3 |
| AE calibration REs | `.../EXP_PROB_INFERENCE_V1/ae_calibration_benign_reconstruction_errors.csv` | S1 | N = `N_cal` from the resolved calibration manifest | Gate 3, 4 |
| AE zero-day REs | `.../EXP_PROB_INFERENCE_V1/ae_zeroday_reconstruction_errors.csv` | S1 | N = 37,583 | Gate 3 |
| AE unseen-family REs | `.../EXP_PROB_INFERENCE_V1/ae_unseen_family_reconstruction_errors.csv` | S1 | Worms 44, Shellcode 378, Analysis 677 | Gate 3 |
| Inference metadata and self-check | `.../EXP_PROB_INFERENCE_V1/metadata.json`, `self_check.json` | S1 | Hashes, seeds, counts, checks | Gate 7 |
| IF models, scores, summaries | `results/checkpoints/EXP_IF_V1/…`, `results/publication_experiments/EXP_IF_V1/…` | S7 | See §7 | Gate 2, 3, 4, 7 |
| Matched-FPR table | `results/publication_experiments/EXP_MATCHED_FPR_V1/matched_fpr_table.csv` | S3 | All models × 4 budgets × 2 tiers (`calibration_tier` column): threshold, calibration FPR, held-out FPR + CI, recall + CI, F2, prevalence, detections | Gate 4, 6 |
| Cross-model comparison | `.../EXP_MATCHED_FPR_V1/cross_model_comparison.csv` | S3 | Stacking vs AE vs IF (mean ± SD where seeded) at common budgets, incl. unseen-family recall for AE/IF | Gate 6 |
| Alert budget table | `.../EXP_MATCHED_FPR_V1/alert_budget_table.csv` | S8 | Alerts per 100k/1M benign flows, review-budget formula, PPV sensitivity, recall (+ CI) per review scenario (headline tier) | Gate 4, 6 |
| Partition-shift diagnostic | `.../EXP_MATCHED_FPR_V1/partition_shift_diagnostic.csv` | S3 | Per model/seed/budget: nominal vs realized FPR, ratio, CP CI, `shift_affected`, KS statistic | Gate 4, 6 |
| Headline-tier decision | `.../EXP_MATCHED_FPR_V1/headline_tier_decision.json` | S3 | Tier chosen by the committed rule, rule-text hash, list of shift-affected cells | Gate 4, 6 |
| ROC data | `results/publication_experiments/EXP_ROC_PR_V1/roc/roc_{model}_{pop}.csv` | S2 | fpr, tpr, thresholds | Gate 4 |
| PR data | `.../EXP_ROC_PR_V1/pr/pr_{model}_{pop}.csv` | S2 | precision, recall, thresholds | Gate 4 |
| PR-AUC and F2 summaries | `.../EXP_ROC_PR_V1/prauc_summary.json`, `f2_summary.json` | S2 | Per model × population; PR-AUC = average precision; F2 at all four common matched-FPR budgets plus reference-only default F2 | Gate 4, 6 |
| Main figure | `.../EXP_ROC_PR_V1/figures/roc_pr_ae_if_stacking_zeroday.pdf` | S2 | Explicit ROC panel + explicit PR panel, with matched-FPR operating points; no seed pooling | Visual inspection, source traceability |
| Equivalence result | `results/publication_experiments/EXP_TOST_V1/tost_rf_equivalence.json` | S4 | Conservative exact paired-equivalence result | Gate 5 |
| AE threshold family | `results/publication_experiments/EXP_MAD_THRESHOLD_V1/mad_threshold.json` | S5 | Six primary rules, MAD sensitivity, achieved calibration FPR, source hash | Gate 4 |
| AE ablation table | `results/publication_experiments/EXP_AE_ABLATION_V1/ae_threshold_ablation_table.csv` | S6 | Rule × family × achieved calibration/held-out FPR × recall | Gate 6 |
| Cross-check report | `results/publication_experiments/EXP_CROSSCHECK_V1/cross_check_report.json` | S9 | PASS/FAIL per check | Gate 6 |
| Preregistration timing doc | `docs/DOC_PREREGISTRATION_TIMING.md` | Manual (from S0 evidence) | Timestamps, Git evidence, wording decision | Gate 7 |
| Scope decision doc | `docs/DOC_SCOPE_DECISION.md` | Manual | Second-dataset decision, rationale, Limitations content | Gate 8 |
| Environment lock | `requirements-lock.txt` (or equivalent) | Commit before final rerun | Exact Python/package environment for reproduction | Gate 9 |

---

## 16. Exact File-Level Change Plan

All scripts use `--config <yaml>` only. Every config below is committed to Git **before** its script is run (Rule 14). All scripts import the zero-training guard (`src.utils.zero_training_guard`, or replicate `scan_ml_patterns`), except S7, which is the only script allowed to call `fit` and only on the IF model.

### Configs

**`publication_experiments/configs/populations.yaml`** (shared by S1, S3, S6, S7, S9)

```yaml
populations:
  dev_test:
    path: data/splits/development_test.csv
    expected_n: 81749
    sha256: 04725e85732ab2fc6d9eaaa6105418b22b083b5c651067e7b0785464f414e508
  calibration_benign:
    path: null                     # resolved by S0: full untouched VAL benign OR documented clean calibration source
    filter: {label: 0}
    expected_n: null               # populated by S0; never hardcode when the clean calibration source changes
    source_status: null            # untouched_val / alternate_clean_source / contaminated_sensitivity_only
    row_uid_list: null
    row_uid_list_sha256: null
  zero_day:
    backdoor:
      path: data/splits/protected_unseen_attack.csv
      expected_n: 583
      sha256: 6ffd23479b575e438ad90678268f40f674a663c2b9507aaf65089623397a9d91
    benign_control:
      source_csv: data/splits/development_test.csv
      row_uid_list: null          # RESOLVE IN PHASE 0 (S0). S1/S7/S3 refuse to run while null.
      row_uid_list_sha256: null   # RESOLVE IN PHASE 0.
      expected_n: 37000
      tier_b_split:
        split_seed: 20260928        # declared here; skeleton committed BEFORE S0 generates the lists
        method: "numpy.random.default_rng(split_seed) permutation of the 37,000 source-prefixed row IDs; first 18,500 = cal_control, rest = eval_control"
        cal_control:  {row_uid_list: null, row_uid_list_sha256: null, expected_n: 18500}   # RESOLVED BY S0
        eval_control: {row_uid_list: null, row_uid_list_sha256: null, expected_n: 18500}   # RESOLVED BY S0
  unseen_families:
    source: null                  # RESOLVE IN PHASE 0 (file and filter). Refuse to run while null.
    attack_cat_col: attack_cat
    expected_counts: {Worms: 44, Shellcode: 378, Analysis: 677}
row_uid_definition: "source-prefixed stable row ID: <source_split>:<existing row_uid>; if source row_uid is absent, <source_split>:<zero-based row index>. IDs must be unique within every population."
overlap_policy:
  benign_control_is_subset_of_dev_test: true   # intentional; exact subset identity must be asserted
  tier_b_halves: {disjoint: true, union_equals_benign_control: true}
  forbidden_overlaps:
    - [train, calibration_benign]
    - [train, dev_test]
    - [train, backdoor]
    - [calibration_benign, dev_test]
    - [calibration_benign, backdoor]
    - [dev_test, backdoor]
    - [backdoor, unseen_families]
    - [cal_control, eval_control]
    - [cal_control, backdoor]
  unseen_family_overlap_with_dev_test: "resolve and document in Phase 0; do not assume disjointness"

```

**`publication_experiments/configs/prob_inference.yaml`**

```yaml
experiment_id: EXP_PROB_INFERENCE_V1
populations_manifest: publication_experiments/configs/populations.yaml
seeds: [42, 123, 2024]
checkpoints:
  dt: results/checkpoints/EXP_BASE_MODELS_V1/dt/dt_final.joblib
  rf: results/checkpoints/EXP_BASE_MODELS_V1/rf/rf_final.joblib
  svm: results/checkpoints/EXP_BASE_MODELS_V1/svm/svm_final.joblib
  svm_scaler: results/checkpoints/EXP_BASE_MODELS_V1/svm/svm_scaler.joblib
  nn: results/checkpoints/EXP_BASE_MODELS_V1/nn/nn_final.pt
  nn_scaler: results/checkpoints/EXP_BASE_MODELS_V1/nn/nn_scaler.joblib
  ae: results/checkpoints/EXP_AE_V1/ae_final.pt
  ae_scaler: results/checkpoints/EXP_AE_V1/ae_scaler.joblib
  meta_seed_42: results/checkpoints/EXP_OOF_STACK_V1/seed_42/meta_learner.joblib
  meta_seed_123: results/checkpoints/EXP_OOF_STACK_V1/seed_123/meta_learner.joblib
  meta_seed_2024: results/checkpoints/EXP_OOF_STACK_V1/seed_2024/meta_learner.joblib
features: results/feature_selection/EXP_MI_V1_1/selected_features.json
output_dir: results/publication_experiments/EXP_PROB_INFERENCE_V1
calibration_source: populations.calibration_benign
calibration_n_from_manifest: true
prohibited: [fit, fit_transform, backward, model.train, optim]
```

**`publication_experiments/configs/matched_fpr.yaml`**

```yaml
experiment_id: EXP_MATCHED_FPR_V1
populations_manifest: publication_experiments/configs/populations.yaml
score_dirs:
  supervised_and_ae: results/publication_experiments/EXP_PROB_INFERENCE_V1
  isolation_forest: results/publication_experiments/EXP_IF_V1/scores
budgets: [0.001, 0.005, 0.010, 0.050]
rule: order_statistic_strict_greater   # §0.1
k_computation: exact_arithmetic        # §0.1; S3 asserts against a Fraction-based reference
calibration_tiers:
  A: {calibration: populations.calibration_benign, evaluation: [zero_day.benign_control, zero_day.backdoor]}
  B: {calibration: populations.zero_day.benign_control.tier_b_split.cal_control,
      evaluation: [populations.zero_day.benign_control.tier_b_split.eval_control, zero_day.backdoor]}
shift_diagnostic: true
headline_tier_rule: >
  A (model, seed, budget) cell is shift_affected if the nominal budget lies outside the Clopper-Pearson 95% CI of the
  realized Tier-A held-out control FPR. If no cell is shift_affected, Tier A is the headline tier and Tier B is a
  robustness table. If any cell is shift_affected, Tier B is the headline tier for all matched-FPR recall/F2 claims and
  Tier A is reported as the partition-shifted operating point. Tiers are never mixed within one comparison table.
  (Identical to Rule 15; committed before S3 runs.)
models: [dt, rf, svm, nn, stacking, ae, if]
seeded_models: {stacking: [42, 123, 2024], if: [42, 123, 2024]}
include_oracle_columns: true           # labelled sensitivity analysis only
ci_method: clopper_pearson
ci_level: 0.95
output_dir: results/publication_experiments/EXP_MATCHED_FPR_V1
```

**`publication_experiments/configs/tost.yaml`**

```yaml
experiment_id: EXP_TOST_V1
model: RF
paired_predictions_input: null   # preferred: canonical/no-TTL per-row RF predictions for protected Backdoor; resolved in Phase 0 if available
aggregate_fallback_input: results/publication_experiments/EXP_STATS_ROBUSTNESS_V1/paired_tests/mcnemar_results.csv
population: protected_backdoor
expected_n: 583
equivalence_margin: 0.01        # proportion = 1 percentage point
margin_units: proportion
alpha: 0.05
margin_status: "specified after the paired counts were observed (post-hoc); committed before S4 execution"
materiality_reference_detections: 6
materiality_reference_rate: 0.0102916
output_dir: results/publication_experiments/EXP_TOST_V1
```

**`publication_experiments/configs/mad.yaml`** (S5, S6)

```yaml
experiment_id: EXP_MAD_THRESHOLD_V1
calibration_re_primary: results/publication_experiments/EXP_PROB_INFERENCE_V1/ae_calibration_benign_reconstruction_errors.csv
legacy_val_re_crosscheck: results/autoencoder/EXP_AE_V1/threshold/validation_reconstruction_errors.csv
ae_threshold_config: results/checkpoints/EXP_AE_V1/threshold_config.json
percentile_method: linear
primary_rules: [p95, p99, p999, mean_plus_2sigma, mean_plus_3sigma, raw_mad_k3]
sensitivity: {raw_mad_k: [2, 3, 4], scaled_mad_k: [2, 3, 4], scaled_mad_constant: 1.4826}
output_dir: results/publication_experiments/EXP_MAD_THRESHOLD_V1
```

S5 uses `calibration_re_primary`, generated by S1 from the canonical AE checkpoint and frozen scaler. When untouched VAL is eligible, this file is the regenerated validation RE vector from `ae_final.pt`. The legacy saved VAL RE file is cross-check-only. Under an alternate clean-calibration branch, the S1-generated alternate calibration RE vector is primary and the old VAL RE file is not used as a headline calibration source.

**`publication_experiments/stage_f/configs/stage_f.yaml`** (S7): populations manifest path, seeds `[42, 123, 2024]`, the IF parameters in §7, `ae_scaler: results/checkpoints/EXP_AE_V1/ae_scaler.joblib`, `train_path: data/splits/train.csv` with `filter: {label: 0}` and `expected_n: 44800`, feature list path, output directories from §7.

**`publication_experiments/configs/roc_pr.yaml`** (S2) and **`alert_budget.yaml`** (S8): input paths, output paths; S8 also lists `prevalences` (must include the observed prevalence of the headline tier's evaluation population: 583/37,583 for Tier A, 583/19,083 for Tier B) and `review_scenarios` (list of `{alerts_per_day B, flows_per_day F}`); every value other than the observed prevalence is labelled illustrative. **`cross_check.yaml`** (S9): paths to every artifact and frozen reference file listed in §17 Phase 7, and the §0.3 tolerances.

### S0 — `phase0_discovery.py`

Read-only. Writes `phase0_discovery.json` containing:

1. SHA-256 of every frozen split and checkpoint.
2. **Unseen-family source:** scans `data/splits/*.csv` (and the EXP_AE_UNSEEN_FAMILY_V1 config, if present) for `attack_cat` counts; lists every file/filter combination that yields Worms = 44, Shellcode = 378, Analysis = 677.
3. **VAL-usage and DEV_TEST-usage audits:** `git grep` and static scan of trainers/configs for VAL use in early stopping, model selection, meta-learner fitting, feature selection, and fitted preprocessing/scalers, and — separately — for any use of benign DEV_TEST rows in the development or selection of a scored model (needed for Tier-B eligibility); lists every hit for human review.
4. **Calibration-source decision:** classifies the calibration population as `untouched_val`, `alternate_clean_source`, or `contaminated_sensitivity_only`; records source path, filter, row count, row-ID hash, and rationale.
5. **Benign-control identity:** locates EXP_ZERODAY_V1 per-row artifacts, extracts the 37,000 benign source-prefixed row IDs, records count and SHA-256. If no per-row artifact exists, reports this and the sampling code path so identity can be reconstructed and then verified against the frozen threshold-0.5 reference using the historical comparator.
6. **AE validation RE provenance:** records that S1 regenerates validation REs from `ae_final.pt` + frozen AE scaler as the canonical source; the legacy saved RE file is a cross-check only; checkpoint/scaler/file/row-ID hashes are recorded.
7. **Population identity/disjointness:** generates source-prefixed row IDs, asserts uniqueness within each population, and computes the overlap matrix for TRAIN, calibration, DEV_TEST, Backdoor, benign control, and unseen families. The benign control subset-of-DEV_TEST relationship is intentional and must be exact.
8. **Feature/scaler leakage audit (non-blocking):** checks metadata/source code to determine whether feature selection and every fitted scaler were fit on TRAIN only. Record PASS/FAIL/UNCERTAIN and evidence; this audit does not by itself block execution of the new experiments.
9. **Git evidence:** `git log --follow` (commit hash, author date, commit date) for `preregistered_decisions.json`, `materiality_preregistration.json`, and the code/config that define the H2 criteria and materiality threshold; earliest commit that contains the actual criterion text.

10. **Partition-provenance check:** verifies TRAIN benign + VAL benign = 56,000; DEV_TEST benign = 37,000 = benign-control size (DEV_TEST minus 44,749 attack rows); and, from split-generation scripts/metadata, whether TRAIN+VAL and DEV_TEST derive from the official UNSW-NB15 training and testing partitions respectively. Records the result as evidence (PASS / FAIL / UNCERTAIN).
11. **Tier-B split generation:** using the `split_seed` already committed in `populations.yaml`, writes the source-prefixed `CAL_CONTROL` and `EVAL_CONTROL` row-ID lists (18,500 each), asserts disjointness and union = the 37,000-row benign control, and records SHA-256 hashes.

A human then completes `populations.yaml`, records the calibration-source decision, Tier-B eligibility, and overlap policy, and commits.

### S1 — `run_prob_inference.py`

1. Refuse to run if the resolved clean calibration source, its row-ID list/hash, `benign_control.row_uid_list`, or `unseen_families.source` in `populations.yaml` is null. If `source_status=contaminated_sensitivity_only`, refuse to produce headline-calibration outputs unless an explicit sensitivity-analysis flag is set.
2. Verify all checkpoint SHA-256 values against frozen provenance; verify split SHA-256 values.
3. Load models read-only.
4. For each population, extract the 75 EXP_MI_V1_1 features in exact order and compute the supervised scores (SVM/NN with their own frozen scalers; sigmoid on the NN; meta-features in training order) and the AE reconstruction errors. **For validation, S1 must regenerate the reconstruction errors from the canonical `EXP_AE_V1/ae_final.pt` checkpoint and frozen `ae_scaler.joblib`; the legacy saved validation RE file is never the primary source.**
5. Write the score files listed in §6, `metadata.json`, and `self_check.json` (hard-fail on: wrong row counts, NaN/inf, out-of-range probabilities, row-ID hash mismatch, duplicate row IDs, unseen-family counts ≠ 44/378/677, or calibration-source mismatch).
6. For AE validation REs, record the exact checkpoint SHA-256, scaler SHA-256, feature-list SHA-256, and row-ID hash; compare the regenerated primary vector with the legacy saved vector as a cross-check only. SHA-256 every output file.

### S2 — `run_roc_pr_analysis.py`

Implements B2 in §6. Runs after S3 so the headline tier's budget-matched operating points can be marked on the figures. Reports ROC and PR curves without pooling seeds, stacking/IF metrics per seed with mean ± SD, PR-AUC as `average_precision_score`, and F2 at all four common matched-FPR budgets. Argmax-F2 is labelled oracle.

### S3 — `run_matched_fpr_analysis.py`

Implements B1 in §6 and §0.1. Every model, including AE and IF, goes through the same calibration function. Writes `matched_fpr_table.csv` and `cross_model_comparison.csv`. Refuses to run if any evaluation-population score is passed to the calibration function: in Tier A by `population_type`; in Tier B by asserting that calibration rows ⊆ `CAL_CONTROL`, evaluation rows ⊆ `EVAL_CONTROL`, and the two are disjoint. Each seeded model is calibrated on its own seed's scores in each tier. Also writes `partition_shift_diagnostic.csv` and `headline_tier_decision.json` per the committed `headline_tier_rule`, and asserts the computed `k` against an exact-arithmetic reference.

### S4 — `run_tost_analysis.py`

Implements §8.1: prefers per-row paired RF predictions keyed by the committed Backdoor row IDs, derives A/B/C/D, verifies `A+B+C+D=583`, computes the conservative exact paired-equivalence test on the discordant proportion and Clopper–Pearson bounds, writes `tost_rf_equivalence.json`, and aborts if `tost.yaml` has uncommitted changes. If only the aggregate fallback exists, it validates the artifact hash and total before proceeding.

### S5 — `run_mad_threshold.py`

1. Load the **S1-generated AE reconstruction-error vector for the resolved clean calibration population as the primary artifact**. When `source_status=untouched_val`, this is the regenerated EXP_AE_V1 validation RE vector from `ae_final.pt` + frozen AE scaler. The legacy saved validation RE file is a cross-check only.
2. If the legacy file exists, assert element-wise agreement with the S1-generated validation vector within the §0.3 tolerance when VAL is the active calibration source.
3. Assert recomputed mean/std/τ match `threshold_config.json` when the untouched-VAL branch is active; under an alternate clean calibration branch, record that these legacy τ values are historical reference values and do not use them as headline thresholds.
4. Compute the six primary rules and the sensitivity block (raw MAD: `median + k·MAD`; scaled MAD: `median + k·1.4826·MAD`).
5. Compute **calibration FPR** for every rule from the exact `N_cal`-row vector.
6. Write `mad_threshold.json` with the calibration source, `N_cal`, source hash, checkpoint hash, scaler hash, and row-ID hash.

### S6 — `run_ae_threshold_ablation.py`

Join S5 thresholds with S1 AE zero-day and unseen-family REs. Output one row per rule with: threshold, calibration FPR, held-out control FPR (+ CI), Backdoor / Worms / Shellcode / Analysis detections and recall (+ CI). Assert that every threshold's source hash equals the S1-generated AE calibration RE vector hash, and when the active source is untouched VAL also equals the regenerated EXP_AE_V1 VAL RE vector hash.

### S7 — `run_isolation_forest.py`

Implements §7 for seeds 42, 123, 2024. Asserts training rows = 44,800, all `label == 0`, 75 features, and scaler hash equal to the frozen AE scaler. Writes per-row scores for all four populations (row-uid hashes checked against `populations.yaml`).

### S8 — `run_alert_budget_analysis.py`

Implements B4 in §6 on the headline-tier rows named in `headline_tier_decision.json`, including recall (+ CI) under each illustrative review scenario. No absolute enterprise flow rate is derived from the dataset.

### S9 — `run_cross_consistency_check.py`

Executes (not merely lists) the Phase 7 checks in §17 and writes `cross_check_report.json`. Exits non-zero on any FAIL. Reference values are read from artifact files.

---

## 17. Execution Sequence

All commands run in PowerShell from the project root. Line continuation uses the backtick.

### Phase 0: Environment, Freeze Verification, and Discovery

**Before running S0:** commit the skeleton `populations.yaml` (containing the Tier-B `split_seed`) and `matched_fpr.yaml` (containing `headline_tier_rule`), so the split and the headline-tier rule provably precede any result (Rule 14).

```powershell
cd "D:\rishu\zip extraction\major-p\Papers\IDS-UNSW-NB15"
.\.venv\Scripts\Activate.ps1
python scripts/verify_sprint12_freeze.py
python scripts/validate_ae.py
python scripts/validate_oof_stacking.py
python publication_experiments/scripts/phase0_discovery.py
```

Then, by hand:

1. Review `phase0_discovery.json`. Resolve `calibration_benign`, `unseen_families.source`, `benign_control.row_uid_list` (+ SHA-256), source-prefixed row-ID lists, and overlap policy in `populations.yaml`.
2. Review the VAL-usage audit. If VAL is untouched by model development, mark `source_status: untouched_val`. If a demonstrably unused benign calibration population exists, mark `source_status: alternate_clean_source`. If only contaminated VAL is available, mark `source_status: contaminated_sensitivity_only` and prohibit clean headline calibration claims.
3. Record the feature-selection/scaler leakage audit as non-blocking evidence in DOC-07.
4. Confirm the AE calibration RE provenance: S1 generation from `ae_final.pt` + frozen AE scaler is primary; the legacy saved validation RE file is cross-check only.
5. Commit `populations.yaml` and all protocol-defining configs before Phase 1.

**STOP** if: any required hash mismatches; feature count ≠ 75; no clean calibration source can be established for either tier; unseen-family counts do not equal 44/378/677 under any candidate source; the benign-control row-ID list cannot be obtained or reconstructed and verified; required forbidden population overlaps are detected; the Tier-B halves are not disjoint or their union differs from the benign control; or required row IDs are not unique.


### Phase 1: BATCH-A — Frozen Inference

```powershell
python publication_experiments/scripts/run_prob_inference.py `
  --config publication_experiments/configs/prob_inference.yaml
```

S1's `self_check.json` must show all checks passed before proceeding.

### Phase 2: BATCH-C — Isolation Forest (3 seeds)

```powershell
python publication_experiments/stage_f/scripts/run_isolation_forest.py `
  --config publication_experiments/stage_f/configs/stage_f.yaml
```

### Phase 3: TOST (independent; may run any time after its config is committed)

```powershell
python publication_experiments/scripts/run_tost_analysis.py `
  --config publication_experiments/configs/tost.yaml
```

### Phase 4: AE Threshold Family and Ablation

```powershell
python publication_experiments/scripts/run_mad_threshold.py `
  --config publication_experiments/configs/mad.yaml
python publication_experiments/scripts/run_ae_threshold_ablation.py `
  --config publication_experiments/configs/mad.yaml
```

### Phase 5: Matched-FPR for All Models

```powershell
python publication_experiments/scripts/run_matched_fpr_analysis.py `
  --config publication_experiments/configs/matched_fpr.yaml
```

S3 writes `matched_fpr_table.csv` (Tier A and Tier B rows, `calibration_tier` column), `partition_shift_diagnostic.csv`, and `headline_tier_decision.json`. Downstream scripts (S2, S8) read the headline tier from the decision file.

### Phase 6: ROC/PR/F2 and Alert Budget

```powershell
python publication_experiments/scripts/run_roc_pr_analysis.py `
  --config publication_experiments/configs/roc_pr.yaml
python publication_experiments/scripts/run_alert_budget_analysis.py `
  --config publication_experiments/configs/alert_budget.yaml
```

### Phase 7: Cross-Result Consistency Check (executable)

```powershell
python publication_experiments/scripts/run_cross_consistency_check.py `
  --config publication_experiments/configs/cross_check.yaml
```

S9 must verify, reading reference values from frozen files (§0.3 tolerances):

1. Stacking DEV_TEST Macro-F1 for seeds 42/123/2024 matches `h1_results.json`.
2. Stacking threshold-0.5 FPR on the benign control and Backdoor detections match `zero_day_metrics.csv`, using the historical reference comparator.
3. When `source_status=untouched_val`, AE mean/std/τ recomputed from the **S1-regenerated** VAL RE vector match `threshold_config.json` and the legacy VAL RE artifact agrees as a cross-check only. Under an alternate clean-calibration branch, S9 instead verifies the S1-generated calibration RE source/hash and does not require the historical VAL τ match.
4. AE τ applied to the zero-day REs reproduces the frozen Backdoor detection count.
5. Within each tier, every matched-FPR threshold uses that tier's single calibration source (Tier A: resolved clean calibration population; Tier B: `CAL_CONTROL`); seeded models carry seed-specific thresholds; `N_cal` matches the manifest.
6. IF scaler SHA-256 equals the frozen AE scaler SHA-256; IF training rows = 44,800.
7. Source-prefixed row IDs are unique within each population; benign-control and unseen-family row-ID hashes are identical across S1/S3/S6/S7 outputs; forbidden overlaps pass the S0 policy.
8. TOST margin in the JSON equals the committed `tost.yaml`; `A+B+C+D=583`; paired row identities are validated when per-row predictions are available; Git shows the config commit precedes the result file.
9. Every AE ablation threshold source hash equals the S1-generated AE calibration RE vector hash; when untouched VAL is active, it also equals the S1-generated EXP_AE_V1 VAL RE vector hash. No threshold is imported from EXP_AE_UNSEEN_FAMILY_V1.
10. Worms CP upper bound in `ae_primary_summary.csv` rounds to 8.04%.
11. Protocol configs (populations, matched_fpr, tost, mad, stage_f, prob_inference, roc_pr, alert_budget) were committed before their outputs' timestamps.
12. Alert-budget outputs contain no absolute enterprise flow-rate claim (user-supplied scenarios are labelled illustrative).
13. Every model has F2 reported at all four common matched-FPR budgets; default-threshold F2 is reference-only.
14. ROC and PR curves are generated without pooling predictions across seeds; PR-AUC equals `average_precision_score`.
15. Tier-B halves are disjoint, their union equals the benign control, hashes match `populations.yaml` across S1/S3 outputs, and the Tier-B calibration function received only `CAL_CONTROL` rows while evaluation used only `EVAL_CONTROL` rows.
16. `partition_shift_diagnostic.csv` and `headline_tier_decision.json` exist; the decision follows the rule text committed in `matched_fpr.yaml` (hash of the rule text equal); the tier named in the decision file is the tier used by every headline table and figure input; the rule was committed before the S3 output timestamp.
17. `alert_budget_table.csv` includes recall (+ CI) at every calibrated budget and for every review scenario, drawn from the headline tier.

Manuscript work does not start until all configured S9 checks report PASS.

### Phase 8: Documentation

- Write `docs/DOC_PREREGISTRATION_TIMING.md` from the S0 Git evidence.
- Write `docs/DOC_SCOPE_DECISION.md` (Req 4.3): second-dataset decision, rationale, and the Limitations content specified in M17.
- Update the README with new experiments, commands, and the repository link.
- Tag the repository at the commit containing all completed experiments.

### Phase 9: Venue Selection and Scientific Manuscript Corrections

Set `submission_venue` (for example, IEEE conference/journal or Springer LNCS) in the manuscript documentation. Then apply M1–M17 (§20) and the editorial corrections (3.1–3.5), in that order.

---

## 18. Validation Gates

### Gate 1 — Environment, Freeze, and Phase-0 Discovery

- [ ] Python 3.11 `.venv` activated
- [ ] `verify_sprint12_freeze.py` passes (0 hash mismatches)
- [ ] `validate_ae.py` passes all 21 checks
- [ ] `validate_oof_stacking.py` passes all 24 checks
- [ ] Feature list: 75 features, EXP_MI_V1_1
- [ ] DEV_TEST SHA-256 = `04725e85732ab2fc6d9eaaa6105418b22b083b5c651067e7b0785464f414e508`
- [ ] Protected Backdoor SHA-256 = `6ffd23479b575e438ad90678268f40f674a663c2b9507aaf65089623397a9d91`
- [ ] Frozen AE scaler SHA-256 recorded
- [ ] `phase0_discovery.json` exists; unseen-family source resolved with counts 44 / 378 / 677
- [ ] Clean calibration source resolved and recorded (`untouched_val`, `alternate_clean_source`, or `contaminated_sensitivity_only`)
- [ ] Actual calibration `N_cal` and source-prefixed calibration row-ID hash recorded in `populations.yaml`
- [ ] Benign-control row-ID list resolved: 37,000 rows, SHA-256 recorded in `populations.yaml`
- [ ] Tier-B split: `CAL_CONTROL` 18,500 + `EVAL_CONTROL` 18,500, disjoint, union = benign control; `split_seed` and SHA-256s recorded; skeleton committed before S0
- [ ] Partition-provenance check recorded (TRAIN+VAL benign = 56,000; DEV_TEST benign = 37,000; official-partition mapping PASS/FAIL/UNCERTAIN)
- [ ] Source-prefixed row IDs are unique; population disjointness/intentional overlap policy passes
- [ ] VAL-usage and DEV_TEST-usage audits reviewed; decisions (incl. Tier-B eligibility) recorded in DOC-07
- [ ] Feature-selection/scaler leakage audit recorded as non-blocking evidence
- [ ] AE S1 regeneration provenance is tied to `ae_final.pt` + frozen AE scaler; when untouched VAL is active, mean/std/τ also match `threshold_config.json`; otherwise the alternate calibration branch is recorded without forcing the historical τ match
- [ ] `populations.yaml` and all protocol configs committed

### Gate 2 — IF Model Validation (each seed)

- [ ] Model loads; fitted on exactly 44,800 rows, all `label == 0`
- [ ] Feature set = EXP_MI_V1_1 (75 features, exact order)
- [ ] Scaler is the frozen AE scaler (hash equal); `n_features_in_ == 75`; no scaler fit call executed
- [ ] Seeds 42, 123, 2024 all present; each seed reproducible (repeat run yields identical scores)

### Gate 3 — Score-File Validation

- [ ] `dev_test_probabilities.csv`: 81,749 rows
- [ ] `calibration_benign_probabilities.csv`: actual manifest `N_cal` rows, all label 0
- [ ] `zeroday_probabilities.csv`: 37,583 rows (583 Backdoor + 37,000 benign control); `population_type` correct
- [ ] AE files: DEV_TEST 81,749; resolved clean calibration population (`N_cal` from manifest); zero-day 37,583; unseen families 44 / 378 / 677
- [ ] IF files (per seed): resolved clean calibration population (`N_cal` from manifest); DEV_TEST 81,749; zero-day 37,583; unseen families 44 / 378 / 677
- [ ] Source-prefixed row-ID hashes of the benign control and unseen families identical across S1 and S7 outputs
- [ ] No duplicate row IDs within any score file
- [ ] No NaN/inf in any score column
- [ ] DT, RF, NN, Meta probabilities in [0, 1]; SVM scores unbounded

### Gate 4 — Metric Validation (references read from artifacts; §0.3 tolerances)

- [ ] Stacking DEV_TEST Macro-F1 (each seed) matches `h1_results.json` within ±1e-6
- [ ] Stacking threshold-0.5 FPR on the benign control matches `zero_day_metrics.csv` within ±1e-3; Backdoor detections match exactly
- [ ] When `source_status=untouched_val`, AE mean, std, τ recomputed from the S1-generated VAL REs match `threshold_config.json` (relative 1e-4); alternate clean-calibration branches do not use the historical τ as a headline threshold
- [ ] AE τ on zero-day REs reproduces the frozen Backdoor detection count exactly
- [ ] Every model and every seed has its own calibrated thresholds at all four budgets, in both tiers (`calibration_tier` column populated)
- [ ] `partition_shift_diagnostic.csv` and `headline_tier_decision.json` exist and follow the committed rule; no table mixes tiers
- [ ] `k` for every budget matches the exact-arithmetic reference
- [ ] Achieved calibration FPR ≤ budget for every entry; achieved held-out FPR and CIs reported for every entry
- [ ] F2 exists at all four common matched-FPR budgets for every model; default-threshold F2 is reference-only
- [ ] ROC-AUC, PR-AUC, and F2 lie in [0, 1]; PR-AUC is `average_precision_score`; AUC values are reported as computed (AE AUC < 0.5 is not clipped)
- [ ] ROC/PR curves are not pooled across seeds
- [ ] AE validation RE source is S1-generated from `ae_final.pt` + frozen scaler
- [ ] MAD thresholds are finite and valid for the model's score domain

### Gate 5 — Statistical Validation (TOST)

- [ ] Margin in the result JSON equals the committed `tost.yaml` value
- [ ] Conservative exact paired-equivalence p-value and Clopper–Pearson bounds computed from first principles
- [ ] Equivalence is claimed only if the one-sided 95% upper bound on q is below δ and the conservative p-value is below α
- [ ] RF A/B/C/D are derived from per-row paired predictions when available; otherwise the aggregate fallback is hash-validated and `A+B+C+D=583`
- [ ] Limitations statement (post-hoc margin, saturated rate, zero discordance) present in the JSON and later in the manuscript

### Gate 6 — Cross-Artifact Consistency (S9 all configured checks PASS)

- [ ] All configured S9 checks pass
- [ ] Every AE ablation threshold traces to the S1-generated AE reconstruction-error vector for the resolved clean calibration population; when `source_status=untouched_val`, this is the regenerated EXP_AE_V1 VAL RE vector; none from EXP_AE_UNSEEN_FAMILY_V1
- [ ] AE, IF, and stacking rows in the cross-model table use identical budgets, calibration population, and evaluation populations within the headline tier
- [ ] Cross-model F2 is reported at all four common matched-FPR budgets
- [ ] Main figure contains both ROC and PR panels and does not pool seeds

### Gate 7 — Provenance Validation

- [ ] `EXP_PROB_INFERENCE_V1/metadata.json`: timestamp, checkpoint SHAs verified, feature_count = 75, seeds, population counts, row-identity hashes
- [ ] `EXP_IF_V1/metadata.json`: timestamp, seeds [42, 123, 2024], n_estimators = 200, training_rows = 44,800, feature_count = 75, frozen scaler hash
- [ ] `tost_rf_equivalence.json`: declared δ, paired-input provenance, conservative exact procedure, timestamp
- [ ] `DOC_PREREGISTRATION_TIMING.md` states experiment/document timestamps and Git evidence
- [ ] No artifact claims "pre-registered" for post-hoc material
- [ ] Protocol configs were committed before their outputs were generated

### Gate 8 — Manuscript Evidence Validation

- [ ] Every number in new results sections traces to an artifact
- [ ] NN architecture stated as `75 → 128 → 64 → 1` everywhere; no "→ 2" remains
- [ ] AE training count states both 40,320 (early stopping) and 44,800 (final refit)
- [ ] Worms 8.04% appears in Abstract, Results, Limitations, and Conclusion
- [ ] Matched-FPR values trace to `matched_fpr_table.csv`; IF values to the IF artifacts; TOST wording to `tost_rf_equivalence.json`
- [ ] The TOST margin is described as post-hoc; "predeclared" is used only where Git evidence supports it
- [ ] Calibration protocol (both tiers, Tier-B split and seed, held-out evaluation, VAL-usage and DEV_TEST-usage audit outcomes, partition-provenance finding, headline-tier decision) disclosed (M16)
- [ ] Any realized-vs-nominal FPR gap is reported as a finding (partition shift) rather than as sampling noise
- [ ] Scope decision recorded (DOC-08) and Limitations strengthened (M17); no generalization claim beyond UNSW-NB15
- [ ] Conclusion reflects the observed constrained-FPR results
- [ ] No informal phrasing remains in §V–§VIII

### Gate 9 — Reproducibility Validation

- [ ] All new scripts run from the project root using their exact paths and `--config`
- [ ] `requirements-lock.txt` records the tested Python/library environment
- [ ] All seeds, checkpoint SHAs, dataset SHAs, and row-identity hashes recorded in metadata
- [ ] Repository tagged at the completion commit
- [ ] A second researcher can reproduce all new results from the repository and environment alone

---

## 19. Provenance and Reproducibility Plan

### Existing (Reuse)

The existing provenance infrastructure covers:
- All base model checkpoints (SHA-verified)
- AE checkpoint (SHA-verified)
- Meta-learner checkpoints (SHA-verified)
- Dataset splits (SHA-verified)
- `results/evaluation/EXP_H123_V1/provenance/*.json` — all checkpoint hashes at evaluation time

### New (Must Add)

Each new experiment must produce a `metadata.json` containing at minimum:

```json
{
  "experiment_id": "EXP_PROB_INFERENCE_V1",
  "timestamp_utc": "<ISO 8601>",
  "git_commit": "<git rev-parse HEAD>",
  "python_version": "<sys.version>",
  "library_versions": {
    "sklearn": "<sklearn.__version__>",
    "torch": "<torch.__version__>",
    "numpy": "<np.__version__>",
    "pandas": "<pd.__version__>"
  },
  "checkpoint_sha256": {
    "dt_final_joblib": "<sha>",
    ...
  },
  "dataset_sha256": {
    "development_test": "<sha>",
    "protected_unseen_attack": "<sha>"
  },
  "feature_count": 75,
  "feature_set": "EXP_MI_V1_1",
  "seeds": [42, 123, 2024],
  "threshold_calibration": {
    "population": "<resolved_clean_calibration_source>",
    "rows": "<N_cal_from_manifest>",
    "held_out_evaluation_benign_rows": 37000,
    "seed_specific_thresholds": true
  },
  "population_counts": {
    "dev_test": 81749,
    "zeroday_backdoor": 583,
    "zeroday_benign_control": 37000,
    "unseen_family_counts": {"Worms": 44, "Shellcode": 378, "Analysis": 677}
  },
  "row_identity_sha256": {
    "benign_control_row_uid_list": "<sha>",
    "unseen_family_row_uid_list": "<sha>"
  }
}
```

### Version Control

Experimental code/config commits must be created **before** execution where they declare calibration rules, TOST margin, seeds, metric definitions, curve aggregation, or other protocol parameters. Do not batch all protocol-defining changes into a post-result commit. After validation, a final commit should capture the completed artifacts and manuscript-supporting documentation.

For exact reproduction, commit a lockfile such as `requirements-lock.txt` (or an equivalent environment lock) capturing the Python/package environment used for the final runs. The final manuscript should phrase exact reproducibility as requiring the repository, the locked environment, and documented dataset access.

---

## 20. Scientific Manuscript Corrections Required

> **Rule:** Every correction listed here requires its evidence artifact to exist and be validated (Gates 4–8, and S9 all PASS) BEFORE the correction is made to the manuscript.

| # | Section | Current Text (paraphrase) | Correction | Evidence Prerequisite |
|---|---------|--------------------------|------------|----------------------|
| M1 | §III.E | "architecture 75 → 128 → 64 → 2" | Replace with "75 → 128 → 64 → 1 (binary sigmoid output, binary cross-entropy loss)" | Gate 1 (`nn_architecture.json` + `nn_metadata.json`) |
| M2 | §III.F | "trained exclusively on 40,320 normal flows from TRAIN" | Replace with "trained using a 40,320/4,480 early-stopping split to determine best epoch (133), then refitted on all 44,800 Normal TRAIN rows for the final checkpoint" | Gate 1 (`ae_metadata.json`) |
| M3 | §III.D | — | Add new §III.D describing Isolation Forest baseline: n_estimators=200, seeds=42/123/2024, same 75-feature space, benign-only training, frozen EXP_AE_V1 scaler, threshold calibrated on the resolved clean benign calibration population | Gate 2 (EXP_IF_V1 validated) |
| M4 | §V.A | Per-model Macro-F1 table | Keep Macro-F1 in a column group labelled `DEV_TEST` (prevalence stated). Add PR-AUC (AP) and matched-FPR F2 in a **separate** column group labelled with the headline tier's zero-day population and its prevalence (1.55% Tier A / 3.06% Tier B); DEV_TEST PR-AUC may appear only as a labelled reference. Never mix populations within one column group. F2 headline values are the common 0.1/0.5/1/5% matched-FPR values; default-threshold F2 is reference-only | Gate 4 (`f2_summary.json`, `prauc_summary.json`) |
| M5 | §V.A + §V.E | — | Add new §V.E for IF baseline results: DEV_TEST Macro-F1 at Tier-A matched-FPR points (descriptive only; Tier-B calibration rows are part of DEV_TEST), zero-day Backdoor detection rates, AE vs IF comparison table | Gate 2 + Gate 4 (EXP_IF_V1 results) |
| M6 | §V.B or new §V.F | — | Add "Matched-FPR Operating Point Analysis" subsection: recall and F2 at 0.1%, 0.5%, 1.0%, 5.0% nominal FPR for every model, with stacking/IF seed summaries, thresholds calibrated on the resolved clean calibration population and evaluated on the held-out control, achieved FPR and Clopper–Pearson CIs shown; explicitly state that 19.19% FPR corresponds to the historical uncalibrated threshold-0.5 reference operating point; show Tier A and Tier B, name the headline tier per the committed decision rule, and report any realized-vs-nominal FPR gap as a partition-shift finding | Gate 4 (`matched_fpr_table.csv`) |
| M7 | §V.D + §V.G | AE threshold sweep (Fig 1) | Replace/extend Fig. 1 with adjacent ROC and PR panels containing AE, stacking, and IF curves; mark the matched-FPR operating points; report per-seed curves without pooling | Gate 4 (EXP_ROC_PR_V1 figures) |
| M8 | §V.C / §III.F | McNemar test for RF "inconclusive" | Add the **conservative exact paired-equivalence test on the discordant proportion** only after execution: declared δ = 0.01, computed conservative exact p-value, one-sided exact 95% upper bound on the discordant proportion, and the limitations (margin specified after the paired counts were observed; saturated Backdoor recall; zero discordant pairs). Do not hardcode an equivalence sentence before Gate 5. | Gate 5 (`tost_rf_equivalence.json`) |
| M9 | Abstract | "null recall across three unseen families" | Add explicit CIs: "0/44 Worms (95% CI upper bound: 8.04%), 0/378 Shellcode (0.97%), 0/677 Analysis (0.54%)" | Gate 6 (`ae_primary_summary.csv` — already validated) |
| M10 | §VIII Conclusion | No Worms CI | Add: "The 44 Worms samples yielded 0% detection with a 95% Clopper-Pearson upper bound of 8.04%" | Gate 6 (same as M9) |
| M11 | Table III title | "PRE-REGISTERED" | Replace with "PREDECLARED" only where Git/contemporaneous evidence supports the term; add explicit timing footnote for the post-hoc materiality document. | Gate 7 (`DOC_PREREGISTRATION_TIMING.md`) |
| M12 | §VI (Discussion) | Conclusion framing not yet tied to constrained-FPR evidence | After matched-FPR results exist, describe the observed deployment implications without precommitting to a "neither paradigm" outcome. State clearly whether recall remains high or collapses at constrained FPR. | Gate 4 (`matched_fpr_table.csv`) |
| M13 | §VI.D | Alert-budget absent | Add standardized alert-budget sensitivity using alerts per 100k/1M benign flows and `alerts = benign_flows × FPR`; add precision sensitivity at selected prevalence values and, for each illustrative review scenario, the recall each model retains at the largest common budget not exceeding B/F (Req 1.4). Do not derive enterprise flows/day from UNSW-NB15 lab capture. | Gate 4 (`alert_budget_table.csv`) |
| M14 | §V.D / new | AE threshold ablation mentioned but not tabled | Add table: p95/p99/p999/mean+2σ/mean+3σ/raw-MAD(k=3), all computed from the S1-generated AE REs of the resolved clean calibration population; when untouched VAL is active, this is the regenerated EXP_AE_V1 validation RE vector; include clearly labelled MAD sensitivity if included. | Gate 4 (`ae_threshold_ablation_table.csv`) |
| M15 | §I or end | No availability statement | Add: "Code and experimental artifacts are available at [REPOSITORY_URL]. All frozen results are SHA-256 verified." | Gate 9 (repository is public or will be submitted) |
| M16 | §III + §V.F | Calibration protocol not described | Describe the resolved calibration-source branch (untouched VAL benign when eligible, otherwise an independent untouched benign calibration population), actual `N_cal`, threshold rule, realized-vs-nominal FPR reporting, held-out 37,000-row control and 583 Backdoor evaluation, the Tier-B control-split protocol (seed, 18,500/18,500 halves), the partition-provenance finding, the outcomes of the VAL-usage and DEV_TEST-usage audits, and the headline-tier decision. State explicitly if only development-contaminated sensitivity results were possible. | Gate 1 (DOC-07), Gate 4 |
| M17 | §VII (Limitations) | Scope limitations not fully articulated | Add Limitations covering: single dataset (UNSW-NB15) with synthetic-testbed artifacts; no second dataset in this revision (rationale from DOC-08); official train/test partition shift and its effect on VAL-calibrated thresholds; Backdoor as the only zero-day proxy for supervised models and n = 44 / 378 / 677 unseen families for AE/IF (Worms CI 8.04%); post-hoc TOST margin and saturated Backdoor recall; TTL/shortcut caveat. Do not claim generalization beyond UNSW-NB15. | Gate 8 (DOC-08) |

> **Corrections NOT in this list** (outside scientific scope — pure formatting/editorial): email typo (3.4), author affiliation format (3.3), informal language rewrite (3.1), Eq.(5) move (3.2), table layout (3.5). These are required by the requirements document but do not require evidence artifacts — they should be done during the same editing pass, after all scientific corrections are complete.

---

## 21. Risk Register

| # | Risk | Why It Matters | Detection | Mitigation | Blocks |
|---|------|---------------|-----------|------------|--------|
| R1 | Wrong evaluation population for matched-FPR analysis | Using TRAIN/OOF benign or a different 37,000-row sample changes FPR comparability | Gate-3: verify 37,000-row control identity/hash and population_type | Reuse the exact benign-control rows from EXP_ZERODAY_V1; seed 42 is a provenance check, not a substitute for row identity | Req 1.2 |
| R2 | Wrong feature set for IF | Using full feature set instead of EXP_MI_V1_1 | Gate-2: verify feature_count=75 in metadata | S7 must load `selected_features.json` and filter columns | Req 2.1 |
| R3 | SVM probability mismatch | LinearSVC has no `predict_proba` — calling it would raise or return garbage | Gate-3: verify SVM column is `svm_decision_score` (unbounded) | S1 must call `decision_function()` and document that SVM ROC uses raw scores | Req 1.1, 1.3 |
| R4 | Meta-learner column order mismatch | If meta-features are not in [DT, RF, SVM, NN] order, predictions will be garbage | Gate-4: Macro-F1 won't match h1_results.json | S1 must use `META_FEATURE_COLS = ['dt_attack_probability', 'rf_attack_probability', 'svm_decision_score', 'nn_attack_probability']` — verify against meta_learner.py | All of Req 1.x |
| R5 | IF scaling mismatch | IF could be fit/evaluated in a different scaling domain from AE | Gate-2: verify IF consumes the frozen EXP_AE_V1 scaler hash | S7 must reuse `EXP_AE_V1/ae_scaler.joblib`; do not refit a new scaler | Req 2.1 |
| R6 | NN sigmoid not applied in inference | Forward pass without sigmoid gives logits, not probabilities | Gate-3: verify NN proba in [0,1] | S1 must apply `torch.sigmoid()` to NN output | Req 1.1, 1.3 |
| R7 | OOF probabilities substituted for zero-day evaluation | OOF is TRAIN population — invalid for zero-day FPR analysis | Gate-3: population_type column check; row count 37,583 | S1 explicitly uses protected_backdoor.csv + benign_control subset | Req 1.2 |
| R8 | Accidental retraining | A script calls `model.fit()` or similar | Automated scan: copy `scan_ml_patterns.py` check into S1-S8 headers | All new scripts: import guard fails if any training operation detected | All |
| R9 | Overwriting existing results | New artifacts accidentally written to existing EXP_ZERODAY_V1 paths | File lock / explicit new experiment IDs | All new artifacts use new experiment IDs (EXP_PROB_INFERENCE_V1, etc.) | All |
| R10 | TOST margin chosen after seeing data | Post-hoc margin selection can invalidate the intended equivalence interpretation | Git/config check: margin must exist in the committed analysis config before S4 runs | S4 reads one numeric margin from YAML; never modify it after seeing TOST output | Req 2.3 |
| R11 | MAD from wrong AE run | If REs come from an unseen-family re-run, the ablation no longer describes EXP_AE_V1 | Gate-1/6: source hash must match EXP_AE_V1 | Use saved EXP_AE_V1 REs or regenerate them with the frozen EXP_AE_V1 checkpoint/scaler only | Req 2.2 |
| R12 | Post-hoc preregistration mislabeled | Calling the materiality doc "pre-registered" despite 7-day lag | Gate-7: DOC_PREREGISTRATION_TIMING.md must flag this | Use "predeclared" only where Git evidence supports it; otherwise describe as post-hoc | Req 4.2 |
| R13 | Architecture mismatch in manuscript | Reporting 75→128→64→2 after correction to 75→128→64→1 is overlooked | Gate-8: audit all mentions of "→2" in DOCX | Search DOCX for "64 → 2", "64→2", "> 2" in architecture context | M1 |
| R14 | IF comparison at incompatible FPR levels | AE and IF could be compared at their own thresholds rather than common operating budgets | Gate-6: comparison table must show nominal budget, achieved calibration FPR, achieved held-out control FPR | Compare at common budgets and disclose empirical deviations | Req 2.1 |
| R15 | Nondeterministic IF output | IsolationForest changes with seed | Gate-3: all three configured seeds are present and deterministic per seed | Run seeds 42/123/2024 and record all seeds in metadata | Req 2.1 |
| R16 | Threshold leakage / same-set tuning | Selecting a threshold on the reported 37,000 benign control or protected Backdoor labels inflates performance | Gate-4: calibration source must be the tier's declared source (Tier A: resolved clean benign population; Tier B: `CAL_CONTROL`); evaluation source must be that tier's held-out control + Backdoor | Enforce calibration/evaluation population separation in S3 | Req 1.2, 1.5 |
| R17 | Seed-threshold reuse | Applying seed-42 threshold to seeds 123/2024 invalidates matched-FPR claims | Gate-4: threshold ID includes seed | Calibrate each meta-learner seed independently | Req 1.2 |
| R18 | Mixed-model AE ablation | Thresholds imported from EXP_AE_UNSEEN_FAMILY_V1 are not thresholds of the canonical calibration model | Gate-6: all threshold source hashes point to the S1-generated AE calibration RE dump | Compute every rule from one S1-generated calibration RE vector; when untouched VAL is active, this is the regenerated EXP_AE_V1 validation RE vector | Req 2.2 |
| R19 | False preregistration claim | A later-created document is described as though it predated results | Gate-7: compare Git timestamps with experiment timestamps | Use evidence-backed "predeclared" / "post-hoc" terminology | Req 4.2 |
| R20 | Hardcoded expected metrics | Blueprint assumes 582/583, fixed FPR, or exact Macro-F1 without reading current frozen artifacts | Gate-4: reference values are loaded from artifact files | Read reference metrics from existing CSV/JSON; hardcode only population sizes/protocol constants | All |
| R21 | Benign-control population differs between new inference and existing EXP_ZERODAY_V1 | If the 37,000 benign control rows are sampled differently, FPR values won't be comparable | Gate-4: row identity/hash and threshold-0.5 reference must match frozen EXP_ZERODAY_V1 artifact | Reuse the exact benign-control rows; seed 42 is a provenance check only | Req 1.1, 1.2 |
| R22 | Unseen-family population undefined | Per-family recall would be computed on an unverified population | Gate 1/3: counts must equal 44/378/677 | Resolve source in Phase 0; assert counts in S1, S7 | Req 2.1, 2.2 |
| R23 | IF scores missing for evaluation rows | IF cannot be ROC-evaluated or matched-FPR-compared without per-row scores | Gate 3: IF files for VAL, DEV_TEST, zero-day, families | S7 writes per-row scores for all populations | Req 2.1, 1.1 |
| R24 | Calibration-population overlap | If VAL was used for early stopping or model selection, calibration FPR understates held-out FPR | Phase 0 VAL-usage audit; DOC-07 | Disclose (M16); oracle sensitivity column mandatory | Req 1.2, 1.5 |
| R25 | Noisy low-FPR calibration | 0.1% budget rests on about 11 VAL rows | Wide Clopper–Pearson CIs on held-out FPR | Report CIs and achieved FPR; do not claim exact matching | Req 1.2 |
| R26 | AE/IF evaluated under a different protocol from supervised models | Reintroduces the asymmetric comparison the paper criticizes | Gate 6: identical budgets, populations, and rule across models | S3 uses one calibration function for all models | Req 1.2, 2.1 |
| R27 | TOST over-interpreted | Margin chosen after seeing paired counts; Backdoor recall saturated | Gate 5/8 limitations statement | Manuscript states post-hoc margin and scope | Req 2.3 |
| R28 | Benign-control row identity unresolved | FPR values not comparable with EXP_ZERODAY_V1 | Gate 1/3: row-uid hash match | Resolve list in Phase 0; refuse to run while null | Req 1.1, 1.2 |
| R29 | Non-executable consistency check | A comment-only check gives false assurance | Gate 6: S9 exits non-zero on failure | S9 is a real script with reference values read from artifacts | All |
| R30 | Protocol config committed after execution | Undermines "declared before" claims | S9 check 11 (Git timestamps) | Commit configs before running scripts | All |
| R31 | F2 evaluated at different operating points across models | Recreates asymmetric evaluation despite adding F2 | Gate-4/6: F2 columns exist at all four common budgets for every model | Compute F2 from the same S3 thresholds used for every model | Req 1.3 |
| R32 | PR curve omitted while only PR-AUC is shown | Does not satisfy the explicit PR-curve requirement | Gate-6 visual/metadata check | Generate an explicit PR panel beside ROC | Req 1.1 |
| R33 | AE validation REs generated from a different checkpoint | Thresholds and evaluation scores become model-state inconsistent | Gate-4: checkpoint/scaler hash in S1 metadata | Make S1 regeneration from `ae_final.pt` primary; legacy file cross-check only | Req 2.2 |
| R34 | Contaminated VAL treated as clean calibration | Threshold-selection independence is overstated | Gate-1 calibration-source branch | Require untouched VAL or independent untouched benign calibration for headline claims | Req 1.2 |
| R35 | Row-ID collision across split files | Cross-population identity checks become ambiguous | Gate-1 uniqueness check | Prefix IDs with source split | All |
| R36 | Seed predictions pooled into one curve | Produces an undefined pooled curve and can misstate uncertainty | Gate-6 curve aggregation check | Plot per-seed curves or one declared representative seed; never pool | Req 1.1 |
| R37 | Partition shift: VAL (official training partition) vs. evaluation control (official testing partition) makes VAL-calibrated thresholds miss the nominal FPR systematically, recreating the asymmetric-comparison objection | `partition_shift_diagnostic.csv` (realized/nominal ratio, CP flag, KS); Phase-0 provenance check | Two-tier design; committed headline-tier rule; gap reported as a finding | Req 1.2, 1.5, 1.6 |
| R38 | Floating-point `floor(b × N_cal)` off-by-one for some `N_cal` | S3 assertion vs. exact-arithmetic reference | Compute `k` in exact arithmetic (§0.1) | Req 1.2 |
| R39 | F2 or PPV compared across tiers with different prevalence (1.55% vs 3.06%) | Gate 6: prevalence column; no cross-tier F2 table | Label prevalence; compare recall/FPR across tiers only | Req 1.3 |
| R40 | Headline tier chosen after seeing results (forking paths) | S9 check 16: rule-text hash + commit-before-output | Rule committed before S3; decision file generated by S3, not by hand | Req 1.2, 1.6 |
| R41 | Benign DEV_TEST rows influenced development of a scored model, so Tier B is not independent | DEV_TEST-usage audit (S0 item 3) | Label Tier B sensitivity-only and disclose (M16) if not clean | Req 1.2 |

---

## 22. Stop Conditions

Implementation must **stop and report** (not silently proceed) if any of the following occurs:

| Condition | Reason | Affects |
|-----------|--------|---------|
| Any checkpoint, DEV_TEST, or protected-Backdoor SHA mismatch | Integrity / population cannot be authenticated | All |
| `selected_features.json` count ≠ 75 | Feature-set mismatch | All |
| No clean calibration source can be established for either tier (Tier A: untouched VAL / alternate source; Tier B: `CAL_CONTROL` with a clean DEV_TEST-usage audit) for the requested headline matched-FPR analysis | Calibration independence cannot be supported for headline claims; only an explicitly flagged development-contaminated sensitivity analysis may proceed | 1.2, 1.5, 1.3 |
| Duplicate source-prefixed row IDs or forbidden population overlap is detected | Population identity is ambiguous/contaminated | All |
| Unseen-family counts ≠ 44 / 378 / 677 under every candidate source | Per-family results would be on the wrong population | 2.1, 2.2 |
| Benign-control row-uid list cannot be obtained or reconstructed and verified | FPR values would not be comparable with EXP_ZERODAY_V1 | 1.1, 1.2 |
| `populations.yaml` still contains `null` placeholders when S1, S3, S6, or S7 starts | Population identity unresolved | All |
| S1 `self_check.json` reports any failure | Score files invalid | All |
| Stacking DEV_TEST Macro-F1 differs from `h1_results.json` by more than ±1e-6 | Inference or preprocessing mismatch | 1.1, 1.3 |
| Stacking threshold-0.5 FPR differs from `zero_day_metrics.csv` by more than ±1e-3, or Backdoor detections differ | Population or preprocessing mismatch | 1.2 |
| AE mean/std/τ recomputed from VAL REs differ from `threshold_config.json` (relative 1e-4) | VAL RE vector is not the canonical calibration set | 2.2 |
| Saved and regenerated AE VAL REs disagree | Ablation cannot be tied to one model | 2.2 |
| IF scaler hash ≠ frozen AE scaler hash, or IF training rows ≠ 44,800 | Scaling-domain or population error | 2.1 |
| Any calibration call receives an evaluation-population score (incl. any `EVAL_CONTROL` or Backdoor row in Tier B) | Threshold leakage | 1.2, 1.5, 2.1 |
| Tier-B halves overlap, do not union to the benign control, or lists/`split_seed` were not committed before S0/S3 | Tier-B independence cannot be shown | 1.2, 1.5 |
| `headline_tier_rule` not committed before S3 runs, or a headline table uses a tier different from `headline_tier_decision.json` | Forking paths / inconsistent headline | 1.2, 1.6 |
| Any table compares F2 or PPV across tiers | Different prevalence | 1.3 |
| Any seeded model lacks its own threshold set | Seed-specific protocol violated | 1.2, 2.1 |
| Any model lacks F2 at a common matched-FPR budget | Metric symmetry violated | 1.3 |
| ROC/PR S2 pools predictions across seeds | Curve definition invalid | 1.1 |
| Protocol config not committed before its script runs | Rule 14 violated | All |
| TOST code uses a Wilson or normal approximation, the conservative discordance procedure is not used, or the margin is absent from committed config | Invalid statistical protocol | 2.3 |
| VAL-usage audit shows overlap and the decision is not recorded | Calibration-integrity rule 13 | 1.2, 1.5 |
| Submission venue not selected before table/template work | Formatting is venue-dependent | 3.5 |
| Any new result cannot be reconciled with frozen artifacts | Contradiction requires investigation | All |
| Requirements source is reinterpreted differently from this plan | Ambiguity requires human resolution | All |

---

## 23. Definition of Done

A requirement is complete ONLY when ALL of the following are true:

### For each experiment-based requirement (1.1–2.3)

- [ ] Implementation: new script exists and is runnable
- [ ] Configuration: declared in YAML and committed to Git before execution
- [ ] Executed: script ran to completion with no errors
- [ ] Correct population: dataset SHA verified; population counts match specification
- [ ] Correct features: 75 features, EXP_MI_V1_1 order
- [ ] Correct models: checkpoint SHAs match frozen hashes
- [ ] Raw artifact exists: prediction/score/reconstruction-error file is present on disk
- [ ] Calibration artifact exists where thresholds are required
- [ ] Calibration population identity and `N_cal` are recorded and independently supported
- [ ] Source-prefixed row IDs are unique and population overlap policy passes
- [ ] Evaluation is performed on a distinct held-out population
- [ ] Final result artifact exists: derived metric file (ROC CSV, matched-FPR table, etc.)
- [ ] Metrics validated: key metrics match existing verified results where applicable (Gate-4)
- [ ] Threshold leakage check passes: no headline threshold was selected on the reported evaluation population
- [ ] Both calibration tiers computed; the headline tier follows the committed decision rule (Rule 15)
- [ ] Internal consistency: artifact values are logically consistent (Gate-6)
- [ ] Provenance: metadata JSON exists with timestamp, checkpoint SHAs, dataset SHAs, seed, feature count
- [ ] Reported: result correctly and fully represented in the manuscript
- [ ] Reproducible: another researcher can produce the same result using the repository, locked environment, and documented dataset access instructions

### For each manuscript-only requirement (2.4, 3.1–3.5, 4.1–4.3)

- [ ] Evidence artifact exists and validated (if applicable)
- [ ] Manuscript text updated with correct values
- [ ] No contradictory text remaining in paper
- [ ] Table/figure updated if applicable

### Global completion criteria

- [ ] All 18 subrequirements pass their individual definition-of-done
- [ ] No informal language remains in §V and §VI (full list from audit confirmed removed)
- [ ] Author affiliation block follows the selected venue's standard format
- [ ] Email typo corrected
- [ ] Eq.(5) is in §VI.A.2
- [ ] Tables II, III, IV rebuilt in venue template
- [ ] Code/data availability statement includes repository URL
- [ ] Scope decision for Req 4.3 recorded in DOC-08; Limitations (M17) strengthened; no generalization claim beyond UNSW-NB15
- [ ] "Pre-registered" language replaced with evidence-backed "predeclared" only where justified, plus explicit post-hoc timing disclosure where needed
- [ ] All cross-experiment numbers are consistent (Gate-6 for all requirements)
- [ ] Worms 8.04% CI appears in Abstract, Results, Limitations, and Conclusion
- [ ] NN architecture is correctly described as `75 → 128 → 64 → 1` everywhere
- [ ] AE training count correctly describes both 40,320 (early-stopping phase) and 44,800 (final refit)
- [ ] Repository is tagged with the git commit at which all new experiments were completed

---

## 24. Final Implementation Checklist

### Phase 0 — Environment, freeze, discovery

- [ ] `.venv` (Python 3.11) activates via `.\.venv\Scripts\Activate.ps1`
- [ ] `verify_sprint12_freeze.py`, `validate_ae.py` (21 checks), `validate_oof_stacking.py` (24 checks) all PASS
- [ ] Run S0; review `phase0_discovery.json`
- [ ] Resolve unseen-family source (counts 44 / 378 / 677)
- [ ] Resolve clean calibration source and actual `N_cal`
- [ ] Resolve benign-control source-prefixed row-ID list and SHA-256
- [ ] Run and review the population disjointness/overlap matrix
- [ ] Commit the skeleton `populations.yaml` (with `split_seed`) and `matched_fpr.yaml` (with `headline_tier_rule`) BEFORE running S0
- [ ] Review the partition-provenance check and generate/commit the Tier-B `CAL_CONTROL` / `EVAL_CONTROL` lists
- [ ] Review the DEV_TEST-usage audit; record Tier-B eligibility in DOC-07
- [ ] Review VAL-usage audit; record decision in DOC-07
- [ ] Record the non-blocking feature-selection/scaler leakage audit
- [ ] Confirm S1 AE calibration-RE regeneration from `ae_final.pt` + frozen scaler; when untouched VAL is active, mean/std/τ match `threshold_config.json`; otherwise record the alternate clean calibration source and do not use the historical τ as a headline threshold
- [ ] Complete and commit `populations.yaml` and all protocol configs

### Phase 1 — Frozen inference

- [ ] Write and run S1; `self_check.json` all pass
- [ ] Gate 3 score-file checks pass for supervised and AE outputs

### Phase 2 — Isolation Forest

- [ ] Write `stage_f.yaml` and S7; run seeds 42/123/2024
- [ ] Gate 2 passes; per-row IF scores exist for all four populations

### Phase 3 — Conservative exact paired-equivalence analysis

- [ ] Commit `tost.yaml` (δ = 0.01) before running S4
- [ ] Run S4; Gate 5 passes

### Phase 4 — AE threshold family and ablation

- [ ] Run S5 then S6; all thresholds come from the S1-generated AE RE vector for the resolved clean calibration population; when untouched VAL is eligible, this is the regenerated EXP_AE_V1 VAL RE vector from `ae_final.pt`

### Phase 5 — Matched-FPR for all models

- [ ] Run S3; every model and seed calibrated on the same resolved clean benign population only
- [ ] Achieved FPRs and Clopper–Pearson CIs present; oracle columns labelled
- [ ] Both tiers computed; `partition_shift_diagnostic.csv` and `headline_tier_decision.json` written per the committed rule; `k` matches the exact-arithmetic reference

### Phase 6 — ROC/PR/F2 and alert budget

- [ ] Run S2 and S8; figure includes explicit ROC and PR panels for AE, stacking, and IF
- [ ] F2 is reported at all four common matched-FPR budgets for every model; no seed pooling is used for curves

### Phase 7 — Cross-result check

- [ ] Run S9; all configured checks PASS

### Phase 8 — Documentation

- [ ] Write `docs/DOC_PREREGISTRATION_TIMING.md` from S0 Git evidence
- [ ] Write `docs/DOC_SCOPE_DECISION.md` (Req 4.3)
- [ ] Create/commit `requirements-lock.txt` (or equivalent) from the final execution environment
- [ ] Update README with new experiments and repository link; tag the repository

### Phase 9 — Venue and manuscript

- [ ] Select the submission venue and record it
- [ ] Apply M1–M17
- [ ] Apply editorial corrections 3.1–3.5
- [ ] Apply availability and scope items 4.1–4.3
- [ ] Gate 8 passes; manuscript numbers spot-checked against artifacts (at least 3 per new table)
- [ ] Final PDF generated from the corrected source

---

## 25. Final Protocol Summary

Execution order:

**Freeze verification and discovery → clean-calibration-source decision + committed population manifest → frozen supervised + AE inference (AE calibration REs regenerated from `ae_final.pt`) → Isolation Forest (3 seeds) → conservative exact paired-equivalence test on the discordant proportion → AE threshold family and ablation → two-tier (VAL-calibrated + control-split-calibrated) held-out matched-FPR for every model with a pre-committed headline-tier rule → ROC/PR/F2 with explicit ROC and PR panels + alert-budget analysis → executable cross-result check → provenance/locked-environment and preregistration documentation → venue selection and manuscript editing.**

Main protections against overstated results:

- Thresholds are calibrated on the resolved clean benign calibration population and evaluated once on the held-out control; oracle analyses are labelled and excluded from headline claims.
- Every model, including the AE and IF, passes through the same threshold rule, budgets, and populations.
- Each seed is calibrated independently; realized FPR and recall carry Clopper–Pearson CIs.
- Partition shift between the calibration population and the evaluation control is measured (two tiers, committed headline-tier rule), and any realized-vs-nominal FPR gap is reported as a finding, not hidden as noise.
- The AE ablation uses one S1-generated AE calibration-error vector for the resolved clean calibration population; when untouched VAL is active, this is the regenerated EXP_AE_V1 validation-error vector. AE curves come from frozen inference only.
- Populations are defined once, with row-identity hashes checked in every script.
- The statistical analysis uses a conservative exact paired-equivalence test on the discordant proportion, one committed margin, and explicit disclosure that the margin was set after the paired data were seen.
- "Predeclared" and "post-hoc" wording is tied to Git evidence, not file names.
- Conclusion wording is written after the constrained-FPR results exist.
- Alert-budget claims are standardized sensitivity calculations, not enterprise facts inferred from a lab dataset.
- Cross-result consistency is enforced by an executable script, not a checklist stub.

---

*This Version 5.0 blueprint is a planning-only document. No repository files were modified, no experiments were run, and no models were changed in its preparation.*
