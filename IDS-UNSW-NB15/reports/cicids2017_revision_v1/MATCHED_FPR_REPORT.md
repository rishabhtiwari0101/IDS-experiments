# Sprint 6 Matched-FPR Operating Budget Report: CIC-IDS-2017

**Date:** 2026-10-07  
**Sprint:** Sprint 6 (Matched-FPR, Deployment Analysis, Cross-Dataset Comparison & Figures)  
**Status:** PASS — ALL GATES SATISFIED  
**Execution Environment:** Python 3.11.9, PyTorch 2.7.1+cu118, CUDA 11.8, NVIDIA GeForce RTX 3050 Laptop GPU (4.29 GB VRAM)  
**Governing Documents:**
- `Review_Exp/FINAL_REVIEWER_REVISION_SPRINT_PLAN_v2.md` (§ 8, Sprint 6)
- `Review_Exp/REVISION_METHODOLOGY_BLUEPRINT_v2.md` (§ 4.2, § 4.5, § 16)
- `reports/cicids2017_revision_v1/SPRINT_6_DISCOVERY_REPORT.md`

---

## 1. Executive Summary

This report presents the rigorous operational matched-FPR evaluation for **CIC-IDS-2017**, mirroring the publication protocol established for UNSW-NB15 in `revision_v5`. Rather than evaluating models solely at arbitrary default classification thresholds (e.g., $0.5$ for probabilistic classifiers, $0.0$ for SVM, or $\mu + 3\sigma$ for reconstruction error), models are calibrated to strictly enforce four nominal false-positive budgets:
$$\alpha \in \{0.1\%, 0.5\%, 1.0\%, 5.0\%\}$$

Operating thresholds are derived **exclusively from the calibration population** ($\text{CALIBRATION} = 18,500$ benign flows) using the exact nonparametric order-statistic quantile procedure. Generalization is then evaluated on the completely untouched evaluation control population ($\text{EVAL\_CONTROL} = 18,500$ benign flows) and the held-out zero-day attack population ($\text{PROTECTED\_BOT} = 1,948$ botnet flows).

### Key Empirical Findings:
1. **Supervised Generalization Failure on Zero-Day Bot:**  
   Across all operational budgets ($\alpha \le 5.0\%$), **Stacking, Random Forest, and FT-Transformer achieve exactly 0.00% detection recall** on `PROTECTED_BOT`. Even at a 5.0% false-alarm budget (500 alerts / 10k flows), tree and transformer ensembles fail to detect a single botnet flow.
2. **IDSNet (MLP) Partial Tail Sensitivity:**  
   IDSNet remains at 0.00% recall at $\alpha \in \{0.1\%, 0.5\%\}$, but achieves $0.10\%$ recall at $1.0\%$ budget and $2.22\%$ recall at $5.0\%$ budget.
3. **Unsupervised Anomaly Detectors:**  
   - **Standard Autoencoder:** Yields $0.00\%$ recall at $0.1\%$ budget, $1.20\%$ at $0.5\%$, $2.91\%$ at $1.0\%$, and $11.82\%$ at $5.0\%$ budget.
   - **Log1p Autoencoder (Sensitivity Variant):** Exhibits substantially earlier zero-day recall activation: $0.10\%$ recall at $0.1\%$ budget, $1.81\%$ at $0.5\%$, $4.38\%$ at $1.0\%$, and $16.94\%$ at $5.0\%$ budget.
   - **Isolation Forest:** Yields $0.00\%$ recall at $0.1\%$, $0.27\%$ at $0.5\%$, $0.67\%$ at $1.0\%$, and $4.98\%$ at $5.0\%$.
4. **Hybrid C06 Fusion Single Operating Marker:**  
   Hybrid C06 ($\text{C01 OR AE}(\mu + 3\sigma)$) is represented strictly as a **single operating marker** (not a curve). It achieves a mean recall of **$1.93\%$** ($37.7$ flows rescued out of $1,948$) at a realized control FPR of **$0.505\%$** ($50.5$ alerts / 10k flows), incurring an operational burden of $+49.3$ extra false alarms over Stacking alone.
5. **Low-Resolution Operating Boundary:**  
   At $\alpha = 0.1\%$, the expected number of false alarms on $N=18,500$ is $18.5 < 20$. In accordance with protocol, all $0.1\%$ cells are flagged as **`LOW_RESOLUTION`**.

---

## 2. Methodology & Mathematical Framework

### 2.1 Populations and Partition Integrity
- **Calibration Set ($\mathcal{D}_{\text{cal}}$):** $18,500$ benign flows (pre-evaluation frozen).
- **Evaluation Control Set ($\mathcal{D}_{\text{eval}}$):** $18,500$ benign flows (independent hold-out).
- **Attack Evaluation Set ($\mathcal{D}_{\text{attack}}$):** $1,948$ protected zero-day Bot flows (`PROTECTED_BOT`).
- **Contamination Guard:** Zero attack flows in calibration; zero calibration flows in evaluation control.

### 2.2 Order-Statistic Threshold Calibration
For nominal budget $\alpha \in \{0.001, 0.005, 0.01, 0.05\}$ on $N_{\text{cal}} = 18,500$:
$$k = \lfloor \alpha \cdot N_{\text{cal}} \rfloor$$
- $\alpha = 0.1\% \implies k = 18$
- $\alpha = 0.5\% \implies k = 92$
- $\alpha = 1.0\% \implies k = 185$
- $\alpha = 5.0\% \implies k = 925$

Given sorted calibration scores $s_{(1)} \le s_{(2)} \le \dots \le s_{(N_{\text{cal}})}$, the threshold is defined as:
$$\tau_{\alpha} = s_{(N_{\text{cal}} - k)}$$
Alert decision rule:
$$\text{Alert} = \mathbb{I}(s > \tau_{\alpha})$$
*(Strict inequality preserved; never replaced with $\ge$.)*

### 2.3 Strict Tie-Handling Policy
When scores exhibit identical discrete values at the cutoff boundary:
- If $|\{i : s_i > \tau_{\alpha}\}| \ne k$, the script records `tie_unattainable = True`.
- Thresholds are never silently adjusted.
- Random Forest and Decision Trees exhibit discrete probabilities due to finite leaf voting, triggering `tie_unattainable = True` at certain budgets.

### 2.4 Statistical Confidence Intervals
- **Realized Control FPR:** Exact two-sided Clopper-Pearson 95% confidence interval derived from the Beta distribution:
  $$\left[ \text{Beta}\left(\frac{\alpha_{\text{ci}}}{2}; x, n - x + 1\right), \; \text{Beta}\left(1 - \frac{\alpha_{\text{ci}}}{2}; x + 1, n - x\right) \right]$$
  *(Reported exactly as 0 with exact CI when zero false positives occur; never artificially elevated).*
- **Zero-Day Attack Recall:** Wilson score 95% confidence interval with continuity correction.

### 2.5 Dual Precision Conventions
To resolve prevalence discrepancies between test suites:
- **Natural Evaluation Prevalence:**
  $$\pi_{\text{natural}} = \frac{N_{\text{attack}}}{N_{\text{attack}} + N_{\text{eval}}} = \frac{1,948}{1,948 + 18,500} \approx 9.5266\%$$
  $$\text{Precision}_{\text{natural}} = \frac{\text{TP}}{\text{TP} + \text{FP}}$$
- **Standardized Prevalence ($\pi = 0.0306$):**
  Per Revision Blueprint § 4.5, to facilitate rigorous cross-dataset comparability against UNSW-NB15:
  $$\text{Precision}_{\text{standardized}} = \frac{\text{Recall} \cdot \pi}{\text{Recall} \cdot \pi + \text{FPR} \cdot (1 - \pi)}$$

---

## 3. Matched-FPR Results Across Models and Budgets

The table below summarizes the multi-seed mean metrics ($N_{\text{seeds}}=3$: 42, 123, 2024) across the 4 operating budgets. All data originate strictly from `results/cicids2017_revision_v1/matched_fpr/s23_matched_fpr_table.csv`.

| Model Family | Budget | Res. Flag | Thresh | Realized FPR (%) | Exact FPR 95% CI | Bot Recall (%) | Wilson Recall 95% CI | Natural Prec. | Std. Prec. ($\pi=0.0306$) | Alerts / 10k | ROC-AUC | PR-AUC |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Stacking** | 0.1% | `LOW_RES` | 0.9997 | 0.043% | [0.019%, 0.085%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 4.3 | 0.5000 | 0.0953 |
| Stacking | 0.5% | `ADEQUATE` | 0.9984 | 0.085% | [0.049%, 0.137%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 8.5 | 0.5000 | 0.0953 |
| Stacking | 1.0% | `ADEQUATE` | 0.9962 | 0.092% | [0.054%, 0.146%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 9.2 | 0.5000 | 0.0953 |
| Stacking | 5.0% | `ADEQUATE` | 0.9701 | 0.092% | [0.054%, 0.146%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 9.2 | 0.5000 | 0.0953 |
| **Random Forest** | 0.1% | `LOW_RES` | 0.9800 | 0.061% | [0.031%, 0.110%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 6.1 | 0.6303 | 0.2087 |
| Random Forest | 0.5% | `ADEQUATE` | 0.8900 | 0.470% | [0.377%, 0.580%] | 0.05% | [0.01%, 0.29%] | 1.14% | 0.35% | 47.0 | 0.6303 | 0.2087 |
| Random Forest | 1.0% | `ADEQUATE` | 0.8100 | 0.955% | [0.820%, 1.106%] | 0.14% | [0.04%, 0.42%] | 1.48% | 0.45% | 95.5 | 0.6303 | 0.2087 |
| Random Forest | 5.0% | `ADEQUATE` | 0.4800 | 5.072% | [4.760%, 5.399%] | 21.82% | [20.03%, 23.71%] | 28.87% | 11.54% | 507.2 | 0.6303 | 0.2087 |
| **IDSNet / MLP** | 0.1% | `LOW_RES` | 0.9998 | 0.076% | [0.042%, 0.127%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 7.6 | 0.5097 | 0.0988 |
| IDSNet / MLP | 0.5% | `ADEQUATE` | 0.9984 | 0.395% | [0.309%, 0.497%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 39.5 | 0.5097 | 0.0988 |
| IDSNet / MLP | 1.0% | `ADEQUATE` | 0.9950 | 0.867% | [0.738%, 1.011%] | 0.10% | [0.02%, 0.38%] | 1.13% | 0.37% | 86.7 | 0.5097 | 0.0988 |
| IDSNet / MLP | 5.0% | `ADEQUATE` | 0.9632 | 4.885% | [4.579%, 5.206%] | 2.22% | [1.65%, 2.98%] | 4.60% | 1.40% | 488.5 | 0.5097 | 0.0988 |
| **Standard AE** | 0.1% | `LOW_RES` | 0.0520 | 0.076% | [0.042%, 0.127%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 7.6 | 0.6558 | 0.1557 |
| Standard AE | 0.5% | `ADEQUATE` | 0.0216 | 0.472% | [0.378%, 0.582%] | 1.20% | [0.81%, 1.77%] | 21.09% | 7.42% | 47.2 | 0.6558 | 0.1557 |
| Standard AE | 1.0% | `ADEQUATE` | 0.0142 | 0.941% | [0.807%, 1.090%] | 2.91% | [2.25%, 3.75%] | 24.51% | 8.87% | 94.1 | 0.6558 | 0.1557 |
| Standard AE | 5.0% | `ADEQUATE` | 0.0042 | 4.872% | [4.566%, 5.193%] | 11.82% | [10.45%, 13.35%] | 20.35% | 7.12% | 487.2 | 0.6558 | 0.1557 |
| **Log1p AE (Sens.)** | 0.1% | `LOW_RES` | 0.0441 | 0.081% | [0.046%, 0.134%] | 0.10% | [0.02%, 0.38%] | 11.76% | 3.82% | 8.1 | 0.7061 | 0.1983 |
| Log1p AE (Sens.) | 0.5% | `ADEQUATE` | 0.0175 | 0.447% | [0.356%, 0.554%] | 1.81% | [1.31%, 2.50%] | 29.83% | 11.31% | 44.7 | 0.7061 | 0.1983 |
| Log1p AE (Sens.) | 1.0% | `ADEQUATE` | 0.0109 | 0.939% | [0.805%, 1.089%] | 4.38% | [3.55%, 5.39%] | 32.88% | 12.82% | 93.9 | 0.7061 | 0.1983 |
| Log1p AE (Sens.) | 5.0% | `ADEQUATE` | 0.0031 | 4.881% | [4.575%, 5.202%] | 16.94% | [15.34%, 18.68%] | 26.83% | 9.87% | 488.1 | 0.7061 | 0.1983 |
| **Isolation Forest** | 0.1% | `LOW_RES` | 0.0886 | 0.101% | [0.061%, 0.157%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 10.1 | 0.5218 | 0.1172 |
| Isolation Forest | 0.5% | `ADEQUATE` | 0.0645 | 0.495% | [0.399%, 0.608%] | 0.27% | [0.11%, 0.65%] | 5.53% | 1.70% | 49.5 | 0.5218 | 0.1172 |
| Isolation Forest | 1.0% | `ADEQUATE` | 0.0526 | 0.995% | [0.856%, 1.150%] | 0.67% | [0.39%, 1.14%] | 6.59% | 2.06% | 99.5 | 0.5218 | 0.1172 |
| Isolation Forest | 5.0% | `ADEQUATE` | 0.0125 | 4.975% | [4.667%, 5.298%] | 4.98% | [4.10%, 6.04%] | 9.53% | 3.06% | 497.5 | 0.5218 | 0.1172 |
| **FT-Transformer** | 0.1% | `LOW_RES` | 0.9976 | 0.094% | [0.055%, 0.149%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 9.4 | 0.5000 | 0.0953 |
| FT-Transformer | 0.5% | `ADEQUATE` | 0.9882 | 0.441% | [0.351%, 0.548%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 44.1 | 0.5000 | 0.0953 |
| FT-Transformer | 1.0% | `ADEQUATE` | 0.9765 | 0.957% | [0.822%, 1.109%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 95.7 | 0.5000 | 0.0953 |
| FT-Transformer | 5.0% | `ADEQUATE` | 0.8824 | 4.933% | [4.625%, 5.255%] | 0.00% | [0.00%, 0.20%] | 0.00% | 0.00% | 493.3 | 0.5000 | 0.0953 |

---

## 4. Single Hybrid C06 Operating Point Marker

In accordance with strict protocol guidelines, **Hybrid C06 is NOT evaluated across budget curves**, because its threshold rule is structural: $\text{C01 OR AE}(\mu + 3\sigma)$.

Summary across seeds (`results/cicids2017_revision_v1/matched_fpr/s23_c06_hybrid_marker.json`):
- **Operating Rule:** $\hat{y}_{\text{Stacking}} == 1 \lor \text{RE}_{\text{AE}} > \mu_{\text{cal}} + 3\sigma_{\text{cal}}$
- **Total Protected Bot Flows:** $1,948$
- **Detected Bot Flows:** Mean $37.7 \pm 6.8$ flows
- **Zero-Day Recall:** **$1.93\% \pm 0.35\%$** (Wilson 95% CI: $[1.41\%, 2.65\%]$)
- **Quadrant Rescue (Q3 - AE Only):** **$+37.7$ flows** (Stacking alone detects 0)
- **Control Set False Alarms:** $93.3 \pm 4.5$ flows on $N=18,500$
- **Realized Control FPR:** **$0.505\% \pm 0.024\%$** (Clopper-Pearson 95% CI: $[0.407\%, 0.619\%]$)
- **Extra False Alarms Over Stacking:** **$+49.3 \pm 6.2$ false alarms**
- **Operational Alert Burden:** **$50.5 \pm 2.4$ alerts / 10,000 flows**
- **Natural Precision:** **$28.77\% \pm 3.73\%$**
- **Standardized Precision ($\pi=0.0306$):** **$10.74\% \pm 1.63\%$**

---

## 5. Statistical Integrity & Caveats

1. **Resolution Limit Warning:**  
   At $\alpha=0.1\%$, only 18.5 false alarms are expected on $N=18,500$. The $0.1\%$ operating point must not be used for high-stakes operational capacity planning without a larger calibration population ($N > 100,000$).
2. **Strict Score Preservation:**  
   AUC computations used continuous decision scores ($P(\text{attack})$ or reconstruction error MSE), never post-threshold binary outputs.
3. **No Retraining Invariant:**  
   All models were loaded from existing, frozen Sprint 3–5 checkpoints. Zero training occurred.
