"""Тести для моделі DetectionEvent."""

from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType


def test_detection_event_serialization() -> None:
    """Перевірка серіалізації та десеріалізації DetectionEvent."""
    data = {
        "id": "e2e-123",
        "type": "RF",
        "name": "Phantom 4",
        "object_class": "uav",
        "confidence": 0.92,
        "timestamp": "2026-05-30T10:00:00",
        "distance_km": 0.8,
        "angle": 120.5,
        "frequency_hz": 2400.0,
    }
    obj = DetectionEvent.from_dict(data)

    assert obj.id == "e2e-123", "ID should match the input data"
    assert obj.type == SourceType.RF, "Source type should be RF"
    assert obj.confidence == 0.92, "Confidence should match"
    assert obj.to_dict() == data, "to_dict result should be identical to the input data"


def test_detection_event_from_dict_minimal() -> None:
    """Перевірка десеріалізації з мінімальними даними."""
    obj = DetectionEvent.from_dict({"id": "custom-id"})
    assert obj.id == "custom-id", "ID should be set"
    assert obj.type == SourceType.RF, "Default type should be RF"
    assert obj.name == "unknown", "Default name should be unknown"
    assert obj.confidence == 0.0, "Default confidence should be 0.0"


def test_detection_event_invalid_type() -> None:
    """Обробка некоректного типу джерела при десеріалізації."""
    obj = DetectionEvent.from_dict({"type": "INVALID"})
    assert obj.type == SourceType.RF, "Invalid type should be replaced with RF"
