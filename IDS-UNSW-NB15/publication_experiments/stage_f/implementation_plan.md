# Stage F — Final Research & Publication Readiness Audit Implementation Plan

## 1. Executive Summary & Role
As senior research scientist, statistical reviewer, reproducibility auditor, and journal reviewer for the UNSW-NB15 Intrusion Detection System publication project, this implementation plan establishes the protocol for **Stage F: Final Research & Publication Readiness Audit**.

Stage F is the **final read-only publication-readiness audit** before manuscript submission. It rigorously evaluates the entire chain of evidence spanning:
- **Canonical Baselines**: `EXP_ZERODAY_V1`, `EXP_OOF_STACK_V1`, `EXP_AE_V1` (Seed 42 historical baseline)
- **Stage B**: Controlled No-TTL feature ablation (`EXP_NO_TTL_V1`) across seeds 42, 123, 2024
- **Stage C**: Benign-only Autoencoder evaluation (`EXP_AE_UNSEEN_FAMILY_V1`) across seeds 42, 123, 2024 against 4 AE-unseen attack families
- **Stage D**: Inferential statistical & robustness layer (`EXP_STATS_ROBUSTNESS_V1`)
- **Stage E**: Integrated publication evidence & comparative analysis (`EXP_INTEGRATED_PUBLICATION_V1`)
- **Manuscript Target**: `RESEARCH_PAPER_MANUSCRIPT.md`

Stage F is strictly an **audit-only, read-only stage**. It will NOT train, retrain, refit, or recalibrate any model, modify any split or dataset, alter canonical or Stage B–E artifacts, or edit the manuscript automatically.

All Stage-F code and output artifacts are strictly isolated to:
- Scripts & Configs: `publication_experiments/stage_f/`
- Output Directory: `results/publication_experiments/EXP_FINAL_PUBLICATION_AUDIT_V1/`
- Walkthrough: `publication_experiments/stage_f/walkthrough.md`

---

## 2. Manuscript State Resolution & Severity Separation

### Manuscript Audit Target
Target manuscript: `RESEARCH_PAPER_MANUSCRIPT.md` (verified on disk, 353 lines).

### State Resolution: `STALE`
- `RESEARCH_PAPER_MANUSCRIPT.md` currently documents only the historical canonical baseline experiments (75 features, Seed 42, canonical Backdoor 0/583 and Stacking C01).
- It does NOT yet incorporate the completed Stage B–E publication extension evidence (72-feature No-TTL ablation across 3 seeds, 4 AE-unseen families, exact inferential tests, 60-cell threshold sensitivity matrix, and integrated publication Tables E1–E7 / Figures E1–E8).
- Therefore, the manuscript is formally classified as **`STALE`**.

### Separation of Revision Severity
We explicitly distinguish substantial content gaps from cosmetic wording repairs:
- **Substantial Manuscript Update Required**:
  `R_MANUSCRIPT_SUBSTANTIAL_UPDATE = TRUE`
  `SUBSTANTIAL_MANUSCRIPT_UPDATE_REQUIRED = TRUE`
  *Meaning*: The empirical evidence across Stages B–E is complete, validated, and audit-ready, but the physical manuscript text requires substantial content integration in Stage G prior to journal submission.
- **Minor Wording & Formatting Repairs**:
  `R6_MINOR_WORDING_FORMATTING = FALSE` (or set as appropriate for isolated phrasing cleanups).
- **Readiness Impact**:
  Per the deterministic truth table, `R_MANUSCRIPT_SUBSTANTIAL_UPDATE = TRUE` sets the formal verdict to **`READY WITH MINOR REVISIONS`** (capping it from `READY FOR SUBMISSION`), while explicitly reporting `SUBSTANTIAL_MANUSCRIPT_UPDATE_REQUIRED = TRUE` in the executive summary and final gate.

---

## 3. Authoritative Population Resolution (Verified from Disk)

No population count is hardcoded or assumed merely from prose. The populations are verified programmatically from disk:
1. `data/splits/development_test.csv`:
   - Path: `C:\Users\Atul2\OneDrive\Desktop\Papers\IDS-UNSW-NB15\data\splits\development_test.csv`
   - SHA-256: `04725e85732ab2fc6d9eaaa6105418b22b083b5c651067e7b0785464f414e508`
   - Verified Row Count: $N = 81,749$
   - Verified Composition: $44,749$ attack flows and $37,000$ benign flows
2. `data/splits/protected_unseen_attack.csv`:
   - Path: `C:\Users\Atul2\OneDrive\Desktop\Papers\IDS-UNSW-NB15\data\splits\protected_unseen_attack.csv`
   - SHA-256: `6ffd23479b575e438ad90678268f40f674a663c2b9507aaf65089623397a9d91`
   - Verified Row Count: $N = 583$ (all Backdoor attack flows)

---

## 4. 9-Gate Audit Architecture

### Gate 1: Numerical Consistency (`G1`)
- **Dynamic Resolution & Pre-Execution Status**:
  - In static audit, Check 1 `PASS` means ONLY:
    "verification mechanism exists and no hard-coded expected values are used."
  - It does NOT imply canonical metrics or Stage-B 0.8909 are already numerically verified.
  - Explicit pre-execution status:
    `NUMERIC_VERIFICATION_EXECUTED = FALSE`
    until master execution runs and produces `MATCH/MISMATCH` against underlying raw prediction artifacts.
  - During master execution, every numeric value is resolved dynamically from its underlying machine-readable source artifact (e.g. `results/zero_day/EXP_ZERODAY_V1/`, `results/publication_experiments/EXP_NO_TTL_V1/`, `EXP_STATS_ROBUSTNESS_V1/`, `EXP_INTEGRATED_PUBLICATION_V1/`).
  - For each number, logs: `value`, `source_artifact`, `source_field`, `verification_method`, and `status` (`MATCH`, `MISMATCH`, `MISSING_SOURCE`).
  - If any core metric fails to match its machine-readable source or if a required source artifact is missing, sets `critical_numerical_failure = TRUE`.
  - Gate evaluation: $G_1 = \mathbf{not}\ critical\_numerical\_failure$.

### Gate 2: Methodology Consistency (`G2`)
- Verifies adherence to preregistered research protocol:
  - Strict TRAIN / VALIDATION / DEV TEST / PROTECTED BACKDOOR partitioning.
  - TRAIN-only preprocessing and MI feature selection fitting.
  - Canonical 75-feature representation vs controlled 72-feature No-TTL ablation.
  - 5-fold OOF meta-learner stacking.
  - Seed-42 canonical baseline ($N=1$ seed; anti-fabrication check).
  - Three-seed Stage-B replication (seeds 42, 123, 2024; descriptive only).
  - Benign-only Autoencoder training with fit/monitor separation.
  - Primary threshold calibration on benign validation (`mean+3σ`, ddof=0).
- If any methodological contradiction is detected, sets `critical_methodology_failure = TRUE`.
- Gate evaluation: $G_2 = \mathbf{not}\ critical\_methodology\_failure$.

### Gate 3: Leakage & Data Integrity (`G3`)
- **Actual Empirical Leakage Test (7A)**:
  - Verifies zero data contamination:
    - Protected Backdoor never present in supervised or AE training sets.
    - Zero overlap between AE-fit and AE-monitor subsets.
    - Scalers and encoders fit strictly on benign training data.
    - No post-hoc threshold tuning against test or protected data.
    - No duplicate protected rows or invalid row alignment.
  - If empirical leakage is detected: sets `actual_leakage_found = TRUE`.
- **Documentation Evidence Test (7B)**:
  - If leakage prevention claims in manuscript require additional explicit repository citations or expanded descriptions: sets `leakage_documentation_gap = TRUE` (flag $R_{leakage\_doc}$).
- Gate evaluation: $G_3 = \mathbf{not}\ actual\_leakage\_found$.

### Gate 4: Statistical Validity (`G4`)
- **Heterogeneous Metric Operational Rule**:
  - Requires: `same_task`, `same_population`, `same_metric`, `same_direction/interpretation`.
  - Heterogeneous metrics (e.g. AE FPR vs Classifier Macro-F1) must NEVER be ranked, averaged, or synthesized into a common score.
- Verifies exact paired McNemar contingency tables ($A, B, C, D$) on protected Backdoor ($N=583$).
- Verifies Holm step-down multiple testing correction across exactly 5 supervised models ($m=5$).
- Verifies exact Clopper-Pearson binomial confidence intervals.
- Verifies structural degeneracy handling: RF ($B=0, C=0$) and Canonical AE vs New AE ($B=0, C=0$) dynamically assigned `STRUCTURALLY_NON_INFORMATIVE`; equivalence is NOT claimed.
- If statistical violations occur, sets `critical_statistical_failure = TRUE`.
- Gate evaluation: $G_4 = \mathbf{not}\ critical\_statistical\_failure$.

### Gate 5: Claims Safety (`G5`) & Strengthened Check 3
- Audits all 5 core publication claims (Claims A through E).
- **Mandatory AE Wording Constraint**:
  - Observed zero detections must remain strictly scoped to evaluated samples, thresholds, and attack families.
  - Must NEVER imply true sensitivity is 0% or that the AE is incapable of anomaly detection in general.
  - **No Pooled Statistic & Semantic Safeguard (Strengthened Check 3)**:
    - Retains literal check: Any pooled multi-family denominator or string is strictly prohibited from code and plan.
    - Lightweight semantic safeguard: Programmatically inspects analysis AST to verify that NO computation combines the four AE-family denominators or detection counts into a pooled statistic.
    - Explicitly asserts that Backdoor, Worms, Shellcode, and Analysis are handled strictly independently.
    - Reports: `NO_POOLED_AE_AGGREGATION = PASS/FAIL`.
    - Four individual families evaluated independently:
      - Backdoor ($N=583$): 0 detections observed [95% CI: $0.00\%–0.63\%$]
      - Worms ($N=44$): 0 detections observed [95% CI: $0.00\%–8.04\%$, `[SMALL-N WARNING]`]
      - Shellcode ($N=378$): 0 detections observed [95% CI: $0.00\%–0.97\%$]
      - Analysis ($N=677$): 0 detections observed [95% CI: $0.00\%–0.54\%$]
- If any core claim is unsupported or overbroad, sets `unsupported_core_claim = TRUE`.
- Gate evaluation: $G_5 = \mathbf{not}\ unsupported\_core\_claim$.

### Gate 6: Table & Figure Consistency (`G6`) & Figure E8 Upstream Handoff
- Inspects all Stage-E publication tables (`table_E1.csv` to `table_E7.csv`) and figures (`figure_E1.png` to `figure_E8.png`).
- **Figure E8 Upstream Resolution & Handoff Rule**:
  - Inspects `figure_E8.png` and verifies it depicts Stage D validating BOTH research branches (Supervised Ablation and Benign-only AE) as a conceptual validation map, explicitly marked NOT a fusion model.
  - **Explicit Handoff Protocol**: If an upstream defect is found in Figure E8 (`figure_E8_upstream_defect = TRUE`), Stage F must NOT attempt to modify or redraw Stage E outputs. Instead, Stage F logs:
    `UPSTREAM_STAGE_E_REVISION_REQUIRED = TRUE`
    identifies the exact regeneration instructions in `audits/table_figure_consistency.json`, sets revision flag $R_{fig_e8\_upstream} = \mathbf{True}$, and caps the publication verdict at `READY WITH MINOR REVISIONS` without failing the read-only audit.
- If material table/figure evidence discrepancies exist: sets `table_figure_evidence_inconsistency = TRUE`.
- Gate evaluation: $G_6 = \mathbf{not}\ table\_figure\_evidence\_inconsistency$.

### Gate 7: Reproducibility & Derivation Registry (`G7`)
- **Existence-First Derivation Registry Verification**:
  - Step 1: Tests existence of `results/publication_experiments/EXP_INTEGRATED_PUBLICATION_V1/derivations/derivation_registry.json`.
  - Step 2: If file exists, inspects JSON structure, verifies all logged derivations reconcile with raw prediction artifacts, and cross-checks SHA-256 hashes.
  - Step 3: If file does NOT exist, records `derivation_registry_documentation_gap = TRUE` (flag $R_{deriv\_doc}$); never assumes or fabricates the registry.
- If critical published numbers cannot be reproduced or traced: sets `reproducibility_untraceable = TRUE`.
- Gate evaluation: $G_7 = \mathbf{not}\ reproducibility\_untraceable$.

### Gate 8: Frozen-Artifact Integrity (`G8`) & Explicit Baseline-Hash Coverage
- **Complete Inventory of Frozen Scope**:
  - Stage 0 canonical directories (`results/zero_day`, `results/stacking`, `results/autoencoder`, `results/checkpoints`, `results/feature_selection`)
  - Stage B outputs (`results/publication_experiments/EXP_NO_TTL_V1`)
  - Stage C outputs (`results/publication_experiments/EXP_AE_UNSEEN_FAMILY_V1`)
  - Stage D outputs (`results/publication_experiments/EXP_STATS_ROBUSTNESS_V1`)
  - Stage E outputs (`results/publication_experiments/EXP_INTEGRATED_PUBLICATION_V1`)
  - Data splits (`data/splits`, `data/raw`)
  - Manuscript (`RESEARCH_PAPER_MANUSCRIPT.md`)
- **Explicit Coverage Reporting (No Silent Gaps)**:
  Before evaluating G8, Stage F enumerates all frozen files and explicitly tallies and reports:
  1. `total_frozen_files`
  2. `hash_verified_count` (`HASH_VERIFIED`: verified against pre-recorded baseline SHA-256)
  3. `repository_verified_count` (`REPOSITORY_VERIFIED`: verified clean working tree in git status with zero diff)
  4. `no_baseline_hash_count` (`NO_BASELINE_HASH_AVAILABLE`: files without prior cryptographic hash baseline)
  These counts are explicitly stored in `audits/frozen_artifact_integrity.json` and in `final_report/stage_f_final_report.md`.
- **Stage-F Output Exclusion Rule**:
  - Newly created files in `publication_experiments/stage_f/` and `results/publication_experiments/EXP_FINAL_PUBLICATION_AUDIT_V1/` are excluded from the frozen violation set.
  - Modifications, additions, or deletions inside Stage 0–E frozen paths set `frozen_artifact_modified = TRUE`.
- Gate evaluation: $G_8 = \mathbf{not}\ frozen\_artifact\_modified$.

### Gate 9: Reviewer Risk Dynamic Evaluation (`G9`) — Separated Evidence & Manuscript Basis
- **Separation of Evidence Safety from Manuscript Wording**:
  - `stage_e_final_report.md` / Stage-E evidence serves as the **evidence/protocol basis**.
  - `RESEARCH_PAPER_MANUSCRIPT.md` serves as the **submission-wording basis**.
- **Dynamic Two-Level Classification per Objection**:
  For each of the 10 reviewer objections, Gate 9 evaluates:
  1. `evidence_risk_classification`: Evaluated against Stage-E evidence and experimental protocol (`ALREADY CONTROLLED` / `EXPLICITLY LIMITED` / `CRITICAL`).
  2. `manuscript_wording_classification`: Evaluated against `RESEARCH_PAPER_MANUSCRIPT.md`:
     - First determines whether the relevant claim/limitation exists in the manuscript.
     - If the manuscript is silent because it is `STALE` or `ABSENT`, it is strictly classified as:
       `REQUIRES MANUSCRIPT REVISION`.
     - Stage-E evidence alone CANNOT produce `EXPLICITLY LIMITED` or `ALREADY CONTROLLED` when the manuscript wording is absent or silent.
     - If the manuscript explicitly contains the correct limitation/claim wording:
       - adequate $\to$ `EXPLICITLY LIMITED` / `ALREADY CONTROLLED`
       - inadequate $\to$ `REQUIRES MANUSCRIPT REVISION`
  3. `final_classification`: Prioritizes the manuscript status when assessing publication readiness:
     - If `evidence_risk_classification == "CRITICAL"`, then `final_classification = "CRITICAL"`.
     - Else if `manuscript_wording_classification == "REQUIRES MANUSCRIPT REVISION"`, then `final_classification = "REQUIRES MANUSCRIPT REVISION"`.
     - Else `final_classification = evidence_risk_classification`.
- **The 10 Dynamically Evaluated Objections**:
  1. Single-dataset evaluation scope (UNSW-NB15)
  2. Small sample size for Worms ($N=44$, wide CI $[0.00\%, 8.04\%]$)
  3. Zero primary AE detections across four separate families (Backdoor 583, Worms 44, Shellcode 378, Analysis 677)
  4. AE secondary threshold sensitivity (benign FPR trade-off at relaxed thresholds)
  5. Paired test structural degeneracy ($B=0, C=0$)
  6. TTL dependence & non-causal representation ablation
  7. Multi-seed descriptive replication ($N=3$ seeds)
  8. Absence of external multi-testbed validation
  9. Scope of zero-day definition (held-out family vs wild attacks)
  10. Practical deployment viability (operational false alarm burden)
- **Reporting Both Classifications & Revision List**:
  - Gate 9 reports BOTH `evidence_risk_classification` and `manuscript_wording_classification` for every objection.
  - Because the manuscript is currently `STALE`, the audit explicitly identifies which of the 10 reviewer objections require manuscript integration rather than falsely presenting them as already limited in the text.
  - Evaluates $G_9 = \mathbf{not}\ critical\_reviewer\_risk$ ($G_9 = \mathbf{True}$ when no objection is `CRITICAL`).
  - Prominently surfaces:
    `reviewer_risk_requires_revision = TRUE/FALSE`
    and explicitly lists all objections requiring manuscript revision.
  - Enforces: `G9: PASS` confirms the research methodology contains no unmitigated fatal flaws; it does NOT imply "no reviewer concerns."
  - Gate evaluation: $G_9 = \mathbf{not}\ critical\_reviewer\_risk$.

---

## 5. Complete Final-Verdict Truth Table (Formal Booleans)

### Formal Safety Flags:
- `critical_numerical_failure` $\in \{\mathbf{True}, \mathbf{False}\}$
- `critical_methodology_failure` $\in \{\mathbf{True}, \mathbf{False}\}$
- `actual_leakage_found` $\in \{\mathbf{True}, \mathbf{False}\}$
- `critical_statistical_failure` $\in \{\mathbf{True}, \mathbf{False}\}$
- `unsupported_core_claim` $\in \{\mathbf{True}, \mathbf{False}\}$
- `table_figure_evidence_inconsistency` $\in \{\mathbf{True}, \mathbf{False}\}$
- `reproducibility_untraceable` $\in \{\mathbf{True}, \mathbf{False}\}$
- `frozen_artifact_modified` $\in \{\mathbf{True}, \mathbf{False}\}$
- `critical_reviewer_risk` $\in \{\mathbf{True}, \mathbf{False}\}$

### Core Gates ($G_1 \dots G_9$):
$$G_1 = \mathbf{not}\ critical\_numerical\_failure$$
$$G_2 = \mathbf{not}\ critical\_methodology\_failure$$
$$G_3 = \mathbf{not}\ actual\_leakage\_found$$
$$G_4 = \mathbf{not}\ critical\_statistical\_failure$$
$$G_5 = \mathbf{not}\ unsupported\_core\_claim$$
$$G_6 = \mathbf{not}\ table\_figure\_evidence\_inconsistency$$
$$G_7 = \mathbf{not}\ reproducibility\_untraceable$$
$$G_8 = \mathbf{not}\ frozen\_artifact\_modified$$
$$G_9 = \mathbf{not}\ critical\_reviewer\_risk$$

### Revision Flags ($R_1 \dots R_6$):
- $R_1$: `R_MANUSCRIPT_SUBSTANTIAL_UPDATE` (True when manuscript lacks Stage B–E results)
- $R_2$: `R_LEAKAGE_DOCUMENTATION_GAP` (True if leakage documentation needs strengthening)
- $R_3$: `R_DERIVATION_REGISTRY_DOCUMENTATION_GAP` (True if derivation registry has gaps)
- $R_4$: `R_FIGURE_E8_UPSTREAM_DEFECT` (True if Figure E8 needs upstream revision)
- $R_5$: `R_REVIEWER_RISK_REQUIRES_REVISION` (True if reviewer objection requires manuscript text)
- $R_6$: `R_MINOR_WORDING_FORMATTING` (True for minor cosmetic cleanups)

### Final Verdict Mapping:
```python
any_automatic_not_ready = (
    not G1 or not G2 or not G3 or not G4 or not G5 or not G6 or not G7 or not G8 or not G9
    or actual_leakage_found
    or unsupported_core_claim
    or critical_numerical_failure
    or critical_methodology_failure
    or critical_statistical_failure
    or frozen_artifact_modified
)

has_revision_flag = (
    R_MANUSCRIPT_SUBSTANTIAL_UPDATE
    or R_LEAKAGE_DOCUMENTATION_GAP
    or R_DERIVATION_REGISTRY_DOCUMENTATION_GAP
    or R_FIGURE_E8_UPSTREAM_DEFECT
    or R_REVIEWER_RISK_REQUIRES_REVISION
    or R_MINOR_WORDING_FORMATTING
)

if any_automatic_not_ready:
    final_verdict = "NOT READY"
elif has_revision_flag:
    final_verdict = "READY WITH MINOR REVISIONS"
else:
    final_verdict = "READY FOR SUBMISSION"
```

Because `R_MANUSCRIPT_SUBSTANTIAL_UPDATE = TRUE`, the final verdict when all 9 core gates pass will be **`READY WITH MINOR REVISIONS`**, with the explicit condition `SUBSTANTIAL_MANUSCRIPT_UPDATE_REQUIRED = TRUE`.

---

## 6. Output Architecture (`results/publication_experiments/EXP_FINAL_PUBLICATION_AUDIT_V1/`)

```text
EXP_FINAL_PUBLICATION_AUDIT_V1/
├── metadata/
│   ├── execution_metadata.json
│   ├── environment.json
│   └── source_scope.json
├── audits/
│   ├── numerical_consistency.json
│   ├── methodology_consistency.json
│   ├── leakage_integrity.json
│   ├── statistical_validity.json
│   ├── claims_audit.json
│   ├── table_figure_consistency.json
│   ├── reproducibility_audit.json
│   ├── frozen_artifact_integrity.json
│   ├── reviewer_risk.json
│   └── final_gate.json
└── final_report/
    ├── stage_f_final_report.md
    └── stage_f_final_report.json
```

---

## 7. Verification Plan & Execution Protocol

### Step 1: Static Pre-Execution Audit
- Run: `.venv\Scripts\python.exe publication_experiments/stage_f/scripts/run_stage_f_audit.py`
- Asserts:
  1. Dynamic numeric verification mechanism exists with no hardcoded expected values; static status reports `NUMERIC_VERIFICATION_EXECUTED = FALSE`.
  2. Derivation registry existence checked before content assertions.
  3. No pooled multi-family denominators or pooled AE statistics anywhere in code or plan.
  4. All safety conditions are formal computable booleans.
  5. Manuscript severity is separated (`R_MANUSCRIPT_SUBSTANTIAL_UPDATE` vs `R_MINOR_WORDING_FORMATTING`).
  6. Stage-F output exclusion is explicitly tested.
  7. Frozen artifact isolation check passes.
  8. Gate 9 objection classifications are computed dynamically, not hard-coded.
  9. Baseline-hash coverage is counted explicitly across all frozen files.
  10. Figure E8 upstream handoff protocol exists.
  11. Reviewer-risk revision flag is surfaced separately from G9.

### Step 2: Stop and Report Static Audit Result
- As instructed by user, after these fixes, run ONLY the static audit and report PASS/FAIL.
- Do NOT run the master analysis pipeline until user approval is obtained.
