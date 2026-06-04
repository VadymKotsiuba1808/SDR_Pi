"""Юніт-тести для PiNetworkService."""

import json
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtNetwork import QTcpSocket

from app.models.detection_event import DetectionEvent
from app.models.gps_data import GPSData
from app.models.service_response import DbOperation, ServiceResponse, StatusCode
from app.services.pi_network_service import PiNetworkService


@pytest.fixture
def mock_settings() -> MagicMock:
    """Створює макет налаштувань для тестування."""
    settings = MagicMock()
    settings.pi_target_ip = "127.0.0.1"
    settings.pi_target_port = 6000
    return settings


@pytest.fixture
def network_service(
    mock_settings: MagicMock,
) -> Generator[tuple[PiNetworkService, MagicMock], None, None]:
    """Ініціалізує PiNetworkService з підміненим QTcpSocket."""
    # Зберігаємо оригінальні Enum для коректної перевірки станів
    with patch("app.services.pi_network_service.QTcpSocket") as mock_socket_class:
        mock_socket_class.SocketState = QTcpSocket.SocketState
        mock_socket = mock_socket_class.return_value
        mock_socket.state.return_value = QTcpSocket.SocketState.ConnectedState

        service = PiNetworkService(mock_settings)
        service.socket = mock_socket
        yield service, mock_socket


def test_send_packet_success(
    network_service: tuple[PiNetworkService, MagicMock],
) -> None:
    """Перевіряє успішну відправку JSON-пакета."""
    service, mock_socket = network_service

    action = "test_action"
    data = {"param": "value"}
    service.send_packet(action, data)

    assert mock_socket.write.called
    args, _ = mock_socket.write.call_args
    sent_payload = json.loads(args[0].decode("utf-8").strip())

    assert sent_payload["action"] == action
    assert sent_payload["data"] == data
    assert "timestamp" in sent_payload


def test_send_packet_no_connection(
    network_service: tuple[PiNetworkService, MagicMock],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Перевіряє обробку відсутності з'єднання при відправці."""
    service, mock_socket = network_service
    mock_socket.state.return_value = QTcpSocket.SocketState.UnconnectedState

    with caplog.at_level("WARNING"):
        service.send_packet("action")
        assert "Cannot send packet: No connection." in caplog.text

    assert not mock_socket.write.called


def test_read_data_gps_signal(
    network_service: tuple[PiNetworkService, MagicMock], qtbot
) -> None:
    """Перевіряє обробку вхідних GPS-даних."""
    service, mock_socket = network_service

    payload = {
        "action": "gps_position",
        "data": {
            "lat": 50.45,
            "lon": 30.52,
            "strength": 80,
            "timestamp": "2026-05-30T12:00:00",
        },
    }
    json_bytes = (json.dumps(payload) + "\n").encode("utf-8")

    mock_line = MagicMock()
    mock_line.data.return_value = json_bytes
    mock_socket.canReadLine.side_effect = [True, False]
    mock_socket.readLine.return_value.trimmed.return_value = mock_line

    with qtbot.waitSignal(service.gps_received, timeout=1000) as blocker:
        service._read_data()

    received_gps = blocker.args[0]
    assert isinstance(received_gps, GPSData)
    assert received_gps.lat == 50.45
    assert received_gps.lon == 30.52


def test_read_data_detection_signal(
    network_service: tuple[PiNetworkService, MagicMock], qtbot
) -> None:
    """Перевіряє обробку події детекції."""
    service, mock_socket = network_service

    payload = {
        "action": "detection",
        "data": {
            "id": "event_123",
            "timestamp": "2026-05-30T12:00:00",
            "frequency_hz": 433920000,
            "signal_level_db": -75.5,
            "object_name": "Test Drone",
        },
    }
    json_bytes = (json.dumps(payload) + "\n").encode("utf-8")

    mock_line = MagicMock()
    mock_line.data.return_value = json_bytes
    mock_socket.canReadLine.side_effect = [True, False]
    mock_socket.readLine.return_value.trimmed.return_value = mock_line

    with qtbot.waitSignal(service.detection_received, timeout=1000) as blocker:
        service._read_data()

    event = blocker.args[0]
    assert isinstance(event, DetectionEvent)
    assert event.id == "event_123"
    assert event.frequency_hz == 433920000


def test_read_data_db_result(
    network_service: tuple[PiNetworkService, MagicMock], qtbot
) -> None:
    """Перевіряє обробку результату операції з БД."""
    service, mock_socket = network_service

    payload = {
        "action": "db_operation_result",
        "data": {
            "operation": "add_object",
            "status": 201,
            "message": "Created",
            "data": {"id": 10},
        },
    }
    json_bytes = (json.dumps(payload) + "\n").encode("utf-8")

    mock_line = MagicMock()
    mock_line.data.return_value = json_bytes
    mock_socket.canReadLine.side_effect = [True, False]
    mock_socket.readLine.return_value.trimmed.return_value = mock_line

    with qtbot.waitSignal(service.request_finished, timeout=1000) as blocker:
        service._read_data()

    response = blocker.args[0]
    assert isinstance(response, ServiceResponse)
    assert response.operation == DbOperation.ADD_OBJECT
    assert response.status == StatusCode.CREATED


def test_request_methods(network_service: tuple[PiNetworkService, MagicMock]) -> None:
    """Перевіряє допоміжні методи запитів."""
    service, mock_socket = network_service

    service.request_remote_gps()
    assert mock_socket.write.called
    args, _ = mock_socket.write.call_args
    assert b"get_gps" in args[0]

    service.request_db_delete_object(42)
    args, _ = mock_socket.write.call_args
    sent_payload = json.loads(args[0].decode("utf-8").strip())
    assert sent_payload["action"] == "db_request_delete"
    assert sent_payload["data"]["id"] == 42
