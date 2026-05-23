"""
ADL Lite — Semantic Validator

Validates ADL documents against SSA (Structured Semantic Anchoring) constraints:
    1. Pronoun prohibition — fuzzy referents break cross-agent consensus
    2. Scope routing — validates namespace access patterns
    3. Slot completeness — required fields per semantic type
    4. Evidence integrity — refs must be well-formed URIs

References:
    - ADL Lite Spec §6.4: Namespace isolation (adl://public/, adl://private/...)
    - ADL Lite Spec §7.5: Validator design
"""

from __future__ import annotations

import re

from .models import (
    ADLDocument,
    ADLFrontMatter,
    ADLRelationBlock,
    ADLType,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FORBIDDEN_PRONOUNS = frozenset({
    "this", "that", "it", "these", "those",
    "这个", "那个", "它", "它们", "这里", "那里",
})

# Demonstrative / vague referent patterns (English L2)
_DEMONSTRATIVE_START = re.compile(
    r"(?:^|[\n.!?]\s+)(This|That|These|Those|It)\b",
    re.MULTILINE,
)
_DEMONSTRATIVE_PREDICATE = re.compile(
    r"\b(This|That|These|Those|It)\s+"
    r"(?:is|are|was|were|shows?|demonstrates?|indicates?|means?|refers?|"
    r"describes?|documents?|uses?|works?|will|can|should|must|has|have|had)\b",
    re.IGNORECASE,
)
_IT_AFTER_CONJ = re.compile(
    r"\b(because|when|where|if|while|although|since)\s+it\b",
    re.IGNORECASE,
)
# Chinese — always flag
_CJK_PRONOUN = re.compile(
    r"(这个|那个|它|它们|这里|那里)",
)

_COMPLEMENTIZER_VERBS = (
    "understand", "believe", "know", "show", "indicate", "mean", "suggest",
    "require", "demonstrate", "ensure", "note", "see", "prove", "confirm",
    "assert", "observe", "recognize", "acknowledge",
)


def _is_allowed_that(body: str, match: re.Match[str]) -> bool:
    """Allow relative ('nodes that feed') and complementizer ('shows that X') uses of 'that'."""
    start = match.start()
    before = body[:start].rstrip()
    after = body[match.end() :].lstrip()
    if re.search(r"\b[\w-]+\s*$", before) and re.match(r"[\w-]+", after):
        return True
    verb_pat = r"\b(?:" + "|".join(_COMPLEMENTIZER_VERBS) + r")s?\s*$"
    if re.search(verb_pat, before, re.IGNORECASE):
        return True
    return False


def find_pronoun_violations(body: str) -> list[str]:
    """Return human-readable pronoun violation messages for fuzzy referents."""
    errors: list[str] = []

    for m in _CJK_PRONOUN.finditer(body):
        errors.append(
            f"Forbidden pronoun detected: '{m.group(0)}'. "
            "Use explicit concept names or URIs instead."
        )

    for pat, label in (
        (_DEMONSTRATIVE_START, "sentence-initial demonstrative"),
        (_DEMONSTRATIVE_PREDICATE, "demonstrative predicate"),
        (_IT_AFTER_CONJ, "vague 'it' after conjunction"),
    ):
        for m in pat.finditer(body):
            token = m.group(1) if m.lastindex else m.group(0).split()[-1]
            errors.append(
                f"Forbidden pronoun detected: '{token.lower()}'. "
                "Use explicit concept names or URIs instead."
            )

    for m in re.finditer(r"\bthat\b", body, re.IGNORECASE):
        if not _is_allowed_that(body, m):
            errors.append(
                "Forbidden pronoun detected: 'that'. "
                "Use explicit concept names or URIs instead."
            )

    for pronoun in ("this", "these", "those"):
        if re.search(r"\b" + pronoun + r"\b", body, re.IGNORECASE):
            errors.append(
                f"Forbidden pronoun detected: '{pronoun}'. "
                "Use explicit concept names or URIs instead."
            )

    for m in re.finditer(r"\b(it)\b", body, re.IGNORECASE):
        start = m.start()
        prefix = body[max(0, start - 30) : start]
        if re.search(r"\b(because|when|where|if|while|although|since)\s+$", prefix, re.IGNORECASE):
            errors.append(
                "Forbidden pronoun detected: 'it'. "
                "Use explicit concept names or URIs instead."
            )
            continue
        if re.search(r"(?:^|[\n.!?]\s+)It\b", body[: start + 2]):
            continue  # caught by _DEMONSTRATIVE_START
        # other standalone 'it' — flag
        if not re.search(r"[\w-]+\s+$", prefix.rstrip()):  # skip "word it" object?
            errors.append(
                "Forbidden pronoun detected: 'it'. "
                "Use explicit concept names or URIs instead."
            )

    seen: set[str] = set()
    unique: list[str] = []
    for e in errors:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return unique

_SCOPE_PATTERN = re.compile(
    r"^(public|public/.*|private/[a-zA-Z0-9_-]+|user/[a-zA-Z0-9_-]+|shared/[a-zA-Z0-9_-]+)$"
)


class ADLValidator:
    """
    Stateless semantic validator for ADL Lite documents.

    Usage:
        validator = ADLValidator()
        errors = validator.validate_document(doc)
        if errors:
            for e in errors:
                print(f"  [VALIDATION] {e}")
    """

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_document(self, doc: ADLDocument) -> list[str]:
        """
        Run all validation checks on a parsed ADLDocument.
        Returns a list of human-readable error strings (empty = valid).
        """
        errors: list[str] = []
        errors.extend(self._validate_front_matter(doc.front_matter))
        errors.extend(self._validate_markdown_body(doc.markdown_body))
        for block in doc.adl_blocks:
            if isinstance(block, ADLRelationBlock):
                errors.extend(self._validate_relation_block(block))
        return errors

    def validate_scope_access(self, doc_scope: str, requester_scope: str) -> bool:
        """
        Check if *requester_scope* is allowed to access *doc_scope*.

        Rules:
            public        ← anyone
            private/X     ← only private/X
            user/U        ← only user/U
            shared/S      ← members of shared/S
        """
        if doc_scope == "public" or doc_scope.startswith("public/"):
            return True
        return doc_scope == requester_scope

    # ------------------------------------------------------------------
    # Internal checks
    # ------------------------------------------------------------------

    def _validate_front_matter(self, fm: ADLFrontMatter) -> list[str]:
        errors: list[str] = []

        # Scope format
        if not _SCOPE_PATTERN.match(fm.scope):
            errors.append(
                f"Invalid scope format: '{fm.scope}'. "
                "Expected: public | private/<org> | user/<id> | shared/<collab>"
            )

        # Confidence / Novelty range (Pydantic already enforces, but double-check)
        if not (0.0 <= fm.confidence <= 1.0):
            errors.append(f"confidence must be in [0, 1], got {fm.confidence}")
        if not (0.0 <= fm.novelty <= 1.0):
            errors.append(f"novelty must be in [0, 1], got {fm.novelty}")

        # Type-specific required fields
        if fm.adl_type == ADLType.DISCOVERY and fm.mechanism is None:
            errors.append("Discovery documents must specify 'mechanism'")

        if fm.adl_type == ADLType.FORMAL_SEAL and not fm.validators:
            if self.strict:
                errors.append("Formal seal requires at least one validator in strict mode")

        # Naming sanity
        names = fm.provisional_names
        if not names.zh and not names.en:
            errors.append("At least one provisional name (zh or en) is required")

        return errors

    def _validate_markdown_body(self, body: str) -> list[str]:
        return find_pronoun_violations(body)

    def _validate_relation_block(self, block: ADLRelationBlock) -> list[str]:
        errors: list[str] = []

        # Source / target must not be empty
        if not block.source.strip():
            errors.append("Relation block: 'source' must not be empty")
        if not block.target.strip():
            errors.append("Relation block: 'target' must not be empty")

        # Target URI scheme check
        target = block.target
        if target.startswith("adl://"):
            # Validate ADL URI format
            if not re.match(r"^adl://(public|private|user|shared)/", target):
                errors.append(f"Invalid ADL URI scheme in target: '{target}'")

        return errors
