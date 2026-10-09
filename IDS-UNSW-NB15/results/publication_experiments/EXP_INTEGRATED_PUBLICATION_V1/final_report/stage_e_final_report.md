# Stage E Final Report: Integrated Publication Evidence & Comparative Analysis
**UNSW-NB15 NIDS Publication Extension**  
**Experiment ID**: `EXP_INTEGRATED_PUBLICATION_V1`  
**Date**: 2026-09-08 17:57:49 UTC  
**Final Status**: `PASS WITH EXPLICIT LIMITATIONS`

---

## 1. Executive Summary
Stage E synthesizes the empirical evidence generated across the canonical baseline experiments (`EXP_ZERODAY_V1`, `EXP_OOF_STACK_V1`, `EXP_AE_V1`), the controlled Stage-B feature ablation (`EXP_NO_TTL_V1`), the multi-seed Stage-C benign-only Autoencoder evaluation (`EXP_AE_UNSEEN_FAMILY_V1`), and the Stage-D inferential statistical layer (`EXP_STATS_ROBUSTNESS_V1`).

Stage E is strictly an evidence integration, statistical auditing, and comparative analysis layer. In accordance with publication-integrity protocols, no models were trained or recalibrated, no feature sets were modified, and all frozen source artifacts remained completely untouched.

Key findings of this integrated synthesis include:
1. **Supervised No-TTL Ablation**: Ensemble classifiers (Random Forest and Stacking) showed minimal observed sensitivity to the removal of TTL features. Differences in Macro-F1 ($|\Delta| \le 0.0020$) and protected Backdoor detections ($|\Delta| \le 2$ out of 583) fell comfortably below preregistered practical materiality thresholds ($|\Delta\text{Macro-F1}| \ge 0.01$, $|\Delta\text{Backdoor}| \ge 6$).
2. **Linear SVM Sensitivity**: The Linear SVM exhibited greater sensitivity to the No-TTL representation ($|\Delta\text{Macro-F1}| = 0.0297$, $|\Delta\text{Backdoor}| = 11$), satisfying preregistered materiality criteria.
3. **Primary Autoencoder Evaluation**: Under the conservative primary threshold (`mean+3σ`), the benign-only reconstruction Autoencoder yielded zero detections across all four evaluated AE-unseen attack families and all three seeds (0/583 Backdoor, 0/44 Worms, 0/378 Shellcode, 0/677 Analysis). Exact 95% Clopper-Pearson upper confidence bounds were established as 0.63% (Backdoor), 8.04% (Worms), 0.97% (Shellcode), and 0.54% (Analysis).
4. **Operating-Point Trade-offs**: In exploratory secondary analysis across 60 matrix cells, relaxed threshold rules recovered partial anomaly detection (e.g., up to 6.00% Backdoor and 13.64% Worms under `p95`), accompanied by higher benign false-positive rates (5.62%–8.60%, corresponding to 2,080–3,182 false alarms per 37,000 benign flows).
5. **Methodological Isolation**: Supervised classification and unsupervised reconstruction anomaly detection address fundamentally different objectives and evaluate distinct task definitions. They are explicitly reported with transparent metric comparability indicators and are never collapsed into an artificial composite ranking or unevaluated fusion model.

---

## 2. Research Questions
This integrated evidence layer directly answers five core research questions:
- **RQ1 (Ensemble Feature Robustness)**: Does removing TTL features materially degrade the detection efficacy of supervised ensemble models?
  - *Answer*: No. Supervised ensemble models (Random Forest and Stacking) exhibited minimal performance shifts that fell well below preregistered materiality criteria.
- **RQ2 (Linear Model Sensitivity)**: Does a linear decision boundary show greater vulnerability to feature representation changes than ensembles?
  - *Answer*: Yes. Linear SVM showed material drops in both Macro-F1 and zero-day Backdoor detection, confirming that linear boundaries depend more heavily on the original feature space.
- **RQ3 (Zero-Day Anomaly Detection)**: Can a benign-only Autoencoder under standard conservative thresholding detect unseen attack families?
  - *Answer*: In the evaluated samples under `mean+3σ`, no detections were observed across four families. Statistical upper bounds bound sensitivity below 0.54%–0.97% (and 8.04% for Worms).
- **RQ4 (Operating-Point Sensitivity)**: Does relaxing reconstruction thresholds reveal latent anomaly signals, and what is the false-alarm cost?
  - *Answer*: Yes. Detection rates increased modestly across selected families, but at a substantial operational cost of 2,080 to 3,182 false positives per 37,000 benign flows.
- **RQ5 (Cross-Paradigm Comparability)**: Can supervised classifiers and anomaly detection autoencoders be directly compared on a single continuous scale?
  - *Answer*: No. They represent fundamentally distinct detection paradigms with heterogeneous objectives, populations, and operational trade-offs.

---

## 3. Experimental Evidence Map
The research synthesis maps across two distinct methodological branches independently evaluated by the Stage-D statistical layer:
```text
                    ┌─ Stage-B No-TTL ─┐
Canonical Supervised ───────────────────┤
                    └─ Stage-D stats ──┘

                    ┌─ Stage-C AE ─────┐
Canonical AE ────────────────────────────┤
                    └─ Stage-D stats ──┘
```
- **Supervised Branch**: Evaluates supervised generalization from canonical 75 features to 72 features (No-TTL ablation) on `development_test.csv` ($N=81,749$) and `protected_unseen_attack.csv` ($N=583$).
- **Autoencoder Branch**: Evaluates unsupervised benign reconstruction on 72 features across three random seeds against four AE-unseen attack families and benign validation flows ($N=37,000$).
- **Statistical Layer (Stage D)**: Provides unified inferential testing, exact paired McNemar contingency evaluations, multiple-testing corrections, exact confidence intervals, and preregistered materiality auditing.

---

## 4. Canonical Supervised Baselines
Canonical baseline performance established under historical Seed 42:
- **4.1 Decision Tree (DT)**: Macro-F1 = 0.8499; Backdoor Detections = 577/583 (98.97%).
- **4.2 Random Forest (RF)**: Macro-F1 = 0.8807; Backdoor Detections = 582/583 (99.83%).
- **4.3 Linear SVM (SVM)**: Macro-F1 = 0.8236; Backdoor Detections = 577/583 (98.97%).
- **4.4 Neural Network (NN)**: Macro-F1 = 0.8943; Backdoor Detections = 578/583 (99.14%).
- **4.5 Canonical Stacking Ensemble**: Macro-F1 = 0.8926; Backdoor Detections = 582/583 (99.83%).

*Anti-Fabrication Guard*: Canonical Backdoor evaluation was conducted strictly under Seed 42 ($N=1$ seed). No synthetic canonical seeds (123 or 2024) have been fabricated.

---

## 5. Canonical AE Baseline
The historical canonical benign-only Autoencoder (`EXP_AE_V1`) was trained on 75 features under Seed 42 using a `mean+3σ` threshold. When evaluated against the protected Backdoor population ($N=583$), it detected 0/583 flows (0.00%).

---

## 6. Stage-B Controlled No-TTL Ablation
Stage B evaluated the removal of `sttl`, `ct_state_ttl`, and `dttl` (72 features remaining; SHA-256: `21c949fc...`) across seeds 42, 123, and 2024:
- **Random Forest**: Macro-F1 mean = 0.8787 (SD = 0.0003); Backdoor detections = 582/583 across all seeds.
- **Stacking Ensemble**: Macro-F1 mean = 0.8886 (SD = 0.0022; Seed 42 verified independently as 0.8909); Backdoor detections mean = 581.0 (SD = 1.0).
- **Descriptive Evaluation**: Summarized as a descriptive three-seed evaluation. Observed seed variation is small but does not constitute formal population-level proof of seed invariance.

---

## 7. Stage-C AE-Unseen-Family Evaluation
Stage C evaluated a bottleneck reconstruction Autoencoder ($72 \rightarrow 12 \rightarrow 6 \rightarrow 12 \rightarrow 72$, 1,974 parameters) trained exclusively on benign flows across seeds 42, 123, and 2024:
- **Backdoor** ($N=583$, globally held-out / zero-day): 0 detections observed across all seeds.
- **Worms** ($N=44$, AE-unseen only; `[SMALL-N WARNING]`): 0 detections observed across all seeds.
- **Shellcode** ($N=378$, AE-unseen only): 0 detections observed across all seeds.
- **Analysis** ($N=677$, AE-unseen only): 0 detections observed across all seeds.
- **Benign False-Positive Rate**: $0.0243\%$ to $0.0595\%$ (9 to 22 false alarms per 37,000 benign flows).

---

## 8. Stage-D Statistical Evidence
Stage D carried forward validated inferential tests:
- **Paired McNemar Tests (Backdoor N=583)**:
  - Stacking: $A=580, B=2, C=0, D=1$; discordant pairs = 2; raw $p=0.5000$, Holm-adjusted $p=1.0000$.
  - Random Forest: $A=582, B=0, C=0, D=1$; discordant pairs = 0; structurally non-informative ($p=1.0000$).
  - Linear SVM: $A=563, B=14, C=3, D=3$; discordant pairs = 17; raw $p=0.01273$, Holm-adjusted $p=0.06363$.
  - Neural Network: $A=571, B=7, C=1, D=4$; discordant pairs = 8; raw $p=0.07031$, Holm-adjusted $p=0.28125$.
  - Decision Tree: $A=576, B=1, C=5, D=1$; discordant pairs = 6; raw $p=0.21875$, Holm-adjusted $p=0.65625$.
- **Canonical AE vs New AE Paired Comparison**: Dynamically resolved: $A=0, B=0, C=0, D=583$; discordant pairs = 0. Status: `STRUCTURALLY_NON_INFORMATIVE`; equivalence is NOT established.

---

## 9. Integrated Comparative Results
Table E1 presents the direct supervised comparison on Seed 42:
| Model | Representation | Dev-Test Pop | Macro-F1 (Canon vs No-TTL) | $\Delta$Macro-F1 | Backdoor Pop | Backdoor Det (Canon vs No-TTL) | $\Delta$Backdoor | Materiality Status | Holm $p$ | Comparability |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| DT | 75 vs 72 | N=81,749 | 0.8499 vs 0.8560 | +0.0061 | N=583 | 577 vs 581 | +4 | BELOW_MATERIALITY | 0.65625 | DIRECTLY_COMPARABLE |
| RF | 75 vs 72 | N=81,749 | 0.8807 vs 0.8791 | -0.0016 | N=583 | 582 vs 582 | 0 | BELOW_MATERIALITY | 1.00000 | DIRECTLY_COMPARABLE |
| SVM | 75 vs 72 | N=81,749 | 0.8236 vs 0.7939 | -0.0297 | N=583 | 577 vs 566 | -11 | MATERIAL_DIFFERENCE | 0.06363 | DIRECTLY_COMPARABLE |
| NN | 75 vs 72 | N=81,749 | 0.8943 vs 0.8874 | -0.0069 | N=583 | 578 vs 572 | -6 | MATERIAL_DIFFERENCE (BD) | 0.28125 | DIRECTLY_COMPARABLE |
| Stacking | 75 vs 72 | N=81,749 | 0.8926 vs 0.8909 | -0.0017 | N=583 | 582 vs 580 | -2 | BELOW_MATERIALITY | 1.00000 | DIRECTLY_COMPARABLE |

---

## 10. Threshold/FPR Operating Points
Evaluating the secondary threshold matrix revealed an empirical trade-off:
- Relaxing the threshold from `mean+3σ` to `p95` recovered modest detection counts for Backdoor (up to 35/583 = 6.00%), Worms (up to 6/44 = 13.64%), Shellcode (up to 9/378 = 2.38%), and Analysis (up to 27/677 = 3.99%).
- This came at an operational false-positive burden: benign FPR rose from ~0.035% (13 false alarms) to 5.62%–8.60% (2,080 to 3,182 false alarms per 37,000 flows).
- All secondary threshold findings are classified as `materiality_status = DESCRIPTIVE ONLY`.

---

## 11. Practical Materiality
Practical materiality was assessed against Stage-D preregistered thresholds:
- Criterion 1: $|\Delta\text{Macro-F1}| \ge 0.01$
- Criterion 2: $|\Delta\text{Backdoor Rate}| \ge 1.0\text{ percentage point}$ (equivalent to $\ge 6$ detections for $N=583$)
Ensemble models (Random Forest and Stacking) showed no material change under either criterion. SVM exceeded both thresholds, confirming greater empirical sensitivity to the evaluated representation.

---

## 12. Cross-Stage Comparability
Comparisons between supervised classifiers and the Autoencoder are explicitly categorized as `NOT_DIRECTLY_COMPARABLE`:
- Macro-F1 measures multi-class discrimination across known categories.
- Benign FPR and detection rates measure unsupervised reconstruction novelty thresholding.
- These metrics must never be averaged, ranked, or normalized into a synthetic composite index.

---

## 13. Claims-vs-Evidence Audit
The claims audit confirmed full compliance with publication standards:
- **Claim A (No-TTL Ensembles)**: Supported against preregistered criteria.
- **Claim B (SVM Sensitivity)**: Supported descriptively based on preregistered criteria.
- **Claim C (Primary AE Zero Detections)**: Formulated as observed sample counts with exact confidence bounds (never 0% true sensitivity).
- **Claim D (Threshold Trade-Off)**: Formulated as an observed operating-point trade-off limited to evaluated cells.
- **Claim E (Overall Defense)**: Universal zero-day defense claims rejected; replaced with bounded empirical characterization.

---

## 14. Limitations
1. **Worms Sample Size ($N=44$)**: Wide 95% confidence interval ($[0.00\%, 8.04\%]$); limited statistical power.
2. **Three-Seed Descriptive Scope**: Multi-seed evaluation provides descriptive variability but not formal population-level proof.
3. **Primary AE Zero Detections**: Primary threshold was conservative, resulting in zero observed detections.
4. **Structural Degeneracy**: Paired McNemar tests for RF and Canonical vs New AE yielded zero discordant pairs, preventing inferential difference testing or proof of equivalence.
5. **Single-Dataset Evaluation**: Evaluated exclusively on UNSW-NB15; generalizability to other networks requires external validation.
6. **Absence of Causality**: Feature ablation isolates representation effects but cannot establish causal mechanisms.

---

## 15. What the Evidence Does Not Establish
- The experiments do NOT establish that the Autoencoder has zero true detection probability for the evaluated attack families.
- The experiments do NOT establish universal unseen-attack protection.
- The experiments do NOT establish that supervised and AE systems are equivalent or interchangeable.
- The experiments do NOT establish causal importance of TTL-related features.
- Three evaluated seeds do NOT constitute formal population-level proof of seed robustness.
- The threshold sensitivity analysis does NOT establish an optimal threshold.
- The integrated analysis does NOT constitute evaluation of a new jointly trained supervised-plus-AE fusion system.

---

## 16. Reproducibility
All results, tables, figures, and audits are reproducible via a single executable command:
```powershell
.venv\Scripts\python.exe publication_experiments/stage_e/scripts/run_stage_e_analysis.py
```
Static validation is executed via:
```powershell
.venv\Scripts\python.exe publication_experiments/stage_e/scripts/run_stage_e_audit.py
```

---

## 17. Final Audit
- **Source Integrity**: PASS
- **Numerical Integrity**: PASS
- **Comparability Integrity**: PASS
- **Statistical Integrity**: PASS
- **Anti-Cherry-Picking**: PASS
- **Isolation**: PASS
- **Final Status**: `PASS WITH EXPLICIT LIMITATIONS`
- **Decision Rationale**: Determined PASS WITH EXPLICIT LIMITATIONS because all 9 audit gates passed and 5 empirical limitation(s) are active: worms_small_sample_n44, primary_ae_zero_detections, paired_structural_degeneracy, exploratory_secondary_thresholds, single_dataset_non_causal

---

## 18. Artifact Manifest
- **Metadata**: `metadata/execution_metadata.json`, `metadata/config_used.yaml`, `metadata/environment.json`
- **Source Manifest**: `source_manifest/source_manifest.json`, `source_manifest/source_manifest.csv`
- **Derivation Registry**: `derivations/derivation_registry.json`, `derivations/derivation_registry.csv`
- **Publication Tables**: `publication_tables/table_E1.csv` through `table_E7.csv`
- **Publication Figures**: `publication_figures/figure_E1.png` through `figure_E8.png`
- **Claims Audit**: `claims_audit/integrated_claims_audit.csv`, `claims_audit/integrated_claims_audit.md`
- **Audits**: `audits/cross_stage_comparability.json`, `audits/numerical_reconciliation.json`, `audits/anti_cherry_picking.json`, `audits/terminology_audit.json`, `audits/source_integrity.json`, `audits/statistical_consistency.json`, `audits/isolation_audit.json`, `audits/final_gate.json`
- **Final Report**: `final_report/stage_e_final_report.md`, `final_report/stage_e_final_report.json`