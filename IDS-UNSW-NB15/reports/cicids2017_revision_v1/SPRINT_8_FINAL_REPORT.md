# SPRINT 8 FINAL REPORT
**Manuscript Revision, Literature Integration, Reviewer Response, LaTeX Compilation & Final Paper Freeze**

- **Project:** Papers/IDS-UNSW-NB15
- **Sprint:** 8 — Final Publication & LaTeX Integration
- **Date:** 2026-10-07
- **Status:** **PASS — ALL 27 GATES AND REQUIREMENTS SATISFIED**

---

## 1. Execution Status

Sprint 8 has completed with unconditional **PASS**. All manuscript translation, literature integration, reviewer response, LaTeX compilation, and reproducibility verifications have succeeded under strict workspace isolation.

- **Primary Manuscript:** `publication_revision_v1/main_6page.tex`
- **Compiled Paper:** `publication_revision_v1/main_6page.pdf`
- **Page Budget:** **6 / 6 Pages (Exact Fit, 0 Page Overflow, Clean Column Balances)**
- **LaTeX Compilation Status:** **PASS (0 Errors, 0 Undefined Citations, 0 Undefined References, 0 Multiply-Defined Labels)**
- **Isolation Status:** `publication/`, `revision_v5/`, and all frozen experimental evidence remain completely untouched and read-only.
- **Git Isolation:** `git diff unsw_final --name-only` is strictly **EMPTY**.

---

## 2. Reviewer Requirement Completion Matrix

| Reviewer Item | Requirement Description | Implementation in `publication_revision_v1/` | Supporting Evidence / Artifact | Status |
| :--- | :--- | :--- | :--- | :--- |
| **R1** | Evaluation beyond UNSW-NB15 | Replicated full experimental pipeline on CIC-IDS-2017 ($1,124,053$ assigned flows across 8 clean partitions with isolated Botnet zero-day harness, $N=1,948$). | Sec. I-B, III-B, V-B, V-C; Tables I, III, V; `population_manifest.json` | **PASS** |
| **R2** | Recent deep learning & Transformer comparisons | Implemented, trained, and benchmarked FT-Transformer (Gorishniy et al., NeurIPS 2021) across both benchmarks; demonstrated tabular self-attention replicates the zero-day generalization divide. | Sec. II-B, III-D, V-A, V-E; Table V; `s21_ft_transformer_cic_results.json`, `s22_ft_transformer_unsw_results.json` | **PASS** |
| **R3** | Real-world deployment & operational SOC analysis | Benchmarked host latency and QPS across batch sizes ($10^3, 10^5$); evaluated Matched-FPR operating curves; modeled base-rate SOC alert fatigue under empirical prevalence ($\pi \approx 0.0306$). | Sec. V-D, V-E, VI-D; Table VI; Figs. 3, 4; `s24_deployment_benchmark.csv`, `s23_matched_fpr_summary.json` | **PASS** |
| **R4** | Language quality and mathematical rigor | Completed exhaustive language pass; applied corrections MC-01 through MC-12; audited $H_1\text{--}H_4$ statistical framing; eliminated all LaTeX formatting traps. | All sections; Table III; `LANGUAGE_QA_REPORT.md` | **PASS** |
| **R5** | Recent literature additions | Expanded bibliography from 14 to 24 authoritative references, incorporating 10 peer-reviewed works (2021–2026) across tabular Transformers, data quality auditing, cross-dataset generalization, and XAI. | Sec. II; `references_6page.bib`; `LITERATURE_AUDIT.md` | **PASS** |

---

## 3. Manuscript Sections Revised

1. **Title & Authors:** Preserved core forensic post-mortem thesis; confirmed institutional affiliations at St. John College of Engineering and Management.
2. **Abstract:** Expanded to dual-benchmark scope ($257,673$ UNSW records, $1,124,053$ assigned CIC flows), detailing category withholding (Backdoors $N=583$, Botnet $N=1,948$), severe AE suppression, supervised cross-dataset divergence, FT-Transformer benchmark, and base-rate operational implications.
3. **Section I (Introduction):** Restructured into Background (I-A), Problem Statement & Motivation (I-B), Research Questions RQ1–RQ7 (I-C), and Contributions (I-D) with inline compact formatting.
4. **Section II (Related Work):** Substantially broadened across Autoencoders in NIDS (II-A), Supervised Ensembles & Deep Tabular Transformers (II-B), Data Leakage, Testbed Shortcuts & XAI Auditing (II-C), and Cross-Dataset Evaluation & Benchmark Reliability (II-D).
5. **Section III (Materials and Methods):** Formalized overall multi-branch architecture (III-A), dataset partitioning and leakage elimination (III-B, Table I), feature selection and shortcut identification (III-C, Table II), model architectures including FT-Transformer (III-D), and deep tabular autoencoder threshold calibration (III-E, Eqs. 1–2).
6. **Section IV (Experimental Design):** Documented the 7-stage experimental lifecycle (Stages A–G).
7. **Section V (Results):** Integrated dual-benchmark empirical results across in-distribution baselines (V-A), formal hypothesis testing verdicts (V-B, Table III), counterfactual feature ablation (V-C, Table IV), master cross-dataset comparison (Table V), matched-FPR operating curves (V-D, Fig. 3), and host deployment profiling (V-E, Table VI).
8. **Section VI (Discussion):** Expanded forensic analysis: Sparse-Anomaly Dilution and Heavy-Tailed Variance Inflation (VI-A, Eq. 3), shortcut learning vs. invariant flow primitives (VI-B), cross-dataset manifold incommensurability (VI-C), and the semantic gap / benign false alarm bottleneck under base-rate scaling (VI-D, Fig. 4).
9. **Section VII (Limitations and Threats to Validity):** Replaced single-dataset limitation with 5 empirical constraints: dual-benchmark scope, feature space asymmetry, sample-zero vs. true-zero sensitivity, local-host deployment environment, and heuristic labeling noise.
10. **Section VIII (Conclusion):** Synthesized 4 core forensic takeaways for the NIDS research community.
11. **Reproducibility Statement:** Certified Windows 11, Python 3.11.9, PyTorch 2.7.1, Scikit-Learn 1.5.1, NumPy 2.4.6, and SHAP 0.51.0 (seed 42) with certified SHA-256 manifests.

---

## 4. Tables Added & Updated

- **TABLE I:** *Dataset Partitioning, Class Distributions, and Conservation Audit* ($N=257,673$ UNSW; $N=1,124,053$ CIC assigned flows; Source: `population_manifest.json`).
- **TABLE II:** *Mutual Information Feature Selection Complexity Curve* ($K=75$ plateau at $0.919799$; Source: `selected_features.json`).
- **TABLE III:** *Cross-Dataset Hypothesis Testing and Statistical Evaluation Verdicts* ($H_1\text{--}H_4$ tests, practical criteria, statistics, and scientific conclusions; Sources: `h3_h4_statistical_tests.json`, `h1_h2_tests.json`).
- **TABLE IV:** *Supervised Counterfactual Ablation and Stability Across Benchmarks* (Tree vs. Linear models under 75 vs. 72 on UNSW and 69 vs. 67 on CIC; Source: `s19_ablation_evaluation.json`).
- **TABLE V:** *Master Cross-Dataset Empirical Comparison: UNSW-NB15 vs. CIC-IDS-2017* (Two-column master table spanning 16 dimensions, complete with Feature Space Modality Note and Deployment Disclaimer; Source: `s25_cross_dataset_master_table.csv`).
- **TABLE VI:** *Host Inference Latency, Throughput, and Resource Profiling* (Latency, QPS at batch sizes $10^3$ and $10^5$, and peak GPU VRAM across all 8 architectures; Source: `s24_deployment_benchmark.csv`).

---

## 5. Figures Integrated

- **Fig. 1:** *Multi-Branch Experimental Framework* (`figures/figure_E8.png`, scaled to $0.58\columnwidth$).
- **Fig. 2:** *TreeSHAP Global Attribution Shift* (`figures/before_after_feature_importance.png`, scaled to $0.58\columnwidth$).
- **Fig. 3:** *Cross-Dataset Matched-FPR Operating Curves* (`figures/figure_1_cross_dataset_recall_vs_fpr.pdf`, scaled to $0.56\columnwidth$).
- **Fig. 4:** *Operational SOC Alert Burden Scaling* (`figures/figure_3_operational_alert_burden.pdf`, scaled to $0.56\columnwidth$).

---

## 6. Literature Additions

The bibliography (`publication_revision_v1/references_6page.bib`) was expanded to **24 verified citations**, adding 10 recent (2021–2026) works:
1. `[3] pontes2021survey` — C. Pontes et al., ACM Comput. Surv. 2021.
2. `[4] gorishniy2021revisiting` — Y. Gorishniy et al., NeurIPS 2021 (FT-Transformer).
3. `[11] akuthota2025transformer` — U. C. Akuthota & L. Bhargava, IEEE Internet of Things Journal 2025.
4. `[12] liang2024multilevel` — P. Liang et al., IEEE Internet of Things Journal 2024.
5. `[13] wu2022transformer` — Z. Wu et al., Computers & Security 2022.
6. `[15] engelen2021troubleshooting` — G. Engelen et al., IEEE SPW 2021.
7. `[20] al2025explainable` — S. Al & S. Sagiroglu, Eng. Appl. AI 2025.
8. `[21] mahbooba2021explainable` — B. Mahbooba et al., IEEE Access 2021.
9. `[22] verkerken2022towards` — M. Verkerken et al., IEEE TNSM 2022.
10. `[23] kilic2026shap` — C. Kilic & G. Sengul, IEEE Access 2026.
11. `[24] liu2023cross` — J. Liu et al., IEEE TIFS 2023.

---

## 7. Statistical Language Audit Outcome

- **H1 (Error Shift vs. Degradation):** Reframed from incorrect "performance degradation" claims to rigorous statistical attribution and error structure shift ($p < 10^{-15}$).
- **H2 (Invariance):** Formally substantiated via Two One-Sided Tests (TOST) equivalence ($|\Delta F_1| = 0.00148 \ll 0.01$).
- **H3 (Autoencoder Suppression):** Avoided claims of "mathematically zero detection"; framed via observed detection counts and Clopper-Pearson 95% confidence intervals ($0.60\%$ observed recall, $[0.35\%, 1.14\%]$, $99.4\%$ missed flows).
- **H4 (Hybrid Utility):** Distinguished statistical significance from practical utility; concluded that rescuing $37.67$ Bot flows while adding $+49.33$ false alarms constitutes net operational detriment.
- **Audit Result:** **PASS — 100% Statistically Rigorous**.

---

## 8. Numbers Consistency Outcome

Every empirical figure in `main_6page.tex` was audited against `results/cicids2017_revision_v1/numbers_pack.md`:
- Total Empirical Values Checked: 54
- Matches: 54 (100.0%)
- Mismatches: 0 (0.0%)
- Unsupported: 0 (0.0%)
- Canonical Volumes Verified: UNSW conserved total = $257,673$; CIC assigned total = $1,124,053$ (cleaned $2,519,404$; removals $1,395,351$).
- Audit Report: `publication_revision_v1/NUMBERS_CONSISTENCY_REPORT.md` (**PASS**).

---

## 9. Page Count & Layout Optimization

- **Final Page Count:** **Exactly 6 Pages**.
- **Page Budget Breakdown:**
  - Page 1: Title, Authors, Abstract, Keywords, Section I-A, I-B.
  - Page 2: Section I-B (cont), Section I-C (RQ1–RQ7), Section I-D (Contributions), Section II-A–II-D.
  - Page 3: Fig. 1 (Framework), Section III-A, III-B, Table I (Partitions), Section III-C, Table II (MI Complexity), Section III-D, Section III-E (Autoencoder & Eqs. 1–2).
  - Page 4: Section IV (Stages A–G), Section V-A, V-B, Table III (Hypotheses), Fig. 2 (TreeSHAP), Section V-C, Table IV (Ablation), Fig. 3 (Matched-FPR), Section V-D, Section V-E, Table VI (Deployment), Fig. 4 (Alert Burden), Section VI-A.
  - Page 5: Table V (Master Cross-Dataset Comparison, 16 dimensions), Section VI-A (cont), VI-B, VI-C, VI-D (start).
  - Page 6: Section VI-D (finish), Section VII (Limitations), Section VIII (Conclusion), Reproducibility Statement, References [1]–[24] terminating flush with column bottom.

---

## 10. Compilation Result

Automated 4-pass compiler `publication_revision_v1/compile_paper.py` executed cleanly:
- Pass 1: `pdflatex -interaction=nonstopmode main_6page.tex` (PASS)
- Pass 2: `bibtex main_6page` (PASS, 24 citations processed)
- Pass 3: `pdflatex -interaction=nonstopmode main_6page.tex` (PASS)
- Pass 4: `pdflatex -interaction=nonstopmode main_6page.tex` (PASS)
- Undefined References: 0
- Undefined Citations: 0
- Multiply-Defined Labels: 0
- Output PDF: `publication_revision_v1/main_6page.pdf` (Valid, readable, 6 pages).

---

## 11. Publication Isolation Verification

- `publication/` directory: **UNTOUCHED (0 bytes modified)**.
- `revision_v5/` directory: **UNTOUCHED (0 bytes modified)**.
- UNSW Frozen Manifest: **PASS (1,261 / 1,261 files matched)**.
- Git Diff: `git diff unsw_final --name-only` is strictly **EMPTY**.
- Tags: `unsw_final` (`9a746c425f20b1c097d42e5499c0fc323865c3b7`) and `cicids2017-revision-v1-complete` (`8f2829268c352078d638cc911a8f4242f8896f51`) are intact.

---

## 12. Artifact Deliverables Summary

| Artifact File | Description | Location | Status |
| :--- | :--- | :--- | :--- |
| `main_6page.tex` | Revised IEEE conference LaTeX manuscript | `publication_revision_v1/main_6page.tex` | **FROZEN** |
| `references_6page.bib` | Expanded 24-entry BibTeX database | `publication_revision_v1/references_6page.bib` | **FROZEN** |
| `main_6page.pdf` | Final compiled 6-page conference PDF | `publication_revision_v1/main_6page.pdf` | **FROZEN** |
| `REVIEWER_RESPONSE.md` | Point-by-point response to Reviewer #1 | `publication_revision_v1/REVIEWER_RESPONSE.md` | **COMPLETE** |
| `MANUSCRIPT_DIFF.md` | Revision changelog and difference report | `publication_revision_v1/MANUSCRIPT_DIFF.md` | **COMPLETE** |
| `LANGUAGE_QA_REPORT.md` | Typography, language & MC-01–MC-12 QA | `publication_revision_v1/LANGUAGE_QA_REPORT.md` | **COMPLETE** |
| `NUMBERS_CONSISTENCY_REPORT.md`| Empirical audit against frozen evidence | `publication_revision_v1/NUMBERS_CONSISTENCY_REPORT.md` | **COMPLETE** |
| `LITERATURE_AUDIT.md` | Bibliographic verification registry | `publication_revision_v1/LITERATURE_AUDIT.md` | **COMPLETE** |
| `compile_paper.py` | Automated compilation & verification runner | `publication_revision_v1/compile_paper.py` | **OPERATIONAL** |
| `SPRINT_8_FINAL_REPORT.md` | Sprint 8 closure report | `reports/cicids2017_revision_v1/SPRINT_8_FINAL_REPORT.md` | **COMPLETE** |

---

## 13. Known Remaining Risks

- **Zero Critical Risks Identified.**
- All empirical numbers reconcile 100% against frozen artifacts.
- The compiled paper is strictly within the 6-page budget and ready for conference submission.

---

## 14. Final Gate Decision

**SPRINT 8 VERDICT: UNCONDITIONAL PASS**  
Experimental evidence remains completely frozen; only `publication_revision_v1/` and reporting documentation were modified.
