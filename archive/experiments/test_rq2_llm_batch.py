"""RQ2 LLM batch analysis tests (mock only, no API)."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.rq2_llm_batch import (
    aggregate_results,
    analyze_log,
    build_summary,
    mock_llm_result,
    parse_llm_log,
    run_batch,
    write_summary,
)


def test_parse_llm_log_extracts_results(tmp_path):
    log = tmp_path / "llm_run.jsonl"
    log.write_text(
        json.dumps({"result": {"status": "completed", "consensus_transitions": 2, "attempts": 1, "revised": False}})
        + "\n"
        + json.dumps({"step": 1, "role": "discoverer", "action": "emit_llm"})
        + "\n"
        + json.dumps({"result": {"status": "validation_failed", "consensus_transitions": 0, "attempts": 2, "revised": True}})
        + "\n",
        encoding="utf-8",
    )
    results = parse_llm_log(log)
    assert len(results) == 2
    assert results[0]["status"] == "completed"
    assert results[1]["revised"] is True


def test_aggregate_results_metrics():
    results = [
        {"status": "completed", "consensus_transitions": 2, "attempts": 1, "revised": False},
        {"status": "completed", "consensus_transitions": 2, "attempts": 2, "revised": True},
        {"status": "validation_failed", "consensus_transitions": 0, "attempts": 2, "revised": True},
    ]
    agg = aggregate_results(results)
    assert agg["n_runs"] == 3
    assert agg["consensus_transitions"]["mean"] == 4 / 3
    assert agg["success_rate"] == 2 / 3
    assert agg["mean_attempts"] == 5 / 3
    assert abs(agg["revised_rate"] - 2 / 3) < 1e-9


def test_dry_run_batch_writes_log(tmp_path):
    log = tmp_path / "batch.jsonl"
    results = run_batch(n=5, dry_run=True, log_path=log, append_log=True)
    assert len(results) == 5
    parsed = parse_llm_log(log)
    assert len(parsed) == 5
    assert all("status" in r for r in parsed)


def test_build_summary_includes_scripted_baseline():
    results = [
        mock_llm_result().to_dict(),
        mock_llm_result(revised=True, attempts=2).to_dict(),
    ]
    summary = build_summary(results, dry_run=True)
    assert summary["rq"] == "RQ2"
    assert summary["llm"]["n_runs"] == 2
    assert "scripted_baseline" in summary
    assert summary["scripted_baseline"]["consensus_transitions"] >= 0
    assert "comparison" in summary


def test_analyze_only_from_log(tmp_path):
    log = tmp_path / "llm_run.jsonl"
    run_batch(n=3, dry_run=True, log_path=log)
    summary = analyze_log(log)
    assert summary["llm"]["n_runs"] == 3
    assert summary["dry_run"] is False


def test_write_summary(tmp_path):
    summary = build_summary([mock_llm_result().to_dict()], dry_run=True)
    out = write_summary(summary, tmp_path / "rq2_llm_summary.json")
    assert out.exists()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["rq"] == "RQ2"


def test_main_dry_run_cli(tmp_path, capsys):
    from experiments.rq2_llm_batch import main

    log = tmp_path / "llm_run.jsonl"
    out = tmp_path / "summary.json"
    main(["--n", "2", "--dry-run", "--log", str(log), "--out", str(out)])
    captured = capsys.readouterr()
    assert "written:" in captured.out
    assert out.exists()
