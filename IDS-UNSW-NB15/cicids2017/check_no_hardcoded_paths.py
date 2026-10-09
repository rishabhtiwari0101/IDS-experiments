#!/usr/bin/env python3
"""
check_no_hardcoded_paths.py — Enforce Rule G4: Config-driven path and constant decoupling.

Scans ONLY python source files in cicids2017/src/ (or specified target directory).
Explicitly ignores itself, config files, reports, tests, and generated artifacts.

Fails on:
- Absolute user paths (e.g. C:/Users, OneDrive)
- Dataset-specific strings: 'UNSW', 'Backdoor', 'sttl', 'dttl', 'ct_state_ttl', 'attack_cat'
- Frozen historical UNSW constants: 583, 11.160063, 37000, 44800, 40320, 162395, 81749, 20260928
- Dimension-assignment literals: 72 or 75 assigned to dimension variables (e.g. n_features, D, input_dim)
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

FORBIDDEN_STRINGS = [
    "C:/Users",
    "c:/Users",
    "C:\\Users",
    "c:\\Users",
    "OneDrive",
    "UNSW",
    "Backdoor",
    "sttl",
    "dttl",
    "ct_state_ttl",
    "attack_cat",
]

FORBIDDEN_NUMERIC_CONSTANTS = {
    583,
    11.160063,
    37000,
    44800,
    40320,
    162395,
    81749,
    20260928,
}

DIMENSION_VAR_NAMES = {
    "n_features",
    "num_features",
    "d_in",
    "dim",
    "d",
    "D",
    "input_dim",
    "in_features",
    "feature_dim",
}

FORBIDDEN_DIMENSION_LITERALS = {72, 75}


class CodeAuditor(ast.NodeVisitor):
    def __init__(self, filepath: Path, lines: List[str], is_cross_dataset: bool = False):
        self.filepath = filepath
        self.lines = lines
        self.is_cross_dataset = is_cross_dataset
        self.violations: List[Tuple[int, str, str]] = []

    def visit_Constant(self, node: ast.Constant):
        val = node.value
        if isinstance(val, str):
            for s in FORBIDDEN_STRINGS:
                # If this is an allowed cross-dataset comparison script, allow UNSW and Backdoor
                if self.is_cross_dataset and s in ["UNSW", "Backdoor"]:
                    continue
                if re.search(re.escape(s), val, re.IGNORECASE if "user" in s.lower() else 0):
                    self.violations.append(
                        (node.lineno, f"Forbidden string '{s}'", self.lines[node.lineno - 1].strip())
                    )
        elif isinstance(val, (int, float)):
            # If this is an allowed cross-dataset comparison script, allow UNSW zero-day constant 583
            if self.is_cross_dataset and val in [583]:
                pass
            elif val in FORBIDDEN_NUMERIC_CONSTANTS:
                self.violations.append(
                    (node.lineno, f"Forbidden UNSW constant '{val}'", self.lines[node.lineno - 1].strip())
                )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # Check for dimension assignments like n_features = 75 or D = 75
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in DIMENSION_VAR_NAMES:
                if isinstance(node.value, ast.Constant) and node.value.value in FORBIDDEN_DIMENSION_LITERALS:
                    self.violations.append(
                        (
                            node.lineno,
                            f"Hardcoded dimension assignment '{target.id} = {node.value.value}'",
                            self.lines[node.lineno - 1].strip(),
                        )
                    )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Check kwargs like in_features=75
        for kw in node.keywords:
            if kw.arg in DIMENSION_VAR_NAMES:
                if isinstance(kw.value, ast.Constant) and kw.value.value in FORBIDDEN_DIMENSION_LITERALS:
                    self.violations.append(
                        (
                            node.lineno,
                            f"Hardcoded dimension argument '{kw.arg}={kw.value.value}'",
                            self.lines[node.lineno - 1].strip(),
                        )
                    )
        self.generic_visit(node)


def audit_file(filepath: Path) -> List[Tuple[int, str, str]]:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
        lines = content.splitlines()

    # Text-level scan for raw absolute paths or comments
    violations: List[Tuple[int, str, str]] = []
    for idx, line in enumerate(lines, 1):
        for s in ["C:/Users", "c:/Users", "C:\\Users", "c:\\Users", "OneDrive"]:
            if s in line:
                violations.append((idx, f"Absolute user path '{s}'", line.strip()))

    try:
        tree = ast.parse(content, filename=str(filepath))
        auditor = CodeAuditor(filepath, lines)
        auditor.visit(tree)
        # Combine unique violations
        seen = set()
        unique_violations = []
        for v in violations + auditor.violations:
            key = (v[0], v[1])
            if key not in seen:
                seen.add(key)
                unique_violations.append(v)
        return sorted(unique_violations, key=lambda x: x[0])
    except SyntaxError as e:
        return [(e.lineno or 1, f"Syntax error during AST parse: {e.msg}", "")]


CROSS_DATASET_SCRIPTS = {
    "s22_train_ft_transformer_unsw.py",
    "s25_cross_dataset_table.py",
    "s26_generate_figures.py",
}


def audit_file(filepath: Path, allow_cross_dataset: bool = False) -> List[Tuple[int, str, str]]:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
        lines = content.splitlines()

    # Text-level scan for raw absolute paths or comments (ALWAYS FORBIDDEN, NO EXCEPTIONS)
    violations: List[Tuple[int, str, str]] = []
    for idx, line in enumerate(lines, 1):
        for s in ["C:/Users", "c:/Users", "C:\\Users", "c:\\Users", "OneDrive", "C:\\ids_data", "C:/ids_data"]:
            if s.lower() in line.lower():
                violations.append((idx, f"Absolute user or external storage path '{s}'", line.strip()))

    is_cross_dataset = allow_cross_dataset and (filepath.name in CROSS_DATASET_SCRIPTS)

    # AST-level scan
    try:
        tree = ast.parse(content, filename=str(filepath))
        auditor = CodeAuditor(filepath, lines, is_cross_dataset=is_cross_dataset)
        auditor.visit(tree)
        for v in auditor.violations:
            if v not in violations:
                violations.append(v)
        return sorted(violations, key=lambda x: x[0])
    except SyntaxError as e:
        return [(e.lineno or 1, f"Syntax error during AST parse: {e.msg}", "")]


def scan_directory(target_dir: Path, allow_cross_dataset: bool = False) -> Tuple[int, int, Dict[Path, List[Tuple[int, str, str]]]]:
    files_scanned = 0
    total_violations = 0
    results: Dict[Path, List[Tuple[int, str, str]]] = {}

    if not target_dir.exists():
        return 0, 0, results

    for root, _, files in os.walk(target_dir):
        for f in files:
            if f.endswith(".py"):
                p = Path(root) / f
                # Explicit safety: never scan this checker script itself
                if p.resolve() == Path(__file__).resolve():
                    continue
                files_scanned += 1
                v = audit_file(p, allow_cross_dataset=allow_cross_dataset)
                if v:
                    results[p] = v
                    total_violations += len(v)

    return files_scanned, total_violations, results


def run_self_test() -> bool:
    """Run an isolated test to verify scanner correctly detects violations and ignores itself."""
    print("Running self-test...")
    # Test 1: Self-ignorance
    self_path = Path(__file__).resolve()
    v_self = audit_file(self_path)
    # The audit_file function directly will find text in string definitions, but scan_directory skips it
    scanned, total, res = scan_directory(self_path.parent)
    if self_path in res:
        print("FAIL: Checker scanned itself!")
        return False

    # Test 2: In-memory AST test with deliberate violations
    test_code = '''
def test_func():
    path = "C:/Users/test/data.csv"
    ds = "UNSW"
    n_features = 75
    val = 11.160063
    c = 583
    normal_math = 75 * 2  # should not flag
'''
    tree = ast.parse(test_code)
    lines = test_code.splitlines()
    auditor = CodeAuditor(Path("memory_fixture.py"), lines)
    auditor.visit(tree)
    
    flagged_reasons = [v[1] for v in auditor.violations]
    expected_substrings = [
        "C:/Users",
        "UNSW",
        "n_features = 75",
        "11.160063",
        "583"
    ]
    for exp in expected_substrings:
        if not any(exp in r for r in flagged_reasons):
            print(f"FAIL: Self-test failed to flag expected violation: {exp}")
            return False

    print("Self-test passed successfully (self-exclusion verified, test fixture flagged as expected).")
    return True


def main():
    if "--self-test" in sys.argv:
        success = run_self_test()
        sys.exit(0 if success else 1)

    allow_cross_dataset = "--allow-cross-dataset" in sys.argv

    repo_root = Path(__file__).resolve().parent.parent
    target_dir = repo_root / "cicids2017" / "src"
    
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            target_dir = Path(arg).resolve()
            break

    print(f"Scanning directory: {target_dir}")
    if allow_cross_dataset:
        print("Note: --allow-cross-dataset enabled (UNSW/Backdoor allowed exclusively in s22, s25, s26).")
    files_scanned, total_violations, results = scan_directory(target_dir, allow_cross_dataset=allow_cross_dataset)

    print(f"Files scanned: {files_scanned}")
    if total_violations == 0:
        print("PASS: Zero hardcoded paths or forbidden constants found.")
        sys.exit(0)
    else:
        print(f"FAIL: Found {total_violations} violations across {len(results)} files:")
        for path, v_list in results.items():
            rel = path.relative_to(repo_root) if repo_root in path.parents else path
            print(f"\n[{rel}]")
            for lineno, msg, line in v_list:
                print(f"  Line {lineno:4d}: {msg}")
                print(f"             {line}")
        sys.exit(1)


if __name__ == "__main__":
    main()
