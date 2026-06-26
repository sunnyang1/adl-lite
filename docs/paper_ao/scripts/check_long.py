#!/usr/bin/env python3
import os
import re

files = [f for f in os.listdir("sections") if f.endswith(".tex") and not f.endswith(".bak")]

for fname in files:
    with open(f"sections/{fname}") as fh:
        content = fh.read()

    # Remove LaTeX environments
    clean = re.sub(r"\\begin\{[^}]+\}.*?\\end\{[^}]+\}", "", content, flags=re.DOTALL)
    # Remove commands
    clean = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", clean)
    # Remove math
    clean = re.sub(r"\$[^$]+\$", " ", clean)
    # Remove comments
    clean = re.sub(r"%.*", "", clean)

    # Split into sentences
    sentences = re.split(r"[.!?]\s+", clean)
    long_sentences = []
    for s in sentences:
        words = [w for w in s.split() if w.strip()]
        if len(words) > 40:
            long_sentences.append((len(words), " ".join(words[:20]) + "..."))

    if long_sentences:
        print(f"\n=== {fname} ===")
        for count, snippet in sorted(long_sentences, reverse=True)[:5]:
            print(f"  {count} words: {snippet}")
