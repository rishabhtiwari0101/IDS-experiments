# Sprint 9 — T-DETERMINISTIC Verification

## Purpose
Second identical evaluation run to verify T-DETERMINISTIC per Final Design §13.

## Result
**T-DETERMINISTIC = PASS**
- 17 fields PASS / 0 fields FAIL
- FP tolerance: 1e-08 (rtol and atol)

## Provenance Note
Original Sprint 9 result artifacts were generated using the pre-correction
implementation of evaluate_sprint9.py. A non-verdict-affecting H1 boundary defect
was subsequently corrected to implement DD-7 exactly.
The observed Sprint 9 diff (0.01222799051528034) lies outside the affected interval
(-0.005, 0), so the correction does not change the stored H1 verdict.
This deterministic verification run was performed using the corrected implementation
solely to verify reproducibility and future-evaluation correctness.

## Artifacts
- `rerun_h1_results.json` — H1 rerun output
- `rerun_h2_results.json` — H2 rerun output
- `rerun_h3_results.json` — H3 rerun (inherited Sprint 8 evidence; no new inference)
- `rerun_runtime_report.json` — timing
- `comparison.json` — field-by-field match against original EXP_H123_V1/ artifacts
