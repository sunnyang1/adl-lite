"""Tests for adl_lite.l2_template — L2 structured Markdown body validation.

Covers:
    - L2Template model creation and from_markdown parsing
    - L2TemplateValidator strict/relaxed modes
    - Section extraction with various header levels and casing
    - react_to_l2_template ReAct mapping
    - ADLTemplateError exception hierarchy
"""

from __future__ import annotations

import pytest

from adl_lite.exceptions import ADLError, ADLTemplateError
from adl_lite.l2_template import (
    L2Template,
    L2TemplateValidator,
    _parse_sections,
    react_to_l2_template,
)


class TestL2TemplateModel:
    def test_create_valid(self) -> None:
        t = L2Template(observation="obs", reasoning="rea", conclusion="con")
        assert t.observation == "obs"
        assert t.reasoning == "rea"
        assert t.conclusion == "con"

    def test_create_invalid_missing_field(self) -> None:
        with pytest.raises(Exception):
            L2Template(observation="obs", reasoning="rea")

    def test_from_markdown_full(self) -> None:
        body = (
            "# Observation\n"
            "We saw X.\n"
            "# Reasoning\n"
            "Therefore Y.\n"
            "# Conclusion\n"
            "Do Z."
        )
        t = L2Template.from_markdown(body)
        assert t.observation == "We saw X."
        assert t.reasoning == "Therefore Y."
        assert t.conclusion == "Do Z."

    def test_from_markdown_empty(self) -> None:
        t = L2Template.from_markdown("")
        assert t.observation == ""
        assert t.reasoning == ""
        assert t.conclusion == ""


class TestParseSections:
    def test_basic_extraction(self) -> None:
        body = (
            "# Observation\nObs text\n"
            "# Reasoning\nRea text\n"
            "# Conclusion\nCon text"
        )
        sections = _parse_sections(body)
        assert sections == {
            "observation": "Obs text",
            "reasoning": "Rea text",
            "conclusion": "Con text",
        }

    def test_multi_level_headers(self) -> None:
        body = (
            "## Observation\nObs\n"
            "### Reasoning\nRea\n"
            "#### Conclusion\nCon"
        )
        sections = _parse_sections(body)
        assert set(sections.keys()) == {"observation", "reasoning", "conclusion"}

    def test_case_insensitive(self) -> None:
        body = (
            "# OBSERVATION\nObs\n"
            "# reasoning\nRea\n"
            "# ConClUsIoN\nCon"
        )
        sections = _parse_sections(body)
        assert sections["observation"] == "Obs"
        assert sections["reasoning"] == "Rea"
        assert sections["conclusion"] == "Con"

    def test_empty_section_omitted(self) -> None:
        body = "# Observation\nObs\n# Reasoning\n\n# Conclusion\nCon"
        sections = _parse_sections(body)
        assert "reasoning" not in sections
        assert sections["observation"] == "Obs"
        assert sections["conclusion"] == "Con"

    def test_extra_text_ignored(self) -> None:
        body = (
            "Intro paragraph.\n"
            "# Observation\nObs\n"
            "More obs.\n"
            "# Reasoning\nRea\n"
            "# Conclusion\nCon\n"
            "Footer."
        )
        sections = _parse_sections(body)
        assert sections["observation"] == "Obs\nMore obs."
        assert sections["reasoning"] == "Rea"
        assert sections["conclusion"] == "Con\nFooter."

    def test_reordered_sections(self) -> None:
        body = (
            "# Conclusion\nCon\n"
            "# Observation\nObs\n"
            "# Reasoning\nRea"
        )
        sections = _parse_sections(body)
        assert sections["conclusion"] == "Con"
        assert sections["observation"] == "Obs"
        assert sections["reasoning"] == "Rea"

    def test_no_sections(self) -> None:
        sections = _parse_sections("Just plain markdown.")
        assert sections == {}


class TestL2TemplateValidator:
    def test_valid_body(self) -> None:
        body = (
            "# Observation\nObservation text.\n"
            "## Reasoning\nReasoning text.\n"
            "### Conclusion\nConclusion text."
        )
        validator = L2TemplateValidator()
        assert validator.validate(body) is True

    def test_missing_section_strict(self) -> None:
        body = "# Observation\nObs\n# Reasoning\nRea"
        validator = L2TemplateValidator()
        with pytest.raises(ADLTemplateError, match="Missing or empty L2 sections: conclusion"):
            validator.validate(body, mode="strict")

    def test_missing_section_relaxed(self) -> None:
        body = "# Observation\nObs\n# Reasoning\nRea"
        validator = L2TemplateValidator()
        assert validator.validate(body, mode="relaxed") is False

    def test_multiple_missing_sections_strict(self) -> None:
        body = "# Observation\nObs"
        validator = L2TemplateValidator()
        with pytest.raises(ADLTemplateError, match="Missing or empty L2 sections: reasoning, conclusion"):
            validator.validate(body)

    def test_empty_section_strict(self) -> None:
        body = "# Observation\nObs\n# Reasoning\n\n# Conclusion\nCon"
        validator = L2TemplateValidator()
        with pytest.raises(ADLTemplateError, match="Missing or empty L2 sections: reasoning"):
            validator.validate(body)

    def test_empty_section_relaxed(self) -> None:
        body = "# Observation\nObs\n# Reasoning\n\n# Conclusion\nCon"
        validator = L2TemplateValidator()
        assert validator.validate(body, mode="relaxed") is False

    def test_valid_body_relaxed(self) -> None:
        body = "# Observation\nObs\n# Reasoning\nRea\n# Conclusion\nCon"
        validator = L2TemplateValidator()
        assert validator.validate(body, mode="relaxed") is True

    def test_parse_sections_public_api(self) -> None:
        body = "# Observation\nObs\n# Reasoning\nRea\n# Conclusion\nCon"
        validator = L2TemplateValidator()
        sections = validator.parse_sections(body)
        assert sections["observation"] == "Obs"


class TestReactToL2Template:
    def test_full_mapping(self) -> None:
        react = {
            "observation": "The system crashed.",
            "thought": "Memory leak suspected.",
            "conclusion": "Restart the service.",
        }
        t = react_to_l2_template(react)
        assert t.observation == "The system crashed."
        assert t.reasoning == "Memory leak suspected."
        assert t.conclusion == "Restart the service."

    def test_fallback_action(self) -> None:
        react = {
            "observation": "Obs",
            "thought": "Tho",
            "action": "Act",
        }
        t = react_to_l2_template(react)
        assert t.conclusion == "Act"

    def test_fallback_answer(self) -> None:
        react = {
            "observation": "Obs",
            "thought": "Tho",
            "answer": "Ans",
        }
        t = react_to_l2_template(react)
        assert t.conclusion == "Ans"

    def test_conclusion_priority_over_action(self) -> None:
        react = {
            "observation": "Obs",
            "thought": "Tho",
            "conclusion": "Con",
            "action": "Act",
        }
        t = react_to_l2_template(react)
        assert t.conclusion == "Con"

    def test_empty_dict(self) -> None:
        t = react_to_l2_template({})
        assert t.observation == ""
        assert t.reasoning == ""
        assert t.conclusion == ""

    def test_partial_dict(self) -> None:
        t = react_to_l2_template({"observation": "Obs"})
        assert t.observation == "Obs"
        assert t.reasoning == ""
        assert t.conclusion == ""


class TestADLTemplateError:
    def test_is_adl_error(self) -> None:
        assert issubclass(ADLTemplateError, ADLError)

    def test_raise_and_catch(self) -> None:
        with pytest.raises(ADLTemplateError, match="template issue"):
            raise ADLTemplateError("template issue")
