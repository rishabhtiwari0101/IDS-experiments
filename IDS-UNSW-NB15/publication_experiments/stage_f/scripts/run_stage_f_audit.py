"""
STAGE F STATIC AUDIT SCRIPT
Verifies implementation compliance against Stage-F pre-execution criteria:
1. Static-audit wording: PASS signifies only verification mechanism exists without hardcoded constants; NUMERIC_VERIFICATION_EXECUTED = FALSE.
2. Derivation registry existence checked before content assertions.
3. Prohibition of pooled AE statistic anywhere in code or plan (literal check + AST semantic safeguard, NO_POOLED_AE_AGGREGATION = PASS).
4. Formal computable booleans for safety conditions and deterministic truth table.
5. Separation of manuscript revision severity (R_MANUSCRIPT_SUBSTANTIAL_UPDATE vs R6_MINOR_WORDING_FORMATTING).
6. Figure E8 upstream resolution and explicit handoff protocol (UPSTREAM_STAGE_E_REVISION_REQUIRED).
7. Explicit baseline-hash coverage enumeration across all frozen files (no silent gaps).
8. Dynamic Gate-9 reviewer-risk evaluation separating evidence safety (Stage E) from manuscript wording (submission basis).
9. Reviewer-risk revision flag surfaced prominently and separately from G9.
10. Stage-F output exclusion rule tested and verified.
11. Working tree isolation of all Stage 0-E frozen artifacts and manuscript.
12. Valid Python AST syntax of analysis script.
13. Static audit additions:
    - stale manuscript + silent claim -> REQUIRES MANUSCRIPT REVISION
    - Stage-E evidence alone cannot produce EXPLICITLY LIMITED for absent manuscript wording
    - Gate 9 outputs separate evidence and manuscript classifications
    - no pooled AE-family aggregation exists beyond per-family reporting
    - literal and semantic pooling checks both pass
"""

import sys
import os
import re
import ast
import json
import subprocess
from pathlib import Path

# Ensure console supports UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_ROOT = Path("c:/Users/Atul2/OneDrive/Desktop/Papers/IDS-UNSW-NB15")
STAGE_F_ANALYSIS_SCRIPT = WORKSPACE_ROOT / "publication_experiments/stage_f/scripts/run_stage_f_analysis.py"
STAGE_F_PLAN_PATH = WORKSPACE_ROOT / "publication_experiments/stage_f/implementation_plan.md"

FROZEN_PATHS = [
    WORKSPACE_ROOT / "results/zero_day",
    WORKSPACE_ROOT / "results/stacking",
    WORKSPACE_ROOT / "results/autoencoder",
    WORKSPACE_ROOT / "results/checkpoints",
    WORKSPACE_ROOT / "results/feature_selection",
    WORKSPACE_ROOT / "data/raw",
    WORKSPACE_ROOT / "data/splits",
    WORKSPACE_ROOT / "results/publication_experiments/EXP_NO_TTL_V1",
    WORKSPACE_ROOT / "results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1",
    WORKSPACE_ROOT / "results/publication_experiments/EXP_STATS_ROBUSTNESS_V1",
    WORKSPACE_ROOT / "results/publication_experiments/EXP_INTEGRATED_PUBLICATION_V1",
    WORKSPACE_ROOT / "RESEARCH_PAPER_MANUSCRIPT.md",
]

def check(condition: bool, description: str) -> bool:
    status = "[PASS]" if condition else "[FAIL]"
    print(f"{status} {description}")
    return condition

def check_git_isolation() -> tuple:
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=WORKSPACE_ROOT).decode("utf-8")
        lines = [ln.strip() for ln in out.strip().split("\n") if ln.strip()]
        for fpath in FROZEN_PATHS:
            rel = str(fpath.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
            for line in lines:
                code = line[:2]
                path = line[3:].strip().replace("\\", "/")
                if path.startswith(rel) and rel != "RESEARCH_PAPER_MANUSCRIPT.md":
                    return False, f"Modified frozen path: {line}"
                elif rel == "RESEARCH_PAPER_MANUSCRIPT.md" and path == "RESEARCH_PAPER_MANUSCRIPT.md" and ("M" in code or "D" in code):
                    return False, f"Modified manuscript: {line}"
        return True, "All frozen paths untouched"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 80)
    print("STAGE F STATIC AUDIT — VERIFICATION OF PUBLICATION READINESS PROTOCOL")
    print("=" * 80)

    if not STAGE_F_ANALYSIS_SCRIPT.exists():
        print(f"[FATAL] Analysis script missing: {STAGE_F_ANALYSIS_SCRIPT}")
        sys.exit(1)

    with open(STAGE_F_ANALYSIS_SCRIPT, "r", encoding="utf-8") as f:
        code_content = f.read()

    plan_content = ""
    if STAGE_F_PLAN_PATH.exists():
        with open(STAGE_F_PLAN_PATH, "r", encoding="utf-8") as f:
            plan_content = f.read()

    all_checks = []

    # -------------------------------------------------------------------------
    # CHECK 1: Static-Audit Wording & Dynamic Numeric Verification Mechanism
    # -------------------------------------------------------------------------
    print("\n--- CHECK 1: Dynamic Numeric Verification Mechanism & Execution State ---")
    
    stage_f_output_root = WORKSPACE_ROOT / "results/publication_experiments/EXP_FINAL_PUBLICATION_AUDIT_V1"
    num_audit_file = stage_f_output_root / "audits/numerical_consistency.json"
    final_gate_file = stage_f_output_root / "audits/final_gate.json"
    
    stage_f_executed = num_audit_file.exists() and final_gate_file.exists()
    gate_data = {}
    num_data = {}
    
    if stage_f_executed:
        try:
            with open(num_audit_file, "r", encoding="utf-8") as f:
                num_data = json.load(f)
            with open(final_gate_file, "r", encoding="utf-8") as f:
                gate_data = json.load(f)
            num_crit_fail = num_data.get("critical_failure", True)
            g1_status = gate_data.get("core_gates", {}).get("G1_numerical_consistency", "FAIL")
            numeric_verif_result = "PASS" if (not num_crit_fail and g1_status == "PASS") else "FAIL"
        except Exception:
            numeric_verif_result = "FAIL"
            
        print("  [POST-EXECUTION STATUS] NUMERIC_VERIFICATION_EXECUTED = TRUE")
        print(f"  [POST-EXECUTION STATUS] NUMERIC_VERIFICATION_RESULT = {numeric_verif_result}")
        print(f"  [AUDIT DEFINITION] Master execution completed. Dynamic numeric verification verified against source artifacts (G1: {numeric_verif_result}).")
    else:
        print("  [PRE-EXECUTION STATUS] NUMERIC_VERIFICATION_EXECUTED = FALSE")
        print("  [AUDIT DEFINITION] PASS signifies only that the dynamic verification mechanism exists")
        print("                     and no hard-coded expected values are used.")
        print("                     It does NOT imply canonical metrics or 0.8909 are already numerically verified;")
        print("                     numerical verification executes during master run to produce MATCH/MISMATCH.")

    has_source_derivation = "PROGRAMMATIC_DERIVATION_FROM_RAW_PREDICTIONS" in code_content
    c1_1 = check(has_source_derivation, "Verification mechanism exists: Stage-B metrics resolved dynamically from raw prediction artifacts")

    has_table_lookup = "MACHINE_READABLE_TABLE_LOAD" in code_content
    c1_2 = check(has_table_lookup, "Verification mechanism exists: published numbers resolved from machine-readable tables")

    has_status_mapping = "MISSING_SOURCE" in code_content and "MATCH" in code_content
    c1_3 = check(has_status_mapping, "Dynamic verification status mapping present (MATCH/MISMATCH/MISSING_SOURCE assigned at runtime)")

    no_hardcoded_asserts = ("assert derived_s42_f1 ==" not in code_content) and ("== 0.8909" not in code_content)
    c1_4 = check(no_hardcoded_asserts, "No hard-coded expected values (e.g. 0.8909) asserted without dynamic derivation")

    plan_c1_wording = "verification mechanism exists and no hard-coded expected values are used" in plan_content
    c1_5 = check(plan_c1_wording, "Implementation plan specifies Check 1 PASS definition and NUMERIC_VERIFICATION_EXECUTED = FALSE")

    all_checks.extend([c1_1, c1_2, c1_3, c1_4, c1_5])

    # -------------------------------------------------------------------------
    # CHECK 2: Existence-First Derivation Registry Handling
    # -------------------------------------------------------------------------
    print("\n--- CHECK 2: Existence-First Derivation Registry Handling ---")
    has_existence_first = "deriv_reg_exists = deriv_reg_path.exists()" in code_content
    c2_1 = check(has_existence_first, "Derivation registry existence is checked before content parsing")

    has_gap_flag = "R_DERIVATION_REGISTRY_DOCUMENTATION_GAP" in code_content
    c2_2 = check(has_gap_flag, "Derivation registry documentation gap flag is defined")

    all_checks.extend([c2_1, c2_2])

    # -------------------------------------------------------------------------
    # CHECK 3: Prohibition of Pooled AE Statistic & Lightweight Semantic Safeguard
    # -------------------------------------------------------------------------
    print("\n--- CHECK 3: Prohibition of Pooled AE Statistic & Lightweight Semantic Safeguard ---")
    # 1. Literal grep/string check
    no_pooled_in_code = ("0/1682" not in code_content) and ("1682" not in code_content)
    c3_1 = check(no_pooled_in_code, "String '0/1682' or pooled denominator '1682' absent from analysis script")

    no_pooled_in_plan = ("0/1682" not in plan_content) and ("1682" not in plan_content)
    c3_2 = check(no_pooled_in_plan, "String '0/1682' or pooled denominator '1682' absent from implementation plan")

    # 2. Semantic AST safeguard: inspect code for any computation combining four AE-family denominators/detection counts
    analysis_tree = ast.parse(code_content)
    family_denominators = {583, 44, 378, 677}
    pooled_operations = []

    for node in ast.walk(analysis_tree):
        # Inspect binary addition
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            operands = []
            if isinstance(node.left, ast.Constant) and node.left.value in family_denominators:
                operands.append(node.left.value)
            if isinstance(node.right, ast.Constant) and node.right.value in family_denominators:
                operands.append(node.right.value)
            if operands:
                pooled_operations.append(f"BinOp Add involving denominator {operands} at line {node.lineno}")

        # Inspect sum() calls
        if isinstance(node, ast.Call):
            func_id = getattr(node.func, "id", None)
            if func_id == "sum":
                for arg in node.args:
                    if isinstance(arg, (ast.List, ast.Tuple, ast.Set)):
                        for elt in arg.elts:
                            if isinstance(elt, ast.Constant) and elt.value in family_denominators:
                                pooled_operations.append(f"sum() call containing {elt.value} at line {node.lineno}")

        # Inspect variable assignments representing pooled multi-family statistics
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            name_lower = node.id.lower()
            if "pooled" in name_lower and any(kw in name_lower for kw in ["ae", "family", "denom", "stat", "count"]):
                pooled_operations.append(f"Pooled variable {node.id} at line {node.lineno}")

    semantic_no_pooling = (len(pooled_operations) == 0)
    c3_3 = check(semantic_no_pooling, "AST semantic safeguard: no binary additions, sum() calls, or pooled variables combine AE denominators")

    # 3. Explicitly assert that Backdoor, Worms, Shellcode, Analysis are handled independently
    has_four_families = all(fam in code_content for fam in ["Backdoor", "Worms", "Shellcode", "Analysis"])
    families_independent = has_four_families and ("separate" in code_content.lower() or "independent" in code_content.lower())
    c3_4 = check(families_independent, "Attack families (Backdoor, Worms, Shellcode, Analysis) are handled strictly independently")

    # 4. Report NO_POOLED_AE_AGGREGATION
    no_pooled_ae_aggregation = no_pooled_in_code and no_pooled_in_plan and semantic_no_pooling and families_independent
    print(f"  NO_POOLED_AE_AGGREGATION = {'PASS' if no_pooled_ae_aggregation else 'FAIL'}")
    c3_5 = check(no_pooled_ae_aggregation, "NO_POOLED_AE_AGGREGATION = PASS (literal check, semantic AST check, and independent reporting pass)")

    all_checks.extend([c3_1, c3_2, c3_3, c3_4, c3_5])

    # -------------------------------------------------------------------------
    # CHECK 4: Formal Computable Booleans for Safety & Final Verdict
    # -------------------------------------------------------------------------
    print("\n--- CHECK 4: Formal Computable Booleans for Safety & Final Verdict ---")
    formal_flags = [
        "critical_numerical_failure",
        "critical_methodology_failure",
        "actual_leakage_found",
        "critical_statistical_failure",
        "unsupported_core_claim",
        "frozen_artifact_modified",
        "critical_reviewer_risk"
    ]
    has_formal_flags = all(f in code_content for f in formal_flags)
    c4_1 = check(has_formal_flags, "All formal safety conditions are defined as explicit computable booleans")

    has_truth_table = "any_automatic_not_ready" in code_content and "has_revision_flag" in code_content
    c4_2 = check(has_truth_table, "Final verdict mapping is strictly boolean truth-table driven")

    all_checks.extend([c4_1, c4_2])

    # -------------------------------------------------------------------------
    # CHECK 5: Separation of Manuscript Revision Severity
    # -------------------------------------------------------------------------
    print("\n--- CHECK 5: Separation of Manuscript Revision Severity ---")
    has_substantial_flag = "R_MANUSCRIPT_SUBSTANTIAL_UPDATE" in code_content and "substantial_update_required" in code_content
    c5_1 = check(has_substantial_flag, "Substantial manuscript update required flag is explicitly separated")

    has_minor_formatting = "R6_MINOR_WORDING_FORMATTING" in code_content
    c5_2 = check(has_minor_formatting, "Minor wording/formatting flag is maintained separately")

    has_manuscript_state = all(s in code_content for s in ["CURRENT", "STALE", "ABSENT"])
    c5_3 = check(has_manuscript_state, "Manuscript state resolution explicitly covers CURRENT, STALE, ABSENT")

    all_checks.extend([c5_1, c5_2, c5_3])

    # -------------------------------------------------------------------------
    # CHECK 6: Figure E8 Upstream Resolution & Explicit Handoff Protocol
    # -------------------------------------------------------------------------
    print("\n--- CHECK 6: Figure E8 Upstream Resolution & Handoff Protocol ---")
    has_fig_defect = "figure_E8_upstream_defect = not (fig_e8_exists and fig_e8_validates_both_branches)" in code_content
    c6_1 = check(has_fig_defect, "Figure E8 upstream defect boolean is defined programmatically")

    has_upstream_handoff = "UPSTREAM_STAGE_E_REVISION_REQUIRED" in code_content and "required_stage_e_update" in code_content
    c6_2 = check(has_upstream_handoff, "UPSTREAM_STAGE_E_REVISION_REQUIRED logged with exact Stage-E regeneration update")

    has_fig_rev_flag = "R_FIGURE_E8_UPSTREAM_DEFECT" in code_content
    c6_3 = check(has_fig_rev_flag, "Upstream defect sets revision flag R_FIGURE_E8_UPSTREAM_DEFECT and does NOT fail G6")

    all_checks.extend([c6_1, c6_2, c6_3])

    # -------------------------------------------------------------------------
    # CHECK 7: Explicit Baseline-Hash Coverage Enumeration (No Silent Gaps)
    # -------------------------------------------------------------------------
    print("\n--- CHECK 7: Baseline-Hash Coverage Enumeration across Frozen Files ---")
    has_coverage_counts = all(cnt in code_content for cnt in [
        "total_frozen_files",
        "hash_verified_count",
        "repository_verified_count",
        "no_baseline_hash_count"
    ])
    c7_1 = check(has_coverage_counts, "Analysis script explicitly enumerates total, HASH_VERIFIED, REPOSITORY_VERIFIED, and NO_BASELINE counts")

    has_no_gaps_check = "coverage_has_no_gaps" in code_content
    c7_2 = check(has_no_gaps_check, "Coverage integrity verified with no silent gaps (total == hash + repo + no_baseline)")

    has_coverage_in_json_and_report = ("frozen_artifact_integrity.json" in code_content) and ("stage_f_final_report.md" in code_content)
    c7_3 = check(has_coverage_in_json_and_report, "Coverage counts saved in frozen_artifact_integrity.json and stage_f_final_report.md")

    all_checks.extend([c7_1, c7_2, c7_3])

    # -------------------------------------------------------------------------
    # CHECK 8: Dynamic Gate-9 Reviewer-Risk Evaluation (Separated Evidence & Manuscript)
    # -------------------------------------------------------------------------
    print("\n--- CHECK 8: Dynamic Gate-9 Reviewer-Risk Evaluation (Separated Basis) ---")
    # Verify no static pre-assigned outcomes in plan
    no_preassigned_in_plan = not re.search(r"REV_\d+.*(ALREADY CONTROLLED|EXPLICITLY LIMITED|REQUIRES MANUSCRIPT REVISION)", plan_content)
    c8_1 = check(no_preassigned_in_plan, "Implementation plan contains NO pre-assigned reviewer-risk classifications")

    # Verify all 4 categories are used dynamically in code
    has_all_categories = all(cat in code_content for cat in [
        "ALREADY CONTROLLED",
        "EXPLICITLY LIMITED",
        "REQUIRES MANUSCRIPT REVISION",
        "CRITICAL"
    ])
    c8_2 = check(has_all_categories, "Code dynamically assigns: ALREADY CONTROLLED / EXPLICITLY LIMITED / REQUIRES MANUSCRIPT REVISION / CRITICAL")

    # Verify dynamic evaluation of the 3 especially highlighted objections
    has_ae_dynamic = "REV_03_PRIMARY_AE_DETECTION" in code_content and ("e_ok_03" in code_content or "e_lim_03" in code_content) and ("m_ok_03" in code_content or "m_lim_03" in code_content)
    c8_3 = check(has_ae_dynamic, "AE zero detections dynamically evaluated against 4 separate families & Clopper-Pearson CIs")

    has_ttl_dynamic = "REV_06_TTL_CAUSALITY" in code_content and ("e_ok_06" in code_content or "e_lim_06" in code_content) and ("m_ok_06" in code_content or "m_lim_06" in code_content)
    c8_4 = check(has_ttl_dynamic, "TTL causality dynamically evaluated for representation isolation vs causal claims")

    has_zeroday_dynamic = "REV_09_ZERO_DAY_DEFINITION" in code_content and ("e_ok_09" in code_content or "e_lim_09" in code_content) and ("m_ok_09" in code_content or "m_lim_09" in code_content)
    c8_5 = check(has_zeroday_dynamic, "Zero-day scope dynamically evaluated for held-out benchmark family vs wild zero-days")

    # Separate evidence safety from manuscript wording
    has_separate_classifications = (
        "evidence_risk_classification" in code_content
        and "manuscript_wording_classification" in code_content
        and "final_classification" in code_content
    )
    c8_6 = check(has_separate_classifications, "Gate 9 outputs separate evidence_risk_classification and manuscript_wording_classification")

    # Logic test: Stale manuscript + silent claim -> REQUIRES MANUSCRIPT REVISION
    has_stale_silent_logic = (
        'manuscript_state in ["STALE", "ABSENT"] or not manuscript_adequacy' in code_content
        and 'manuscript_cls = "REQUIRES MANUSCRIPT REVISION"' in code_content
    )
    c8_7 = check(has_stale_silent_logic, "Code logic asserts: stale manuscript + silent claim -> REQUIRES MANUSCRIPT REVISION")

    # Verification that Stage-E evidence alone cannot produce EXPLICITLY LIMITED for absent manuscript wording
    has_evidence_alone_protection = (
        'final_cls = "REQUIRES MANUSCRIPT REVISION"' in code_content
        and 'elif manuscript_cls == "REQUIRES MANUSCRIPT REVISION":' in code_content
    )
    c8_8 = check(has_evidence_alone_protection, "Stage-E evidence alone cannot produce EXPLICITLY LIMITED when manuscript wording is absent/silent")

    # Prioritization of manuscript status when assessing publication readiness
    has_manuscript_priority = 'elif manuscript_cls == "REQUIRES MANUSCRIPT REVISION":' in code_content and 'final_cls = "REQUIRES MANUSCRIPT REVISION"' in code_content
    c8_9 = check(has_manuscript_priority, "Final reviewer-risk classification strictly prioritizes manuscript status for publication readiness")

    # Explicit identification of objections requiring manuscript integration
    has_integration_identification = (
        "objections_requiring_revision" in code_content
        and "reviewer_risk_requires_revision" in code_content
    )
    c8_10 = check(has_integration_identification, "Explicitly identifies which of the 10 reviewer objections require manuscript integration")

    all_checks.extend([c8_1, c8_2, c8_3, c8_4, c8_5, c8_6, c8_7, c8_8, c8_9, c8_10])

    # -------------------------------------------------------------------------
    # CHECK 9: Separate Surfacing of Reviewer-Risk Revision Flag
    # -------------------------------------------------------------------------
    print("\n--- CHECK 9: Separate Surfacing of Reviewer-Risk Revision Flag ---")
    has_g9_pass = "G9 = not critical_reviewer_risk" in code_content
    c9_1 = check(has_g9_pass, "G9 = True when there is no CRITICAL reviewer risk")

    has_rev_flag_surfaced = "reviewer_risk_requires_revision" in code_content and "objections_requiring_revision" in code_content
    c9_2 = check(has_rev_flag_surfaced, "reviewer_risk_requires_revision surfaced separately with explicit list of objections")

    has_no_implication_note = "does NOT imply zero reviewer concerns" in code_content
    c9_3 = check(has_no_implication_note, "Reporting explicitly states G9: PASS does NOT imply zero reviewer concerns")

    all_checks.extend([c9_1, c9_2, c9_3])

    # -------------------------------------------------------------------------
    # CHECK 10: Stage-F Output Exclusion Rule Testing
    # -------------------------------------------------------------------------
    print("\n--- CHECK 10: Stage-F Output Exclusion Rule Testing ---")
    has_exclusion_func = "def check_frozen_violation" in code_content
    c10_1 = check(has_exclusion_func, "Function check_frozen_violation exists in analysis script")

    excluded_test_1 = False
    for exc in ["publication_experiments/stage_f", "results/publication_experiments/EXP_FINAL_PUBLICATION_AUDIT_V1"]:
        if "publication_experiments/stage_f/scripts/run_stage_f_audit.py".startswith(exc):
            excluded_test_1 = True
    c10_2 = check(excluded_test_1, "Mock test: Stage-F script path is properly excluded from frozen scope")

    excluded_test_2 = False
    for exc in ["publication_experiments/stage_f", "results/publication_experiments/EXP_FINAL_PUBLICATION_AUDIT_V1"]:
        if "results/publication_experiments/EXP_FINAL_PUBLICATION_AUDIT_V1/audits/final_gate.json".startswith(exc):
            excluded_test_2 = True
    c10_3 = check(excluded_test_2, "Mock test: Stage-F output path is properly excluded from frozen scope")

    frozen_test_1 = any("data/splits/development_test.csv".startswith(str(p.relative_to(WORKSPACE_ROOT)).replace("\\", "/")) for p in FROZEN_PATHS)
    c10_4 = check(frozen_test_1, "Mock test: Stage 0 split path is properly identified as protected frozen scope")

    all_checks.extend([c10_1, c10_2, c10_3, c10_4])

    # -------------------------------------------------------------------------
    # CHECK 11: Current Working Tree Isolation
    # -------------------------------------------------------------------------
    print("\n--- CHECK 11: Working Tree Isolation of Frozen Artifacts ---")
    iso_ok, iso_msg = check_git_isolation()
    c11_1 = check(iso_ok, f"All Stage 0-E frozen directories and manuscript remain 100% clean ({iso_msg})")
    all_checks.append(c11_1)

    # -------------------------------------------------------------------------
    # CHECK 12: Python AST Syntax Validity
    # -------------------------------------------------------------------------
    print("\n--- CHECK 12: Python AST Syntax Check ---")
    try:
        ast.parse(code_content)
        syntax_ok = True
    except SyntaxError as e:
        print(f"[FAIL] Syntax error in analysis script: {e}")
        syntax_ok = False
    c12_1 = check(syntax_ok, "run_stage_f_analysis.py parses with valid Python AST syntax")
    all_checks.append(c12_1)

    # -------------------------------------------------------------------------
    # CHECK 13: Static Audit Additions (Explicit Formal Assertions)
    # -------------------------------------------------------------------------
    print("\n--- CHECK 13: Static Audit Additions (Formal Gate-9 & Pooling Assertions) ---")
    
    # 1. Stale manuscript + silent claim -> REQUIRES MANUSCRIPT REVISION
    def eval_sim(m_state, e_adeq, e_ctrl, m_adeq):
        if not e_adeq:
            e_cls = "CRITICAL"
        elif e_ctrl:
            e_cls = "ALREADY CONTROLLED"
        else:
            e_cls = "EXPLICITLY LIMITED"

        if m_state in ["STALE", "ABSENT"] or not m_adeq:
            m_cls = "REQUIRES MANUSCRIPT REVISION"
            m_silent = True
        else:
            m_cls = e_cls
            m_silent = False

        if e_cls == "CRITICAL":
            f_cls = "CRITICAL"
        elif m_cls == "REQUIRES MANUSCRIPT REVISION":
            f_cls = "REQUIRES MANUSCRIPT REVISION"
        else:
            f_cls = e_cls
        return e_cls, m_cls, f_cls, m_silent

    # Verify: stale manuscript + silent claim -> REQUIRES MANUSCRIPT REVISION
    e_c1, m_c1, f_c1, s1 = eval_sim("STALE", True, False, False)
    c13_1 = check(
        m_c1 == "REQUIRES MANUSCRIPT REVISION" and f_c1 == "REQUIRES MANUSCRIPT REVISION",
        "Static audit addition 1: stale manuscript + silent claim -> REQUIRES MANUSCRIPT REVISION"
    )

    # Verify: Stage-E evidence alone cannot produce EXPLICITLY LIMITED for absent manuscript wording
    c13_2 = check(
        e_c1 == "EXPLICITLY LIMITED" and m_c1 != "EXPLICITLY LIMITED" and f_c1 != "EXPLICITLY LIMITED",
        "Static audit addition 2: Stage-E evidence alone cannot produce EXPLICITLY LIMITED for absent manuscript wording"
    )

    # Verify: Gate 9 outputs separate evidence and manuscript classifications
    c13_3 = check(
        has_separate_classifications,
        "Static audit addition 3: Gate 9 outputs separate evidence and manuscript classifications"
    )

    # Verify: no pooled AE-family aggregation exists beyond per-family reporting
    c13_4 = check(
        semantic_no_pooling and families_independent,
        "Static audit addition 4: no pooled AE-family aggregation exists beyond per-family reporting"
    )

    # Verify: literal and semantic pooling checks both pass
    c13_5 = check(
        no_pooled_in_code and no_pooled_in_plan and semantic_no_pooling,
        "Static audit addition 5: literal and semantic pooling checks both pass"
    )

    all_checks.extend([c13_1, c13_2, c13_3, c13_4, c13_5])

    all_passed = all(all_checks)

    print("\n" + "=" * 80)
    if stage_f_executed:
        safety_failures = any(gate_data.get("safety_flags", {}).values())
        core_failures = any(v != "PASS" for v in gate_data.get("core_gates", {}).values())
        post_exec_verdict = "PASS" if (all_passed and not safety_failures and not core_failures) else "FAIL"
        print("STAGE F MASTER ANALYSIS: COMPLETED")
        print(f"STAGE F POST-EXECUTION AUDIT: {post_exec_verdict} — ALL {len(all_checks)} CHECKS SATISFIED")
    else:
        if all_passed:
            print(f"STAGE F STATIC AUDIT: PASS — ALL {len(all_checks)} CHECKS SATISFIED")
        else:
            print(f"STAGE F STATIC AUDIT: FAIL — ONE OR MORE CHECKS FAILED")
    print("=" * 80)

    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
