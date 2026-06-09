"""
Тести для моделі DetectionEvent.
"""

from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType


def test_detection_event_serialization():
    """Тест серіалізації та десеріалізації DetectionEvent."""
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

    assert obj.id == "e2e-123"
    assert obj.type == SourceType.RF
    assert obj.confidence == 0.92
    assert obj.to_dict() == data


def test_detection_event_from_dict_minimal():
    """Тест десеріалізації DetectionEvent з мінімальними даними."""
    obj = DetectionEvent.from_dict({"id": "custom-id"})
    assert obj.id == "custom-id"
    assert obj.type == SourceType.RF
    assert obj.name == "unknown"
    assert obj.confidence == 0.0


def test_detection_event_invalid_type():
    """Тест обробки некоректного типу джерела."""
    obj = DetectionEvent.from_dict({"type": "INVALID"})
    assert obj.type == SourceType.RF  # Дефолтний тип
