"""RQ1 human eval scaffold tests (no API key required)."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.rq1_batch_discover import SCENARIOS, load_template, run_batch
from experiments.rq1_human_eval import load_template as load_eval_template
from experiments.rq1_human_eval import run, summarize

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "data" / "eval" / "human_rq1_template.json"


def test_template_has_20_entries():
    data = load_eval_template(TEMPLATE)
    assert len(data["entries"]) == 20


def test_template_prepopulated_scenarios():
    data = load_eval_template(TEMPLATE)
    scenarios = [e["scenario"] for e in data["entries"][:3]]
    assert all(s and "Peripheral Attention Trap" in scenarios[0] for s in scenarios[:1])
    assert any("Smurfing Pattern" in s for s in scenarios)
    assert any("Crypto Mixer Exposure" in s for s in scenarios)
    ids = [e["adl_id"] for e in data["entries"][:3]]
    assert ids == [
        "disc-llm-peripheral-trap",
        "disc-llm-smurfing-pattern",
        "disc-llm-crypto-mixer",
    ]


def test_summarize_mean_referent_clarity():
    template = load_eval_template(TEMPLATE)
    template["entries"][0]["referent_clarity"] = 4
    template["entries"][1]["referent_clarity"] = 2
    summary = summarize(template)
    assert summary["n_rated"] == 2
    assert summary["mean_referent_clarity"] == 3.0


def test_summarize_with_discovery_paths(tmp_path):
    example = ROOT / "examples" / "gradient_explosion.md"
    template = load_eval_template(TEMPLATE)
    template["entries"][0]["discovery_path"] = str(example.relative_to(ROOT))
    template["entries"][0]["referent_clarity"] = 5

    summary = summarize(template)
    assert summary["n_with_discovery"] == 1
    assert summary["adl_mean_ambiguity"] is not None
    assert summary["plain_mean_ambiguity"] is not None
    assert summary["paired_details"][0]["referent_clarity"] == 5


def test_run_writes_summary(tmp_path):
    out = tmp_path / "rq1_human_summary.json"
    summary = run(template_path=TEMPLATE, output_path=out)
    assert out.exists()
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["metric"] == "human_referent_clarity"
    assert summary["output_path"] == str(out)


def test_run_with_plain_stub(tmp_path):
    stub = {"mean_ambiguity": 1.5, "source": "test"}
    stub_path = tmp_path / "plain_stub.json"
    stub_path.write_text(json.dumps(stub), encoding="utf-8")

    example = ROOT / "examples" / "gradient_explosion.md"
    template = load_eval_template(TEMPLATE)
    template["entries"][0]["discovery_path"] = str(example.relative_to(ROOT))

    summary = summarize(template, plain_stub=stub)
    assert summary["plain_stub"]["mean_ambiguity"] == 1.5
    assert "adl_vs_stub_delta" in summary


def test_batch_discover_skips_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MIMO_API_KEY", raising=False)
    result = run_batch()
    assert result["status"] == "skipped"


def test_batch_scenarios_match_template():
    data = load_template(TEMPLATE)
    template_ids = {e["adl_id"] for e in data["entries"][:3]}
    scenario_ids = {s["adl_id"] for s in SCENARIOS}
    assert template_ids == scenario_ids
