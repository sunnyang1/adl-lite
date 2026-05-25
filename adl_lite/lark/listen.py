"""
MVP consensus feedback listener — stdin/file ingest or recent IM poll.

Full websocket streaming is out of scope; this module counts endorsements
from structured feedback and optionally auto-transitions via ConsensusEngine.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ..consensus import ConsensusEngine
from ..models import DiscoveryStatus
from .client import run_lark_cli

ENDORSE_PATTERNS = (
    re.compile(r"\bvalidate[d]?\b", re.I),
    re.compile(r"\bapprove[d]?\b", re.I),
    re.compile(r"👍|✅|\+1|lgtm", re.I),
    re.compile(r"同意|认可|通过"),
)


@dataclass(frozen=True)
class FeedbackEvent:
    adl_id: str
    actor: str
    text: str
    endorsed: bool


@dataclass(frozen=True)
class ListenResult:
    events: list[FeedbackEvent]
    endorsements: dict[str, int]
    transitions: list[str]
    mode: str


def _is_endorsement(text: str) -> bool:
    return any(p.search(text) for p in ENDORSE_PATTERNS)


def parse_feedback_lines(
    lines: list[str],
    *,
    default_adl_id: str | None = None,
) -> list[FeedbackEvent]:
    """
    Parse lines as ``adl_id|actor|message`` or free text with optional adl_id prefix.

    Examples:
        disc-capital-trap|agent_2|LGTM, validate
        👍 approve disc-capital-trap
    """
    events: list[FeedbackEvent] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        adl_id = default_adl_id or ""
        actor = "unknown"
        text = line
        if "|" in line:
            parts = line.split("|", 2)
            if len(parts) == 3:
                adl_id, actor, text = parts[0].strip(), parts[1].strip(), parts[2].strip()
            elif len(parts) == 2:
                adl_id, text = parts[0].strip(), parts[1].strip()
        else:
            m = re.search(r"\b(disc-|concept-)[a-zA-Z0-9_-]+\b", line)
            if m:
                adl_id = m.group(0)
        if not adl_id:
            continue
        events.append(
            FeedbackEvent(
                adl_id=adl_id,
                actor=actor,
                text=text,
                endorsed=_is_endorsement(text),
            )
        )
    return events


def load_feedback_file(path: Path) -> list[FeedbackEvent]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return parse_feedback_lines(lines)


def fetch_recent_messages(
    chat_id: str,
    *,
    limit: int = 20,
    lark_cli: str | None = None,
) -> list[str]:
    payload = run_lark_cli(
        [
            "im",
            "+chat-messages-list",
            "--chat-id",
            chat_id,
            "--page-size",
            str(min(limit, 50)),
            "--format",
            "json",
        ],
        lark_cli=lark_cli,
    )
    texts: list[str] = []
    items = payload.get("data", {}).get("items") or payload.get("items") or []
    for item in items:
        body = item.get("body") or item.get("content") or {}
        if isinstance(body, dict):
            text = body.get("text") or body.get("content") or ""
        else:
            text = str(body)
        if text:
            texts.append(str(text))
    return texts


def process_consensus_feedback(
    events: list[FeedbackEvent],
    engine: ConsensusEngine,
    *,
    threshold: int = 2,
    auto_transition: bool = False,
    actor_prefix: str = "lark_feedback",
) -> ListenResult:
    endorsements: dict[str, int] = {}
    transitions: list[str] = []

    for ev in events:
        if not ev.endorsed:
            continue
        endorsements[ev.adl_id] = endorsements.get(ev.adl_id, 0) + 1

    if auto_transition:
        for adl_id, count in endorsements.items():
            if count < threshold:
                continue
            if adl_id not in engine.chains:
                continue
            current = engine.get_status(adl_id)
            if current != DiscoveryStatus.PROVISIONAL:
                continue
            try:
                engine.transition(
                    adl_id,
                    DiscoveryStatus.VALIDATED,
                    actor=f"{actor_prefix}:{count}",
                    reason=f"Lark consensus feedback threshold ({count}>={threshold})",
                )
                transitions.append(adl_id)
            except ValueError:
                pass

    return ListenResult(
        events=events,
        endorsements=endorsements,
        transitions=transitions,
        mode="consensus_feedback",
    )


def listen(
    *,
    chat_id: str | None = None,
    stdin: bool = False,
    feedback_file: Path | None = None,
    poll_messages: bool = False,
    engine: ConsensusEngine | None = None,
    threshold: int = 2,
    auto_transition: bool = False,
    lark_cli: str | None = None,
) -> ListenResult:
    events: list[FeedbackEvent] = []
    if feedback_file:
        events.extend(load_feedback_file(feedback_file))
    if stdin:
        events.extend(parse_feedback_lines(sys.stdin.read().splitlines()))
    if poll_messages and chat_id:
        texts = fetch_recent_messages(chat_id, lark_cli=lark_cli)
        events.extend(parse_feedback_lines(texts))

    eng = engine or ConsensusEngine()
    return process_consensus_feedback(
        events,
        eng,
        threshold=threshold,
        auto_transition=auto_transition,
    )


def save_listen_state(result: ListenResult, path: Path) -> None:
    payload = {
        "endorsements": result.endorsements,
        "transitions": result.transitions,
        "event_count": len(result.events),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
