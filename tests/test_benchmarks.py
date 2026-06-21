"""Performance benchmarks for critical ADL Lite paths.

Run with: pytest tests/test_benchmarks.py -v --benchmark-only
Compare:  pytest tests/test_benchmarks.py -v --benchmark-compare
Save:     pytest tests/test_benchmarks.py -v --benchmark-save=baseline
"""

from __future__ import annotations

import pytest

from adl_lite import (
    ADLMemory,
    ConsensusEngine,
    DiscoveryStatus,
    Event,
    EventChain,
    EventType,
    parse_text,
)

# ---------------------------------------------------------------------------
# Event chain benchmarks
# ---------------------------------------------------------------------------


def test_benchmark_event_append_1k(benchmark):
    """Benchmark: append 1,000 events to an EventChain."""

    def _append_1k():
        c = EventChain(concept_id="bench-test")
        for i in range(1000):
            c.append(
                Event(
                    concept_id="bench-test",
                    event_type=EventType.REGISTER,
                    actor=f"agent_{i % 5}",
                    payload={"index": i},
                )
            )
        return c

    result = benchmark(_append_1k)
    assert len(result.history()) == 1000


def test_benchmark_event_append_10k(benchmark):
    """Benchmark: append 10,000 events to an EventChain."""

    def _append_10k():
        c = EventChain(concept_id="bench-10k")
        for i in range(10000):
            c.append(
                Event(
                    concept_id="bench-10k",
                    event_type=EventType.VALIDATE,
                    actor=f"agent_{i % 10}",
                    payload={"index": i, "confidence": 0.85},
                )
            )
        return c

    result = benchmark(_append_10k)
    assert len(result.history()) == 10000


def test_benchmark_chain_integrity(benchmark):
    """Benchmark: verify chain integrity on a 1K-event chain."""
    chain = EventChain(concept_id="bench-integrity")
    for i in range(1000):
        chain.append(
            Event(
                concept_id="bench-integrity",
                event_type=EventType.REGISTER,
                actor=f"agent_{i % 5}",
            )
        )

    benchmark(chain.verify_integrity)


# ---------------------------------------------------------------------------
# CRDT merge benchmarks
# ---------------------------------------------------------------------------


@pytest.fixture
def crdt_chains():
    """Create two 500-event chains for merge benchmarking."""
    chain_a = EventChain(concept_id="crdt-bench-a")
    chain_b = EventChain(concept_id="crdt-bench-b")

    for i in range(500):
        chain_a.append(
            Event(
                concept_id="crdt-bench-a",
                event_type=EventType.VALIDATE,
                actor=f"agent_{i % 5}",
                payload={"confidence": 0.5 + (i % 50) / 100},
            )
        )
        chain_b.append(
            Event(
                concept_id="crdt-bench-b",
                event_type=EventType.VALIDATE,
                actor=f"agent_{(i + 3) % 5}",
                payload={"confidence": 0.6 + (i % 50) / 100},
            )
        )
    return chain_a, chain_b


def test_benchmark_crdt_merge_500(benchmark, crdt_chains):
    """Benchmark: CRDT merge of two 500-event chains."""
    from adl_lite.crdt import CRDTState

    chain_a, chain_b = crdt_chains
    state_a = CRDTState.from_chain(chain_a)
    state_b = CRDTState.from_chain(chain_b)

    def _merge():
        return state_a.merge(state_b)

    result = benchmark(_merge)
    assert result is not None


# ---------------------------------------------------------------------------
# Parser benchmarks
# ---------------------------------------------------------------------------


SAMPLE_LARGE = """---
adl_type: discovery
adl_id: disc-bench-{i}
status: provisional
confidence: 0.8{n}
novelty: 0.7{n}
domain: financial_aml
mechanism: isomorphic_mapping
scope: private/bench
---

# Concept: Benchmark Discovery {i}

This concept describes an automated benchmark discovery {i} in the AML domain.

```adl:relation
source: disc-bench-{i}
predicate: related-to
target: disc-bench-{j}
weight: 0.5
```

```adl:evidence
source: disc-bench-{i}
evidence_type: empirical_observation
description: Automated benchmark evidence for discovery {i}
```

```adl:action
action: validate
actor: bench_agent
reasoning: "Auto-validation for benchmark {i}"
params:
  confidence_boost: 0.1
```
"""


def _make_large_doc(num_concepts: int) -> str:
    parts = []
    for i in range(num_concepts):
        j = (i + 1) % num_concepts
        n = str(i + 1).zfill(2)
        parts.append(SAMPLE_LARGE.format(i=i, j=j, n=n))
    return "".join(parts)


@pytest.fixture
def large_doc_10():
    return _make_large_doc(10)


@pytest.fixture
def large_doc_50():
    return _make_large_doc(50)


def test_benchmark_parse_10_concepts(benchmark, large_doc_10):
    """Benchmark: parse 10-concept document."""
    result = benchmark(parse_text, large_doc_10)
    assert result is not None


def test_benchmark_parse_50_concepts(benchmark, large_doc_50):
    """Benchmark: parse 50-concept document."""
    result = benchmark(parse_text, large_doc_50)
    assert result is not None


# ---------------------------------------------------------------------------
# Memory / WarmIndex benchmarks
# ---------------------------------------------------------------------------


def test_benchmark_memory_store_100(benchmark):
    """Benchmark: store 100 concepts in ADLMemory."""

    def _store_100():
        mem = ADLMemory(":memory:")
        for i in range(100):
            doc = parse_text(
                f"---\n"
                f"adl_type: discovery\n"
                f"adl_id: mem-bench-{i}\n"
                f"status: provisional\n"
                f"confidence: 0.5\n"
                f"---\n\n"
                f"# Benchmark {i}\n"
            )
            mem.store(doc)
        mem.close()
        return mem

    result = benchmark(_store_100)
    assert result is not None


def test_benchmark_consensus_transition(benchmark):
    """Benchmark: consensus state transitions."""

    def _transition():
        engine = ConsensusEngine()
        for i in range(100):
            doc = parse_text(
                f"---\n"
                f"adl_type: discovery\n"
                f"adl_id: cons-bench-{i}\n"
                f"status: provisional\n"
                f"confidence: 0.5\n"
                f"---\n\n"
                f"# Benchmark {i}\n"
            )
            engine.register(doc)
        for i in range(100):
            engine.transition(
                adl_id=f"cons-bench-{i}",
                to_status=DiscoveryStatus.VALIDATED,
                actor="bench",
            )
        return True

    result = benchmark(_transition)
    assert result is True
