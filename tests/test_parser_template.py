"""Tests for L2 template validation integration in ADLParser."""

from __future__ import annotations

from pathlib import Path

import pytest

from adl_lite.cli import main
from adl_lite.exceptions import ADLParseError, ADLTemplateError
from adl_lite.parser import ADLParser, parse_file, parse_text


def _make_doc(l2_template: str | bool | None = None, sections: tuple[str, ...] = ()) -> str:
    """Build a minimal ADL Markdown document."""
    fm_lines = [
        "adl_type: concept",
        "adl_id: test-concept",
        "scope: public",
    ]
    if l2_template is not None:
        fm_lines.append(f"l2_template: {l2_template}")

    front = "---\n" + "\n".join(fm_lines) + "\n---\n"
    body = "\n\n".join(f"## {s}\nContent for {s.lower()}." for s in sections)
    return front + body


class TestL2TemplateParser:
    def test_valid_template_strict_parser(self):
        """All 3 sections present with l2_template: true → parse succeeds."""
        text = _make_doc(l2_template=True, sections=("Observation", "Reasoning", "Conclusion"))
        doc = parse_text(text)
        assert doc.front_matter.l2_template is True
        assert "Observation" in doc.markdown_body

    def test_valid_template_strict_flag(self):
        """All 3 sections present with --strict-template flag → parse succeeds."""
        text = _make_doc(sections=("Observation", "Reasoning", "Conclusion"))
        doc = ADLParser(strict_template=True).parse_text(text)
        assert doc.front_matter.l2_template is None

    def test_missing_section_l2_template_true(self):
        """Missing section with l2_template: true → raises ADLTemplateError."""
        text = _make_doc(l2_template=True, sections=("Observation", "Conclusion"))
        with pytest.raises(ADLTemplateError):
            parse_text(text)

    def test_missing_section_strict_template_flag(self):
        """Missing section with --strict-template flag → raises ADLTemplateError."""
        text = _make_doc(sections=("Observation", "Conclusion"))
        with pytest.raises(ADLTemplateError):
            ADLParser(strict_template=True).parse_text(text)

    def test_missing_section_no_strict(self):
        """Missing section without strict flag or l2_template → parse succeeds."""
        text = _make_doc(sections=("Observation", "Conclusion"))
        doc = parse_text(text)
        assert doc.front_matter.adl_id == "test-concept"

    def test_l2_template_false_with_strict_flag(self):
        """l2_template: false should skip validation even with strict_template=True."""
        text = _make_doc(l2_template=False, sections=("Observation",))
        doc = ADLParser(strict_template=True).parse_text(text)
        assert doc.front_matter.l2_template is False

    def test_l2_template_relaxed_skips_validation(self):
        """l2_template: relaxed should skip strict validation."""
        text = _make_doc(l2_template="relaxed", sections=("Observation",))
        doc = parse_text(text)
        assert doc.front_matter.l2_template == "relaxed"

    def test_backward_compat_no_l2_template(self):
        """Documents without l2_template field parse unchanged."""
        text = _make_doc(sections=("Observation", "Reasoning", "Conclusion"))
        doc = parse_text(text)
        assert doc.front_matter.l2_template is None
        assert doc.front_matter.adl_id == "test-concept"

    def test_parse_with_l3_blocks(self):
        """Parsing a document with L3 blocks covers _dispatch_block and _extract_adl_blocks."""
        text = (
            "---\n"
            "adl_type: concept\n"
            "adl_id: test-l3\n"
            "scope: public\n"
            "---\n"
            "## Observation\n\n"
            "Some observation.\n\n"
            "```adl:relation\n"
            "source: a\n"
            "relation: isomorphic-to\n"
            "target: b\n"
            "```\n\n"
            "## Reasoning\n\n"
            "Some reasoning.\n\n"
            "## Conclusion\n\n"
            "Final conclusion.\n"
        )
        doc = parse_text(text)
        assert len(doc.relations) == 1
        assert doc.relations[0].source == "a"

    def test_parse_with_action_block(self):
        """Parsing a document with L4 action blocks covers _parse_action_block."""
        text = (
            "---\n"
            "adl_type: concept\n"
            "adl_id: test-action\n"
            "scope: public\n"
            "---\n"
            "## Observation\n\n"
            "Obs.\n\n"
            "## Reasoning\n\n"
            "Reason.\n\n"
            "## Conclusion\n\n"
            "Conclusion.\n\n"
            "```adl:action\n"
            "action: validate\n"
            "actor: agent_1\n"
            "reasoning: test\n"
            "param_confidence: 0.9\n"
            "```\n"
        )
        doc = parse_text(text)
        assert len(doc.actions) == 1
        assert doc.actions[0].action == "validate"
        assert doc.actions[0].params.get("confidence") == "0.9"

    def test_extract_wiki_links(self):
        """extract_wiki_links covers the wiki-link regex."""
        from adl_lite.parser import extract_wiki_links

        links = extract_wiki_links("See [[Concept A]] and [[Concept B|alias]].")
        assert links == ["Concept A", "Concept B"]

    def test_parse_file_no_front_matter(self, tmp_path: Path):
        """parse_file without front matter falls through _split_front_matter."""
        text = "# Just markdown\n\nNo front matter here."
        path = tmp_path / "no_fm.md"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(ADLParseError):
            parse_file(path)

    def test_parse_file_strict_template(self, tmp_path: Path):
        """parse_file with strict_template=True enforces L2 template."""
        text = _make_doc(sections=("Observation", "Conclusion"))
        path = tmp_path / "test.md"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(ADLTemplateError):
            parse_file(path, strict_template=True)

    def test_parse_file_valid_template(self, tmp_path: Path):
        """parse_file with strict_template=True succeeds for valid template."""
        text = _make_doc(sections=("Observation", "Reasoning", "Conclusion"))
        path = tmp_path / "test.md"
        path.write_text(text, encoding="utf-8")
        doc = parse_file(path, strict_template=True)
        assert doc.front_matter.adl_id == "test-concept"

    def test_cli_parse_strict_template(self, tmp_path: Path, capsys):
        """CLI --strict-template flag raises error on missing section."""
        text = _make_doc(sections=("Observation", "Conclusion"))
        path = tmp_path / "test.md"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            main(["--strict-template", "parse", str(path)])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Missing or empty L2 sections" in captured.err

    def test_cli_parse_strict_template_valid(self, tmp_path: Path, capsys):
        """CLI --strict-template flag succeeds on valid template."""
        text = _make_doc(sections=("Observation", "Reasoning", "Conclusion"))
        path = tmp_path / "test.md"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            main(["--strict-template", "parse", str(path)])
        assert exc_info.value.code == 0

    def test_cli_parse_no_strict_template(self, tmp_path: Path, capsys):
        """Without --strict-template, bad template parses successfully."""
        text = _make_doc(sections=("Observation", "Conclusion"))
        path = tmp_path / "test.md"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            main(["parse", str(path)])
        assert exc_info.value.code == 0
