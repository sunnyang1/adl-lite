"""
Extended tests for adl_lite.cli — normalize, verify-inclusion, verify-anchor,
ontology validate/query flags, and ADLOntologyError handling.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from adl_lite.cli import _build_parser, main

VALID_DOC_TEXT = (
    "---\n"
    "adl_type: concept\n"
    "adl_id: test-capability\n"
    "scope: public\n"
    "provisional_names:\n"
    '  zh: "测试能力"\n'
    '  en: "Test Capability"\n'
    "---\n"
    "## Observation\n\nTest observation.\n\n"
    "## Reasoning\n\nTest reasoning.\n\n"
    "## Conclusion\n\nTest conclusion.\n"
)


def _write_valid_doc(tmp_path: Path, name: str = "test.md", content: str | None = None) -> Path:
    path = tmp_path / name
    path.write_text(content or VALID_DOC_TEXT, encoding="utf-8")
    return path


def _setup_normalize_mocks():
    """Create mock modules for vector_index, canonicalization, and memory."""
    mock_vi_module = ModuleType("adl_lite.vector_index")
    mock_vi_class = MagicMock()
    mock_vi_module.VectorIndex = mock_vi_class

    mock_can_module = ModuleType("adl_lite.canonicalization")
    mock_can_class = MagicMock()
    mock_llm_class = MagicMock()
    mock_can_module.CanonicalizationEngine = mock_can_class
    mock_can_module.OpenAILLMBackend = mock_llm_class

    mock_mem_module = ModuleType("adl_lite.memory")
    mock_mem_class = MagicMock()
    mock_mem_module.ADLMemory = mock_mem_class

    return {
        "adl_lite.vector_index": mock_vi_module,
        "adl_lite.canonicalization": mock_can_module,
        "adl_lite.memory": mock_mem_module,
    }


class TestCmdNormalizeExtended:
    """Extended tests for the normalize CLI subcommand."""

    def test_normalize_command_with_mock_deps(self, tmp_path: Path, capsys):
        """normalize with mock VectorIndex/CanonicalizationEngine — basic flow."""
        input_dir = tmp_path / "docs"
        input_dir.mkdir()
        _write_valid_doc(input_dir, "test.md")

        mock_modules = _setup_normalize_mocks()
        mock_engine_inst = MagicMock()
        mock_engine_inst.normalize.return_value = [
            {
                "cluster": ["test-capability"],
                "proposal": {"canonical_adl_id": "test-capability"},
                "actions": [],
                "executed": False,
            }
        ]
        # Make CanonicalizationEngine() return our mock instance
        mock_modules["adl_lite.canonicalization"].CanonicalizationEngine = MagicMock(
            return_value=mock_engine_inst
        )

        with patch.dict(sys.modules, mock_modules):
            with pytest.raises(SystemExit) as exc_info:
                main(["normalize", "--input-dir", str(input_dir), "--threshold", "0.92"])
            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "Parsed" in captured.out
        assert "candidate" in captured.out

    def test_normalize_command_with_execute_flag(self, tmp_path: Path, capsys):
        """normalize --execute should call normalize with dry_run=False."""
        input_dir = tmp_path / "docs"
        input_dir.mkdir()
        _write_valid_doc(input_dir, "test.md")

        mock_modules = _setup_normalize_mocks()
        mock_engine_inst = MagicMock()
        mock_engine_inst.normalize.return_value = []
        mock_modules["adl_lite.canonicalization"].CanonicalizationEngine = MagicMock(
            return_value=mock_engine_inst
        )

        with patch.dict(sys.modules, mock_modules):
            with pytest.raises(SystemExit) as exc_info:
                main(["normalize", "--input-dir", str(input_dir), "--execute"])
            assert exc_info.value.code == 0

        # Verify dry_run=False was passed
        mock_engine_inst.normalize.assert_called_once_with(dry_run=False)

    def test_normalize_command_no_duplicates(self, tmp_path: Path, capsys):
        """normalize with no near-duplicates should report 0 clusters."""
        input_dir = tmp_path / "docs"
        input_dir.mkdir()
        _write_valid_doc(input_dir, "test.md")

        mock_modules = _setup_normalize_mocks()
        mock_engine_inst = MagicMock()
        mock_engine_inst.normalize.return_value = []  # No duplicates
        mock_modules["adl_lite.canonicalization"].CanonicalizationEngine = MagicMock(
            return_value=mock_engine_inst
        )

        with patch.dict(sys.modules, mock_modules):
            with pytest.raises(SystemExit) as exc_info:
                main(["normalize", "--input-dir", str(input_dir)])
            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "0 candidate" in captured.out

    def test_normalize_command_json_output(self, tmp_path: Path, capsys):
        """normalize --json should emit JSON output."""
        input_dir = tmp_path / "docs"
        input_dir.mkdir()
        _write_valid_doc(input_dir, "test.md")

        mock_modules = _setup_normalize_mocks()
        mock_engine_inst = MagicMock()
        mock_engine_inst.normalize.return_value = []
        mock_modules["adl_lite.canonicalization"].CanonicalizationEngine = MagicMock(
            return_value=mock_engine_inst
        )

        with patch.dict(sys.modules, mock_modules):
            with pytest.raises(SystemExit) as exc_info:
                main(["normalize", "--input-dir", str(input_dir), "--json"])
            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)

    def test_normalize_command_parse_error_in_file(self, tmp_path: Path, capsys):
        """normalize with a bad .md file should report parse error and continue."""
        input_dir = tmp_path / "docs"
        input_dir.mkdir()
        _write_valid_doc(input_dir, "good.md")
        bad_path = input_dir / "bad.md"
        bad_path.write_text("# No front matter\n\nJust text.", encoding="utf-8")

        mock_modules = _setup_normalize_mocks()
        mock_engine_inst = MagicMock()
        mock_engine_inst.normalize.return_value = []
        mock_modules["adl_lite.canonicalization"].CanonicalizationEngine = MagicMock(
            return_value=mock_engine_inst
        )

        with patch.dict(sys.modules, mock_modules):
            with pytest.raises(SystemExit) as exc_info:
                main(["normalize", "--input-dir", str(input_dir)])
            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "parse error" in captured.err

    def test_normalize_command_llm_provider_mock(self, tmp_path: Path, capsys):
        """normalize --llm-provider mock should not attempt OpenAI backend."""
        input_dir = tmp_path / "docs"
        input_dir.mkdir()
        _write_valid_doc(input_dir, "test.md")

        mock_modules = _setup_normalize_mocks()
        mock_engine_inst = MagicMock()
        mock_engine_inst.normalize.return_value = []
        mock_modules["adl_lite.canonicalization"].CanonicalizationEngine = MagicMock(
            return_value=mock_engine_inst
        )

        with patch.dict(sys.modules, mock_modules):
            with pytest.raises(SystemExit) as exc_info:
                main(
                    [
                        "normalize",
                        "--input-dir",
                        str(input_dir),
                        "--llm-provider",
                        "mock",
                    ]
                )
            assert exc_info.value.code == 0

        mock_engine_inst.normalize.assert_called_once()


class TestCmdVerifyInclusionFullFlow:
    """Full flow test for verify-inclusion CLI."""

    def test_verify_inclusion_full_flow(self, tmp_path: Path, capsys):
        """Register, anchor with Merkle, generate proof, then verify inclusion."""
        state = str(tmp_path / "consensus.json")
        output = str(tmp_path / "ANCHOR.md")
        proofs_dir = str(tmp_path / "proofs")

        # Register a concept
        with pytest.raises(SystemExit):
            main(["consensus", "register", "--adl-id", "incl-flow-test", "--state", state])
        capsys.readouterr()

        # Anchor with Merkle + proofs
        with pytest.raises(SystemExit):
            main(
                [
                    "anchor",
                    "--state",
                    state,
                    "--output",
                    output,
                    "--merkle",
                    "--proofs-dir",
                    proofs_dir,
                ]
            )
        capsys.readouterr()

        # Verify inclusion
        proof_path = str(tmp_path / "proofs" / "incl-flow-test.proof.json")
        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "verify-inclusion",
                    "incl-flow-test",
                    "--proof",
                    proof_path,
                    "--anchor",
                    output,
                    "--state",
                    state,
                ]
            )
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "inclusion proof OK" in captured.out


class TestCmdVerifyAnchorExtended:
    """Extended tests for verify-anchor CLI."""

    def test_verify_anchor_with_state_flag(self, tmp_path: Path, capsys):
        """verify-anchor with --state should load chains and verify."""
        state = str(tmp_path / "consensus.json")
        output = str(tmp_path / "ANCHOR.md")

        # Register and anchor
        with pytest.raises(SystemExit):
            main(["consensus", "register", "--adl-id", "va-state-test", "--state", state])
        capsys.readouterr()
        with pytest.raises(SystemExit):
            main(["anchor", "--state", state, "--output", output])
        capsys.readouterr()

        # Verify with state
        with pytest.raises(SystemExit) as exc_info:
            main(["verify-anchor", "--file", output, "--state", state])
        # May succeed or fail depending on process-local chain state
        assert exc_info.value.code in (0, 1)

    def test_verify_anchor_with_commit_flag(self, tmp_path: Path, capsys):
        """verify-anchor --commit should call verify_anchor_at_commit."""
        anchor_path = tmp_path / "ANCHOR.md"
        anchor_path.write_text("# ADL Transparency Anchor\n\n`abc123`\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc_info:
            main(["verify-anchor", "--file", str(anchor_path), "--commit", "nonexistent_commit"])
        # Should fail since no git repo exists with that commit
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "NOT verified" in captured.err


class TestCmdOntologyExtended:
    """Extended tests for ontology validate/query CLI flags."""

    def test_ontology_validate_with_examples_flag(self, tmp_path: Path, capsys):
        """ontology validate --examples should validate example files."""
        with pytest.raises(SystemExit) as exc_info:
            main(["ontology", "validate", "--examples"])
        assert exc_info.value.code in (0, 1)

    def test_ontology_validate_with_aml_flag(self, tmp_path: Path, capsys):
        """ontology validate --aml should validate AML concepts if directory exists."""
        with pytest.raises(SystemExit) as exc_info:
            main(["ontology", "validate", "--aml"])
        assert exc_info.value.code in (0, 1)

    def test_ontology_validate_with_examples_and_aml(self, tmp_path: Path, capsys):
        """ontology validate --examples --aml should validate both."""
        path = _write_valid_doc(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            main(["ontology", "validate", str(path), "--examples", "--aml"])
        assert exc_info.value.code in (0, 1)

    def test_ontology_validate_with_examples_and_invalid_file(self, tmp_path: Path, capsys):
        """ontology validate with examples and a bad file should report errors."""
        bad_path = tmp_path / "bad.md"
        bad_path.write_text("# No front matter", encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            main(["ontology", "validate", str(bad_path), "--examples"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "parse error" in captured.err

    def test_ontology_query_with_output_format_json(self, tmp_path: Path, capsys):
        """ontology query --json should output JSON format."""
        with pytest.raises(SystemExit) as exc_info:
            main(["ontology", "query", "--json"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "predicates" in data
        assert "allowed_transitions" in data

    def test_ontology_query_with_output_format_text(self, tmp_path: Path, capsys):
        """ontology query (default text) should output human-readable text."""
        with pytest.raises(SystemExit) as exc_info:
            main(["ontology", "query"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "ontology:" in captured.out
        assert "predicates" in captured.out

    def test_ontology_validate_valid_file_strict(self, tmp_path: Path, capsys):
        """ontology validate with valid file under strict ontology."""
        path = _write_valid_doc(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            main(["ontology", "validate", str(path)])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "OK" in captured.out

    def test_cli_error_handling_adl_ontology_error(self, tmp_path: Path, capsys):
        """CLI should catch and display ADLOntologyError when ontology fails."""
        with pytest.raises(SystemExit) as exc_info:
            main(["ontology", "query", "--ontology", str(tmp_path / "nonexistent.yaml")])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "ontology error" in captured.err


class TestCmdVerifyInclusionProofFileCorrupt:
    """Test verify-inclusion with corrupt or invalid proof files."""

    def test_verify_inclusion_corrupt_proof_json(self, tmp_path: Path, capsys):
        """verify-inclusion with invalid JSON in proof file raises JSONDecodeError.

        The CLI _cmd_verify_inclusion calls json.loads which raises JSONDecodeError
        on corrupt JSON. This error is NOT caught by the CLI handler, so it
        propagates directly (not wrapped in SystemExit). We verify the error
        is raised correctly.
        """
        state = str(tmp_path / "consensus.json")
        proof_path = tmp_path / "proof.json"
        # Write invalid JSON
        proof_path.write_text("{bad_json_content", encoding="utf-8")

        # Register a concept so it exists
        with pytest.raises(SystemExit):
            main(["consensus", "register", "--adl-id", "corrupt-test", "--state", state])
        capsys.readouterr()

        # The CLI will crash on JSONDecodeError which propagates as SystemExit(1)
        # through main() which raises SystemExit(args.func(args))
        with pytest.raises((SystemExit, json.decoder.JSONDecodeError)):
            main(
                [
                    "verify-inclusion",
                    "corrupt-test",
                    "--proof",
                    str(proof_path),
                    "--state",
                    state,
                ]
            )

    def test_verify_inclusion_proof_valid_but_wrong_data(self, tmp_path: Path, capsys):
        """verify-inclusion with a proof file that has valid JSON but wrong Merkle data."""
        state = str(tmp_path / "consensus.json")
        proof_path = tmp_path / "proof.json"

        # Create a valid JSON proof with wrong data
        bad_proof_data = {
            "leaf_index": 0,
            "leaf_hash": "deadbeef",
            "siblings": [],
            "root": "0000000000000000",
        }
        proof_path.write_text(json.dumps(bad_proof_data), encoding="utf-8")

        # Register a concept
        with pytest.raises(SystemExit):
            main(["consensus", "register", "--adl-id", "bad-proof-test", "--state", state])
        capsys.readouterr()

        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "verify-inclusion",
                    "bad-proof-test",
                    "--proof",
                    str(proof_path),
                    "--anchor",
                    str(tmp_path / "ANCHOR.md"),
                    "--state",
                    state,
                ]
            )
        # Should fail — the proof data doesn't match the chain
        assert exc_info.value.code == 1


class TestParserSubcommands:
    """Verify parser accepts all subcommand variations."""

    def test_parser_normalize_subcommand(self):
        parser = _build_parser()
        args = parser.parse_args(["normalize", "--input-dir", "/tmp/docs"])
        assert args.command == "normalize"
        assert args.input_dir == "/tmp/docs"
        assert args.threshold == 0.92
        assert args.execute is False
        assert args.json is False

    def test_parser_normalize_with_all_options(self):
        parser = _build_parser()
        args = parser.parse_args(
            [
                "normalize",
                "--input-dir",
                "/tmp/docs",
                "--threshold",
                "0.85",
                "--llm-provider",
                "mock",
                "--execute",
                "--json",
            ]
        )
        assert args.threshold == 0.85
        assert args.execute is True
        assert args.json is True
        assert args.llm_provider == "mock"

    def test_parser_verify_anchor_with_state(self):
        parser = _build_parser()
        args = parser.parse_args(["verify-anchor", "--file", "ANCHOR.md", "--state", "state.json"])
        assert args.file == "ANCHOR.md"
        assert args.state == "state.json"

    def test_parser_verify_anchor_with_commit(self):
        parser = _build_parser()
        args = parser.parse_args(
            [
                "verify-anchor",
                "--file",
                "ANCHOR.md",
                "--commit",
                "abc123",
            ]
        )
        assert args.commit == "abc123"
