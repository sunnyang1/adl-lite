"""
L3 Relation Reconciliation Validator for ADL Lite.

Implements Invariant 2 (paper §4.2):
    valid(r) ↔ S(C1) ∉ {archived} ∧ S(C2) ∉ {archived}
              ∧ ¬(S(C1)=deprecated ∧ S(C2)=deprecated)

Also implements fork inheritance rules:
    - Parent retains all existing relations
    - Child inherits isomorphic-to and specialisation-of
    - Child does NOT inherit analogical-to (re-evaluated during validation)

This module ensures that the relation graph remains navigable during
multi-agent reorganisation, and that stale or superseded edges do not
pollute semantic queries.
"""

from __future__ import annotations

from .models import ADLRelationBlock, DiscoveryStatus, EventChain


class RelationValidator:
    """
    Validates L3 relations against the lifecycle status of their endpoints.

    Usage:
        validator = RelationValidator()
        is_valid = validator.valid(relation, source_status, target_status)
        inherited = validator.inherit_relations(parent_chain, child_id)
    """

    # Predicates that are inherited during a fork
    INHERITABLE_PREDICATES = frozenset({"isomorphic-to", "specialisation-of"})
    # Predicates that are NOT inherited (must be re-evaluated)
    NON_INHERITABLE_PREDICATES = frozenset({"analogical-to"})

    def valid(
        self,
        relation: ADLRelationBlock,
        source_status: DiscoveryStatus,
        target_status: DiscoveryStatus,
    ) -> bool:
        """
        Check whether a relation is valid given the lifecycle status of its endpoints.

        Invariant 2:
            valid(r) ↔ S(C1) ∉ {archived} ∧ S(C2) ∉ {archived}
                      ∧ ¬(S(C1)=deprecated ∧ S(C2)=deprecated)

        Relations with at least one endpoint in 'validated' status remain valid.
        Relations between two 'archived' or both 'deprecated' concepts are excluded.
        """
        # Both endpoints archived → invalid
        if source_status == DiscoveryStatus.ARCHIVED or target_status == DiscoveryStatus.ARCHIVED:
            return False

        # Both endpoints deprecated → invalid
        if source_status == DiscoveryStatus.DEPRECATED and target_status == DiscoveryStatus.DEPRECATED:
            return False

        return True

    def filter_valid_relations(
        self,
        relations: list[ADLRelationBlock],
        status_lookup: dict[str, DiscoveryStatus],
    ) -> list[ADLRelationBlock]:
        """
        Filter a list of relations, keeping only those that satisfy Invariant 2.

        Args:
            relations: List of ADLRelationBlock to validate.
            status_lookup: Mapping from concept_id → DiscoveryStatus.

        Returns:
            Subset of relations whose endpoints are both valid per Invariant 2.
        """
        valid_relations: list[ADLRelationBlock] = []
        for rel in relations:
            src_status = status_lookup.get(rel.source, DiscoveryStatus.PROVISIONAL)
            tgt_status = status_lookup.get(rel.target, DiscoveryStatus.PROVISIONAL)
            if self.valid(rel, src_status, tgt_status):
                valid_relations.append(rel)
        return valid_relations

    def inherit_relations(
        self,
        parent_chain: EventChain,
        child_id: str,
        parent_relations: list[ADLRelationBlock],
    ) -> list[ADLRelationBlock]:
        """
        Compute the set of relations a forked child concept should inherit from its parent.

        Fork inheritance rules (paper §4.2):
            - Parent retains all existing relations.
            - Child inherits only 'isomorphic-to' and 'specialisation-of' links.
            - Child does NOT inherit 'analogical-to' links (re-evaluated during validation).
            - All inherited relations are re-pointed: source = child_id, target = original_target.

        Args:
            parent_chain: The EventChain of the parent concept.
            child_id: The concept_id of the newly forked child.
            parent_relations: All relations from which the parent is a source or target.

        Returns:
            List of inherited ADLRelationBlock objects for the child concept.
        """
        inherited: list[ADLRelationBlock] = []

        for rel in parent_relations:
            if rel.relation not in self.INHERITABLE_PREDICATES:
                continue

            # Re-point relations where parent was the source
            if rel.source == parent_chain.concept_id:
                inherited.append(
                    ADLRelationBlock(
                        source=child_id,
                        relation=rel.relation,
                        target=rel.target,
                        mapping_type=rel.mapping_type,
                        confidence=rel.confidence,
                    )
                )
            # Re-point relations where parent was the target
            elif rel.target == parent_chain.concept_id:
                inherited.append(
                    ADLRelationBlock(
                        source=rel.source,
                        relation=rel.relation,
                        target=child_id,
                        mapping_type=rel.mapping_type,
                        confidence=rel.confidence,
                    )
                )

        return inherited

    def check_invariant_violations(
        self,
        relations: list[ADLRelationBlock],
        status_lookup: dict[str, DiscoveryStatus],
    ) -> list[str]:
        """
        Return a list of human-readable invariant violation descriptions.

        Useful for debugging and audit reports.
        """
        violations: list[str] = []
        for rel in relations:
            src_status = status_lookup.get(rel.source, DiscoveryStatus.PROVISIONAL)
            tgt_status = status_lookup.get(rel.target, DiscoveryStatus.PROVISIONAL)
            if not self.valid(rel, src_status, tgt_status):
                violations.append(
                    f"Relation {rel.relation} from {rel.source}({src_status.value}) "
                    f"to {rel.target}({tgt_status.value}) violates Invariant 2"
                )
        return violations
