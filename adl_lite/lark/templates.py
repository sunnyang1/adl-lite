"""
IM message templates for Lark consensus room broadcasts.
"""

from __future__ import annotations

from typing import Any

from ..models import ADLDocument, DiscoveryStatus


def _status_line(status: DiscoveryStatus, confidence: float) -> str:
    badges = {
        DiscoveryStatus.PROVISIONAL: "🟡 provisional",
        DiscoveryStatus.VALIDATED: "🟢 validated",
        DiscoveryStatus.DEPRECATED: "🔴 deprecated",
        DiscoveryStatus.FORKED: "🔵 forked",
        DiscoveryStatus.ARCHIVED: "⚪ archived",
    }
    badge = badges.get(status, status.value)
    return f"**Status:** {badge} | **Confidence:** {confidence:.0%}"


def discovery_broadcast(
    doc: ADLDocument,
    *,
    doc_url: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Structured markdown for a new discovery announcement."""
    fm = doc.front_matter
    title = doc.concept_name or fm.adl_id
    names = fm.provisional_names
    subtitle = ""
    if names.zh or names.en:
        parts = [p for p in (names.zh, names.en) if p]
        subtitle = f" ({' / '.join(parts)})"

    lines = [
        f"## ADL Discovery: {title}{subtitle}",
        "",
        _status_line(fm.status, fm.confidence),
        f"**ID:** `{fm.adl_id}`",
        f"**Scope:** `{fm.scope}`",
    ]
    if fm.domain:
        lines.append(f"**Domain:** {fm.domain}")
    if doc.relations:
        rel_bits = [f"{r.source} → {r.target} ({r.relation})" for r in doc.relations[:5]]
        lines.extend(["", "**Relations:**", *[f"- {b}" for b in rel_bits]])
    if doc_url:
        lines.extend(["", f"**Doc:** {doc_url}"])
    if extra:
        for key, val in extra.items():
            lines.append(f"**{key}:** {val}")
    lines.extend(["", "_Reply with feedback or 👍 to endorse validation._"])
    return "\n".join(lines)


TEMPLATES: dict[str, Any] = {
    "discovery_broadcast": discovery_broadcast,
}


def render_template(name: str, doc: ADLDocument, **kwargs: Any) -> str:
    fn = TEMPLATES.get(name)
    if fn is None:
        raise ValueError(f"unknown template: {name}")
    return fn(doc, **kwargs)
