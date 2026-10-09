# Manuscript Corrections Audit & Staging Log
**Sprint:** Sprint 1 — Repository Freeze, Pre-Registration & Reuse Audit  
**Document:** `reports/cicids2017_revision_v1/MANUSCRIPT_CORRECTIONS.md`  
**Governing Rule:** Rule G14 (Manuscript is touched ONLY in Sprint 8 in a revision copy under `publication_revision_v1/`)  
**Status:** READ-ONLY INVENTORY — ZERO EDITS APPLIED TO MANUSCRIPT  

---

## 1. Safety Boundary Declaration

In strict compliance with **Rule G14**, neither `publication/main_6page.tex` nor `main_6page.docx` / `FINAL_PAPER.docx` has been edited or modified during Sprint 1. All identified typographical, grammatical, mathematical, and attribution issues are logged here and staged for Sprint 8 revision.

---

## 2. Identified Corrections Staging Table

| Issue ID | File & Location | Current Erroneous Text | Recommended Corrected Text | Severity | Rationale / Source |
|---|---|---|---|:---:|---|
| **MC-01** | `publication/main_6page.tex:27` | `rishabhtiwari7781@gamil.com` | `rishabhtiwari7781@gmail.com` | **Major** | Typo in author correspondence email address domain. |
| **MC-02** | `publication/main_6page.tex:29`<br>`FINAL_PAPER.docx` | Dr. Juily Tarade with email `saptarshi.j.j.1091@gmail.com` | `[AWAITING AUTHOR CONFIRMATION]` | **Major** | Fourth author email appears dissociated from author name. Per Rule G12, requires author confirmation before changing. |
| **MC-03** | `publication/main_6page.tex:188` | "Section 1.3.6" | "Section 3.6" (or "Section III-F") | **Minor** | Internal document section cross-reference artifact. |
| **MC-04** | `publication/main_6page.tex:442` | "Section 1.6.4" | "Section 6.4" (or "Section VI-D") | **Minor** | Internal document section cross-reference artifact. |
| **MC-05** | `publication/main_6page.tex:274` | Table II footnote runs into tabular body | Wrap in standard IEEE `\begin{tablenotes}` or `\multicolumn` | **Minor** | Typesetting cleanliness and PDF compilation hygiene. |
| **MC-06** | `publication/main_6page.tex:215` | Equation 4 formatting artifacts | Standardized mathematical notation $\mathcal{L}_{\text{MSE}}(\mathbf{x}) = \frac{1}{D}\sum_{j=1}^D (x_j - \hat{x}_j)^2$ | **Moderate** | Resolves OCR/conversion artifacts in math blocks. |
| **MC-07** | `publication/main_6page.tex:230` | Equation 5 formatting artifacts | Clean LaTeX mathematical formulation for Three-Sigma threshold $\tau = \mu_{\text{val}} + 3\sigma_{\text{val}}$ | **Moderate** | Resolves OCR/conversion artifacts in math blocks. |
| **MC-08** | `publication/main_6page.tex:224` | "gradient updat" | "gradient update" | **Minor** | Missing terminal letter 'e' in manuscript text. |
| **MC-09** | `publication/main_6page.tex:142` | "Does autoencoders suppress zero-day attacks..." | "Do autoencoders suppress zero-day attacks..." | **Minor** | Grammatical subject-verb disagreement in Research Question 1. |
| **MC-10** | `publication/main_6page.tex:159` | "PyTorch MLP ($75 \to 128 \to 64 \to 2$)" | "PyTorch MLP ($75 \to 128 \to 64 \to 1$), Sigmoid binary output" | **Moderate** | Code uses `Linear(64, 1)` with `BCELoss`, not 2 logits. |
| **MC-11** | `publication/main_6page.tex:158` | "`LinearSVC` ($C=0.1$)... L2 coordinate descent" | "`LinearSVC` ($C=0.1$), squared hinge loss, `dual='auto'` / `dual=True`" | **Minor** | Clarifies exact scikit-learn solver terminology. |
| **MC-12** | `publication/main_6page.tex:510` | Generic software version statements in reproducibility section | Explicit recorded versions: Python 3.11/3.13, PyTorch 2.0+, scikit-learn 1.3+, NumPy 1.24+ | **Moderate** | Aligns manuscript claims with verified environment audit. |

---

## 3. Staging Protocol for Sprint 8

1. In **Sprint 8**, a copy directory `publication_revision_v1/` will be initialized.
2. The manuscript copy in `publication_revision_v1/` will receive the above corrections MC-01 through MC-12, along with:
   - The new cross-dataset evaluation section (incorporating CIC-IDS2017 results from Sprints 2–6);
   - The FT-Transformer baseline comparison table (Sprint 5 Part B);
   - The matched-FPR alert burden table and local deployment benchmark results (Sprint 6);
   - Additional recent references requested by the reviewers.
3. Original publication files in `publication/` remain permanently untouched.
