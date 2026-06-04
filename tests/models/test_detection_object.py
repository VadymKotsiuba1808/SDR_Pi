"""Тести для моделі DetectionObject."""

from app.models.detection_object import DetectionObject


def test_detection_object_serialization() -> None:
    # Arrange
    data = {
        "id": 10,
        "name": "Mavic 3",
        "class_id": 1,
        "object_class": "Drone",
        "is_dangerous": True,
        "rf_params_hz": ["2400-2483.5"],
        "sound_params_hz": [1000, 2000],
    }

    # Act
    obj = DetectionObject.from_dict(data)

    # Assert
    assert obj.id == 10, "Object ID should be 10"
    assert obj.name == "Mavic 3", "Object name should be 'Mavic 3'"
    assert obj.is_dangerous is True, "Object should be marked as dangerous"
    assert obj.rf_params_hz == ["2400-2483.5"], "RF parameters should match"
    assert obj.to_dict() == data, "Serialized object should match the input data"


def test_detection_object_from_dict_minimal() -> None:
    # Act
    obj = DetectionObject.from_dict({})

    # Assert
    assert obj.id is None, "ID should be None for empty data"
    assert obj.name == "Unnamed", "Default name should be 'Unnamed'"
    assert obj.class_id == 0, "Default class ID should be 0"
    assert obj.rf_params_hz == [], "RF parameters list should be empty"
