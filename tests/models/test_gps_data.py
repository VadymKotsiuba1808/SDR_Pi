"""
Модуль для тестування моделі GPSData.
"""

from app.models.gps_data import GPSData


def test_gps_data_serialization() -> None:
    """
    Перевіряє правильність серіалізації та десеріалізації об'єкта GPSData.

    Тест перевіряє створення об'єкта зі словника та зворотне перетворення
    у словник, переконуючись, що всі поля збережені коректно.
    """
    data = {"lat": 50.4501, "lon": 30.5234, "strength": 85}
    obj = GPSData.from_dict(data)

    assert obj.lat == 50.4501, f"Expected latitude to be 50.4501, but got {obj.lat}"
    assert obj.lon == 30.5234, f"Expected longitude to be 30.5234, but got {obj.lon}"
    assert obj.strength == 85, f"Expected strength to be 85, but got {obj.strength}"
    assert obj.to_dict() == data, (
        "The serialized dictionary does not match the original input"
    )


def test_gps_data_from_dict_minimal() -> None:
    """
    Перевіряє поведінку GPSData.from_dict при отриманні порожнього словника.

    Очікується, що поля будуть ініціалізовані значеннями за замовчуванням (0.0 або 0).
    """
    obj = GPSData.from_dict({})
    assert obj.lat == 0.0, f"Expected default latitude to be 0.0, but got {obj.lat}"
    assert obj.lon == 0.0, f"Expected default longitude to be 0.0, but got {obj.lon}"
    assert obj.strength == 0, (
        f"Expected default strength to be 0, but got {obj.strength}"
    )
