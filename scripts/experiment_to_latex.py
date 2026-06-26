#!/usr/bin/env python3
"""
Auto-generate LaTeX tables from experiment JSON results.

Usage:
    python scripts/experiment_to_latex.py
    # Generates docs/paper_ao/tables_auto/e27.tex, e28.tex, e29.tex from JSON
"""

import json
import pathlib
import sys
from typing import Any


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in text."""
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "\\": r"\textbackslash{}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def format_number(val: Any, digits: int = 2) -> str:
    """Format a numeric value for LaTeX table."""
    if val is None:
        return "—"
    if isinstance(val, bool):
        return "1.00" if val else "0.00"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if abs(val) >= 1e4 or (0 < abs(val) < 1e-3 and val != 0):
            return f"{val:.{digits}e}"
        fmt = f"{val:.{digits}f}"
        if "." in fmt:
            fmt = fmt.rstrip("0").rstrip(".")
        return fmt
    return str(val)


def make_tabular(
    columns: list[str], align: str, rows: list[list[str]], label: str, caption: str
) -> str:
    """Generate a single LaTeX table environment."""
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\footnotesize",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{align}}}",
        r"\toprule",
    ]

    # Header row
    header = " & ".join(f"\\textbf{{{c}}}" for c in columns) + r" \\"
    lines.append(header)
    lines.append(r"\midrule")

    # Data rows
    for row in rows:
        lines.append(" & ".join(row) + r" \\")

    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )

    return "\n".join(lines) + "\n"


def generate_e27(json_path: pathlib.Path, out_dir: pathlib.Path) -> None:
    """Generate E27 CRDT merge benchmark table."""
    data = json.loads(json_path.read_text())
    raw = data.get("raw_data", [])

    columns = ["Branches", "Conflict rate", "Merge (ms)", "Integrity (ms)", "Resolution rate"]
    align = r"@{}rrrrr@{}"
    rows = []

    for entry in raw:
        branches = entry["branches"]
        conflict_rate = int(entry["conflict_rate"] * 100)
        merge_ms = entry["merge_time_ms"]["mean"]
        integrity_ms = entry["consistency_check_time_ms"]["mean"]
        resolution = entry["conflict_resolution_success_rate"]

        rows.append(
            [
                str(branches),
                f"{conflict_rate}\\%",
                format_number(merge_ms, 2),
                format_number(integrity_ms, 2),
                format_number(resolution, 2),
            ]
        )

    caption = (
        "CRDT merge benchmark (E27). Merge latency and integrity check for 100--1000 "
        "concurrent branches at conflict rates 0\\%--50\\%. All values are mean wall-clock (ms)."
    )
    label = "tab:e27-results"

    tex = make_tabular(columns, align, rows, label, caption)
    (out_dir / "e27.tex").write_text(tex)
    print("Generated", out_dir / "e27.tex")


def generate_e28(json_path: pathlib.Path, out_dir: pathlib.Path) -> None:
    """Generate E28 expert validation tables (annotator metrics + inter-rater agreement)."""
    data = json.loads(json_path.read_text())
    metrics = data.get("metrics", {})

    # Table 1: Annotator metrics
    columns1 = ["Annotator", "Precision", "Recall", "F1", "Accuracy"]
    align1 = r"@{}lrrrr@{}"
    rows1 = []

    experts = ["expert_A", "expert_B", "expert_C"]
    expert_labels = {
        "expert_A": "Expert A (acc=0.85, bias=+0.05)",
        "expert_B": "Expert B (acc=0.75, bias=-0.10)",
        "expert_C": "Expert C (acc=0.90, bias=0.00)",
    }

    for expert in experts:
        m = metrics.get(expert, {})
        rows1.append(
            [
                expert_labels[expert],
                format_number(m.get("precision", 0), 2),
                format_number(m.get("recall", 0), 2),
                format_number(m.get("f1", 0), 2),
                format_number(m.get("accuracy", 0), 2),
            ]
        )

    # Majority consensus and ADL delta
    mc = metrics.get("majority_consensus", {})
    adl = metrics.get("adl_delta_C", {})
    rows1.append(
        [
            "Majority consensus",
            format_number(mc.get("precision", 0), 2),
            format_number(mc.get("recall", 0), 2),
            format_number(mc.get("f1", 0), 2),
            format_number(mc.get("accuracy", 0), 2),
        ]
    )
    rows1.append(
        [
            "ADL $\\delta(C)$ derivation",
            format_number(adl.get("precision", 0), 2),
            format_number(adl.get("recall", 0), 2),
            format_number(adl.get("f1", 0), 2),
            format_number(adl.get("accuracy", 0), 2),
        ]
    )

    caption1 = (
        "Expert validation proxy (E28). Simulated 3 annotators with accuracy settings "
        "0.85, 0.75, 0.90 on 50 concepts with known ground truth. ADL $\\delta(C)$ precision is 1.0."
    )
    label1 = "tab:e28-results"

    tex1 = make_tabular(columns1, align1, rows1, label1, caption1)

    # Table 2: Inter-annotator agreement
    columns2 = ["Pair", "Cohen's $\\kappa$", "Agreement"]
    align2 = r"@{}lrr@{}"
    rows2 = []

    kappa_pairs = [
        ("Expert A--B", "cohens_kappa_expert_A_expert_B"),
        ("Expert A--C", "cohens_kappa_expert_A_expert_C"),
        ("Expert B--C", "cohens_kappa_expert_B_expert_C"),
    ]

    def kappa_agreement(val: float) -> str:
        if val < 0.4:
            return "slight"
        elif val < 0.6:
            return "moderate"
        elif val < 0.8:
            return "substantial"
        else:
            return "almost perfect"

    for label_text, key in kappa_pairs:
        val = metrics.get(key, 0.0)
        rows2.append(
            [
                label_text,
                format_number(val, 2),
                kappa_agreement(val),
            ]
        )

    fleiss = metrics.get("fleiss_kappa", 0.0)
    rows2.append(
        [
            "All three (Fleiss')",
            format_number(fleiss, 2),
            kappa_agreement(fleiss),
        ]
    )

    caption2 = "Inter-annotator agreement (E28). Cohen's $\\kappa$ (pairwise) and Fleiss' $\\kappa$ (three-way)."
    label2 = "tab:e28-agreement"

    tex2 = make_tabular(columns2, align2, rows2, label2, caption2)

    combined = tex1 + "\n" + tex2
    (out_dir / "e28.tex").write_text(combined)
    print("Generated", out_dir / "e28.tex")


def generate_e29(json_path: pathlib.Path, out_dir: pathlib.Path) -> None:
    """Generate E29 Merkle log comparison table."""
    data = json.loads(json_path.read_text())
    raw = data.get("raw_data", [])

    columns = [
        "Events",
        "ADL verify (ms)",
        "Rekor verify (ms)",
        "Speedup",
        "ADL proof (KB)",
        "Rekor proof (B)",
    ]
    align = r"@{}lrrrrr@{}"
    rows = []

    for entry in raw:
        n = entry["n_events"]
        # Format n as power of 10
        if n == 100:
            events = "$10^2$"
        elif n == 1000:
            events = "$10^3$"
        elif n == 10000:
            events = "$10^4$"
        elif n == 100000:
            events = "$10^5$"
        else:
            events = f"{n:,}"

        adl = entry["adl"]
        rekor = entry["sigstore_rekor"]

        adl_verify = adl["verify_time_ms"]
        rekor_verify = rekor["verify_time_ms"]
        speedup = adl_verify / rekor_verify if rekor_verify != 0 else float("inf")
        adl_proof_kb = adl["proof_size_bytes"] / 1024
        rekor_proof_b = rekor["proof_size_bytes"]

        # Format speedup with comma separator for thousands
        if speedup >= 1000:
            speedup_str = f"{speedup:,.0f}$\\times$"
        else:
            speedup_str = f"{speedup:.0f}$\\times$"

        rows.append(
            [
                events,
                format_number(adl_verify, 2),
                format_number(rekor_verify, 4),
                speedup_str,
                format_number(adl_proof_kb, 2),
                str(int(rekor_proof_b)),
            ]
        )

    caption = (
        "Merkle log quantitative comparison (E29). ADL Lite ($O(n)$ hash chain) vs. "
        "Sigstore Rekor ($O(\\log n)$ Merkle tree) at 100--100,000 events. Rekor values are "
        "analytical estimates; ADL values are measured."
    )
    label = "tab:e29-results"

    tex = make_tabular(columns, align, rows, label, caption)
    (out_dir / "e29.tex").write_text(tex)
    print("Generated", out_dir / "e29.tex")


def main() -> int:
    base = pathlib.Path(__file__).resolve().parent.parent
    experiments_dir = base / "docs" / "experiments"
    tables_dir = base / "docs" / "paper_ao" / "tables_auto"
    tables_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "e27": experiments_dir / "e27_crdt_merge.json",
        "e28": experiments_dir / "e28_expert_validation.json",
        "e29": experiments_dir / "e29_merkle_comparison.json",
    }

    for path in files.values():
        if not path.exists():
            print(f"ERROR: {path} not found", file=sys.stderr)
            return 1

    generate_e27(files["e27"], tables_dir)
    generate_e28(files["e28"], tables_dir)
    generate_e29(files["e29"], tables_dir)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
