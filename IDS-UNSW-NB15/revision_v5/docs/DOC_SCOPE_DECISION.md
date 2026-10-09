# DOC-09: Scope Decision, Non-Claims, and Research Limitations

**Date:** 2026-09-28  
**Scope:** Revision 5 (`revision_v5`) Publication Experiments  
**Governing Authority:** [`docs/IMPLEMENTATION_BLUEPRINT_v5.md`](IMPLEMENTATION_BLUEPRINT_v5.md) (§5F; §13; §18; Manuscript Items M8, M16, M17; `DECISIONS.md`)  

---

## 1. Primary Research Scope & Objective

The primary objective of `revision_v5` is to establish methodological rigor in evaluating intrusion detection system (IDS) models on the **UNSW-NB15** dataset under strict data-leakage controls, partition-shift diagnostics, and a controlled zero-day simulation (held-out Backdoor attack family).

Key experimental foci implemented in stages S0 through S9:
1. **Calibration Integrity & Partition Shift Diagnostics:** Documenting that realized FPR falls outside the nominal budget’s Clopper-Pearson CI for 43/44 Tier A cells, consistent with partition shift between validation and held-out test distributions (Tier A vs Tier B); noting that Tier B nominal budget lies inside the eval-half CI for 34 of 44 cells (Stages S0, S3).
2. **Constrained-FPR Benchmark Comparison:** Evaluating supervised ensembles, unsupervised autoencoders, and Isolation Forest models under identical operational budgets (0.1%, 0.5%, 1%, 5% FPR) using exact order-statistic thresholds (Stages S3, S7).
3. **Equivalence Testing:** Evaluating the impact of feature engineering (removal of TTL) using conservative paired equivalence testing (Stage S4).
4. **Threshold Ablations & Operational Alert Budgets:** Measuring the real-world operational burden (alerts per 10,000 benign flows) and testing heuristic threshold rules (MAD, percentiles, standard deviation) on both trained and zero-day attack families (Stages S5, S6, S8).
5. **Cross-Stage Integrity Reconciliation:** Verifying that all intermediate results, partition partitions, and historical baselines cross-reconcile bit-for-bit without discrepancy (Stage S9).

---

## 2. Second-Dataset Scope Decision (Req 4.3 / §5F / M17)

Per blueprint §5F and §13:
- **Decision:** Evaluation on a second independent network intrusion dataset (e.g., CIC-IDS-2017) is **excluded from the empirical scope** of this revision.
- **Audit Basis:** The repository is frozen around the UNSW-NB15 raw feature vectors, official splits, and fitted feature selection pipelines (`EXP_MI_V1_1`). Raw PCAP capture files and cross-dataset network feature extraction pipelines are not present in the frozen repository baseline.
- **Reporting Requirement (M17):** This exclusion is explicitly documented in the manuscript Limitations section (M17) as an empirical constraint of the current study. The paper explicitly scopes its experimental findings to the UNSW-NB15 feature representation and evaluation splits.

---

## 3. Explicit Non-Claims

To ensure complete scientific integrity, the research artifacts and manuscript make the following explicit non-claims:

1. **No Operational Deployment Claim:**
   - The authors do not claim that any evaluated model (supervised or unsupervised) is ready for uncalibrated out-of-the-box production deployment.
   - Empirical findings document that the default classification threshold ($t = 0.5$) incurs an unacceptable false positive rate of **~19% on benign network traffic** (19.03% on `EVAL_CONTROL` [3,520 / 18,500]; 19.19% on the full benign control [7,100 / 37,000]), generating approximately 1,900 false alarms per 10,000 flows (Stage S2, S8, DECISIONS.md BN-08).

2. **No Blanket Paradigm Superiority Claim:**
   - The paper does not claim that unsupervised anomaly detection is superior to supervised learning for zero-day threats.
   - At operationally viable false positive rates ($\le 1.4\%$), the deep reconstruction Autoencoder achieves near-zero Backdoor detection (0% to 6.5% recall across percentile and $3\sigma$ rules; Stage S6).
   - Under the headline Tier B matched-FPR calibration, supervised Stacking achieves measured zero-day Backdoor recall of **81.5%–81.8%** at 0.1% budget, **89.5%–91.3%** at 0.5% budget, **93.3%–94.0%** at 1% budget, and **98.3%** at 5% budget on the evaluation half (across seeds 42, 123, 2024 in `matched_fpr_tier_b.csv`), with seed 123 at 5% budget tie-flagged (`tie_unattainable=True`).

3. **No Claim of Fully Pre-Registered Equivalence Margins:**
   - Per blueprint §0 Rule 7 and Manuscript Item M8, the equivalence margin ($\delta = 0.01$) used in the conservative exact paired-equivalence test in Stage S4 is explicitly disclosed as **post-hoc**. The discordant counts $(582, 0, 0, 1)$ between canonical RF and no-TTL RF were known from prior sprint reports before the equivalence margin was committed in `tost.yaml`.

---

## 4. Key Experimental Trace & Git Hash Index

All findings and non-claims are backed by committed code, deterministic configs, and immutable output artifacts:

| Stage | Experiment ID | Git Commit | Key Output Artifact | Primary Measured Finding |
|:---|:---|:---|:---|:---|
| **S0** | `EXP_DISCOVERY_V1` | `4accd8c` | `phase0_discovery.json`, `DOC-07` | Clean VAL confirmed; Tier A and Tier B both eligible. |
| **S1** | `EXP_PROB_INFERENCE_V1` | `1818b81` | `zeroday_probabilities.csv` | Zero-training inference; all probability vectors exported. |
| **S3/S7** | `EXP_MATCHED_FPR_V1`, `EXP_IF_V1` | `970f84c` | `matched_fpr_tier_b.csv`, `headline_tier_decision.json` | 43/44 cells shift-affected in Tier A; Headline Tier B decided dynamically. |
| **S2** | `EXP_ROC_PR_V1` | `ad2bd8d` | `fig_roc_pr_zeroday.png` | Stacking zero-day ROC-AUC 0.9966 vs ~19% FPR at default threshold 0.5. |
| **S4** | `EXP_TOST_V1` | `dfeb6f2` | `tost_rf_equivalence.json` | Exact paired equivalence confirmed (conservative exact test, $\delta=0.01$, $p = 0.00285$). |
| **S5** | `EXP_MAD_THRESHOLD_V1` | `468e895` | `mad_thresholds.csv` | Empirical percentiles and MAD thresholds computed on calibration errors. |
| **S6** | `EXP_AE_ABLATION_V1` | `72d9fcd` | `ae_ablation_results.csv` | AE Backdoor recall $\le 6.5\%$ at FPR $\le 1.4\%$; raw MAD $k=3$ recall 90.7% at 23.5% FPR. |
| **S8** | `EXP_ALERT_BUDGET_V1` | `28fbfc5` | `alert_budget_table.csv` | 44 rows; alerts per 10k benign flows computed; 14 tied cells flagged. |
| **S9** | `EXP_CROSS_CHECK_V1` | `7d3074c` | `cross_check_report.json` | 9/9 cross-stage consistency and frozen baseline checks PASS. |
