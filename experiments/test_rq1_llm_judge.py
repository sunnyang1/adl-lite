"""RQ1 LLM-as-judge tests (mocked APIs, no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.judge_clients import parse_judge_response
from experiments.rq1_llm_judge import (
    DEFAULT_TEMPLATE,
    build_summary,
    judge_text,
    l2_body_from_path,
    load_judge_prompt,
    run,
    run_judges_for_entry,
)

ROOT = Path(__file__).resolve().parent.parent
DISCOVERY = ROOT / "experiments" / "outputs" / "llm_discovery_peripheral-trap.md"


def test_parse_judge_response_json():
    out = parse_judge_response('{"referent_clarity": 4, "rationale": "Clear entities."}')
    assert out["referent_clarity"] == 4
    assert "Clear" in out["rationale"]


def test_parse_judge_response_fenced():
    text = 'Here is the score:\n```json\n{"referent_clarity": 3, "rationale": "Some gaps."}\n```'
    out = parse_judge_response(text)
    assert out["referent_clarity"] == 3


def test_load_judge_prompt_exists():
    prompt = load_judge_prompt()
    assert "referent clarity" in prompt.lower()
    assert "referent_clarity" in prompt


def test_l2_body_from_discovery():
    if not DISCOVERY.exists():
        pytest.skip("MiMo discovery output missing")
    body = l2_body_from_path(DISCOVERY, plain=False)
    assert "Peripheral Attention Trap" in body
    assert "```adl:" not in body


def test_l2_plain_strips_blocks():
    if not DISCOVERY.exists():
        pytest.skip("MiMo discovery output missing")
    adl = l2_body_from_path(DISCOVERY, plain=False)
    plain = l2_body_from_path(DISCOVERY, plain=True)
    assert adl == plain


def _mock_chat(provider: str, system: str, user: str, *, model: str | None = None) -> str:
    if provider == "openai":
        score = 5 if "Peripheral" in user else 4
    else:
        score = 3 if "Peripheral" in user else 4
    return json.dumps({"referent_clarity": score, "rationale": f"mock-{provider}"})


def test_judge_text_mock(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    result = judge_text("Sample L2 about Peripheral Attention Trap.", "openai", chat_fn=_mock_chat)
    assert result["score"] == 5
    assert result["model"]
    assert "mock-openai" in result["rationale"]


def test_run_judges_for_entry_mock(monkeypatch):
    if not DISCOVERY.exists():
        pytest.skip("MiMo discovery output missing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    entry = {
        "adl_id": "disc-llm-peripheral-trap",
        "discovery_path": "experiments/outputs/llm_discovery_peripheral-trap.md",
    }
    row = run_judges_for_entry(entry, ["openai", "claude"], chat_fn=_mock_chat)
    assert entry["referent_clarity_openai"] == 5
    assert entry["referent_clarity_claude"] == 3
    assert row["judge_disagreement"] is True
    assert "openai" in row["judges"]
    assert "claude" in row["judges"]


def test_build_summary_aggregates():
    template = json.loads(DEFAULT_TEMPLATE.read_text(encoding="utf-8"))
    # Isolate the scaffold case: summaries count every row with discovery_path populated.
    for e in template["entries"][3:]:
        e["discovery_path"] = ""
    for e in template["entries"][:3]:
        e["llm_judge_openai"] = {"score": 4, "model": "gpt-4o-mini", "rationale": "a"}
        e["llm_judge_claude"] = {"score": 5, "model": "claude-test", "rationale": "b"}
        e["llm_judge_openai_plain"] = {"score": 3, "model": "gpt-4o-mini", "rationale": "c"}
        e["llm_judge_claude_plain"] = {"score": 3, "model": "claude-test", "rationale": "d"}

    rows = [{"judge_disagreement": True}, {"judge_disagreement": False}, {"judge_disagreement": False}]
    summary = build_summary(template, rows)
    assert summary["metric"] == "llm_referent_clarity"
    assert summary["n_discoveries"] == 3
    assert summary["per_judge"]["openai"]["mean_adl"] == 4.0
    assert summary["per_judge"]["claude"]["mean_adl"] == 5.0
    assert summary["disagreement_count"] == 1


def test_run_writes_summary(tmp_path, monkeypatch):
    if not DISCOVERY.exists():
        pytest.skip("MiMo discovery output missing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    template = json.loads(DEFAULT_TEMPLATE.read_text(encoding="utf-8"))
    tpl_copy = tmp_path / "template.json"
    tpl_copy.write_text(json.dumps(template), encoding="utf-8")
    out = tmp_path / "rq1_llm_judge_summary.json"

    summary = run(
        template_path=tpl_copy,
        summary_path=out,
        discovery=DISCOVERY,
        judges=["openai", "claude"],
        write_template=False,
        chat_fn=_mock_chat,
    )
    assert out.exists()
    assert summary["output_path"] == str(out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["label"].startswith("LLM-as-judge")


def test_run_skips_missing_keys(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    template = json.loads(DEFAULT_TEMPLATE.read_text(encoding="utf-8"))
    tpl_copy = tmp_path / "template.json"
    tpl_copy.write_text(json.dumps(template), encoding="utf-8")
    out = tmp_path / "summary.json"

    summary = run(
        template_path=tpl_copy,
        summary_path=out,
        all_discoveries=True,
        judges=["openai", "claude"],
        write_template=False,
    )
    assert "openai" in summary["judges_skipped"] or "claude" in summary["judges_skipped"]
