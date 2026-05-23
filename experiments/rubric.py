"""
Ambiguity rubric for RQ1 (Phase B).

Scores cross-agent referent clarity without injecting synthetic pronouns into baselines.
Lower ambiguity_score is better for ADL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from adl_lite import ADLDocument
from adl_lite.validator import ADLValidator

_FORBIDDEN = re.compile(
    r"\b(this|that|it|these|those|这个|那个|它|它们|这里|那里)\b",
    re.IGNORECASE,
)
_WIKI = re.compile(r"\[\[([^\]]+)\]\]")
_ADL_URI = re.compile(r"adl://[^\s\"']+")


@dataclass
class AmbiguityRubricResult:
    pronoun_rate: float
    entity_anchor_rate: float
    validator_errors: int
    ambiguity_score: float
    word_count: int

    def to_dict(self) -> dict:
        return {
            "pronoun_rate": round(self.pronoun_rate, 4),
            "entity_anchor_rate": round(self.entity_anchor_rate, 4),
            "validator_errors": self.validator_errors,
            "ambiguity_score": round(self.ambiguity_score, 4),
            "word_count": self.word_count,
        }


def score_document(doc: ADLDocument, *, strict: bool = False) -> AmbiguityRubricResult:
    """Compute ambiguity rubric on one document."""
    body = doc.markdown_body
    words = max(len(body.split()), 1)
    pronoun_hits = len(_FORBIDDEN.findall(body))
    pronoun_rate = pronoun_hits / words

    concept = doc.concept_name or doc.adl_id
    anchors = 0
    if concept and concept.lower() in body.lower():
        anchors += 1
    anchors += len(_WIKI.findall(body))
    anchors += len(_ADL_URI.findall(body))
    entity_anchor_rate = anchors / words

    validator = ADLValidator(strict=strict)
    errors = validator.validate_document(doc)
    validator_errors = len(errors)

    # Weighted composite: pronouns hurt, anchors help, validator errors hurt
    ambiguity_score = (
        pronoun_rate * 10.0
        + validator_errors * 0.5
        - entity_anchor_rate * 2.0
    )
    ambiguity_score = max(0.0, ambiguity_score)

    return AmbiguityRubricResult(
        pronoun_rate=pronoun_rate,
        entity_anchor_rate=entity_anchor_rate,
        validator_errors=validator_errors,
        ambiguity_score=ambiguity_score,
        word_count=words,
    )


def compare_corpus(adl_docs: list[ADLDocument], plain_docs: list[ADLDocument]) -> dict:
    """Compare ADL vs fair plain baseline on paired documents."""
    if len(adl_docs) != len(plain_docs):
        raise ValueError("ADL and plain corpora must be same length (paired)")

    adl_scores = [score_document(d) for d in adl_docs]
    plain_scores = [score_document(d) for d in plain_docs]

    adl_mean = sum(s.ambiguity_score for s in adl_scores) / max(len(adl_scores), 1)
    plain_mean = sum(s.ambiguity_score for s in plain_scores) / max(len(plain_scores), 1)
    reduction = (plain_mean - adl_mean) / max(plain_mean, 1e-9)

    return {
        "metric": "ambiguity_rubric",
        "adl_mean_ambiguity": round(adl_mean, 4),
        "plain_mean_ambiguity": round(plain_mean, 4),
        "ambiguity_reduction_pct": round(reduction * 100, 2),
        "n_pairs": len(adl_docs),
        "phase_b": True,
        "adl_details": [s.to_dict() for s in adl_scores[:5]],
        "plain_details": [s.to_dict() for s in plain_scores[:5]],
    }
