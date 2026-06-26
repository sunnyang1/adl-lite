"""
Scan all .tex files for theorem definitions and verify consistency.

Checks:
  - Every \begin{theorem} has a \\label
  - Every theorem label has a proof (\begin{proof} or \\paragraph{Proof})
  - Every theorem is cited by at least one \ref
  - Theorem numbering is consistent (no gaps, no duplicates)
  - Theorem summary table (tab:theorems-summary) covers all theorems

Usage:
    python scripts/check_theorems.py docs/paper_ao
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

# Map theorem labels to their expected T-number (from summary table)
CORE_THEOREM_MAP = {
    "thm:determinism": 1,
    "thm:confluence": 2,
    "thm:monotonicity-status": 3,
    "thm:boundedness": 4,
    "thm:monotonicity-confidence": 5,
    "thm:consistency": 6,
    "thm:wf-preservation": 7,
    "thm:precondition-decidability": 8,
    "thm:crdt-convergence-appendix": 9,
}


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <directory>")
        sys.exit(1)

    root = Path(sys.argv[1])
    if not root.exists():
        print(f"Error: directory not found: {root}")
        sys.exit(1)

    # Patterns
    theorem_env_pat = re.compile(r"\\begin\{theorem\}(?:\[[^\]]*\])?\s*\\label\{([^}]*)\}")
    theorem_env_no_label_pat = re.compile(r"\\begin\{theorem\}(?:\[[^\]]*\])?(?!\s*\\label)")
    inline_theorem_pat = re.compile(r"Theorem~([0-9]+)")
    proof_env_pat = re.compile(r"\\begin\{proof\}")
    proof_paragraph_pat = re.compile(r"\\paragraph\{Proof\}")
    proof_emph_pat = re.compile(r"\\emph\{Proof")
    ref_pat = re.compile(r"\\(?:ref|cref)\{([^}]*)\}")
    theorem_ref_pat = re.compile(r"Theorem~\\ref\{([^}]*)\}")
    summary_table_pat = re.compile(r"T([0-9])\s*&")

    # Data structures
    theorems = {}  # label -> (file, line, theorem_number or None)
    theorem_envs_no_label = []  # (file, line)
    inline_theorems = {}  # number -> list of (file, line)
    proofs = defaultdict(list)  # file -> list of line numbers
    refs = defaultdict(list)  # label -> list of (file, line)
    theorem_refs = defaultdict(list)  # label -> list of (file, line)
    summary_entries = set()  # T-numbers found in summary table

    tex_files = list(root.rglob("*.tex"))

    for tex_file in tex_files:
        content = tex_file.read_text(encoding="utf-8")
        lines = content.splitlines()
        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if line.startswith("%"):
                continue

            # Theorem environments with label
            for m in theorem_env_pat.finditer(line):
                label = m.group(1).strip()
                t_num = CORE_THEOREM_MAP.get(label)
                theorems[label] = (str(tex_file), line_no, t_num)

            # Theorem environments without label
            if theorem_env_no_label_pat.search(line):
                # Check if there's a label on the next line
                has_label = False
                for i in range(line_no, min(line_no + 3, len(lines) + 1)):
                    if "\\label" in lines[i - 1]:
                        has_label = True
                        break
                if not has_label:
                    theorem_envs_no_label.append((str(tex_file), line_no))

            # Inline Theorem~N declarations
            for m in inline_theorem_pat.finditer(line):
                num = int(m.group(1))
                inline_theorems.setdefault(num, []).append((str(tex_file), line_no))

            # Proofs
            if proof_env_pat.search(line):
                proofs[str(tex_file)].append(line_no)
            if proof_paragraph_pat.search(line):
                proofs[str(tex_file)].append(line_no)
            if proof_emph_pat.search(line):
                proofs[str(tex_file)].append(line_no)

            # References
            for m in ref_pat.finditer(line):
                ref_label = m.group(1).strip()
                refs[ref_label].append((str(tex_file), line_no))

            for m in theorem_ref_pat.finditer(line):
                ref_label = m.group(1).strip()
                theorem_refs[ref_label].append((str(tex_file), line_no))

            # Summary table entries (T1, T2, etc.)
            for m in summary_table_pat.finditer(line):
                summary_entries.add(int(m.group(1)))

    print(f"Scanned {len(tex_files)} .tex files")
    print(f"Found {len(theorems)} theorem environments")
    print(f"Found {len(inline_theorems)} inline theorem declarations")
    print(f"Found {sum(len(v) for v in proofs.values())} proof blocks")
    print()

    issues = 0

    # Check 1: Theorems without labels
    if theorem_envs_no_label:
        issues += len(theorem_envs_no_label)
        print(f"=== THEOREMS WITHOUT LABELS ({len(theorem_envs_no_label)}) ===")
        for file, line in theorem_envs_no_label:
            print(f"  {file}:{line}  \\begin{{theorem}} has no \\label")
        print()

    # Check 2: Proofs for each theorem
    # We consider a theorem "has proof" if there's a proof marker in the same file after the theorem
    missing_proofs = []
    for label, (file, line, t_num) in theorems.items():
        file_proofs = proofs.get(file, [])
        has_proof = any(p > line for p in file_proofs)
        if not has_proof:
            missing_proofs.append((label, file, line, t_num))

    if missing_proofs:
        issues += len(missing_proofs)
        print(f"=== THEOREMS WITHOUT PROOFS ({len(missing_proofs)}) ===")
        for label, file, line, t_num in missing_proofs:
            t_str = f"T{t_num}" if t_num else "unnumbered"
            print(f"  {file}:{line}  \\label{{{label}}} ({t_str}) — no proof found")
        print()

    # Check 3: Unreferenced theorems
    all_refs = defaultdict(list)
    for label, locs in refs.items():
        all_refs[label].extend(locs)
    for label, locs in theorem_refs.items():
        all_refs[label].extend(locs)

    unreferenced = []
    for label, (file, line, t_num) in theorems.items():
        if label not in all_refs or not all_refs[label]:
            unreferenced.append((label, file, line, t_num))

    if unreferenced:
        print(f"=== UNREFERENCED THEOREMS ({len(unreferenced)}) ===")
        for label, file, line, t_num in unreferenced:
            t_str = f"T{t_num}" if t_num else "unnumbered"
            print(
                f"  {file}:{line}  \\label{{{label}}} ({t_str}) — no \\ref or Theorem~\\ref found"
            )
        print()

    # Check 4: Numbering consistency (T1-T9)
    core_numbers = {t_num for _, _, t_num in theorems.values() if t_num is not None}
    expected = set(range(1, 10))
    missing_numbers = expected - core_numbers
    duplicate_numbers = [
        n for n in range(1, 10) if sum(1 for _, _, t_num in theorems.values() if t_num == n) > 1
    ]

    if missing_numbers or duplicate_numbers:
        issues += len(missing_numbers) + len(duplicate_numbers)
        print("=== NUMBERING ISSUES ===")
        if missing_numbers:
            print(f"  Missing theorem numbers: {sorted(missing_numbers)}")
        if duplicate_numbers:
            print(f"  Duplicate theorem numbers: {duplicate_numbers}")
        print()

    # Check 5: Summary table coverage
    missing_in_summary = expected - summary_entries
    extra_in_summary = summary_entries - expected

    if missing_in_summary or extra_in_summary:
        issues += len(missing_in_summary) + len(extra_in_summary)
        print("=== SUMMARY TABLE (tab:theorems-summary) ISSUES ===")
        if missing_in_summary:
            print(f"  Missing in summary: T{', T'.join(map(str, sorted(missing_in_summary)))}")
        if extra_in_summary:
            print(f"  Extra entries in summary: T{', T'.join(map(str, sorted(extra_in_summary)))}")
        print()

    # Check 6: Extra theorems (not in T1-T9)
    extra_theorems = [label for label, (_, _, t_num) in theorems.items() if t_num is None]
    if extra_theorems:
        print("=== EXTRA THEOREMS (not in T1-T9 core set) ===")
        for label in extra_theorems:
            file, line, _ = theorems[label]
            print(f"  {file}:{line}  \\label{{{label}}}")
        print()

    # Summary
    print("=== SUMMARY ===")
    print(f"  Total theorem environments: {len(theorems)}")
    print(f"  Core theorems (T1-T9): {len([t for t in theorems.values() if t[2] is not None])}")
    print(f"  Theorems without labels: {len(theorem_envs_no_label)}")
    print(f"  Missing proofs: {len(missing_proofs)}")
    print(f"  Unreferenced: {len(unreferenced)}")
    print(f"  Missing in summary: {len(missing_in_summary)}")
    print(f"  Extra theorems: {len(extra_theorems)}")
    print()

    if issues == 0:
        print("✅ All theorem checks passed.")
        sys.exit(0)
    else:
        print(f"❌ Found {issues} issue(s). Please review above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
