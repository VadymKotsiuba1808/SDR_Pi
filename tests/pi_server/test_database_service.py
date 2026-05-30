"""
Тести для DatabaseService (pi_server).
Використовується SQLite в пам'яті для ізоляції.
"""

import pytest

from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from app.models.service_response import DbOperation, StatusCode
from pi_server.database_service import DatabaseService


@pytest.fixture
def db_service(qtbot):
    """Фікстура для ініціалізації DatabaseService з БД в пам'яті."""
    # Використовуємо sqlite:///:memory: для тестів
    service = DatabaseService(db_url="sqlite:///:memory:")
    return service


def test_db_add_and_get_classes(db_service, qtbot):
    """Тест додавання та отримання класів об'єктів."""
    new_class = ObjectClass(id=None, name="UAV")

    with qtbot.wait_signal(db_service.request_finished) as blocker:
        db_service.add_class(new_class)

    resp = blocker.args[0]
    assert resp.operation == DbOperation.ADD_CLASS, "Operation should be ADD_CLASS"
    assert resp.status == StatusCode.CREATED, (
        f"Expected CREATED status, got {resp.status} ({resp.message})"
    )
    assert resp.data["name"] == "UAV", "Class name mismatch in response"

    # Перевіряємо отримання списку класів
    with qtbot.wait_signal(db_service.request_finished) as blocker:
        db_service.request_classes()

    resp = blocker.args[0]
    assert resp.status == StatusCode.OK, "Expected OK status for request_classes"
    assert len(resp.data["classes"]) == 1, (
        f"Expected 1 class, got {len(resp.data['classes'])}"
    )
    assert resp.data["classes"][0]["name"] == "UAV", "Retrieved class name mismatch"


def test_db_add_object(db_service, qtbot):
    """Тест додавання об'єкта (сигнатури)."""
    # Спочатку додаємо клас і чекаємо на завершення
    with qtbot.wait_signal(db_service.request_finished):
        db_service.add_class(ObjectClass(id=None, name="Drone"))

    obj = DetectionObject(
        id=None,
        name="Mavic 3",
        class_id=0,  # Буде знайдено за назвою класу "Drone"
        object_class="Drone",
        is_dangerous=True,
        rf_params_hz=["2.4GHz"],
        sound_params_hz=[100, 200],
    )

    with qtbot.wait_signal(db_service.request_finished) as blocker:
        db_service.add_object(obj)

    resp = blocker.args[0]
    assert resp.status == StatusCode.CREATED, (
        f"Expected CREATED status, got {resp.status} ({resp.message})"
    )
    assert resp.data["name"] == "Mavic 3", "Object name mismatch"
    assert resp.data["object_class"] == "Drone", "Object class mismatch"


def test_db_pagination(db_service, qtbot):
    """Тест пагінації об'єктів."""
    with qtbot.wait_signal(db_service.request_finished):
        db_service.add_class(ObjectClass(id=None, name="TestClass"))

    # Додаємо 5 об'єктів послідовно
    for i in range(5):
        obj = DetectionObject(
            id=None, name=f"Obj {i}", class_id=0, object_class="TestClass"
        )
        with qtbot.wait_signal(db_service.request_finished):
            db_service.add_object(obj)

    # Запитуємо першу сторінку (розмір 2)
    with qtbot.wait_signal(db_service.request_finished) as blocker:
        db_service.request_objects_page(page=1, page_size=2)

    resp = blocker.args[0]
    assert resp.status == StatusCode.OK, "Expected OK status for pagination"
    assert len(resp.data["items"]) == 2, (
        f"Expected 2 items on page, got {len(resp.data['items'])}"
    )
    assert resp.data["total"] == 5, f"Expected total 5 items, got {resp.data['total']}"
    assert resp.data["total_pages"] == 3, (
        f"Expected 3 total pages, got {resp.data['total_pages']}"
    )


def test_db_delete_class_with_usage_fails(db_service, qtbot):
    """Тест: неможливо видалити клас, який використовується об'єктами."""
    # 1. Створюємо клас та об'єкт послідовно
    with qtbot.wait_signal(db_service.request_finished) as blocker:
        db_service.add_class(ObjectClass(id=None, name="Danger"))

    class_data = blocker.args[0].data
    assert class_data is not None, "Class data should not be None after creation"
    class_id = class_data["id"]

    with qtbot.wait_signal(db_service.request_finished):
        db_service.add_object(
            DetectionObject(
                id=None, name="Weapon", class_id=class_id, object_class="Danger"
            )
        )

    # 2. Спробуємо видалити клас
    with qtbot.wait_signal(db_service.request_finished) as blocker:
        db_service.delete_class(class_id)

    resp = blocker.args[0]
    assert resp.status == StatusCode.CONFLICT, (
        f"Should return CONFLICT when deleting used class, got {resp.status}"
    )
    assert "used by" in resp.message.lower(), (
        f"Error message should mention usage, got: {resp.message}"
    )
