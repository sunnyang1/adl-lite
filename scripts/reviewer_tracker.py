#!/usr/bin/env python3
"""Parse reviewer response markdown and verify each question is properly addressed.

Checks:
1. Every question has a status marker (DONE, IN PROGRESS, PARTIAL, PENDING)
2. Every question has evidence (references to section, table, equation, or file)
3. Every question has a commit reference (git commit hash or "Commit: ...")
4. No question is orphaned (has a heading but no content)

Usage:
    python scripts/reviewer_tracker.py docs/REVIEWER_RESPONSE_MR3.md
    # Returns: 0 if all pass, 1 if any fail, with printed report
"""

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class QuestionResult:
    id: str
    title: str = ""
    status: Optional[str] = None
    evidence_found: bool = False
    commit_found: bool = False
    is_future_work: bool = False
    content: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "evidence_found": self.evidence_found,
            "commit_found": self.commit_found,
            "is_future_work": self.is_future_work,
            "warnings": self.warnings,
        }


STATUS_PATTERN = re.compile(
    r"\b(DONE|IN\s*PROGRESS|PARTIAL|PENDING)\b",
    re.IGNORECASE,
)

EVIDENCE_PATTERNS = [
    re.compile(r"[§§]\d+(?:\.\d+)*"),  # Section references
    re.compile(r"Table~\\ref\{[^}]+\}"),  # Table references
    re.compile(r"eq:[a-zA-Z0-9_-]+"),  # Equation labels
    re.compile(r"`[^`]+\.(?:py|tex|md|yaml|json|sh|yml)`"),  # File paths in backticks
    re.compile(r"docs/\S+"),  # docs/ paths
    re.compile(r"Appendix\s*[A-Z~]"),  # Appendix references
    re.compile(r"\bmain\.tex\b|\bsections/\S+"),  # LaTeX files
    re.compile(r"\bE\d+\b"),  # Experiment IDs as evidence
]

COMMIT_PATTERN = re.compile(
    r"(?:\*\*)?Commit(?:\*\*)?[\s:]+(?:\*\*)?([a-f0-9]{7,40})|(?:\*\*)?commit(?:\*\*)?[\s:]+(?:\*\*)?([a-f0-9]{7,40})|\b([a-f0-9]{7,40})\b",
    re.IGNORECASE,
)

FUTURE_WORK_PATTERN = re.compile(
    r"\b(?:Future\s+Work|Planned|TODO|FIXME|FW\d+|future\s+work)\b",
    re.IGNORECASE,
)

QUESTION_HEADING_PATTERN = re.compile(
    r"^(#{2,4})\s*Q(\d+)(?:[.:]\s*|\s+)(.*)$",
    re.MULTILINE,
)


def parse_questions(text: str) -> List[QuestionResult]:
    matches = list(QUESTION_HEADING_PATTERN.finditer(text))
    results: List[QuestionResult] = []

    # Precompute line start positions for context-aware splitting
    lines = text.splitlines(keepends=True)
    line_starts = [0]
    for line in lines:
        line_starts.append(line_starts[-1] + len(line))

    def find_next_boundary(pos: int) -> int:
        # Search for next markdown heading or section separator after pos
        next_heading = re.search(r"^#{2,4}\s", text[pos:], re.MULTILINE)
        next_sep = re.search(r"^---\s*$", text[pos:], re.MULTILINE)
        candidates = []
        if next_heading:
            candidates.append(pos + next_heading.start())
        if next_sep:
            candidates.append(pos + next_sep.start())
        return min(candidates) if candidates else len(text)

    for i, match in enumerate(matches):
        q_id = match.group(2)
        title = match.group(3).strip()
        start = match.end()
        end = find_next_boundary(start)
        content = text[start:end]

        # Check for orphaned (empty content)
        if not content.strip():
            results.append(
                QuestionResult(
                    id=f"Q{q_id}",
                    title=title,
                    content="",
                    warnings=["Orphaned: no content after heading"],
                )
            )
            continue

        status_match = STATUS_PATTERN.search(content)
        status = status_match.group(1).upper().replace(" ", "_") if status_match else None

        evidence_found = any(p.search(content) for p in EVIDENCE_PATTERNS)
        commit_found = bool(COMMIT_PATTERN.search(content))
        is_future_work = bool(FUTURE_WORK_PATTERN.search(content))

        warnings: List[str] = []
        if not status:
            warnings.append("Missing status marker (DONE/IN PROGRESS/PARTIAL/PENDING)")
        if not evidence_found and not is_future_work:
            warnings.append("Missing evidence (section/table/equation/file reference)")
        if not commit_found and not is_future_work:
            warnings.append("Missing commit reference")

        results.append(
            QuestionResult(
                id=f"Q{q_id}",
                title=title,
                status=status,
                evidence_found=evidence_found,
                commit_found=commit_found,
                is_future_work=is_future_work,
                content=content,
                warnings=warnings,
            )
        )

    return results


def generate_report(results: List[QuestionResult]) -> str:
    lines: List[str] = []
    total = len(results)
    fully = sum(1 for r in results if not r.warnings)
    partial = sum(1 for r in results if r.warnings and r.status and (r.evidence_found or r.commit_found))
    pending = sum(1 for r in results if r.warnings and (not r.status or not (r.evidence_found or r.commit_found)))
    future_work = sum(1 for r in results if r.is_future_work)

    lines.append("=" * 60)
    lines.append("Reviewer Response Tracker Report")
    lines.append("=" * 60)
    lines.append(f"Total questions:       {total}")
    lines.append(f"Fully addressed:       {fully}")
    lines.append(f"Partially addressed:   {partial}")
    lines.append(f"Pending / gaps:        {pending}")
    lines.append(f"Future work items:     {future_work}")
    lines.append("")

    for r in results:
        if not r.warnings:
            symbol = "✓"
            reason = "OK"
        elif r.is_future_work:
            symbol = "⚠"
            reason = "Future Work — evidence/commit optional"
        else:
            symbol = "✗"
            reason = "; ".join(r.warnings)

        lines.append(f"{symbol} {r.id}: {r.title}")
        if r.status:
            lines.append(f"   Status: {r.status}")
        lines.append(f"   {reason}")
        lines.append("")

    lines.append("-" * 60)
    lines.append("Missing evidence list:")
    missing_evidence = [r for r in results if not r.evidence_found and not r.is_future_work]
    if missing_evidence:
        for r in missing_evidence:
            lines.append(f"  - {r.id}")
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Missing commit list:")
    missing_commit = [r for r in results if not r.commit_found and not r.is_future_work]
    if missing_commit:
        for r in missing_commit:
            lines.append(f"  - {r.id}")
    else:
        lines.append("  (none)")
    lines.append("-" * 60)

    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/reviewer_tracker.py <path-to-reviewer-response.md>")
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: file not found: {path}")
        return 1

    text = path.read_text(encoding="utf-8")
    results = parse_questions(text)

    report = generate_report(results)
    print(report)

    # Export JSON
    project_root = Path(__file__).resolve().parent.parent
    json_path = project_root / "docs" / "reviewer_tracking_status.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)

    export_data = {
        "source_file": str(path),
        "total_questions": len(results),
        "fully_addressed": sum(1 for r in results if not r.warnings),
        "partially_addressed": sum(
            1 for r in results if r.warnings and r.status and (r.evidence_found or r.commit_found)
        ),
        "pending": sum(
            1 for r in results if r.warnings and (not r.status or not (r.evidence_found or r.commit_found))
        ),
        "future_work": sum(1 for r in results if r.is_future_work),
        "questions": [r.to_dict() for r in results],
    }

    json_path.write_text(json.dumps(export_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nExported JSON: {json_path}")

    return 0 if all(not r.warnings for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
