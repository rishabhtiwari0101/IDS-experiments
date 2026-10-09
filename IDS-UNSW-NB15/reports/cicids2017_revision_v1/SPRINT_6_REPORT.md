# SPRINT 6 REPORT: Matched-FPR, Deployment Analysis, Cross-Dataset Comparison & Figures

**Date:** 2026-10-07  
**Sprint:** Sprint 6 (Execution Phase)  
**Status:** **PASS — ALL GATES & INVARIANTS SATISFIED**  
**Governing Document:** `Review_Exp/FINAL_REVIEWER_REVISION_SPRINT_PLAN_v2.md` (§ 8, Sprint 6)  
**Preceding Discovery:** `reports/cicids2017_revision_v1/SPRINT_6_DISCOVERY_REPORT.md`  

---

## 1. Executive Summary

Sprint 6 has completed full execution under strict compliance with all absolute constraints:
- **Workspace Confinement:** All operations executed strictly within `Papers/IDS-UNSW-NB15`. Zero writes to external drives or parent directories.
- **UNSW Freeze Preserved:** The 1,261-file UNSW manifest has zero missing files and zero SHA-256 mismatches. UNSW models and results remain completely untouched.
- **No Retraining:** Zero models were retrained during Sprint 6. All evaluations, calibrations, benchmarks, and figures purely load saved models and artifacts.
- **Git State:** Working tree remains uncommitted with exact tracking.

### Core Achievements of Sprint 6:
1. **Matched-FPR Analysis (`s23`):**  
   Calibrated 7 models (Stacking, RF, IDSNet/MLP, Standard AE, Log1p AE, Isolation Forest, FT-Transformer) across 4 nominal budgets ($\alpha \in \{0.1\%, 0.5\%, 1.0\%, 5.0\%\}$) on $\text{CALIBRATION} = 18,500$ benign flows. Realized FPR and attack recall were rigorously evaluated on $\text{EVAL\_CONTROL} = 18,500$ flows and $\text{PROTECTED\_BOT} = 1,948$ flows. Hybrid C06 ($\text{C01 OR AE}(\mu+3\sigma)$) was evaluated as a single operating point marker ($1.93\%$ recall @ $0.505\%$ FPR).
2. **Deployment Benchmark (`s24`):**  
   Benchmarked local inference latency, throughput, CPU RSS memory, and GPU VRAM across all 8 model families across 1k, 10k, and 100k flows sampled from `DEV_TEST`. Neural architectures (IDSNet, Autoencoder) demonstrated line-rate capability ($> 6\text{M flows/s}$), while tree ensembles and FT-Transformer demonstrated heavy computational overheads. Safe 4096-flow mini-batch chunking prevented CUDA OOM on FT-Transformer.
3. **Cross-Dataset Master Table (`s25`):**  
   Synthesized 15 comparative dimensions between UNSW-NB15 and CIC-IDS-2017 strictly from saved artifacts, complete with the four mandatory comparability footnotes (Prevalence, Protected Attack Family, Feature Representation, Statistical Resolution).
4. **Publication Figures (`s26`):**  
   Produced Figures 1–4 in both 300 DPI PNG and vector PDF formats inside `figures/cicids2017_revision_v1/`, generated entirely from saved JSON and CSV files.
5. **Specialized Reports:**  
   Produced `MATCHED_FPR_REPORT.md`, `DEPLOYMENT_BENCHMARK_REPORT.md`, and `CROSS_DATASET_REPORT.md`.

---

## 2. Preflight Verification Results (Step 0)

| Preflight Check | Target Requirement | Realized Value | Status |
| :--- | :--- | :--- | :--- |
| **Shortcut Hash** | `5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2` | `5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2` | **PASS** |
| **Frozen Shortcuts** | `["Destination Port", "Init_Win_bytes_backward"]` | `["Destination Port", "Init_Win_bytes_backward"]` | **PASS** |
| **UNSW Freeze** | 1,261 files, 0 missing, 0 mismatches | 1,261 files verified, 0 missing, 0 mismatches | **PASS** |
| **TRAIN Population** | 340,464 flows | 340,464 flows | **PASS** |
| **CALIBRATION Population** | 18,500 benign flows | 18,500 benign flows | **PASS** |
| **EVAL_CONTROL Population** | 18,500 benign flows | 18,500 benign flows | **PASS** |
| **DEV_TEST Population** | 743,921 flows | 743,921 flows | **PASS** |
| **PROTECTED_BOT Population**| 1,948 flows | 1,948 flows | **PASS** |

---

## 3. Matched-FPR Analysis Results (Step 1)

**Script:** `cicids2017/src/s23_matched_fpr_analysis.py`  
**Artifacts Produced:**
- `results/cicids2017_revision_v1/matched_fpr/s23_matched_fpr_table.csv` (84 rows)
- `results/cicids2017_revision_v1/matched_fpr/s23_matched_fpr_summary.json`
- `results/cicids2017_revision_v1/matched_fpr/s23_c06_hybrid_marker.json`

### Key Empirical Observations:
- **Supervised Failure on Botnet:** Stacking, Random Forest, and FT-Transformer achieve **$0.00\%$ Bot recall** across all nominal budgets ($0.1\%$, $0.5\%$, $1.0\%$, $5.0\%$).
- **Standard Autoencoder:** Recalls $0.00\%$ at $0.1\%$, $1.20\%$ at $0.5\%$, $2.91\%$ at $1.0\%$, and $11.82\%$ at $5.0\%$ budget.
- **Log1p Autoencoder (Sensitivity Variant):** Activates recall earlier: $0.10\%$ at $0.1\%$, $1.81\%$ at $0.5\%$, $4.38\%$ at $1.0\%$, and $16.94\%$ at $5.0\%$ budget.
- **Hybrid C06 Single Marker:** Rescues $37.7$ flows ($1.93\%$ recall) at the cost of $+49.3$ extra false alarms ($50.5$ alerts / 10k flows) over Stacking alone.
- **Low-Resolution Rule:** All $0.1\%$ budget cells are flagged as `LOW_RESOLUTION` because $k = 18.5 < 20$ expected false alarms.

---

## 4. Deployment Benchmark Results (Step 2)

**Script:** `cicids2017/src/s24_deployment_benchmark.py`  
**Artifacts Produced:**
- `results/cicids2017_revision_v1/deployment/s24_deployment_benchmark.csv` (24 rows)
- `results/cicids2017_revision_v1/deployment/s24_deployment_benchmark.json`

> **Disclaimer:** *"Local host inference benchmarks, not production gateway throughput."*

### Benchmark Summary on $N=100,000$ Flows:
1. **IDSNet (MLP):** Median latency **$5.27\text{ ms}$** $\implies$ **$18,975,332\text{ flows/s}$** (GPU, 205.8 MB VRAM).
2. **Autoencoder (Standard):** Median latency **$15.12\text{ ms}$** $\implies$ **$6,612,226\text{ flows/s}$** (GPU, 73.7 MB VRAM).
3. **Decision Tree:** Median latency **$17.68\text{ ms}$** $\implies$ **$5,656,557\text{ flows/s}$** (CPU).
4. **Linear SVC:** Median latency **$70.32\text{ ms}$** $\implies$ **$1,422,056\text{ flows/s}$** (CPU).
5. **Isolation Forest:** Median latency **$1,807.06\text{ ms}$** $\implies$ **$55,338\text{ flows/s}$** (CPU).
6. **Random Forest:** Median latency **$1,995.11\text{ ms}$** $\implies$ **$50,123\text{ flows/s}$** (CPU).
7. **Stacking Ensemble:** Median latency **$3,122.35\text{ ms}$** $\implies$ **$32,027\text{ flows/s}$** (Hybrid CPU+GPU).
8. **FT-Transformer:** Median latency **$7,049.74\text{ ms}$** $\implies$ **$14,185\text{ flows/s}$** (GPU, Chunked 4096, 528.0 MB VRAM).

---

## 5. Cross-Dataset Master Table (Step 3)

**Script:** `cicids2017/src/s25_cross_dataset_table.py`  
**Artifacts Produced:**
- `results/cicids2017_revision_v1/cross_dataset/s25_cross_dataset_master_table.csv` (15 rows)
- `results/cicids2017_revision_v1/cross_dataset/s25_cross_dataset_master_table.json`

### Mandatory Comparability Footnotes Addressed:
- **Footnote A (Prevalence):** Addressed via standardized precision ($\pi = 0.0306$) alongside natural evaluation prevalence ($\pi_{\text{UNSW}} = 3.06\%$ vs $\pi_{\text{CIC}} = 9.53\%$).
- **Footnote B (Protected Attack Families):** Clearly distinguishes multi-protocol Backdoor from IRC C&C Botnet.
- **Footnote C (Feature Spaces & Dimensionality):** Details $K=75$ vs $K=50$ for UNSW (where 50 is the exact prefix of 75) and $K^*=69$ vs $D=67$ for CIC.
- **Footnote D (Statistical Resolution):** Explains why $0.1\%$ budget has low resolution on an 18,500-flow control set.

---

## 6. Publication Figures Generated (Step 4)

**Script:** `cicids2017/src/s26_generate_figures.py`  
**Output Directory:** `figures/cicids2017_revision_v1/`

| Figure | Description | Formats | Status |
| :--- | :--- | :--- | :--- |
| **Figure 1** | Cross-Dataset Zero-Day Recall vs Operational FPR (UNSW Backdoor vs CIC Bot) | PNG (300 DPI) + PDF | **PASS** |
| **Figure 2** | CIC Model Performance Comparison Across Matched-FPR Budgets (with C06 Marker) | PNG (300 DPI) + PDF | **PASS** |
| **Figure 3** | Operational Alert Burden (Alerts per 10k Benign Flows vs Nominal Budgets) | PNG (300 DPI) + PDF | **PASS** |
| **Figure 4** | TreeSHAP Attribution Shift Following Shortcut Ablation (Destination Port & Init Win) | PNG (300 DPI) + PDF | **PASS** |

---

## 7. Execution Environment & Dependencies

- **Host Platform:** Windows 11 Enterprise (amd64)
- **CPU:** Intel Core i5-11400H @ 2.70GHz (6 physical cores, 12 threads)
- **RAM:** 16.0 GB DDR4
- **GPU:** NVIDIA GeForce RTX 3050 Laptop GPU (4.29 GB VRAM, Compute Capability 8.6)
- **Python:** 3.11.9 (`.venv\Scripts\python.exe`)
- **PyTorch:** 2.7.1+cu118
- **CUDA:** 11.8
- **Scikit-Learn:** 1.6.1
- **Matplotlib:** 3.11.1
- **Pandas:** 2.2.3
- **NumPy:** 2.2.3

---

## 8. Exact Reproduction Commands

All Sprint 6 results are completely reproducible using the following commands executed from the repository root:

```bash
# Step 1: Matched-FPR Analysis
.venv\Scripts\python.exe cicids2017/src/s23_matched_fpr_analysis.py

# Step 2: Deployment Latency & Throughput Benchmark
.venv\Scripts\python.exe cicids2017/src/s24_deployment_benchmark.py

# Step 3: Cross-Dataset Master Table
.venv\Scripts\python.exe cicids2017/src/s25_cross_dataset_table.py

# Step 4: Publication Figures
.venv\Scripts\python.exe cicids2017/src/s26_generate_figures.py

# Step 6: Invariant Verification
.venv\Scripts\python.exe cicids2017/verify_sprint6_invariants.py
```

---

## 9. Final PASS/FAIL Determination

**SPRINT 6 STATUS: PASS**

All preflight checks, analysis scripts, benchmarks, tables, publication figures, and deliverables have executed to completion without errors or integrity violations.
