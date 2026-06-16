import json
from datetime import datetime
from typing import Any, Dict, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtNetwork import QTcpServer, QTcpSocket

from app.core.logging_config import get_logger
from app.models.detection_background import DetectionBackground
from app.models.detection_event import DetectionEvent
from app.models.detection_object import DetectionObject
from app.models.gps_data import GPSData
from app.models.object_class import ObjectClass
from app.models.service_response import ServiceResponse
from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk
from app.protocols import NetworkServiceSettings

logger = get_logger(__name__)


class PiNetworkService(QObject):
    """
    # PiNetworkService

    Сервіс мережевої взаємодії з Raspberry Pi (Ethernet/TCP).

    Забезпечує:
    - Підтримку з'єднання в реальному часі.
    - Обмін JSON-пакетами (команди, телеметрія, потоки).
    - Проксування запитів до бази даних на стороні Pi.
    """

    data_received = pyqtSignal(dict)
    gps_received = pyqtSignal(GPSData)
    detection_received = pyqtSignal(DetectionEvent)
    background_received = pyqtSignal(DetectionBackground)

    # --- Сигнали для потокових даних ---
    rf_data_received = pyqtSignal(StreamDataChunk)
    sound_data_received = pyqtSignal(StreamDataChunk)

    # --- Сигнал для роботи з БД ---
    request_finished = pyqtSignal(ServiceResponse)

    # --- Сигнали стану з'єднання ---
    connection_status_changed = pyqtSignal(bool)

    def __init__(
        self, settings: NetworkServiceSettings, parent: Optional[QObject] = None
    ) -> None:
        """Ініціалізує мережевий сервіс."""
        super().__init__(parent)
        self.settings = settings
        self.socket: Optional[QTcpSocket] = None
        self.server: Optional[QTcpServer] = None

        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self._try_connect)

    def start(self) -> None:
        self._try_connect()

    def stop(self) -> None:
        self.reconnect_timer.stop()
        if self.socket:
            self.socket.close()

    @pyqtSlot()
    def _try_connect(self) -> None:
        """Намагається встановити TCP-з'єднання з сервером."""
        if self.socket:
            state = self.socket.state()
            if (
                state == QTcpSocket.SocketState.ConnectedState
                or state == QTcpSocket.SocketState.ConnectingState
            ):
                return

            self.socket.close()
            self.socket.deleteLater()
            self.socket = None

        self.socket = QTcpSocket(self)
        self.socket.connected.connect(self._handle_connected)
        self.socket.disconnected.connect(self._handle_disconnected)
        self.socket.readyRead.connect(self._read_data)
        self.socket.errorOccurred.connect(self._handle_error)

        ip = self.settings.pi_target_ip
        port = self.settings.pi_target_port

        logger.info(f"Connecting to {ip}:{port}...")
        self.socket.connectToHost(ip, port)

    @pyqtSlot()
    def _handle_connected(self) -> None:
        logger.info("Connected to server!")
        self.reconnect_timer.stop()
        self.connection_status_changed.emit(True)

    @pyqtSlot()
    def _handle_disconnected(self) -> None:
        logger.info("Disconnected.")
        self.connection_status_changed.emit(False)
        self.socket = None

        logger.info("Will try to reconnect in 5s...")
        self.reconnect_timer.start(5000)

    @pyqtSlot()
    def _handle_error(self) -> None:
        if self.socket:
            logger.error(f"Socket Error: {self.socket.errorString()}")
        self.connection_status_changed.emit(False)
        self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Планує швидке перепідключення після помилки (3с)."""
        sock = self.socket
        if sock:
            self.socket = None
            sock.abort()
            sock.deleteLater()

        if not self.reconnect_timer.isActive():
            logger.info("Scheduling reconnect in 3s...")
            self.reconnect_timer.setSingleShot(True)
            self.reconnect_timer.start(3000)

    @pyqtSlot()
    def _read_data(self) -> None:
        """Читає та десеріалізує JSON-пакети з сокета."""
        if not self.socket:
            return

        while self.socket.canReadLine():
            line = self.socket.readLine().trimmed()
            try:
                json_str = line.data().decode("utf-8")
                if not json_str:
                    continue

                packet = json.loads(json_str)
                action = packet.get("action")
                data = packet.get("data", {})

                if action == "detection":
                    self.detection_received.emit(DetectionEvent.from_dict(data))
                elif action == "detection_background":
                    self.background_received.emit(DetectionBackground.from_dict(data))
                elif action == "gps_position":
                    self.gps_received.emit(GPSData.from_dict(data))
                elif action == "rf_stream":
                    self.rf_data_received.emit(
                        StreamDataChunk.from_dict(data, SourceType.RF)
                    )
                elif action == "sound_stream":
                    self.sound_data_received.emit(
                        StreamDataChunk.from_dict(data, SourceType.SOUND)
                    )
                elif action == "db_operation_result":
                    response_obj = ServiceResponse.from_dict(data)
                    self.request_finished.emit(response_obj)
                    logger.debug(
                        f"DB Op '{response_obj.operation}' status: {response_obj.status.value}"
                    )
                else:
                    self.data_received.emit(packet)

            except json.JSONDecodeError:
                logger.error(f"JSON Decode Error: {line}")
            except Exception as e:
                logger.error(f"Read Error: {e}")

    def send_packet(self, action: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Відправляє JSON-пакет на сервер."""
        if self.socket and self.socket.state() == QTcpSocket.SocketState.ConnectedState:
            payload = {
                "action": action,
                "data": data if data else {},
                "timestamp": datetime.now().isoformat(),
            }
            try:
                msg = (json.dumps(payload) + "\n").encode("utf-8")
                self.socket.write(msg)
                self.socket.flush()
            except Exception as e:
                logger.error(f"Send Error: {e}")
        else:
            logger.warning("Cannot send packet: No connection.")

    # --- PUBLIC API METHODS ---

    def request_remote_gps(self) -> None:
        logger.debug("Requesting GPS...")
        self.send_packet("get_gps")

    def request_rf_data_start(self) -> None:
        logger.debug("Starting RF stream...")
        self.send_packet("start_rf_stream")

    def request_rf_data_end(self) -> None:
        logger.debug("Stopping RF stream...")
        self.send_packet("stop_rf_stream")

    def request_sound_data_start(self) -> None:
        logger.debug("Starting Sound stream...")
        self.send_packet("start_sound_stream")

    def request_sound_data_end(self) -> None:
        logger.debug("Stopping Sound stream...")
        self.send_packet("stop_sound_stream")

    def report_false_alarm(self, event_id: str) -> None:
        """Повідомляє сервер про помилкове спрацювання детекції."""
        logger.debug(f"Reporting false alarm: {event_id}")
        self.send_packet("false_alarm", {"event_id": event_id})

    def request_alarm_start(self, relays: list[str]) -> None:
        """Запускає роботу апаратних реле (Jammer)."""
        logger.debug(f"Starting relays: {relays}")
        self.send_packet("start_alarm", {"relays": relays})

    def request_alarm_stop(self) -> None:
        logger.debug("Stopping relays...")
        self.send_packet("stop_alarm")

    def set_rf_range(self, rf_range: list[int]) -> None:
        """Встановлює робочий діапазон частот для SDR."""
        logger.debug(f"Setting RF range: {rf_range}")
        self.send_packet("set_rf_range", {"range": rf_range})

    # --- DATABASE PROXY METHODS ---

    def request_db_objects_page(self, page: int, page_size: int) -> None:
        """Запитує сторінку сигнатур об'єктів з БД."""
        logger.debug(f"DB Request: Objects Page {page}")
        self.send_packet("db_request_page", {"page": page, "size": page_size})

    def request_db_add_object(self, obj_data: DetectionObject) -> None:
        """Запит на додавання нової сигнатури об'єкта."""
        logger.debug(f"DB Request: Add Object '{obj_data.name}'")
        self.send_packet("db_request_add", {"object": obj_data.to_dict()})

    def request_db_update_object(self, obj_data: DetectionObject) -> None:
        """Запит на оновлення існуючої сигнатури."""
        logger.debug(f"DB Request: Update Object ID {obj_data.id}")
        self.send_packet("db_request_update", {"object": obj_data.to_dict()})

    def request_db_delete_object(self, object_id: int) -> None:
        """Запит на видалення сигнатури."""
        logger.debug(f"DB Request: Delete Object ID {object_id}")
        self.send_packet("db_request_delete", {"id": object_id})

    def request_db_classes(self) -> None:
        logger.debug("DB Request: Get All Classes")
        self.send_packet("db_request_classes")

    def request_db_add_class(self, class_obj: ObjectClass) -> None:
        """Запит на додавання нового класу об'єктів."""
        logger.debug(f"DB Request: Add Class '{class_obj.name}'")
        self.send_packet("db_request_add_class", {"class": class_obj.to_dict()})

    def request_db_rename_class(
        self, old_class_obj: ObjectClass, new_class_obj: ObjectClass
    ) -> None:
        """Запит на перейменування класу."""
        logger.debug(f"DB Request: Rename Class '{old_class_obj.name}'")
        self.send_packet(
            "db_request_rename_class",
            {
                "old_class": old_class_obj.to_dict(),
                "new_class": new_class_obj.to_dict(),
            },
        )

    def request_db_delete_class(self, class_id: int) -> None:
        """Запит на видалення класу."""
        logger.debug(f"DB Request: Delete Class ID {class_id}")
        self.send_packet("db_request_delete_class", {"id": class_id})
