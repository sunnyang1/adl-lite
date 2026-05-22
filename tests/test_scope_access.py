"""
Scope access control matrix — ADLValidator.validate_scope_access.
"""

from __future__ import annotations

import pytest

from adl_lite.validator import ADLValidator


@pytest.fixture
def validator() -> ADLValidator:
    return ADLValidator()


@pytest.mark.parametrize(
    "doc_scope,requester,expected",
    [
        ("public", "public", True),
        ("public", "private/acme", True),
        ("public", "user/alice", True),
        ("public/concepts/foo", "private/acme", True),
        ("private/acme", "private/acme", True),
        ("private/acme", "private/other", False),
        ("private/acme", "public", False),
        ("user/alice", "user/alice", True),
        ("user/alice", "user/bob", False),
        ("user/alice", "private/acme", False),
        ("shared/team-alpha", "shared/team-alpha", True),
        ("shared/team-alpha", "shared/team-beta", False),
        ("shared/team-alpha", "user/alice", False),
    ],
)
def test_scope_access_matrix(
    validator: ADLValidator,
    doc_scope: str,
    requester: str,
    expected: bool,
) -> None:
    assert validator.validate_scope_access(doc_scope, requester) is expected
