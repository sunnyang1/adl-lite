"""
Publish ADL Markdown files to Feishu Docs via lark-cli docs +create.
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..parser import ADLParseError, parse_file
from ..validator import ADLValidator
from .client import LarkCliError, run_lark_cli
from .namespace import resolve_wiki_space_for_scope
from .registry import LarkRegistry


@dataclass(frozen=True)
class PublishResult:
    adl_id: str
    title: str
    doc_id: str
    doc_url: str
    dry_run: bool
    source_path: str


def _doc_title_from_path(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def _relative_file_ref(path: Path) -> str:
    """Cwd-relative @path for lark-cli (absolute @paths are rejected)."""
    try:
        rel = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError as exc:
        raise ValueError(
            f"ADL file must be under the current working directory for lark-cli @file refs: {path}"
        ) from exc
    return f"@{rel.as_posix()}"


_FRONT_MATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
_LEADING_H1_RE = re.compile(r"^#\s+.+?\n(?:\s*\n)?", re.MULTILINE)


def _strip_leading_h1(text: str) -> str:
    """Drop the first markdown H1 (after YAML front matter) to avoid duplicate titles."""
    m = _FRONT_MATTER_RE.match(text)
    if m:
        head, rest = text[: m.end()], text[m.end() :]
        return head + _LEADING_H1_RE.sub("", rest, count=1)
    return _LEADING_H1_RE.sub("", text, count=1)


def _content_file_ref(
    src: Path,
    *,
    api_version: str,
    doc_title: str,
    explicit_title: bool,
) -> tuple[str, tempfile.TemporaryDirectory[str] | None]:
    """
    Return lark-cli @file ref for document body.

    When the caller passes an explicit ``--title``, strip the first H1 so Feishu
    does not show title twice (v1 ``--title``; v2 has no title flag — prepend H1).
    """
    if not explicit_title:
        return _relative_file_ref(src), None

    body = _strip_leading_h1(src.read_text(encoding="utf-8"))
    if api_version == "v2":
        body = f"# {doc_title}\n\n{body.lstrip()}"
    tmp = tempfile.TemporaryDirectory(prefix="adl_lark_publish_", dir=Path.cwd())
    staged = Path(tmp.name) / src.name
    staged.write_text(body, encoding="utf-8")
    return _relative_file_ref(staged), tmp


def _append_parent_flags(
    cmd: list[str],
    *,
    api_version: str,
    folder_token: str | None,
    wiki_node: str | None,
    wiki_space: str | None,
) -> None:
    if folder_token:
        if api_version == "v2":
            cmd.extend(["--parent-token", folder_token])
        else:
            cmd.extend(["--folder-token", folder_token])
    elif wiki_node:
        if api_version == "v2":
            cmd.extend(["--parent-token", wiki_node])
        else:
            cmd.extend(["--wiki-node", wiki_node])
    elif wiki_space:
        if api_version == "v2":
            if wiki_space == "my_library":
                cmd.extend(["--parent-position", "my_library"])
            else:
                cmd.extend(["--parent-token", wiki_space])
        else:
            cmd.extend(["--wiki-space", wiki_space])


def _build_docs_create_argv(
    *,
    api_version: str,
    doc_title: str,
    content_ref: str,
    folder_token: str | None,
    wiki_node: str | None,
    wiki_space: str | None,
    dry_run: bool,
) -> list[str]:
    cmd = ["docs", "+create", "--api-version", api_version]
    if api_version == "v2":
        cmd.extend(["--doc-format", "markdown", "--content", content_ref])
    else:
        cmd.extend(["--markdown", content_ref, "--title", doc_title])

    _append_parent_flags(
        cmd,
        api_version=api_version,
        folder_token=folder_token,
        wiki_node=wiki_node,
        wiki_space=wiki_space,
    )
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def _extract_create_result(payload: dict[str, Any]) -> tuple[str, str]:
    """Parse doc_id / doc_url from lark-cli docs +create JSON."""
    for key in ("data", "result"):
        block = payload.get(key)
        if isinstance(block, dict):
            nested = block.get("document")
            if isinstance(nested, dict):
                block = {**block, **nested}
            doc_id = block.get("doc_id") or block.get("document_id") or block.get("token")
            doc_url = block.get("doc_url") or block.get("url")
            if doc_id and doc_url:
                return str(doc_id), str(doc_url)
    doc_id = payload.get("doc_id")
    doc_url = payload.get("doc_url")
    if doc_id and doc_url:
        return str(doc_id), str(doc_url)
    raise LarkCliError(
        "docs +create succeeded but doc_id/doc_url missing in response",
        payload=payload,
    )


def publish_file(
    path: str | Path,
    *,
    title: str | None = None,
    folder_token: str | None = None,
    wiki_node: str | None = None,
    wiki_space: str | None = None,
    namespaces_path: Path | None = None,
    api_version: str = "v2",
    strict_validate: bool = False,
    dry_run: bool = False,
    lark_cli: str | None = None,
    registry: LarkRegistry | None = None,
) -> PublishResult:
    """
    Validate (optional), then create a Feishu doc whose body is the full ADL .md file.

    Uses lark-cli ``--content @file`` (v2) or ``--markdown @file`` (v1) so L1 YAML + L2
    prose + L3 blocks round-trip intact. Paths are cwd-relative ``@`` refs.
    """
    src = Path(path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"ADL file not found: {src}")

    try:
        doc = parse_file(src)
    except (ADLParseError, OSError, ValueError) as exc:
        raise ValueError(f"parse error: {exc}") from exc

    if strict_validate:
        errors = ADLValidator(strict=True).validate_document(doc)
        if errors:
            raise ValueError("validation failed:\n  - " + "\n  - ".join(errors))

    doc_title = title or doc.concept_name or _doc_title_from_path(src)
    explicit_title = title is not None
    content_ref, tmp = _content_file_ref(
        src,
        api_version=api_version,
        doc_title=doc_title,
        explicit_title=explicit_title,
    )

    resolved_wiki = wiki_space
    if not resolved_wiki and not folder_token and not wiki_node:
        reg_data = registry.load() if registry else None
        resolved_wiki = resolve_wiki_space_for_scope(
            doc.scope,
            namespaces_path=namespaces_path,
            registry_data=reg_data,
        )

    cmd = _build_docs_create_argv(
        api_version=api_version,
        doc_title=doc_title,
        content_ref=content_ref,
        folder_token=folder_token,
        wiki_node=wiki_node,
        wiki_space=resolved_wiki,
        dry_run=dry_run,
    )

    try:
        payload = run_lark_cli(cmd, lark_cli=lark_cli)
    finally:
        if tmp is not None:
            tmp.cleanup()

    if dry_run:
        return PublishResult(
            adl_id=doc.adl_id,
            title=doc_title,
            doc_id="(dry-run)",
            doc_url="(dry-run)",
            dry_run=True,
            source_path=str(src),
        )

    doc_id, doc_url = _extract_create_result(payload)

    if registry is not None:
        registry.record_publish(
            doc.adl_id,
            doc_id=doc_id,
            doc_url=doc_url,
            source_path=str(src),
            title=doc_title,
        )

    return PublishResult(
        adl_id=doc.adl_id,
        title=doc_title,
        doc_id=doc_id,
        doc_url=doc_url,
        dry_run=False,
        source_path=str(src),
    )
