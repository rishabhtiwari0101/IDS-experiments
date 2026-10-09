# SPRINT 5 REPORT — CIC-IDS-2017 REVISION
## Shortcut Feature Ablation, TreeSHAP Attribution Shift, Formal Hypothesis Testing (H1 & H2), and FT-Transformer Modern Deep Tabular Baselines Across CIC-IDS-2017 and UNSW-NB15

**Date:** 2026-10-06  
**Status:** **PASS — ALL GATES & INVARIANTS SATISFIED**  
**Governing Plan:** `Review_Exp/FINAL_REVIEWER_REVISION_SPRINT_PLAN_v2.md` (§ 8, Sprint 5)  
**Detailed Report:** `reports/cicids2017_revision_v1/SHORTCUT_AND_TRANSFORMER_REPORT.md`  
**Ablation Results:** `results/cicids2017_revision_v1/ablation/s19_ablation_evaluation.json`  
**SHAP Shift Results:** `results/cicids2017_revision_v1/ablation/s20_shap_ablation_shift.json`  
**CIC Transformer Results:** `results/cicids2017_revision_v1/ft_transformer/s21_ft_transformer_cic_results.json`  
**UNSW Transformer Results:** `results/cicids2017_revision_v1/transformer/unsw/s22_ft_transformer_unsw_results.json`

---

## 1. Executive Summary

Sprint 5 successfully addressed two core scientific inquiries raised by peer review:
1. **Shortcut Ablation & Generalization (Part A):** Evaluated whether high-performing classifiers depend on port/window protocol artifacts, and whether removing them disrupts model accuracy or unlocks zero-day attack detection.
2. **Modern Deep Tabular Transformer Baseline (Part B):** Implemented and evaluated the Feature Tokenizer Transformer (FT-Transformer; Gorishniy et al., NeurIPS 2021) across both CIC-IDS-2017 and UNSW-NB15 under standardized protocols.

All 6 planned steps were implemented and validated:

| Step | Script | Target / Scope | Status | Key Output / Metric |
|---|---|---|---|---|
| **Step 1** | `s17_train_ablated_base_models.py` | DT, RF, LinearSVC, IDSNet on $D_{\text{ablated}}=67$ (Seeds 42, 123, 2024) | **PASS** | 12 base model checkpoints saved in `cicids2017/models/ablated/` |
| **Step 2** | `s18_ablated_oof_stacking.py` | 5-Fold Stratified OOF CV on $D_{\text{ablated}}=67$ | **PASS** | Meta-LR Macro-F1 = $0.9984$; zero data leakage |
| **Step 3** | `s19_evaluate_shortcut_ablation.py` | Evaluation on `DEV_TEST` & `PROTECTED_BOT`, McNemar H1, TOST H2 | **PASS** | H1 **REJECTED** ($p < 10^{-80}$); H2 **CONFIRMED** ($p < 10^{-5}$); $\Delta\text{Bot} = 0$ |
| **Step 4** | `s20_treeshap_ablation_shift.py` | TreeSHAP on 2,000 stratified samples (Full vs Ablated RF) | **PASS** | 13.97% attribution mass redistributed to packet geometry |
| **Step 5** | `s21_train_ft_transformer_cic.py` | FT-Transformer on CIC (Full $K^*=69$ & Ablated $D=67$) | **PASS** | Full Macro-F1 = $0.9864$; Zero-day Bot Recall = $0.00\%$ ($0/1,948$) |
| **Step 6** | `s22_train_ft_transformer_unsw.py` | FT-Transformer on UNSW (Read-Only, $K=50$, Seeds 42, 123, 2024) | **PASS** | UNSW Macro-F1 = $0.8488$; Zero-day Backdoor Recall = $100.00\%$ ($583/583$) |

---

## 2. Invariant Verification & Integrity Pre-Flight Checks

Before commencing retraining or evaluation, all environmental invariants were cryptographically validated:

1. **Frozen Shortcut Manifest:**
   - Feature List: `['Destination Port', 'Init_Win_bytes_backward']` ($k=2$).
   - Expected SHA-256: `5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2`.
   - Realized SHA-256: `5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2` (**MATCH — BIT-IDENTICAL**).
2. **Feature Dimensionality:**
   - Full Feature Set: $K^* = 69$.
   - Ablated Feature Set: $D_{\text{ablated}} = 69 - 2 = 67$.
3. **Zero UNSW Tampering Invariant:**
   - `git diff --stat`: **0 files changed**.
   - Working tree clean for all tracked files; all UNSW splits, precomputed baselines, and models remained strictly read-only.
4. **Zero-Day Population Conservation:**
   - `PROTECTED_BOT` ($N=1,948$ rows) and `EVAL_CONTROL` ($N=18,500$ rows) remained untouched throughout all training steps.

---

## 3. Step 1 & 2: Ablated Base Models and Stacking OOF CV

### 3.1 Base Model Training on $D_{\text{ablated}}=67$
Base classifiers were trained on all 340,464 training flows (44,800 benign, 295,664 known attacks) across seeds 42, 123, and 2024:
- **Decision Tree (DT):** Entropy criterion, balanced class weighting. Average training time: 2.7s.
- **Random Forest (RF):** 300 trees, Gini criterion, $\sqrt{d}$ max features, balanced class weighting. Average training time: 104.2s. Checkpoint SHA-256 (Seed 42): `e7e9cafbd49ec538cc8508ccdad63dd825247126548fdc0fcac4b093e74a4ec6`.
- **Linear SVC:** L2 penalty, squared hinge loss, `dual=False`, tolerance $10^{-4}$. Average training time: 8.8s.
- **IDSNet (MLP):** PyTorch implementation ($67 \to 128 \to 64 \to 32 \to 2$, LayerNorm, Dropout 0.2). Average training time: 660.1s.

### 3.2 Genuine 5-Fold Stratified OOF Cross-Validation
To prevent meta-learner data leakage, out-of-fold probability vectors were generated using 5-fold Stratified K-Fold CV on `TRAIN` ($N=340,464$):
- Each fold trained DT, RF, LinearSVC, and IDSNet on 272,371 rows and evaluated on 68,093 held-out validation rows (8,960 benign, 59,133 attack).
- Meta-Learner (Logistic Regression, $C=1.0$, balanced class weight) was fitted on the concatenated OOF prediction matrix:
  - Seed 42: OOF Macro-F1 = $0.998402$, Precision = $0.999780$, Recall = $0.999378$, FPR = $0.001451$.
  - Seed 123: OOF Macro-F1 = $0.998402$, Precision = $0.999780$, Recall = $0.999378$, FPR = $0.001451$.
  - Seed 2024: OOF Macro-F1 = $0.998402$, Precision = $0.999780$, Recall = $0.999378$, FPR = $0.001451$.

---

## 4. Step 3: Ablation Evaluation & Hypotheses H1 / H2

All ablated models were evaluated on the full `DEV_TEST` partition ($N=743,921$ flows: 617,209 benign, 126,712 known attacks) and the isolated zero-day `PROTECTED_BOT` set ($N=1,948$ flows).

### 4.1 Macro-Level Performance Summary on `DEV_TEST`

| Model Architecture | Features | Mean Macro-F1 | Mean Precision | Mean Recall | Mean FPR | Alert Load / 10k |
|---|---|---|---|---|---|---|
| **Decision Tree (Original)** | $K^*=69$ | 0.9947 ± 0.0001 | 0.9832 | 0.9996 | 0.003501 | 35.01 |
| **Decision Tree (Ablated)** | $D=67$ | 0.9943 ± 0.0001 | 0.9816 | 0.9996 | 0.003835 | 38.35 |
| **Random Forest (Original)** | $K^*=69$ | **0.99856 ± 0.00002** | 0.9959 | 0.9994 | 0.000850 | 8.50 |
| **Random Forest (Ablated)** | $D=67$ | **0.99708 ± 0.00001** | 0.9910 | 0.9994 | 0.001873 | 18.73 |
| **Linear SVC (Original)** | $K^*=69$ | 0.9080 ± 0.0000 | 0.7423 | 0.9803 | 0.069792 | 697.92 |
| **Linear SVC (Ablated)** | $D=67$ | 0.8616 ± 0.0000 | 0.6513 | 0.9792 | 0.107641 | 1,076.41 |
| **IDSNet MLP (Original)** | $K^*=69$ | 0.9413 ± 0.0084 | 0.8208 | 0.9972 | 0.044950 | 449.50 |
| **IDSNet MLP (Ablated)** | $D=67$ | 0.9144 ± 0.0103 | 0.7604 | 0.9970 | 0.064705 | 647.05 |
| **Stacking (Original)** | $K^*=69$ | **0.99876 ± 0.00004** | 0.9964 | 0.9994 | 0.000732 | 7.32 |
| **Stacking (Ablated)** | $D=67$ | **0.99796 ± 0.00003** | 0.9939 | 0.9994 | 0.001264 | 12.64 |

### 4.2 Hypothesis H1: McNemar's Paired Exact Test
- **Objective:** Determine whether removing the two shortcut features changes individual classification decisions.
- **Null Hypothesis ($H_{0,1}$):** $P(b) = P(c)$ where $b$ = Original Correct / Ablated Wrong, and $c$ = Original Wrong / Ablated Correct.
- **Results:**
  - Seed 42: $b = 835$, $c = 221$, $N_{\text{discordant}} = 1,056$, $p = 1.98 \times 10^{-84}$.
  - Seed 123: $b = 836$, $c = 205$, $N_{\text{discordant}} = 1,041$, $p = 6.84 \times 10^{-91}$.
  - Seed 2024: $b = 845$, $c = 213$, $N_{\text{discordant}} = 1,058$, $p = 1.55 \times 10^{-89}$.
- **Verdict:** **REJECTED ($p \ll 10^{-80}$)**. Removing shortcut features significantly alters prediction paths.

### 4.3 Hypothesis H2: TOST Equivalence Testing
- **Objective:** Test whether Random Forest performance remains equivalent to the original model within a practical materiality margin $\delta = 0.01$ ($|\Delta\text{Macro-F1}| < 0.01$).
- **Results:**
  - Observed Shift: $\text{Mean } \Delta\text{Macro-F1} = 0.001480$ (0.148% change).
  - Standard Error: $\text{SE} = 1.381 \times 10^{-5}$.
  - Lower Bound ($t_{\text{lower}}$): $831.13$ ($p = 7.24 \times 10^{-7}$).
  - Upper Bound ($t_{\text{upper}}$): $-616.79$ ($p = 1.31 \times 10^{-6}$).
- **Verdict:** **CONFIRMED / ACCEPTED**. Tree ensembles maintain statistical equivalence under shortcut removal, successfully substituting correlated packet geometry features.

### 4.4 Materiality Check on `PROTECTED_BOT`
Under the sprint plan, materiality requires $|\Delta\text{Bot}| \ge 20$ flows.
- Original RF: 0 / 1,948 detected.
- Ablated RF: 0 / 1,948 detected ($\Delta\text{Bot} = 0$).
- Original Stacking: 0 / 1,948 detected.
- Ablated Stacking: 0 / 1,948 detected ($\Delta\text{Bot} = 0$).
- **Verdict:** The impact on zero-day bot detection is **immaterial** ($\Delta\text{Bot} = 0 < 20$).

---

## 5. Step 4: TreeSHAP Attribution Shift Diagnostic

TreeSHAP attribution values were computed on the exact same 2,000 stratified flows sampled from `DEV_TEST` for the Random Forest model (Seed 42):
- **Shortcut Mass in Original RF:**
  - `Destination Port`: Mean $| \text{SHAP} | = 0.06152$ (**Rank 2**, $10.00\%$ of total attribution).
  - `Init_Win_bytes_backward`: Mean $| \text{SHAP} | = 0.02443$ (**Rank 9**, $3.97\%$ of total attribution).
  - Total Shortcut Mass: **$13.97\%$** ($0.08595 / 0.61528$).
- **Post-Ablation Mass Redistribution:**
  1. `Average Packet Size`: Rank 3 $\to$ Rank 2 ($+2.45\%$ attribution share).
  2. `Packet Length Variance`: Rank 4 $\to$ Rank 3 ($+1.48\%$ attribution share).
  3. `Packet Length Std`: Rank 6 $\to$ Rank 4 ($+1.10\%$ attribution share).
  4. `Init_Win_bytes_forward`: Rank 17 $\to$ Rank 10 ($+1.08\%$ attribution share).
  5. `Fwd Packet Length Mean`: Rank 13 $\to$ Rank 9 ($+1.03\%$ attribution share).

Attribution mass did not concentrate in a single substitute; it dispersed across statistical packet geometry and the forward TCP window parameter.

---

## 6. Step 5 & 6: FT-Transformer Baseline (CIC vs UNSW)

To benchmark against modern tabular deep learning, the Feature Tokenizer Transformer (Gorishniy et al., NeurIPS 2021) was trained and evaluated under identical conditions.

### 6.1 Architectural Parameters
- Token Dimension ($d_{\text{model}}$): 64
- Attention Heads: 4
- Transformer Blocks: 3
- Feed-Forward Dimension: 128
- Dropout: 0.1
- Classification: Learnable `[CLS]` token $\to$ Linear layer ($64 \to 2$)
- Parameter Counts:
  - CIC Full ($K^*=69$): 106,434
  - CIC Ablated ($D=67$): 106,178
  - UNSW ($K=50$): 104,001

### 6.2 CIC-IDS-2017 FT-Transformer Performance

| Variant | Seed | DEV_TEST Macro-F1 | Precision | Recall | FPR | Zero-Day Bot Recall | 95% Wilson CI | Control Alerts / 10k |
|---|---|---|---|---|---|---|---|---|
| **Full ($K^*=69$)** | 42 | 0.9855 | 0.9536 | 0.9996 | 0.009987 | 0.0000 (0 / 1,948) | [0.0000, 0.0020] | 103.78 |
| **Full ($K^*=69$)** | 123 | 0.9906 | 0.9719 | 0.9974 | 0.005925 | 0.0000 (0 / 1,948) | [0.0000, 0.0020] | 65.41 |
| **Full ($K^*=69$)** | 2024 | 0.9830 | 0.9455 | 0.9998 | 0.011840 | 0.0000 (0 / 1,948) | [0.0000, 0.0020] | 120.54 |
| **Full Mean** | — | **0.9864 ± 0.0032**| **0.9570** | **0.9990** | **0.009251** | **0.0000 (0 / 1,948)** | **[0.0000, 0.0020]** | **96.58** |
| **Ablated ($D=67$)**| 42 | 0.9754 | 0.9237 | 0.9981 | 0.016923 | 0.0000 (0 / 1,948) | [0.0000, 0.0020] | 182.16 |
| **Ablated ($D=67$)**| 123 | 0.9830 | 0.9512 | 0.9937 | 0.010476 | 0.0000 (0 / 1,948) | [0.0000, 0.0020] | 112.43 |
| **Ablated ($D=67$)**| 2024 | 0.9830 | 0.9478 | 0.9974 | 0.011277 | 0.0000 (0 / 1,948) | [0.0000, 0.0020] | 117.84 |
| **Ablated Mean** | — | **0.9805 ± 0.0036**| **0.9409** | **0.9964** | **0.012892** | **0.0000 (0 / 1,948)** | **[0.0000, 0.0020]** | **137.48** |

### 6.3 UNSW-NB15 FT-Transformer Performance (Read-Only Benchmark)

| Seed | DEV_TEST Macro-F1 | Precision | Recall | FPR | Zero-Day Backdoor Recall | Backdoor Detections | 95% Wilson CI |
|---|---|---|---|---|---|---|---|
| **42** | 0.8663 | 0.8175 | 0.9865 | 0.266297 | 1.0000 | 583 / 583 | [0.9935, 1.0000] |
| **123** | 0.8368 | 0.7853 | 0.9889 | 0.327027 | 1.0000 | 583 / 583 | [0.9935, 1.0000] |
| **2024** | 0.8435 | 0.7916 | 0.9900 | 0.315162 | 1.0000 | 583 / 583 | [0.9935, 1.0000] |
| **Mean** | **0.8488 ± 0.0126** | **0.7981** | **0.9885** | **0.302829** | **1.0000** | **583 / 583 (100.0%)** | **[0.9935, 1.0000]** |

### 6.4 Cross-Dataset Structural Asymmetry
The FT-Transformer benchmark reveals that architectural inductive bias cannot overcome dataset manifold geometry:
- On **UNSW-NB15**, FT-Transformer achieves 100.00% detection on unseen Backdoor attacks, identically replicating Random Forest and Stacking.
- On **CIC-IDS-2017**, FT-Transformer achieves 0.00% detection on unseen Bot attacks, identically replicating Random Forest and Stacking.
- Tabular self-attention captures complex high-order feature interactions, but if zero-day flows occupy benign feature space, all supervised models fail alike.

---

## 7. Sprint 5 Verification Gates Checklist

| Gate Condition | Preregistered Requirement | Verified Evidence | Status |
|---|---|---|---|
| **Shortcut Hash Gate** | Hash must match `shortcut_list_frozen.json` | `5e2942c8...` verified bit-for-bit | **PASS** |
| **Ablation Reproducibility** | Full 3-seed evaluation across DT, RF, LinearSVC, IDSNet, Stacking | Seeds 42, 123, 2024 evaluated on 743k flows | **PASS** |
| **SHAP Audit Gate** | Same 2,000 stratified samples before and after | Table and JSON saved; 13.97% mass tracked | **PASS** |
| **Hypothesis Testing Gate** | H1 McNemar & H2 TOST recorded with exact values | H1 $p < 10^{-80}$; H2 $p < 10^{-5}$ confirmed | **PASS** |
| **Zero-Day Materiality Gate** | Materiality bound $|\Delta\text{Bot}| < 20$ flows | $\Delta\text{Bot} = 0$ flows on RF & Stacking | **PASS** |
| **Leakage-Free Transformer** | Early stopping on internal split; no test contamination | CUDA training on TRAIN; evaluated on DEV_TEST | **PASS** |
| **UNSW Frozen Gate** | Zero modifications to UNSW benchmark files | `git diff --stat` clean (0 tracked changes) | **PASS** |

---

## 8. Transition to Sprint 6

Sprint 5 is fully accomplished and closed. All model artifacts and results are persisted.
The repository is prepared to proceed to **Sprint 6 — Matched-FPR, Deployment Analysis, Cross-Dataset Comparison & Figures**:
- **Matched-FPR Evaluation:** Calibrating operational budgets ($\alpha \in \{0.1\%, 0.5\%, 1.0\%, 5.0\%\}$) on `CALIBRATION` and evaluating realized false alarms on `EVAL_CONTROL` across Stacking, RF, MLP, AE, IF, and FT-Transformer.
- **Deployment Benchmarks:** Wall-clock, GPU/CPU memory, and batch latency timings across batch sizes (1k, 10k, 100k flows).
- **Cross-Dataset Master Table:** Unified synthesis comparing UNSW-NB15 vs CIC-IDS-2017 across all dimensions.
- **Publication Figures:** Generating publication-grade vector figures directly from saved JSON/CSV result artifacts.
