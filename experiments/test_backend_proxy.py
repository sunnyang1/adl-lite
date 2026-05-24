"""Tests for deterministic RQ1 backend proxy (no API keys)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.backend_proxy import (
    RQ1_OUTPUT_SPECS,
    backend_proxy_enabled,
    build_discovery_markdown,
    materialize_rq1_discoveries,
    run_backend_proxy_batch,
    strict_validate_file,
)
from experiments.rq1_batch_discover import run_batch

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "data" / "eval" / "human_rq1_template.json"


def test_build_discovery_markdown_strict_valid(tmp_path):
    md = build_discovery_markdown(
        adl_id="disc-llm-peripheral-trap",
        slug="peripheral-trap",
        batch=None,
    )
    path = tmp_path / "llm_discovery_peripheral-trap.md"
    path.write_text(md, encoding="utf-8")
    ok, errors = strict_validate_file(path)
    assert ok, errors


def test_materialize_all_fifteen_strict_pass(tmp_path):
    summary = materialize_rq1_discoveries(
        output_dir=tmp_path,
        include_plain=True,
        specs=RQ1_OUTPUT_SPECS,
        sync_template=False,
    )
    assert summary["n_strict_pass"] == 15
    assert summary["status"] == "completed"
    assert summary["template_synced"] is False
    assert summary["template_path"] is None
    assert len(list(tmp_path.glob("llm_discovery_*.md"))) == 15


def test_materialize_sync_template_updates_flags(tmp_path):
    template_copy = tmp_path / "template.json"
    template_copy.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")

    summary = materialize_rq1_discoveries(
        output_dir=tmp_path / "out",
        template_path=template_copy,
        specs=RQ1_OUTPUT_SPECS[:1],
        include_plain=False,
        sync_template=True,
    )
    assert summary["template_synced"] is True
    after = json.loads(template_copy.read_text(encoding="utf-8"))
    assert after["entries"][0]["validator_pass"] is True
    assert after["entries"][0].get("discovery_path")


def test_run_backend_proxy_batch_canonical_three(tmp_path):
    summary = run_backend_proxy_batch(
        output_dir=tmp_path,
        regenerate_all=False,
        include_plain=False,
        sync_template=False,
    )
    assert summary["n_target"] == 3
    assert summary["n_strict_pass"] == 3


def test_backend_proxy_env_is_ignored(monkeypatch):
    monkeypatch.setenv("ADL_BACKEND_PROXY", "1")
    with pytest.warns(UserWarning, match="ADL_BACKEND_PROXY is ignored"):
        assert backend_proxy_enabled() is False


def test_run_batch_skips_without_key_or_proxy(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MIMO_API_KEY", raising=False)
    monkeypatch.setenv("ADL_BACKEND_PROXY", "1")
    result = run_batch()
    assert result["status"] == "skipped"


def test_run_batch_proxy_only_when_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MIMO_API_KEY", raising=False)
    result = run_batch(
        output_dir=tmp_path,
        use_backend_proxy=True,
        sync_template=False,
    )
    assert result["provider"] == "backend-proxy"
    assert result["n_strict_pass"] == 3
