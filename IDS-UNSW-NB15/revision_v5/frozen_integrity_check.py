#!/usr/bin/env python3
"""
frozen_integrity_check.py
==========================
Read-only integrity guard for revision_v5.

PURPOSE
-------
At the start of every phase, run this script to verify:
  1. No file OUTSIDE revision_v5/ has changed since baseline (git diff check).
  2. SHA-256 hashes of all files in the frozen directories match the stored baseline.

USAGE
-----
  # Normal check (run after every phase):
  python revision_v5/frozen_integrity_check.py

  # Initial baseline capture (run ONCE after directory creation, before any work):
  python revision_v5/frozen_integrity_check.py --update-baseline

BEHAVIOUR
---------
- Exits 0 if all checks PASS.
- Exits 1 if ANY check FAILS. Prints a detailed report of what changed.
- NEVER modifies any file outside revision_v5/.
- If anything outside NEW_ROOT changed: stop immediately and report.

BLUEPRINT REF: §Frozen-Integrity Guard
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
NEW_ROOT = REPO_ROOT / "revision_v5"
BASELINE_FILE = NEW_ROOT / "frozen_baseline_full.json"

# Directories to hash (repo-relative). These are the frozen directories.
FROZEN_DIRS = [
    "data/splits",
    "results/checkpoints",
    "results/evaluation",
    "results/zero_day",
    "results/publication_experiments",  # existing content only
    "results/feature_selection",
    "results/autoencoder",
]

# Known-critical hashes from the blueprint (hard-coded for defence-in-depth)
BLUEPRINT_HASHES = {
    "data/splits/development_test.csv":
        "04725e85732ab2fc6d9eaaa6105418b22b083b5c651067e7b0785464f414e508",
    "data/splits/protected_unseen_attack.csv":
        "6ffd23479b575e438ad90678268f40f674a663c2b9507aaf65089623397a9d91",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_hashes(dirs: list[str]) -> dict[str, str]:
    hashes = {}
    for d in dirs:
        full = REPO_ROOT / d
        if not full.exists():
            continue
        for root, _, files in os.walk(full):
            for fn in files:
                path = Path(root) / fn
                rel = path.relative_to(REPO_ROOT).as_posix()
                # Skip anything inside NEW_ROOT (only check frozen files)
                if rel.startswith("revision_v5/"):
                    continue
                hashes[rel] = sha256_file(path)
    return hashes


def git_diff_outside_new_root() -> list[str]:
    """Return list of modified files outside NEW_ROOT according to git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        changed = [
            line.strip()
            for line in result.stdout.strip().splitlines()
            if line.strip() and not line.strip().startswith("revision_v5/")
        ]
        return changed
    except subprocess.CalledProcessError as e:
        return [f"GIT_ERROR: {e}"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def update_baseline():
    print("Collecting hashes for baseline (this may take a moment)...")
    hashes = collect_hashes(FROZEN_DIRS)
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        git_commit = "UNKNOWN"

    baseline = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "file_count": len(hashes),
        "frozen_dirs": FROZEN_DIRS,
        "hashes": hashes,
    }
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f, indent=2)
    print(f"Baseline written to: {BASELINE_FILE}")
    print(f"  Files hashed: {len(hashes)}")
    print(f"  Git commit:   {git_commit}")
    return 0


def run_check():
    failures = []
    warnings = []

    # ------------------------------------------------------------------
    # 1. Git diff check: nothing outside revision_v5/ should be modified
    # ------------------------------------------------------------------
    print("[1/3] Checking git diff for changes outside revision_v5/ ...")
    changed = git_diff_outside_new_root()
    if changed:
        for f in changed:
            failures.append(f"GIT_DIFF: {f} was modified outside NEW_ROOT")
    else:
        print("      PASS — no changes outside revision_v5/ in git diff")

    # ------------------------------------------------------------------
    # 2. Blueprint hard-coded critical hashes
    # ------------------------------------------------------------------
    print("[2/3] Verifying blueprint-critical hashes ...")
    for rel, expected in BLUEPRINT_HASHES.items():
        path = REPO_ROOT / rel
        if not path.exists():
            failures.append(f"MISSING: {rel}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            failures.append(
                f"HASH_MISMATCH: {rel}\n"
                f"  expected: {expected}\n"
                f"  actual:   {actual}"
            )
        else:
            print(f"      PASS  {rel}")

    # ------------------------------------------------------------------
    # 3. Full baseline comparison (if baseline file exists)
    # ------------------------------------------------------------------
    if BASELINE_FILE.exists():
        print("[3/3] Comparing against full baseline ...")
        with open(BASELINE_FILE) as f:
            baseline = json.load(f)
        stored = baseline.get("hashes", {})
        current = collect_hashes(FROZEN_DIRS)

        for rel, expected in stored.items():
            if rel.startswith("revision_v5/"):
                continue
            if rel not in current:
                failures.append(f"FILE_DELETED: {rel}")
            elif current[rel] != expected:
                failures.append(f"HASH_MISMATCH: {rel}")
        for rel in current:
            if rel not in stored:
                warnings.append(f"NEW_FILE_OUTSIDE_NEW_ROOT: {rel}")
        if not failures and not warnings:
            print(f"      PASS — {len(stored)} baseline files match")
        else:
            for w in warnings:
                print(f"      WARN  {w}")
    else:
        print("[3/3] No full baseline file found — skipping hash comparison.")
        print("      Run with --update-baseline to create the full baseline.")

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    print()
    if failures:
        print("=" * 60)
        print("FROZEN INTEGRITY CHECK: FAILED")
        print("=" * 60)
        for f in failures:
            print(f"  FAIL: {f}")
        print()
        print("ACTION REQUIRED: Stop immediately and report. Do not proceed.")
        return 1
    else:
        print("=" * 60)
        print("FROZEN INTEGRITY CHECK: PASSED")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 60)
        return 0


def main():
    parser = argparse.ArgumentParser(description="Frozen integrity guard for revision_v5")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Compute and store the full SHA-256 baseline (run once at start).",
    )
    args = parser.parse_args()

    if args.update_baseline:
        sys.exit(update_baseline())
    else:
        sys.exit(run_check())


if __name__ == "__main__":
    main()
