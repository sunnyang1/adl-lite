"""ADL Lite agents package — native multi-agent runtime primitives (M1a+).

Imports only core modules; heavy optional deps stay lazy (PEP 562 contract
enforced at the ``adl_lite`` top level via ``_LAZY_ATTRS``).
"""

from .bus import MessageBus, TaskQueue
from .config import AgentConfig
from .identity import (
    AgentProfile,
    AgentRegistry,
    AgentRole,
    AgentStatus,
    chain_kind,
)
from .planner import Planner
from .roles import ROLE_SPECS, RoleSpec
from .runtime import AgentRuntime, CheckpointKind, RuntimeManager
from .task import Task, TaskRegistry, TaskStatus, TaskStatusView, derive_task_status
from .trust import DidWebAffiliationResolver, Reputation, ReputationScore

__all__ = [
    "AgentConfig",
    "AgentProfile",
    "AgentRegistry",
    "AgentRole",
    "AgentRuntime",
    "AgentStatus",
    "CheckpointKind",
    "DidWebAffiliationResolver",
    "MessageBus",
    "Planner",
    "ROLE_SPECS",
    "Reputation",
    "ReputationScore",
    "RoleSpec",
    "RuntimeManager",
    "Task",
    "TaskQueue",
    "TaskRegistry",
    "TaskStatus",
    "TaskStatusView",
    "chain_kind",
    "derive_task_status",
]
