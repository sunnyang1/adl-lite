"""
Detect potentially redundant paragraphs across LaTeX sections.

Extracts text paragraphs (excluding equations, tables, citations, figure captions)
and computes cosine similarity. Reports pairs with similarity > threshold.

Usage:
    python scripts/check_redundancy.py docs/paper_ao --threshold 0.6
    # Returns: 0 if clean, 1 if redundant pairs found
"""

import argparse
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

# ANSI color codes
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"
BOLD = "\033[1m"


def supports_color():
    """Check if terminal supports color output."""
    return os.isatty(sys.stdout.fileno()) and os.environ.get("TERM", "dumb") != "dumb"


def color(text, code):
    return f"{code}{text}{RESET}" if supports_color() else text


def strip_latex_commands(text):
    """Remove LaTeX commands like \\textbf{...}, \\emph{...}, etc."""
    # Remove nested commands: \\command{...}
    # Do this iteratively to handle nesting
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\\[a-zA-Z]+\*?\{[^\}]*\}", "", text)
    # Remove commands without braces like \\textbf{...} are handled above
    # Remove remaining simple commands like \\LaTeX, \\cite{...} etc.
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^\}]*\})?", "", text)
    # Remove special chars
    text = re.sub(r"[\{\}\[\]\\]", " ", text)
    return text


def extract_paragraphs(tex_path):
    """Extract text paragraphs from a .tex file."""
    paragraphs = []
    with open(tex_path, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    skip_envs = {"equation", "align", "figure", "table", "lstlisting", "verbatim"}
    current_para = []
    current_start_line = 0
    in_skip = 0  # nesting level for skip environments

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip comment-only lines
        if stripped.startswith("%"):
            continue

        # Remove inline comments (be careful with \%)
        # Simple approach: remove from % to end of line, but not \%
        # We'll do a simple regex
        line = re.sub(r"(?<!\\)%.*$", "", line)

        # Check for begin/end of skip environments
        begin_match = re.search(r"\\begin\{([^\}]+)\}", line)
        end_match = re.search(r"\\end\{([^\}]+)\}", line)

        if begin_match:
            env_name = begin_match.group(1).split("*")[0]  # handle align*, equation*
            if (
                env_name in skip_envs
                or env_name.startswith("figure")
                or env_name.startswith("table")
            ):
                in_skip += 1

        if end_match and in_skip > 0:
            env_name = end_match.group(1).split("*")[0]
            if (
                env_name in skip_envs
                or env_name.startswith("figure")
                or env_name.startswith("table")
            ):
                in_skip -= 1
                continue

        if in_skip > 0:
            continue

        # Skip lines with only structural commands
        if re.fullmatch(
            r"\\(section|subsection|subsubsection|paragraph|subparagraph|label|ref|cite|bibitem|item|hspace|vspace|newpage|clearpage|pagebreak|noindent|indent|centering|raggedright|raggedleft).*",
            stripped,
        ):
            continue

        # Skip empty lines - they break paragraphs
        if not stripped:
            if current_para:
                para_text = " ".join(current_para).strip()
                if para_text and len(para_text) > 30:  # skip very short fragments
                    paragraphs.append(
                        {
                            "text": para_text,
                            "file": str(tex_path),
                            "start_line": current_start_line,
                        }
                    )
                current_para = []
            continue

        if not current_para:
            current_start_line = i

        current_para.append(line.strip())

    # Handle last paragraph
    if current_para:
        para_text = " ".join(current_para).strip()
        if para_text and len(para_text) > 30:
            paragraphs.append(
                {
                    "text": para_text,
                    "file": str(tex_path),
                    "start_line": current_start_line,
                }
            )

    return paragraphs


def clean_text(text):
    """Normalize text for comparison: lowercase, strip latex, remove punctuation."""
    text = strip_latex_commands(text)
    text = text.lower()
    # Remove non-alphanumeric but keep spaces
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def bow_vector(text):
    """Bag-of-words vector as Counter."""
    words = text.split()
    # Filter out very short words and stop words
    stop_words = {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "shall",
        "this",
        "that",
        "these",
        "those",
        "we",
        "our",
        "us",
        "it",
        "its",
        "they",
        "them",
        "their",
        "he",
        "she",
        "his",
        "her",
        "him",
        "i",
        "me",
        "my",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "any",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "s",
        "t",
        "don",
        "now",
        "d",
        "ll",
        "m",
        "o",
        "re",
        "ve",
        "y",
        "ain",
        "aren",
    }
    words = [w for w in words if len(w) > 2 and w not in stop_words]
    return Counter(words)


def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two Counter vectors."""
    if not vec1 or not vec2:
        return 0.0
    keys = set(vec1.keys()) | set(vec2.keys())
    dot = sum(vec1[k] * vec2[k] for k in keys)
    norm1 = math.sqrt(sum(v * v for v in vec1.values()))
    norm2 = math.sqrt(sum(v * v for v in vec2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def main():
    parser = argparse.ArgumentParser(description="Detect redundant paragraphs in LaTeX files.")
    parser.add_argument("directory", help="Directory to scan for .tex files")
    parser.add_argument(
        "--threshold", type=float, default=0.6, help="Similarity threshold (default 0.6)"
    )
    parser.add_argument(
        "--min-length", type=int, default=30, help="Minimum paragraph length in characters"
    )
    args = parser.parse_args()

    root = Path(args.directory)
    if not root.exists():
        print(f"Directory not found: {args.directory}")
        sys.exit(2)

    tex_files = list(root.rglob("*.tex"))
    if not tex_files:
        print(f"No .tex files found in {args.directory}")
        sys.exit(0)

    print(f"Scanning {len(tex_files)} .tex files for redundancy (threshold={args.threshold})...\n")

    all_paras = []
    for tf in tex_files:
        paras = extract_paragraphs(tf)
        for p in paras:
            p["cleaned"] = clean_text(p["text"])
            p["bow"] = bow_vector(p["cleaned"])
        all_paras.extend(paras)

    # Compare pairs
    # Rule: different files, or same file but >5 lines apart
    results = []
    n = len(all_paras)
    for i in range(n):
        for j in range(i + 1, n):
            pi = all_paras[i]
            pj = all_paras[j]

            # Skip if same file and within 5 lines
            if pi["file"] == pj["file"] and abs(pi["start_line"] - pj["start_line"]) <= 5:
                continue

            # Skip if either paragraph is too short after cleaning
            if len(pi["cleaned"]) < args.min_length or len(pj["cleaned"]) < args.min_length:
                continue

            sim = cosine_similarity(pi["bow"], pj["bow"])
            if sim >= args.threshold:
                results.append(
                    {
                        "sim": sim,
                        "p1": pi,
                        "p2": pj,
                    }
                )

    results.sort(key=lambda x: x["sim"], reverse=True)

    if not results:
        print(color("No redundant paragraphs found above threshold.", GREEN))
        sys.exit(0)

    print(
        f"Found {color(str(len(results)), YELLOW)} pair(s) with similarity >= {args.threshold}:\n"
    )

    for r in results:
        sim = r["sim"]
        p1 = r["p1"]
        p2 = r["p2"]
        sim_str = f"{sim:.3f}"
        if sim >= 0.8:
            sim_str = color(sim_str, RED + BOLD)
        elif sim >= 0.7:
            sim_str = color(sim_str, YELLOW)
        else:
            sim_str = color(sim_str, YELLOW)

        print(f"Similarity: {sim_str}")
        print(f"  {p1['file']}:{p1['start_line']}")
        print(f"    {p1['text'][:80]}...")
        print(f"  {p2['file']}:{p2['start_line']}")
        print(f"    {p2['text'][:80]}...")
        print()

    sys.exit(1)


if __name__ == "__main__":
    main()
