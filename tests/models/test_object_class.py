"""Юніт-тести для моделі `ObjectClass`."""

from app.models.object_class import ObjectClass


def test_object_class_serialization() -> None:
    data = {"id": 1, "name": "Drone"}
    obj = ObjectClass.from_dict(data)

    assert obj.id == 1, "Object ID should match input data"
    assert obj.name == "Drone", "Object name should match input data"
    assert obj.to_dict() == data, (
        "Serialized object should match the original dictionary"
    )


def test_object_class_from_dict_minimal() -> None:
    obj = ObjectClass.from_dict({})
    assert obj.id is None, "ID should be None if not provided"
    assert obj.name == "Unnamed", "Default name should be 'Unnamed'"
