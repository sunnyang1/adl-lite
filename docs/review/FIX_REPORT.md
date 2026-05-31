# Adversarial Review Fix Report

**Date**: 2026-05-31 | **Based on**: `docs/review/ADVERSARIAL_REVIEW.md`

## Summary

| Category | Total | Fixed Before | Fixed Today | Remaining |
|----------|-------|-------------|-------------|-----------|
| P0 Critical | 4 | 4 ✅ | — | 0 |
| P1 Design | 6 | 1 ✅ | 5 ✅ | 0 |
| P2 Paper/Code | 5 | — | 4 ✅ | 1 (formal proofs) |

## P0 Fixes (4/4)

| # | Issue | Status | Fix |
|---|-------|--------|-----|
| P0-1 | Dual chain: EventChain vs ConceptChain | ✅ Pre-existing | ConsensusEngine uses EventChain exclusively; ConceptChain removed in v0.3 |
| P0-2 | ActionExecutor mutates front_matter.status | ✅ Pre-existing | Now appends lifecycle Events to EventChain + refresh_snapshot() |
| P0-3 | ActionExecutor bypasses ConsensusEngine | ✅ Pre-existing | ActionExecutor no longer stores status directly |
| P0-4 | E10 overrides chain-derived confidence | ✅ Pre-existing | Uses SNAPSHOT event with derived confidence from data patterns |

## P1 Fixes (6/6)

| # | Issue | Status | Fix |
|---|-------|--------|-----|
| P1-1 | Smurfing `all()` false negatives | ✅ Today | Windowed check on 5 most recent laundering events with re-emergence detection |
| P1-2 | No concurrency protection | ✅ Today | `threading.RLock` on ConsensusEngine.chains; `threading.Lock` on EventChain._events + RealtimeWatcher._alerts |
| P1-3 | RealtimeWatcher.attach() non-composable | ✅ Today | Wrapper stacking via `chain._wrapped_appends` stack |
| P1-4 | DataImporter strips quotes | ✅ Today | Removed `strip('"')` from field name parameters (csv.DictReader handles value quoting) |
| P1-5 | SyncManager merge non-deterministic | ✅ Today | Changed tie-break from uuid4 event_id → SHA-256 hash (deterministic) |
| P1-6 | from_parsed() synthetic events | ✅ Pre-existing | `payload.synthetic=True` tag on all reconstruction events |

## P2 Fixes (4/5)

| # | Issue | Status | Fix |
|---|-------|--------|-----|
| P2-1 | "Status never stored" claim | ✅ Pre-existing | No code paths directly store status |
| P2-2 | No formal proof artifacts | ⚠️ Outstanding | Needs Coq/Lean/TLA+ files or downgrade "Theorem" → "Property" |
| P2-3 | "Zero merge conflicts" tautological | ✅ Today | E8 expanded: semantic conflict, contradictory lifecycle, divergent terminal states |
| P2-4 | "495,671 chains zero failures" misleading | ✅ Today | E6 metrics renamed to `chains_import_integrity`; docstring clarifies import correctness |
| P2-5 | E4 only tests 3 of 9 actions | ✅ Today | E4 expanded: 19 test cases covering 8 actions (was 13 cases, 5 actions) |

## Additional Bug Fixes

- **fork() idempotency**: `ConsensusEngine.fork()` now skips transition if concept already in `forked` status (prevents `forked→forked` ValueError)
- **Reentrant lock**: Upgraded `ConsensusEngine._lock` from `Lock` to `RLock` to support `fork()` → `transition()` call chain

## Test Results

```
112/112 tests pass (5.01s)

E1  [PASS] Chain integrity           valid 1.0, corrupt detect 1.0
E2  [PASS] Status derivation          2204/2204 (100%)
E3  [PASS] Snapshot roundtrip         38/38 status match
E4  [PASS] Precondition enforcement   P=1.0 R=1.0 F1=1.0 (19 cases, 8 actions)
E5  [PASS] 5-agent audit              5/5 chains integrity OK
E6  [PASS] IBM AML pipeline           201/201 import integrity
E7  [PASS] Realtime watcher           smurfing/rapid/fanout/FP all OK
E8  [PASS] Edge sync                  8/8 tests (incl. semantic conflicts)
E9  [PASS] Chain tampering            100% detection rate
E10 [PART] FDE pipeline               201 accounts, 1 validated (small dataset)
E11 [PASS] Side effect queue          2000 calls, 1000/1000 drained
```

## Files Changed

| File | Changes |
|------|---------|
| `adl_lite/models.py` | +`threading`, `EventChain._lock`, thread-safe `append()`/`events` |
| `adl_lite/consensus.py` | +`threading`, `RLock`, `register()`/`transition()`/`fork()` thread-safe, fork idempotent |
| `adl_lite/realtime.py` | +`threading`, `RealtimeWatcher._lock`, windowed smurfing check, composable `attach()`/`detach()` |
| `adl_lite/data_importer.py` | Removed `strip('"')` on field name params |
| `adl_lite/sync_manager.py` | `(timestamp, hash)` sort instead of `(timestamp, event_id)` |
| `experiments/e4_precondition.py` | +6 test cases (publish, sync_dashboard, listen) |
| `experiments/e6_aml_pipeline.py` | Metrics renamed, docstring updated |
| `experiments/e7_realtime_watcher.py` | No changes (test verifies new smurfing behavior) |
| `experiments/e8_edge_sync.py` | +3 test scenarios (semantic conflict, lifecycle, divergent terminal) |
| `experiments/e10_fde_pipeline.py` | Sample size 5→5000, confidence from data patterns via SNAPSHOT event |

---

## Round 2 Review (2026-05-31 10:36)

Second-pass adversarial review of the post-fix codebase.

### R2 Findings

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| R2-1 | P1 | EventChain read methods (`length`/`__iter__`/`status`/`confidence`/`verify_integrity`/`history` etc.) access `_events` without lock | Added `with self._lock` to all 12 methods |
| R2-2 | P1 | ConsensusEngine query methods (`get_history`/`get_status`/`verify_all`) read `self.chains` without lock | Added `with self._lock` to all 3 methods |
| R2-3 | P1 | RealtimeWatcher `on()`/`on_any()`/`_dispatch()` access `self._handlers` without lock | Added `with self._lock` to all 3 methods |
| R2-4 | P1 | Parser `strip('"')` on 14 value fields — same data-loss pattern as old DataImporter | Replaced with `_unquote()` helper: removes ONE outer pair only, preserves embedded quotes |

### R2 Edge Cases Reviewed (no fix needed)

| Area | Finding | Verdict |
|------|---------|---------|
| Smurfing window re-emergence | `prev_window` logic verified correct for 6-event trace | ✅ Correct |
| ForkManager.register_fork() | Accessed through ConsensusEngine (under lock) | ✅ Safe |
| Parser regex YAML parsing | Single-line KV only — multi-line values unsupported | ⚠️ Design limitation |
| ActionExecutor front_matter staleness | User docs should call `refresh_snapshot()` before `validate_action()` | 📝 Documentation issue |
| EventChain lock consistency | Now all `_events` access is lock-protected (read and write) | ✅ Fixed |

### R2 Results

```
112/112 tests pass
9/10 experiments PASS (E10 partial on small dataset)
All round-1 fixes intact
No regressions
```

### Final state: total fixes applied

| Round | P0 | P1 | P2 | Total |
|-------|-----|-----|-----|-------|
| Pre-existing | 4 | 1 | — | 5 |
| Round 1 | — | 5 | 4 | 9 |
| Round 2 | — | 4 | — | 4 |
| Round 3 | 1 | 3 | — | 4 |
| **Total** | **5** | **13** | **4** | **22** |

---

## Round 3 Review (2026-05-31 12:26)

Third-pass adversarial review — cross-module consistency, data integrity, SQL injection.

### R3 Findings

| # | Severity | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| R3-0 | **P0** | `adl_consensus_transition()` 访问 `Event.from_status`/`.to_status` — 属性不存在 | `tools.py:114-121` | 重写为使用 `event.event_type`/`.actor`/`.hash` |
| R3-1 | P1 | `WarmIndex` 所有 SQLite 操作无锁 (`check_same_thread=False` 但无保护) | `memory.py:136-185` | 添加 `threading.RLock`，`insert_document`/`get_document`/`delete_document`/`get_related`/`cascade_filter` 全部持锁 |
| R3-2 | P1 | `cascade_filter` SQL LIKE 通配符注入 — `%`/`_` 在 `scope_prefix` 中成为通配符 | `memory.py:276-305` | 添加 `ESCAPE '\'` 并转义 `%` → `\%`, `_` → `\_` |
| R3-3 | P1 | `_load_engine` 反序列化丢失 `event_id`/`hash`，中断外部引用 | `cli.py:43-57` | 保存/加载时保留 `event_id` 和 `hash`；`history()` 增加 `payload` 字段 |

### R3 Edge Cases Reviewed

| Area | Finding | Verdict |
|------|---------|---------|
| `_RE_KV_LINE` ReDoS | `.+` on long single-line values | ⚠️ Low risk (PyYAML pre-parses YAML) |
| Event payload unbounded growth | `payload: dict[str, Any]` 无大小限制 | 📝 已知限制 |
| `adl_id` 输入验证 | 无字符约束，可用于路径/SQL | 📝 已知限制 |
| `events` property O(n) copy | 每次访问复制整个列表 | ⚠️ 性能考虑（大型链） |

### R3 Results

```
112/112 tests pass
9/10 experiments PASS
tools.py crash: VERIFIED FIXED
event_id round-trip: VERIFIED PRESERVED
SQL LIKE injection: VERIFIED ESCAPED
```
