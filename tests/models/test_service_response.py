"""
Тести для моделі ServiceResponse.
"""

from app.models.service_response import DbOperation, ServiceResponse, StatusCode


def test_service_response_success() -> None:
    resp = ServiceResponse(
        status=StatusCode.OK,
        message="Success",
        operation=DbOperation.GET_CLASSES,
        data={"classes": []},
    )

    assert resp.is_success is True, "Response should be successful"
    assert resp.is_error is False, "Response should not be an error"
    assert resp.get_title() == "Success", "Title should match the passed message"


def test_service_response_error() -> None:
    resp = ServiceResponse(
        status=StatusCode.NOT_FOUND,
        message="Not found",
        operation=DbOperation.DELETE_OBJECT,
    )

    assert resp.is_success is False, "Response should not be successful"
    assert resp.is_error is True, "Response should be an error"
    assert "Error" in resp.get_title(), (
        "Title should contain the word 'Error' for errors"
    )


def test_service_response_messages() -> None:
    resp = ServiceResponse(status=StatusCode.INTERNAL_ERROR, message="Boom")
    assert "Internal server error" in resp.get_message_or_default(), (
        "Default message for server error should be returned"
    )


def test_service_response_serialization() -> None:
    data = {
        "status": 201,
        "message": "Created",
        "operation": "add_object",
        "data": {"id": 1},
    }

    obj = ServiceResponse.from_dict(data)
    assert obj.status == StatusCode.CREATED, "Status should be CREATED (201)"
    assert obj.operation == DbOperation.ADD_OBJECT, "Operation should be ADD_OBJECT"
    assert obj.to_dict() == data, "Serialized object should match the input data"
