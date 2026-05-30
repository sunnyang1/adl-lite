"""ADL Lite experiments.

Unified experiment registry architecture:
    base.py       — BaseExperiment + ExperimentResult
    registry.py   — @register("E2") decorator
    runner.py     — python -m experiments.runner E2 | all | list
    e1..e5.py     — Event-first experiment implementations
"""
