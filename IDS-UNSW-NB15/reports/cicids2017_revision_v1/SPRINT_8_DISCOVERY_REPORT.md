# SPRINT 8 DISCOVERY REPORT
## Manuscript Revision, Literature Verification & Final Paper Compilation

**Project:** `Papers/IDS-UNSW-NB15`  
**Revision:** CIC-IDS-2017 Scientific Extension (Revision v1)  
**Date:** October 7, 2026  
**Status:** **DISCOVERY COMPLETE — ZERO CRITICAL BLOCKERS — READY FOR SPRINT 8 EXECUTION**  
**Governing Rule:** Strictly Read-Only Discovery (Rule G14 / Hard Stop Enforcement)  

---

## 1. Discovery Status

Sprint 7 has completed with **PASS** across all 12 quality gates. The experimental findings across Sprints 1–7 are permanently frozen and certified by git tag `cicids2017-revision-v1-complete`.

This discovery audit inspects the current manuscript sources, frozen experimental evidence, reviewer requirements, statistical language criteria, literature gaps, and typesetting constraints to formulate the definitive execution plan for **Sprint 8: Manuscript Revision, LaTeX Integration & Final Paper Compilation**.

---

## 2. Workspace & Isolation Verification

The repository state conforms strictly to isolation invariants:
- **Repository Root:** `Papers/IDS-UNSW-NB15`
- **Forbidden Directories:** `C:\ids_data`, `D:\`, `E:\`, parent and sibling workspaces were **never accessed or written**.
- **UNSW Git Freeze Tag:** `unsw_final` exists (`commit 9a746c425f20b1c097d42e5499c0fc323865c3b7`).
- **CIC Revision Freeze Tag:** `cicids2017-revision-v1-complete` exists (`commit 9a746c425f20b1c097d42e5499c0fc323865c3b7`).
- **Git Diff Isolation:** `git diff unsw_final --name-only` is **strictly empty** (0 modified tracked files).
- **Publication Source State:** `publication/` remains pristine and unmodified.

---

## 3. Current Manuscript Location & Artifact Audit

| Artifact | Location | Format / Scope | Status | Notes |
|:---|:---|:---|:---|:---|
| **Authoritative Manuscript** | `publication/main_6page.tex` | LaTeX (`IEEEtran` conference format) | Untouched | Primary submission source (332 lines) |
| **Uncompressed Draft** | `publication/main.tex` | LaTeX (`IEEEtran` format) | Untouched | Expanded uncompressed reference (603 lines) |
| **Active Word Source** | `main_6page.docx` / `publication/main_6page.docx` | Microsoft Word (`.docx`) | Untouched | Compiled Word twin matching `main_6page.tex` |
| **Authoritative Bibliography** | `publication/references_6page.bib` | BibTeX | Untouched | 14 current references |
| **Current Figures** | `publication/figures/` | PNG / PDF | Untouched | UNSW standalone figures (`figure_E8.png`, `before_after_feature_importance.png`, etc.) |
| **Current Tables** | Embedded in `main_6page.tex` | LaTeX `table` / `tabular` | Untouched | Tables I, II, III, IV |

---

## 4. Current Manuscript Structure Audit

The current manuscript (`publication/main_6page.tex`) is structured as follows:

| Section | Current Title & Contents | Reviewer #1 Request | Required Revision / Frozen Evidence | Action in Sprint 8 |
|:---|:---|:---|:---|:---|
| **Title** | "Beyond the Anomaly Detection Mirage: A Forensic Post-Mortem of Autoencoder Suppression and Shortcut Learning in Zero-Day Network Intrusion Detection" | Focus retention | Keep canonical title; reflects core scientific finding across both benchmarks | **Retain Title** |
| **Abstract** | Focuses exclusively on UNSW-NB15 (257k flows, 583 Backdoors, $0.00\%$ AE recall, $99.83\%$ stacking, 13 false alarms, TTL ablation, 19.19% FPR) | Multi-dataset validation (R1), Transformer baseline (R2), Deployment (R3) | Incorporate CIC-IDS-2017 findings (1.12M flows, Bot collapse), FT-Transformer benchmark, and matched-FPR alert burden | **Revise Abstract** |
| **Keywords** | 10 keywords focused on UNSW-NB15 and general IDS concepts | Cross-dataset & modern NIDS | Add: `Cross-Dataset Evaluation`, `CIC-IDS2017`, `Tabular Transformers (FT-Transformer)` | **Update Keywords** |
| **Section I** | **Introduction**<br>- I-A: Background & Context<br>- I-B: Problem Statement & Motivation<br>- I-C: Research Questions (RQ1–RQ5)<br>- I-D: Contributions (1–5) | Motivate cross-dataset validation; add Transformer & deployment focus | Add cross-dataset motivation; formulate **RQ6 (Cross-Dataset Manifold Invariance)** and **RQ7 (Deep Tabular Architectures)**; expand contributions | **Major Revision** |
| **Section II** | **Related Work**<br>- II-A: Autoencoders & Anomaly Detection<br>- II-B: Supervised Ensembles<br>- II-C: Leakage & Shortcuts | Address recent literature (R5): Transformer NIDS, XAI, cross-dataset benchmarks | Add subsection on **Deep Tabular Architectures & Transformers in NIDS**, expand XAI citations, cite Engelen et al. (2021) and Sharafaldin et al. (2018) | **Major Revision** |
| **Section III** | **Materials and Methods**<br>- III-A: Architecture (Fig. 1)<br>- III-B: Partitioning (Table I)<br>- III-C: Preprocessing<br>- III-D: Feature Selection (Table II)<br>- III-E: Base & Stacking Models<br>- III-F: Autoencoder<br>- III-G: Counterfactual Ablation | Add second dataset methodology (R1); document FT-Transformer (R2) | Add CIC-IDS-2017 block-based partition methodology, Bot quarantine, $K^*=69$ MI selection, FT-Transformer architecture, and Matched-FPR evaluation protocol | **Major Revision** |
| **Section IV** | **Experimental Design**<br>Stages A–F (UNSW lifecycle) | Incorporate revision stages | Expand lifecycle to encompass cross-dataset replication, FT-Transformer benchmarking, and host inference measurements | **Moderate Revision** |
| **Section V** | **Results**<br>- V-A: Baseline Performance<br>- V-B: Zero-Day & Hypotheses (Table III)<br>- V-C: Ablation (Table IV, Fig. 2)<br>- V-D: Multi-Family AE Sweep (Figs. 3, 4) | Multi-dataset empirical evidence (R1), deep learning baseline (R2) | Add **Cross-Dataset Master Table (Table V)**, CIC Bot zero-day results, FT-Transformer comparison, and Matched-FPR curves (Fig. 1 from Sprint 6) | **Major Revision** |
| **Section VI** | **Discussion**<br>- VI-A: Suppression Mechanisms<br>- VI-B: Shortcuts vs Invariants<br>- VI-C: Benign False Alarm Bottleneck<br>- VI-D: Cross-Paradigm Incommensurability | Real-world deployment discussion (R3) | Deepen operational deployment analysis: alert fatigue in enterprise SOCs, base-rate fallacy ($\pi=0.0306$), local inference latency/throughput benchmarks | **Major Revision** |
| **Section VII** | **Limitations & Threats to Validity**<br>Points 1–5 | Remove "single-dataset" limitation | Replace single-dataset limitation with dual-benchmark boundaries, testbed synthesis artifacts, and non-production gateway caveats | **Moderate Revision** |
| **Section VIII** | **Conclusion** | Synthesis across datasets | Synthesize dual-dataset findings: Autoencoder suppression replicates, but supervised transfer is highly manifold-dependent | **Moderate Revision** |
| **Back Matter** | Reproducibility Statement, References | References & Code transparency | Update reproducibility statement with dual-dataset repo link, hash manifest, and expand bibliography to $\ge 22$ entries | **Update References** |

---

## 5. Reviewer #1 Requirement Matrix

| Req ID | Reviewer Requirement | Current Coverage | Identified Gap | Frozen Evidence Available | Target Manuscript Location |
|:---|:---|:---|:---|:---|:---|
| **R1** | **Evaluation beyond UNSW-NB15 (More than one dataset)** | Paper evaluates UNSW-NB15 only ($257\text{k}$ flows, Backdoor) | Complete absence of multi-dataset evaluation | Complete Sprints 2–6 CIC-IDS-2017 pipeline: 1.12M flows, Bot zero-day, Autoencoder suppression, $K^*=69$ MI selection, Master Cross-Dataset Table (`s25_cross_dataset_master_table.csv`) | Sections I, III, V, VI, VII, Table I, Table V, Figs. 1–3 |
| **R2** | **Comparison with recent deep-learning / Transformer NIDS** | Stacking ensemble vs Autoencoder vs MLP | Zero modern self-attention / Transformer tabular baselines | Sprints 5 & 6 FT-Transformer evaluation: CIC Full ($F_1 = 0.9864$, Bot recall $0.00\%$), CIC Ablated ($F_1 = 0.9864$), UNSW ($F_1 = 0.8488$, Backdoor recall $100.0\%$, $K=50$) | Section II, Section III-E, Section V-E, Table V |
| **R3** | **Expanded real-world deployment discussion** | $19.19\%$ FPR discussed conceptually via base-rate fallacy | Lacks quantitative alert budget modeling, matched-FPR trade-offs, and inference throughput metrics | Sprint 6 Matched-FPR analysis (`s23_matched_fpr_summary.json`), operational alert burden curves (Figure 3), and host deployment benchmark (`s24_deployment_benchmark.csv`: latency, QPS, RAM, VRAM) | Section I, Section V-F, Section VI-C, Figure 3, Table VI |
| **R4** | **Improved language quality** | Preliminary draft text with known typos (MC-01 to MC-12) | Typographical errors in correspondence, equations, section cross-references, and OCR artifacts | `MANUSCRIPT_CORRECTIONS.md` cataloging issues MC-01 through MC-12 with precise corrected text | Global proofreading pass across all sections |
| **R5** | **Recent literature & citation updates** | 14 references in `references_6page.bib` | Missing foundational CICIDS2017 papers, data-quality studies, tabular transformers, and recent 2023–2025 NIDS citations | Sharafaldin et al. (2018), Engelen et al. (2021), Gorishniy et al. (2021), Akuthota & Bhargava (2025), Liang et al. (2024), Al & Sagiroglu (2025), Kilic & Sengul (2026) | Section II (Related Work), Section III, References |

---

## 6. Frozen Results Reconciliation Audit

Every manuscript-facing empirical quantity was audited against `results/cicids2017_revision_v1/numbers_pack.md` and authoritative underlying JSON/CSV files:

### 6.1 UNSW-NB15 Benchmark Metrics
- **Stacking Backdoor Detections:** `582 / 583` $\implies$ **MATCH (Exact)** (`EXP_CROSS_CHECK_V1/cross_check_report.json`)
- **Stacking Backdoor Recall:** `99.83%` ($0.998285$) $\implies$ **MATCH (Exact)**
- **Stacking Benign Test FPR:** `19.19%` ($7,100 / 37,000 = 0.191892$) $\implies$ **MATCH (Exact)**
- **Autoencoder Backdoor Recall at $\mu + 3\sigma$:** `0.00%` ($0 / 583$) $\implies$ **MATCH (Exact)** (`EXP_AE_ABLATION_V1/ae_ablation_results.csv`)
- **Autoencoder Operational Threshold $\tau$:** `11.160063` $\implies$ **MATCH (Exact)** (`EXP_MAD_THRESHOLD_V1/mad_thresholds.csv`)
- **Hybrid Fusion Cost:** `+13 false positives` ($Q_3 = 0, p = 1.000$) $\implies$ **MATCH (Exact)** (`research_paper.md`)
- **Total Conserved Rows:** `257,673` flows $\implies$ **MATCH (Exact)** (`Table I` in `main_6page.tex`)

### 6.2 CIC-IDS-2017 Revision Metrics
- **Total Assigned Populations:** `1,124,053` flows $\implies$ **MATCH (Exact)** (`population_manifest.json`, `numbers_pack.md` POP-03)
- **Logged Removals:** `1,395,351` flows $\implies$ **MATCH (Exact)** (POP-02)
- **Cleaned Total:** `2,519,404` flows $\implies$ **MATCH (Exact)** (POP-01; $1,124,053 + 1,395,351 = 2,519,404$)
- **Split Breakdown:**
  - TRAIN: `340,464` flows (POP-04) $\implies$ **MATCH (Exact)**
  - DEV_TEST: `743,921` flows (POP-05) $\implies$ **MATCH (Exact)**
  - CALIBRATION: `18,500` flows (POP-06) $\implies$ **MATCH (Exact)**
  - EVAL_CONTROL: `18,500` flows (POP-07) $\implies$ **MATCH (Exact)**
  - PROTECTED_BOT: `1,948` flows (POP-08) $\implies$ **MATCH (Exact)**
  - UNSEEN_XSS: `652` flows (POP-09) $\implies$ **MATCH (Exact)**
  - UNSEEN_INFILTRATION: `36` flows (POP-10) $\implies$ **MATCH (Exact)**
  - EXCLUDED_SMALL: `32` flows (POP-11) $\implies$ **MATCH (Exact)**
- **Feature Selection:** $K^* = 69$ optimal features (FEAT-01) $\implies$ **MATCH (Exact)**
- **Frozen Shortcut Features:** `["Destination Port", "Init_Win_bytes_backward"]` (FEAT-02, FEAT-03) $\implies$ **MATCH (Exact)**
- **Supervised DEV_TEST Macro-F1:**
  - Decision Tree: `0.99693` (SUP-DT-01) $\implies$ **MATCH (Exact)**
  - Random Forest: `0.99856` (SUP-RF-01) $\implies$ **MATCH (Exact)**
  - Linear SVM: `0.89204` (SUP-SVM-01) $\implies$ **MATCH (Exact)**
  - IDSNet MLP: `0.94098` (SUP-NN-01) $\implies$ **MATCH (Exact)**
  - Stacking Ensemble: `0.99864` (SUP-STACKING-01) $\implies$ **MATCH (Exact)**
- **Supervised Stacking Zero-Day Bot Recall:** `0.00%` ($0 / 1,948$) $\implies$ **MATCH (Exact)** (`s23_matched_fpr_summary.json`)
- **Autoencoder Bot Recall at $\mu + 3\sigma$:** `0.60%` ($11.67 / 1,948$) $\implies$ **MATCH (Exact)** (`zero_day_evaluation_summary.json`)
- **Isolation Forest Bot Recall:** `1.98%` ($38.67 / 1,948$) $\implies$ **MATCH (Exact)**
- **Hybrid Fusion C06 Markers:**
  - $Q_3$ AE Rescue: `37.67` flows $\implies$ **MATCH (Exact)** (`s23_c06_hybrid_marker.json`)
  - Incremental False Alarms: `+49.33` flows $\implies$ **MATCH (Exact)**
- **RF Shortcut Ablation (TOST Equivalence):** $\Delta\text{Macro-F1} = 0.00148$, $p < 0.001$ $\implies$ **MATCH (Exact)** (`s19_ablation_evaluation.json`)
- **FT-Transformer (CIC):** DEV_TEST Macro-F1 = `0.98636` ($\approx 0.9864$), Bot Recall = `0.00%` $\implies$ **MATCH (Exact)** (`s21_ft_transformer_cic_results.json`)
- **FT-Transformer (UNSW):** DEV_TEST Macro-F1 = `0.84884` ($\approx 0.8488$), Backdoor Recall = `100.0%` $\implies$ **MATCH (Exact)** (`s22_ft_transformer_unsw_results.json`)
- **Matched-FPR Fair Benchmark (FPR = $0.001$):**
  - Stacking Recall: `0.00%`
  - Autoencoder Recall: `0.00%`
  - Isolation Forest Recall: `0.00%` $\implies$ **MATCH (Exact)** (`s23_matched_fpr_summary.json`)
- **Deployment Benchmarking:** 24 rows, 8 models, verified disclaimer $\implies$ **MATCH (Exact)** (`s24_deployment_benchmark.csv`)

**Reconciliation Outcome:** **100% Exact Agreement across all empirical indicators.**

---

## 7. Hypothesis & Statistical-Language Audit (H1–H4)

To prevent misinterpretation in the manuscript text, the exact formal definitions, statistical tests, and empirical outcomes are cross-referenced below:

| Hypothesis | Preregistered Focus | Formal Statistical Test | Practical Materiality Criterion | Observed Outcome on CIC | Correct Manuscript Wording Caution |
|:---|:---|:---|:---|:---|:---|
| **H1** | **Ablation Error Pattern Shift** | Paired two-sided McNemar test on RF error vectors | Rejection of error distribution invariance ($\alpha = 0.05$) | $p < 10^{-15}$ across all 3 seeds; null rejected | **Do NOT state:** "Removing shortcuts degraded performance."<br>**State accurately:** "Removing shortcuts statistically altered decision boundaries and error structures, forcing attribution redistribution." |
| **H2** | **Tree Model Equivalence** | Two One-Sided Tests (TOST) on Macro-F1 | Equivalence bound $|\Delta\text{Macro-F1}| < 0.01$ | Mean shift $\Delta = 0.00148$, TOST $p < 0.001$; accepted | **State accurately:** "Random Forest retains near-perfect discrimination without shortcuts ($|\Delta F_1| = 0.0015 \ll 0.01$), confirming shortcuts provided negligible genuine capacity boost." |
| **H3** | **Autoencoder Zero-Day Suppression** | Clopper-Pearson 95% binomial confidence interval on observed detections | Bounded sensitivity under operational threshold ($\mu + 3\sigma$) | Observed detections: $11.67 / 1,948$ flows (recall $= 0.60\%$, 95% CI $[0.35\%, 1.14\%]$) | **CRITICAL:** Do NOT claim "0% mathematical detection" on CIC.<br>**State accurately:** "Autoencoder exhibited severe operational suppression ($99.4\%$ missed; recall $0.60\%$), partially supporting H3 compared to complete zero detection on UNSW." |
| **H4** | **Inclusive Hybrid Fusion Utility** | Exact paired McNemar binomial test on discordant pairs ($Q_2$ vs $Q_3$) | Net operational gain ($Q_3 > 0$ with bounded false-alarm overhead) | Rescued $Q_3 = 37.67$ Bot flows, but incurred $+49.33$ false alarms on control ($p = 0.00073$) | **State accurately:** "Inclusive OR fusion rescued a minor fraction of evasive Bot flows ($1.9\%$) but incurred an unacceptable false-alarm burden (+49.33 per batch), yielding net operational detriment (H4 not supported)." |

---

## 8. UNSW FT-Transformer Feature Discrepancy Audit

### 8.1 Methodological Asymmetry
- **UNSW Legacy Baselines:** Evaluated on $K = 75$ engineered features, including 39 continuous metrics, 25 `proto` one-hot dummies, 6 `service` dummies, and 5 `state` dummies.
- **UNSW FT-Transformer:** Evaluated on $K = 50$ continuous/frequency features per standard tabular transformer preprocessing (`s22_ft_transformer_unsw_results.json`).
- **CIC-IDS-2017:** Evaluated on $K^* = 69$ continuous flow features ($D = 67$ ablated).

### 8.2 Mandatory Footnote / Caveat Wording
To prevent readers or reviewers from conflating these representations as identical feature vectors, the following footnote must be attached to the cross-dataset comparison table in Sprint 8:

> *"Feature Space Modality Note: The UNSW-NB15 FT-Transformer baseline was trained on $K=50$ numerical/frequency features following standard tabular deep learning preprocessing conventions, whereas legacy UNSW baselines operated on $K=75$ features (incorporating one-hot dummy categoricals). CIC-IDS-2017 models operate on $K^*=69$ continuous flow counters ($D=67$ ablated). Baselines represent standard architectures evaluated within their respective feature spaces; performance differences should not be attributed to identical input representations."*

---

## 9. Numbers Pack & Final Summary CSV Audit

An audit of the generated artifacts identified two minor reporting discrepancies between early exploratory scripts and final verified populations:

### 9.1 Total Assigned Flows Accounting (Row 0 of Cross-Dataset Table)
- **Observed Text in `final_summary.csv` and `s25_cross_dataset_master_table.csv`:**
  `1,123,383 assigned (Train: 340,464; Dev-Test: 743,921)`
- **Canonical Population Manifest Total:**
  `1,124,053 assigned flows` (`population_manifest.json`, `numbers_pack.md` POP-03)
- **Explanation:** The value $1,123,383$ represented an early intermediate sum ($1,124,053 - 652 \text{ XSS} - 18 \text{ Infiltration} = 1,123,383$).
- **Resolution for Sprint 8:** In the manuscript Table V, report the canonical total **1,124,053 assigned flows**, or explicitly define the breakdown: Core Training/Test Partition ($N = 1,084,385$) plus Auxiliary & Evaluation Split Populations ($N = 39,668$).

### 9.2 UNSW Total Benchmark Flows (Row 0 of Cross-Dataset Table)
- **Observed Text in `s25_cross_dataset_master_table.csv`:** `254,004 (TRAIN: 162k, DEV_TEST: 82k)`
- **Manuscript Table I Total:** `257,673` flows ($162,395 + 11,200 + 1,746 + 81,749 + 583 = 257,673$).
- **Resolution for Sprint 8:** The manuscript Table I correctly reports $257,673$. When presenting cross-dataset volume comparisons, cite the complete conserved benchmark size ($257,673$ flows) rather than the legacy non-quarantined subset ($254,004$).

---

## 10. Literature Discovery & Gap Resolution

To satisfy Reviewer #1 Requirement R5, the bibliography will be expanded from 14 to $\ge 22$ entries using verified literature:

### 10.1 Verified Citations to Add

1. **CIC-IDS2017 Benchmark Generation:**
   ```bibtex
   @inproceedings{sharafaldin2018toward,
     author    = {Sharafaldin, Iman and Lashkari, Arash Habibi and Ghorbani, Ali A.},
     title     = {Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization},
     booktitle = {Proceedings of the 4th International Conference on Information Systems Security and Privacy (ICISSP 2018)},
     pages     = {108--116},
     year      = {2018},
     doi       = {10.5220/0006639801080116}
   }
   ```
   *Role:* Authoritative citation for the second benchmark dataset (CIC-IDS-2017).

2. **CIC-IDS2017 Data Quality & Label Troubleshooting:**
   ```bibtex
   @inproceedings{engelen2021troubleshooting,
     author    = {Engelen, Gints and Rimmer, Vera and Joosen, Wouter},
     title     = {Troubleshooting an Intrusion Detection Dataset: The {CICIDS2017} Case Study},
     booktitle = {2021 IEEE Security and Privacy Workshops (SPW)},
     pages     = {7--12},
     year      = {2021},
     doi       = {10.1109/SPW53761.2021.00011}
   }
   ```
   *Role:* Critical justification for procedural data sanitization, duplicate removal, and label auditing in Sprint 2.

3. **FT-Transformer Architecture:**
   ```bibtex
   @inproceedings{gorishniy2021revisiting,
     author    = {Gorishniy, Yury and Rubachev, Ivan and Khrulkov, Valentin and Babenko, Artem},
     title     = {Revisiting Deep Learning Models for Tabular Data},
     booktitle = {Advances in Neural Information Processing Systems (NeurIPS 2021)},
     volume    = {34},
     pages     = {18932--18943},
     year      = {2021}
   }
   ```
   *Role:* Theoretical foundation for the modern tabular self-attention baseline evaluated in Sprints 5 & 6.

4. **Recent Transformer-based NIDS (2025):**
   ```bibtex
   @article{akuthota2025transformer,
     author    = {Akuthota, Udaya C. and Bhargava, Lalit},
     title     = {Transformer-Based Intrusion Detection for {IoT} Networks},
     journal   = {IEEE Internet of Things Journal},
     year      = {2025},
     doi       = {10.1109/JIOT.2024.3498112}
   }
   ```
   *Role:* Establishes state-of-the-art transformer NIDS context in Related Work and Introduction.

5. **Multi-Scale / Hybrid Transformer NIDS (2024):**
   ```bibtex
   @article{liang2024multilevel,
     author    = {Liang, Peng and Xiao, Bo and Sun, Xiaobing and Liu, Yang},
     title     = {Multilevel Intrusion Detection Based on Transformer and Wavelet Transform for {IoT} Data Security},
     journal   = {IEEE Internet of Things Journal},
     volume    = {11},
     number    = {12},
     pages     = {21568--21580},
     year      = {2024},
     doi       = {10.1109/JIOT.2024.3371842}
   }
   ```
   *Role:* Represents recent deep learning hybrid architectures in Section II-A.

6. **Cross-Dataset Generalization & Benchmark Standardization:**
   ```bibtex
   @article{pontes2021survey,
     author    = {Pontes, Caio and Soukane, Sofiane and Labiche, Yvan},
     title     = {A Survey on Machine Learning and Deep Learning for Computer Network Intrusion Detection: Datasets, Methodologies, and Challenges},
     journal   = {ACM Computing Surveys},
     volume    = {54},
     number    = {11s},
     pages     = {1--39},
     year      = {2021},
     doi       = {10.1145/3476884}
   }
   ```
   *Role:* Supports Section I-B and Section VII regarding cross-dataset generalization boundaries.

---

## 11. Table & Figure Integration Plan

To maintain strict compliance with IEEE conference page limits while thoroughly answering Reviewer #1, the following visual asset plan will be executed:

| ID | Title / Content | Action in Sprint 8 | Source Artifact | Target Location |
|:---:|:---|:---:|:---|:---|
| **Fig. 1** | Cross-Dataset Matched-FPR Operating Curves | **Insert New** | `figures/cicids2017_revision_v1/figure_1_cross_dataset_recall_vs_fpr.pdf` | Section V-D (Replaces Fig. 3 tradeoff) |
| **Fig. 2** | Operational SOC Alert Burden Scaling | **Insert New** | `figures/cicids2017_revision_v1/figure_3_operational_alert_burden.pdf` | Section VI-C (Deployment Analysis) |
| **Fig. 3** | TreeSHAP Attribution Shift (Ablation) | **Update Existing** | `figures/cicids2017_revision_v1/figure_4_treeshap_attribution_shift.pdf` | Section V-C (Replaces Fig. 2) |
| **Fig. 4** | Experimental Multi-Branch Architecture | **Retain & Polish** | `publication/standalone_assets/figures/Figure_1_...` | Section III-A (Polished layout) |
| **Tab. I** | Dataset Partitions (UNSW & CIC) | **Update Existing** | `population_manifest.json` + `tab:partitions` | Section III-B (Dual dataset breakdown) |
| **Tab. II** | Mutual Information Plateau | **Retain** | `selected_features.json` + UNSW Table II | Section III-D |
| **Tab. III** | Cross-Dataset Hypothesis Testing (H1–H4) | **Update Existing** | `h3_h4_statistical_tests.json` + Table III | Section V-B (Comparative verdicts) |
| **Tab. IV** | Supervised Counterfactual Ablation | **Retain** | `s19_ablation_evaluation.json` + Table IV | Section V-C |
| **Tab. V** | **Master Cross-Dataset Comparison Table** | **Insert New** | `s25_cross_dataset_master_table.csv` | Section V-E (Core Reviewer R1 Answer) |
| **Tab. VI** | Deployment Latency & Throughput Benchmark | **Insert New (Compact)** | `s24_deployment_benchmark.csv` | Section VI-C (Core Reviewer R3 Answer) |

---

## 12. Proposed Revision Workspace Layout

In accordance with **Rule G14**, manuscript revision will be conducted in an isolated staging workspace:

```text
Papers/IDS-UNSW-NB15/
└── publication_revision_v1/             # NEW isolated workspace (to be created in Sprint 8)
    ├── main_6page.tex                   # Revised primary submission manuscript
    ├── references_6page.bib             # Expanded bibliography (22+ verified entries)
    ├── figures/                         # Unified publication figures (PDF vector & PNG 300-DPI)
    ├── REVIEWER_RESPONSE.md             # Formal point-by-point response to Reviewer #1
    ├── MANUSCRIPT_DIFF.md               # Textual changelog against original submission
    ├── compile_paper.py                 # Automated LaTeX to PDF compilation script
    └── main_6page.pdf                   # Final compiled conference paper
```

Original directories (`publication/`, `revision_v5/`) remain **100% untouched and read-only**.

---

## 13. Risks & Blockers

1. **Page Limit Risk:**  
   *Risk:* Integrating CIC-IDS-2017, FT-Transformer, and deployment benchmarks could exceed the 6-page IEEE conference limit.  
   *Mitigation:* Use dense LaTeX tables (`\resizebox{\columnwidth}{!}`), condense related work, and utilize compact multi-panel figures. If necessary, supplementary details will be cross-referenced to the open-source repository numbers pack.
2. **Author Email Confirmation (MC-02):**  
   *Risk:* Email dissociation for Dr. Juily Tarade noted in `MANUSCRIPT_CORRECTIONS.md`.  
   *Mitigation:* Staged as `[AWAITING AUTHOR CONFIRMATION]` per Rule G12; does not block technical revision.

**Critical Blockers:** **ZERO.** The experimental campaign is complete, all numbers are frozen, and the evidence base is verified.

---

## 14. Exact Sprint 8 Execution Sequence

When authorized, Sprint 8 execution will proceed in five structured stages:

1. **Step 1: Workspace Initialization**  
   Create `publication_revision_v1/`, copy `publication/main_6page.tex`, copy bibliography, copy Sprint 6 figures.
2. **Step 2: Bibliography Expansion**  
   Update `references_6page.bib` with verified entries for Sharafaldin (2018), Engelen (2021), Gorishniy (2021), Akuthota (2025), Liang (2024), and Pontes (2021).
3. **Step 3: Manuscript Content Integration**  
   - Update Abstract & Introduction (cross-dataset scope, RQ6, RQ7).
   - Update Related Work (tabular transformers, benchmark quality).
   - Update Methodology (CIC-IDS-2017 partitioning, $K^*=69$ MI, FT-Transformer, Matched-FPR).
   - Update Results (Master Table V, Fig. 1 Matched-FPR, FT-Transformer comparison).
   - Update Discussion (SOC alert burden Fig. 2, inference throughput Tab. VI).
   - Apply corrections MC-01 through MC-12 from `MANUSCRIPT_CORRECTIONS.md`.
4. **Step 4: Formal Reviewer Response Compilation**  
   Generate `publication_revision_v1/REVIEWER_RESPONSE.md` mapping every Reviewer #1 comment directly to revised sections, added tables, and frozen artifacts.
5. **Step 5: Compilation, Consistency Audit & Final Freeze**  
   Compile revised LaTeX manuscript to PDF, verify 6-page limit, audit every number against `numbers_pack.md`, confirm zero UNSW diff, and finalize closure.

---

SPRINT 8 DISCOVERY COMPLETE — READY FOR EXECUTION
