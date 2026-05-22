"""
Golden parser snapshot for capital_reflux_trap.md (stable fields only).
"""

from __future__ import annotations

from pathlib import Path

from adl_lite import parse_file

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "capital_reflux_trap.md"


def test_capital_reflux_trap_golden():
    doc = parse_file(EXAMPLE)
    fm = doc.front_matter

    assert fm.adl_id == "disc-capital-trap"
    assert fm.adl_type.value == "discovery"
    assert fm.scope == "private/ceiec-aml"
    assert fm.provisional_names.en == "Capital Attention Trap"
    assert len(doc.relations) == 2
    assert len(doc.evidence) == 3
    assert len(doc.seals) == 1
    assert doc.relations[0].relation == "isomorphic-to"
    assert "gradient_explosion" in doc.relations[0].target

    errors = doc.validate_semantics()
    assert errors == []
