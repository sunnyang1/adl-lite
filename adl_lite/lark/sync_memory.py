"""
Sync ADLMemory warm-layer summaries to Feishu Base via lark-cli.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..memory import ADLMemory
from ..models import DiscoveryStatus
from .client import run_lark_cli
from .registry import LarkRegistry


@dataclass(frozen=True)
class WarmRecord:
    adl_id: str
    adl_type: str
    status: str
    scope: str
    domain: str | None
    confidence: float | None
    novelty: float | None
    concept_title: str
    relation_summary: str
    doc_link: str


@dataclass(frozen=True)
class SyncMemoryResult:
    synced: int
    created: int
    updated: int
    skipped: int
    dry_run: bool
    base_token: str
    table_id: str


def _resolve_base_token(base: str, registry: LarkRegistry | None) -> str:
    """Resolve human base name via registry ``bases`` map, else use as token."""
    if base.startswith("bas"):
        return base
    if registry is not None:
        data = registry.load()
        token = data.get("bases", {}).get(base)
        if token:
            return str(token)
    return base


def iter_warm_records(
    mem: ADLMemory,
    *,
    registry: LarkRegistry | None = None,
) -> list[WarmRecord]:
    """Build warm sync rows without loading full markdown bodies."""
    rows = mem.warm.conn.execute(
        """
        SELECT adl_id, adl_type, status, scope, domain, confidence, novelty
        FROM documents
        ORDER BY adl_id
        """
    ).fetchall()

    out: list[WarmRecord] = []
    for row in rows:
        adl_id = row["adl_id"]
        rel_rows = mem.warm.conn.execute(
            "SELECT source, predicate, target FROM relations WHERE source = ? OR target = ?",
            (adl_id, adl_id),
        ).fetchall()
        rel_parts = [
            f"{r['source']}--{r['predicate']}-->{r['target']}" for r in rel_rows
        ]
        sk = mem.hot.get(adl_id)
        title = adl_id
        if sk and sk.domain_tag:
            title = sk.domain_tag
        reg_entry = registry.get(adl_id) if registry else None
        if reg_entry:
            title = reg_entry.get("title") or title
            doc_link = reg_entry.get("doc_url") or ""
        else:
            doc_link = ""

        out.append(
            WarmRecord(
                adl_id=adl_id,
                adl_type=row["adl_type"],
                status=row["status"],
                scope=row["scope"],
                domain=row["domain"],
                confidence=row["confidence"],
                novelty=row["novelty"],
                concept_title=title,
                relation_summary="; ".join(rel_parts[:20]),
                doc_link=doc_link,
            )
        )
    return out


def warm_record_to_fields(rec: WarmRecord) -> dict[str, Any]:
    try:
        badge = DiscoveryStatus(rec.status).value
    except ValueError:
        badge = rec.status
    return {
        "adl_id": rec.adl_id,
        "status": rec.status,
        "status_badge": badge,
        "confidence": rec.confidence if rec.confidence is not None else 0.0,
        "scope": rec.scope,
        "domain": rec.domain or "",
        "concept_title": rec.concept_title,
        "relation_summary": rec.relation_summary,
        "doc_link": rec.doc_link,
        "adl_type": rec.adl_type,
        "novelty": rec.novelty if rec.novelty is not None else 0.0,
    }


def _search_existing_record_id(
    *,
    base_token: str,
    table_id: str,
    adl_id: str,
    lark_cli: str | None,
) -> str | None:
    payload = run_lark_cli(
        [
            "base",
            "+record-search",
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--json",
            json.dumps(
                {
                    "keyword": adl_id,
                    "search_fields": ["adl_id"],
                    "select_fields": ["adl_id"],
                    "limit": 5,
                }
            ),
            "--format",
            "json",
        ],
        lark_cli=lark_cli,
    )
    items = payload.get("data", {}).get("items") or payload.get("items") or []
    for item in items:
        rid = item.get("record_id") or item.get("id")
        fields = item.get("fields") or {}
        if fields.get("adl_id") == adl_id and rid:
            return str(rid)
    return None


def upsert_warm_record(
    rec: WarmRecord,
    *,
    base_token: str,
    table_id: str,
    dry_run: bool = False,
    lark_cli: str | None = None,
) -> str:
    """Idempotent upsert by adl_id. Returns action: created|updated|dry-run."""
    fields = warm_record_to_fields(rec)
    record_id = None if dry_run else _search_existing_record_id(
        base_token=base_token,
        table_id=table_id,
        adl_id=rec.adl_id,
        lark_cli=lark_cli,
    )

    cmd = [
        "base",
        "+record-upsert",
        "--base-token",
        base_token,
        "--table-id",
        table_id,
        "--json",
        json.dumps(fields, ensure_ascii=False),
    ]
    if record_id:
        cmd.extend(["--record-id", record_id])
    if dry_run:
        cmd.append("--dry-run")

    run_lark_cli(cmd, lark_cli=lark_cli)
    return "updated" if record_id else "created"


def sync_memory(
    db_path: str,
    *,
    base: str,
    mode: str = "warm",
    table: str = "concepts",
    dry_run: bool = False,
    lark_cli: str | None = None,
    registry_path: Path | None = None,
) -> SyncMemoryResult:
    if mode != "warm":
        raise ValueError(f"unsupported sync mode: {mode} (only 'warm' implemented)")

    registry = LarkRegistry(registry_path) if registry_path else None
    base_token = _resolve_base_token(base, registry)

    mem = ADLMemory(db_path=db_path)
    try:
        records = iter_warm_records(mem, registry=registry)
    finally:
        mem.close()

    created = updated = skipped = 0
    for rec in records:
        if dry_run:
            upsert_warm_record(
                rec,
                base_token=base_token,
                table_id=table,
                dry_run=True,
                lark_cli=lark_cli,
            )
            created += 1
            continue
        action = upsert_warm_record(
            rec,
            base_token=base_token,
            table_id=table,
            dry_run=False,
            lark_cli=lark_cli,
        )
        if action == "created":
            created += 1
        else:
            updated += 1

    return SyncMemoryResult(
        synced=len(records),
        created=created,
        updated=updated,
        skipped=skipped,
        dry_run=dry_run,
        base_token=base_token,
        table_id=table,
    )
