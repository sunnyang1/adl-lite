"""
ADL Lite — agent-facing tool wrappers matching CLI semantics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cli import _default_state_path, _load_engine, _save_engine
from .memory import ADLMemory
from .models import DiscoveryStatus
from .parser import ADLParseError, parse_file
from .validator import ADLValidator


def adl_parse(path: str | Path) -> dict[str, Any]:
    """Parse an ADL file; returns summary dict (matches `adl-lite parse -o json` shape)."""
    doc = parse_file(path)
    data = json.loads(doc.model_dump_json())
    data["_summary"] = {
        "adl_id": doc.adl_id,
        "concept_name": doc.concept_name,
        "relations": len(doc.relations),
        "evidence": len(doc.evidence),
        "wiki_links": doc.wiki_links,
    }
    return data


def adl_validate(path: str | Path) -> dict[str, Any]:
    """Validate one file; returns {ok, errors, path}."""
    path = Path(path)
    try:
        doc = parse_file(path)
    except (ADLParseError, OSError, ValueError) as exc:
        return {"ok": False, "path": str(path), "errors": [f"parse error: {exc}"]}

    errors = ADLValidator().validate_document(doc)
    return {"ok": len(errors) == 0, "path": str(path), "errors": errors}


def adl_store(path: str | Path, db: str | Path) -> dict[str, Any]:
    """Store document in ADLMemory."""
    doc = parse_file(path)
    mem = ADLMemory(db_path=str(db))
    mem.store(doc)
    mem.close()
    return {"stored": doc.adl_id, "db": str(db)}


def adl_query_related(
    adl_id: str,
    db: str | Path,
    depth: int = 1,
) -> list[dict[str, Any]]:
    """Graph neighbors for adl_id."""
    mem = ADLMemory(db_path=str(db))
    related = mem.find_related(adl_id, depth=depth)
    mem.close()
    return [
        {"concept": concept, "relation": relation, "confidence": conf}
        for concept, relation, conf in related
    ]


def adl_consensus_register(
    path: str | Path | None = None,
    adl_id: str | None = None,
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Register concept in consensus engine."""
    state_path = Path(state) if state else _default_state_path(None)
    engine = _load_engine(state_path)

    if path:
        doc = parse_file(path)
        engine.register(doc)
        cid = doc.adl_id
    elif adl_id:
        if adl_id not in engine.chains:
            from .models import ADLDocument, ADLFrontMatter, ADLType, ProvisionalNames

            stub = ADLDocument(
                front_matter=ADLFrontMatter(
                    adl_type=ADLType.CONCEPT,
                    adl_id=adl_id,
                    scope="public",
                    provisional_names=ProvisionalNames(en=adl_id),
                )
            )
            engine.register(stub)
        cid = adl_id
    else:
        raise ValueError("adl_consensus_register requires path or adl_id")

    _save_engine(engine, state_path)
    return {"registered": cid, "state": str(state_path)}


def adl_consensus_transition(
    adl_id: str,
    to_status: str | DiscoveryStatus,
    actor: str,
    reason: str = "",
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Transition concept status."""
    state_path = Path(state) if state else _default_state_path(None)
    engine = _load_engine(state_path)
    target = DiscoveryStatus(to_status) if isinstance(to_status, str) else to_status
    entry = engine.transition(adl_id, target, actor=actor, reason=reason)
    _save_engine(engine, state_path)
    assert entry is not None
    return {
        "adl_id": adl_id,
        "from_status": entry.from_status.value,
        "to_status": entry.to_status.value,
        "hash": entry.hash,
    }


def adl_consensus_verify(
    adl_id: str,
    state: str | Path | None = None,
) -> dict[str, Any]:
    """Verify chain integrity for adl_id."""
    state_path = Path(state) if state else _default_state_path(None)
    engine = _load_engine(state_path)
    if adl_id not in engine.chains:
        return {"ok": False, "adl_id": adl_id, "error": "not registered"}
    ok = engine.chains[adl_id].verify_integrity()
    return {
        "ok": ok,
        "adl_id": adl_id,
        "status": engine.get_status(adl_id).value,
    }
