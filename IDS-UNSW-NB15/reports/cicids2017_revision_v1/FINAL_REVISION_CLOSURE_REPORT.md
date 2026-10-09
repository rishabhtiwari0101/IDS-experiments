# Final Revision Closure Report — CIC-IDS-2017 Revision v1
**Sprint:** 7 (Verification, Reproducibility & Results Freeze)  
**Overall Status:** PASS — EXPERIMENTAL CAMPAIGN OFFICIALLY FROZEN & CLOSED  
**Date:** October 7, 2026  
**Handoff Target:** Sprint 8 (Manuscript Integration & Final Paper Compilation)  

---

## 1. Sprint Lifecycle & Gate Verdicts

The multi-sprint revision campaign has concluded with 100% successful gate completion across all phases:

| Sprint | Title | Objective | Verdict | Evidence Artifact |
|:---|:---|:---|:---|:---|
| **Sprint 1** | Project Infrastructure & Discovery | Environment discovery, GPU verification, frozen isolation | **PASS** | `reports/cicids2017_revision_v1/SPRINT_1_REPORT.md` |
| **Sprint 2** | Data Ingestion & Sanitization | Shard audit, deduplication, 8 disjoint partitions (1.12M) | **PASS** | `reports/cicids2017_revision_v1/SPRINT_2_REPORT.md` |
| **Sprint 3** | Feature Selection & Supervised Baselines | MI plateau ($K^*=69$), 5 base models, OOF stacking, shortcut freeze | **PASS** | `reports/cicids2017_revision_v1/SPRINT_3_REPORT.md` |
| **Sprint 4** | Anomaly Detection & Zero-Day Evaluation | Autoencoders, Isolation Forest, threshold calibration, zero-day Bot eval | **PASS** | `reports/cicids2017_revision_v1/SPRINT_4_REPORT.md` |
| **Sprint 5** | Feature Ablation & Deep Tabular Baselines | TreeSHAP shift, TOST equivalence (H1/H2), FT-Transformer (CIC & UNSW) | **PASS** | `reports/cicids2017_revision_v1/SPRINT_5_REPORT.md` |
| **Sprint 6** | Matched-FPR, Deployment & Figures | Fair Matched-FPR benchmark, host inference benchmark, Figures 1–4 | **PASS** | `reports/cicids2017_revision_v1/SPRINT_6_REPORT.md` |
| **Sprint 7** | Verification, Reproducibility & Freeze | 12-Gate Master Audit, Numbers Pack (224), Summary CSV, CIC Manifest | **PASS** | `reports/cicids2017_revision_v1/SPRINT_7_REPORT.md` |

---

## 2. Final Evidence Inventory

The experimental evidence supporting the revision is fully persisted, tamper-evident, and auditable:

1. **Partitions & Populations:**
   - 8 mutually disjoint split CSVs totaling 1,124,053 assigned flows.
   - Cleaned flow accounting: $2,519,404 - 1,395,351 = 1,124,053$. Zero leaks, zero overlap.
2. **Model Artifacts:**
   - 75 serialized model checkpoints, PyTorch weights, and StandardScalers across random seeds 42, 123, and 2024.
   - Zero missing or zero-byte model files.
3. **Statistical Artifacts:**
   - Formal test records for H1, H2, H3, and H4 including exact two-sided McNemar binomial tests and Two One-Sided Tests (TOST) equivalence intervals.
4. **Publication Figures:**
   - 4 publication figures generated in dual formats: 300-DPI PNG and publication vector PDF (`figures/cicids2017_revision_v1/`).
5. **Authoritative Numbers Pack:**
   - `results/cicids2017_revision_v1/numbers_pack.md` mapping 224 distinct metrics directly to source JSON/CSV fields.
6. **Master Summary Table:**
   - `results/cicids2017_revision_v1/final_summary.csv` providing a 16-dimension comparative audit between UNSW-NB15 and CIC-IDS-2017.

---

## 3. Results Freeze & Reconciliation Integrity

- **Table-to-Result Reconciliation:** **100% exact agreement** across all reported figures, tables, and text summaries. Zero discrepancies detected.
- **UNSW-NB15 Isolation:** 1,261 files verified via SHA-256 with 0 mismatches. `git diff unsw_final` is strictly empty.
- **Shortcut Freeze:** Cryptographic hash `5e2942c8a5e5083f71d214ecb2c62d015025bba9cbbad2583ff2b36eb5f86ab2` confirmed. Preceded zero-day evaluation by 2 hours, 54 minutes, and 20 seconds.

---

## 4. Scientific Finding Summary

The multi-dataset experimental campaign establishes three major scientific findings:

1. **Cross-Dataset Generalization Asymmetry:**
   Supervised stacking ensembles that exhibited serendipitous generalization on the UNSW-NB15 Backdoor class ($99.83\%$ recall) suffered catastrophic blindness on the CIC-IDS-2017 Bot class ($0.00\%$ recall). Generalization is profoundly sensitive to attack-manifold structure.
2. **Replication of the Anomaly Suppression Phenomenon:**
   On both benchmarks, unsupervised Autoencoders calibrated under realistic operational false-alarm constraints ($\text{FPR} \le 10^{-3}$, Chebyshev $\mu + 3\sigma$) failed completely, missing $>99\%$ of zero-day attacks due to heavy-tailed benign connection variance pushing thresholds outward.
3. **Operational Detriment of Inclusive Hybrid Fusion:**
   Naive logical-OR fusion strictly degraded alert precision across both environments. On CIC-IDS-2017, OR fusion marginally rescued $1.9\%$ of Bot attacks but generated an unacceptable $+49.33$ false alarms per test batch.

---

## 5. Formal Authorization for Sprint 8

With all 12 Gates of Sprint 7 achieving **PASS**, all experimental evidence is permanently frozen.

**Authorization:**
Sprint 8 (Manuscript Revision, LaTeX Integration, and Final Paper Compilation) is formally authorized to commence. No further model training or experimental modification is permitted.
