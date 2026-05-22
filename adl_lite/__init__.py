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

__version__ = "0.1.0"

from .parser import ADLParser, ADLParseError, parse_file, parse_text
from .models import (
    ADLDocument,
    ADLFrontMatter,
    ADLRelationBlock,
    ADLEvidenceBlock,
    ADLFormalSealBlock,
    ConceptSkeleton,
    DiscoveryStatus,
    ADLType,
    EvidenceType,
    MechanismType,
)
from .validator import ADLValidator
from .consensus import ConsensusEngine, ConceptChain, ForkManager, ForkResolution
from .memory import ADLMemory, HotIndex, WarmIndex

__all__ = [
    # Version
    "__version__",
    # Parser
    "ADLParser",
    "ADLParseError",
    "parse_file",
    "parse_text",
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
