"""
LLM-as-judge clients for RQ1 referent clarity (OpenAI + Anthropic).

Separate from MiMo discoverer — judges must not share the discovery provider.

Environment:
  OPENAI_API_KEY, OPENAI_BASE_URL (optional, e.g. DeepSeek), OPENAI_JUDGE_MODEL
  ANTHROPIC_API_KEY, ANTHROPIC_JUDGE_MODEL (default: claude-sonnet-4-20250514)
"""

from __future__ import annotations

import json
import os
import re
from typing import Literal

JudgeProvider = Literal["openai", "claude"]

DEFAULT_OPENAI_JUDGE_MODEL = "gpt-4o-mini"
DEFAULT_ANTHROPIC_JUDGE_MODEL = "claude-sonnet-4-20250514"

_RE_JSON_OBJECT = re.compile(r"\{[^{}]*\"referent_clarity\"[^{}]*\}", re.DOTALL)


def openai_judge_config() -> tuple[str, str] | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    model = os.environ.get("OPENAI_JUDGE_MODEL", DEFAULT_OPENAI_JUDGE_MODEL).strip()
    return key, model or DEFAULT_OPENAI_JUDGE_MODEL


def anthropic_judge_config() -> tuple[str, str] | None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    model = os.environ.get("ANTHROPIC_JUDGE_MODEL", DEFAULT_ANTHROPIC_JUDGE_MODEL).strip()
    return key, model or DEFAULT_ANTHROPIC_JUDGE_MODEL


def parse_judge_response(text: str) -> dict[str, object]:
    """Parse referent_clarity JSON from model output."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty judge response")

    candidates = [raw]
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence:
        candidates.insert(0, fence.group(1))
    for m in _RE_JSON_OBJECT.finditer(raw):
        candidates.append(m.group(0))

    last_err: Exception | None = None
    for chunk in candidates:
        try:
            data = json.loads(chunk)
        except json.JSONDecodeError as e:
            last_err = e
            continue
        score = data.get("referent_clarity")
        if score is None:
            raise ValueError("missing referent_clarity")
        score_int = int(score)
        if score_int < 1 or score_int > 5:
            raise ValueError(f"referent_clarity out of range: {score_int}")
        rationale = str(data.get("rationale", "")).strip()
        return {"referent_clarity": score_int, "rationale": rationale}

    raise ValueError(f"could not parse judge JSON: {last_err}")


def chat_openai(system: str, user: str, *, model: str | None = None, temperature: float = 0.0) -> str:
    cfg = openai_judge_config()
    if not cfg:
        raise RuntimeError("OPENAI_API_KEY not set")
    _key, default_model = cfg
    use_model = model or default_model

    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError('Install: pip install -e ".[experiments]"') from e

    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    client = OpenAI(api_key=_key, base_url=base_url) if base_url else OpenAI(api_key=_key)
    resp = client.chat.completions.create(
        model=use_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def chat_claude(system: str, user: str, *, model: str | None = None, temperature: float = 0.0) -> str:
    cfg = anthropic_judge_config()
    if not cfg:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    _key, default_model = cfg
    use_model = model or default_model

    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError('Install: pip install -e ".[experiments]" (includes anthropic)') from e

    client = anthropic.Anthropic(api_key=_key)
    resp = client.messages.create(
        model=use_model,
        max_tokens=512,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts = [b.text for b in resp.content if hasattr(b, "text") and b.text]
    return "".join(parts)


def judge_chat(provider: JudgeProvider, system: str, user: str, *, model: str | None = None) -> str:
    if provider == "openai":
        return chat_openai(system, user, model=model)
    if provider == "claude":
        return chat_claude(system, user, model=model)
    raise ValueError(f"unknown judge provider: {provider}")
