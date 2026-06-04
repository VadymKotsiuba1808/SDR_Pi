"""Модуль з тестами для сервісу бази даних (DatabaseService).

Ці тести перевіряють основні операції з БД: додавання/отримання класів,
об'єктів, пагінацію та обмеження цілісності. Для забезпечення ізоляції
та швидкості виконання використовується SQLite у пам'яті.
"""

import pytest
from pytestqt.qtbot import QtBot

from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass
from app.models.service_response import DbOperation, StatusCode
from pi_server.database_service import DatabaseService


@pytest.fixture
def db_service(qtbot: QtBot) -> DatabaseService:
    """Створює екземпляр DatabaseService з БД у пам'яті."""
    service = DatabaseService(db_url="sqlite:///:memory:")
    return service


def test_db_add_and_get_classes(db_service: DatabaseService, qtbot: QtBot) -> None:
    """Перевіряє успішне додавання та отримання списку класів об'єктів."""
    new_class = ObjectClass(id=None, name="UAV")

    with qtbot.wait_signal(db_service.request_finished) as blocker:
        db_service.add_class(new_class)

    resp = blocker.args[0]
    assert resp.operation == DbOperation.ADD_CLASS, "Operation should be ADD_CLASS"
    assert resp.status == StatusCode.CREATED, (
        f"Expected CREATED status, got {resp.status} ({resp.message})"
    )
    assert resp.data["name"] == "UAV", "Class name mismatch in response"

    with qtbot.wait_signal(db_service.request_finished) as blocker:
        db_service.request_classes()

    resp = blocker.args[0]
    assert resp.status == StatusCode.OK, "Expected OK status for request_classes"
    assert len(resp.data["classes"]) == 1, (
        f"Expected 1 class, got {len(resp.data['classes'])}"
    )
    assert resp.data["classes"][0]["name"] == "UAV", "Retrieved class name mismatch"


def test_db_add_object(db_service: DatabaseService, qtbot: QtBot) -> None:
    """Перевіряє додавання нового об'єкта (сигнатури) до бази даних."""
    with qtbot.wait_signal(db_service.request_finished):
        db_service.add_class(ObjectClass(id=None, name="Drone"))

    obj = DetectionObject(
        id=None,
        name="Mavic 3",
        class_id=0,  # Пошук за назвою класу "Drone"
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


def test_db_pagination(db_service: DatabaseService, qtbot: QtBot) -> None:
    """Перевіряє роботу механізму пагінації об'єктів."""
    with qtbot.wait_signal(db_service.request_finished):
        db_service.add_class(ObjectClass(id=None, name="TestClass"))

    for i in range(5):
        obj = DetectionObject(
            id=None, name=f"Obj {i}", class_id=0, object_class="TestClass"
        )
        with qtbot.wait_signal(db_service.request_finished):
            db_service.add_object(obj)

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


def test_db_delete_class_with_usage_fails(
    db_service: DatabaseService, qtbot: QtBot
) -> None:
    """Перевіряє заборону видалення класу, до якого прив'язані об'єкти."""
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

    with qtbot.wait_signal(db_service.request_finished) as blocker:
        db_service.delete_class(class_id)

    resp = blocker.args[0]
    assert resp.status == StatusCode.CONFLICT, (
        f"Should return CONFLICT when deleting used class, got {resp.status}"
    )
    assert "used by" in resp.message.lower(), (
        f"Error message should mention usage, got: {resp.message}"
    )
