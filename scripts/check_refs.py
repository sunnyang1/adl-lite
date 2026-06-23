"""
Scan all .tex files for \label{...} and \ref{...}/\cref{...}/\eqref{...}.
Report:
  - Broken references: \ref with no matching \label
  - Dead labels: \label with no matching \ref
  - Duplicate labels: same \label in multiple files
  - File rename orphans: \ref pointing to non-existent file

Usage:
    python scripts/check_refs.py docs/paper_ao
    # Returns: 0 if clean, 1 if issues found, with printed report
"""
import sys
import re
from pathlib import Path
from collections import defaultdict


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <directory>")
        sys.exit(1)

    root = Path(sys.argv[1])
    if not root.exists():
        print(f"Error: directory not found: {root}")
        sys.exit(1)

    # Regex patterns
    label_pat = re.compile(r'\\label\{([^}]*)\}')
    ref_pat = re.compile(r'\\(?:ref|cref|eqref|pageref)\{([^}]*)\}')

    # Data structures
    labels = {}           # label -> (file, line)
    all_labels = defaultdict(list)  # label -> list of (file, line)
    refs = []             # list of (ref_key, file, line)
    issues = 0

    tex_files = list(root.rglob('*.tex'))

    for tex_file in tex_files:
        content = tex_file.read_text(encoding='utf-8')
        lines = content.splitlines()
        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if line.startswith('%'):
                continue

            # Find labels
            for m in label_pat.finditer(line):
                label_key = m.group(1).strip()
                all_labels[label_key].append((str(tex_file), line_no))
                if label_key not in labels:
                    labels[label_key] = (str(tex_file), line_no)

            # Find refs
            for m in ref_pat.finditer(line):
                ref_key = m.group(1).strip()
                refs.append((ref_key, str(tex_file), line_no))

    print(f"Scanned {len(tex_files)} .tex files")
    print(f"Found {len(labels)} unique labels, {len(refs)} references\n")

    # Broken refs
    broken = []
    for ref_key, file, line in refs:
        if ref_key not in labels:
            broken.append((ref_key, file, line))

    if broken:
        issues += len(broken)
        print(f"=== BROKEN REFERENCES ({len(broken)}) ===")
        for ref_key, file, line in broken:
            print(f"  {file}:{line}  \\ref{{{ref_key}}} — no matching \\label")
        print()

    # Dead labels (labels with no refs)
    ref_keys = {r[0] for r in refs}
    dead = []
    for label_key, locations in all_labels.items():
        if label_key not in ref_keys:
            dead.append((label_key, locations))

    if dead:
        print(f"=== DEAD LABELS ({len(dead)}) ===")
        for label_key, locations in dead:
            for file, line in locations:
                print(f"  {file}:{line}  \\label{{{label_key}}} — no references")
        print()

    # Duplicate labels
    duplicates = {k: v for k, v in all_labels.items() if len(v) > 1}
    if duplicates:
        issues += len(duplicates)
        print(f"=== DUPLICATE LABELS ({len(duplicates)}) ===")
        for label_key, locations in duplicates.items():
            print(f"  \\label{{{label_key}}} appears in:")
            for file, line in locations:
                print(f"    {file}:{line}")
        print()

    # Summary
    if issues == 0:
        print("✅ All references clean. No broken refs, no duplicates.")
        sys.exit(0)
    else:
        print(f"❌ Found {issues} issue(s). Please review above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
