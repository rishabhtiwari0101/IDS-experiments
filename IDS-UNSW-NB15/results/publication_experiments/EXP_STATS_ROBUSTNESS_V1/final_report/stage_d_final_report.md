# Stage D — Statistical & Robustness Analysis Final Report
## Publication Extension for UNSW-NB15 NIDS

**Execution Timestamp**: 2026-09-08T17:16:57.378186+00:00
**Canonical Commit**: `f694e19` | **Git Commit**: `e08366f9b41c2c77ab8d71c4d75deb3bcce2123e`
**Final Audit Status**: **PASS WITH EXPLICIT LIMITATIONS**

---

## 1. Executive Summary

Stage D executed a publication-grade statistical and robustness analysis of the completed Stage-B (No-TTL feature ablation) and Stage-C (multi-seed benign-only Autoencoder) experiments. All evaluations strictly adhere to immutable project freezes, preregistered materiality rules, exact Clopper-Pearson binomial uncertainty bounds, and row-level paired McNemar testing with Holm multiple-testing adjustment.

## 2. Frozen Source Experiments & Terminology Enforcement

- **Canonical Stacking Ensemble**: Supervised OOF stacking system, 75 features, historical Seed 42, protected Backdoor detection = 582/583.
- **Canonical AE**: Benign-only Autoencoder, 75 features, historical Seed 42, threshold = 11.16006275, Backdoor detection = 0/583.
- **Stage-B No-TTL**: 72 features (removed sttl, ct_state_ttl, dttl; SHA-256 `21c949fc...`), seeds 42, 123, 2024.
- **Stage-C AE**: 72 features, architecture 72 → 12 → 6 → 12 → 72 (1,974 params), seeds 42, 123, 2024, evaluated against 4 AE-unseen families.
- **Attack Family Status**: **Backdoor** is globally held-out from supervised training and AE training. **Worms, Shellcode, Analysis** are AE-unseen (present in supervised TRAIN, absent from AE training).

## 3. Predeclared Materiality Assessment

- **Macro-F1 Materiality Threshold**: Absolute change $\ge 0.01$.
- **Protected Backdoor Materiality Threshold**: Absolute change $\ge 1$ percentage point ($\lceil 583 \times 0.01 \rceil = 6$ detections).

## 4. Supervised Paired McNemar Comparison (Protected Backdoor N=583)

Family 1 contains exactly five supervised paired comparisons (DT, RF, SVM, NN, Stacking). Holm step-down multiple-testing correction is applied across these five p-values ($m=5$). Family 2 is kept separate and is not Holm-corrected.

The RF paired comparison resulted in A=582, B=0, C=0, D=1 (discordant pairs B+C=0) and is structurally non-informative for the McNemar test. However, RF is strictly retained in the multiple-testing inventory to ensure full evaluation of Family 1 with $m=5$.

| Model | Both Correct (A) | Canon Only (B) | No-TTL Only (C) | Neither (D) | Discordant (B+C) | Raw p | Holm p | Test Status | Materiality |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| DT | 576 | 1 | 5 | 1 | 6 | 0.21875 | 0.65625 | INFORMATIVE | BELOW THRESHOLD |
| RF | 582 | 0 | 0 | 1 | 0 | 1.00000 | 1.00000 | STRUCTURALLY_NON_INFORMATIVE | BELOW THRESHOLD |
| SVM | 563 | 14 | 3 | 3 | 17 | 0.01273 | 0.06363 | INFORMATIVE | MATERIAL |
| NN | 571 | 7 | 1 | 4 | 8 | 0.07031 | 0.28125 | INFORMATIVE | MATERIAL |
| Stacking | 580 | 2 | 0 | 1 | 2 | 0.50000 | 1.00000 | INFORMATIVE | BELOW THRESHOLD |

## 5. Canonical AE vs New AE Paired Comparison (Computed from Row Predictions)

- Contingency: A=0, B=0, C=0, D=583
- Discordant Pairs: 0 (B+C)
- Classification: **STRUCTURALLY_NON_INFORMATIVE**
- Scientific Conclusion: Computed A=0, B=0, C=0, D=583. Zero discordant pairs observed (B=0, C=0); test is structurally non-informative and cannot evaluate difference or establish equivalence.

## 6. Stage-C Primary AE Detection & Zero-Detection Uncertainty

| Family | Status | N | Observed Detections | Exact 95% Clopper-Pearson CI | Exact 95% Upper Bound | Warning |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| BACKDOOR | globally held-out / zero-day | 583 | 0/583 (0.00%) | [0.00%–0.63%] | **0.63%** | NONE |
| WORMS | AE-unseen | 44 | 0/44 (0.00%) | [0.00%–8.04%] | **8.04%** | [SMALL-N WARNING] |
| SHELLCODE | AE-unseen | 378 | 0/378 (0.00%) | [0.00%–0.97%] | **0.97%** | NONE |
| ANALYSIS | AE-unseen | 677 | 0/677 (0.00%) | [0.00%–0.54%] | **0.54%** | NONE |

## 7. Observed Threshold Trade-Off Analysis

Several relaxed threshold operating points increased observed detections for selected AE-unseen attack families, accompanied in the corresponding evaluated settings by higher benign false-positive rates:
- In the 60-cell secondary threshold detection matrix (Table D6) and 15-cell benign FPR matrix (Table D7, Table D8): at **p95** (Seed 42), Backdoor detection reached 35/583 (6.00%), Worms reached 6/44 (13.64%), Shellcode reached 9/378 (2.38%), and Analysis reached 27/677 (3.99%).
- Accompanied in evaluated settings by higher benign false-positive rates: benign dev-test FPR increased from 0.0351% (13/37,000) at mean+3sigma to 5.6216% (2,080/37,000) at p95 in Seed 42, and up to 8.6000% (3,182/37,000) in Seed 123.
- Operating point selection materially affects detection behavior. This trade-off is observed descriptively at specific evaluated operating points and is not claimed as a universal continuous law across all possible thresholds or attack types. No single threshold is globally optimal.

## 8. STAGE D SCIENTIFIC DECISION SUMMARY

- **No-TTL Practical Robustness**: **SUPPORTED**
  - *Evidence*: Stacking and RF changes fell below practical materiality thresholds (|delta_Backdoor| < 6, |delta_Macro-F1| < 0.01).
  - *Supporting Artifacts*: publication_tables/table_D1.csv, publication_tables/table_D12.csv
- **RF Practical Stability**: **SUPPORTED**
  - *Evidence*: RF Backdoor detection and Macro-F1 showed zero observed change under Seed 42, remaining below practical materiality thresholds.
  - *Supporting Artifacts*: publication_tables/table_D1.csv, publication_tables/table_D2.csv
- **Stacking Practical Stability**: **SUPPORTED**
  - *Evidence*: Stacking showed delta Backdoor = -2 (< 6) and delta Macro-F1 = -0.0017 (< 0.01).
  - *Supporting Artifacts*: publication_tables/table_D1.csv, publication_tables/table_D2.csv
- **SVM Representation Sensitivity**: **SUPPORTED DESCRIPTIVELY**
  - *Evidence*: Linear SVM exhibited material drops (delta Backdoor = -11 >= 6, delta Macro-F1 = -0.0184 >= 0.01).
  - *Supporting Artifacts*: publication_tables/table_D2.csv, publication_tables/table_D9.csv
- **AE Primary-Threshold Detection**: **NOT SUPPORTED**
  - *Evidence*: 0 detections observed across all 4 AE-unseen attack families under primary threshold mean+3sigma.
  - *Supporting Artifacts*: publication_tables/table_D4.csv, publication_tables/table_D11.csv
- **Threshold Trade-Off**: **SUPPORTED DESCRIPTIVELY**
  - *Evidence*: Several relaxed threshold operating points increased observed detections for selected AE-unseen attack families, accompanied in the corresponding evaluated settings by higher benign false-positive rates.
  - *Supporting Artifacts*: publication_tables/table_D6.csv, publication_tables/table_D7.csv, publication_tables/table_D8.csv
- **Three-Seed Characterization**: **DESCRIPTIVE ONLY**
  - *Evidence*: The three evaluated seeds (42, 123, 2024) are summarized descriptively. Observed seed-to-seed variation is reported using mean, SD, minimum, maximum, and range. No formal preregistered criterion for seed “consistency” was defined; therefore the analysis does not establish formal seed robustness.
  - *Supporting Artifacts*: publication_tables/table_D1.csv, stage_b_statistics/seed_robustness.csv
- **Canonical AE vs New AE Equivalence**: **NOT ESTABLISHED — STRUCTURAL DEGENERACY**
  - *Evidence*: Computed contingency table A=0, B=0, C=0, D=583 (discordant pairs=0).
  - *Supporting Artifacts*: publication_tables/table_D9.csv, paired_tests/mcnemar_results.csv

## 9. Final Audit Gate Results

**Final Status**: **PASS WITH EXPLICIT LIMITATIONS**

All computational, source verification, semantic validation, invariant, reproducibility, and directory isolation checks passed. The status is qualified as `PASS WITH EXPLICIT LIMITATIONS` due to genuine empirical constraints: small sample size for Worms (N=44), zero observed detections for the AE primary threshold across all seeds, structural degeneracy in the canonical vs new AE paired test, and evaluation across three random seeds.
