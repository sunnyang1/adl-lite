"""Unified experiment registry — all experiments register here.

Usage:
    from experiments.registry import register, get, list_all

    @register("E2")
    class E2StatusDerivation(BaseExperiment):
        ...
"""

from __future__ import annotations

from .base import BaseExperiment

_registry: dict[str, type[BaseExperiment]] = {}


def register(experiment_id: str):
    """Decorator to register an experiment class by ID."""

    def _decorator(cls: type[BaseExperiment]) -> type[BaseExperiment]:
        cls.experiment_id = experiment_id
        _registry[experiment_id] = cls
        return cls

    return _decorator


def get(experiment_id: str) -> type[BaseExperiment] | None:
    return _registry.get(experiment_id)


def list_all() -> list[dict[str, str]]:
    return [
        {
            "id": eid,
            "name": cls.name,
            "description": cls.description,
        }
        for eid, cls in sorted(_registry.items())
    ]


def instantiate(experiment_id: str) -> BaseExperiment | None:
    cls = _registry.get(experiment_id)
    if cls is None:
        return None
    return cls()
