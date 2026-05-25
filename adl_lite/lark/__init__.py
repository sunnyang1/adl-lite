"""
ADL-Lark Bridge — publish ADL Markdown concepts to Feishu/Lark via lark-cli.

Requires: https://github.com/larksuite/cli installed and authenticated
(`lark-cli config init`, `lark-cli auth login --recommend`).
"""

from .announce import AnnounceResult, announce
from .client import (
    LarkCliError,
    LarkCliNotFoundError,
    auth_status,
    find_lark_cli,
    run_lark_cli,
)
from .dashboard import DashboardResult, init_dashboard, sync_dashboard_row
from .listen import ListenResult, listen
from .namespace import LarkNamespaceRegistry, resolve_wiki_space_for_scope, scope_to_adl_uri
from .publish import PublishResult, publish_file
from .registry import LarkRegistry
from .sync_memory import SyncMemoryResult, sync_memory
from .templates import render_template

__all__ = [
    "AnnounceResult",
    "DashboardResult",
    "LarkCliError",
    "LarkCliNotFoundError",
    "LarkNamespaceRegistry",
    "LarkRegistry",
    "ListenResult",
    "PublishResult",
    "SyncMemoryResult",
    "announce",
    "find_lark_cli",
    "init_dashboard",
    "listen",
    "publish_file",
    "render_template",
    "resolve_wiki_space_for_scope",
    "run_lark_cli",
    "scope_to_adl_uri",
    "sync_dashboard_row",
    "sync_memory",
    "auth_status",
]
