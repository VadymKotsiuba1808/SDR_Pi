"""
Тести для моделі GPSData.
"""

from app.models.gps_data import GPSData


def test_gps_data_serialization():
    """Тест серіалізації та десеріалізації GPSData."""
    data = {"lat": 50.4501, "lon": 30.5234, "strength": 85}
    obj = GPSData.from_dict(data)

    assert obj.lat == 50.4501
    assert obj.lon == 30.5234
    assert obj.strength == 85
    assert obj.to_dict() == data


def test_gps_data_from_dict_minimal():
    """Тест десеріалізації GPSData з порожніми даними."""
    obj = GPSData.from_dict({})
    assert obj.lat == 0.0
    assert obj.lon == 0.0
    assert obj.strength == 0
