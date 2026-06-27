"""
tests/test_preconditions_extended.py
Property-based (Hypothesis) + mutation testing for PreconditionRule.

Targets:
- 1000+ random generated test cases
- O(1) evaluation time for every rule
- Invalid comparators rejected at construction time
- 500+ mutation test cases (single-field mutation of valid front matter)
"""

from __future__ import annotations

import time
from typing import Any

import hypothesis.strategies as st
import pytest
from hypothesis import HealthCheck, given, settings
from pydantic import ValidationError

from adl_lite.models import (
    ADLFrontMatter,
    ADLType,
    Comparator,
    DiscoveryStatus,
    MechanismType,
    PreconditionRule,
    ProvisionalNames,
)

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------


def _valid_scope() -> st.SearchStrategy[str]:
    return st.sampled_from(
        [
            "public",
            "private/org1",
            "user/u1",
            "shared/collab1",
        ]
    )


def _valid_adl_front_matter() -> st.SearchStrategy[ADLFrontMatter]:
    return st.builds(
        ADLFrontMatter,
        adl_type=st.sampled_from(ADLType),
        adl_id=st.text(
            min_size=1,
            max_size=20,
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
        ),
        status=st.sampled_from(DiscoveryStatus),
        confidence=st.floats(min_value=0.0, max_value=1.0),
        novelty=st.floats(min_value=0.0, max_value=1.0),
        domain=st.text(
            min_size=0,
            max_size=30,
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
        ),
        mechanism=st.sampled_from(list(MechanismType) + [None]),
        scope=_valid_scope(),
        validators=st.lists(
            st.text(min_size=1, max_size=10),
            min_size=0,
            max_size=5,
        ),
        provisional_names=st.builds(
            ProvisionalNames,
            zh=st.one_of(st.none(), st.text(max_size=10)),
            en=st.one_of(st.none(), st.text(max_size=10)),
        ),
        evidence_refs=st.lists(
            st.text(max_size=20),
            min_size=0,
            max_size=3,
        ),
    )


def _valid_precondition_rule() -> st.SearchStrategy[PreconditionRule]:
    """Generate a PreconditionRule with a compatible field/comparator/value trio."""
    fields = [
        "confidence",
        "status",
        "scope",
        "domain",
        "novelty",
        "validators",
        "adl_id",
        "mechanism",
    ]

    def _rule_for_field(field: str) -> st.SearchStrategy[PreconditionRule]:
        if field == "confidence":
            return st.one_of(
                st.builds(
                    PreconditionRule,
                    field=st.just("confidence"),
                    comparator=st.sampled_from(
                        [
                            Comparator.EQ,
                            Comparator.NEQ,
                            Comparator.GT,
                            Comparator.GTE,
                            Comparator.LT,
                            Comparator.LTE,
                        ]
                    ),
                    value=st.floats(min_value=0.0, max_value=1.0),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("confidence"),
                    comparator=st.just(Comparator.IN),
                    value=st.lists(
                        st.floats(min_value=0.0, max_value=1.0),
                        min_size=1,
                        max_size=3,
                    ),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("confidence"),
                    comparator=st.just(Comparator.EXISTS),
                    value=st.none(),
                ),
            )
        elif field == "status":
            return st.one_of(
                st.builds(
                    PreconditionRule,
                    field=st.just("status"),
                    comparator=st.sampled_from([Comparator.EQ, Comparator.NEQ]),
                    value=st.sampled_from(DiscoveryStatus),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("status"),
                    comparator=st.just(Comparator.IN),
                    value=st.lists(
                        st.sampled_from(DiscoveryStatus),
                        min_size=1,
                        max_size=3,
                    ),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("status"),
                    comparator=st.just(Comparator.EXISTS),
                    value=st.none(),
                ),
            )
        elif field == "scope":
            return st.one_of(
                st.builds(
                    PreconditionRule,
                    field=st.just("scope"),
                    comparator=st.sampled_from([Comparator.EQ, Comparator.NEQ]),
                    value=_valid_scope(),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("scope"),
                    comparator=st.just(Comparator.IN),
                    value=st.lists(_valid_scope(), min_size=1, max_size=3),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("scope"),
                    comparator=st.just(Comparator.EXISTS),
                    value=st.none(),
                ),
            )
        elif field == "domain":
            return st.one_of(
                st.builds(
                    PreconditionRule,
                    field=st.just("domain"),
                    comparator=st.sampled_from([Comparator.EQ, Comparator.NEQ]),
                    value=st.text(max_size=20),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("domain"),
                    comparator=st.just(Comparator.IN),
                    value=st.lists(st.text(max_size=20), min_size=1, max_size=3),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("domain"),
                    comparator=st.just(Comparator.EXISTS),
                    value=st.none(),
                ),
            )
        elif field == "novelty":
            return st.one_of(
                st.builds(
                    PreconditionRule,
                    field=st.just("novelty"),
                    comparator=st.sampled_from(
                        [
                            Comparator.EQ,
                            Comparator.GT,
                            Comparator.GTE,
                            Comparator.LT,
                            Comparator.LTE,
                        ]
                    ),
                    value=st.floats(min_value=0.0, max_value=1.0),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("novelty"),
                    comparator=st.just(Comparator.IN),
                    value=st.lists(
                        st.floats(min_value=0.0, max_value=1.0),
                        min_size=1,
                        max_size=3,
                    ),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("novelty"),
                    comparator=st.just(Comparator.EXISTS),
                    value=st.none(),
                ),
            )
        elif field == "validators":
            return st.one_of(
                st.builds(
                    PreconditionRule,
                    field=st.just("validators"),
                    comparator=st.sampled_from(
                        [
                            Comparator.EQ,
                            Comparator.NEQ,
                            Comparator.IN,
                            Comparator.EXISTS,
                        ]
                    ),
                    value=st.one_of(
                        st.text(min_size=1),
                        st.lists(st.text(min_size=1), min_size=1, max_size=3),
                    ),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("validators"),
                    comparator=st.just(Comparator.IN),
                    value=st.lists(st.text(min_size=1), min_size=1, max_size=3),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("validators"),
                    comparator=st.just(Comparator.EXISTS),
                    value=st.none(),
                ),
            )
        elif field == "adl_id":
            return st.one_of(
                st.builds(
                    PreconditionRule,
                    field=st.just("adl_id"),
                    comparator=st.sampled_from([Comparator.EQ, Comparator.NEQ]),
                    value=st.text(min_size=1, max_size=20),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("adl_id"),
                    comparator=st.just(Comparator.IN),
                    value=st.lists(
                        st.text(min_size=1, max_size=20),
                        min_size=1,
                        max_size=3,
                    ),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("adl_id"),
                    comparator=st.just(Comparator.EXISTS),
                    value=st.none(),
                ),
            )
        elif field == "mechanism":
            return st.one_of(
                st.builds(
                    PreconditionRule,
                    field=st.just("mechanism"),
                    comparator=st.sampled_from([Comparator.EQ, Comparator.NEQ]),
                    value=st.sampled_from(MechanismType),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("mechanism"),
                    comparator=st.just(Comparator.IN),
                    value=st.lists(
                        st.sampled_from(MechanismType),
                        min_size=1,
                        max_size=3,
                    ),
                ),
                st.builds(
                    PreconditionRule,
                    field=st.just("mechanism"),
                    comparator=st.just(Comparator.EXISTS),
                    value=st.none(),
                ),
            )
        else:
            return st.builds(
                PreconditionRule,
                field=st.just(field),
                comparator=st.sampled_from(list(Comparator)),
                value=st.one_of(
                    st.integers(),
                    st.text(),
                    st.floats(allow_nan=False, allow_infinity=False),
                ),
            )

    return st.sampled_from(fields).flatmap(_rule_for_field)


def _mutated_front_matter(fm: ADLFrontMatter) -> st.SearchStrategy[ADLFrontMatter]:
    """Return a strategy that yields a single-field mutation of *fm*."""
    mutations = [
        fm.model_copy(update={"confidence": min(1.0, max(0.0, fm.confidence + 0.1))}),
        fm.model_copy(update={"confidence": min(1.0, max(0.0, fm.confidence - 0.1))}),
        fm.model_copy(update={"novelty": min(1.0, max(0.0, fm.novelty + 0.1))}),
        fm.model_copy(update={"novelty": min(1.0, max(0.0, fm.novelty - 0.1))}),
        fm.model_copy(
            update={
                "status": (
                    DiscoveryStatus.DEPRECATED
                    if fm.status != DiscoveryStatus.DEPRECATED
                    else DiscoveryStatus.VALIDATED
                )
            }
        ),
        fm.model_copy(
            update={"scope": ("private/org1" if fm.scope != "private/org1" else "public")}
        ),
        fm.model_copy(update={"domain": "mutated" if fm.domain != "mutated" else "original"}),
        fm.model_copy(update={"validators": fm.validators + ["mutator"]}),
        fm.model_copy(update={"validators": []}),
        fm.model_copy(
            update={"adl_id": ("mutated-id" if fm.adl_id != "mutated-id" else "original-id")}
        ),
    ]
    return st.sampled_from(mutations)


def _fm_and_mutation() -> st.SearchStrategy[tuple[ADLFrontMatter, ADLFrontMatter]]:
    return _valid_adl_front_matter().flatmap(
        lambda fm: st.tuples(st.just(fm), _mutated_front_matter(fm))
    )


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPreconditionPropertyBased:
    """Property-based evaluation and timing guarantees."""

    @given(
        rule=_valid_precondition_rule(),
        fm=_valid_adl_front_matter(),
    )
    @settings(
        max_examples=500,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_random_rules_evaluate_in_o1(
        self,
        rule: PreconditionRule,
        fm: ADLFrontMatter,
    ):
        """Every generated rule must evaluate in <1 ms (O(1))."""
        start = time.perf_counter()
        result = rule.check(fm)
        elapsed = time.perf_counter() - start
        assert isinstance(result, bool)
        assert elapsed < 0.001, f"Rule evaluation took {elapsed:.4f}s (expected O(1))"

    @given(
        rule=_valid_precondition_rule(),
        data=_fm_and_mutation(),
    )
    @settings(
        max_examples=500,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_mutated_front_matter_still_evaluates(
        self,
        rule: PreconditionRule,
        data: tuple[ADLFrontMatter, ADLFrontMatter],
    ):
        """Single-field mutation must not break evaluation determinism."""
        fm, mutated = data
        res_orig = rule.check(fm)
        res_mut = rule.check(mutated)
        assert isinstance(res_orig, bool)
        assert isinstance(res_mut, bool)
        start = time.perf_counter()
        _ = rule.check(mutated)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.001, f"Mutated evaluation took {elapsed:.4f}s (expected O(1))"


# ---------------------------------------------------------------------------
# Invalid-rule rejection
# ---------------------------------------------------------------------------


class TestPreconditionInvalidRules:
    """Construction-time rejection of malformed rules."""

    @given(
        field=st.sampled_from(
            [
                "confidence",
                "status",
                "scope",
                "validators",
            ]
        ),
        bad_comparator=st.text(min_size=1).filter(lambda s: s not in {c.value for c in Comparator}),
    )
    @settings(max_examples=200, deadline=None)
    def test_invalid_comparator_rejected(
        self,
        field: str,
        bad_comparator: str,
    ):
        """PreconditionRule must reject unknown comparators at construction time."""
        with pytest.raises(ValidationError):
            PreconditionRule(
                field=field,
                comparator=bad_comparator,  # type: ignore[arg-type]
                value=0.5,
            )

    @given(
        field=st.text(min_size=1).filter(
            lambda f: f
            not in {
                "confidence",
                "status",
                "scope",
                "domain",
                "novelty",
                "validators",
                "adl_id",
                "adl_type",
                "mechanism",
                "created_at",
                "updated_at",
                "provisional_names",
                "evidence_refs",
                "validator_count",
                "is_public",
                "is_private",
                "status_badge",
                # Pydantic model methods that can be accessed via getattr
                "json",
                "dict",
                "model_dump",
                "model_dump_json",
                "model_copy",
                "model_validate",
                "model_validate_json",
                "model_post_init",
            }
        ),
        comparator=st.sampled_from(list(Comparator)),
        value=st.one_of(
            st.integers(),
            st.text(),
            st.floats(allow_nan=False, allow_infinity=False),
        ),
    )
    @settings(max_examples=300, deadline=None)
    def test_nonexistent_field_returns_false(
        self,
        field: str,
        comparator: Comparator,
        value: Any,
    ):
        """Rules referencing a nonexistent field must evaluate to False."""
        rule = PreconditionRule(
            field=field,
            comparator=comparator,
            value=value,
        )
        fm = ADLFrontMatter(
            adl_type=ADLType.DISCOVERY,
            adl_id="test",
            confidence=0.5,
            status=DiscoveryStatus.PROVISIONAL,
            scope="public",
        )
        result = rule.check(fm)
        assert result is False
