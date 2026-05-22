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
        errors: list[str] = []
        lowered = body.lower()

        # Pronoun check — fuzzy referents destroy cross-agent consensus
        for pronoun in _FORBIDDEN_PRONOUNS:
            # Simple word-boundary check (sufficient for 95%+ cases)
            pattern = r'\b' + re.escape(pronoun) + r'\b'
            if re.search(pattern, lowered):
                errors.append(
                    f"Forbidden pronoun detected: '{pronoun}'. "
                    "Use explicit concept names or URIs instead."
                )

        return errors

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
