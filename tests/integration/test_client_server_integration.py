"""Інтеграційні тести взаємодії Desktop Client <-> Pi Server."""

import pytest

from app.models.object_class import ObjectClass
from app.models.service_response import DbOperation, StatusCode
from app.services.pi_network_service import PiNetworkService
from pi_server.database_service import DatabaseService
from pi_server.pi_server_service import PiServerService


class MockSettings:
    """
    ### MockSettings
    Мок-об'єкт для налаштувань мережевого сервісу.
    """

    def __init__(self, ip: str, port: int) -> None:
        """Ініціалізація налаштувань."""
        self.pi_target_ip = ip
        self.pi_target_port = port


@pytest.fixture
def server_instance(qtbot):
    """Запуск реального екземпляра Pi Server в ізольованому середовищі."""
    # Використовуємо SQLite в пам'яті для ізоляції тестів
    db = DatabaseService(db_url="sqlite:///:memory:")

    # port=0 дозволяє ОС автоматично виділити вільний порт
    srv = PiServerService(port=0, db_service=db)
    srv.start()

    # Чекаємо, поки сервер почне слухати
    qtbot.wait_until(
        lambda: srv.server.isListening() if srv.server else False, timeout=2000
    )

    yield srv
    srv.stop()


@pytest.fixture
def client_instance(server_instance, qtbot):
    """Ініціалізація та підключення клієнтського мережевого сервісу."""
    port = server_instance.server.serverPort()
    settings = MockSettings(ip="127.0.0.1", port=port)

    client = PiNetworkService(settings=settings)
    client.start()

    # Очікуємо стабільного TCP-з'єднання
    qtbot.wait_until(
        lambda: (
            client.socket is not None
            and client.socket.state() == client.socket.SocketState.ConnectedState
        ),
        timeout=3000,
    )

    yield client
    client.stop()


def test_integration_connection_established(client_instance) -> None:
    """Перевірка успішного встановлення з'єднання між клієнтом та сервером."""
    assert (
        client_instance.socket.state()
        == client_instance.socket.SocketState.ConnectedState
    ), "Client should have connection status ConnectedState"


def test_integration_db_get_classes_empty(client_instance, qtbot) -> None:
    """Перевірка отримання порожнього списку класів при першому запиті."""
    with qtbot.wait_signal(client_instance.request_finished, timeout=3000) as blocker:
        client_instance.request_db_classes()

    response = blocker.args[0]
    assert response.operation == DbOperation.GET_CLASSES
    assert response.status == StatusCode.OK
    assert isinstance(response.data["classes"], list)
    assert len(response.data["classes"]) == 0


def test_integration_db_add_and_list_class(client_instance, qtbot) -> None:
    """Перевірка циклу додавання нового класу об'єктів та його верифікація."""
    new_class = ObjectClass(id=None, name="IntegrationTest")

    # Створення нового класу в БД
    with qtbot.wait_signal(client_instance.request_finished, timeout=3000) as blocker:
        client_instance.request_db_add_class(new_class)

    add_resp = blocker.args[0]
    assert add_resp.status == StatusCode.CREATED
    assert add_resp.data["name"] == "IntegrationTest"
    class_id = add_resp.data["id"]

    # Перевірка збереження у списку
    with qtbot.wait_signal(client_instance.request_finished, timeout=3000) as blocker:
        client_instance.request_db_classes()

    list_resp = blocker.args[0]
    classes = list_resp.data["classes"]
    assert any(
        c["id"] == class_id and c["name"] == "IntegrationTest" for c in classes
    ), "Доданий клас повинен бути присутнім у списку"


def test_integration_server_events(server_instance, client_instance, qtbot) -> None:
    """Перевірка отримання подій детекції від сервера в реальному часі."""
    from app.models.detection_event import DetectionEvent
    from app.models.source_type import SourceType

    fake_event = DetectionEvent(
        id="test_event",
        type=SourceType.RF,
        name="UAV Detected",
        object_class="mavic_3",
        confidence=0.95,
        timestamp="2020-01-01T10:00:00",
        distance_km=1.2,
        angle=45.0,
        frequency_hz=2400000000,
    )

    # Очікуємо сигнал про отримання події
    with qtbot.wait_signal(client_instance.detection_received, timeout=3000) as blocker:
        server_instance.send_detection_event(fake_event)

    received_event = blocker.args[0]
    assert received_event.name == "UAV Detected"
    assert received_event.distance_km == 1.2


def test_integration_db_object_crud_cycle(client_instance, qtbot) -> None:
    """Перевірка повного CRUD-циклу для об'єктів детекції."""
    # Підготовка: додаємо клас
    with qtbot.wait_signal(client_instance.request_finished):
        client_instance.request_db_add_class(ObjectClass(id=None, name="CRUD_Test"))
    class_id = 1

    from app.models.detection_object import DetectionObject

    obj = DetectionObject(
        id=None, name="Initial Name", class_id=class_id, object_class="CRUD_Test"
    )

    # CREATE
    with qtbot.wait_signal(client_instance.request_finished) as blocker:
        client_instance.request_db_add_object(obj)
    obj_id = blocker.args[0].data["id"]

    # UPDATE
    updated_obj = DetectionObject(
        id=obj_id, name="Updated Name", class_id=class_id, object_class="CRUD_Test"
    )
    with qtbot.wait_signal(client_instance.request_finished) as blocker:
        client_instance.request_db_update_object(updated_obj)
    assert blocker.args[0].status == StatusCode.OK
    assert blocker.args[0].data["name"] == "Updated Name"

    # DELETE
    with qtbot.wait_signal(client_instance.request_finished) as blocker:
        client_instance.request_db_delete_object(obj_id)
    assert blocker.args[0].status == StatusCode.OK
    assert blocker.args[0].data["id"] == obj_id


def test_integration_db_pagination(client_instance, qtbot) -> None:
    """Перевірка коректності роботи пагінації об'єктів."""
    with qtbot.wait_signal(client_instance.request_finished):
        client_instance.request_db_add_class(ObjectClass(id=None, name="PageTest"))

    from app.models.detection_object import DetectionObject

    # Наповнення тестовими даними
    for i in range(3):
        with qtbot.wait_signal(client_instance.request_finished):
            client_instance.request_db_add_object(
                DetectionObject(
                    id=None, name=f"Obj{i}", class_id=1, object_class="PageTest"
                )
            )

    # Запит першої сторінки
    with qtbot.wait_signal(client_instance.request_finished) as blocker:
        client_instance.request_db_objects_page(page=1, page_size=2)

    resp = blocker.args[0]
    assert len(resp.data["items"]) == 2
    assert resp.data["total"] == 3


def test_integration_db_class_rename(client_instance, qtbot) -> None:
    """Перевірка операції перейменування класу об'єктів."""
    with qtbot.wait_signal(client_instance.request_finished):
        client_instance.request_db_add_class(ObjectClass(id=None, name="OldName"))

    old_cls = ObjectClass(id=1, name="OldName")
    new_cls = ObjectClass(id=1, name="NewName")

    # Запит на зміну метаданих
    with qtbot.wait_signal(client_instance.request_finished) as blocker:
        client_instance.request_db_rename_class(old_cls, new_cls)

    assert blocker.args[0].status == StatusCode.OK
    assert blocker.args[0].data["name"] == "NewName"


def test_integration_telemetry_gps(server_instance, client_instance, qtbot) -> None:
    """Перевірка передачі та обробки телеметрії GPS."""
    from app.models.gps_data import GPSData

    fake_gps = GPSData(lat=50.45, lon=30.52, strength=85)

    with qtbot.wait_signal(client_instance.gps_received, timeout=3000) as blocker:
        server_instance.send_gps_data(fake_gps)

    received_gps = blocker.args[0]
    assert received_gps.lat == 50.45
    assert received_gps.lon == 30.52
    assert received_gps.strength == 85


def test_integration_hardware_commands(server_instance, client_instance, qtbot) -> None:
    """Перевірка проходження апаратних команд від клієнта до сервера."""
    from unittest.mock import MagicMock

    # Перехоплення викликів до драйверів
    mock_handler = MagicMock()
    server_instance._handle_hardware_command = mock_handler

    # 1. Активація Alarm
    client_instance.request_alarm_start(["relay1", "relay2"])

    qtbot.wait_until(lambda: mock_handler.called, timeout=2000)
    assert mock_handler.called

    args = mock_handler.call_args
    assert args[0][0] == "start_alarm"
    assert args[0][1]["relays"] == ["relay1", "relay2"]

    mock_handler.reset_mock()

    # 2. Помилкова детекція (False Alarm)
    client_instance.report_false_alarm("event_123")
    qtbot.wait_until(lambda: mock_handler.called, timeout=2000)
    assert mock_handler.called
    assert mock_handler.call_args[0][0] == "false_alarm"
    assert mock_handler.call_args[0][1]["event_id"] == "event_123"

    mock_handler.reset_mock()

    # 3. Налаштування діапазону частот SDR
    client_instance.set_rf_range([900, 930])
    qtbot.wait_until(lambda: mock_handler.called, timeout=2000)
    assert mock_handler.called
    assert mock_handler.call_args[0][0] == "set_rf_range"
    assert mock_handler.call_args[0][1]["range"] == [900, 930]


def test_integration_gps_request_cycle(server_instance, client_instance, qtbot) -> None:
    """Перевірка циклу запиту GPS-координат (Клієнт -> Сервер)."""
    from unittest.mock import MagicMock

    mock_handler = MagicMock()
    server_instance._handle_hardware_command = mock_handler

    client_instance.request_remote_gps()

    qtbot.wait_until(lambda: mock_handler.called, timeout=2000)
    assert mock_handler.called
    assert mock_handler.call_args[0][0] == "get_gps"
