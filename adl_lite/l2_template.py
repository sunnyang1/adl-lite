"""L2 Template Schema — structured Markdown body validation.

Survival-path only: Pydantic models, no SHACL, no NLP libraries.

The L2 layer is the Markdown body in ADL documents. This module enforces a
structured three-section template: **Observation**, **Reasoning**, **Conclusion**.

Template mode is declared in YAML front matter via ``l2_template: true``
(relaxed — missing = warning) or ``l2_template: strict`` (strict — missing = error).
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from .exceptions import ADLTemplateError

_RE_SECTION_HEADER = re.compile(
    r"^#{1,6}\s*(Observation|Reasoning|Conclusion)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


class L2Template(BaseModel):
    """Structured L2 Markdown body with three mandatory sections."""

    observation: str = Field(..., description="Empirical observation or evidence")
    reasoning: str = Field(..., description="Reasoning chain or analysis")
    conclusion: str = Field(..., description="Final conclusion or action")

    @classmethod
    def from_markdown(cls, body: str) -> L2Template:
        """Parse a Markdown body and build an ``L2Template``."""
        sections = _parse_sections(body)
        return cls(
            observation=sections.get("observation", ""),
            reasoning=sections.get("reasoning", ""),
            conclusion=sections.get("conclusion", ""),
        )


class L2TemplateValidator:
    """Validate L2 Markdown bodies against the three-section template."""

    @staticmethod
    def parse_sections(body: str) -> dict[str, str]:
        """Extract Observation, Reasoning, and Conclusion sections by Markdown headers."""
        return _parse_sections(body)

    def validate(self, body: str, mode: str = "strict") -> bool:
        """Validate that *body* contains all three non-empty sections.

        Args:
            body: Markdown body text.
            mode: ``"strict"`` raises ``ADLTemplateError`` on failure;
                ``"relaxed"`` (or any other value) returns ``False`` on failure.

        Returns:
            ``True`` if all sections are present and non-empty.

        Raises:
            ADLTemplateError: If *mode* is ``"strict"`` and validation fails.
        """
        sections = _parse_sections(body)
        missing = [
            name for name in ("observation", "reasoning", "conclusion")
            if not sections.get(name)
        ]
        if missing:
            msg = f"Missing or empty L2 sections: {', '.join(missing)}"
            if mode == "strict":
                raise ADLTemplateError(msg)
            return False
        return True


def _parse_sections(body: str) -> dict[str, str]:
    """Extract named sections from a Markdown body using header regex."""
    matches = list(_RE_SECTION_HEADER.finditer(body))
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        name = match.group(1).lower()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        if content:
            sections[name] = content
    return sections


def react_to_l2_template(react_output: dict[str, Any]) -> L2Template:
    """Map a ReAct trajectory dict to an ``L2Template``.

    Keys:
        - ``observation`` → ``observation``
        - ``thought`` → ``reasoning``
        - ``conclusion`` (or ``action`` / ``answer``) → ``conclusion``
    """
    observation = react_output.get("observation", "")
    reasoning = react_output.get("thought", "")
    conclusion = (
        react_output.get("conclusion")
        or react_output.get("action")
        or react_output.get("answer")
        or ""
    )
    return L2Template(observation=observation, reasoning=reasoning, conclusion=conclusion)
