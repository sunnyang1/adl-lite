"""
ADL-Lark bridge tests (mocked lark-cli subprocess).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from adl_lite.consensus import ConsensusEngine
from adl_lite.lark.announce import announce
from adl_lite.lark.client import LarkCliError, LarkCliNotFoundError, find_lark_cli
from adl_lite.lark.dashboard import init_dashboard, sync_dashboard_row
from adl_lite.lark.listen import listen, parse_feedback_lines
from adl_lite.lark.namespace import (
    LarkNamespaceRegistry,
    resolve_wiki_space_for_scope,
    scope_to_adl_uri,
)
from adl_lite.lark.publish import _content_file_ref, _strip_leading_h1, publish_file
from adl_lite.lark.registry import LarkRegistry
from adl_lite.lark.sync_memory import iter_warm_records, sync_memory
from adl_lite.lark.templates import render_template
from adl_lite.memory import ADLMemory
from adl_lite.models import DiscoveryStatus
from adl_lite.parser import parse_file

ROOT = Path(__file__).resolve().parents[1]
CAPITAL = ROOT / "examples" / "capital_reflux_trap.md"


def test_find_lark_cli_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(LarkCliNotFoundError):
        find_lark_cli()


def test_publish_builds_create_argv(tmp_path: Path):
    registry_path = tmp_path / "lark_registry.json"
    payload = {
        "ok": True,
        "data": {
            "doc_id": "doxcnTEST123",
            "doc_url": "https://example.feishu.cn/docx/doxcnTEST123",
        },
    }

    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(payload)
        mock_run.return_value.stderr = ""

        result = publish_file(
            CAPITAL,
            lark_cli="/usr/local/bin/lark-cli",
            registry=LarkRegistry(registry_path),
        )

    assert result.adl_id == "disc-capital-trap"
    assert result.doc_id == "doxcnTEST123"
    assert "doxcnTEST123" in result.doc_url

    argv = mock_run.call_args[0][0]
    assert argv[0] == "/usr/local/bin/lark-cli"
    assert argv[1:4] == ["docs", "+create", "--api-version"]
    assert argv[4] == "v2"
    assert "--doc-format" in argv
    assert argv[argv.index("--doc-format") + 1] == "markdown"
    assert "--content" in argv
    content_idx = argv.index("--content")
    assert argv[content_idx + 1].startswith("@")
    assert "examples/capital_reflux_trap.md" in argv[content_idx + 1]
    assert "--markdown" not in argv

    reg = LarkRegistry(registry_path).get("disc-capital-trap")
    assert reg is not None
    assert reg["doc_id"] == "doxcnTEST123"


def test_publish_v1_uses_markdown_and_title(tmp_path: Path):
    payload = {
        "ok": True,
        "data": {"doc_id": "dox1", "doc_url": "https://example/docx/dox1"},
    }

    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(payload)
        mock_run.return_value.stderr = ""

        publish_file(
            CAPITAL,
            api_version="v1",
            lark_cli="/usr/local/bin/lark-cli",
        )

    argv = mock_run.call_args[0][0]
    assert argv[argv.index("--api-version") + 1] == "v1"
    assert "--markdown" in argv
    assert "--title" in argv
    assert "--content" not in argv
    md_idx = argv.index("--markdown")
    assert "examples/capital_reflux_trap.md" in argv[md_idx + 1]


def test_publish_v2_maps_wiki_space_to_parent_token(tmp_path: Path):
    payload = {
        "ok": True,
        "data": {"doc_id": "dox1", "doc_url": "https://example/docx/dox1"},
    }

    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(payload)
        mock_run.return_value.stderr = ""

        publish_file(
            CAPITAL,
            wiki_space="aml_wiki_space",
            lark_cli="/usr/local/bin/lark-cli",
        )

    argv = mock_run.call_args[0][0]
    idx = argv.index("--parent-token")
    assert argv[idx + 1] == "aml_wiki_space"
    assert "--wiki-space" not in argv


def test_publish_resolves_wiki_space_from_namespace(tmp_path: Path):
    ns_path = tmp_path / "namespaces.json"
    LarkNamespaceRegistry(ns_path).set_mapping(
        "adl://private/ceiec-aml/",
        "aml_wiki_space",
    )
    payload = {
        "ok": True,
        "data": {"doc_id": "dox1", "doc_url": "https://example/docx/dox1"},
    }

    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(payload)
        mock_run.return_value.stderr = ""

        publish_file(
            CAPITAL,
            lark_cli="/usr/local/bin/lark-cli",
            namespaces_path=ns_path,
        )

    argv = mock_run.call_args[0][0]
    idx = argv.index("--parent-token")
    assert argv[idx + 1] == "aml_wiki_space"


def test_strip_leading_h1_after_front_matter():
    raw = "---\nadl_id: x\n---\n\n# Old\n\npara\n"
    out = _strip_leading_h1(raw)
    assert "# Old" not in out
    assert "para" in out
    assert out.startswith("---")


def test_content_file_ref_explicit_title_v2(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(ROOT)
    adl = tmp_path / "sample.md"
    adl.write_text(
        "---\nadl_id: test-id\n---\n\n# Old Title\n\nBody text.\n",
        encoding="utf-8",
    )
    ref, tmp = _content_file_ref(
        adl,
        api_version="v2",
        doc_title="New Title",
        explicit_title=True,
    )
    try:
        staged = ROOT / ref[1:]
        text = staged.read_text(encoding="utf-8")
        assert text.startswith("# New Title")
        assert "# Old Title" not in text
        assert "Body text." in text
    finally:
        if tmp is not None:
            tmp.cleanup()


def test_publish_dry_run_skips_registry(tmp_path: Path):
    registry_path = tmp_path / "lark_registry.json"
    payload = {"ok": True, "dry_run": True}

    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(payload)
        mock_run.return_value.stderr = ""

        result = publish_file(
            CAPITAL,
            dry_run=True,
            lark_cli="/usr/local/bin/lark-cli",
            registry=LarkRegistry(registry_path),
        )

    assert result.dry_run is True
    assert not registry_path.exists()
    argv = mock_run.call_args[0][0]
    assert "--dry-run" in argv


def test_publish_raises_on_lark_error():
    payload = {
        "ok": False,
        "error": {"type": "config", "message": "not configured"},
    }

    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 2
        mock_run.return_value.stdout = json.dumps(payload)
        mock_run.return_value.stderr = ""

        with pytest.raises(LarkCliError, match="not configured"):
            publish_file(CAPITAL, lark_cli="/usr/local/bin/lark-cli")


def test_namespace_resolve_longest_prefix():
    assert scope_to_adl_uri("private/ceiec-aml") == "adl://private/ceiec-aml/"
    mappings = {
        "adl://private/": "generic_private",
        "adl://private/ceiec-aml/": "aml_space",
    }
    hit = resolve_wiki_space_for_scope(
        "private/ceiec-aml",
        registry_data={"namespaces": mappings},
    )
    assert hit == "aml_space"


def test_sync_memory_upsert_argv(tmp_path: Path):
    db = tmp_path / "mem.db"
    reg_path = tmp_path / "registry.json"
    reg = LarkRegistry(reg_path)
    reg.set_base_token("AML概念知识库", "bascnTEST")

    mem = ADLMemory(db_path=str(db))
    mem.store(parse_file(CAPITAL))
    mem.close()

    search_payload = {"ok": True, "data": {"items": []}}
    upsert_payload = {"ok": True, "data": {"record_id": "recNEW"}}

    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        mock_run.return_value.stdout = json.dumps(search_payload)

        def side_effect(cmd, **kwargs):
            proc = mock_run.return_value
            if "+record-upsert" in cmd:
                proc.stdout = json.dumps(upsert_payload)
            else:
                proc.stdout = json.dumps(search_payload)
            return proc

        mock_run.side_effect = lambda *a, **k: side_effect(a[0])

        result = sync_memory(
            str(db),
            base="AML概念知识库",
            mode="warm",
            table="concepts",
            registry_path=reg_path,
            lark_cli="/usr/local/bin/lark-cli",
        )

    assert result.synced == 1
    assert result.created == 1
    calls = [c[0][0] for c in mock_run.call_args_list]
    upsert_calls = [c for c in calls if "+record-upsert" in c]
    assert len(upsert_calls) == 1
    assert "bascnTEST" in upsert_calls[0]
    json_idx = upsert_calls[0].index("--json")
    fields = json.loads(upsert_calls[0][json_idx + 1])
    assert fields["adl_id"] == "disc-capital-trap"


def test_iter_warm_records_no_raw_json(tmp_path: Path):
    db = tmp_path / "mem.db"
    mem = ADLMemory(db_path=str(db))
    mem.store(parse_file(CAPITAL))
    rows = iter_warm_records(mem)
    mem.close()
    assert len(rows) == 1
    assert rows[0].adl_id == "disc-capital-trap"
    assert rows[0].scope == "private/ceiec-aml"


def test_announce_sends_markdown(tmp_path: Path):
    payload = {"ok": True, "data": {"message_id": "om_test"}}
    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(payload)
        mock_run.return_value.stderr = ""

        result = announce(
            str(CAPITAL),
            chat_id="oc_test_chat",
            lark_cli="/usr/local/bin/lark-cli",
        )

    assert result.adl_id == "disc-capital-trap"
    argv = mock_run.call_args[0][0]
    assert argv[1:3] == ["im", "+messages-send"]
    assert "--markdown" in argv


def test_listen_auto_transition(tmp_path: Path):
    engine = ConsensusEngine()
    doc = parse_file(CAPITAL)
    engine.register(doc)

    events = parse_feedback_lines(
        [
            "disc-capital-trap|agent_a|LGTM validate",
            "disc-capital-trap|agent_b|approve 👍",
        ]
    )
    from adl_lite.lark.listen import process_consensus_feedback

    result = process_consensus_feedback(
        events,
        engine,
        threshold=2,
        auto_transition=True,
    )
    assert result.endorsements["disc-capital-trap"] == 2
    assert "disc-capital-trap" in result.transitions
    assert engine.get_status("disc-capital-trap") == DiscoveryStatus.VALIDATED


def test_listen_from_stdin_mock(tmp_path: Path):
    engine = ConsensusEngine()
    engine.register(parse_file(CAPITAL))
    fb = tmp_path / "fb.txt"
    fb.write_text("disc-capital-trap|a|validate\n", encoding="utf-8")

    result = listen(feedback_file=fb, engine=engine, auto_transition=False)

    assert len(result.events) == 1
    assert result.endorsements.get("disc-capital-trap") == 1


def test_init_dashboard_create(tmp_path: Path):
    db = tmp_path / "mem.db"
    mem = ADLMemory(db_path=str(db))
    mem.store(parse_file(CAPITAL))
    mem.close()

    payload = {
        "ok": True,
        "data": {"spreadsheet_token": "shtcnTEST", "sheet_id": "sheet1"},
    }
    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(payload)
        mock_run.return_value.stderr = ""

        result = init_dashboard(
            "AML概念共识看板",
            db_path=str(db),
            lark_cli="/usr/local/bin/lark-cli",
            registry_path=tmp_path / "reg.json",
        )

    assert result.spreadsheet_token == "shtcnTEST"
    assert result.sheet_id == "sheet1"
    argv = mock_run.call_args[0][0]
    assert argv[1:3] == ["sheets", "+create"]
    reg = json.loads((tmp_path / "reg.json").read_text(encoding="utf-8"))
    assert reg["dashboards"]["AML概念共识看板"]["sheet_id"] == "sheet1"


def test_init_dashboard_fetches_sheet_id_when_create_omits(tmp_path: Path):
    db = tmp_path / "mem.db"
    mem = ADLMemory(db_path=str(db))
    mem.store(parse_file(CAPITAL))
    mem.close()

    create_payload = {"ok": True, "data": {"spreadsheet_token": "shtcnTEST"}}
    info_payload = {
        "ok": True,
        "data": {"sheets": {"sheets": [{"sheet_id": "sheetFromInfo"}]}},
    }

    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        def side_effect(cmd, **kwargs):
            proc = mock_run.return_value
            if "+info" in cmd:
                proc.stdout = json.dumps(info_payload)
            else:
                proc.stdout = json.dumps(create_payload)
            return proc

        mock_run.side_effect = lambda *a, **k: side_effect(a[0])

        result = init_dashboard(
            "AML概念共识看板",
            db_path=str(db),
            lark_cli="/usr/local/bin/lark-cli",
            registry_path=tmp_path / "reg.json",
        )

    assert result.sheet_id == "sheetFromInfo"
    calls = [c[0][0] for c in mock_run.call_args_list]
    assert any("+info" in c for c in calls)
    reg = json.loads((tmp_path / "reg.json").read_text(encoding="utf-8"))
    assert reg["dashboards"]["AML概念共识看板"]["sheet_id"] == "sheetFromInfo"


def test_sync_dashboard_row_uses_registry_sheet_id(tmp_path: Path):
    db = tmp_path / "mem.db"
    mem = ADLMemory(db_path=str(db))
    mem.store(parse_file(CAPITAL))
    mem.close()

    reg_path = tmp_path / "reg.json"
    reg = LarkRegistry(reg_path)
    reg.save(
        {
            "version": 1,
            "entries": {},
            "dashboards": {
                "AML概念共识看板": {
                    "spreadsheet_token": "shtcnTEST",
                    "sheet_id": "sheet1",
                    "columns": [
                        "concept_id",
                        "status_badge",
                        "confidence",
                        "discoverer",
                        "validators",
                        "last_update",
                        "doc_link",
                    ],
                }
            },
        }
    )

    append_payload = {"ok": True}
    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(append_payload)
        mock_run.return_value.stderr = ""

        sync_dashboard_row(
            "disc-capital-trap",
            sheet_title="AML概念共识看板",
            registry_path=reg_path,
            db_path=str(db),
            lark_cli="/usr/local/bin/lark-cli",
        )

    calls = [c[0][0] for c in mock_run.call_args_list]
    assert len(calls) == 1
    argv = calls[0]
    assert argv[1:3] == ["sheets", "+append"]
    assert argv[argv.index("--sheet-id") + 1] == "sheet1"
    assert argv[argv.index("--range") + 1] == "sheet1!A2:G2"
    assert "+info" not in " ".join(argv)


def test_sync_dashboard_row_resolves_sheet_id_via_info(tmp_path: Path):
    db = tmp_path / "mem.db"
    mem = ADLMemory(db_path=str(db))
    mem.store(parse_file(CAPITAL))
    mem.close()

    reg_path = tmp_path / "reg.json"
    reg = LarkRegistry(reg_path)
    reg.save(
        {
            "version": 1,
            "entries": {},
            "dashboards": {
                "AML概念共识看板": {
                    "spreadsheet_token": "shtcnTEST",
                    "sheet_id": "",
                    "columns": [
                        "concept_id",
                        "status_badge",
                        "confidence",
                        "discoverer",
                        "validators",
                        "last_update",
                        "doc_link",
                    ],
                }
            },
        }
    )

    info_payload = {
        "ok": True,
        "data": {"sheets": {"sheets": [{"sheet_id": "resolvedSheet"}]}},
    }
    append_payload = {"ok": True}

    with patch("adl_lite.lark.client.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        def side_effect(cmd, **kwargs):
            proc = mock_run.return_value
            if "+info" in cmd:
                proc.stdout = json.dumps(info_payload)
            else:
                proc.stdout = json.dumps(append_payload)
            return proc

        mock_run.side_effect = lambda *a, **k: side_effect(a[0])

        sync_dashboard_row(
            "disc-capital-trap",
            sheet_title="AML概念共识看板",
            registry_path=reg_path,
            db_path=str(db),
            lark_cli="/usr/local/bin/lark-cli",
        )

    calls = [c[0][0] for c in mock_run.call_args_list]
    assert any("+info" in c for c in calls)
    append_argv = next(c for c in calls if "+append" in c)
    assert append_argv[append_argv.index("--sheet-id") + 1] == "resolvedSheet"
    assert append_argv[append_argv.index("--range") + 1] == "resolvedSheet!A2:G2"

    reg_data = reg.load()
    assert reg_data["dashboards"]["AML概念共识看板"]["sheet_id"] == "resolvedSheet"


def test_render_template():
    doc = parse_file(CAPITAL)
    body = render_template("discovery_broadcast", doc, doc_url="https://example/doc")
    assert "disc-capital-trap" in body
    assert "https://example/doc" in body
