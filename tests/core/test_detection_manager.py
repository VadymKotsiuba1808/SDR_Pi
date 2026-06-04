"""Тести для менеджера детекцій (DetectionManager)."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.detection_manager import DetectionManager
from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType


@pytest.fixture
def mock_settings() -> MagicMock:
    """Макет об'єкта налаштувань з TTL 2 секунди."""
    settings = MagicMock()
    settings.detection_ttl_s = 2
    return settings


@pytest.fixture
def manager(mock_settings: MagicMock) -> DetectionManager:
    """Ініціалізація DetectionManager з вимкненим таймером."""
    m = DetectionManager(mock_settings)
    m.ttl_timer.stop()
    return m


def create_event(
    event_id: str = "t1",
    freq: float = 433.0,
    dist: float = 1.0,
    angle: float = 45.0,
) -> DetectionEvent:
    """Допоміжна функція для створення події детекції."""
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


def test_add_new_detection(manager: DetectionManager) -> None:
    """Перевірка додавання нової цілі та присвоєння індексу."""
    # Arrange
    event = create_event(event_id="target_1", freq=433920000)

    # Act
    manager.add_detection(event)

    # Assert
    assert len(manager.active_targets) == 1, "Target should be added to the list"
    assert "target_1" in manager.active_targets, (
        "Target ID should be a key in the dictionary"
    )
    assert manager.active_targets["target_1"].visual_index == 1, (
        "First target should get index 1"
    )


def test_update_existing_detection(manager: DetectionManager) -> None:
    """Перевірка оновлення параметрів існуючої цілі."""
    # Arrange
    event1 = create_event(event_id="target_1", freq=433920000, dist=1.0)
    manager.add_detection(event1)
    event2 = create_event(event_id="target_1", freq=433920000, dist=1.5)

    # Act
    manager.add_detection(event2)

    # Assert
    assert len(manager.active_targets) == 1, (
        "Number of targets should not increase during update"
    )
    assert manager.active_targets["target_1"].event.distance_km == 1.5, (
        "Distance should be updated"
    )


def test_ignore_logic(manager: DetectionManager) -> None:
    """Перевірка механізму ігнорування ID."""
    # Arrange
    manager.ignored_ids["target_1"] = datetime.now() + timedelta(seconds=1)
    event = create_event(event_id="target_1")

    # Act
    manager.add_detection(event)

    # Assert
    assert len(manager.active_targets) == 0, (
        "Target with ignored ID should not be added"
    )


def test_manual_removal(manager: DetectionManager) -> None:
    """Перевірка ручного видалення цілі та потрапляння в ігнор."""
    # Arrange
    event = create_event(event_id="target_1")
    manager.add_detection(event)

    # Act
    manager.remove_detection("target_1")

    # Assert
    assert len(manager.active_targets) == 0, "Target should be removed"
    assert "target_1" in manager.ignored_ids, (
        "Deleted target ID should be added to ignored IDs"
    )


def test_ttl_expiration(manager: DetectionManager, mock_settings: MagicMock) -> None:
    """Перевірка автоматичного видалення цілей за TTL."""
    # Arrange
    event = create_event(event_id="target_1")
    manager.add_detection(event)
    manager.active_targets["target_1"].last_seen = datetime.now() - timedelta(seconds=3)

    # Act
    manager._check_ttl()

    # Assert
    assert len(manager.active_targets) == 0, "Target should be removed by TTL"


def test_visual_indexing(manager: DetectionManager) -> None:
    """Перевірка послідовності візуальних індексів."""
    # Arrange
    event1 = create_event(event_id="t1")
    event2 = create_event(event_id="t2")
    event3 = create_event(event_id="t3")

    # Act & Assert
    manager.add_detection(event1)
    manager.add_detection(event2)
    assert manager.active_targets["t1"].visual_index == 1
    assert manager.active_targets["t2"].visual_index == 2

    manager.remove_detection("t1")
    manager.add_detection(event3)
    assert manager.active_targets["t3"].visual_index == 3, "Next index should be 3"


def test_cleanup_resets_indexing(manager: DetectionManager) -> None:
    """Перевірка скидання лічильника індексів при повному очищенні."""
    # Arrange
    manager.add_detection(create_event(event_id="t1"))

    # Act
    manager.remove_detection("t1")

    # Assert
    assert manager.next_index == 1, (
        "Index counter should reset after removing the last target"
    )

    # Act
    manager.add_detection(create_event(event_id="t2"))

    # Assert
    assert manager.active_targets["t2"].visual_index == 1, (
        "New target after cleanup should get index 1"
    )
