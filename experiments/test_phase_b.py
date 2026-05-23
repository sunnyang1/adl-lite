"""Phase B metric tests (no API key required)."""

from __future__ import annotations

from pathlib import Path

from experiments.baselines.fair_plain import adl_to_fair_plain
from experiments.rq1_ambiguity import run_phase_b, run_pilot
from experiments.rq3_retrieval import run as rq3_run
from experiments.rubric import score_document
from experiments.tfidf import TfidfIndex


def test_rubric_scores_adl_example():
    root = Path(__file__).resolve().parent.parent
    doc = adl_to_fair_plain(root / "examples" / "gradient_explosion.md")
    # fair plain strips L3 but keeps body
    result = score_document(doc)
    assert result.word_count > 0
    assert result.ambiguity_score >= 0


def test_phase_b_rq1_fair_baseline():
    root = Path(__file__).resolve().parent.parent
    paths = list((root / "examples").glob("*.md"))[:3]
    out = run_phase_b(paths=paths)
    assert out["phase_b"] is True
    assert out["n_pairs"] == 3
    assert "adl_mean_ambiguity" in out


def test_pilot_rq1_still_works():
    out = run_pilot()
    assert out["pilot"] is True
    assert "ambiguity_reduction_pct" in out


def test_tfidf_ranking():
    idx = TfidfIndex()
    idx.add("a", "smurfing small deposit structuring")
    idx.add("b", "crypto mixer blockchain tumbler")
    ranked = idx.rank("small deposit smurfing", k=1)
    assert ranked[0][0] == "a"


def test_phase_b_rq3_runs():
    out = rq3_run(mode="phase_b", k=10)
    assert out["phase_b"] is True
    assert out["scorer"] == "tfidf_fair_plain"
    assert 0 <= out["adl_recall"] <= 1
    assert out["delta"] > 0
    assert out["label_recall_delta"] is not None
    assert out["label_recall_delta"] > 0


def test_llm_sim_skips_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MIMO_API_KEY", raising=False)
    from experiments.llm_harness import run_llm_sim

    result = run_llm_sim()
    assert result.status == "skipped"


def test_revise_prompt_includes_errors():
    from experiments.llm_harness import _build_revise_prompt

    p = _build_revise_prompt("---\ntitle: x\n---\nbody", validation_errors=["Forbidden pronoun: that"])
    assert "Forbidden pronoun" in p
    assert "disc-llm-peripheral-trap" in p


def test_llm_sim_retries_on_validation_failure(monkeypatch, tmp_path):
    """Second LLM call returns clean doc after validation failure on first."""
    calls: list[str] = []

    bad = """---
adl_type: discovery
adl_id: disc-llm-peripheral-trap
status: provisional
confidence: 0.8
novelty: 0.7
domain: financial_aml
mechanism: emergent_pattern
scope: private/ceiec-aml
provisional_names:
  en: "Peripheral Attention Trap"
---

# Peripheral Attention Trap

## Discovery Statement

That pattern shows it clearly.

```adl:relation
source: "Peripheral Attention Trap"
relation: related-to
target: "adl://public/concepts/x"
mapping_type: domain
confidence: 0.8
```

```adl:evidence
evidence_type: vector_cluster
data_ref: vecdb://x
description: "ok"
confidence: 0.8
observed_at: "2026-05-23T00:00:00Z"
```
"""

    good = bad.replace(
        "That pattern shows it clearly.",
        "The Peripheral Attention Trap pattern appears clearly in AML graph monitoring.",
    )

    def fake_llm(system: str, user: str, model: str | None = None) -> str:
        calls.append(user[:40])
        return bad if len(calls) == 1 else good

    monkeypatch.setenv("MIMO_API_KEY", "tp-test")
    monkeypatch.setattr("experiments.llm_harness.mimo_config", lambda: ("tp-test", "http://localhost/v1", "mimo-v2.5-pro"))
    monkeypatch.setattr("experiments.llm_harness._call_llm", fake_llm)

    from experiments.llm_harness import run_llm_sim

    result = run_llm_sim(output_dir=tmp_path, max_retries=1)
    assert len(calls) == 2
    assert result.detail.get("revised") is True
    assert result.status == "completed"
