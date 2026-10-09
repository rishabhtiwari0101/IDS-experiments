# Sprint 9 Quality Review
## Verdicts
- H1 Verdict: SUPPORTED
- H2 Verdict: NOT_SUPPORTED
- H3 Verdict: NOT_SUPPORTED

## Multiplicity
H1–H3 are evaluated as independently pre-registered engineering checks. No multiple-comparisons adjustment is applied across the three hypotheses.

## Mandatory Limitations
**L1 — Sprint 6 in-sample meta-learner limitation** (h1_summary.json):
> "H1 Macro-F1 is computed by evaluating the meta-learner on the same OOF matrix used to train it. No separate meta-learner holdout exists under the current data-isolation rules. This is in-sample evaluation at the meta-learner level and is NOT a fully held-out end-to-end generalisation estimate."

**L2 — Sprint 5 RF unmatched-baseline limitation** (h1_summary.json):
> "Two reporting units are used: (a) three-seed H1 stacking mean±std; (b) frozen Sprint 5 single-CV base-model reference. These are not statistically matched quantities."

**L3 — Sprint 7 single-seed AE limitation** (ae_model.py):
> "Sprint 7 uses a single AE training seed (42). No multi-seed stability estimate exists for AE reconstruction error or threshold values. This is an accepted scope limitation and not a null result."

**L4 — Validation reuse limitation** (sprint8_final_design.md):
> "VALIDATION is reused for Sprint 7 AE threshold calibration AND Sprint 8 fusion-rule selection. Both are selection-stage uses, not final held-out evaluation. This reuse is within the frozen data-isolation rules but is an explicit limitation."

**L5 — n=583 sample-size caveat** (EXP_FUSION_V1):
> "1 row = 1/583 = 0.1716 percentage points; small differences not interpretable as strong generalisation evidence."

**L6 — DD-6 FPR cap post-evidence disclosure** (sprint9_discussion_v1.md):
> "The underlying Sprint 8 C01/C06 Development TEST FPR difference (+0.0351 pp) was already known when the 2-percentage-point H3 tolerance was proposed. Therefore this tolerance is a documented operational guardrail rather than a blind pre-registration made before any relevant FPR evidence existed."

**L7 — H3 FPR cap non-determinative disclosure** (sprint9_discussion_v1.md):
> "For the frozen Sprint 8 result, the H3 FPR cap is not decision-determinative because C06 and C01 have identical Protected Backdoor detection counts (582/583). The primary H3 condition therefore already fails before the FPR cap can affect the verdict."
