"""
Модульні тести для моделі DetectionEvent.

Цей модуль містить тести для перевірки коректності серіалізації,
десеріалізації та обробки даних у класі DetectionEvent.
"""

from app.models.detection_event import DetectionEvent
from app.models.source_type import SourceType


def test_detection_event_serialization() -> None:
    """
    Перевіряє правильність серіалізації та десеріалізації DetectionEvent.

    Переконується, що об'єкт коректно створюється з повного набору даних
    та правильно перетворюється назад у словник, зберігаючи всі значення.
    """
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

    assert obj.id == "e2e-123", "ID має збігатися з вхідними даними"
    assert obj.type == SourceType.RF, "Тип джерела має бути RF"
    assert obj.confidence == 0.92, "Впевненість має збігатися"
    assert obj.to_dict() == data, "Результат to_dict має бути ідентичним вхідним даним"


def test_detection_event_from_dict_minimal() -> None:
    """
    Перевіряє десеріалізацію DetectionEvent з мінімальними даними.

    Тестує здатність методу from_dict обробляти відсутні поля,
    підставляючи значення за замовчуванням.
    """
    obj = DetectionEvent.from_dict({"id": "custom-id"})
    assert obj.id == "custom-id", "ID має бути встановлено"
    assert obj.type == SourceType.RF, "Тип за замовчуванням має бути RF"
    assert obj.name == "unknown", "Назва за замовчуванням має бути unknown"
    assert obj.confidence == 0.0, "Впевненість за замовчуванням має бути 0.0"


def test_detection_event_invalid_type() -> None:
    """
    Перевіряє обробку некоректного типу джерела при десеріалізації.

    Переконується, що при отриманні невідомого типу джерела система
    автоматично встановлює безпечне значення за замовчуванням (RF).
    """
    obj = DetectionEvent.from_dict({"type": "INVALID"})
    assert obj.type == SourceType.RF, "Некоректний тип має замінюватися на RF"
