"""
Тести для PiServerService (pi_server).

Цей модуль містить набір тестів для перевірки працездатності TCP сервера,
маршрутизації команд до бази даних та обробки вхідних JSON-пакетів.
"""

import json
import time
from typing import Generator
from unittest.mock import MagicMock

import pytest
from PyQt6.QtNetwork import QHostAddress, QTcpSocket

from app.models.detection_object import DetectionObject
from app.models.service_response import DbOperation, ServiceResponse, StatusCode
from pi_server.pi_server_service import PiServerService


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


@pytest.fixture
def server(mock_db: MagicMock, qtbot) -> Generator[PiServerService, None, None]:
    """Налаштовує та запускає екземпляр PiServerService для тестування."""
    srv = PiServerService(port=0, db_service=mock_db)
    srv.start()
    yield srv
    srv.stop()


def test_server_starts_and_stops(mock_db: MagicMock) -> None:
    """Перевіряє життєвий цикл сервера: запуск та коректну зупинку."""
    srv = PiServerService(port=0, db_service=mock_db)
    srv.start()
    assert srv.server is not None, "Server should be initialized"
    assert srv.server.isListening(), "Server should be listening to the port after start"

    port = srv.server.serverPort()
    assert port > 0, f"Server should be bound to a valid port, got {port}"

    srv.stop()
    assert not srv.server.isListening(), (
        "Server should stop listening after stop"
    )


def test_client_connection(server: PiServerService, qtbot) -> None:
    """Перевіряє можливість успішного підключення клієнта до сервера."""
    client = QTcpSocket()
    assert server.server is not None
    port = server.server.serverPort()

    # Спроба підключення до локального сервера
    client.connectToHost(QHostAddress.SpecialAddress.LocalHost, port)

    try:
        # Очікуємо переходу сокета в стан підключення
        qtbot.wait_until(
            lambda: client.state() == QTcpSocket.SocketState.ConnectedState,
            timeout=2000,
        )

        # Перевіряємо, чи сервер прийняв підключення та зберіг посилання на клієнтський сокет
        qtbot.wait_until(lambda: server.client_socket is not None, timeout=2000)
        assert server.client_socket is not None, (
            "Server did not accept client connection"
        )
    finally:
        client.disconnectFromHost()


def test_db_command_routing(server: PiServerService, mock_db: MagicMock, qtbot) -> None:
    """Перевіряє правильність маршрутизації JSON-команд до DatabaseService."""
    client = QTcpSocket()
    assert server.server is not None
    port = server.server.serverPort()
    client.connectToHost(QHostAddress.SpecialAddress.LocalHost, port)

    try:
        qtbot.wait_until(lambda: server.client_socket is not None, timeout=2000)
        assert server.client_socket is not None, "Server did not accept the client"

        # Відправляємо команду запиту класів об'єктів
        packet = {"action": "db_request_classes", "data": {}}
        client.write(json.dumps(packet).encode("utf-8") + b"\n")
        client.flush()

        # Перевіряємо, чи був викликаний відповідний метод у БД сервісі
        qtbot.wait_until(lambda: mock_db.request_classes.called, timeout=2000)
        assert mock_db.request_classes.called, (
            "Method mock_db.request_classes should have been called"
        )
    finally:
        client.disconnectFromHost()


def test_send_db_response_to_client(
    server: PiServerService, mock_db: MagicMock, qtbot
) -> None:
    """Перевіряє відправку результатів операцій БД підключеному клієнту."""
    client = QTcpSocket()
    assert server.server is not None
    port = server.server.serverPort()
    client.connectToHost(QHostAddress.SpecialAddress.LocalHost, port)

    try:
        qtbot.wait_until(lambda: server.client_socket is not None, timeout=2000)
        assert server.client_socket is not None, "Server did not accept the client"

        # Формуємо тестову відповідь, яку зазвичай генерує DatabaseService
        response = ServiceResponse(
            operation=DbOperation.GET_CLASSES,
            status=StatusCode.OK,
            message="Success",
            data={"classes": []},
        )

        # Емулюємо сигнал про завершення операції БД
        server.send_db_response(response)

        # Перевіряємо отримання даних клієнтом
        qtbot.wait_until(lambda: client.bytesAvailable() > 0, timeout=2000)
        assert client.bytesAvailable() > 0, (
            "Client should have received data from the server"
        )

        data = client.readAll().data().decode("utf-8").strip()
        received_packet = json.loads(data)

        assert received_packet["action"] == "db_operation_result", (
            "Mismatch in action in the packet"
        )
        assert received_packet["data"]["operation"] == DbOperation.GET_CLASSES, (
            "Mismatch in operation type in data"
        )
    finally:
        client.disconnectFromHost()


def test_add_object_command(server: PiServerService, mock_db: MagicMock, qtbot) -> None:
    """Перевіряє обробку команди додавання нового об'єкта."""
    client = QTcpSocket()
    assert server.server is not None
    port = server.server.serverPort()
    client.connectToHost(QHostAddress.SpecialAddress.LocalHost, port)

    try:
        qtbot.wait_until(lambda: server.client_socket is not None, timeout=2000)
        assert server.client_socket is not None, "Server did not accept the client"

        obj_dict: dict[str, object] = {
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

        # Перевірка виклику методу додавання з правильним типом даних
        qtbot.wait_until(lambda: mock_db.add_object.called, timeout=2000)
        assert mock_db.add_object.called, (
            "Method mock_db.add_object should have been called"
        )

        call_args = mock_db.add_object.call_args[0][0]
        assert isinstance(call_args, DetectionObject), (
            "Argument should be an instance of DetectionObject"
        )
        assert call_args.name == "Test UAV", "Object name mismatch"
    finally:
        client.disconnectFromHost()


def test_invalid_json_handling(server: PiServerService, qtbot, capsys) -> None:
    """Перевіряє стійкість сервера до отримання некоректних JSON-даних."""
    client = QTcpSocket()
    assert server.server is not None
    port = server.server.serverPort()
    client.connectToHost(QHostAddress.SpecialAddress.LocalHost, port)
    qtbot.wait_until(lambda: server.client_socket is not None)

    # Відправка невалідного JSON (сирих байтів)
    client.write(b"invalid json data\n")
    client.flush()

    # Даємо невелику затримку для асинхронної обробки помилки на стороні сервера
    time.sleep(0.1)

    assert server.client_socket is not None
    assert server.client_socket.state() == QTcpSocket.SocketState.ConnectedState, (
        "Server should not close connection upon receiving invalid JSON"
    )
