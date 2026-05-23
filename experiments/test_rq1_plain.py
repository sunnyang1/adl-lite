"""RQ1 plain Markdown baseline utilities (no MiMo / no API)."""

from __future__ import annotations

import json

from experiments.rq1_batch_discover import slug_from_adl_id
from experiments.rq1_plain_discover import (
    next_plain_need_index,
    plain_output_relative,
    plain_task_markdown,
    write_stub_to_path,
)


def test_slug_from_adl_id_batch():
    assert slug_from_adl_id("disc-llm-peripheral-trap-batch001") == "peripheral-trap"
    assert slug_from_adl_id("disc-llm-crypto-mixer") == "crypto-mixer"
    assert slug_from_adl_id(None) is None


def test_plain_task_markdown_contains_scenario_and_marker():
    blob = plain_task_markdown("smurfing-pattern")
    assert "smurfing-pattern" in blob
    assert "<!-- scenario-slug: smurfing-pattern -->" in blob
    assert "Smurfing Pattern" in blob or "sub-threshold" in blob


def test_plain_output_relative():
    rel = plain_output_relative("crypto-mixer", batch_suffix="007")
    assert rel.endswith("plain_discovery_crypto-mixer_batch007.md")


def test_write_stub_has_pronouns_and_marker(tmp_path):
    dest = tmp_path / "p.md"
    write_stub_to_path("peripheral-trap", dest)
    text = dest.read_text(encoding="utf-8")
    assert "<!-- scenario-slug: peripheral-trap -->" in text
    assert "They" in text or "they" in text


def test_next_plain_need_index_requires_discovery():
    template = {
        "entries": [
            {
                "adl_id": "disc-llm-peripheral-trap",
                "discovery_path": "",
                "plain_discovery_path": "",
            },
            {
                "adl_id": "disc-llm-smurfing-pattern",
                "discovery_path": "experiments/outputs/x.md",
                "plain_discovery_path": "",
            },
        ]
    }
    assert next_plain_need_index(template) == 1


def test_fixture_merge_flow(tmp_path):
    from experiments.rq1_llm_judge import merge_plain_llm_fixture, summarize_from_template

    tpl = {
        "entries": [
            {
                "adl_id": "disc-llm-peripheral-trap",
                "discovery_path": "experiments/outputs/d1.md",
                "llm_judge_openai": {"score": 4, "model": "m", "rationale": "r"},
                "llm_judge_composer": {"score": 5, "model": "m", "rationale": "r"},
                "llm_judge_openai_plain": {"score": 4, "model": "m", "rationale": "r"},
                "llm_judge_composer_plain": {"score": 5, "model": "m", "rationale": "r"},
            }
        ]
    }
    fx = tmp_path / "fx.json"
    fx.write_text(json.dumps({"peripheral-trap": {"openai_proxy": 2, "composer_proxy": 3}}), encoding="utf-8")

    merge_plain_llm_fixture(tpl, fx)

    summary = summarize_from_template(tpl)
    pll = summary["plain_llm"]["per_judge"]["openai_proxy"]
    assert pll["mean_plain_llm"] == 2.0
    assert pll["mean_delta_adl_minus_plain_llm"] == 2.0
