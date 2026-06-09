"""
Тести для моделі DetectionObject.
"""

from app.models.detection_object import DetectionObject


def test_detection_object_serialization():
    """Тест серіалізації та десеріалізації DetectionObject."""
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

    assert obj.id == 10
    assert obj.name == "Mavic 3"
    assert obj.is_dangerous is True
    assert obj.rf_params_hz == ["2400-2483.5"]
    assert obj.to_dict() == data


def test_detection_object_from_dict_minimal():
    """Тест десеріалізації DetectionObject з мінімальними даними."""
    obj = DetectionObject.from_dict({})
    assert obj.id is None
    assert obj.name == "Unnamed"
    assert obj.class_id == 0
    assert obj.rf_params_hz == []
