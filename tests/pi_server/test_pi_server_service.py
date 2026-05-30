"""
Тести для PiServerService (pi_server).
Перевірка TCP сервера та обробки команд.
"""

import json
import time
from unittest.mock import MagicMock

import pytest
from PyQt6.QtNetwork import QHostAddress, QTcpSocket

from app.models.detection_object import DetectionObject
from app.models.service_response import DbOperation, ServiceResponse, StatusCode
from pi_server.pi_server_service import PiServerService


@pytest.fixture
def mock_db():
    """Фікстура для мока DatabaseService."""
    db = MagicMock()
    return db


@pytest.fixture
def server(mock_db, qtbot):
    """Фікстура для PiServerService."""
    # Використовуємо випадковий порт для тестів, щоб уникнути конфліктів
    srv = PiServerService(port=0, db_service=mock_db)
    srv.start()
    yield srv
    srv.stop()


def test_server_starts_and_stops(mock_db):
    """Тест запуску та зупинки сервера."""
    srv = PiServerService(port=0, db_service=mock_db)
    srv.start()
    assert srv.server is not None, "Server should be initialized"

    assert srv.server.isListening(), "Server should be listening after start()"

    port = srv.server.serverPort()
    assert port > 0, f"Server should be bound to a valid port, got {port}"

    srv.stop()
    assert not srv.server.isListening(), "Server should stop listening after stop()"


def test_client_connection(server, qtbot):
    """Тест підключення клієнта до сервера."""
    client = QTcpSocket()
    port = server.server.serverPort()

    # Підключаємось до локального сервера
    client.connectToHost(QHostAddress.SpecialAddress.LocalHost, port)

    # Чекаємо підключення на стороні клієнта
    try:
        qtbot.wait_until(
            lambda: client.state() == QTcpSocket.SocketState.ConnectedState,
            timeout=2000,
        )

        # Чекаємо прийняття на стороні сервера
        qtbot.wait_until(lambda: server.client_socket is not None, timeout=2000)
        assert server.client_socket is not None, "Server failed to accept connection"
    finally:
        client.disconnectFromHost()


def test_db_command_routing(server, mock_db, qtbot):
    """Тест маршрутизації команд до бази даних."""
    client = QTcpSocket()
    port = server.server.serverPort()
    client.connectToHost(QHostAddress.SpecialAddress.LocalHost, port)

    try:
        qtbot.wait_until(lambda: server.client_socket is not None, timeout=2000)
        assert server.client_socket is not None, "Server did not accept client"

        # Відправляємо команду запиту класів
        packet = {"action": "db_request_classes", "data": {}}
        client.write(json.dumps(packet).encode("utf-8") + b"\n")
        client.flush()

        # Перевіряємо, чи був викликаний відповідний метод у БД
        qtbot.wait_until(lambda: mock_db.request_classes.called, timeout=2000)
        assert mock_db.request_classes.called, (
            "mock_db.request_classes should be called"
        )
    finally:
        client.disconnectFromHost()


def test_send_db_response_to_client(server, mock_db, qtbot):
    """Тест відправки відповіді від БД назад клієнту."""
    client = QTcpSocket()
    port = server.server.serverPort()
    client.connectToHost(QHostAddress.SpecialAddress.LocalHost, port)

    try:
        qtbot.wait_until(lambda: server.client_socket is not None, timeout=2000)
        assert server.client_socket is not None, "Server did not accept client"

        # Створюємо фейкову відповідь від БД
        response = ServiceResponse(
            operation=DbOperation.GET_CLASSES,
            status=StatusCode.OK,
            message="Success",
            data={"classes": []},
        )

        # Емулюємо сигнал від БД
        server.send_db_response(response)

        # Чекаємо дані на стороні клієнта
        qtbot.wait_until(lambda: client.bytesAvailable() > 0, timeout=2000)
        assert client.bytesAvailable() > 0, "Client should receive data"

        data = client.readAll().data().decode("utf-8").strip()
        received_packet = json.loads(data)

        assert received_packet["action"] == "db_operation_result", (
            "Action mismatch in received packet"
        )
        assert received_packet["data"]["operation"] == DbOperation.GET_CLASSES, (
            "Operation mismatch in data"
        )
    finally:
        client.disconnectFromHost()


def test_add_object_command(server, mock_db, qtbot):
    """Тест команди додавання об'єкта."""
    client = QTcpSocket()
    port = server.server.serverPort()
    client.connectToHost(QHostAddress.SpecialAddress.LocalHost, port)

    try:
        qtbot.wait_until(lambda: server.client_socket is not None, timeout=2000)
        assert server.client_socket is not None, "Server did not accept client"

        obj_dict = {
            "id": None,
            "name": "Test UAV",
            "class_id": 1,
            "object_class": "UAV",
            "is_dangerous": True,
            "rf_params_hz": [],
            "sound_params_hz": [],
        }

        packet = {"action": "db_request_add", "data": {"object": obj_dict}}

        client.write(json.dumps(packet).encode("utf-8") + b"\n")
        client.flush()

        # Перевіряємо, чи викликано add_object з правильним об'єктом
        qtbot.wait_until(lambda: mock_db.add_object.called, timeout=2000)
        assert mock_db.add_object.called, "mock_db.add_object should be called"

        call_args = mock_db.add_object.call_args[0][0]
        assert isinstance(call_args, DetectionObject), (
            "Argument should be DetectionObject"
        )
        assert call_args.name == "Test UAV", "Object name mismatch"
    finally:
        client.disconnectFromHost()


def test_invalid_json_handling(server, qtbot, capsys):
    """Тест обробки невалідного JSON."""
    client = QTcpSocket()
    port = server.server.serverPort()
    client.connectToHost(QHostAddress.SpecialAddress.LocalHost, port)
    qtbot.wait_until(lambda: server.client_socket is not None)

    client.write(b"invalid json data\n")
    client.flush()

    # Перевіряємо, що сервер не впав і вивів помилку в консоль
    # (В реальному житті краще перевіряти логи, але тут перевіримо що сокет живий)
    time.sleep(0.1)  # Даємо час на обробку
    assert server.client_socket.state() == QTcpSocket.SocketState.ConnectedState, (
        "Server should not close connection on invalid JSON"
    )
