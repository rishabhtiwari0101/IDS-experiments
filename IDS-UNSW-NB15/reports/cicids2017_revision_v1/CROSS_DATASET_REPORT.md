# Sprint 6 Cross-Dataset Comparative Master Report: UNSW-NB15 vs CIC-IDS-2017

**Date:** 2026-10-07  
**Sprint:** Sprint 6 (Matched-FPR, Deployment Analysis, Cross-Dataset Comparison & Figures)  
**Status:** PASS — ALL GATES SATISFIED  
**Authoritative Artifact:** `results/cicids2017_revision_v1/cross_dataset/s25_cross_dataset_master_table.csv`  
**Governing Documents:**
- `Review_Exp/FINAL_REVIEWER_REVISION_SPRINT_PLAN_v2.md` (§ 8, Sprint 6)
- `Review_Exp/REVISION_METHODOLOGY_BLUEPRINT_v2.md` (§ 4.5, § 17)

---

## 1. Executive Summary & Scientific Synthesis

This report provides the authoritative cross-dataset comparison between **UNSW-NB15** and **CIC-IDS-2017**. To preserve scientific integrity:
1. **Zero Retraining / Zero Recomputation:** Every UNSW number is read directly from frozen publication artifacts (`results/zero_day/`, `revision_v5/results/`, `results/cicids2017_revision_v1/transformer/unsw/`).
2. **Replication Fidelity:** Evaluates whether architectural behaviors (supervised generalization, unsupervised anomaly blindness, shortcut invariance, hybrid rescue, transformer parity) transfer across distinct benchmark environments.

### Headline Cross-Dataset Findings:
- **Divergence in Supervised Zero-Day Generalization:**  
  On UNSW-NB15, tree ensembles and Stacking successfully detect unseen Backdoor attacks ($99.83\%$ recall). Conversely, on CIC-IDS-2017, Stacking and Random Forest fail completely on unseen Botnet flows ($0.00\%$ recall). This demonstrates that supervised zero-day transfer is not an inherent property of tree-based models, but depends heavily on attack-manifold topology and feature representation.
- **Replication of Heavy-Tail Anomaly Blindness:**  
  Both datasets confirm severe anomaly suppression for Autoencoders and Isolation Forests at standard operating points ($\mu + 3\sigma$). At this threshold, Autoencoders achieve $0.00\%$ recall on UNSW Backdoor and only $0.60\%$ recall on CIC Bot.
- **Replication of Negligible Hybrid Rescue (Q3):**  
  In both datasets, OR-fusion ($\text{C01 OR AE}$) rescues an operationally negligible fraction of zero-day attacks ($+0$ flows on UNSW; $+37.7$ flows or $1.93\%$ on CIC) while dramatically inflating operational false alarms ($+13$ false alarms on UNSW; $+49.3$ false alarms on CIC).
- **Replication of Random Forest Structural Resilience to Shortcuts:**  
  In both benchmarks, removing shortcut features (`ct_dst_sport_ltm` on UNSW; `Destination Port` and `Init_Win_bytes_backward` on CIC) satisfies two one-sided tests (TOST) for equivalence within $|\Delta| < 0.01$ Macro-F1 ($p < 0.003$ on UNSW; $p < 10^{-5}$ on CIC).
- **Parity of Modern Tabular Deep Baselines:**  
  FT-Transformer achieves high in-distribution performance on both benchmarks ($0.8488$ Macro-F1 on UNSW; $0.9864$ Macro-F1 on CIC) and mirrors the exact dataset-specific zero-day behavior of tree baselines ($100.0\%$ recall on UNSW Backdoor; $0.00\%$ recall on CIC Bot).

---

## 2. Master Comparative Table

| Dimension | Metric / Phenomenon | UNSW-NB15 Value | CIC-IDS-2017 Value | Comparability Status | Methodological Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Dataset Scale** | Total Raw Benchmark Flows | 254,004 flows (Train: 162k, Dev-Test: 82k) | 1,123,383 flows (Train: 340k, Dev-Test: 744k) | Direct Comparison | CIC is 4.4x larger in flow volume. |
| **Zero-Day Class** | Protected Attack Family | Backdoor ($N = 583$ flows) | Botnet / ARES ($N = 1,948$ flows) | **Distinct Attack Classes [Footnote B]** | Backdoor spans multiple protocols; Bot is IRC C&C traffic. |
| **Prevalence** | Natural Evaluation Attack Prevalence | 3.06% ($583 / 19,083$) | 9.53% ($1,948 / 20,448$) | **Standardization Required [Footnote A]** | Standardized $\pi=0.0306$ used for unbiased precision comparison. |
| **Feature Space** | Feature Dimensionality & Modality | $K=75$ (Baselines) / $K=50$ (FT-Transformer) [Footnote C] | $K^*=69$ (Full) / $D=67$ (Ablated) | **Modality Difference [Footnote C]** | UNSW contains one-hot categoricals; CIC is purely continuous flow statistics. |
| **Stacking** | Zero-Day Detection Recall | **99.83%** ($582 / 583$) | **0.00%** ($0 / 1,948$) | Dramatic Divergence | Ensembles generalize on UNSW Backdoor, but fail completely on CIC Bot. |
| **Stacking** | Benign False Positive Rate (FPR) | 19.19% ($1,918.9$ alerts / 10k) | 0.087% ($8.74$ alerts / 10k) | Direct Comparison | CIC stacking maintains drastically lower operational false alarm load. |
| **Stacking** | Standardized Precision ($\pi = 0.0306$) | 14.11% (Natural: 7.58%) | 0.00% (Natural: 0.00%) | Standardized Metric [Footnote A] | Derived comparison metric per Blueprint § 4.5. |
| **Autoencoder** | Zero-Day Recall at $\mu + 3\sigma$ | **0.00%** ($0 / 583$) | **0.60%** ($12.0 / 1,948$) | **Replicated Phenomenon** | Both datasets confirm severe anomaly suppression at $\mu+3\sigma$. |
| **Autoencoder** | Control FPR at $\mu + 3\sigma$ | 0.049% ($4.86$ alerts / 10k) | 0.146% ($14.59$ alerts / 10k) | Direct Comparison | Low benign FPR achieved at the expense of missing $>99\%$ of zero-day attacks. |
| **Isolation Forest** | Zero-Day Recall at $\mu + 3\sigma$ | **0.00%** ($0 / 583$) | **1.98%** ($34.7 / 1,948$) | Direct Comparison | Isolation Forest mirrors AE anomaly blindness on zero-day attack manifolds. |
| **Hybrid C06** | Zero-Day Attack Rescue (Q3) | **+0 flows** (0.0% rescue) | **+37.7 flows** (1.93% rescue) | Direct Comparison | OR-fusion yields negligible rescue ($<2\%$) across both benchmarks. |
| **Hybrid C06** | Operational Extra False Alarms | **+13 False Alarms** (+3.5 alerts / 10k) | **+49.3 False Alarms** (+27.4 alerts / 10k) | Direct Comparison | Rescue benefit is heavily outweighed by triage alert burden. |
| **Ablation (RF)** | Shortcut Invariance (TOST Equivalence) | **Equivalence Supported** ($\delta=0.01, p=0.0029$) | **Equivalence Supported** ($\delta=0.01, p < 10^{-5}$) | **Replicated Structural Finding** | Removing shortcuts does not materially alter RF Macro-F1 ($|\Delta| < 0.01$). |
| **FT-Transformer** | In-Distribution DEV_TEST Macro-F1 | 0.8488 ($K=50$) | 0.9864 ($K^*=69$) | Tabular DL Comparison | High in-distribution classification performance on both datasets. |
| **FT-Transformer** | Zero-Day Detection Recall | **100.00%** ($583 / 583$) | **0.00%** ($0 / 1,948$) | **Asymmetry Parity** | Replicates tree-baseline zero-day behavior on each respective dataset. |

---

## 3. Mandatory Comparability Footnotes

### Footnote A — Evaluation Prevalence Discrepancy
> **Evaluation Attack Prevalence:** In UNSW-NB15, the held-out zero-day test set consists of 583 Backdoor flows and 18,500 evaluation control benign flows, yielding a natural prevalence of $\pi_{\text{UNSW}} = 583 / 19,083 \approx 3.055\%$. In CIC-IDS-2017, the zero-day test set contains 1,948 Botnet flows and 18,500 evaluation control benign flows, yielding a natural prevalence of $\pi_{\text{CIC}} = 1,948 / 20,448 \approx 9.527\%$. Because unadjusted precision is mathematically tied to base-rate prevalence, natural precision values cannot be compared directly across datasets. All rigorous cross-dataset precision comparisons are standardized to the benchmark reference prevalence of $\pi = 0.0306$ per Blueprint § 4.5.

### Footnote B — Protected Attack Family Differences
> **Attack Classes:** The protected zero-day classes represent fundamentally distinct threat profiles. UNSW-NB15 Backdoor consists of multi-vector interactive exploit attempts distributed across various transport protocols, whereas CIC-IDS-2017 Bot comprises command-and-control (C&C) IRC traffic from the Ares botnet. They are not equivalent attack classes, and differences in zero-day detection recall reflect distinct geometric separation from normal baseline traffic.

### Footnote C — Feature Representation and UNSW FT-Transformer Feature Count
> **Feature Space & Dimensionality:** CIC-IDS-2017 uses $K^* = 69$ purely continuous numeric flow summary statistics derived from bidirectional traffic flows. In contrast, UNSW-NB15 legacy baselines utilize $K = 75$ mutual-information-selected features (incorporating one-hot encoded protocol, state, and service categoricals under `EXP_MI_V1_1`). The UNSW FT-Transformer model evaluated in Sprint 5 utilized $K = 50$ continuous features (`EXP_MI_V1`). The 50-feature subset is the exact prefix of the first 50 features of the 75-feature ranking. This distinction is explicitly reported.

### Footnote D — Statistical Resolution at 0.1% Budget
> **Low-Resolution Boundary:** On an evaluation control population of $N = 18,500$ benign flows, a nominal false-positive budget of $\alpha = 0.1\%$ produces an expected false alarm count of only $k = 18.5$. Per Blueprint § 16, any operating point with fewer than 20 expected events falls below adequate statistical resolution and is flagged as `LOW_RESOLUTION`. Nominal budgets of $0.5\%$, $1.0\%$, and $5.0\%$ satisfy adequate resolution ($92.5$, $185$, and $925$ expected events, respectively).

---

## 4. Source Traceability Matrix

Every single value reported in this cross-dataset synthesis is traceable to an authoritative frozen artifact on disk:

| Dataset | Metric / Model | Saved Artifact Path | Key / Column |
| :--- | :--- | :--- | :--- |
| **UNSW** | Baseline Zero-Day Table | `results/zero_day/EXP_ZERODAY_V1/analysis/table_1_zero_day_metrics.csv` | Full table |
| **UNSW** | Detection Overlap (Q1-Q4) | `results/zero_day/EXP_ZERODAY_V1/analysis/detection_overlap.csv` | `quadrant`, `count` |
| **UNSW** | Matched-FPR Table | `revision_v5/results/publication_experiments/EXP_MATCHED_FPR_V1/matched_fpr_table.csv` | Full table |
| **UNSW** | TOST RF Equivalence | `revision_v5/results/publication_experiments/EXP_TOST_V1/tost_rf_equivalence.json` | `tost_results` |
| **UNSW** | FT-Transformer Results | `results/cicids2017_revision_v1/transformer/unsw/s22_ft_transformer_unsw_results.json` | `mean_dev_test_macro_f1` |
| **CIC** | Supervised DEV_TEST | `results/cicids2017_revision_v1/supervised/dev_test_evaluation.json` | `aggregated.stacking` |
| **CIC** | Zero-Day Evaluations | `results/cicids2017_revision_v1/zero_day/zero_day_evaluation_summary.json` | `results` array |
| **CIC** | Matched-FPR Table | `results/cicids2017_revision_v1/matched_fpr/s23_matched_fpr_table.csv` | Full table |
| **CIC** | Hybrid C06 Marker | `results/cicids2017_revision_v1/matched_fpr/s23_c06_hybrid_marker.json` | Full array |
| **CIC** | TOST RF Equivalence | `results/cicids2017_revision_v1/ablation/s19_ablation_evaluation.json` | `tost_rf_macro_f1` |
| **CIC** | FT-Transformer Results | `results/cicids2017_revision_v1/ft_transformer/s21_ft_transformer_cic_results.json` | `results.full` |

---

## 5. Scientific Reporting Integrity Statements

1. **No Manufactured Symmetry:**  
   We report the empirical data exactly as observed. We do not attempt to force artificial symmetry between UNSW-NB15 (where trees generalize to Backdoor) and CIC-IDS-2017 (where trees fail completely on Bot). The discrepancy is an important scientific finding.
2. **Equivalence vs Importance:**  
   Statistical equivalence in TOST demonstrates that the two shortcut features are not required for in-distribution classification; it does not imply that shortcuts are benign in general network operations.
3. **FT-Transformer Scope:**  
   FT-Transformer is reported as **a representative modern deep tabular baseline**, not an exhaustive evaluation of all transformer architectures or attention variants.
4. **Generalization Scope:**  
   Empirical findings on two benchmark datasets cannot be extrapolated into universal laws of zero-day network intrusion detection.
