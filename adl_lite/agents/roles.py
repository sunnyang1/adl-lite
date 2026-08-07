"""Role specifications for the thin runtime (M3).

Each role maps to a system prompt and a TOOL WHITELIST. The whitelist is the
enforcement point for privilege separation: ``AgentRuntime._call_tool`` rejects
any tool not in ``RoleSpec.allowed_tools`` with ``PermissionError`` (RT-02).

Tool names match the in-memory tool registry built by
``runtime._default_tools`` (NOT the disk-reload wrappers in ``tools.py`` —
those load/save state per call and would race the runtime's in-memory engine;
see M3 implementation note). ``adl_fork`` from experiments/harness.py is
expressed here as ``adl_consensus_transition`` (fork target status), which is
what the tools layer actually exposes.
"""

from __future__ import annotations

from dataclasses import dataclass

from .identity import AgentRole


@dataclass(frozen=True)
class RoleSpec:
    role: AgentRole
    system_prompt: str
    allowed_tools: tuple[str, ...]
    validation_policy: str  # propose / approve / challenge / merge / curate


ROLE_SPECS: dict[AgentRole, RoleSpec] = {
    AgentRole.DISCOVERER: RoleSpec(
        role=AgentRole.DISCOVERER,
        system_prompt=(
            "You discover phenomena and draft capability Markdown (L1-L3). "
            "Use adl_parse then adl_consensus_register to land a new capability."
        ),
        allowed_tools=("adl_parse", "adl_consensus_register", "adl_ontology_query"),
        validation_policy="propose",
    ),
    AgentRole.REVIEWER: RoleSpec(
        role=AgentRole.REVIEWER,
        system_prompt=("You validate semantics against the ontology and approve transitions."),
        allowed_tools=("adl_validate", "adl_consensus_transition", "adl_ontology_query"),
        validation_policy="approve",
    ),
    AgentRole.SKEPTIC: RoleSpec(
        role=AgentRole.SKEPTIC,
        system_prompt="You challenge claims by forking or rejecting.",
        allowed_tools=("adl_consensus_transition", "adl_consensus_verify"),
        validation_policy="challenge",
    ),
    AgentRole.MERGER: RoleSpec(
        role=AgentRole.MERGER,
        system_prompt="You resolve forks via merge/parallel/prune.",
        allowed_tools=("adl_consensus_transition", "adl_consensus_verify"),
        validation_policy="merge",
    ),
    AgentRole.LIBRARIAN: RoleSpec(
        role=AgentRole.LIBRARIAN,
        system_prompt="You store documents and gate reads by scope.",
        allowed_tools=("adl_store", "adl_query_related", "adl_consensus_verify"),
        validation_policy="curate",
    ),
}


def role_spec(role: AgentRole) -> RoleSpec:
    """Look up a role spec; raises KeyError for unknown roles (registration
    already validates roles, so this is defensive only)."""
    return ROLE_SPECS[role]
