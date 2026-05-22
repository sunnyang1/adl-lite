"""Baseline: plain Markdown (L3 blocks stripped, minimal front matter)."""

from __future__ import annotations

import re
from pathlib import Path

from adl_lite import parse_file
from adl_lite.memory import ADLMemory
from adl_lite.models import ADLDocument, ADLFrontMatter, ADLType

_RE_ADL_BLOCK = re.compile(r"```adl:\w+.*?```", re.DOTALL)


def strip_to_plain_markdown(path: Path) -> str:
    """Remove L3 blocks; keep YAML + L2 body only."""
    text = path.read_text(encoding="utf-8")
    body_start = text.find("\n---", 3)
    if body_start == -1:
        return text
    fm = text[: body_start + 4]
    body = text[body_start + 4 :]
    clean = _RE_ADL_BLOCK.sub("", body)
    return fm + clean


def index_plain_markdown(paths: list[Path], db_path: str) -> ADLMemory:
    """Index documents as plain markdown (no L3 relation graph)."""
    mem = ADLMemory(db_path=db_path)
    for path in paths:
        doc = parse_file(path)
        plain_body = strip_to_plain_markdown(path).split("---", 2)[-1]
        plain_doc = ADLDocument(
            front_matter=ADLFrontMatter(
                adl_type=ADLType.CONCEPT,
                adl_id=doc.adl_id,
                scope=doc.scope,
                domain=doc.front_matter.domain,
                provisional_names=doc.front_matter.provisional_names,
            ),
            markdown_body=plain_body,
            adl_blocks=[],
            source_path=str(path),
        )
        mem.store(plain_doc)
    return mem
