"""
Тести для моделей логів (LogEntry, LogType).
"""

from app.models.detection_event import DetectionEvent
from app.models.log_entries import (
    FalseAlarmPayload,
    LogEntry,
    LogType,
    is_detection,
    is_false_alarm,
)
from app.models.source_type import SourceType


def test_log_entry_detection_serialization():
    """Тест серіалізації логу детекції."""
    det = DetectionEvent(
        id="d1",
        type=SourceType.RF,
        name="D",
        object_class="uav",
        confidence=0.9,
        timestamp="T1",
        distance_km=1.0,
        angle=0.0,
        frequency_hz=2400,
    )
    entry = LogEntry(type=LogType.DETECTION, payload=det, timestamp="T1")

    data = entry.to_dict()
    assert data["type"] == "detection"
    assert data["payload"]["id"] == "d1"

    # Десеріалізація
    restored = LogEntry.from_dict(data)
    assert restored.type == LogType.DETECTION
    assert isinstance(restored.payload, DetectionEvent)
    assert restored.payload.id == "d1"
    assert is_detection(restored) is True


def test_log_entry_false_alarm_serialization():
    """Тест серіалізації логу помилкової тривоги."""
    payload = FalseAlarmPayload(detection_id="e1", name="Drone")
    entry = LogEntry(type=LogType.FALSE_ALARM, payload=payload)

    data = entry.to_dict()
    assert data["type"] == "false_alarm"

    restored = LogEntry.from_dict(data)
    assert restored.type == LogType.FALSE_ALARM
    assert isinstance(restored.payload, FalseAlarmPayload)
    assert restored.payload.detection_id == "e1"
    assert is_false_alarm(restored) is True


def test_log_entry_invalid_type():
    """Тест обробки невідомого типу логу (має дефолтитись до DetectionEvent)."""
    data = {"type": "unknown_type", "payload": {"id": "test"}}
    entry = LogEntry.from_dict(data)
    assert entry.type == "unknown_type"
    assert isinstance(entry.payload, DetectionEvent)
    assert entry.payload.id == "test"
