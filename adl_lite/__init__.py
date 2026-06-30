"""
ADL Lite — An Event-First Capability-Lifecycle Registry for LLM Agent Ecosystems

A Markdown-native registry for multi-agent systems to record, validate,
and govern the lifecycle of agent capabilities.

Every capability is an append-only, cryptographically linked EventChain.
Status, confidence, and validators are derived exclusively from event history.

Philosophy (Wittgenstein, Tractatus §1.1): "The world is the totality of facts, not of things."
→ Action is primary. Capabilities exist only as participants in events.

Layers:
    L1  YAML Front Matter    — identity, type, status, evidence refs, scope
    L2  Markdown Body        — natural language, [[Wiki Links]], lists
    L3  ```adl:* blocks      — relation graphs, evidence chains, formal seals
    L4  ```adl:action blocks — typed actions with preconditions and side effects

Quick Start:
    from adl_lite import parse_file, ADLDocument, ADLMemory

    doc = parse_file("my_discovery.md")
    print(doc.front_matter.status_badge)   # 🟡
    errors = doc.validate_semantics()
    mem = ADLMemory()
    mem.store(doc)
"""

__version__ = "0.6.0-alpha"

from .action_executor import ActionExecutor
from .calibration import (
    CalibrationProfile,
    MARGINCalibrator,
    aggregated_confidence,
    calibrated_confidence,
)
from .canonicalization import (
    AnthropicLLMBackend,
    CanonicalizationEngine,
    LLMBackend,
    OpenAILLMBackend,
)
from .consensus import ConsensusEngine, ForkManager, ForkResolution
from .crdt import CRDTState, StatusOrder, merge_event_chains
from .did_resolver import (
    DIDDocument,
    DIDResolver,
    VerificationMethod,
    create_did_key,
    is_did,
    resolve_did,
    resolve_did_key,
    resolve_did_web,
    verify_did_signature,
)
from .embeddings import EmbeddingBackend, OpenAIBackend, SentenceTransformerBackend
from .exceptions import (
    ADLConfigError,
    ADLConsensusError,
    ADLError,
    ADLMemoryError,
    ADLOntologyError,
    ADLParseError,
    ADLTemplateError,
    ADLValidationError,
)
from .jsonld_export import export_jsonld
from .key_registry import GitSignatureVerifier, KeyRegistry, TransparencyAnchor
from .ld_proof import create_event_proof, sign_event, verify_event_proof
from .logging_config import get_logger
from .memory import ADLMemory, HotIndex, WarmIndex
from .merkle import MerkleProof, MerkleTree, compute_chain_merkle_root
from .near_duplicate import (
    check_near_duplicate,
    check_near_duplicate_embedding,
    suggest_merge,
)
from .neo4j_adapter import Neo4jGraphAdapter
from .owl_export import export_owl
from .owl_import import parse_owl_rdfxml, parse_owl_turtle
from .rdfstar_export import document_to_rdfstar_turtle, sparqlstar_query_template
from .relation_validator import RelationValidator
from .shacl_validation import validate_adl_document
from .vector_index import VectorIndex

# FDE Platform extensions (optional — imports are safe even if modules don't exist yet)
try:
    from .fde import agent_runner, pipeline_engine, tenant_manager  # noqa: F401
except ImportError:
    tenant_manager = None  # type: ignore[assignment]
    pipeline_engine = None  # type: ignore[assignment]
    agent_runner = None  # type: ignore[assignment]

from .l2_template import L2Template, L2TemplateValidator
from .models import (
    ActionDef,
    ActionExecStatus,
    ADLActionBlock,
    ADLDocument,
    ADLEvidenceBlock,
    ADLFormalSealBlock,
    ADLFrontMatter,
    ADLRelationBlock,
    ADLType,
    Comparator,
    ConceptSkeleton,
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
    EvidenceType,
    ExecutionEntry,
    MechanismType,
    PreconditionRule,
    ValidationResult,
)
from .ontology import OntologyManager
from .parser import ADLParser, extract_wiki_links, parse_file, parse_text
from .validator import ADLValidator

__all__ = [
    # Version
    "__version__",
    # Parser
    "ADLParser",
    "ADLParseError",
    "parse_file",
    "parse_text",
    "extract_wiki_links",
    # Models
    "ADLActionBlock",
    "ActionDef",
    "ActionExecStatus",
    "Comparator",
    "ADLDocument",
    "ADLFrontMatter",
    "ADLRelationBlock",
    "ADLEvidenceBlock",
    "ADLFormalSealBlock",
    "ConceptSkeleton",
    "DiscoveryStatus",
    "ADLType",
    "Event",
    "EventChain",
    "EventType",
    "EvidenceType",
    "ExecutionEntry",
    "MechanismType",
    "PreconditionRule",
    "ValidationResult",
    # Calibration
    "CalibrationProfile",
    "MARGINCalibrator",
    "aggregated_confidence",
    "calibrated_confidence",
    # CRDT
    "CRDTState",
    "StatusOrder",
    "merge_event_chains",
    # DID / Key Registry
    "KeyRegistry",
    "GitSignatureVerifier",
    "TransparencyAnchor",
    "DIDDocument",
    "DIDResolver",
    "VerificationMethod",
    "resolve_did",
    "resolve_did_key",
    "resolve_did_web",
    "verify_did_signature",
    "is_did",
    "create_did_key",
    "create_event_proof",
    "sign_event",
    "verify_event_proof",
    "MerkleProof",
    "MerkleTree",
    "compute_chain_merkle_root",
    # Relation Validator
    "RelationValidator",
    # OWL Import
    "parse_owl_turtle",
    "parse_owl_rdfxml",
    # RDF-star Export
    "document_to_rdfstar_turtle",
    "sparqlstar_query_template",
    # SHACL
    "validate_adl_document",
    # Export
    "export_owl",
    "export_jsonld",
    # Near-duplicate
    "check_near_duplicate",
    "check_near_duplicate_embedding",
    "suggest_merge",
    "EmbeddingBackend",
    "SentenceTransformerBackend",
    "OpenAIBackend",
    "CanonicalizationEngine",
    "LLMBackend",
    "OpenAILLMBackend",
    "AnthropicLLMBackend",
    "VectorIndex",
    # L2 Template
    "L2Template",
    "L2TemplateValidator",
    # Validator
    "ADLValidator",
    # Ontology
    "OntologyManager",
    # Action Executor
    "ActionExecutor",
    # Consensus
    "ConsensusEngine",
    "ForkManager",
    "ForkResolution",
    # Memory
    "Neo4jGraphAdapter",
    "ADLMemory",
    "HotIndex",
    "WarmIndex",
    # Logging
    "get_logger",
    # Exceptions
    "ADLError",
    "ADLParseError",
    "ADLValidationError",
    "ADLOntologyError",
    "ADLConsensusError",
    "ADLMemoryError",
    "ADLConfigError",
    "ADLTemplateError",
]
