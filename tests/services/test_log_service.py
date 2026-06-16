"""Тести для сервісу логування (LogService)."""

import os
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest

from app.models.detection_event import DetectionEvent
from app.models.log_entries import LogEntry, LogType, is_detection
from app.models.source_type import SourceType
from app.services.log_service import LogService


@pytest.fixture
def temp_logs_dir(tmp_path: Path) -> str:
    """Створює тимчасову директорію для логів."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    return str(logs_dir)


@pytest.fixture
def log_service(temp_logs_dir: str) -> Generator[LogService, None, None]:
    """Ініціалізує сервіс логування для тестування."""
    # Великий інтервал flush (100с) для контролю запису в тестах
    service = LogService(flush_interval=100, logs_dir=temp_logs_dir)
    yield service
    service.stop()


def create_detection_event(event_id: str = "t1") -> DetectionEvent:
    """Створює подію детекції для тестів."""
    return DetectionEvent(
        id=event_id,
        type=SourceType.RF,
        name="Mavic 3",
        object_class="drone",
        confidence=0.85,
        timestamp=datetime.now().isoformat(),
        distance_km=1.5,
        angle=45.0,
        frequency_hz=2400.0,
    )


def test_add_log_and_force_flush(log_service: LogService, temp_logs_dir: str) -> None:
    event = create_detection_event("test_id")
    entry = LogEntry(type=LogType.DETECTION, payload=event)

    log_service.add_log(entry)
    log_service.force_flush()

    # Перевіряємо створення файлу сесії
    files = [f for f in os.listdir(temp_logs_dir) if f.startswith("session_")]
    assert len(files) >= 1, "Log session file should be created"

    # Перевіряємо коректність збережених даних
    loaded_entries = log_service.load_session_data(files[0])
    assert len(loaded_entries) >= 1, "Should load at least 1 entry"
    assert loaded_entries[0].type == LogType.DETECTION, "Loaded log type mismatch"
    assert (
        is_detection(loaded_entries[0]) and loaded_entries[0].payload.id == "test_id"
    ), "Loaded event ID mismatch"


def test_load_non_existent_session(log_service: LogService) -> None:
    entries = log_service.load_session_data("non_existent.jsonl")
    assert entries == [], "Should return empty list for non-existent session file"


def test_get_available_sessions(log_service: LogService, temp_logs_dir: str) -> None:
    # Створюємо фіктивний файл сесії
    fake_session = os.path.join(temp_logs_dir, "session_2024-01-01_12-00-00.jsonl")
    with open(fake_session, "w", encoding="utf-8") as f:
        f.write('{"type": "info", "timestamp": "2024-01-01T12:00:00", "payload": {}}\n')

    sessions = log_service.get_available_sessions()
    assert len(sessions) >= 1, "Should find at least 1 session file"
    assert any("2024-01-01" in s.filename for s in sessions), (
        "Should find the manually created session file"
    )


def test_session_rotation_by_date(log_service: LogService, temp_logs_dir: str) -> None:
    # Створюємо подію з минулою датою для ротації
    old_ts = "2023-01-01T10:00:00"
    event = create_detection_event("old_target")
    entry = LogEntry(type=LogType.DETECTION, payload=event, timestamp=old_ts)

    log_service.add_log(entry)
    log_service.force_flush()

    assert log_service._current_session_date == "2023-01-01", (
        "Service should rotate session date to match log entry timestamp"
    )

    files = os.listdir(temp_logs_dir)
    assert len(files) >= 1, "Log files should exist after flush"
