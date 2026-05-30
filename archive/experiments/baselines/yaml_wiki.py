"""Baseline: YAML-only wiki (generic front matter, no adl:* blocks)."""

from __future__ import annotations

from pathlib import Path

import yaml

from adl_lite.memory import ADLMemory
from adl_lite.models import ADLDocument, ADLFrontMatter, ADLType, ProvisionalNames


def to_yaml_wiki(path: Path) -> ADLDocument:
    """Convert ADL file to LLM-Wiki style: YAML tags + markdown, no L3."""
    text = path.read_text(encoding="utf-8")
    text = text.lstrip()
    end = text.find("\n---", 3)
    fm_raw = text[3:end].strip() if end != -1 else ""
    body = text[end + 4 :].strip() if end != -1 else text

    data = yaml.safe_load(fm_raw) or {}
    adl_id = data.get("adl_id", path.stem)
    names = data.get("provisional_names") or {}
    en = names.get("en") if isinstance(names, dict) else adl_id

    return ADLDocument(
        front_matter=ADLFrontMatter(
            adl_type=ADLType.CONCEPT,
            adl_id=adl_id,
            scope=data.get("scope", "public"),
            domain=data.get("domain", ""),
            provisional_names=ProvisionalNames(en=en or adl_id),
        ),
        markdown_body=body,
        adl_blocks=[],
        source_path=str(path),
    )


def index_yaml_wiki(paths: list[Path], db_path: str) -> ADLMemory:
    mem = ADLMemory(db_path=db_path)
    for path in paths:
        mem.store(to_yaml_wiki(path))
    return mem
