"""ADL Lite — Unified exception hierarchy.

All ADL-specific exceptions inherit from ADLError, making it easy to
catch any ADL error with a single except clause while still allowing
fine-grained handling of specific failure modes.

Usage:
    from adl_lite.exceptions import ADLError, ADLValidationError

    try:
        doc.validate()
    except ADLValidationError as exc:
        print(f"Validation failed: {exc}")
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class ADLError(Exception):
    """Base for all ADL Lite exceptions."""


class ADLTemplateError(ADLError):
    """Raised when an L2 template validation fails."""


# ---------------------------------------------------------------------------
# Parse errors (document structure)
# ---------------------------------------------------------------------------


class ADLParseError(ADLError):
    """Raised when a document cannot be parsed (invalid YAML, missing front matter, etc.)."""


# ---------------------------------------------------------------------------
# Validation errors (semantic / structural)
# ---------------------------------------------------------------------------


class ADLValidationError(ADLError):
    """Raised when a document fails semantic or structural validation."""


# ---------------------------------------------------------------------------
# Ontology errors
# ---------------------------------------------------------------------------


class ADLOntologyError(ADLError):
    """Raised when an ontology constraint is violated.

    Examples:
        - Unknown predicate
        - Invalid transition
        - Missing action definition
    """


# ---------------------------------------------------------------------------
# Consensus errors
# ---------------------------------------------------------------------------


class ADLConsensusError(ADLError):
    """Raised when a consensus operation fails.

    Examples:
        - Invalid state transition
        - Concept not found in registry
        - Fork resolution failure
    """


# ---------------------------------------------------------------------------
# Memory / storage errors
# ---------------------------------------------------------------------------


class ADLMemoryError(ADLError):
    """Raised when a memory/storage operation fails.

    Examples:
        - Database connection error
        - Concept not found in store
        - Index corruption
    """


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class ADLConfigError(ADLError):
    """Raised when configuration is invalid or missing."""


# ---------------------------------------------------------------------------
# Re-export aliases for backward compatibility
# ---------------------------------------------------------------------------

# ADLParseError was originally defined in parser.py — re-export here
# for the public API, but keep the definition in parser.py for now
# to avoid breaking existing imports.
