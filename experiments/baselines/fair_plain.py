"""Fair plain-Markdown baseline: same L2 prose, no L3 blocks, minimal generic front matter."""

from __future__ import annotations

import re
from pathlib import Path

from adl_lite import parse_file
from adl_lite.models import ADLDocument, ADLFrontMatter, ADLType

_RE_ADL_BLOCK = re.compile(r"```adl:\w+.*?```", re.DOTALL)
_RE_FM = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def strip_adl_blocks(body: str) -> str:
    return _RE_ADL_BLOCK.sub("", body).strip()


def adl_to_fair_plain(path: Path) -> ADLDocument:
    """Parse ADL file and produce paired plain document (same body, no structured L3)."""
    doc = parse_file(path)
    plain_body = strip_adl_blocks(doc.markdown_body)
    return ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id=f"plain-{doc.adl_id}",
            scope=doc.scope,
            domain=doc.front_matter.domain,
            provisional_names=doc.front_matter.provisional_names,
        ),
        markdown_body=plain_body,
        adl_blocks=[],
        source_path=str(path),
    )


def adl_paths_to_fair_plain(paths: list[Path]) -> list[ADLDocument]:
    return [adl_to_fair_plain(p) for p in paths]
