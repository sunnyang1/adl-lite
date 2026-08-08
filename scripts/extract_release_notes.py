#!/usr/bin/env python3
"""Extract release notes for a specific version from CHANGELOG.md.

Usage:
    python scripts/extract_release_notes.py <version>

Example:
    python scripts/extract_release_notes.py 0.9.0-alpha
"""

import re
import sys
from pathlib import Path


def extract_release_notes(changelog_path: Path, version: str) -> str:
    """Extract the changelog section for the given version."""
    text = changelog_path.read_text(encoding="utf-8")

    # Normalize version: strip leading 'v' if present
    clean_version = version.lstrip("v")

    # Find all version headers and their positions
    header_positions = []
    for m in re.finditer(r"^## \[([^\]]+)\]", text, re.MULTILINE):
        header_positions.append((m.start(), m.group(0), m.group(1)))

    # Find the target version
    target_idx = None
    for i, (_pos, _hdr, ver) in enumerate(header_positions):
        if ver.strip() == clean_version:
            target_idx = i
            break

    if target_idx is None:
        print(f"Error: version [{clean_version}] not found in CHANGELOG.md", file=sys.stderr)
        sys.exit(1)

    # Extract from this header to the next header (or end of file)
    start = header_positions[target_idx][0]
    if target_idx + 1 < len(header_positions):
        end = header_positions[target_idx + 1][0]
    else:
        end = len(text)

    section = text[start:end].strip()

    # Remove the date suffix from the header line for cleaner display
    # e.g. "## [0.9.0-alpha] -- 2026-08-08" -> "## [0.9.0-alpha]"
    section = re.sub(rf"^(## \[{re.escape(clean_version)}\]).*", r"\1", section, count=1)

    # Build a summary header
    lines = section.split("\n")
    body_lines = lines[1:]

    output_parts = [
        f"# ADL Lite {clean_version}",
        "",
        "## What's Changed",
        "",
    ]

    # Parse subsections
    current_section = None
    sections: dict[str, list[str]] = {
        "Added": [],
        "Changed": [],
        "Fixed": [],
        "Breaking Changes": [],
        "Notes": [],
        "Docs": [],
        "Deferred": [],
    }

    section_map = {
        "### Added": "Added",
        "### Changed": "Changed",
        "### Fixed": "Fixed",
        "### Breaking Changes": "Breaking Changes",
        "### Notes": "Notes",
        "### Docs": "Docs",
        "### Deferred": "Deferred",
    }

    for line in body_lines:
        stripped = line.strip()
        if stripped in section_map:
            current_section = section_map[stripped]
        elif current_section and stripped and not stripped.startswith("<!--"):
            sections[current_section].append(line)

    for section_name, items in sections.items():
        if items:
            output_parts.append(f"### {section_name}")
            output_parts.append("")
            output_parts.extend(items)
            output_parts.append("")

    return "\n".join(output_parts)


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_release_notes.py <version>", file=sys.stderr)
        sys.exit(1)

    version = sys.argv[1]
    changelog = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
    print(extract_release_notes(changelog, version))


if __name__ == "__main__":
    main()
