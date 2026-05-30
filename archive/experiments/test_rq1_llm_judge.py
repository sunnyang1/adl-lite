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


def _mock_chat(proxy: str, system: str, user: str) -> str:
    if proxy == "openai_proxy":
        score = 5 if "Peripheral" in user else 4
    elif proxy == "composer_proxy":
        score = 3 if "Peripheral" in user else 4
    else:
        score = 4
    return json.dumps({"referent_clarity": score, "rationale": f"mock-{proxy}"})


def test_judge_text_mock(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    result = judge_text(
        "Sample L2 about Peripheral Attention Trap.", proxy="openai_proxy", chat_fn=_mock_chat
    )
    assert result["score"] == 5
    assert result["model"]
    assert "mock-openai_proxy" in result["rationale"]


def test_run_judges_for_entry_mock(monkeypatch):
    if not DISCOVERY.exists():
        pytest.skip("MiMo discovery output missing")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    entry = {
        "adl_id": "disc-llm-peripheral-trap",
        "discovery_path": "experiments/outputs/llm_discovery_peripheral-trap.md",
    }
    row = run_judges_for_entry(
        entry,
        ["openai_proxy", "composer_proxy"],
        include_fair_plain=True,
        include_plain_llm_live=False,
        chat_fn=_mock_chat,
    )
    assert entry["referent_clarity_openai_proxy"] == 5
    assert entry["referent_clarity_composer_proxy"] == 3
    assert row["judge_disagreement"] is True
    assert "openai_proxy" in row["judges"]
    assert "composer_proxy" in row["judges"]


def test_build_summary_aggregates():
    template = json.loads(DEFAULT_TEMPLATE.read_text(encoding="utf-8"))
    # Isolate the scaffold case: summaries count every row with discovery_path populated.
    for e in template["entries"][3:]:
        e["discovery_path"] = ""
    for e in template["entries"][:3]:
        e["llm_judge_openai"] = {"score": 4, "model": "gpt-test", "rationale": "a"}
        e["llm_judge_composer"] = {"score": 5, "model": "composer-test", "rationale": "b"}
        e["llm_judge_openai_plain"] = {"score": 3, "model": "gpt-test", "rationale": "c"}
        e["llm_judge_composer_plain"] = {"score": 3, "model": "composer-test", "rationale": "d"}
        e["llm_judge_openai_plain_llm"] = {"score": 2, "model": "gpt-test", "rationale": "p"}
        e["llm_judge_composer_plain_llm"] = {"score": 2, "model": "composer-test", "rationale": "p"}

    rows = [{"judge_disagreement": True}, {"judge_disagreement": False}, {"judge_disagreement": False}]
    summary = build_summary(template, rows)
    assert summary["metric"] == "llm_referent_clarity"
    assert summary["n_discoveries"] == 3
    assert summary["per_judge"]["openai_proxy"]["mean_adl"] == 4.0
    assert summary["per_judge"]["composer_proxy"]["mean_adl"] == 5.0
    assert summary["disagreement_count"] == 1
    pa = summary["plain_llm"]["per_judge"]["openai_proxy"]
    assert pa["mean_plain_llm"] == 2.0


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
        discovery=ROOT / "examples" / "capital_reflux_trap.md",
        write_template=False,
        chat_fn=None,
    )
    assert isinstance(summary["judges_skipped"], list)
    assert summary["judges_skipped"], "Providers should record skips when APIs missing"
