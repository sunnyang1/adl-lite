"""
ADL Lite - Semantic Type Models (Pydantic)

Structured Semantic Anchoring (SSA) core data models.
Every ADL document decomposes into typed slots that constrain
the interpretive space of natural language.

References:
    - ADL Lite Spec §7.2: Three-layer syntax (L1/L2/L3)
    - ADL Lite Spec §7.4: Consensus status badges
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enumerations — Consensus & Semantic Types
# ---------------------------------------------------------------------------

class DiscoveryStatus(str, Enum):
    """Concept lifecycle status (emoji badges)."""
    PROVISIONAL = "provisional"   # 🟡
    VALIDATED = "validated"       # 🟢
    DEPRECATED = "deprecated"     # 🔴
    FORKED = "forked"             # 🔵
    ARCHIVED = "archived"         # ⚪


class ADLType(str, Enum):
    """Top-level semantic types for ADL documents."""
    DISCOVERY = "discovery"
    CONCEPT = "concept"
    RELATION = "relation"
    EVIDENCE = "evidence"
    FORMAL_SEAL = "formal_seal"


class MechanismType(str, Enum):
    """Valid isomorphic / analogical mechanism tags."""
    ISOMORPHIC_MAPPING = "isomorphic_mapping"
    ANALOGICAL_TRANSFER = "analogical_transfer"
    COMPOSITIONAL_BLEND = "compositional_blend"
    ABSTRACT_GENERALISATION = "abstract_generalisation"
    EMERGENT_PATTERN = "emergent_pattern"


class EvidenceType(str, Enum):
    """Evidence taxonomy for the evidence chain."""
    VECTOR_CLUSTER = "vector_cluster"
    SIMULATOR_RUN = "simulator_run"
    HUMAN_EXPERT = "human_expert"
    CROSS_REFERENCE = "cross_reference"
    EMPIRICAL_OBSERVATION = "empirical_observation"


# ---------------------------------------------------------------------------
# L1: YAML Front Matter Model
# ---------------------------------------------------------------------------

class ProvisionalNames(BaseModel):
    """Multilingual provisional naming."""
    zh: str | None = None
    en: str | None = None


class ADLFrontMatter(BaseModel):
    """
    L1 Header — machine-parseable identity & metadata.
    Consumed by: YAML Parser (PyYAML)
    """
    adl_type: ADLType = Field(..., description="Semantic type of the document")
    adl_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$", description="Unique identifier")
    status: DiscoveryStatus = Field(default=DiscoveryStatus.PROVISIONAL)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    domain: str = Field(default="", description="Domain tag, e.g. 'financial_aml'")
    mechanism: MechanismType | None = None
    scope: str = Field(default="public", description="Namespace scope")
    validators: list[str] = Field(default_factory=list)
    provisional_names: ProvisionalNames = Field(default_factory=ProvisionalNames)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        valid_prefixes = ("public", "private/", "user/", "shared/")
        if not any(v.startswith(p) for p in valid_prefixes):
            raise ValueError(f"Scope must start with one of {valid_prefixes}, got: {v}")
        return v

    @property
    def status_badge(self) -> str:
        badges = {
            DiscoveryStatus.PROVISIONAL: "🟡",
            DiscoveryStatus.VALIDATED: "🟢",
            DiscoveryStatus.DEPRECATED: "🔴",
            DiscoveryStatus.FORKED: "🔵",
            DiscoveryStatus.ARCHIVED: "⚪",
        }
        return badges.get(self.status, "⬜")

    @property
    def is_public(self) -> bool:
        return self.scope == "public" or self.scope.startswith("public/")

    @property
    def is_private(self) -> bool:
        return self.scope.startswith("private/")


# ---------------------------------------------------------------------------
# L3: ADL Block Models (embedded ```adl:* code blocks)
# ---------------------------------------------------------------------------

class ADLRelationBlock(BaseModel):
    """
    L3 Relation Block — typed edge between concepts.
    Syntax: ```adl:relation ... ```
    """
    block_type: Literal["relation"] = "relation"
    source: str = Field(..., description="Source concept name or URI")
    relation: str = Field(..., description="Relation predicate, e.g. 'isomorphic-to'")
    target: str = Field(..., description="Target concept URI or name")
    mapping_type: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("source", "target")
    @classmethod
    def validate_no_pronouns(cls, v: str) -> str:
        forbidden = {"this", "that", "it", "these", "those",
                     "这个", "那个", "它", "它们"}
        lowered = v.lower().strip()
        if lowered in forbidden:
            raise ValueError(f"Pronouns are forbidden in ADL slots: '{v}'")
        return v


class ADLEvidenceBlock(BaseModel):
    """
    L3 Evidence Block — structured evidence entry.
    Syntax: ```adl:evidence ... ```
    """
    block_type: Literal["evidence"] = "evidence"
    evidence_type: EvidenceType
    data_ref: str = Field(..., description="Pointer to data (vecdb://, file://, etc.)")
    description: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    observed_at: str | None = None


class ADLFormalSealBlock(BaseModel):
    """
    L3 Formal Seal — formal verification reference.
    Syntax: ```adl:seal ... ```
    """
    block_type: Literal["seal"] = "seal"
    assertion: str = Field(..., description="Formal assertion statement")
    language: Literal["lean4", "coq", "z3", "fol"] = "lean4"
    proof_ref: str | None = None
    status: Literal["pending", "verified", "failed"] = "pending"
    verified_by: str | None = None


# Union type for all ADL blocks
ADLBlock = ADLRelationBlock | ADLEvidenceBlock | ADLFormalSealBlock


# ---------------------------------------------------------------------------
# Concept Skeleton (Hot Storage)
# ---------------------------------------------------------------------------

class ConceptSkeleton(BaseModel):
    """
    Lightweight summary for fast retrieval (< 500 bytes).
    Stored in Hot layer (in-memory HashMap).
    """
    adl_id: str
    semantic_type: ADLType
    domain_tag: str
    status: DiscoveryStatus
    scope: str
    relation_summary: list[str] = Field(default_factory=list)
    evidence_count: int = 0
    confidence: float = 0.0
    novelty: float = 0.0

    @classmethod
    def from_front_matter(cls, fm: ADLFrontMatter) -> ConceptSkeleton:
        return cls(
            adl_id=fm.adl_id,
            semantic_type=fm.adl_type,
            domain_tag=fm.domain,
            status=fm.status,
            scope=fm.scope,
            confidence=fm.confidence,
            novelty=fm.novelty,
        )


# ---------------------------------------------------------------------------
# Full Parsed ADL Document
# ---------------------------------------------------------------------------

class ADLDocument(BaseModel):
    """
    Complete in-memory representation of an ADL Lite document.
    Decomposes into L1 (front_matter) + L2 (markdown_body) + L3 (adl_blocks).
    """
    front_matter: ADLFrontMatter
    markdown_body: str = ""
    adl_blocks: list[ADLBlock] = Field(default_factory=list)
    source_path: str | None = None

    # --- Computed properties ---

    @property
    def adl_id(self) -> str:
        return self.front_matter.adl_id

    @property
    def status(self) -> DiscoveryStatus:
        return self.front_matter.status

    @property
    def scope(self) -> str:
        return self.front_matter.scope

    @property
    def concept_name(self) -> str:
        """Return the English or Chinese provisional name."""
        names = self.front_matter.provisional_names
        return names.en or names.zh or self.adl_id

    @property
    def relations(self) -> list[ADLRelationBlock]:
        return [b for b in self.adl_blocks if isinstance(b, ADLRelationBlock)]

    @property
    def evidence(self) -> list[ADLEvidenceBlock]:
        return [b for b in self.adl_blocks if isinstance(b, ADLEvidenceBlock)]

    @property
    def seals(self) -> list[ADLFormalSealBlock]:
        return [b for b in self.adl_blocks if isinstance(b, ADLFormalSealBlock)]

    @property
    def wiki_links(self) -> list[str]:
        """L2 wiki-link slugs extracted from markdown body."""
        from .parser import extract_wiki_links

        return extract_wiki_links(self.markdown_body)

    def to_skeleton(self) -> ConceptSkeleton:
        """Derive the Hot-storage skeleton from this document."""
        sk = ConceptSkeleton.from_front_matter(self.front_matter)
        sk.relation_summary = [
            f"{r.source}--{r.relation}-->{r.target}" for r in self.relations
        ]
        sk.evidence_count = len(self.evidence)
        return sk

    def validate_semantics(self) -> list[str]:
        """Run semantic validation and return list of errors."""
        from .validator import ADLValidator
        validator = ADLValidator()
        return validator.validate_document(self)
