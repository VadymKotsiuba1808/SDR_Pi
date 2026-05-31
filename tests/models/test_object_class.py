"""
Тести для моделі ObjectClass.
"""

from app.models.object_class import ObjectClass


def test_object_class_serialization():
    """Тест серіалізації та десеріалізації ObjectClass."""
    data = {"id": 1, "name": "Drone"}
    obj = ObjectClass.from_dict(data)

    assert obj.id == 1
    assert obj.name == "Drone"
    assert obj.to_dict() == data


def test_object_class_from_dict_minimal():
    """Тест десеріалізації ObjectClass з мінімальними даними."""
    obj = ObjectClass.from_dict({})
    assert obj.id is None
    assert obj.name == "Unnamed"
