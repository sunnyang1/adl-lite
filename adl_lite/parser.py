"""
ADL Lite — Parser for Capability Registry Documents

Three standard tools:
    - PyYAML  → Front Matter (L1)
    - regex   → ADL code blocks (L3 & L4)
    - str.split → Markdown body (L2)

Implements the four-layer syntax:
    L1: YAML Front Matter   — identity, type, status, evidence refs, scope
    L2: Markdown Body       — natural language, [[Wiki Links]], lists
    L3: ```adl:* blocks     — relation graphs, evidence chains, formal seals
    L4: ```adl:action       — typed actions with preconditions and side effects

References:
    - ADL Lite Spec §7.2: Three-layer syntax
    - ADL Lite Spec §7.3: Full example
    - ADL Lite Milestone 2d: L4 action blocks
"""

from __future__ import annotations

import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

from .l2_template import L2TemplateValidator
from .logging_config import get_logger
from .models import (
    ActionExecStatus,
    ADLActionBlock,
    ADLBlock,
    ADLDocument,
    ADLEvidenceBlock,
    ADLExecutionBlock,
    ADLFormalSealBlock,
    ADLFrontMatter,
    ADLRelationBlock,
    ADLType,
    DiscoveryStatus,
    EvidenceType,
    MechanismType,
    ProvisionalNames,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for L3 ADL blocks
# ---------------------------------------------------------------------------

# Matches ```adl:<subtype> ... ``` blocks (non-greedy)
_RE_ADL_BLOCK = re.compile(
    r"^```adl:(?P<block_type>\w+)\s*\n" r"(?P<body>.*?)" r"^```",
    re.MULTILINE | re.DOTALL,
)

# Inline YAML inside ADL blocks — key: value pairs
_RE_KV_LINE = re.compile(r"^(\w+):\s*(.+)$", re.MULTILINE)

# Obsidian-style wiki links in L2 body
_RE_WIKI_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


class ADLParser:
    """
    Stateless parser for ADL Lite Markdown documents.

    Usage:
        parser = ADLParser()
        doc = parser.parse_file("examples/capital_reflux_trap.md")
        doc = parser.parse_text(raw_markdown_string)
    """

    # ------------------------------------------------------------------
    # Helper: unquote a string that is wrapped in matching double-quotes
    # ------------------------------------------------------------------

    @staticmethod
    def _unquote(s: str) -> str:
        """Remove ONE pair of matching outer double-quotes, preserving embedded quotes.
        Unlike strip('"'), this does NOT destroy quotes inside the value.
        'He said "hello"' → 'He said "hello"' (no change)
        '"He said "hello""' → 'He said "hello"' (removes outer pair only)
        """
        if s.startswith('"') and s.endswith('"') and len(s) >= 2:
            return s[1:-1]
        return s

    def __init__(self, strict_template: bool = False) -> None:
        if yaml is None:
            raise ImportError("PyYAML is required. Install: pip install pyyaml")
        self.strict_template = strict_template

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_file(self, path: str | Path) -> ADLDocument:
        """Parse an ADL Lite document from a file path."""
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        doc = self.parse_text(text)
        doc.source_path = str(path)
        logger.debug("Parsed ADL document %s from %s", doc.adl_id, path)
        return doc

    def parse_text(self, text: str) -> ADLDocument:
        """
        Parse raw Markdown text into an ADLDocument.

        Algorithm:
            1. Split L1 (YAML Front Matter) from L2+L3 (Body)
            2. Parse YAML → ADLFrontMatter
            3. Extract L3 blocks from body → ADLBlock list
            4. Remove L3 blocks from body → clean L2 Markdown
            5. If l2_template is enabled, validate L2 body structure
        """
        front_matter_raw, body = self._split_front_matter(text)
        fm = self._parse_front_matter(front_matter_raw)
        l3_blocks, action_blocks, clean_body = self._extract_adl_blocks(body)
        doc = ADLDocument(
            front_matter=fm,
            markdown_body=clean_body.strip(),
            adl_blocks=l3_blocks,
            action_blocks=action_blocks,
        )

        # L2 template validation
        l2_val = doc.front_matter.l2_template
        if isinstance(l2_val, str):
            l2_val = l2_val.lower().strip()

        if l2_val not in (False, "false"):
            if self.strict_template or l2_val in (True, "true", "strict"):
                validator = L2TemplateValidator()
                validator.validate(doc.markdown_body, mode="strict")

        return doc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_front_matter(text: str) -> tuple[str, str]:
        """
        Split YAML front matter (---\n...\n---\n) from the rest.
        Returns (front_matter_yaml, remaining_body).
        """
        text = text.lstrip()
        if not text.startswith("---"):
            return "", text

        # Find the closing ---
        end_idx = text.find("\n---", 3)
        if end_idx == -1:
            return "", text

        front = text[3:end_idx].strip()
        body = text[end_idx + 4 :]  # skip past \n---\n
        return front, body

    @classmethod
    def _parse_front_matter(cls, raw_yaml: str) -> ADLFrontMatter:
        """Parse YAML string into ADLFrontMatter model."""
        if not raw_yaml:
            raise ADLParseError("Empty or missing YAML front matter")

        data: dict = yaml.safe_load(raw_yaml) or {}

        # Handle provisional_names which may be a plain dict
        pn = data.get("provisional_names", {})
        if isinstance(pn, dict):
            data["provisional_names"] = ProvisionalNames(**pn)

        # Coerce string enums
        if "adl_type" in data and isinstance(data["adl_type"], str):
            data["adl_type"] = ADLType(data["adl_type"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = DiscoveryStatus(data["status"])
        if "mechanism" in data and isinstance(data["mechanism"], str):
            data["mechanism"] = MechanismType(data["mechanism"])

        # Add timestamps if missing
        if not data.get("created_at"):
            from datetime import datetime, timezone

            data["created_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        return ADLFrontMatter(**data)

    @classmethod
    def _extract_adl_blocks(cls, body: str) -> tuple[list[ADLBlock], list[ADLActionBlock], str]:
        """
        Extract all ```adl:* blocks from the Markdown body.
        Returns (l3_blocks, action_blocks, body_with_blocks_removed).
        Action blocks (block_type="action") are routed to the L4 list.
        """
        l3_blocks: list[ADLBlock] = []
        action_blocks: list[ADLActionBlock] = []
        clean_body = body

        for match in _RE_ADL_BLOCK.finditer(body):
            block_type = match.group("block_type")
            block_body = match.group("body")

            if block_type == "action":
                kv = dict(_RE_KV_LINE.findall(block_body))
                try:
                    action_block = cls._parse_action_block(kv)
                    action_blocks.append(action_block)
                except (ValueError, KeyError) as exc:
                    raise ADLParseError(f"Invalid action block: {exc}") from exc
            elif block_type == "execution":
                # The execution spec is nested YAML (invocation / properties /
                # test_vectors), so it bypasses the flat KV-line path.
                try:
                    spec_data = yaml.safe_load(block_body) or {}
                except yaml.YAMLError as exc:
                    raise ADLParseError(f"Invalid execution block YAML: {exc}") from exc
                if not isinstance(spec_data, dict):
                    raise ADLParseError("Invalid execution block: expected a YAML mapping")
                try:
                    l3_blocks.append(ADLExecutionBlock(**spec_data))
                except ValueError as exc:
                    raise ADLParseError(f"Invalid execution block: {exc}") from exc
            else:
                kv = dict(_RE_KV_LINE.findall(block_body))
                block = cls._dispatch_block(block_type, kv)
                if block:
                    l3_blocks.append(block)

            clean_body = clean_body.replace(match.group(0), "")

        return l3_blocks, action_blocks, clean_body

    @classmethod
    def _parse_action_block(cls, kv: dict) -> ADLActionBlock:
        """Parse inline KV dict into an ADLActionBlock."""
        params = {}
        for k, v in kv.items():
            if k.startswith("param_"):
                params[k[len("param_") :]] = cls._unquote(v)

        return ADLActionBlock(
            action=cls._unquote(kv.get("action", "")),
            actor=cls._unquote(kv.get("actor", "")),
            reasoning=cls._unquote(kv.get("reasoning", "")),
            timestamp=kv.get("timestamp"),
            params=params,
            exec_status=ActionExecStatus.PENDING,
        )

    @classmethod
    def _dispatch_block(cls, block_type: str, kv: dict) -> ADLBlock | None:
        """Route parsed KV dict to the correct block constructor."""
        try:
            if block_type == "relation":
                return ADLRelationBlock(
                    source=cls._unquote(kv.get("source", "")),
                    relation=cls._unquote(kv.get("relation", "")),
                    target=cls._unquote(kv.get("target", "")),
                    mapping_type=kv.get("mapping_type"),
                    confidence=float(kv.get("confidence", "1.0")),
                )
            elif block_type == "evidence":
                return ADLEvidenceBlock(
                    evidence_type=EvidenceType(
                        cls._unquote(kv.get("evidence_type", "empirical_observation"))
                    ),
                    data_ref=cls._unquote(kv.get("data_ref", "")),
                    description=cls._unquote(kv.get("description", "")) or None,
                    confidence=float(kv.get("confidence", "1.0")),
                    observed_at=cls._unquote(kv.get("observed_at", "")) or None,
                )
            elif block_type == "seal":
                return ADLFormalSealBlock(
                    assertion=cls._unquote(kv.get("assertion", "")),
                    language=cls._unquote(kv.get("language", "lean4")),  # type: ignore[arg-type]
                    proof_ref=kv.get("proof_ref"),
                    status=cls._unquote(kv.get("status", "pending")),  # type: ignore[arg-type]
                    verified_by=kv.get("verified_by"),
                )
            else:
                # Unknown block type — skip for forward compatibility, but
                # leave a trace so typos (e.g. ``adl:relations``) are visible.
                logger.warning("Skipping unknown adl block type: %r", block_type)
                return None
        except (ValueError, KeyError) as exc:
            raise ADLParseError(f"Invalid {block_type} block: {exc}") from exc


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


from .exceptions import ADLParseError  # noqa: E402, F811 — re-export for backward compat

# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def parse_file(path: str | Path, strict_template: bool = False) -> ADLDocument:
    """One-shot parse a file."""
    return ADLParser(strict_template=strict_template).parse_file(path)


def parse_text(text: str, strict_template: bool = False) -> ADLDocument:
    """One-shot parse a string."""
    return ADLParser(strict_template=strict_template).parse_text(text)


def extract_wiki_links(text: str) -> list[str]:
    """Extract [[Wiki Link]] slugs from Markdown body text."""
    return _RE_WIKI_LINK.findall(text)
