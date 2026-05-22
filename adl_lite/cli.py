"""
ADL Lite — command-line interface (stdlib argparse).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .consensus import ConceptChain, ConsensusEngine, ConsensusEntry
from .memory import ADLMemory
from .models import DiscoveryStatus
from .parser import ADLParseError, parse_file
from .validator import ADLValidator


def _default_state_path(db_path: str | None) -> Path:
    if db_path:
        p = Path(db_path)
        return p.with_suffix(p.suffix + ".consensus.json")
    return Path("adl_consensus.json")


def _load_engine(state_path: Path) -> ConsensusEngine:
    engine = ConsensusEngine()
    if not state_path.exists():
        return engine

    data = json.loads(state_path.read_text(encoding="utf-8"))
    for cid, entries in data.get("chains", {}).items():
        chain = ConceptChain(cid)
        for raw in entries:
            entry = ConsensusEntry(
                adl_id=raw["adl_id"],
                from_status=DiscoveryStatus(raw["from_status"]),
                to_status=DiscoveryStatus(raw["to_status"]),
                actor=raw["actor"],
                reason=raw.get("reason", ""),
                parent_hash=raw.get("parent_hash", "0" * 64),
            )
            chain.append(entry)
        engine.chains[cid] = chain
    return engine


def _save_engine(engine: ConsensusEngine, state_path: Path) -> None:
    payload = {
        "chains": {
            cid: chain.history() for cid, chain in engine.chains.items()
        }
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _cmd_parse(args: argparse.Namespace) -> int:
    try:
        doc = parse_file(args.file)
    except (ADLParseError, OSError, ValueError) as exc:
        print(f"parse error: {exc}", file=sys.stderr)
        return 1

    if args.output == "json":
        print(doc.model_dump_json(indent=2))
    else:
        fm = doc.front_matter
        print(f"adl_id:     {fm.adl_id}")
        print(f"adl_type:   {fm.adl_type.value}")
        print(f"status:     {fm.status.value} {fm.status_badge}")
        print(f"scope:      {fm.scope}")
        print(f"concept:    {doc.concept_name}")
        print(f"relations:  {len(doc.relations)}")
        print(f"evidence:   {len(doc.evidence)}")
        print(f"seals:      {len(doc.seals)}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    validator = ADLValidator()
    any_errors = False

    for path_str in args.files:
        path = Path(path_str)
        try:
            doc = parse_file(path)
        except (ADLParseError, OSError, ValueError) as exc:
            print(f"{path}: parse error: {exc}", file=sys.stderr)
            any_errors = True
            continue

        errors = validator.validate_document(doc)
        if errors:
            any_errors = True
            print(f"{path}: FAIL ({len(errors)} error(s))", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
        else:
            print(f"{path}: OK")

    return 1 if any_errors else 0


def _cmd_store(args: argparse.Namespace) -> int:
    try:
        doc = parse_file(args.file)
    except (ADLParseError, OSError, ValueError) as exc:
        print(f"store error: {exc}", file=sys.stderr)
        return 1

    mem = ADLMemory(db_path=args.db)
    mem.store(doc)
    mem.close()
    print(f"stored {doc.adl_id} -> {args.db}")
    return 0


def _cmd_related(args: argparse.Namespace) -> int:
    mem = ADLMemory(db_path=args.db)
    related = mem.find_related(args.adl_id, depth=args.depth)
    mem.close()

    if not related:
        print(f"no related concepts for {args.adl_id} (depth={args.depth})")
        return 0

    for concept, relation, conf in related:
        print(f"{concept}\t{relation}\t{conf:.2f}")
    return 0


def _cmd_consensus_register(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    engine = _load_engine(state_path)

    if args.file:
        try:
            doc = parse_file(args.file)
        except (ADLParseError, OSError, ValueError) as exc:
            print(f"register error: {exc}", file=sys.stderr)
            return 1
        adl_id = doc.adl_id
        engine.register(doc)
    elif args.adl_id:
        if args.adl_id in engine.chains:
            print(f"already registered: {args.adl_id}")
        else:
            from .models import ADLDocument, ADLFrontMatter, ADLType, ProvisionalNames

            stub = ADLDocument(
                front_matter=ADLFrontMatter(
                    adl_type=ADLType.CONCEPT,
                    adl_id=args.adl_id,
                    scope="public",
                    provisional_names=ProvisionalNames(en=args.adl_id),
                )
            )
            engine.register(stub)
        adl_id = args.adl_id
    else:
        print("register requires --file or --adl-id", file=sys.stderr)
        return 1

    _save_engine(engine, state_path)
    print(f"registered {adl_id}")
    return 0


def _cmd_consensus_transition(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    engine = _load_engine(state_path)

    try:
        target = DiscoveryStatus(args.to)
    except ValueError:
        print(f"invalid status: {args.to}", file=sys.stderr)
        return 1

    try:
        entry = engine.transition(
            args.adl_id,
            target,
            actor=args.actor,
            reason=args.reason or "",
        )
    except (KeyError, ValueError) as exc:
        print(f"transition error: {exc}", file=sys.stderr)
        return 1

    _save_engine(engine, state_path)
    print(f"transition {args.adl_id}: {entry.from_status.value} -> {entry.to_status.value}")
    return 0


def _cmd_consensus_verify(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    engine = _load_engine(state_path)

    if args.adl_id not in engine.chains:
        print(f"not registered: {args.adl_id}", file=sys.stderr)
        return 1

    ok = engine.chains[args.adl_id].verify_integrity()
    status = engine.get_status(args.adl_id).value
    if ok:
        print(f"{args.adl_id}: chain OK (status={status})")
        return 0
    print(f"{args.adl_id}: chain INTEGRITY FAILED", file=sys.stderr)
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adl-lite",
        description="ADL Lite — parse, validate, store, and manage concept consensus",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse", help="Parse an ADL Markdown file")
    p_parse.add_argument("file", help="Path to .md document")
    p_parse.add_argument(
        "-o",
        "--output",
        choices=("json", "text"),
        default="text",
        help="Output format (default: text)",
    )
    p_parse.set_defaults(func=_cmd_parse)

    p_validate = sub.add_parser("validate", help="Validate one or more ADL files")
    p_validate.add_argument("files", nargs="+", help="Paths to .md documents")
    p_validate.set_defaults(func=_cmd_validate)

    p_store = sub.add_parser("store", help="Store document in ADLMemory database")
    p_store.add_argument("file", help="Path to .md document")
    p_store.add_argument("--db", required=True, help="SQLite database path")
    p_store.set_defaults(func=_cmd_store)

    p_related = sub.add_parser("related", help="Find related concepts via graph")
    p_related.add_argument("adl_id", help="Concept adl_id")
    p_related.add_argument("--db", required=True, help="SQLite database path")
    p_related.add_argument("--depth", type=int, default=1, help="Traversal depth")
    p_related.set_defaults(func=_cmd_related)

    p_consensus = sub.add_parser("consensus", help="Concept consensus chain")
    cons_sub = p_consensus.add_subparsers(dest="consensus_cmd", required=True)

    p_reg = cons_sub.add_parser("register", help="Register concept in consensus engine")
    p_reg.add_argument("file", nargs="?", help="ADL file to register")
    p_reg.add_argument("--adl-id", help="Register by id without file")
    p_reg.add_argument(
        "--state",
        default=None,
        help="Consensus state JSON (default: adl_consensus.json)",
    )
    p_reg.set_defaults(func=_cmd_consensus_register)

    p_trans = cons_sub.add_parser("transition", help="Transition concept status")
    p_trans.add_argument("adl_id", help="Concept adl_id")
    p_trans.add_argument("--to", required=True, dest="to", help="Target status")
    p_trans.add_argument("--actor", required=True, help="Actor id")
    p_trans.add_argument("--reason", default="", help="Reason text")
    p_trans.add_argument("--state", default=None, help="Consensus state JSON path")
    p_trans.set_defaults(func=_cmd_consensus_transition)

    p_verify = cons_sub.add_parser("verify", help="Verify consensus chain integrity")
    p_verify.add_argument("adl_id", help="Concept adl_id")
    p_verify.add_argument("--state", default=None, help="Consensus state JSON path")
    p_verify.set_defaults(func=_cmd_consensus_verify)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "state") and getattr(args, "state", None) is None:
        args.state = str(_default_state_path(None))

    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
