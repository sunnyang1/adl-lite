"""
ADL Lite — Agent Discovery Language (Lite Edition)

A Markdown-native language for multi-agent systems to record, validate,
and reach consensus on conceptual discoveries.

Layers:
    L1  YAML Front Matter    — identity, type, status, evidence refs, scope
    L2  Markdown Body        — natural language, [[Wiki Links]], lists
    L3  ```adl:* blocks      — relation graphs, evidence chains, formal seals

Quick Start:
    from adl_lite import parse_file, ADLDocument, ADLMemory

    doc = parse_file("my_discovery.md")
    print(doc.front_matter.status_badge)   # 🟡
    errors = doc.validate_semantics()
    mem = ADLMemory()
    mem.store(doc)
"""

__version__ = "0.2.0"

from .consensus import ConceptChain, ConsensusEngine, ForkManager, ForkResolution
from .memory import ADLMemory, HotIndex, WarmIndex
from .models import (
    ADLDocument,
    ADLEvidenceBlock,
    ADLFormalSealBlock,
    ADLFrontMatter,
    ADLRelationBlock,
    ADLType,
    ConceptSkeleton,
    DiscoveryStatus,
    EvidenceType,
    MechanismType,
)
from .ontology import OntologyManager
from .parser import ADLParseError, ADLParser, extract_wiki_links, parse_file, parse_text
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
    "ADLDocument",
    "ADLFrontMatter",
    "ADLRelationBlock",
    "ADLEvidenceBlock",
    "ADLFormalSealBlock",
    "ConceptSkeleton",
    "DiscoveryStatus",
    "ADLType",
    "EvidenceType",
    "MechanismType",
    # Validator
    "ADLValidator",
    # Ontology
    "OntologyManager",
    # Consensus
    "ConsensusEngine",
    "ConceptChain",
    "ForkManager",
    "ForkResolution",
    # Memory
    "ADLMemory",
    "HotIndex",
    "WarmIndex",
]
