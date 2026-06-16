"""Тести для моделі GPSData."""

from app.models.gps_data import GPSData


def test_gps_data_serialization() -> None:
    """Перевірка повної серіалізації та десеріалізації об'єкта GPSData."""
    # Arrange
    data = {"lat": 50.4501, "lon": 30.5234, "strength": 85}

    # Act
    obj = GPSData.from_dict(data)

    # Assert
    assert obj.lat == 50.4501, f"Expected latitude to be 50.4501, but got {obj.lat}"
    assert obj.lon == 30.5234, f"Expected longitude to be 30.5234, but got {obj.lon}"
    assert obj.strength == 85, f"Expected strength to be 85, but got {obj.strength}"
    assert obj.to_dict() == data, (
        "The serialized dictionary does not match the original input"
    )


def test_gps_data_from_dict_minimal() -> None:
    """Перевірка обробки порожніх даних у from_dict."""
    # Act
    obj = GPSData.from_dict({})

    # Assert
    assert obj.lat == 0.0, f"Expected default latitude to be 0.0, but got {obj.lat}"
    assert obj.lon == 0.0, f"Expected default longitude to be 0.0, but got {obj.lon}"
    assert obj.strength == 0, (
        f"Expected default strength to be 0, but got {obj.strength}"
    )
