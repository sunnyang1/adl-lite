"""
Feishu Sheets consensus dashboard for ADL concepts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..consensus import ConceptChain, ConsensusEngine, ConsensusEntry
from ..memory import ADLMemory
from ..models import DiscoveryStatus
from .client import run_lark_cli
from .registry import LarkRegistry


def _load_engine_from_state(state_path: Path | None) -> ConsensusEngine | None:
    if state_path is None or not state_path.exists():
        return None
    data = json.loads(state_path.read_text(encoding="utf-8"))
    engine = ConsensusEngine()
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


DEFAULT_COLUMNS = [
    "concept_id",
    "status_badge",
    "confidence",
    "discoverer",
    "validators",
    "last_update",
    "doc_link",
]


@dataclass(frozen=True)
class DashboardRow:
    concept_id: str
    status_badge: str
    confidence: float
    discoverer: str
    validators: str
    last_update: str
    doc_link: str

    def as_list(self, columns: list[str]) -> list[Any]:
        mapping = {
            "concept_id": self.concept_id,
            "status_badge": self.status_badge,
            "confidence": self.confidence,
            "discoverer": self.discoverer,
            "validators": self.validators,
            "last_update": self.last_update,
            "doc_link": self.doc_link,
        }
        return [mapping.get(c, "") for c in columns]


@dataclass(frozen=True)
class DashboardResult:
    spreadsheet_token: str
    sheet_id: str
    rows_written: int
    dry_run: bool
    title: str


def _status_badge(status: str) -> str:
    try:
        return DiscoveryStatus(status).value
    except ValueError:
        return status


def build_dashboard_rows(
    mem: ADLMemory,
    engine: ConsensusEngine | None = None,
    *,
    registry: LarkRegistry | None = None,
) -> list[DashboardRow]:
    rows_db = mem.warm.conn.execute(
        """
        SELECT adl_id, status, confidence, scope, updated_at, created_at
        FROM documents ORDER BY adl_id
        """
    ).fetchall()
    rows: list[DashboardRow] = []
    for row in rows_db:
        adl_id = row["adl_id"]
        status = row["status"]
        if engine and adl_id in engine.chains:
            status = engine.get_status(adl_id).value
        badge = _status_badge(status)
        discoverer = ""
        validators = ""
        last_update = row["updated_at"] or row["created_at"] or ""
        if engine and adl_id in engine.chains:
            hist = engine.get_history(adl_id)
            if hist:
                discoverer = hist[0].get("actor", "")
                validators = ", ".join(
                    e["actor"] for e in hist if e.get("to_status") == "validated"
                )
                last_update = hist[-1].get("timestamp", last_update)
        doc_link = ""
        if registry:
            entry = registry.get(adl_id)
            if entry:
                doc_link = entry.get("doc_url", "")
        rows.append(
            DashboardRow(
                concept_id=adl_id,
                status_badge=badge,
                confidence=float(row["confidence"] or 0.0),
                discoverer=discoverer,
                validators=validators,
                last_update=last_update or "",
                doc_link=doc_link,
            )
        )
    return rows


def _extract_spreadsheet(payload: dict[str, Any]) -> tuple[str, str]:
    data = payload.get("data") or payload
    if isinstance(data, dict):
        token = (
            data.get("spreadsheet_token")
            or data.get("token")
            or data.get("spreadsheetToken")
        )
        if not token and isinstance(data.get("spreadsheet"), dict):
            inner = data["spreadsheet"].get("spreadsheet") or data["spreadsheet"]
            if isinstance(inner, dict):
                token = inner.get("token") or inner.get("spreadsheet_token")
        sheet_id = data.get("sheet_id") or data.get("sheetId") or ""
        if not sheet_id:
            sheets = data.get("sheets")
            if isinstance(sheets, list) and sheets:
                first = sheets[0]
                if isinstance(first, dict):
                    sheet_id = first.get("sheet_id") or first.get("sheetId") or ""
            elif isinstance(sheets, dict):
                sheet_id = _extract_first_sheet_id({"data": {"sheets": sheets}})
        if token:
            return str(token), str(sheet_id or "")
    raise ValueError("spreadsheet token missing in lark-cli response")


def _extract_first_sheet_id(payload: dict[str, Any]) -> str:
    """First worksheet id from ``sheets +info`` (or similar) response."""
    data = payload.get("data") or payload
    if not isinstance(data, dict):
        return ""

    sheets_block = data.get("sheets")
    sheet_list: list[Any] = []
    if isinstance(sheets_block, dict):
        sheet_list = list(sheets_block.get("sheets") or sheets_block.get("items") or [])
    elif isinstance(sheets_block, list):
        sheet_list = sheets_block

    for item in sheet_list:
        if isinstance(item, dict):
            sid = item.get("sheet_id") or item.get("sheetId")
            if sid:
                return str(sid)
    return ""


def _fetch_sheet_id(
    spreadsheet_token: str,
    *,
    lark_cli: str | None = None,
    dry_run: bool = False,
) -> str:
    payload = run_lark_cli(
        ["sheets", "+info", "--spreadsheet-token", spreadsheet_token]
        + (["--dry-run"] if dry_run else []),
        lark_cli=lark_cli,
    )
    sheet_id = _extract_first_sheet_id(payload)
    if not sheet_id:
        raise ValueError(
            f"no sheet_id in spreadsheet metadata for token {spreadsheet_token}"
        )
    return sheet_id


def _resolve_dashboard_sheet_id(
    dash: dict[str, Any],
    *,
    sheet_title: str,
    registry: LarkRegistry | None = None,
    lark_cli: str | None = None,
    dry_run: bool = False,
) -> str:
    sheet_id = str(dash.get("sheet_id") or "").strip()
    if sheet_id:
        return sheet_id

    token = dash["spreadsheet_token"]
    sheet_id = _fetch_sheet_id(token, lark_cli=lark_cli, dry_run=dry_run)

    if registry and not dry_run:
        data = registry.load()
        entry = data.get("dashboards", {}).get(sheet_title)
        if isinstance(entry, dict) and not entry.get("sheet_id"):
            entry["sheet_id"] = sheet_id
            registry.save(data)

    return sheet_id


def _column_letter(col_index: int) -> str:
    """1-based column index to spreadsheet column letter (1=A, 27=AA)."""
    if col_index < 1:
        raise ValueError(f"column index must be >= 1, got {col_index}")
    letters = ""
    n = col_index
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _row_range(sheet_id: str, num_cols: int, *, row: int = 2) -> str:
    end_col = _column_letter(num_cols)
    return f"{sheet_id}!A{row}:{end_col}{row}"


def _append_dashboard_row(
    *,
    spreadsheet_token: str,
    sheet_id: str,
    values: list[Any],
    dry_run: bool = False,
    lark_cli: str | None = None,
) -> None:
    range_spec = _row_range(sheet_id, len(values))
    cmd = [
        "sheets",
        "+append",
        "--spreadsheet-token",
        spreadsheet_token,
        "--sheet-id",
        sheet_id,
        "--range",
        range_spec,
        "--values",
        json.dumps([values], ensure_ascii=False),
    ]
    if dry_run:
        cmd.append("--dry-run")
    run_lark_cli(cmd, lark_cli=lark_cli)


def init_dashboard(
    title: str,
    *,
    db_path: str | None = None,
    columns: list[str] | None = None,
    state_path: Path | None = None,
    registry_path: Path | None = None,
    dry_run: bool = False,
    lark_cli: str | None = None,
) -> DashboardResult:
    cols = columns or list(DEFAULT_COLUMNS)
    engine = _load_engine_from_state(state_path)

    mem = ADLMemory(db_path=db_path) if db_path else None
    rows: list[DashboardRow] = []
    if mem:
        try:
            registry = LarkRegistry(registry_path) if registry_path else None
            rows = build_dashboard_rows(mem, engine, registry=registry)
        finally:
            mem.close()

    header_row = cols
    data_rows = [r.as_list(cols) for r in rows]

    create_cmd = [
        "sheets",
        "+create",
        "--title",
        title,
        "--headers",
        json.dumps(header_row, ensure_ascii=False),
    ]
    if data_rows:
        create_cmd.extend(["--data", json.dumps(data_rows, ensure_ascii=False)])
    if dry_run:
        create_cmd.append("--dry-run")

    payload = run_lark_cli(create_cmd, lark_cli=lark_cli)
    token, sheet_id = _extract_spreadsheet(payload)
    if not sheet_id and token and not dry_run:
        sheet_id = _fetch_sheet_id(token, lark_cli=lark_cli)

    if registry_path and not dry_run:
        reg = LarkRegistry(registry_path)
        data = reg.load()
        dashboards = data.setdefault("dashboards", {})
        dashboards[title] = {
            "spreadsheet_token": token,
            "sheet_id": sheet_id,
            "columns": cols,
        }
        reg.save(data)

    return DashboardResult(
        spreadsheet_token=token,
        sheet_id=sheet_id,
        rows_written=len(data_rows),
        dry_run=dry_run,
        title=title,
    )


def sync_dashboard_row(
    adl_id: str,
    *,
    sheet_title: str,
    registry_path: Path,
    db_path: str | None = None,
    state_path: Path | None = None,
    dry_run: bool = False,
    lark_cli: str | None = None,
) -> DashboardResult:
    """Append or refresh one concept row on an existing dashboard sheet."""
    reg = LarkRegistry(registry_path)
    dash = reg.load().get("dashboards", {}).get(sheet_title)
    if not dash:
        raise KeyError(f"dashboard not in registry: {sheet_title}")

    token = dash["spreadsheet_token"]
    cols = dash.get("columns") or DEFAULT_COLUMNS
    sheet_id = _resolve_dashboard_sheet_id(
        dash,
        sheet_title=sheet_title,
        registry=reg,
        lark_cli=lark_cli,
        dry_run=dry_run,
    )

    engine = _load_engine_from_state(state_path)

    if not db_path:
        raise ValueError("db_path required for dashboard row sync")

    mem = ADLMemory(db_path=db_path)
    try:
        all_rows = build_dashboard_rows(mem, engine, registry=reg)
    finally:
        mem.close()

    target = next((r for r in all_rows if r.concept_id == adl_id), None)
    if target is None:
        raise KeyError(f"concept not in memory db: {adl_id}")

    _append_dashboard_row(
        spreadsheet_token=token,
        sheet_id=sheet_id,
        values=target.as_list(cols),
        dry_run=dry_run,
        lark_cli=lark_cli,
    )
    return DashboardResult(
        spreadsheet_token=token,
        sheet_id=sheet_id,
        rows_written=1,
        dry_run=dry_run,
        title=sheet_title,
    )
