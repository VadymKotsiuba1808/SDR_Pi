"""
Модуль для тестування менеджера детекцій (DetectionManager).

Цей модуль містить набір тестів для перевірки логіки управління цілями,
включаючи додавання, оновлення, видалення за TTL та візуальну індексацію.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.detection_manager import DetectionManager
from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType


@pytest.fixture
def mock_settings() -> MagicMock:
    """
    Створює макет (mock) об'єкта налаштувань.

    Returns:
        MagicMock: Об'єкт налаштувань з визначеним TTL для детекцій.
    """
    settings = MagicMock()
    settings.detection_ttl_s = 2
    return settings


@pytest.fixture
def manager(mock_settings: MagicMock) -> DetectionManager:
    """
    Ініціалізує екземпляр DetectionManager для тестів.

    Зупиняє внутрішній таймер перевірки TTL, щоб уникнути недетермінованої
    поведінки під час виконання тестів.

    Args:
        mock_settings: Фікстура макета налаштувань.

    Returns:
        DetectionManager: Налаштований менеджер детекцій.
    """
    m = DetectionManager(mock_settings)
    m.ttl_timer.stop()
    return m


def create_event(
    event_id: str = "t1",
    freq: float = 433.0,
    dist: float = 1.0,
    angle: float = 45.0,
) -> DetectionEvent:
    """
    Допоміжна функція для швидкого створення об'єкта події детекції.

    Args:
        event_id: Унікальний ідентифікатор події.
        freq: Частота сигналу в Гц (за замовчуванням МГц для простоти).
        dist: Дистанція до об'єкта в км.
        angle: Азимут об'єкта в градусах.

    Returns:
        DetectionEvent: Сформований об'єкт події.
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


def test_add_new_detection(manager: DetectionManager) -> None:
    """
    Перевіряє успішне додавання нової цілі до менеджера.

    Цей тест гарантує, що при отриманні нової події менеджер створює запис
    у списку активних цілей та призначає йому коректний візуальний індекс.
    """
    event = create_event(event_id="target_1", freq=433920000)
    manager.add_detection(event)

    assert len(manager.active_targets) == 1, "Ціль повинна бути додана до списку"
    assert "target_1" in manager.active_targets, "ID цілі має бути ключем у словнику"
    assert manager.active_targets["target_1"].visual_index == 1, (
        "Перша ціль має отримати індекс 1"
    )


def test_update_existing_detection(manager: DetectionManager) -> None:
    """
    Перевіряє оновлення параметрів існуючої цілі.

    Тест імітує отримання другого пакету даних для тієї самої цілі (з тим самим ID)
    та перевіряє, чи оновилася дистанція без створення нового об'єкта.
    """
    event1 = create_event(event_id="target_1", freq=433920000, dist=1.0)
    manager.add_detection(event1)

    # Оновлюємо дистанцію для перевірки реакції менеджера на зміну даних
    event2 = create_event(event_id="target_1", freq=433920000, dist=1.5)
    manager.add_detection(event2)

    assert len(manager.active_targets) == 1, (
        "Кількість цілей не повинна збільшуватися при оновленні"
    )
    assert manager.active_targets["target_1"].event.distance_km == 1.5, (
        "Дистанція має бути оновлена"
    )


def test_ignore_logic(manager: DetectionManager) -> None:
    """
    Перевіряє роботу механізму ігнорування хибних спрацювань.

    Якщо ID цілі знаходиться в списку ігнорування, менеджер не повинен
    додавати її до списку активних цілей.
    """
    # Додаємо ID в список ігнорування на 1 секунду
    manager.ignored_ids["target_1"] = datetime.now() + timedelta(seconds=1)

    event = create_event(event_id="target_1")
    manager.add_detection(event)

    assert len(manager.active_targets) == 0, (
        "Ціль з ігнорованим ID не повинна додаватися"
    )


def test_manual_removal(manager: DetectionManager) -> None:
    """
    Перевіряє ручне видалення цілі користувачем.

    При ручному видаленні ціль має зникнути зі списку активних, а її ID
    має потрапити до списку ігнорування, щоб уникнути повторного миттєвого додавання.
    """
    event = create_event(event_id="target_1")
    manager.add_detection(event)
    assert len(manager.active_targets) == 1

    manager.remove_detection("target_1")
    assert len(manager.active_targets) == 0, "Ціль має бути видалена"
    assert "target_1" in manager.ignored_ids, "ID видаленої цілі має потрапити в ігнор"


def test_ttl_expiration(manager: DetectionManager, mock_settings: MagicMock) -> None:
    """
    Перевіряє автоматичне видалення цілей за часом життя (TTL).

    Тест штучно змінює час останнього виявлення цілі, щоб зімітувати її
    застарілість, та запускає внутрішню перевірку TTL.
    """
    event = create_event(event_id="target_1")
    manager.add_detection(event)

    # Імітуємо, що ціль бачили 3 секунди тому (при TTL = 2)
    manager.active_targets["target_1"].last_seen = datetime.now() - timedelta(seconds=3)

    manager._check_ttl()
    assert len(manager.active_targets) == 0, "Ціль має бути видалена за TTL"


def test_visual_indexing(manager: DetectionManager) -> None:
    """
    Перевіряє послідовність присвоєння візуальних індексів.

    Це важливо для зручності оператора (відображення номерів цілей на мапі/списку).
    Індекси мають бути унікальними та зростати.
    """
    event1 = create_event(event_id="t1")
    event2 = create_event(event_id="t2")

    manager.add_detection(event1)
    manager.add_detection(event2)

    assert manager.active_targets["t1"].visual_index == 1
    assert manager.active_targets["t2"].visual_index == 2

    # Видаляємо стару ціль та додаємо нову, перевіряючи інкремент індексу
    manager.remove_detection("t1")
    event3 = create_event(event_id="t3")
    manager.add_detection(event3)

    assert manager.active_targets["t3"].visual_index == 3, "Наступний індекс має бути 3"


def test_cleanup_resets_indexing(manager: DetectionManager) -> None:
    """
    Перевіряє скидання лічильника індексів при повному очищенні списку цілей.

    Якщо в системі не залишилося жодної цілі, наступна нова ціль повинна
    знову отримати індекс 1 для чистоти відображення.
    """
    manager.add_detection(create_event(event_id="t1"))
    manager.remove_detection("t1")

    # Всі цілі зникли -> внутрішній лічильник мав скинутися до 1
    assert manager.next_index == 1, (
        "Лічильник індексів має скинутися після видалення останньої цілі"
    )

    manager.add_detection(create_event(event_id="t2"))
    assert manager.active_targets["t2"].visual_index == 1, (
        "Нова ціль після очищення має отримати індекс 1"
    )
