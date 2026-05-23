"""
Xiaomi MiMo API client (OpenAI-compatible).

Token Plan keys (tp-xxxxx) use cluster base URL from subscription, e.g.:
  https://token-plan-cn.xiaomimimo.com/v1

Pay-as-you-go keys (sk-xxxxx) use:
  https://api.xiaomimimo.com/v1

Set via environment (never commit secrets):
  MIMO_API_KEY
  MIMO_API_BASE_URL  (optional)
  MIMO_MODEL         (default: mimo-v2.5-pro)
"""

from __future__ import annotations

import os


DEFAULT_BASE_URL_TP = "https://token-plan-cn.xiaomimimo.com/v1"
DEFAULT_BASE_URL_SK = "https://api.xiaomimimo.com/v1"
DEFAULT_MODEL = "mimo-v2.5-pro"


def mimo_config() -> tuple[str, str, str] | None:
    """Return (api_key, base_url, model) if MiMo is configured."""
    key = os.environ.get("MIMO_API_KEY", "").strip()
    if not key:
        return None
    base = os.environ.get("MIMO_API_BASE_URL", "").strip()
    if not base:
        base = DEFAULT_BASE_URL_TP if key.startswith("tp-") else DEFAULT_BASE_URL_SK
    model = os.environ.get("MIMO_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return key, base.rstrip("/"), model


def chat_completion(system: str, user: str, *, model: str | None = None, temperature: float = 0.2) -> str:
    """Call MiMo chat/completions; raises on HTTP or SDK errors."""
    cfg = mimo_config()
    if not cfg:
        raise RuntimeError("MIMO_API_KEY not set")

    api_key, base_url, default_model = cfg
    use_model = model or default_model

    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError('Install: pip install -e ".[experiments]"') from e

    client = OpenAI(api_key=api_key, base_url=base_url)
    kwargs: dict = {
        "model": use_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    try:
        resp = client.chat.completions.create(**kwargs, extra_body={"thinking": {"type": "disabled"}})
    except TypeError:
        resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""
