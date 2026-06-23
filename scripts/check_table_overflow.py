#!/usr/bin/env python3
"""
Detect tables that might overflow \textwidth in LaTeX.

Heuristic: count columns and estimate content width.
Flag tables with many columns or wide p{...} columns.

Usage:
    python scripts/check_table_overflow.py docs/paper_ao
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any


def supports_color():
    """Check if terminal supports color output."""
    return sys.stdout.isatty() and (sys.platform != "win32" or "ANSICON" in os.environ)


import os


def color(text: str, code: str) -> str:
    """Return color-coded text if terminal supports it."""
    if not supports_color():
        return text
    codes = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    return f"{codes.get(code, '')}{text}{codes['reset']}"


def parse_column_spec(spec: str) -> tuple[int, float, list[str]]:
    """
    Parse a tabular column specification string.

    Returns (num_columns, estimated_width_cm, column_details).

    Column types and their estimated widths:
        l, r, c, |, !{}, @{}, >{...}  -> 0 (no content width, just formatting)
        p{...}                          -> parse width from argument
        m{...}, b{...}                  -> parse width from argument
        X (tabularx)                    -> ~3cm (auto-stretching, but needs some base)
        w{...}, W{...}                  -> parse width
        Other (S, D, etc.)             -> ~2cm as fallback
    """
    # Normalize: remove whitespace inside column spec for easier parsing
    spec = spec.strip()

    columns = []
    total_width = 0.0
    i = 0
    n = len(spec)

    while i < n:
        ch = spec[i]

        # Skip spaces
        if ch.isspace():
            i += 1
            continue

        # Vertical rules (|) or double rules (||)
        if ch == '|':
            i += 1
            if i < n and spec[i] == '|':
                i += 1
            continue

        # @{} or !{} or >{...} or <{...} — these don't add content width but affect spacing
        if ch in '@!><':
            # Look for matching braces
            if i + 1 < n and spec[i + 1] == '{':
                brace_depth = 1
                j = i + 2
                while j < n and brace_depth > 0:
                    if spec[j] == '{':
                        brace_depth += 1
                    elif spec[j] == '}':
                        brace_depth -= 1
                    j += 1
                # We don't count these as columns, but we do note if @{} is present
                inner = spec[i + 2:j - 1]
                i = j
                continue
            else:
                i += 1
                continue

        # p{...}, m{...}, b{...}, w{...}, W{...}, D{...}{...}{...}
        if ch in 'pmbwW' and i + 1 < n and spec[i + 1] == '{':
            brace_depth = 1
            j = i + 2
            while j < n and brace_depth > 0:
                if spec[j] == '{':
                    brace_depth += 1
                elif spec[j] == '}':
                    brace_depth -= 1
                j += 1
            inner = spec[i + 2:j - 1]
            width_cm = parse_width_expr(inner)
            columns.append(f"{ch}{{{inner}}}")
            total_width += width_cm if width_cm else 2.0
            i = j
            continue

        # D{sep}{sep}{decimals} — two required braces
        if ch == 'D' and i + 1 < n and spec[i + 1] == '{':
            # Skip three brace pairs
            for _ in range(3):
                if i < n and spec[i] == '{':
                    brace_depth = 1
                    i += 1
                    while i < n and brace_depth > 0:
                        if spec[i] == '{':
                            brace_depth += 1
                        elif spec[i] == '}':
                            brace_depth -= 1
                        i += 1
            columns.append("D{...}")
            total_width += 2.0
            continue

        # S column (siunitx) — auto-detected width, estimate 2cm
        if ch == 'S':
            columns.append("S")
            total_width += 2.0
            i += 1
            continue

        # X column (tabularx) — auto-stretching
        if ch == 'X':
            columns.append("X")
            total_width += 3.0
            i += 1
            continue

        # Standard columns: l, r, c, L, R, C
        if ch.lower() in 'lrc':
            columns.append(ch)
            total_width += 2.0
            i += 1
            continue

        # Unrecognized column character — treat as 2cm
        columns.append(ch)
        total_width += 2.0
        i += 1

    return len(columns), total_width, columns


def parse_width_expr(expr: str) -> float:
    """Parse a LaTeX width expression like '3cm', '0.5\textwidth', '1.2in', '40pt'."""
    expr = expr.strip()
    if not expr:
        return 0.0

    # Simple numeric with unit: 3cm, 1.2in, 50pt, 10mm, 2em, 4ex
    m = re.match(r'^(\d+\.?\d*)\s*(cm|mm|in|pt|em|ex|pc|bp|dd|cc|sp)$', expr)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
        conversions = {
            'cm': 1.0,
            'mm': 0.1,
            'in': 2.54,
            'pt': 0.0352778,
            'em': 0.4,   # rough for 10pt font
            'ex': 0.35,
            'pc': 0.423,
            'bp': 0.0352778,
            'dd': 0.376,
            'cc': 0.376,
            'sp': 0.00000018,
        }
        return val * conversions.get(unit, 1.0)

    # Fraction of textwidth or linewidth: 0.5\textwidth
    m = re.match(r'^(\d+\.?\d*)\\(textwidth|linewidth|columnwidth)$', expr)
    if m:
        val = float(m.group(1))
        # A4 textwidth is ~16cm
        return val * 16.0

    # Fractional: \textwidth - 2cm, etc. — just approximate
    if 'textwidth' in expr or 'linewidth' in expr:
        return 8.0  # rough half

    # Unknown — return 0 to let caller decide fallback
    return 0.0


def has_at_spacing(spec: str) -> bool:
    """Check if column spec uses @{} for compact spacing."""
    return '@{' in spec



def _extract_braced_args(text: str, count: Optional[int] = None) -> List[str]:
    """Extract top-level braced arguments from text."""
    args = []
    i = 0
    n = len(text)
    while i < n:
        # Skip whitespace
        while i < n and text[i].isspace():
            i += 1
        if i >= n or text[i] != '{':
            break
        # Found opening brace
        brace_depth = 1
        j = i + 1
        while j < n and brace_depth > 0:
            if text[j] == '{' and text[j - 1] != '\\':
                brace_depth += 1
            elif text[j] == '}' and text[j - 1] != '\\':
                brace_depth -= 1
            j += 1
        # text[i+1:j-1] is the content between braces
        args.append(text[i + 1:j - 1])
        i = j
        if count is not None and len(args) >= count:
            break
    return args

def extract_tables(tex_path: Path) -> list[dict]:
    """
    Extract all table/tabular environments from a .tex file.

    Returns list of dicts with keys:
        file, line, environment, column_spec, col_count, est_width, has_at,
        is_tabularx, auto_fit, flag, details
    """
    tables = []
    with open(tex_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Pattern to find \begin{table}...\end{table} and \begin{tabular}...\end{tabular}
    # We match table/tabular/tabularx/longtable environments
    env_pattern = re.compile(
        r'\\begin\{(table|table\*|tabular|tabularx|longtable)\*?\}'
        r'(.*?)'
        r'\\end\{\1\*?\}',
        re.DOTALL
    )

    # Also find standalone tabular/tabularx inside figures or custom environments
    standalone_tabular = re.compile(
        r'\\begin\{(tabular|tabularx|longtable)\*?\}'
        r'(.*?)'
        r'\\end\{\1\*?\}',
        re.DOTALL
    )

    # We need line numbers, so scan line by line looking for \begin...
    lines = content.split('\n')
    line_offsets = [0]
    for line in lines:
        line_offsets.append(line_offsets[-1] + len(line) + 1)

    def line_no_from_pos(pos: int) -> int:
        for i, off in enumerate(line_offsets):
            if pos < off:
                return i
        return len(lines)

    seen_spans = set()

    for pattern in (env_pattern, standalone_tabular):
        for m in pattern.finditer(content):
            start, end = m.span()
            if start in seen_spans:
                continue
            seen_spans.add(start)

            env_name = m.group(1)
            inner = m.group(2)
            line_no = line_no_from_pos(start)

            # Find column spec: for tabularx it's {\textwidth}{...}, for tabular it's {...}
            col_spec = None
            is_tabularx = env_name == 'tabularx'
            auto_fit = is_tabularx
            if env_name in ('table', 'table*'):
                # table environment: find nested tabular/tabularx/longtable
                nested_match = re.search(
                    r'\\begin\{(tabular|tabularx|longtable)\*?\}'
                    r'(.*?)'
                    r'\\end\{\1\*?\}',
                    inner, re.DOTALL
                )
                if nested_match:
                    tabular_inner = nested_match.group(2)
                    is_nested_tabularx = nested_match.group(1) == 'tabularx'
                    args = _extract_braced_args(tabular_inner, count=2 if is_nested_tabularx else 1)
                    if is_nested_tabularx and len(args) >= 2:
                        width_arg = args[0].strip()
                        col_spec = args[1].strip().replace('\n', ' ').replace('\t', ' ')
                        if 'textwidth' in width_arg or 'linewidth' in width_arg:
                            auto_fit = True
                        else:
                            auto_fit = False
                    elif len(args) >= 1:
                        col_spec = args[0].strip().replace('\n', ' ').replace('\t', ' ')
                        auto_fit = False
            else:
                # tabular, tabularx, or longtable (standalone)
                args = _extract_braced_args(inner, count=2 if is_tabularx else 1)
                if is_tabularx and len(args) >= 2:
                    width_arg = args[0].strip()
                    col_spec = args[1].strip().replace('\n', ' ').replace('\t', ' ')
                    if 'textwidth' in width_arg or 'linewidth' in width_arg:
                        auto_fit = True
                    else:
                        auto_fit = False
                elif len(args) >= 1:
                    col_spec = args[0].strip().replace('\n', ' ').replace('\t', ' ')


            if col_spec is None:
                continue

            col_count, est_width, details = parse_column_spec(col_spec)
            has_at = has_at_spacing(col_spec)

            # Determine flag status
            if auto_fit:
                flag = "OK"
            elif est_width > 15.0:
                flag = "OVERFLOW"
            elif est_width > 12.0 or col_count > 8:
                flag = "WARNING"
            else:
                flag = "OK"

            tables.append({
                'file': str(tex_path),
                'line': line_no,
                'environment': env_name,
                'column_spec': col_spec,
                'col_count': col_count,
                'est_width': round(est_width, 2),
                'has_at': has_at,
                'is_tabularx': is_tabularx,
                'auto_fit': auto_fit,
                'flag': flag,
                'details': details,
            })

    return tables


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect table width overflow in LaTeX files.")
    parser.add_argument("directory", type=Path, help="Directory to scan recursively for .tex files")
    parser.add_argument("--overflow-threshold", type=float, default=15.0, help="Width threshold in cm (default: 15.0)")
    parser.add_argument("--warning-threshold", type=float, default=12.0, help="Warning width threshold in cm (default: 12.0)")
    args = parser.parse_args()

    tex_dir = args.directory
    overflow_threshold = args.overflow_threshold
    warning_threshold = args.warning_threshold

    if not tex_dir.exists():
        print(color(f"Error: Directory not found: {tex_dir}", "red"))
        return 2

    print(color(f"Scanning {tex_dir} for .tex files...", "cyan"))
    tex_files = sorted(tex_dir.rglob("*.tex"))
    print(f"Found {len(tex_files)} .tex file(s)")

    all_tables = []
    for tex_path in tex_files:
        tables = extract_tables(tex_path)
        all_tables.extend(tables)

    print(f"Found {len(all_tables)} table/tabular environment(s)\n")

    if not all_tables:
        print(color("No tables found.", "yellow"))
        return 0

    # Categorize
    overflow_tables = [t for t in all_tables if t['flag'] == 'OVERFLOW']
    warning_tables = [t for t in all_tables if t['flag'] == 'WARNING']
    ok_tables = [t for t in all_tables if t['flag'] == 'OK']
    no_at_tables = [t for t in all_tables if not t['has_at'] and not t['auto_fit']]

    # Print results
    def print_table(t: dict, color_code: str):
        short_file = t['file'].replace(str(tex_dir) + "/", "")
        env = t['environment']
        cols = t['col_count']
        width = t['est_width']
        at_marker = "✓ @{}" if t['has_at'] else "✗ no @{}"
        auto = "(auto-fit)" if t['auto_fit'] else ""
        loc_str = f"{short_file}:{t['line']}"
        print(f"  {color(loc_str, color_code)}")
        print(f"    Env: \\begin{{{env}}} {auto}")
        print(f"    Cols: {cols}, Est. width: {width} cm, {at_marker}")
        print(f"    Spec: {t['column_spec'][:70]}{'...' if len(t['column_spec']) > 70 else ''}")
        print()

    if overflow_tables:
        print(color(f"{'='*80}", "red"))
        print(color(f"  OVERFLOW TABLES ({len(overflow_tables)})", "red"))
        print(color(f"{'='*80}", "red"))
        for t in overflow_tables:
            print_table(t, "red")

    if warning_tables:
        print(color(f"{'='*80}", "yellow"))
        print(color(f"  WARNING TABLES ({len(warning_tables)})", "yellow"))
        print(color(f"{'='*80}", "yellow"))
        for t in warning_tables:
            print_table(t, "yellow")

    if no_at_tables:
        print(color(f"{'='*80}", "magenta"))
        print(color(f"  TABLES WITHOUT @{{}} COMPACT SPACING ({len(no_at_tables)})", "magenta"))
        print(color(f"  Suggestion: add @{{}} at start/end of column spec to reduce padding", "magenta"))
        print(color(f"{'='*80}", "magenta"))
        for t in no_at_tables:
            short_file = t['file'].replace(str(tex_dir) + "/", "")
            loc_str = f"{short_file}:{t['line']}"
            print(f"  {color(loc_str, 'magenta')}")
            print(f"    Spec: {t['column_spec'][:70]}{'...' if len(t['column_spec']) > 70 else ''}")
            print()

    if ok_tables:
        print(color(f"  OK TABLES ({len(ok_tables)})", "green"))
        for t in ok_tables:
            print_table(t, "green")

    # Summary
    print(color(f"\n{'='*80}", "cyan"))
    print(f"  SUMMARY")
    print(f"  Total tables: {len(all_tables)}")
    print(f"  OVERFLOW: {len(overflow_tables)}")
    print(f"  WARNING:  {len(warning_tables)}")
    print(f"  OK:       {len(ok_tables)}")
    print(f"  Missing @{{}}: {len(no_at_tables)}")
    print(color(f"{'='*80}", "cyan"))

    if overflow_tables:
        print(color("\n  RETURNING EXIT CODE 1 (overflow detected)", "red"))
        return 1

    print(color("\n  RETURNING EXIT CODE 0 (no overflow)", "green"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
