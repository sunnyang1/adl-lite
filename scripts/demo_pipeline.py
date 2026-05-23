#!/usr/bin/env python3
"""
End-to-end ADL Lite demo: discovery → validate → store → related query.

Usage:
    python scripts/demo_pipeline.py              # default: --scripted
    python scripts/demo_pipeline.py --scripted
    python scripts/demo_pipeline.py --scripted --sim
    python scripts/demo_pipeline.py --llm
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from adl_lite.memory import ADLMemory  # noqa: E402
from adl_lite.parser import ADLParseError, parse_file  # noqa: E402
from adl_lite.validator import ADLValidator  # noqa: E402

DEFAULT_DISCOVERY = ROOT / "examples" / "capital_reflux_trap.md"
SUPPORTING_DOCS = (ROOT / "examples" / "gradient_explosion.md",)
DEFAULT_QUERY_ID = "disc-capital-trap"


@dataclass
class DocResult:
    path: Path
    adl_id: str
    concept: str
    valid: bool
    stored: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineSummary:
    mode: str
    db_path: Path
    documents: list[DocResult]
    query_id: str
    related: list[tuple[str, str, float]]
    sim_log: Path | None = None
    llm_status: str | None = None
    skipped: bool = False
    skip_reason: str = ""


def _parse_validate_store(
    path: Path,
    validator: ADLValidator,
    mem: ADLMemory,
) -> DocResult:
    try:
        doc = parse_file(path)
    except (ADLParseError, OSError, ValueError) as exc:
        return DocResult(
            path=path,
            adl_id="",
            concept="",
            valid=False,
            stored=False,
            errors=[str(exc)],
        )

    errors = validator.validate_document(doc)
    if errors:
        return DocResult(
            path=path,
            adl_id=doc.adl_id,
            concept=doc.concept_name,
            valid=False,
            stored=False,
            errors=errors,
        )

    mem.store(doc)
    return DocResult(
        path=path,
        adl_id=doc.adl_id,
        concept=doc.concept_name,
        valid=True,
        stored=True,
    )


def run_scripted_pipeline(
    db_path: Path,
    *,
    use_sim: bool = False,
    discovery_path: Path | None = None,
    query_id: str = DEFAULT_QUERY_ID,
    depth: int = 2,
) -> PipelineSummary:
    """Parse/validate/store example docs, then query related concepts."""
    if use_sim:
        from experiments.harness import run_scripted_sim

        sim_log = run_scripted_sim(db_path=db_path)
        mem = ADLMemory(db_path=str(db_path))
        related = mem.find_related(query_id, depth=depth)
        mem.close()
        return PipelineSummary(
            mode="scripted-sim",
            db_path=db_path,
            documents=[],
            query_id=query_id,
            related=related,
            sim_log=sim_log,
        )

    validator = ADLValidator()
    mem = ADLMemory(db_path=str(db_path))
    paths = [discovery_path or DEFAULT_DISCOVERY, *SUPPORTING_DOCS]
    results: list[DocResult] = []
    for path in paths:
        results.append(_parse_validate_store(path, validator, mem))

    related = mem.find_related(query_id, depth=depth)
    mem.close()

    return PipelineSummary(
        mode="scripted",
        db_path=db_path,
        documents=results,
        query_id=query_id,
        related=related,
    )


def run_llm_pipeline(
    db_path: Path,
    *,
    model: str | None = None,
    max_retries: int = 1,
    depth: int = 2,
) -> PipelineSummary:
    """Optional LLM discovery; skips gracefully when no API key is set."""
    from experiments.llm_harness import llm_available, run_llm_sim

    if not llm_available():
        return PipelineSummary(
            mode="llm",
            db_path=db_path,
            documents=[],
            query_id="",
            related=[],
            llm_status="skipped",
            skipped=True,
            skip_reason="No LLM API key (set MIMO_API_KEY or OPENAI_API_KEY)",
        )

    result = run_llm_sim(model=model, max_retries=max_retries)
    if result.status == "skipped":
        return PipelineSummary(
            mode="llm",
            db_path=db_path,
            documents=[],
            query_id="",
            related=[],
            llm_status="skipped",
            skipped=True,
            skip_reason=result.detail.get("reason", "LLM unavailable"),
        )

    if result.status != "completed" or not result.discovery_path:
        reason = "; ".join(result.errors) or result.status
        return PipelineSummary(
            mode="llm",
            db_path=db_path,
            documents=[],
            query_id="",
            related=[],
            llm_status=result.status,
            skipped=True,
            skip_reason=reason,
        )

    validator = ADLValidator()
    mem = ADLMemory(db_path=str(db_path))
    doc_results = [_parse_validate_store(result.discovery_path, validator, mem)]
    for path in SUPPORTING_DOCS:
        doc_results.append(_parse_validate_store(path, validator, mem))

    query_id = doc_results[0].adl_id
    related = mem.find_related(query_id, depth=depth) if query_id else []
    mem.close()

    return PipelineSummary(
        mode="llm",
        db_path=db_path,
        documents=doc_results,
        query_id=query_id,
        related=related,
        llm_status=result.status,
    )


def print_summary(summary: PipelineSummary) -> None:
    print()
    print("=" * 60)
    print("ADL Lite Demo Pipeline — Summary")
    print("=" * 60)
    print(f"Mode:      {summary.mode}")
    print(f"Database:  {summary.db_path}")

    if summary.skipped:
        print(f"Status:    skipped ({summary.skip_reason})")
        print("=" * 60)
        return

    if summary.sim_log:
        print(f"Sim log:   {summary.sim_log}")

    if summary.llm_status:
        print(f"LLM:       {summary.llm_status}")

    if summary.documents:
        print()
        print("Documents:")
        for doc in summary.documents:
            status = "OK" if doc.valid and doc.stored else "FAIL"
            label = doc.adl_id or doc.path.name
            print(f"  [{status}] {label} — {doc.concept or doc.path.name}")
            for err in doc.errors:
                print(f"         - {err}")

    print()
    print(f"Related query: {summary.query_id} (depth=2)")
    if summary.related:
        for concept, relation, conf in summary.related:
            print(f"  • {concept}  via {relation}  (conf={conf:.2f})")
    else:
        print("  (no related concepts found)")

    stored = sum(1 for d in summary.documents if d.stored)
    print()
    print(f"Stored {stored} document(s); {len(summary.related)} related concept(s).")
    print("=" * 60)


def _default_db_path() -> Path:
    fd, path = tempfile.mkstemp(suffix=".db", prefix="adl_demo_")
    import os

    os.close(fd)
    return Path(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ADL Lite end-to-end demo: discovery → validate → store → related",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--scripted",
        action="store_true",
        help="Use example discovery (default)",
    )
    mode.add_argument(
        "--llm",
        action="store_true",
        help="LLM discovery via run_sim --llm (skips without API key)",
    )
    parser.add_argument(
        "--sim",
        action="store_true",
        help="Run full 5-agent scripted simulation (with --scripted)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite database path (default: temp file)",
    )
    parser.add_argument(
        "--query-id",
        default=DEFAULT_QUERY_ID,
        help=f"Concept id for related query (default: {DEFAULT_QUERY_ID})",
    )
    parser.add_argument("--model", default=None, help="LLM model override")
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="LLM revision retries on validation failure",
    )
    args = parser.parse_args(argv)

    use_scripted = args.scripted or not args.llm
    db_path = Path(args.db) if args.db else _default_db_path()

    if use_scripted:
        summary = run_scripted_pipeline(
            db_path,
            use_sim=args.sim,
            query_id=args.query_id,
        )
    else:
        summary = run_llm_pipeline(
            db_path,
            model=args.model,
            max_retries=args.max_retries,
        )

    print_summary(summary)

    if summary.skipped:
        return 0

    if summary.documents and not all(d.valid and d.stored for d in summary.documents):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
