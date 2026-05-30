"""
Тести для сервісу логування (LogService).
"""

import os
from datetime import datetime
from pathlib import Path

import pytest

from app.models.detection_event import DetectionEvent
from app.models.log_entries import LogEntry, LogType, is_detection
from app.models.source_type import SourceType
from app.services.log_service import LogService


@pytest.fixture
def temp_logs_dir(tmp_path: Path) -> str:
    """
    Фікстура для тимчасової директорії логів.
    """
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    return str(logs_dir)


@pytest.fixture
def log_service(temp_logs_dir: str):
    """
    Фікстура для ініціалізації LogService.
    Використовуємо великий інтервал flush, щоб контролювати його вручну.
    """
    service = LogService(flush_interval=100, logs_dir=temp_logs_dir)
    yield service
    service.stop()


def create_detection_event(event_id="t1"):
    """
    Допоміжна функція для створення події детекції.
    """
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
    """
    Тест додавання логів та примусового запису на диск.
    """
    event = create_detection_event("test_id")
    entry = LogEntry(type=LogType.DETECTION, payload=event)

    log_service.add_log(entry)
    log_service.force_flush()

    # Перевіряємо наявність файлу сесії
    files = [f for f in os.listdir(temp_logs_dir) if f.startswith("session_")]
    assert len(files) >= 1

    # Завантажуємо дані та перевіряємо вміст
    loaded_entries = log_service.load_session_data(files[0])
    assert len(loaded_entries) >= 1
    assert loaded_entries[0].type == LogType.DETECTION
    assert is_detection(loaded_entries[0]) and loaded_entries[0].payload.id == "test_id"


def test_load_non_existent_session(log_service: LogService) -> None:
    """
    Тест завантаження даних з неіснуючого файлу.
    """
    entries = log_service.load_session_data("non_existent.jsonl")
    assert entries == []


def test_get_available_sessions(log_service: LogService, temp_logs_dir: str) -> None:
    """
    Тест отримання списку доступних сесій.
    """
    # Створюємо фіктивний файл сесії
    fake_session = os.path.join(temp_logs_dir, "session_2024-01-01_12-00-00.jsonl")
    with open(fake_session, "w", encoding="utf-8") as f:
        f.write('{"type": "info", "timestamp": "2024-01-01T12:00:00", "payload": {}}\n')

    sessions = log_service.get_available_sessions()
    assert len(sessions) >= 1
    assert any("2024-01-01" in s.filename for s in sessions)


def test_session_rotation_by_date(log_service: LogService, temp_logs_dir: str) -> None:
    """
    Тест створення нової сесії при зміні дати логів.
    """
    # Лог з минулого року
    old_ts = "2023-01-01T10:00:00"
    event = create_detection_event("old_target")
    entry = LogEntry(type=LogType.DETECTION, payload=event, timestamp=old_ts)

    log_service.add_log(entry)
    log_service.force_flush()

    # Має з'явитися файл сесії, де self._current_session_date буде "2023-01-01"
    assert log_service._current_session_date == "2023-01-01"

    # Перевіряємо, що в списку файлів є хоча б один (сервіс створить файл з поточним часом у назві)
    files = os.listdir(temp_logs_dir)
    assert len(files) >= 1
