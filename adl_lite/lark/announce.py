"""
Announce ADL discoveries to Lark IM consensus rooms.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..parser import parse_file
from .client import run_lark_cli
from .registry import LarkRegistry
from .templates import render_template


@dataclass(frozen=True)
class AnnounceResult:
    adl_id: str
    chat_id: str
    template: str
    dry_run: bool
    message_id: str | None = None


def _load_document(adl_id_or_file: str, registry: LarkRegistry | None):
    path = Path(adl_id_or_file)
    if path.is_file():
        return parse_file(path)
    if registry:
        entry = registry.get(adl_id_or_file)
        if entry and entry.get("source_path"):
            src = Path(entry["source_path"])
            if src.is_file():
                return parse_file(src)
    raise FileNotFoundError(
        f"cannot resolve ADL document for {adl_id_or_file!r} "
        "(pass a .md path or register with publish first)"
    )


def announce(
    adl_id_or_file: str,
    *,
    chat_id: str,
    template: str = "discovery_broadcast",
    dry_run: bool = False,
    lark_cli: str | None = None,
    registry: LarkRegistry | None = None,
) -> AnnounceResult:
    doc = _load_document(adl_id_or_file, registry)
    doc_url = None
    if registry:
        entry = registry.get(doc.adl_id)
        if entry:
            doc_url = entry.get("doc_url")

    body = render_template(template, doc, doc_url=doc_url)

    cmd = [
        "im",
        "+messages-send",
        "--chat-id",
        chat_id,
        "--markdown",
        body,
    ]
    if dry_run:
        cmd.append("--dry-run")

    payload = run_lark_cli(cmd, lark_cli=lark_cli)
    msg_id = None
    data = payload.get("data") or payload
    if isinstance(data, dict):
        msg_id = data.get("message_id") or data.get("msg_id")

    return AnnounceResult(
        adl_id=doc.adl_id,
        chat_id=chat_id,
        template=template,
        dry_run=dry_run,
        message_id=str(msg_id) if msg_id else None,
    )
