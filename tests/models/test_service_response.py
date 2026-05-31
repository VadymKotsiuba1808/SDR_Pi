"""
Тести для моделі ServiceResponse.
"""

from app.models.service_response import DbOperation, ServiceResponse, StatusCode


def test_service_response_success():
    """Тест успішної відповіді."""
    resp = ServiceResponse(
        status=StatusCode.OK,
        message="Success",
        operation=DbOperation.GET_CLASSES,
        data={"classes": []},
    )

    assert resp.is_success is True
    assert resp.is_error is False
    # В юніт-тестах без ініціалізованого QTranslator повертаються оригінальні рядки
    assert resp.get_title() == "Success"


def test_service_response_error():
    """Тест відповіді з помилкою."""
    resp = ServiceResponse(
        status=StatusCode.NOT_FOUND,
        message="Not found",
        operation=DbOperation.DELETE_OBJECT,
    )

    assert resp.is_success is False
    assert resp.is_error is True
    assert "Error" in resp.get_title()


def test_service_response_messages():
    """Тест отримання повідомлень статусів."""
    resp = ServiceResponse(status=StatusCode.INTERNAL_ERROR, message="Boom")
    # Має повернути стандартне повідомлення для 500 помилки
    assert "Internal server error" in resp.get_message_or_default()


def test_service_response_serialization():
    """Тест серіалізації ServiceResponse."""
    data = {
        "status": 201,
        "message": "Created",
        "operation": "add_object",
        "data": {"id": 1},
    }

    obj = ServiceResponse.from_dict(data)
    assert obj.status == StatusCode.CREATED
    assert obj.operation == DbOperation.ADD_OBJECT
    assert obj.to_dict() == data
