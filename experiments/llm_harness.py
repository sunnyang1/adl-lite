"""
Optional LLM-backed discovery simulation (Phase B).

Providers (first match wins):
  1. Xiaomi MiMo — MIMO_API_KEY (tp- or sk- prefix)
  2. OpenAI — OPENAI_API_KEY

Requires: pip install -e ".[experiments]"
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adl_lite import ConsensusEngine, DiscoveryStatus, parse_text
from adl_lite.validator import ADLValidator

from .harness import SimEvent
from .mimo_client import chat_completion as mimo_chat
from .mimo_client import mimo_config

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
PROMPT_PATH = ROOT / "prompts" / "write_discovery.md"

DISCOVERY_TASK = """\
Task: Write an ADL Lite discovery document about "Peripheral Attention Trap" in AML.
Output RAW markdown only — do NOT wrap the document in a ```markdown code fence.

Requirements:
- YAML front matter: adl_type: discovery, adl_id: disc-llm-peripheral-trap, domain: financial_aml,
  scope: private/ceiec-aml, status: provisional
- No pronouns: this, that, it, 这个, 那个
- At least one ```adl:relation block and one ```adl:evidence block
- evidence_type must be one of: vector_cluster, simulator_run, human_expert, cross_reference, empirical_observation
- Align monitoring signals with data/aml/concepts/aml-attention-trap.md (graph peripheral nodes, sink convergence)
"""


def _strip_markdown_fence(raw: str) -> str:
    """Remove optional outer ```markdown ... ``` wrapper from LLM output."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


@dataclass
class LLMSimResult:
    status: str
    events: list[SimEvent] = field(default_factory=list)
    discovery_path: Path | None = None
    errors: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "event_count": len(self.events),
            "discovery_path": str(self.discovery_path) if self.discovery_path else None,
            "errors": self.errors,
            **self.detail,
        }


def llm_available() -> bool:
    return mimo_config() is not None or bool(os.environ.get("OPENAI_API_KEY"))


def _provider_label() -> str:
    if mimo_config():
        _key, base, model = mimo_config()  # type: ignore[misc]
        return f"mimo:{model}@{base}"
    return "openai"


def _call_llm(system: str, user: str, model: str | None = None) -> str:
    if mimo_config():
        return mimo_chat(system, user, model=model)
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError('Install experiments extra: pip install -e ".[experiments]"') from e

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set MIMO_API_KEY or OPENAI_API_KEY")

    client = OpenAI(api_key=api_key)
    use_model = model or "gpt-4o-mini"
    resp = client.chat.completions.create(
        model=use_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""


def resolve_model(cli_model: str | None) -> str | None:
    """Use MiMo default when MIMO_API_KEY is set and CLI left OpenAI default."""
    if mimo_config() and cli_model in (None, "", "gpt-4o-mini"):
        return None
    return cli_model or ("gpt-4o-mini" if not mimo_config() else None)


def _build_revise_prompt(
    draft: str,
    *,
    validation_errors: list[str] | None = None,
    parse_error: str | None = None,
    expected_adl_id: str = "disc-llm-peripheral-trap",
) -> str:
    """Ask the model to fix a failed draft using validator/parser feedback."""
    issues: list[str] = []
    if parse_error:
        issues.append(f"Parse error: {parse_error}")
    if validation_errors:
        issues.extend(validation_errors)

    issue_block = "\n".join(f"- {e}" for e in issues)
    return f"""\
The ADL Lite document below failed checks. Produce a corrected FULL document.

Fix ONLY the listed issues. Keep the same adl_id ({expected_adl_id}) unless parse error requires YAML repair.
Output RAW markdown only — no ```markdown wrapper.

Issues:
{issue_block}

Rules reminder:
- No pronouns: this, that, it, these, those, 这个, 那个
- evidence_type ∈ vector_cluster, simulator_run, human_expert, cross_reference, empirical_observation
- domain: financial_aml

Draft to revise:
---
{draft}
---
"""


def run_llm_sim(
    *,
    model: str | None = None,
    output_dir: Path | None = None,
    max_retries: int = 1,
    discovery_task: str | None = None,
    expected_adl_id: str | None = None,
    output_name: str | None = None,
) -> LLMSimResult:
    """LLM discoverer + reviewer; on failure, ask LLM to revise up to max_retries times."""
    if not llm_available():
        return LLMSimResult(
            status="skipped",
            detail={
                "reason": "No LLM API key",
                "hint": "export MIMO_API_KEY=tp-... or OPENAI_API_KEY=sk-...",
            },
        )

    system = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else "You write ADL Lite markdown."
    events: list[SimEvent] = []
    step = 0
    provider = _provider_label()
    use_model = resolve_model(model)
    model_name = use_model or (mimo_config()[2] if mimo_config() else "gpt-4o-mini")

    def log(role: str, action: str, adl_id: str, **detail: Any) -> None:
        nonlocal step
        step += 1
        events.append(SimEvent(step, role, action, adl_id, detail))

    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    task = discovery_task or DISCOVERY_TASK
    adl_id_hint = expected_adl_id or "disc-llm-peripheral-trap"
    discovery_path = out_dir / (output_name or f"llm_discovery_{ts}.md")

    validator = ADLValidator()
    cleaned = ""
    parse_error: str | None = None
    validation_errors: list[str] = []
    doc = None
    attempts = 0
    max_attempts = 1 + max(0, max_retries)

    for attempt in range(max_attempts):
        attempts = attempt + 1
        user_msg = task if attempt == 0 else _build_revise_prompt(
            cleaned,
            validation_errors=validation_errors or None,
            parse_error=parse_error,
            expected_adl_id=adl_id_hint,
        )
        action = "emit_llm" if attempt == 0 else "revise_llm"

        try:
            raw = _call_llm(system, user_msg, model=use_model)
        except Exception as e:
            return LLMSimResult(
                status="error",
                errors=[str(e)],
                events=events,
                discovery_path=discovery_path if discovery_path.exists() else None,
                detail={"provider": provider, "attempts": attempts},
            )

        cleaned = _strip_markdown_fence(raw)
        discovery_path.write_text(cleaned, encoding="utf-8")
        log("discoverer", action, "pending", path=str(discovery_path), attempt=attempt + 1)

        parse_error = None
        try:
            doc = parse_text(cleaned)
        except Exception as e:
            parse_error = str(e)
            log("reviewer", "parse_failed", "pending", error=parse_error, attempt=attempt + 1)
            validation_errors = []
            if attempt < max_attempts - 1:
                continue
            return LLMSimResult(
                status="parse_failed",
                events=events,
                discovery_path=discovery_path,
                errors=[parse_error],
                detail={"provider": provider, "model": model_name, "attempts": attempts},
            )

        log("discoverer", "parsed", doc.adl_id, adl_type=doc.front_matter.adl_type.value, attempt=attempt + 1)
        validation_errors = validator.validate_document(doc)
        log(
            "reviewer",
            "validate",
            doc.adl_id,
            ok=len(validation_errors) == 0,
            error_count=len(validation_errors),
            attempt=attempt + 1,
        )

        if not validation_errors:
            break

        if attempt < max_attempts - 1:
            log("reviewer", "request_revision", doc.adl_id, errors=validation_errors)

    assert doc is not None
    transitions = 0
    if not validation_errors:
        engine = ConsensusEngine()
        engine.register(doc)
        transitions += 1
        if doc.status == DiscoveryStatus.PROVISIONAL:
            engine.transition(
                doc.adl_id,
                DiscoveryStatus.VALIDATED,
                actor="reviewer",
                reason="LLM discovery passed validation",
            )
            transitions += 1
            log("reviewer", "transition", doc.adl_id, to="validated")

    status = "completed" if not validation_errors else "validation_failed"
    return LLMSimResult(
        status=status,
        events=events,
        discovery_path=discovery_path,
        errors=validation_errors,
        detail={
            "consensus_transitions": transitions,
            "provider": provider,
            "model": model_name,
            "attempts": attempts,
            "revised": attempts > 1,
        },
    )


def write_llm_log(result: LLMSimResult, path: Path | None = None) -> Path:
    out = path or Path(__file__).resolve().parent / "logs" / "llm_run.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"result": result.to_dict()}, sort_keys=True)]
    for e in result.events:
        lines.append(e.to_json())
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
