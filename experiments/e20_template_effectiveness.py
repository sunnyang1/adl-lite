"""E20: L2 Template Compliance Effectiveness.

Simulates 5 agents, 3 shared concepts, 20 rounds.
Measures bad-transition prevention with and without L2 template enforcement.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from adl_lite import ConsensusEngine, DiscoveryStatus
from adl_lite.action_executor import ActionExecutor
from adl_lite.l2_template import L2TemplateValidator, react_to_l2_template
from adl_lite.models import ADLActionBlock, ADLDocument, ADLFrontMatter, ADLType, Event, EventType
from adl_lite.ontology import OntologyManager

try:
    from .base import BaseExperiment, ExperimentResult
    from .registry import register
except ImportError:
    from experiments.base import BaseExperiment, ExperimentResult
    from experiments.registry import register


@dataclass
class RoundResult:
    round_num: int
    template_on: bool
    valid_attempts: int = 0
    valid_accepted: int = 0
    invalid_attempts: int = 0
    invalid_rejected: int = 0


@register("E20")
class E20TemplateEffectiveness(BaseExperiment):
    experiment_id = "E20"
    name = "L2 Template Compliance Effectiveness"
    description = (
        "Template enforcement reduces invalid transitions (5 agents, 3 concepts, 20 rounds)"
    )

    def run(self) -> ExperimentResult:
        random.seed(42)
        mgr = OntologyManager()
        executor = ActionExecutor(mgr)
        engine = ConsensusEngine(mgr)
        tv = L2TemplateValidator()
        concepts = [f"template-concept-{i}" for i in range(3)]
        for cid in concepts:
            engine.register(
                ADLDocument(
                    front_matter=ADLFrontMatter(
                        adl_type=ADLType.DISCOVERY,
                        adl_id=cid,
                        status=DiscoveryStatus.PROVISIONAL,
                        confidence=0.0,
                    )
                )
            )
        agents = [f"agent_{i}" for i in range(5)]
        action_types = [EventType.VALIDATE, EventType.DEPRECATE, EventType.FORK, EventType.EVIDENCE]
        round_results: list[RoundResult] = []
        for rn in range(1, 21):
            ton = rn <= 10
            rr = RoundResult(round_num=rn, template_on=ton)
            for agent in agents:
                concept = random.choice(concepts)
                action = random.choice(action_types)
                tvalid = True
                body = ""
                if action == EventType.VALIDATE:
                    tvalid = random.random() < 0.7
                    tpl = react_to_l2_template(
                        {
                            "observation": "Gradient explosion observed.",
                            "thought": "High LR causes overshoot.",
                            "conclusion": "Validated phenomenon.",
                        }
                        if tvalid
                        else {"observation": "Gradient explosion observed."}
                    )
                    body = "\n\n".join(
                        f"## {k}\n\n{getattr(tpl, k.lower())}"
                        for k in ("Observation", "Reasoning", "Conclusion")
                        if getattr(tpl, k.lower())
                    )
                doc = ADLDocument(
                    front_matter=ADLFrontMatter(
                        adl_type=ADLType.DISCOVERY,
                        adl_id=concept,
                        status=engine.get_status(concept),
                        confidence=0.8,
                    ),
                    markdown_body=body,
                )
                params: dict[str, Any] = (
                    {"confidence": 0.8}
                    if action == EventType.VALIDATE
                    else {"fork_id": f"{concept}-fork", "rationale": "alt"}
                    if action == EventType.FORK
                    else {"reason": "obsolete"}
                    if action == EventType.DEPRECATE
                    else {}
                )
                block = ADLActionBlock(
                    action=action.value, actor=agent, reasoning=f"R{rn}", params=params
                )
                svalid = len(executor.validate_action(doc, block)) == 0
                is_valid = svalid and (
                    not (action == EventType.VALIDATE and ton) or tv.validate(body, mode="relaxed")
                )
                if is_valid:
                    rr.valid_attempts += 1
                else:
                    rr.invalid_attempts += 1
                try:
                    if ton:
                        if is_valid:
                            self._apply(engine, concept, action, agent, rn, params)
                            rr.valid_accepted += 1
                        else:
                            rr.invalid_rejected += 1
                    else:
                        engine.chains[concept].append(
                            Event(
                                concept_id=concept,
                                event_type=action,
                                actor=agent,
                                reasoning=f"R{rn}",
                                payload=params,
                            )
                        )
                        if is_valid:
                            rr.valid_accepted += 1
                except Exception:
                    rr.invalid_rejected += 1
            round_results.append(rr)

        onr = [r for r in round_results if r.template_on]
        offr = [r for r in round_results if not r.template_on]
        tv_on = sum(r.valid_attempts for r in onr)
        tva_on = sum(r.valid_accepted for r in onr)
        ti_on = sum(r.invalid_attempts for r in onr)
        tir_on = sum(r.invalid_rejected for r in onr)
        ti_off = sum(r.invalid_attempts for r in offr)
        tia_off = ti_off - sum(r.invalid_rejected for r in offr)
        gr_on = tva_on / tv_on if tv_on else 0.0
        bp_on = tir_on / ti_on if ti_on else 0.0
        br_off = tia_off / ti_off if ti_off else 0.0
        eff = (br_off - (1 - bp_on)) / br_off if br_off else 0.0
        print("E20: Template Compliance Effectiveness")
        print(f"Condition A (template ON): bad_transition_rate = {1 - bp_on:.2f}")
        print(f"Condition B (template OFF): bad_transition_rate = {br_off:.2f}")
        print(f"Effectiveness: ({br_off:.2f} - {1 - bp_on:.2f}) / {br_off:.2f} = {eff:.2f}")
        return ExperimentResult(
            experiment_id=self.experiment_id,
            status="passed" if eff >= 0.10 else "partial",
            metrics={
                "effectiveness": round(eff, 4),
                "good_transition_rate_on": round(gr_on, 4),
                "bad_transition_prevention_on": round(bp_on, 4),
                "bad_transition_rate_off": round(br_off, 4),
                "total_rounds": 20,
                "agents": 5,
                "concepts": 3,
            },
            raw_data=[
                {
                    "round": r.round_num,
                    "template_on": r.template_on,
                    "valid_attempts": r.valid_attempts,
                    "valid_accepted": r.valid_accepted,
                    "invalid_attempts": r.invalid_attempts,
                    "invalid_rejected": r.invalid_rejected,
                }
                for r in round_results
            ],
        )

    @staticmethod
    def _apply(engine, concept, action, agent, rn, params):
        if action == EventType.VALIDATE:
            engine.transition(concept, DiscoveryStatus.VALIDATED, agent, f"R{rn}")
        elif action == EventType.DEPRECATE:
            engine.transition(concept, DiscoveryStatus.DEPRECATED, agent, f"R{rn}")
        elif action == EventType.FORK:
            engine.transition(concept, DiscoveryStatus.FORKED, agent, f"R{rn}")
        elif action == EventType.ARCHIVE:
            engine.transition(concept, DiscoveryStatus.ARCHIVED, agent, f"R{rn}")
        else:
            engine.chains[concept].append(
                Event(
                    concept_id=concept,
                    event_type=action,
                    actor=agent,
                    reasoning=f"R{rn}",
                    payload=params,
                )
            )


if __name__ == "__main__":
    E20TemplateEffectiveness().run()
