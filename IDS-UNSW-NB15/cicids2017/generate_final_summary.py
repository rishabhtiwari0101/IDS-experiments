"""
cicids2017/generate_final_summary.py
------------------------------------
Generates the authoritative comparative summary CSV:
results/cicids2017_revision_v1/final_summary.csv

Columns:
category,dimension,metric_name,unsw_nb15_value,cicids2017_value,scientific_finding,source_artifact,manuscript_section
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / "results" / "cicids2017_revision_v1" / "final_summary.csv"

rows = [
    # 1. Dataset Scale & Scope
    {
        "category": "Dataset Scope",
        "dimension": "Flow Volume",
        "metric_name": "Total Benchmark Flows",
        "unsw_nb15_value": "254,004 flows (Train: 162,395; Dev-Test: 81,749)",
        "cicids2017_value": "1,123,383 assigned (Train: 340,464; Dev-Test: 743,921)",
        "scientific_finding": "CIC-IDS-2017 provides 4.4x larger flow volume and 9.1x larger evaluation split, confirming scale scalability.",
        "source_artifact": "population_manifest.json / EXP_CROSS_CHECK_V1",
        "manuscript_section": "Section 3.1 / Table 1"
    },
    {
        "category": "Dataset Scope",
        "dimension": "Attack Families",
        "metric_name": "Protected Zero-Day Class",
        "unsw_nb15_value": "Backdoor (N = 583 flows, 3.06% eval prevalence)",
        "cicids2017_value": "Bot / ARES Botnet (N = 1,948 flows, 9.53% eval prevalence)",
        "scientific_finding": "Distinct network topologies: UNSW Backdoor spans multiple protocols; CIC Bot exhibits periodic IRC C&C flows.",
        "source_artifact": "zero_day_evaluation_summary.json / s25_cross_dataset_master_table.json",
        "manuscript_section": "Section 3.2 / Table 1"
    },

    # 2. Feature Space & Caveats
    {
        "category": "Feature Representation",
        "dimension": "Dimensionality",
        "metric_name": "Selected Features Count (Caveat: Modality Disparity)",
        "unsw_nb15_value": "K = 75 (Legacy Baselines) / K = 50 (FT-Transformer)",
        "cicids2017_value": "K* = 69 (Full) / D = 67 (Ablated without shortcuts)",
        "scientific_finding": "UNSW incorporates one-hot protocol/service dummies; CIC-IDS-2017 uses purely numeric statistical flow aggregates. Baselines evaluated within respective feature spaces.",
        "source_artifact": "selected_features.json / s22_ft_transformer_unsw_results.json",
        "manuscript_section": "Section 3.3 / Table 1 Footnote C"
    },
    {
        "category": "Feature Representation",
        "dimension": "Shortcut Exploitation",
        "metric_name": "Identified Shortcut Features",
        "unsw_nb15_value": "sttl, ct_state_ttl, dttl (TTL/TCP state proxies)",
        "cicids2017_value": "Destination Port, Init_Win_bytes_backward",
        "scientific_finding": "Both datasets reveal severe synthetic flow generation artifacts; models memorize static client/server configuration signatures.",
        "source_artifact": "shortcut_list_frozen.json / EXP_TOST_V1",
        "manuscript_section": "Section 4.1 / Table 2"
    },

    # 3. Supervised Stacking Performance
    {
        "category": "Supervised Stacking",
        "dimension": "Generalization",
        "metric_name": "Protected Zero-Day Recall",
        "unsw_nb15_value": "99.83% (582 / 583 flows detected)",
        "cicids2017_value": "0.00% (0 / 1,948 flows detected)",
        "scientific_finding": "Supervised ensemble achieved complete serendipitous generalization on UNSW Backdoor, but suffered total generalization collapse on CIC Bot.",
        "source_artifact": "dev_test_evaluation.json / zero_day_evaluation_summary.json",
        "manuscript_section": "Section 4.2 / Table 3"
    },
    {
        "category": "Supervised Stacking",
        "dimension": "Operational Viability",
        "metric_name": "Benign False Positive Rate (FPR)",
        "unsw_nb15_value": "19.19% (1,918.9 false alarms per 10k flows)",
        "cicids2017_value": "0.087% (8.74 false alarms per 10k flows)",
        "scientific_finding": "CIC stacking achieves vastly superior operational precision on benign traffic, avoiding the operational alert flood observed on UNSW.",
        "source_artifact": "dev_test_evaluation.json / s23_matched_fpr_summary.json",
        "manuscript_section": "Section 4.2 / Figure 3"
    },

    # 4. Autoencoder Anomaly Suppression
    {
        "category": "Unsupervised Anomaly Detection",
        "dimension": "Heavy-Tail Suppression",
        "metric_name": "Autoencoder Recall at mu + 3*sigma",
        "unsw_nb15_value": "0.00% (0 / 583 flows detected; tau = 11.160063)",
        "cicids2017_value": "0.60% (11.67 / 1,948 flows detected; tau = 0.088647)",
        "scientific_finding": "Both datasets replicate the anomaly suppression phenomenon: heavy-tailed benign reconstruction errors decouple Chebyshev parametric thresholds from the zero-day manifold.",
        "source_artifact": "zero_day_evaluation_summary.json / h3_h4_statistical_tests.json",
        "manuscript_section": "Section 4.3 / Table 3"
    },
    {
        "category": "Unsupervised Anomaly Detection",
        "dimension": "Alternative Estimators",
        "metric_name": "Isolation Forest Recall at mu + 3*sigma",
        "unsw_nb15_value": "0.00% (0 / 583 flows detected)",
        "cicids2017_value": "1.98% (38.67 / 1,948 flows detected)",
        "scientific_finding": "Tree-based unsupervised anomaly detection mirrors Autoencoder suppression, proving suppression is manifold-driven rather than architecture-specific.",
        "source_artifact": "zero_day_evaluation_summary.json / EXP_IF_V1",
        "manuscript_section": "Section 4.3 / Table 3"
    },

    # 5. Hybrid Logical-OR Fusion
    {
        "category": "Hybrid Fusion",
        "dimension": "Operational Utility",
        "metric_name": "Incremental Attack Rescues (Q3)",
        "unsw_nb15_value": "0 flows rescued (Q3 = 0, exact binomial p = 1.000)",
        "cicids2017_value": "37.67 flows rescued (Q3 = 37.67, McNemar p = 0.00073)",
        "scientific_finding": "Inclusive OR fusion on CIC marginally rescues 1.9% of Bot attacks but incurs +49.33 false alarms on benign control, yielding net operational detriment.",
        "source_artifact": "s23_c06_hybrid_marker.json / h3_h4_statistical_tests.json",
        "manuscript_section": "Section 4.4 / Table 4"
    },
    {
        "category": "Hybrid Fusion",
        "dimension": "Operational Cost",
        "metric_name": "Incremental False Alarms",
        "unsw_nb15_value": "+13 additional false positives on benign test set",
        "cicids2017_value": "+49.33 additional false positives on evaluation control",
        "scientific_finding": "Across both environments, naive logical-OR fusion strictly degrades alert precision and increases SOC analyst burden.",
        "source_artifact": "s23_c06_hybrid_marker.json / research_paper.md",
        "manuscript_section": "Section 4.4 / Figure 3"
    },

    # 6. Shortcut Ablation & Hypotheses
    {
        "category": "Scientific Hypotheses",
        "dimension": "Attribution Shift",
        "metric_name": "H1 Verdict: Error Independence",
        "unsw_nb15_value": "Rejected (Shortcuts significantly alter error distributions)",
        "cicids2017_value": "REJECTED (McNemar p < 1e-15; 3/3 seeds rejected)",
        "scientific_finding": "Removing frozen shortcuts forces statistical attribution reallocation across genuine network behavioral features.",
        "source_artifact": "s19_ablation_evaluation.json / s20_shap_ablation_shift.json",
        "manuscript_section": "Section 5.1 / Figure 4"
    },
    {
        "category": "Scientific Hypotheses",
        "dimension": "Model Capacity",
        "metric_name": "H2 Verdict: TOST Equivalence (|Delta Macro-F1| < 0.01)",
        "unsw_nb15_value": "Accepted (Shortcuts contribute negligible genuine discrimination)",
        "cicids2017_value": "ACCEPTED (Mean Delta = 0.00148; TOST p < 0.001)",
        "scientific_finding": "Random Forest retains near-perfect discrimination without shortcuts, proving shortcuts inflate perceived confidence without aiding genuine capacity.",
        "source_artifact": "s19_ablation_evaluation.json / EXP_TOST_V1",
        "manuscript_section": "Section 5.1 / Table 2"
    },

    # 7. Deep Tabular Transformer Architecture
    {
        "category": "Modern Architectures",
        "dimension": "Transformer Generalization",
        "metric_name": "FT-Transformer Zero-Day Recall",
        "unsw_nb15_value": "100.0% (583 / 583 flows detected on Backdoor)",
        "cicids2017_value": "0.00% (0 / 1,948 flows detected on Bot)",
        "scientific_finding": "Modern self-attention tabular architectures exhibit the identical dichotomy: perfect generalization on UNSW Backdoor, complete blindness on CIC Bot.",
        "source_artifact": "s21_ft_transformer_cic_results.json / s22_ft_transformer_unsw_results.json",
        "manuscript_section": "Section 5.2 / Table 5"
    },
    {
        "category": "Modern Architectures",
        "dimension": "Tabular Accuracy",
        "metric_name": "FT-Transformer DEV_TEST Macro-F1",
        "unsw_nb15_value": "0.8488 (vs 0.8930 for Stacking)",
        "cicids2017_value": "0.9864 (vs 0.9986 for Stacking)",
        "scientific_finding": "Tree ensembles consistently outperform or match deep self-attention tabular architectures on both benchmark datasets with lower compute overhead.",
        "source_artifact": "s21_ft_transformer_cic_results.json / s22_ft_transformer_unsw_results.json",
        "manuscript_section": "Section 5.2 / Table 5"
    },

    # 8. Matched-FPR Fair Benchmark
    {
        "category": "Matched-FPR Analysis",
        "dimension": "Fair Comparison",
        "metric_name": "Zero-Day Recall at FPR = 10^-3 (1/1000 false alarms)",
        "unsw_nb15_value": "Stacking: 77.02%; AE: 0.69%; IF: 0.00%",
        "cicids2017_value": "Stacking: 0.00%; AE: 0.00%; IF: 0.00%",
        "scientific_finding": "When benign false alarms are constrained to operational limits (FPR <= 0.001), all detectors experience catastrophic failure on the CIC Bot manifold.",
        "source_artifact": "s23_matched_fpr_summary.json / EXP_MATCHED_FPR_V1",
        "manuscript_section": "Section 5.3 / Figure 1"
    },

    # 9. Deployment Benchmarking
    {
        "category": "Operational Deployment",
        "dimension": "Inference Latency",
        "metric_name": "Median Latency per 1,000 Flows (CPU / Host)",
        "unsw_nb15_value": "DT: 0.4ms; RF: 145ms; Stacking: 180ms",
        "cicids2017_value": "DT: 0.59ms; RF: 172.82ms; Stacking: 236.43ms",
        "scientific_finding": "Single decision trees provide microsecond-scale real-time line-rate processing, whereas ensemble and deep models require batching.",
        "source_artifact": "s24_deployment_benchmark.csv",
        "manuscript_section": "Section 5.4 / Table 6"
    },
]

fieldnames = [
    "category", "dimension", "metric_name",
    "unsw_nb15_value", "cicids2017_value",
    "scientific_finding", "source_artifact", "manuscript_section"
]

with open(OUT_FILE, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Successfully generated final summary CSV: {OUT_FILE} ({len(rows)} comparative dimensions)")
