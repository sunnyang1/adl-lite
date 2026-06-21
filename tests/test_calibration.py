"""
Tests for adl_lite.calibration.
"""

import pytest

from adl_lite.calibration import (
    CalibrationProfile,
    MARGINCalibrator,
    band_calibrated_confidence,
    calibrated_confidence,
    context_calibrated_confidence,
    ewma_confidence,
)
from adl_lite.models import Event, EventChain, EventType


def test_calibration_profile_defaults():
    profile = CalibrationProfile(actor="agent_1")
    assert profile.accuracy_score == 0.5


def test_calibration_profile_clamping():
    profile = CalibrationProfile(actor="agent_1", accuracy_score=1.5)
    assert profile.accuracy_score == 1.0
    profile2 = CalibrationProfile(actor="agent_2", accuracy_score=-0.3)
    assert profile2.accuracy_score == 0.0


def test_calibrated_confidence_single_actor(tmp_path):
    calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
    calibrator.update_accuracy("agent_1", 0.6)
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="agent_1",
            payload={"confidence": 0.9},
        )
    ]
    result = calibrated_confidence(events, calibrator)
    assert result == pytest.approx(0.9)  # 0.9 * 0.6 / 0.6 = 0.9


def test_calibrated_confidence_multiple_actors(tmp_path):
    calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
    calibrator.update_accuracy("agent_1", 0.6)
    calibrator.update_accuracy("agent_2", 0.8)
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="agent_1",
            payload={"confidence": 0.9},
        ),
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="agent_2",
            payload={"confidence": 0.8},
        ),
    ]
    result = calibrated_confidence(events, calibrator)
    # (0.9*0.6 + 0.8*0.8) / (0.6 + 0.8) = 1.18 / 1.4 = 0.842857...
    assert result == pytest.approx(0.842857, rel=1e-4)


def test_unknown_actor_default_accuracy(tmp_path):
    calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="unknown_agent",
            payload={"confidence": 0.9},
        )
    ]
    result = calibrated_confidence(events, calibrator)
    assert result == pytest.approx(0.9)  # 0.9 * 0.5 / 0.5 = 0.9


def test_no_validate_events(tmp_path):
    calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
    events = [
        Event(
            concept_id="test",
            event_type=EventType.REGISTER,
            actor="agent_1",
            payload={},
        )
    ]
    assert calibrated_confidence(events, calibrator) == 0.0


def test_event_chain_calibrated_confidence(tmp_path):
    calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
    calibrator.update_accuracy("agent_1", 0.8)
    chain = EventChain(concept_id="test")
    chain.append(
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="agent_1",
            payload={"confidence": 0.8},
        )
    )
    result = chain.calibrated_confidence(calibrator)
    assert result == pytest.approx(0.8)  # 0.8 * 0.8 / 0.8 = 0.8


def test_event_type_calibrate_exists():
    assert EventType.CALIBRATE == "calibrate"


# ---------------------------------------------------------------------------
# EWMA confidence tests
# ---------------------------------------------------------------------------

def test_ewma_confidence_single_event():
    """Single VALIDATE event returns its own confidence."""
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.8},
        )
    ]
    assert ewma_confidence(events, alpha=0.3) == pytest.approx(0.8)


def test_ewma_confidence_no_validate():
    """No VALIDATE events returns 0.0."""
    events = [Event(concept_id="test", event_type=EventType.REGISTER, actor="a1", payload={})]
    assert ewma_confidence(events) == 0.0


def test_ewma_confidence_time_decay():
    """Higher alpha gives more weight to recent events."""
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.5},
        ),
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a2",
            payload={"confidence": 0.9},
        ),
    ]
    # With alpha=0.3: EWMA = 0.3*0.9 + 0.7*0.5 = 0.27 + 0.35 = 0.62
    assert ewma_confidence(events, alpha=0.3) == pytest.approx(0.62)


def test_ewma_confidence_alpha_high():
    """Alpha=0.9 strongly weights the most recent event."""
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.5},
        ),
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a2",
            payload={"confidence": 0.9},
        ),
    ]
    # With alpha=0.9: EWMA = 0.9*0.9 + 0.1*0.5 = 0.81 + 0.05 = 0.86
    assert ewma_confidence(events, alpha=0.9) == pytest.approx(0.86)


def test_ewma_confidence_per_actor_max():
    """EWMA uses per-actor max confidence, not all events."""
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.5},
        ),
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.9},
        ),
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a2",
            payload={"confidence": 0.7},
        ),
    ]
    # Per-actor max: a1=0.9, a2=0.7
    # EWMA(alpha=0.3): S1=0.9, S2=0.3*0.7+0.7*0.9 = 0.21+0.63 = 0.84
    assert ewma_confidence(events, alpha=0.3) == pytest.approx(0.84)


# ---------------------------------------------------------------------------
# Context-calibrated confidence tests
# ---------------------------------------------------------------------------


def test_context_calibrated_confidence_basic(tmp_path):
    """Context calibration uses per-domain accuracy."""
    calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
    calibrator.update_accuracy("agent_1", 0.6, context="aml")
    calibrator.update_accuracy("agent_1", 0.9, context="general")
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="agent_1",
            payload={"confidence": 0.8},
        )
    ]
    # In 'aml' context: 0.8 * 0.6 = 0.48
    assert context_calibrated_confidence(events, calibrator, context="aml") == pytest.approx(0.48)
    # In 'general' context: 0.8 * 0.9 = 0.72
    assert context_calibrated_confidence(events, calibrator, context="general") == pytest.approx(
        0.72
    )


def test_context_calibrated_fallback_to_global(tmp_path):
    """Unknown context falls back to global accuracy."""
    calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
    calibrator.update_accuracy("agent_1", 0.7)
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="agent_1",
            payload={"confidence": 0.8},
        )
    ]
    # Unknown context 'fraud' falls back to global 0.7
    assert context_calibrated_confidence(events, calibrator, context="fraud") == pytest.approx(0.56)


# ---------------------------------------------------------------------------
# Band-calibrated confidence tests
# ---------------------------------------------------------------------------


def test_band_calibrated_confidence_low_band():
    """Low-confidence band gets boosted."""
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.2},
        )
    ]
    # Low band [0.0, 0.3) gets +0.15 → 0.35
    assert band_calibrated_confidence(events) == pytest.approx(0.35)


def test_band_calibrated_confidence_high_band():
    """High-confidence band gets dampened."""
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.9},
        )
    ]
    # High band [0.7, 1.0] gets -0.10 → 0.80
    assert band_calibrated_confidence(events) == pytest.approx(0.80)


def test_band_calibrated_confidence_with_calibrator(tmp_path):
    """Band correction weighted by per-actor accuracy."""
    calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
    calibrator.update_accuracy("a1", 0.5)
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.9},
        )
    ]
    # High band correction -0.10 * accuracy 0.5 = -0.05 → 0.85
    assert band_calibrated_confidence(events, calibrator) == pytest.approx(0.85)


def test_band_calibrated_confidence_multiple_actors():
    """Multiple actors in different bands."""
    events = [
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.2},
        ),
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a2",
            payload={"confidence": 0.9},
        ),
    ]
    # a1: 0.2 + 0.15 = 0.35; a2: 0.9 - 0.10 = 0.80; mean = (0.35+0.80)/2 = 0.575
    assert band_calibrated_confidence(events) == pytest.approx(0.575)


# ---------------------------------------------------------------------------
# EventChain integration tests
# ---------------------------------------------------------------------------


def test_event_chain_ewma_confidence():
    chain = EventChain(concept_id="test")
    chain.append(
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.5},
        )
    )
    chain.append(
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a2",
            payload={"confidence": 0.9},
        )
    )
    assert chain.ewma_confidence(alpha=0.3) == pytest.approx(0.62)


def test_event_chain_context_calibrated(tmp_path):
    calibrator = MARGINCalibrator(path=tmp_path / "cal.yaml")
    calibrator.update_accuracy("a1", 0.6, context="aml")
    chain = EventChain(concept_id="test")
    chain.append(
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.8},
        )
    )
    assert chain.context_calibrated_confidence(calibrator, context="aml") == pytest.approx(0.48)


def test_event_chain_band_calibrated():
    chain = EventChain(concept_id="test")
    chain.append(
        Event(
            concept_id="test",
            event_type=EventType.VALIDATE,
            actor="a1",
            payload={"confidence": 0.9},
        )
    )
    assert chain.band_calibrated_confidence() == pytest.approx(0.80)


def test_yaml_persistence(tmp_path):
    path = tmp_path / "calibration.yaml"
    calibrator = MARGINCalibrator(path=path)
    calibrator.update_accuracy("agent_1", 0.75)
    calibrator2 = MARGINCalibrator(path=path)
    calibrator2.load_profiles()
    assert calibrator2.get_accuracy("agent_1") == pytest.approx(0.75)


def test_yaml_persistence_with_context(tmp_path):
    path = tmp_path / "calibration.yaml"
    calibrator = MARGINCalibrator(path=path)
    calibrator.update_accuracy("agent_1", 0.6, context="aml")
    calibrator2 = MARGINCalibrator(path=path)
    calibrator2.load_profiles()
    assert calibrator2.get_accuracy("agent_1", context="aml") == pytest.approx(0.6)
    assert calibrator2.get_accuracy("agent_1", context="general") == pytest.approx(0.5)  # fallback


def test_yaml_load_missing_file(tmp_path):
    path = tmp_path / "missing.yaml"
    calibrator = MARGINCalibrator(path=path)
    calibrator.load_profiles()
    assert calibrator._profiles == {}
    assert calibrator._context_profiles == {}
