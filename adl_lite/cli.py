"""
ADL Lite — command-line interface (stdlib argparse).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .consensus import ConsensusEngine
from .lark.announce import announce
from .lark.client import LarkCliError, LarkCliNotFoundError, auth_status, find_lark_cli
from .lark.dashboard import init_dashboard, sync_dashboard_row
from .lark.listen import listen, save_listen_state
from .lark.namespace import LarkNamespaceRegistry, resolve_wiki_space_for_scope, scope_to_adl_uri
from .lark.publish import publish_file
from .lark.registry import LarkRegistry
from .lark.sync_memory import sync_memory
from .memory import ADLMemory
from .models import DiscoveryStatus, Event, EventChain
from .ontology import OntologyManager
from .parser import ADLParseError, parse_file
from .validator import ADLValidator

_REPO_ROOT = Path(__file__).resolve().parents[1]


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
    for cid, events_data in data.get("chains", {}).items():
        chain = EventChain(concept_id=cid)
        for raw in events_data:
            event = Event(
                concept_id=cid,
                event_type=raw.get("event_type", "register"),
                actor=raw.get("actor", "system"),
                reasoning=raw.get("reasoning", raw.get("reason", "")),
                timestamp=raw.get("timestamp", ""),
                payload=raw.get("payload", {}),
            )
            # Preserve original event_id, hash, and prev_hash for round-trip fidelity
            if "event_id" in raw:
                event.event_id = raw["event_id"]
            if "hash" in raw:
                event.hash = raw["hash"]
            if "_prev_hash" in raw:
                event._prev_hash = raw["_prev_hash"]
            chain.append(event)
        engine.chains[cid] = chain
    return engine


def _save_engine(engine: ConsensusEngine, state_path: Path) -> None:
    payload = {
        "chains": {
            cid: [
                {
                    "event_id": e["event_id"],
                    "event_type": e["event_type"],
                    "actor": e["actor"],
                    "reasoning": e["reasoning"],
                    "timestamp": e["timestamp"],
                    "hash": e["hash"],
                    "payload": e.get("payload", {}),
                }
                for e in chain.history()
            ]
            for cid, chain in engine.chains.items()
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
    validator = ADLValidator(strict=args.strict)
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
    print(f"transition {args.adl_id} -> {entry.event_type.value} (actor={entry.actor})")

    if getattr(args, "lark_sync", False) and args.sheet:
        reg_path = (
            Path(args.registry)
            if getattr(args, "registry", None)
            else Path(".adl_lark_registry.json")
        )
        try:
            sync_dashboard_row(
                args.adl_id,
                sheet_title=args.sheet,
                registry_path=reg_path,
                db_path=getattr(args, "db", None),
                state_path=state_path,
                dry_run=getattr(args, "dry_run", False),
                lark_cli=getattr(args, "lark_cli", None),
            )
            print(f"  lark dashboard row synced -> {args.sheet}")
        except (KeyError, ValueError, LarkCliError) as exc:
            print(f"  lark-sync warning: {exc}", file=sys.stderr)
    return 0


def _cmd_ontology_query(args: argparse.Namespace) -> int:
    ontology_path = Path(args.ontology) if args.ontology else None
    try:
        mgr = OntologyManager(ontology_path)
        data = mgr.query_schema(
            predicate=args.predicate,
            from_status=args.from_status,
            to_status=args.to_status,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ontology error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print(f"ontology: {data['path']}")
    print(f"version:  {data['version'] or '?'}")
    print(f"classes:  {len(data['classes'])}")
    print(f"predicates ({len(data['predicates'])}): {', '.join(data['predicates']) or '(none)'}")
    print(f"scope_prefixes: {', '.join(data['scope_prefixes'])}")
    print(f"mapping_types: {', '.join(data['mapping_types'])}")

    if args.predicate:
        valid = data.get("predicate_valid", False)
        print(f"predicate '{args.predicate}': {'valid' if valid else 'unknown'}")
        if valid:
            allowed = data.get("allowed_mapping_types", [])
            print(f"  allowed_mapping_types: {', '.join(allowed) or '(any)'}")

    if args.from_status or args.to_status:
        if args.from_status and args.to_status:
            ok = data.get("is_valid_transition", False)
            print(
                f"transition {args.from_status} -> {args.to_status}: "
                f"{'allowed' if ok else 'denied'}"
            )
        elif args.from_status:
            targets = data["allowed_transitions"].get(args.from_status, [])
            print(f"from {args.from_status}: {', '.join(targets) or '(terminal)'}")

    if not args.from_status and not args.predicate:
        print("status_transitions:")
        for status, targets in sorted(data["allowed_transitions"].items()):
            label = ", ".join(targets) if targets else "(terminal)"
            print(f"  {status}: {label}")

    return 0


def _cmd_ontology_validate(args: argparse.Namespace) -> int:
    ontology_path = Path(args.ontology) if args.ontology else None
    try:
        mgr = OntologyManager(ontology_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ontology error: {exc}", file=sys.stderr)
        return 1

    print(f"ontology: {mgr.path}")
    print(f"version:  {mgr.version or '?'}")
    print(f"classes:  {len(mgr.list_classes())}")
    print(f"predicates: {len(mgr.list_predicates())}")
    print(f"statuses: {len(mgr.status_transition_graph())}")

    paths: list[Path] = [Path(p) for p in args.files]
    if args.examples:
        paths.extend(sorted((_REPO_ROOT / "examples").glob("*.md")))
    if args.aml and (_REPO_ROOT / "data" / "aml" / "concepts").is_dir():
        paths.extend(sorted((_REPO_ROOT / "data" / "aml" / "concepts").glob("*.md")))

    if not paths:
        return 0

    validator = ADLValidator(strict=True, ontology=mgr)
    any_errors = False
    for path in paths:
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


def _cmd_lark_doctor(args: argparse.Namespace) -> int:
    try:
        binary = find_lark_cli(args.lark_cli)
    except LarkCliNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"lark-cli: {binary}")
    try:
        status = auth_status(lark_cli=args.lark_cli)
    except LarkCliError as exc:
        print(f"auth: not ready ({exc})", file=sys.stderr)
        print(
            "  run: lark-cli config init --new && lark-cli auth login --recommend",
            file=sys.stderr,
        )
        return 1

    print("auth: ok")
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        user = status.get("user") or status.get("data") or status
        if isinstance(user, dict):
            name = user.get("name") or user.get("user_id") or "?"
            print(f"  identity: {name}")
    return 0


def _cmd_lark_publish(args: argparse.Namespace) -> int:
    registry = None
    if args.registry:
        registry = LarkRegistry(Path(args.registry))

    try:
        namespaces_path = Path(args.namespaces) if getattr(args, "namespaces", None) else None
        result = publish_file(
            args.file,
            title=args.title,
            folder_token=args.folder_token,
            wiki_node=args.wiki_node,
            wiki_space=args.wiki_space,
            namespaces_path=namespaces_path,
            api_version=args.api_version,
            strict_validate=args.strict,
            dry_run=args.dry_run,
            lark_cli=args.lark_cli,
            registry=registry,
        )
    except (LarkCliNotFoundError, LarkCliError, ValueError, FileNotFoundError) as exc:
        print(f"publish error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "adl_id": result.adl_id,
                    "title": result.title,
                    "doc_id": result.doc_id,
                    "doc_url": result.doc_url,
                    "dry_run": result.dry_run,
                    "source_path": result.source_path,
                },
                indent=2,
            )
        )
    else:
        label = "dry-run" if result.dry_run else "published"
        print(f"{label} {result.adl_id}")
        print(f"  title:   {result.title}")
        print(f"  doc_id:  {result.doc_id}")
        print(f"  doc_url: {result.doc_url}")
        if registry and not result.dry_run:
            print(f"  registry: {args.registry}")
    return 0


def _cmd_lark_sync_memory(args: argparse.Namespace) -> int:
    registry_path = Path(args.registry) if args.registry else None
    try:
        result = sync_memory(
            args.db,
            base=args.base,
            mode=args.mode,
            table=args.table,
            dry_run=args.dry_run,
            lark_cli=args.lark_cli,
            registry_path=registry_path,
        )
    except (LarkCliNotFoundError, LarkCliError, ValueError) as exc:
        print(f"sync-memory error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.__dict__, indent=2))
    else:
        label = "dry-run" if result.dry_run else "synced"
        print(
            f"{label} {result.synced} record(s) -> base {result.base_token} "
            f"table {result.table_id} (+{result.created} / ~{result.updated})"
        )
    return 0


def _cmd_lark_announce(args: argparse.Namespace) -> int:
    registry = LarkRegistry(Path(args.registry)) if args.registry else None
    try:
        result = announce(
            args.target,
            chat_id=args.chat_id,
            template=args.template,
            dry_run=args.dry_run,
            lark_cli=args.lark_cli,
            registry=registry,
        )
    except (LarkCliNotFoundError, LarkCliError, ValueError, FileNotFoundError) as exc:
        print(f"announce error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.__dict__, indent=2))
    else:
        print(f"announced {result.adl_id} -> chat {result.chat_id} ({result.template})")
        if result.message_id:
            print(f"  message_id: {result.message_id}")
    return 0


def _cmd_lark_listen(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    engine = _load_engine(state_path)
    feedback_file = Path(args.feedback_file) if args.feedback_file else None

    try:
        result = listen(
            chat_id=args.chat_id,
            stdin=args.stdin,
            feedback_file=feedback_file,
            poll_messages=args.poll,
            engine=engine,
            threshold=args.threshold,
            auto_transition=args.auto_transition,
            lark_cli=args.lark_cli,
        )
    except (LarkCliNotFoundError, LarkCliError, ValueError) as exc:
        print(f"listen error: {exc}", file=sys.stderr)
        return 1

    if args.auto_transition and result.transitions:
        _save_engine(engine, state_path)

    listen_state = (
        Path(args.listen_state) if args.listen_state else state_path.with_suffix(".listen.json")
    )
    save_listen_state(result, listen_state)

    if args.json:
        print(
            json.dumps(
                {
                    "endorsements": result.endorsements,
                    "transitions": result.transitions,
                    "events": len(result.events),
                },
                indent=2,
            )
        )
    else:
        print(f"listen: {len(result.events)} event(s), endorsements={result.endorsements}")
        if result.transitions:
            print(f"  auto-transitioned: {', '.join(result.transitions)}")
    return 0


def _cmd_lark_init_dashboard(args: argparse.Namespace) -> int:
    columns = [c.strip() for c in args.columns.split(",") if c.strip()]
    state_path = Path(args.state) if args.state else None
    registry_path = Path(args.registry) if args.registry else Path(".adl_lark_registry.json")
    try:
        result = init_dashboard(
            args.sheet,
            db_path=args.db,
            columns=columns,
            state_path=state_path,
            registry_path=registry_path,
            dry_run=args.dry_run,
            lark_cli=args.lark_cli,
        )
    except (LarkCliNotFoundError, LarkCliError, ValueError) as exc:
        print(f"init-dashboard error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.__dict__, indent=2))
    else:
        print(
            f"dashboard {result.title}: token={result.spreadsheet_token} rows={result.rows_written}"
        )
    return 0


def _cmd_lark_map_namespace(args: argparse.Namespace) -> int:
    ns_path = Path(args.namespaces) if args.namespaces else Path(".adl_lark_namespaces.json")
    reg_path = Path(args.registry) if args.registry else None

    if args.wiki_space:
        uri = args.scope if args.scope.startswith("adl://") else scope_to_adl_uri(args.scope)
        if reg_path:
            LarkRegistry(reg_path).set_namespace(uri, args.wiki_space)
        LarkNamespaceRegistry(ns_path).set_mapping(uri, args.wiki_space)
        print(f"mapped {uri} -> {args.wiki_space}")
        return 0

    resolved = resolve_wiki_space_for_scope(
        args.scope,
        namespaces_path=ns_path,
        registry_data=LarkRegistry(reg_path).load() if reg_path and reg_path.exists() else None,
    )
    if resolved:
        print(f"{args.scope} -> {resolved}")
    else:
        print(f"no mapping for scope {args.scope}", file=sys.stderr)
        return 1
    return 0


def _cmd_lark_namespace(args: argparse.Namespace) -> int:
    ns_path = Path(args.namespaces) if args.namespaces else Path(".adl_lark_namespaces.json")
    reg_path = Path(args.registry) if args.registry else None

    if args.namespace_cmd == "list":
        mappings: dict[str, str] = {}
        if ns_path.exists():
            mappings.update(LarkNamespaceRegistry(ns_path).list_mappings())
        if reg_path and reg_path.exists():
            mappings.update(LarkRegistry(reg_path).list_namespaces())
        if args.json:
            print(json.dumps(mappings, indent=2, ensure_ascii=False))
        elif mappings:
            for uri, space in sorted(mappings.items()):
                print(f"{uri}\t{space}")
        else:
            print("(no namespace mappings)")
        return 0

    if args.namespace_cmd == "set":
        uri = args.adl_uri if args.adl_uri.endswith("/") else f"{args.adl_uri}/"
        LarkNamespaceRegistry(ns_path).set_mapping(uri, args.wiki_space)
        if reg_path:
            LarkRegistry(reg_path).set_namespace(uri, args.wiki_space)
        print(f"set {uri} -> {args.wiki_space}")
        return 0

    print(f"unknown namespace command: {args.namespace_cmd}", file=sys.stderr)
    return 1


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
    p_validate.add_argument(
        "--strict",
        action="store_true",
        help="Reject unknown L3 relation predicates (ontology registry)",
    )
    p_validate.set_defaults(func=_cmd_validate, strict=False)

    p_store = sub.add_parser("store", help="Store document in ADLMemory database")
    p_store.add_argument("file", help="Path to .md document")
    p_store.add_argument("--db", required=True, help="SQLite database path")
    p_store.set_defaults(func=_cmd_store)

    p_related = sub.add_parser("related", help="Find related concepts via graph")
    p_related.add_argument("adl_id", help="Concept adl_id")
    p_related.add_argument("--db", required=True, help="SQLite database path")
    p_related.add_argument("--depth", type=int, default=1, help="Traversal depth")
    p_related.set_defaults(func=_cmd_related)

    p_ontology = sub.add_parser("ontology", help="Core ontology registry (YAML)")
    onto_sub = p_ontology.add_subparsers(dest="ontology_cmd", required=True)

    p_onto_val = onto_sub.add_parser(
        "validate",
        help="Load ontology YAML; optionally strict-validate ADL files",
    )
    p_onto_val.add_argument(
        "files",
        nargs="*",
        help="ADL .md paths (omit with no --examples/--aml for YAML-only check)",
    )
    p_onto_val.add_argument(
        "--ontology",
        default=None,
        help="Path to adl_core_ontology.yaml (default: packaged registry)",
    )
    p_onto_val.add_argument(
        "--examples",
        action="store_true",
        help="Also strict-validate all examples/*.md",
    )
    p_onto_val.add_argument(
        "--aml",
        action="store_true",
        help="Also strict-validate data/aml/concepts/*.md when present",
    )
    p_onto_val.set_defaults(func=_cmd_ontology_validate)

    p_onto_q = onto_sub.add_parser(
        "query",
        help="Introspect predicates, transitions, scopes (agent schema lookup)",
    )
    p_onto_q.add_argument(
        "--ontology",
        default=None,
        help="Path to adl_core_ontology.yaml (default: packaged registry)",
    )
    p_onto_q.add_argument(
        "--predicate",
        default=None,
        help="Filter to one L3 relation predicate",
    )
    p_onto_q.add_argument(
        "--from-status",
        default=None,
        dest="from_status",
        help="Filter transitions from this status",
    )
    p_onto_q.add_argument(
        "--to-status",
        default=None,
        dest="to_status",
        help="With --from-status, check if this target is allowed",
    )
    p_onto_q.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON (matches adl_ontology_query tool)",
    )
    p_onto_q.set_defaults(func=_cmd_ontology_query)

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
    p_trans.add_argument(
        "--lark-sync",
        action="store_true",
        help="Append/update Feishu sheet row after transition (--sheet required)",
    )
    p_trans.add_argument(
        "--sheet",
        default=None,
        help="Dashboard sheet title (registry dashboards.*)",
    )
    p_trans.add_argument("--registry", default=None, help="Lark registry JSON for dashboard sync")
    p_trans.add_argument("--db", default=None, help="ADLMemory SQLite db for dashboard row fields")
    p_trans.add_argument("--lark-cli", default=None, help="Path to lark-cli binary")
    p_trans.add_argument("--dry-run", action="store_true", help="Dry-run lark-cli dashboard append")
    p_trans.set_defaults(func=_cmd_consensus_transition)

    p_verify = cons_sub.add_parser("verify", help="Verify consensus chain integrity")
    p_verify.add_argument("adl_id", help="Concept adl_id")
    p_verify.add_argument("--state", default=None, help="Consensus state JSON path")
    p_verify.set_defaults(func=_cmd_consensus_verify)

    p_lark = sub.add_parser(
        "lark",
        help="Feishu/Lark bridge via lark-cli (https://github.com/larksuite/cli)",
    )
    lark_sub = p_lark.add_subparsers(dest="lark_cmd", required=True)

    p_lark_doc = lark_sub.add_parser(
        "doctor",
        help="Check lark-cli install and authentication",
    )
    p_lark_doc.add_argument(
        "--lark-cli",
        default=None,
        help="Path to lark-cli binary (default: search PATH)",
    )
    p_lark_doc.add_argument("--json", action="store_true", help="Emit auth status JSON")
    p_lark_doc.set_defaults(func=_cmd_lark_doctor)

    p_lark_pub = lark_sub.add_parser(
        "publish",
        help="Create Feishu doc from ADL Markdown (full L1/L2/L3 file)",
    )
    p_lark_pub.add_argument("file", help="Path to ADL .md document")
    p_lark_pub.add_argument(
        "--title", default=None, help="Feishu doc title (default: concept name)"
    )
    p_lark_pub.add_argument("--folder-token", default=None, help="Parent folder token")
    p_lark_pub.add_argument("--wiki-node", default=None, help="Wiki node token or URL")
    p_lark_pub.add_argument("--wiki-space", default=None, help="Wiki space id (e.g. my_library)")
    p_lark_pub.add_argument(
        "--api-version",
        default="v2",
        choices=("v1", "v2"),
        help="lark-cli docs API version (default: v2)",
    )
    p_lark_pub.add_argument(
        "--registry",
        default=None,
        help="JSON registry path to record adl_id -> doc_id mapping",
    )
    p_lark_pub.add_argument(
        "--namespaces",
        default=None,
        help="Namespace map JSON (default: .adl_lark_namespaces.json)",
    )
    p_lark_pub.add_argument(
        "--strict",
        action="store_true",
        help="Reject invalid ADL before publish (ontology-aware validator)",
    )
    p_lark_pub.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --dry-run to lark-cli (preview request only)",
    )
    p_lark_pub.add_argument("--lark-cli", default=None, help="Path to lark-cli binary")
    p_lark_pub.add_argument("--json", action="store_true", help="Emit JSON result")
    p_lark_pub.set_defaults(func=_cmd_lark_publish)

    p_lark_sync = lark_sub.add_parser(
        "sync-memory",
        help="Sync ADLMemory warm layer to Feishu Base",
    )
    p_lark_sync.add_argument("--db", required=True, help="SQLite ADLMemory database path")
    p_lark_sync.add_argument("--base", required=True, help="Base name or bas* token")
    p_lark_sync.add_argument("--mode", default="warm", choices=("warm",), help="Sync mode")
    p_lark_sync.add_argument("--table", default="concepts", help="Base table name or id")
    p_lark_sync.add_argument(
        "--registry", default=None, help="Registry for doc links / base name map"
    )
    p_lark_sync.add_argument("--dry-run", action="store_true")
    p_lark_sync.add_argument("--lark-cli", default=None)
    p_lark_sync.add_argument("--json", action="store_true")
    p_lark_sync.set_defaults(func=_cmd_lark_sync_memory)

    p_lark_ann = lark_sub.add_parser("announce", help="Broadcast discovery to IM chat")
    p_lark_ann.add_argument("target", help="adl_id or path to .md file")
    p_lark_ann.add_argument("--chat-id", required=True, help="Feishu chat id (oc_xxx)")
    p_lark_ann.add_argument(
        "--template",
        default="discovery_broadcast",
        help="Message template name",
    )
    p_lark_ann.add_argument("--registry", default=None)
    p_lark_ann.add_argument("--dry-run", action="store_true")
    p_lark_ann.add_argument("--lark-cli", default=None)
    p_lark_ann.add_argument("--json", action="store_true")
    p_lark_ann.set_defaults(func=_cmd_lark_announce)

    p_lark_listen = lark_sub.add_parser(
        "listen",
        help="Ingest consensus feedback (stdin/file/poll); optional auto-transition",
    )
    p_lark_listen.add_argument("--chat-id", default=None, help="Chat id for --poll")
    p_lark_listen.add_argument(
        "--mode",
        default="consensus_feedback",
        choices=("consensus_feedback",),
    )
    p_lark_listen.add_argument(
        "--stdin",
        action="store_true",
        help="Read feedback lines from stdin",
    )
    p_lark_listen.add_argument(
        "--feedback-file",
        default=None,
        help="File with feedback lines (adl_id|actor|text)",
    )
    p_lark_listen.add_argument(
        "--poll",
        action="store_true",
        help="Fetch recent chat messages via lark-cli (MVP)",
    )
    p_lark_listen.add_argument("--auto-transition", action="store_true")
    p_lark_listen.add_argument("--threshold", type=int, default=2)
    p_lark_listen.add_argument("--state", default=None, help="Consensus state JSON")
    p_lark_listen.add_argument(
        "--listen-state",
        default=None,
        help="Write listen summary JSON (default: <state>.listen.json)",
    )
    p_lark_listen.add_argument("--lark-cli", default=None)
    p_lark_listen.add_argument("--json", action="store_true")
    p_lark_listen.set_defaults(func=_cmd_lark_listen)

    p_lark_dash = lark_sub.add_parser(
        "init-dashboard",
        help="Create Feishu sheet consensus board from memory + state",
    )
    p_lark_dash.add_argument("--sheet", required=True, help="Spreadsheet title")
    p_lark_dash.add_argument(
        "--columns",
        default="concept_id,status_badge,confidence,discoverer,validators,last_update,doc_link",
        help="Comma-separated column headers",
    )
    p_lark_dash.add_argument("--db", required=True, help="SQLite ADLMemory database")
    p_lark_dash.add_argument("--state", default=None, help="Consensus state JSON")
    p_lark_dash.add_argument("--registry", default=None, help="Lark registry JSON")
    p_lark_dash.add_argument("--dry-run", action="store_true")
    p_lark_dash.add_argument("--lark-cli", default=None)
    p_lark_dash.add_argument("--json", action="store_true")
    p_lark_dash.set_defaults(func=_cmd_lark_init_dashboard)

    p_lark_map = lark_sub.add_parser(
        "map-namespace",
        help="Show or set wiki space for an ADL scope prefix",
    )
    p_lark_map.add_argument("--scope", required=True, help="ADL scope or adl:// URI")
    p_lark_map.add_argument("--wiki-space", default=None, help="Wiki space id to set")
    p_lark_map.add_argument("--namespaces", default=None)
    p_lark_map.add_argument("--registry", default=None)
    p_lark_map.set_defaults(func=_cmd_lark_map_namespace)

    p_lark_ns = lark_sub.add_parser("namespace", help="List or set namespace mappings")
    ns_sub = p_lark_ns.add_subparsers(dest="namespace_cmd", required=True)

    p_ns_list = ns_sub.add_parser("list", help="List scope -> wiki_space mappings")
    p_ns_list.add_argument("--namespaces", default=None)
    p_ns_list.add_argument("--registry", default=None)
    p_ns_list.add_argument("--json", action="store_true")
    p_ns_list.set_defaults(func=_cmd_lark_namespace)

    p_ns_set = ns_sub.add_parser("set", help="Set adl:// URI -> wiki_space")
    p_ns_set.add_argument("adl_uri", help="e.g. adl://private/ceiec-aml/")
    p_ns_set.add_argument("wiki_space", help="Feishu wiki space id")
    p_ns_set.add_argument("--namespaces", default=None)
    p_ns_set.add_argument("--registry", default=None)
    p_ns_set.set_defaults(func=_cmd_lark_namespace)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "state") and getattr(args, "state", None) is None:
        args.state = str(_default_state_path(None))

    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
