"""
Тести для менеджера детекцій (DetectionManager).
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.detection_manager import DetectionManager
from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType


@pytest.fixture
def mock_settings():
    """
    Фікстура для макета налаштувань.
    """
    settings = MagicMock()
    settings.detection_ttl_s = 2
    return settings


@pytest.fixture
def manager(mock_settings):
    """
    Фікстура для ініціалізації DetectionManager.
    Ми зупиняємо внутрішній таймер, щоб він не впливав на тести асинхронно.
    """
    m = DetectionManager(mock_settings)
    m.ttl_timer.stop()
    return m


def create_event(event_id="t1", freq=433.0, dist=1.0, angle=45.0):
    """
    Допоміжна функція для створення події детекції.
    """
    return DetectionEvent(
        id=event_id,
        type=SourceType.RF,
        name="Test",
        object_class="drone",
        confidence=0.9,
        timestamp=datetime.now().isoformat(),
        distance_km=dist,
        angle=angle,
        frequency_hz=freq,
    )


def test_add_new_detection(manager) -> None:
    """
    Тест додавання нової цілі.
    """
    event = create_event(event_id="target_1", freq=433920000)
    manager.add_detection(event)

    assert len(manager.active_targets) == 1
    assert "target_1" in manager.active_targets
    assert manager.active_targets["target_1"].visual_index == 1


def test_update_existing_detection(manager) -> None:
    """
    Тест оновлення існуючої цілі.
    """
    event1 = create_event(event_id="target_1", freq=433920000, dist=1.0)
    manager.add_detection(event1)

    # Оновлюємо дистанцію
    event2 = create_event(event_id="target_1", freq=433920000, dist=1.5)
    manager.add_detection(event2)

    assert len(manager.active_targets) == 1
    assert manager.active_targets["target_1"].event.distance_km == 1.5


def test_ignore_logic(manager) -> None:
    """
    Тест логіки ігнорування (False Alarm).
    """
    # Додаємо ID в список ігнорування на 1 секунду
    manager.ignored_ids["target_1"] = datetime.now() + timedelta(seconds=1)

    event = create_event(event_id="target_1")
    manager.add_detection(event)

    # Ціль не повинна бути додана
    assert len(manager.active_targets) == 0


def test_manual_removal(manager) -> None:
    """
    Тест ручного видалення цілі.
    """
    event = create_event(event_id="target_1")
    manager.add_detection(event)
    assert len(manager.active_targets) == 1

    manager.remove_detection("target_1")
    assert len(manager.active_targets) == 0
    assert "target_1" in manager.ignored_ids


def test_ttl_expiration(manager, mock_settings) -> None:
    """
    Тест видалення цілей за TTL.
    """
    event = create_event(event_id="target_1")
    manager.add_detection(event)

    # Імітуємо, що ціль бачили 3 секунди тому (TTL = 2)
    manager.active_targets["target_1"].last_seen = datetime.now() - timedelta(seconds=3)

    manager._check_ttl()
    assert len(manager.active_targets) == 0


def test_visual_indexing(manager) -> None:
    """
    Тест послідовності візуальних індексів.
    """
    event1 = create_event(event_id="t1")
    event2 = create_event(event_id="t2")

    manager.add_detection(event1)
    manager.add_detection(event2)

    assert manager.active_targets["t1"].visual_index == 1
    assert manager.active_targets["t2"].visual_index == 2

    # Видаляємо одну, додаємо нову
    manager.remove_detection("t1")
    event3 = create_event(event_id="t3")
    manager.add_detection(event3)

    assert manager.active_targets["t3"].visual_index == 3


def test_cleanup_resets_indexing(manager) -> None:
    """
    Тест скидання індексації, якщо всі цілі зникли.
    """
    manager.add_detection(create_event(event_id="t1"))
    manager.remove_detection("t1")

    # Всі цілі зникли -> cleanup мав спрацювати
    assert manager.next_index == 1

    manager.add_detection(create_event(event_id="t2"))
    assert manager.active_targets["t2"].visual_index == 1
