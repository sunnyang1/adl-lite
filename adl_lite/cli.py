"""
ADL Lite — command-line interface (stdlib argparse).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .consensus import ConsensusEngine
from .exceptions import ADLConsensusError, ADLOntologyError, ADLTemplateError
from .logging_config import get_logger
from .memory import ADLMemory
from .models import DiscoveryStatus, Event, EventChain
from .ontology import OntologyManager
from .parser import ADLParseError, parse_file
from .validator import ADLValidator

logger = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _default_state_path(db_path: str | None) -> Path:
    if db_path:
        p = Path(db_path)
        return p.with_suffix(p.suffix + ".consensus.json")
    return Path("adl_consensus.json")


def _load_engine(state_path: Path) -> ConsensusEngine:
    engine = ConsensusEngine(dev_mode=True)  # CLI defaults to dev mode for backward compat
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
        doc = parse_file(args.file, strict_template=getattr(args, "strict_template", False))
    except (ADLParseError, OSError, ValueError, ADLTemplateError) as exc:
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
        print(f"capability: {doc.concept_name}")
        print(f"relations:  {len(doc.relations)}")
        print(f"evidence:   {len(doc.evidence)}")
        print(f"seals:      {len(doc.seals)}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    if args.shacl:
        shacl = True
    elif args.no_shacl:
        shacl = False
    else:
        shacl = None  # auto-detect

    validator = ADLValidator(shacl=shacl, strict=args.strict)
    any_errors = False

    for path_str in args.files:
        path = Path(path_str)
        try:
            doc = parse_file(path, strict_template=getattr(args, "strict_template", False))
        except (ADLParseError, OSError, ValueError, ADLTemplateError) as exc:
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


def _cmd_shacl(args: argparse.Namespace) -> int:
    from .shacl_validation import validate_adl_document as shacl_validate

    all_pass = True
    for path_str in args.files:
        p = Path(path_str)
        try:
            doc = parse_file(str(p))
            conforms, report = shacl_validate(doc)
            if conforms:
                print(f"{p.name}: SHACL OK")
            else:
                print(f"{p.name}: SHACL FAILED")
                for line in report.splitlines():
                    if line.strip():
                        print(f"  {line.strip()}")
                all_pass = False
        except Exception as e:
            print(f"{p.name}: ERROR — {e}", file=sys.stderr)
            all_pass = False

    return 0 if all_pass else 1


def _cmd_store(args: argparse.Namespace) -> int:
    try:
        doc = parse_file(args.file, strict_template=getattr(args, "strict_template", False))
    except (ADLParseError, OSError, ValueError, ADLTemplateError) as exc:
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
        print(f"no related capabilities for {args.adl_id} (depth={args.depth})")
        return 0

    for concept, relation, conf in related:
        print(f"{concept}\t{relation}\t{conf:.2f}")
    return 0


def _cmd_consensus_register(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    engine = _load_engine(state_path)

    if args.file:
        try:
            doc = parse_file(args.file, strict_template=getattr(args, "strict_template", False))
        except (ADLParseError, OSError, ValueError, ADLTemplateError) as exc:
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
    except (KeyError, ValueError, ADLConsensusError) as exc:
        print(f"transition error: {exc}", file=sys.stderr)
        return 1

    if entry is None:
        print("transition failed: no event returned", file=sys.stderr)
        return 1

    _save_engine(engine, state_path)
    print(f"transition {args.adl_id} -> {entry.event_type.value} (actor={entry.actor})")
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
    except (FileNotFoundError, ValueError, ADLOntologyError) as exc:
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
    except (FileNotFoundError, ValueError, ADLOntologyError) as exc:
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
            doc = parse_file(path, strict_template=getattr(args, "strict_template", False))
        except (ADLParseError, OSError, ValueError, ADLTemplateError) as exc:
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


def _cmd_anchor(args: argparse.Namespace) -> int:
    import json as _json

    from .key_registry import TransparencyAnchor

    state_path = Path(args.state)
    engine = _load_engine(state_path)

    if not engine.chains:
        print("no chains to anchor", file=sys.stderr)
        return 1

    chains = list(engine.chains.values())
    anchor = TransparencyAnchor(args.output)
    value = anchor.anchor(chains, use_merkle=args.merkle)
    mode = "Merkle" if args.merkle else "flat"
    print(f"anchored {len(chains)} chains -> {args.output} ({mode}: {value})")

    if args.merkle and args.proofs_dir:
        proofs_dir = Path(args.proofs_dir)
        proofs_dir.mkdir(parents=True, exist_ok=True)
        for chain in chains:
            proof = anchor.prove_inclusion(chain)
            if proof:
                path = proofs_dir / f"{chain.concept_id}.proof.json"
                path.write_text(_json.dumps(proof.__dict__, indent=2), encoding="utf-8")
        print(f"wrote inclusion proofs -> {proofs_dir}")
    return 0


def _cmd_verify_anchor(args: argparse.Namespace) -> int:
    from .key_registry import TransparencyAnchor

    anchor = TransparencyAnchor(args.file)
    if args.commit:
        ok = anchor.verify_anchor_at_commit(args.commit)
        if ok:
            print(f"anchor verified at commit {args.commit}")
            return 0
        print(f"anchor NOT verified at commit {args.commit}", file=sys.stderr)
        return 1

    if not anchor.anchor_path.exists():
        print("anchor file not found", file=sys.stderr)
        return 1

    # Load chains from state to verify against anchor
    state_path = Path(getattr(args, "state", _default_state_path(None)))
    engine = _load_engine(state_path)

    # Attach loaded chains to the anchor so verify_anchor() computes the correct expected hash
    chains = list(engine.chains.values())
    anchor._last_chains = chains
    # If the anchor was created with --merkle, also compute the Merkle tree so
    # verify_anchor() compares against the Merkle root rather than a flat SHA-256.
    if anchor.anchor_path.exists():
        content = anchor.anchor_path.read_text(encoding="utf-8")
        if "Merkle" in content:
            anchor._last_tree = anchor._compute_merkle_anchor(chains)

    ok = anchor.verify_anchor()
    if ok:
        print("anchor OK")
        # Verify each chain's integrity against the loaded state
        if engine.chains:
            chain_results = engine.verify_all()
            failures = [cid for cid, intact in chain_results.items() if not intact]
            if failures:
                print(f"chain integrity failures: {failures}", file=sys.stderr)
                return 1
            print(f"all {len(chain_results)} chains verified")
        return 0
    print("anchor MISMATCH", file=sys.stderr)
    return 1


def _cmd_verify_inclusion(args: argparse.Namespace) -> int:
    import json as _json

    from .key_registry import TransparencyAnchor
    from .merkle import MerkleProof

    state_path = Path(args.state)
    engine = _load_engine(state_path)

    if args.adl_id not in engine.chains:
        print(f"not registered: {args.adl_id}", file=sys.stderr)
        return 1

    proof_path = Path(args.proof)
    if not proof_path.exists():
        print(f"proof file not found: {args.proof}", file=sys.stderr)
        return 1

    data = _json.loads(proof_path.read_text(encoding="utf-8"))
    proof = MerkleProof(**data)
    anchor = TransparencyAnchor(args.anchor)
    ok = anchor.verify_inclusion(engine.chains[args.adl_id], proof)
    if ok:
        print(f"{args.adl_id}: inclusion proof OK")
        return 0
    print(f"{args.adl_id}: inclusion proof FAILED", file=sys.stderr)
    return 1


def _cmd_verify_batch(args: argparse.Namespace) -> int:
    import json as _json

    from .key_registry import TransparencyAnchor
    from .merkle import MerkleProof

    state_path = Path(args.state) if args.state else _default_state_path(None)
    engine = _load_engine(state_path)

    anchor_path = Path(args.anchor)
    if not anchor_path.exists():
        print(f"anchor file not found: {args.anchor}", file=sys.stderr)
        return 1

    content = anchor_path.read_text(encoding="utf-8")
    root_line = next((line for line in content.split("\n") if "Root:" in line), "")
    merkle_root = root_line.split("`")[1] if "`" in root_line else ""

    proofs_dir = Path(args.proofs_dir) if args.proofs_dir else Path(".adl/proofs")

    proofs: dict = {}
    if proofs_dir.exists():
        for pf in sorted(proofs_dir.glob("*.proof.json")):
            data = _json.loads(pf.read_text(encoding="utf-8"))
            proof = MerkleProof(**data)
            cid = pf.stem.replace(".proof", "")
            proofs[cid] = proof

    chains = list(engine.chains.values())
    if not chains:
        print("no chains loaded", file=sys.stderr)
        return 1

    results = TransparencyAnchor.verify_batch(chains, merkle_root, proofs)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    if passed == total:
        print(f"all {total} chains verified")
        return 0

    for cid, ok in results.items():
        if not ok:
            print(f"  FAILED: {cid}", file=sys.stderr)
    print(f"{passed}/{total} chains verified, {total - passed} failed", file=sys.stderr)
    return 1


def _cmd_normalize(args: argparse.Namespace) -> int:
    from .parser import parse_file

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"input-dir not found: {input_dir}", file=sys.stderr)
        return 1

    try:
        from .canonicalization import CanonicalizationEngine, OpenAILLMBackend
        from .vector_index import VectorIndex
    except ImportError as exc:
        print(
            f"VectorIndex/CanonicalizationEngine dependencies are missing: {exc}\n"
            'Install embeddings extras with: pip install -e ".[embeddings]"',
            file=sys.stderr,
        )
        return 1

    backend = None
    if args.llm_provider == "openai":
        try:
            backend = OpenAILLMBackend(model=args.llm_model)
        except ImportError as exc:
            print(
                f"OpenAI backend is not available: {exc}\n"
                'Install with: pip install -e ".[embeddings]"',
                file=sys.stderr,
            )
            return 1

    try:
        vector_index = VectorIndex()
    except ImportError as exc:
        print(
            f"Could not create VectorIndex: {exc}\n"
            'Install embeddings extras with: pip install -e ".[embeddings]"',
            file=sys.stderr,
        )
        return 1

    memory = ADLMemory(vector_index=vector_index)

    parsed = 0
    for path in sorted(input_dir.glob("*.md")):
        try:
            doc = parse_file(path)
        except Exception as exc:
            print(f"{path}: parse error: {exc}", file=sys.stderr)
            continue
        memory.store_with_events(doc)
        parsed += 1

    engine = CanonicalizationEngine(
        vector_index=vector_index,
        llm=backend,
        threshold=args.threshold,
    )
    results = engine.normalize(dry_run=not args.execute)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(f"Parsed {parsed} documents; found {len(results)} candidate cluster(s).")
        for r in results:
            cluster = ", ".join(r["cluster"])
            print(f"\nCluster: {cluster}")
            print(f"  canonical: {r['proposal'].get('canonical_adl_id')}")
            print(f"  actions: {len(r['actions'])}")
            print(f"  executed: {r.get('executed', False)}")

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


def _cmd_mcp(args: argparse.Namespace) -> int:
    """Start the ADL Lite MCP tool server (requires the [mcp] extra).

    Two exit paths:
      * mcp package not installed -> install guidance + exit 1
      * success                   -> blocks serving on the chosen transport
    """
    try:
        from .mcp_server import create_mcp_server
    except ImportError as exc:
        print(
            "The MCP server requires the optional 'mcp' extra.\n"
            "Install it with: pip install adl-lite[mcp]",
            file=sys.stderr,
        )
        print(f"(detail: {exc})", file=sys.stderr)
        return 1

    server = create_mcp_server(state_path=args.state_path)
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        # FastMCP reads host/port for streamable-http from its settings.
        try:
            server.settings.port = args.port
        except AttributeError:
            # Older FastMCP versions expose no mutable settings.port —
            # fall back to the library default port.
            logger.debug("FastMCP settings.port unavailable; using library default port")
        server.run(transport="streamable-http")
    return 0


def _cmd_neo4j_status(args: argparse.Namespace) -> int:
    """Check Neo4j connection status and node count.

    Three exit paths:
      * driver not installed  -> graceful degradation message + exit 1
      * connection failure    -> readable error + exit 1
      * success               -> prints status + node count, exit 0
    """
    from .config import get_neo4j_config
    from .neo4j_adapter import Neo4jGraphAdapter

    config = get_neo4j_config()
    uri = args.uri or config["uri"]
    user = args.user or config["user"]
    password = args.password or config["password"]

    adapter = None
    try:
        adapter = Neo4jGraphAdapter(uri=uri, user=user, password=password)
        count = adapter.node_count()
    except ImportError as exc:
        # Driver library not installed -> graceful degradation (non-zero exit).
        print(
            "Neo4j driver not installed. Enable the graph backend with:\n"
            "    pip install adl-lite[neo4j]",
            file=sys.stderr,
        )
        print(f"(detail: {exc})", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Neo4j connection FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        if adapter is not None:
            try:
                adapter.close()
            except Exception:
                logger.warning("Failed to close Neo4j adapter cleanly", exc_info=True)

    print("Neo4j connection OK")
    print(f"  URI:   {uri}")
    print(f"  Nodes: {count}")
    return 0


def _cmd_neo4j_check(args: argparse.Namespace) -> int:
    """Brief Neo4j connectivity health check (alias of `status` focused on liveness)."""
    from .config import get_neo4j_config
    from .neo4j_adapter import Neo4jGraphAdapter

    config = get_neo4j_config()
    uri = args.uri or config["uri"]
    user = args.user or config["user"]
    password = args.password or config["password"]

    adapter = None
    try:
        adapter = Neo4jGraphAdapter(uri=uri, user=user, password=password)
        ok = adapter.verify_connectivity()
    except ImportError as exc:
        print(
            "Neo4j driver not installed. Enable the graph backend with:\n"
            "    pip install adl-lite[neo4j]",
            file=sys.stderr,
        )
        print(f"(detail: {exc})", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Neo4j health check FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        if adapter is not None:
            try:
                adapter.close()
            except Exception:
                logger.warning("Failed to close Neo4j adapter cleanly", exc_info=True)

    if ok:
        print("Neo4j health check OK")
        return 0
    print("Neo4j health check FAILED: connectivity verification returned False", file=sys.stderr)
    return 1


def _cmd_neo4j_rebuild(args: argparse.Namespace) -> int:
    """Rebuild Neo4j graph from SQLite relations."""
    from .config import get_neo4j_config
    from .neo4j_adapter import Neo4jGraphAdapter

    config = get_neo4j_config()
    uri = args.uri or config["uri"]
    user = args.user or config["user"]
    password = args.password or config["password"]

    # Load relations from state or SQLite
    state_path = Path(args.state) if args.state else None
    relations: list[dict] = []

    if state_path and state_path.exists():
        import json

        data = json.loads(state_path.read_text(encoding="utf-8"))
        relations = data.get("relations", [])

    if not relations:
        # Try loading from WarmIndex SQLite
        from .memory import WarmIndex

        warm = WarmIndex()
        cursor = warm.conn.execute("SELECT source, predicate, target, confidence FROM relations")
        for row in cursor.fetchall():
            relations.append(
                {
                    "source": row["source"],
                    "predicate": row["predicate"],
                    "target": row["target"],
                    "confidence": row["confidence"],
                }
            )
        warm.conn.close()

    if not relations:
        print("No relations found to rebuild", file=sys.stderr)
        return 1

    try:
        adapter = Neo4jGraphAdapter(uri=uri, user=user, password=password)
        count = adapter.rebuild_from_relations(relations)
        print(f"Neo4j graph rebuilt: {count} edges created")
        adapter.close()
        return 0
    except Exception as exc:
        print(f"Neo4j rebuild FAILED: {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# execute — Execution Attestation Layer (EAL, Phase 1)
# ---------------------------------------------------------------------------


def _load_ed25519_private_key(path: str):
    """Load an Ed25519 private key from PEM, or raw 32-byte seed as hex/base64."""
    import base64
    import binascii

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    raw = Path(path).read_bytes()
    try:
        return serialization.load_pem_private_key(raw, password=None)
    except ValueError:
        pass
    text = raw.decode("utf-8", errors="ignore").strip()
    for decode in (bytes.fromhex, base64.b64decode):
        try:
            seed = decode(text)
        except (ValueError, binascii.Error):
            continue
        if len(seed) == 32:
            return ed25519.Ed25519PrivateKey.from_private_bytes(seed)
    raise ValueError(f"unsupported Ed25519 private key format: {path}")


def _cmd_execute_record(args: argparse.Namespace) -> int:
    """Record a signed EXECUTE receipt into the capability's ExecutionLog."""
    from .execution_log import load_log, log_path_for

    try:
        doc = parse_file(args.file)
    except (ADLParseError, OSError, ValueError) as exc:
        print(f"record error: {exc}", file=sys.stderr)
        return 1
    try:
        key = _load_ed25519_private_key(args.key_file)
    except (ValueError, OSError) as exc:
        print(f"key error: {exc}", file=sys.stderr)
        return 1

    log = load_log(args.log_dir, doc.adl_id)
    if not log.verify_integrity():
        print(f"execution log integrity check FAILED for {doc.adl_id}", file=sys.stderr)
        return 1

    event = log.record(
        executor=args.actor,
        input_commitment=args.input_hash,
        output_commitment=args.output_hash,
        occurred_at=args.occurred_at,
        duration_ms=args.duration_ms,
        reasoning=args.reason or "",
        private_key=key,
        verification_method=args.verification_method,
    )
    path = log_path_for(args.log_dir, doc.adl_id)
    log.append_jsonl(path, event)

    if args.json:
        print(
            json.dumps(
                {
                    "execution_id": event.payload["execution_id"],
                    "capability": doc.adl_id,
                    "event_hash": event.hash,
                    "log_count": log.count,
                    "log_merkle_root": log.merkle_root(),
                    "log_file": str(path),
                },
                indent=2,
            )
        )
    else:
        print(
            f"recorded {event.payload['execution_id']} for {doc.adl_id} "
            f"(receipts={log.count}, root={log.merkle_root()[:12]}…)"
        )
    return 0


def _cmd_execute_anchor(args: argparse.Namespace) -> int:
    """Anchor the execution log Merkle root into the governance (consensus) chain."""
    from .execution_log import load_log

    log = load_log(args.log_dir, args.adl_id)
    if log.count == 0:
        print(f"no executions to anchor for {args.adl_id}", file=sys.stderr)
        return 1
    if not log.verify_integrity():
        print(f"execution log integrity check FAILED for {args.adl_id}", file=sys.stderr)
        return 1

    event = log.build_anchor_event(actor=args.actor, reasoning=args.reason or "")
    state_path = Path(args.state)
    engine = _load_engine(state_path)
    chain = engine.chains.get(args.adl_id)

    if args.json or chain is None:
        print(
            json.dumps(
                {
                    "event_type": event.event_type.value,
                    "concept_id": event.concept_id,
                    "payload": event.payload,
                    "appended": chain is not None,
                },
                indent=2,
            )
        )
        if chain is None:
            print(
                f"note: {args.adl_id} not in consensus state {state_path}; anchor NOT appended",
                file=sys.stderr,
            )
        return 0

    chain.append(event)
    _save_engine(engine, state_path)
    root = event.payload["log_merkle_root"]
    print(
        f"anchored {log.count} executions of {args.adl_id} (root={root[:12]}…) into consensus chain"
    )
    return 0


def _cmd_execute_log(args: argparse.Namespace) -> int:
    """List execution receipts, optionally verifying log integrity."""
    from .execution_log import load_log

    log = load_log(args.log_dir, args.adl_id)
    verified: bool | None = None
    if args.verify:
        # Axiom-level verification (proofs present, chain linkage valid).
        # Cryptographic LD-Proof verification requires a DID/key registry and
        # is performed separately via verify-anchor / key-registry tooling.
        verified = log.verify_integrity()

    if args.json:
        print(
            json.dumps(
                {
                    "capability": args.adl_id,
                    "count": log.count,
                    "log_merkle_root": log.merkle_root() or None,
                    "verified": verified,
                    "receipts": [
                        {
                            "execution_id": e.payload.get("execution_id"),
                            "executor": e.actor,
                            "occurred_at": e.payload.get("occurred_at"),
                            "input_commitment": e.payload.get("input_commitment"),
                            "output_commitment": e.payload.get("output_commitment"),
                            "assurance": e.payload.get("assurance"),
                            "hash": e.hash,
                        }
                        for e in log.receipts
                    ],
                },
                indent=2,
            )
        )
        return 0

    print(f"execution log: {args.adl_id} ({log.count} receipts)")
    for e in log.receipts:
        in_c = str(e.payload.get("input_commitment", ""))[:12]
        out_c = str(e.payload.get("output_commitment", ""))[:12]
        print(
            f"  {e.payload.get('execution_id')}  actor={e.actor}  "
            f"in={in_c}… out={out_c}…  assurance={e.payload.get('assurance')}"
        )
    if log.count:
        print(f"merkle root: {log.merkle_root()}")
    if verified is not None:
        print(f"integrity: {'OK' if verified else 'FAILED'}")
    return 0 if verified is not False else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adl-lite",
        description="ADL Lite — parse, validate, store, and manage capability lifecycle consensus",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # NOTE: --strict-template is registered BOTH here (legacy position, kept for
    # backward compatibility — argparse only applies a subparser's flag default
    # when the attribute is not already set, so the root value survives) and on
    # the `validate` subparser (the documented, discoverable position:
    # `adl-lite validate --strict-template examples/*.md`).
    parser.add_argument(
        "--strict-template",
        action="store_true",
        help="Enforce strict L2 template validation on all parsed documents",
    )

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
    p_validate.add_argument(
        "--strict-template",
        action="store_true",
        help="Enforce strict L2 template validation on all parsed documents",
    )
    p_validate.add_argument(
        "--shacl",
        action="store_true",
        default=None,
        help="Enable SHACL validation (auto-detected by default)",
    )
    p_validate.add_argument(
        "--no-shacl",
        action="store_true",
        default=None,
        help="Disable SHACL validation",
    )
    p_validate.set_defaults(func=_cmd_validate, strict=False)

    p_shacl = sub.add_parser("shacl", help="Run SHACL validation on ADL files")
    p_shacl.add_argument("files", nargs="+", help="ADL Markdown files to validate")
    p_shacl.set_defaults(func=_cmd_shacl)

    p_store = sub.add_parser("store", help="Store document in ADLMemory database")
    p_store.add_argument("file", help="Path to .md document")
    p_store.add_argument("--db", required=True, help="SQLite database path")
    p_store.set_defaults(func=_cmd_store)

    p_related = sub.add_parser("related", help="Find related capabilities via graph")
    p_related.add_argument("adl_id", help="Capability adl_id")
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

    p_consensus = sub.add_parser("consensus", help="Capability lifecycle consensus chain")
    cons_sub = p_consensus.add_subparsers(dest="consensus_cmd", required=True)

    p_reg = cons_sub.add_parser("register", help="Register capability in consensus engine")
    p_reg.add_argument("file", nargs="?", help="ADL file to register")
    p_reg.add_argument("--adl-id", help="Register by id without file")
    p_reg.add_argument(
        "--state",
        default=None,
        help="Consensus state JSON (default: adl_consensus.json)",
    )
    p_reg.set_defaults(func=_cmd_consensus_register)

    p_trans = cons_sub.add_parser("transition", help="Transition capability status")
    p_trans.add_argument("adl_id", help="Capability adl_id")
    p_trans.add_argument("--to", required=True, dest="to", help="Target status")
    p_trans.add_argument("--actor", required=True, help="Actor id")
    p_trans.add_argument("--reason", default="", help="Reason text")
    p_trans.add_argument("--state", default=None, help="Consensus state JSON path")
    p_trans.set_defaults(func=_cmd_consensus_transition)

    p_verify = cons_sub.add_parser("verify", help="Verify consensus chain integrity")
    p_verify.add_argument("adl_id", help="Capability adl_id")
    p_verify.add_argument("--state", default=None, help="Consensus state JSON path")
    p_verify.set_defaults(func=_cmd_consensus_verify)

    p_anchor = sub.add_parser("anchor", help="Compute transparency anchor over consensus chains")
    p_anchor.add_argument("--state", default=None, help="Consensus state JSON path")
    p_anchor.add_argument("--output", default="ANCHOR.md", help="Anchor file path")
    p_anchor.add_argument("--merkle", action="store_true", help="Use Merkle tree root anchor")
    p_anchor.add_argument(
        "--proofs-dir",
        default=None,
        help="Directory to write per-chain inclusion proofs (Merkle only)",
    )
    p_anchor.set_defaults(func=_cmd_anchor)

    p_verify_anchor = sub.add_parser("verify-anchor", help="Verify transparency anchor")
    p_verify_anchor.add_argument("--file", default="ANCHOR.md", help="Anchor file path")
    p_verify_anchor.add_argument("--commit", default=None, help="Git commit hash")
    p_verify_anchor.add_argument("--state", default=None, help="Consensus state JSON path")
    p_verify_anchor.set_defaults(func=_cmd_verify_anchor)

    p_verify_inclusion = sub.add_parser("verify-inclusion", help="Verify a Merkle inclusion proof")
    p_verify_inclusion.add_argument("adl_id", help="Capability adl_id")
    p_verify_inclusion.add_argument("--proof", required=True, help="Path to proof JSON file")
    p_verify_inclusion.add_argument("--anchor", default="ANCHOR.md", help="Anchor file path")
    p_verify_inclusion.add_argument("--state", default=None, help="Consensus state JSON path")
    p_verify_inclusion.set_defaults(func=_cmd_verify_inclusion)

    p_verify_batch = sub.add_parser(
        "verify-batch", help="Batch verify chains using Merkle inclusion proofs"
    )
    p_verify_batch.add_argument("--anchor", default="ANCHOR.md", help="Anchor file path")
    p_verify_batch.add_argument(
        "--proofs-dir", default=None, help="Directory containing .proof.json files"
    )
    p_verify_batch.add_argument("--state", default=None, help="Consensus state JSON path")
    p_verify_batch.set_defaults(func=_cmd_verify_batch)

    p_neo4j = sub.add_parser("neo4j", help="Neo4j graph backend management")
    p_neo4j_sub = p_neo4j.add_subparsers(
        dest="neo4j_command", required=True, help="Neo4j sub-command"
    )

    p_neo4j_status = p_neo4j_sub.add_parser(
        "status", help="Check Neo4j connection status and node count"
    )
    p_neo4j_status.add_argument("--uri", default=None, help="Neo4j connection URI (overrides env)")
    p_neo4j_status.add_argument("--user", default=None, help="Neo4j username (overrides env)")
    p_neo4j_status.add_argument("--password", default=None, help="Neo4j password (overrides env)")
    p_neo4j_status.set_defaults(func=_cmd_neo4j_status)

    p_neo4j_check = p_neo4j_sub.add_parser(
        "check", help="Brief Neo4j connectivity health check (liveness)"
    )
    p_neo4j_check.add_argument("--uri", default=None, help="Neo4j connection URI (overrides env)")
    p_neo4j_check.add_argument("--user", default=None, help="Neo4j username (overrides env)")
    p_neo4j_check.add_argument("--password", default=None, help="Neo4j password (overrides env)")
    p_neo4j_check.set_defaults(func=_cmd_neo4j_check)

    p_neo4j_rebuild = p_neo4j_sub.add_parser(
        "rebuild", help="Rebuild Neo4j graph from SQLite relations"
    )
    p_neo4j_rebuild.add_argument("--state", default=None, help="Consensus state JSON path")
    p_neo4j_rebuild.add_argument("--uri", default=None, help="Neo4j connection URI (overrides env)")
    p_neo4j_rebuild.add_argument("--user", default=None, help="Neo4j username (overrides env)")
    p_neo4j_rebuild.add_argument("--password", default=None, help="Neo4j password (overrides env)")
    p_neo4j_rebuild.set_defaults(func=_cmd_neo4j_rebuild)

    p_normalize = sub.add_parser(
        "normalize",
        help="LLM-driven canonicalization of near-duplicate concepts",
    )
    p_normalize.add_argument(
        "--input-dir",
        required=True,
        help="Directory of ADL Markdown files to canonicalize",
    )
    p_normalize.add_argument(
        "--threshold",
        type=float,
        default=0.92,
        help="Cosine similarity threshold for clustering (default: 0.92)",
    )
    p_normalize.add_argument(
        "--llm-provider",
        choices=["mock", "openai"],
        default="mock",
        help="LLM provider for proposals (default: mock)",
    )
    p_normalize.add_argument(
        "--llm-model",
        default="gpt-4o-mini",
        help="Model name when using --llm-provider=openai",
    )
    p_normalize.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute generated actions (default is dry-run)",
    )
    p_normalize.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output",
    )
    p_normalize.set_defaults(func=_cmd_normalize)

    p_execute = sub.add_parser(
        "execute",
        help="Execution Attestation Layer (EAL): record, anchor, and inspect executions",
    )
    exec_sub = p_execute.add_subparsers(dest="execute_cmd", required=True)

    p_exec_rec = exec_sub.add_parser("record", help="Record a signed execution receipt")
    p_exec_rec.add_argument("file", help="ADL Markdown file of the capability")
    p_exec_rec.add_argument(
        "--log-dir",
        default="adl_execution_logs",
        help="Execution log directory (default: adl_execution_logs)",
    )
    p_exec_rec.add_argument("--actor", required=True, help="Executor id (DID or agent name)")
    p_exec_rec.add_argument(
        "--key-file",
        required=True,
        help="Ed25519 private key file (PEM, or raw 32-byte seed as hex/base64)",
    )
    p_exec_rec.add_argument("--input-hash", required=True, help="sha256 input commitment")
    p_exec_rec.add_argument("--output-hash", required=True, help="sha256 output commitment")
    p_exec_rec.add_argument("--occurred-at", default=None, help="ISO timestamp of the execution")
    p_exec_rec.add_argument("--duration-ms", type=int, default=None)
    p_exec_rec.add_argument("--reason", default="")
    p_exec_rec.add_argument(
        "--verification-method",
        default=None,
        help="DID URL for the LD-Proof verificationMethod",
    )
    p_exec_rec.add_argument("--json", action="store_true", help="Emit JSON output")
    p_exec_rec.set_defaults(func=_cmd_execute_record)

    p_exec_anchor = exec_sub.add_parser(
        "anchor", help="Anchor the execution log Merkle root into the governance chain"
    )
    p_exec_anchor.add_argument("adl_id", help="Capability adl_id")
    p_exec_anchor.add_argument("--log-dir", default="adl_execution_logs")
    p_exec_anchor.add_argument("--actor", required=True, help="Anchor author id")
    p_exec_anchor.add_argument("--reason", default="")
    p_exec_anchor.add_argument("--state", default=None, help="Consensus state JSON path")
    p_exec_anchor.add_argument("--json", action="store_true", help="Emit JSON output")
    p_exec_anchor.set_defaults(func=_cmd_execute_anchor)

    p_exec_log = exec_sub.add_parser("log", help="List execution receipts")
    p_exec_log.add_argument("adl_id", help="Capability adl_id")
    p_exec_log.add_argument("--log-dir", default="adl_execution_logs")
    p_exec_log.add_argument(
        "--verify", action="store_true", help="Verify log integrity (axioms 1–15)"
    )
    p_exec_log.add_argument("--json", action="store_true", help="Emit JSON output")
    p_exec_log.set_defaults(func=_cmd_execute_log)

    p_mcp = sub.add_parser(
        "mcp",
        help="Start the MCP tool server (requires the [mcp] extra)",
    )
    p_mcp.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    p_mcp.add_argument(
        "--state-path",
        default=None,
        help="Path to consensus state JSON file (default: .adl/state.json)",
    )
    p_mcp.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for streamable-http transport (default: 8000)",
    )
    p_mcp.set_defaults(func=_cmd_mcp)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "state") and getattr(args, "state", None) is None:
        args.state = str(_default_state_path(None))

    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
