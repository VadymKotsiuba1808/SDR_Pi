"""Тести для моделі DetectionObject.

Цей модуль містить набір тестів для перевірки функціональності моделі
DetectionObject, зокрема серіалізації та десеріалізації даних.
"""

from app.models.detection_object import DetectionObject


def test_detection_object_serialization() -> None:
    """Перевіряє коректність серіалізації та десеріалізації DetectionObject.

    Тест ініціалізує об'єкт з повного словника даних, перевіряє правильність
    заповнення атрибутів та звіряє результат методу `to_dict()` з вихідними даними.
    """
    data = {
        "id": 10,
        "name": "Mavic 3",
        "class_id": 1,
        "object_class": "Drone",
        "is_dangerous": True,
        "rf_params_hz": ["2400-2483.5"],
        "sound_params_hz": [1000, 2000],
    }
    obj = DetectionObject.from_dict(data)

    assert obj.id == 10, "ID об'єкта має бути 10"
    assert obj.name == "Mavic 3", "Назва об'єкта має бути 'Mavic 3'"
    assert obj.is_dangerous is True, "Об'єкт має бути позначений як небезпечний"
    assert obj.rf_params_hz == ["2400-2483.5"], "РЧ параметри мають збігатися"
    assert obj.to_dict() == data, (
        "Серіалізований об'єкт має збігатися з вхідними даними"
    )


def test_detection_object_from_dict_minimal() -> None:
    """Перевіряє десеріалізацію DetectionObject з порожнім або мінімальним словником.

    Тест підтверджує, що модель коректно обробляє відсутність даних,
    встановлюючи значення за замовчуванням для обов'язкових полів.
    """
    obj = DetectionObject.from_dict({})
    assert obj.id is None, "ID має бути None для порожніх даних"
    assert obj.name == "Unnamed", "Назва за замовчуванням має бути 'Unnamed'"
    assert obj.class_id == 0, "ID класу за замовчуванням має бути 0"
    assert obj.rf_params_hz == [], "Список РЧ параметрів має бути порожнім"
