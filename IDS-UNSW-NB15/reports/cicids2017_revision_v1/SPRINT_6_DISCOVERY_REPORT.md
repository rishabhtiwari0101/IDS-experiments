# SPRINT 6 DISCOVERY REPORT
## Matched-FPR Analysis, Deployment Inference Benchmarking, Cross-Dataset Master Comparison & Publication Vector Figures

**Date:** 2026-10-07  
**Status:** **DISCOVERY COMPLETE — NO EXECUTION UNDERTAKEN**  
**Governing Plan:** `Review_Exp/FINAL_REVIEWER_REVISION_SPRINT_PLAN_v2.md` (§ 8, Sprint 6)  
**Predecessor Report:** `reports/cicids2017_revision_v1/SPRINT_5_REPORT.md` (PASS)

---

## 1. Sprint 5 Gate Verification & System Integrity

All cryptographic and dataset boundary checks confirm that the environment is in an uncompromised, reproducible state:

1. **Sprint 5 Deliverable Verification:**
   - Milestone Report: [`reports/cicids2017_revision_v1/SPRINT_5_REPORT.md`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/SPRINT_5_REPORT.md) (14.8 KB, Verified present).
   - Technical & Statistical Report: [`reports/cicids2017_revision_v1/SHORTCUT_AND_TRANSFORMER_REPORT.md`](file:///c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15/reports/cicids2017_revision_v1/SHORTCUT_AND_TRANSFORMER_REPORT.md) (20.6 KB, Verified present).
2. **Frozen Shortcut List Hash:**
   - Path: `results/cicids2017_revision_v1/shortcut_freeze/shortcut_list_frozen.json`
   - Content: `["Destination Port", "Init_Win_bytes_backward"]` ($k=2$, $K^*=69 \to D_{\text{ablated}}=67$)
   - Expected SHA-256: `5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2`
   - Realized SHA-256: `5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2` (**MATCH — BIT-IDENTICAL**)
3. **UNSW Frozen Benchmark Manifest Integrity:**
   - Manifest: `reports/cicids2017_revision_v1/manifests/UNSW_FROZEN_MANIFEST.sha256`
   - Total Tracked Files: **1,261 files**
   - Missing Files: **0**
   - Mismatched Hashes: **0**
   - Verification Status: **`PASS = True`**
4. **Git Repository Status:**
   - `git diff --stat`: **0 tracked files modified** (clean tree for all frozen and published benchmark files).
   - Untracked files strictly confined to: `Review_Exp/`, `cicids2017/`, `configs/`, `reports/`, `results/`.

---

## 2. Sprint 5 Numerical Consistency Audit

All numerical metrics were cross-referenced against authoritative saved JSON/CSV result files:

### 2.1 CIC-IDS-2017 Models
* **Random Forest (Original $K^*=69$):**
  * Macro-F1 = $0.998563 \pm 0.000018$, Benign FPR = $0.000850$ ($8.50$ alerts/10k), Zero-day Bot Recall = $0.00\%$ ($0 / 1,948$). Sourced from `s10_evaluate_supervised.json`.
* **Stacking (Original $K^*=69$):**
  * Macro-F1 = $0.998755 \pm 0.000035$, Benign FPR = $0.000732$ ($7.32$ alerts/10k), Zero-day Bot Recall = $0.00\%$ ($0 / 1,948$). Sourced from `s10_evaluate_supervised.json`.
* **Ablated Random Forest ($D_{\text{ablated}}=67$):**
  * Macro-F1 = $0.997083 \pm 0.000006$, Benign FPR = $0.001873$ ($18.73$ alerts/10k), Zero-day Bot Recall = $0.00\%$ ($0 / 1,948$). Sourced from `s19_ablation_evaluation.json`.
* **Ablated Stacking ($D_{\text{ablated}}=67$):**
  * Macro-F1 = $0.997956 \pm 0.000033$, Benign FPR = $0.001264$ ($12.64$ alerts/10k), Zero-day Bot Recall = $0.00\%$ ($0 / 1,948$). Sourced from `s19_ablation_evaluation.json`.
* **Standard Autoencoder ($\mu+3\sigma$):**
  * Bot Recall = $0.00616 \pm 0.00055$ ($12.0 / 1,948$), Held-out Control FPR = $0.001477$ ($14.77$ alerts/10k). Sourced from `s16_evaluate_zero_day.json`.
* **Isolation Forest ($\mu+3\sigma$):**
  * Bot Recall = $0.01779 \pm 0.00422$ ($34.67 / 1,948$), Held-out Control FPR = $0.025189$ ($251.89$ alerts/10k). Sourced from `s16_evaluate_zero_day.json`.
* **CIC FT-Transformer (Full $K^*=69$):**
  * Macro-F1 = $0.986365 \pm 0.003190$, Benign FPR = $0.009251$ ($92.51$ alerts/10k), Control alerts/10k = $96.58$, Zero-day Bot Recall = $0.00\%$ ($0 / 1,948$, 95% Wilson CI: $[0.0000, 0.0020]$). Sourced from `s21_ft_transformer_cic_results.json`.
* **CIC FT-Transformer (Ablated $D=67$):**
  * Macro-F1 = $0.980469 \pm 0.003605$, Benign FPR = $0.012892$ ($128.92$ alerts/10k), Control alerts/10k = $137.48$, Zero-day Bot Recall = $0.00\%$ ($0 / 1,948$). Sourced from `s21_ft_transformer_cic_results.json`.

---

## 3. UNSW Feature-Dimension Discrepancy Resolution ($K=50$ vs $D=75$)

### 3.1 The Evidence
1. **Feature File Actually Used:**
   - Script `cicids2017/src/s22_train_ft_transformer_unsw.py` loaded `results/feature_selection/EXP_MI_V1/selected_features.json` (Line 74).
   - This file specifies `"selected_k": 50` and contains an array of 50 feature names (`sbytes`, `sttl`, `dbytes`, ..., `service_pop3`).
2. **Features Actually Fed to Model:**
   - `proc_train.X[:, feat_indices]` sliced exactly 50 columns.
   - The FT-Transformer instantiated `FTTransformerUNSW(n_features=50, d_model=64, ...)` with $104,001$ parameters and sequence length $50+1=51$.
3. **Preprocessing Pipeline Artifact:**
   - `PreprocessingPipeline(experiment_id="FT_TRANSFORMER_UNSW")` from `src.preprocessing.preprocessing_pipeline` fitted on `data/splits/train.csv` (162,395 rows), yielding an unscaled matrix of 193 columns from which the 50 selected features were indexed.
4. **Saved Model Metadata:**
   - `results/cicids2017_revision_v1/transformer/unsw/s22_ft_transformer_unsw_results.json` records:
     `"K_unsw": 50`, `"D": 50`, `"seq_len": 51`, and lists the 50 features.
5. **Origin of $D=75$ in Earlier Discovery:**
   - In the legacy UNSW codebase, `EXP_MI_V1_1` (protocol version 1.1) was run after `EXP_MI_V1`.
   - `results/feature_selection/EXP_MI_V1_1/selected_features.json` contains `"selected_k": 75`.
   - All legacy UNSW published models (DT, RF, LinearSVC, IDSNet, Stacking, Autoencoder) were trained on the **75 features of `EXP_MI_V1_1`**.
   - **Critical Subsumption Finding:** The 50 features in `EXP_MI_V1` are literally the **exact prefix of the first 50 features** in `EXP_MI_V1_1` (`features_v1 == features_v1_1[:50]` is `True`).

### 3.2 Formal Classification
* **Internal Sprint 5 Reporting:** **RESOLVED REPORTING DISCREPANCY**.
  * The code, model weights, results JSON, and Sprint 5 report text are 100% consistent with each other: all declare and evaluate $K=50$.
* **Cross-Model Parity Context:** **DOCUMENTED METHODOLOGICAL VARIANT**.
  * For the final manuscript cross-dataset comparison, the paper must explicitly footnote that while legacy UNSW tree/stacking baselines used the $K=75$ MI-selected set, the FT-Transformer baseline evaluated the top $K=50$ MI-selected set.
  * *Optionally*, if the user desires strict $K=75$ parity, a supplementary FT-Transformer run with $K=75$ can be executed during revision, but the existing $K=50$ experiment is completely sound, leak-free, and reproducible.

---

## 4. Matched-FPR Reuse Matrix & Implementation Strategy

| Capability | Existing Blueprint / Script | Class | Reuse Strategy |
|---|---|---|---|
| **Matched-FPR Pipeline** | `revision_v5/.../run_matched_fpr_analysis.py` | **B** | Adapt order-statistic calibration and zero-training guard into `cicids2017/src/s23_matched_fpr_analysis.py`. |
| **Exact Rational Arithmetic** | `compute_exact_k` (using `fractions.Fraction`) | **A** | Direct reuse: $k = \lfloor \text{budget} \times N_{\text{cal}} \rfloor$. |
| **Order-Statistic Threshold** | `calibrate_threshold` ($t = \text{sorted\_desc}[k]$) | **A** | Direct reuse: strict inequality alert rule ($\text{score} > t$). |
| **FPR Exact CI** | `clopper_pearson_ci` (`scipy.stats.beta.ppf`) | **A** | Direct reuse: exact Clopper-Pearson 95% binomial CI. |
| **Recall Score CI** | `wilson_ci` (`scipy.stats.binomtest`) | **A** | Direct reuse: Wilson score interval for attack recall. |
| **Alerts / 10k Scaling** | `revision_v5/.../run_alert_budget_analysis.py` | **A** | Direct reuse: $\text{alerts\_per\_10k} = \frac{\text{FP}}{N_{\text{control}}} \times 10,000$. |
| **Standardized Precision** | Formula in Plan § 4.5 | **A** | Direct reuse: $P_{\text{std}} = \frac{R \cdot \pi}{R \cdot \pi + \text{FPR} \cdot (1 - \pi)}$ with $\pi = 0.0306$. |
| **ROC-AUC & PR-AUC** | `run_roc_pr_analysis.py` (`sklearn.metrics`) | **A** | Direct reuse: computed on held-out control + zero-day attack set. |
| **Deployment Benchmark** | None in repository | **C** | New implementation: `cicids2017/src/s24_deployment_benchmark.py`. |
| **Cross-Dataset Master Table**| `cross_model_comparison.csv` (UNSW) | **B** | Adapt into `cicids2017/src/s25_cross_dataset_table.py` reading saved JSON/CSV. |
| **Publication Vector Figures** | `run_roc_pr_analysis.py` (`matplotlib.use("Agg")`)| **B** | Adapt into `cicids2017/src/s26_generate_figures.py` (exporting both PNG and PDF). |

---

## 5. FPR Budgets & Low-Resolution Operating Rule

### 5.1 Operating Budgets
* **Nominal Budgets ($\alpha$):** $0.1\%$ ($1/1,000$), $0.5\%$ ($1/200$), $1.0\%$ ($1/100$), $5.0\%$ ($1/20$).
* **Calibration Population:** `CALIBRATION` ($N_{\text{cal}} = 18,500$ pure benign flows).
  * Exact rational $k$ calculations:
    - $\alpha = 0.1\% \implies k = \lfloor 1/1000 \times 18500 \rfloor = \mathbf{18}$
    - $\alpha = 0.5\% \implies k = \lfloor 1/200 \times 18500 \rfloor = \mathbf{92}$
    - $\alpha = 1.0\% \implies k = \lfloor 1/100 \times 18500 \rfloor = \mathbf{185}$
    - $\alpha = 5.0\% \implies k = \lfloor 1/20 \times 18500 \rfloor = \mathbf{925}$
* **Evaluation Population:** `EVAL_CONTROL` ($N_{\text{eval}} = 18,500$ held-out pure benign flows) + `PROTECTED_BOT` ($N_{\text{bot}} = 1,948$ zero-day flows).

### 5.2 Mandatory Low-Resolution Rule (§ 4.4 & § 6)
* Preregistered criterion: Any budget with fewer than **20 expected false alarms** on `EVAL_CONTROL` is labeled **`LOW_RESOLUTION`**.
* Expected false alarms on $N_{\text{eval}} = 18,500$:
  * $\alpha = 0.1\%: 18,500 \times 0.001 = \mathbf{18.5} < 20 \implies$ **FLAGGED AS `LOW_RESOLUTION`**.
  * $\alpha = 0.5\%: 18,500 \times 0.005 = 92.5 \ge 20 \implies$ Adequate resolution.
  * $\alpha = 1.0\%: 18,500 \times 0.010 = 185 \ge 20 \implies$ Adequate resolution.
  * $\alpha = 5.0\%: 18,500 \times 0.050 = 925 \ge 20 \implies$ Adequate resolution.
* Strict tie policy: If discrete score ties prevent reaching $k$ strictly greater alerts, the cell is flagged as `tie_unattainable`.

---

## 6. Frozen UNSW Baseline Data Traceability (Read-Only)

No UNSW experiments will be re-run. All values for the cross-dataset comparison table are mapped directly to existing frozen artifacts:

| Model / Metric | Source File in `revision_v5/` or `results/` | Exact Row / Field | Value in Artifact |
|---|---|---|---|
| **Stacking Recall (Backdoor)** | `results/zero_day/EXP_ZERODAY_V1/metrics/zero_day_metrics.csv` | Row 6, `Zero-Day Detection Rate` | `0.99828` (582 / 583) |
| **Stacking Benign FPR** | `results/zero_day/EXP_ZERODAY_V1/metrics/zero_day_metrics.csv` | Row 6, `FPR` | `0.19189` (7,100 / 37,000) |
| **Stacking Natural Precision** | `results/zero_day/EXP_ZERODAY_V1/metrics/zero_day_metrics.csv` | Row 6, `Attack Precision` | `0.07576` (7.58%) |
| **Stacking Alerts / 10k** | Derived from FPR | $\text{FPR} \times 10,000$ | `1,918.9` alerts/10k |
| **Stacking Matched-FPR (0.1%–5%)** | `revision_v5/.../cross_model_comparison.csv` | Rows 18–21 (`model=stacking`) | $R=0.8148 \to 0.9828$ |
| **AE Recall at $\mu+3\sigma$** | `revision_v5/.../EXP_AE_ABLATION_V1/ae_ablation_results.csv` | Row 28 (`mean_plus_3sigma`) | `0.0000` (0 / 583) |
| **AE Control FPR at $\mu+3\sigma$** | `revision_v5/.../EXP_AE_ABLATION_V1/ae_ablation_results.csv` | Row 6 (`mean_plus_3sigma`) | `0.000486` (9 / 18,500) |
| **AE Alerts / 10k at $\mu+3\sigma$** | `revision_v5/.../EXP_AE_ABLATION_V1/ae_ablation_results.csv` | Row 6, $\text{FPR} \times 10,000$ | `4.86` alerts/10k |
| **Isolation Forest Recall ($\mu+3\sigma$)** | `revision_v5/.../EXP_IF_V1/zero_day/backdoor_detection.csv`| Rows 6, 11, 16 (`mean_plus_3sigma`) | `0.0000` (0 / 583) |
| **Hybrid Q3 Rescue** | `results/zero_day/EXP_ZERODAY_V1/analysis/detection_overlap.csv`| Row 4 (`Q3`) | `0` (0.0%) |
| **Hybrid Extra False Alarms** | `results/zero_day/EXP_ZERODAY_V1/metrics/zero_day_metrics.csv` | Row 9 (`C06 FP`) vs Row 8 (`C01 FP`) | `+13` FP (7,113 - 7,100) |
| **RF TOST Ablation Equivalence**| `revision_v5/.../EXP_TOST_V1/tost_rf_equivalence.json` | Field `"equivalence_conclusion"` | `Supported` ($\delta=0.01$, $\Delta=0.0$) |
| **UNSW FT-Transformer ($K=50$)**| `results/.../transformer/unsw/s22_ft_transformer_unsw_results.json`| Mean across seeds 42, 123, 2024 | F1: `0.8488`, Rec: `1.0000` |

---

## 7. Cross-Dataset Comparability & Mandatory Footnotes

The cross-dataset master table will synthesize UNSW-NB15 and CIC-IDS-2017 side-by-side. To prevent misleading direct comparisons, each dimensional discrepancy will be explicitly footnoted:

1. **Prevalence Discrepancy (Footnote a):**
   - In natural zero-day evaluation sets, CIC-IDS-2017 prevalence is $9.53\%$ ($1,948 / 20,448$) vs UNSW-NB15 prevalence of $3.06\%$ ($583 / 19,083$). Natural precision values cannot be compared directly; standardized precision at $\pi = 0.0306$ must be reported alongside natural precision.
2. **Attack Family Behavior (Footnote b):**
   - UNSW Backdoor traffic spans multiple ports and protocols, sharing significant feature density with other known attack families (enabling high supervised transfer). CIC Bot traffic (ARES botnet) consists of stealthy C&C flows that occupy benign-adjacent feature manifolds.
3. **Feature Representations (Footnote c):**
   - UNSW uses 75 (or 50) features including one-hot encoded categorical protocol indicators (`proto`, `service`, `state`). CIC uses 69 purely numeric flow counters.
4. **Resolution Limits (Footnote d):**
   - At $\alpha = 0.1\%$, the expected false alarm count on an 18,500-flow benign control pool is $18.5 < 20$, designating this budget as low-resolution.

---

## 8. Deployment Inference Benchmark Plan

### 8.1 Specification
- **Hardware Record:** Host CPU (Intel 12th Gen) and GPU (NVIDIA RTX 3050 Laptop GPU, 4.29 GB VRAM).
- **Target Models:**
  1. Decision Tree (`dt.pkl`)
  2. Random Forest (`rf.pkl`)
  3. Linear SVC (`linear_svc.pkl`)
  4. IDSNet MLP (`nn_model.pt`)
  5. Stacking Ensemble (`meta_lr.pkl` + 4 base models)
  6. Standard Autoencoder (`ae_standard.pt`)
  7. Isolation Forest (`isolation_forest.pkl`)
  8. FT-Transformer (`ft_model.pt`)
- **Evaluation Batch Volumes:** $N \in \{1,000, 10,000, 100,000\}$ flows (subsampled from `DEV_TEST`).
- **Timing Protocol:**
  - 1 warm-up batch run (discarded).
  - 5 timed repeated runs.
  - Report: Median wall-clock latency (ms), throughput (flows/s), peak CPU RSS memory (MB via `psutil`), and peak GPU allocated memory (MB via PyTorch CUDA stats).
  - Mandatory disclaimer: Labeled strictly as **"local host inference benchmarks, not production gateway throughput"**.

---

## 9. Publication Vector Figures Plan

All figures will be generated strictly from saved JSON and CSV files and exported in both high-resolution PNG (300 DPI) and publication-ready vector PDF formats into `figures/cicids2017_revision_v1/`:

1. **Figure 1: Cross-Dataset Recall vs Operational FPR Curve:**
   - X-axis: Operational FPR ($0\%$ to $5\%$).
   - Y-axis: Zero-day detection recall ($0\%$ to $100\%$).
   - Dual-panel or comparative lines showing UNSW Backdoor vs CIC Bot recall across budgets.
2. **Figure 2: CIC Model Performance Tradeoff:**
   - Scatter/ROC comparison of all evaluated CIC models (RF, Stacking, MLP, AE, IF, FT-Transformer) on `EVAL_CONTROL` + `PROTECTED_BOT`.
   - Distinct marker for Hybrid C06 at its reproduced operating point ($\mu+3\sigma$).
3. **Figure 3: Operational Alert Burden per 10,000 Benign Flows:**
   - Grouped bar chart comparing false alarm load across nominal budgets ($\alpha \in \{0.1\%, 0.5\%, 1.0\%, 5.0\%\}$).
4. **Figure 4: TreeSHAP Attribution Shift (Shortcut Ablation):**
   - Horizontal paired bar chart illustrating feature importance rank and attribution share shifts before and after ablating `Destination Port` and `Init_Win_bytes_backward`.

---

## 10. Sprint 6 Execution Sequence (Draft Plan)

1. **Step 1 (`cicids2017/src/s23_matched_fpr_analysis.py`):**
   - Score `CALIBRATION` ($18,500$) and `EVAL_CONTROL` ($18,500$) + `PROTECTED_BOT` ($1,948$) across Stacking, RF, MLP, Standard AE, Log1p AE, IF, and FT-Transformer.
   - Calibrate order-statistic thresholds for $\alpha \in \{0.1\%, 0.5\%, 1.0\%, 5.0\%\}$.
   - Compute realized FPR, CIs, recall, precision (natural + $\pi=0.0306$), PR-AUC, ROC-AUC, alerts/10k.
   - Add Hybrid C06 operating-point marker.
2. **Step 2 (`cicids2017/src/s24_deployment_benchmark.py`):**
   - Run 1k, 10k, 100k local batch inference timings across all 8 model families.
3. **Step 3 (`cicids2017/src/s25_cross_dataset_table.py`):**
   - Assemble the unified cross-dataset master table reading frozen UNSW and CIC outputs.
4. **Step 4 (`cicids2017/src/s26_generate_figures.py`):**
   - Generate Figures 1, 2, 3, and 4 (PNG + PDF).
5. **Step 5 (Validation & Reporting):**
   - Run invariant audit, verify 0 modifications to UNSW, and write `SPRINT_6_REPORT.md` and `MATCHED_FPR_REPORT.md`.
