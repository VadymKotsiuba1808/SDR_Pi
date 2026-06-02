import json
from datetime import datetime
from typing import Any, Dict, Optional

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtNetwork import QHostAddress, QTcpServer, QTcpSocket

from app.core.logging_config import get_logger
from app.models.detection_background import DetectionBackground
from app.models.detection_event import DetectionEvent
from app.models.detection_object import DetectionObject
from app.models.gps_data import GPSData
from app.models.object_class import ObjectClass
from app.models.service_response import ServiceResponse, StatusCode
from pi_server.database_service import DatabaseService

logger = get_logger(__name__)


class PiServerService(QObject):
    """Сервіс-сервер для Raspberry Pi.

    Цей клас реалізує TCP-сервер, який працює на Raspberry Pi. Він приймає підключення
    від Desktop-клієнта, обробляє вхідні JSON-команди для керування периферією
    (SDR, GPS, GPIO) та взаємодіє з локальною базою даних через DatabaseService.
    """

    def __init__(
        self,
        port: int = 6000,
        db_service: Optional[DatabaseService] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.port = port
        self.server: Optional[QTcpServer] = None
        self.client_socket: Optional[QTcpSocket] = None

        self.db = db_service or DatabaseService()
        self.db.request_finished.connect(self.send_db_response)

    def start(self) -> None:
        """Запускає TCP-сервер на вказаному порту."""
        self.server = QTcpServer(self)
        self.server.newConnection.connect(self._handle_new_connection)

        if self.server.listen(QHostAddress.SpecialAddress.Any, self.port):
            logger.info(f"Server listening on port {self.port}")
        else:
            logger.error(f"Error starting server: {self.server.errorString()}")

    def stop(self) -> None:
        """Зупиняє сервер та розриває активні з'єднання."""
        if self.client_socket:
            self.client_socket.disconnectFromHost()

            # Чекаємо розриву з'єднання (макс. 1 сек), щоб уникнути "завислих" сокетів
            if (
                self.client_socket
                and self.client_socket.state()
                != QTcpSocket.SocketState.UnconnectedState
            ):
                self.client_socket.waitForDisconnected(1000)

        if self.server:
            self.server.close()

        logger.info("Server stopped.")

    @pyqtSlot()
    def _handle_new_connection(self) -> None:
        """Обробляє нове вхідне підключення."""
        if self.server is None:
            return

        # Система підтримує лише одного активного клієнта одночасно
        # Якщо підключається новий клієнт, старе з'єднання примусово закривається
        if self.client_socket:
            peer_address = self.client_socket.peerAddress()
            addr_str = peer_address.toString() if peer_address else "Unknown"
            logger.info(f"Closing old connection from {addr_str}")
            self.client_socket.close()
            self.client_socket.deleteLater()

        self.client_socket = self.server.nextPendingConnection()
        if self.client_socket is None:
            return

        peer_address = self.client_socket.peerAddress()
        addr_str = peer_address.toString() if peer_address else "Unknown"
        logger.info(f"Client connected: {addr_str}")

        self.client_socket.readyRead.connect(self._read_data)
        self.client_socket.disconnected.connect(self._handle_disconnected)

    @pyqtSlot()
    def _handle_disconnected(self) -> None:
        logger.info("Client disconnected.")
        self.client_socket = None

    @pyqtSlot()
    def _read_data(self) -> None:
        """Читає та парсить вхідні дані з сокета."""
        if not self.client_socket:
            return

        while self.client_socket.canReadLine():
            line = self.client_socket.readLine().trimmed()
            try:
                json_str = line.data().decode("utf-8")
                if not json_str:
                    continue

                packet = json.loads(json_str)
                action = packet.get("action")
                data = packet.get("data", {})

                logger.debug(f"Received action: {action}")
                self._process_command(action, data)

            except json.JSONDecodeError:
                logger.error(f"JSON Error: {line}")
            except Exception as e:
                logger.error(f"Processing Error: {e}")

    def _process_command(self, action: str, data: Dict[str, Any]) -> None:
        """Головний маршрутизатор команд від клієнта."""
        if action.startswith("db_"):
            self._handle_db_command(action, data)
        else:
            self._handle_hardware_command(action, data)

    def _handle_hardware_command(self, action: str, data: Dict[str, Any]) -> None:
        """Обробка команд, пов'язаних з сенсорами та апаратним забезпеченням."""
        if action == "get_gps":
            # TODO: Реалізувати отримання реальних даних з GPS-модуля
            pass

        elif action == "start_rf_stream":
            # TODO: Запустити процес зчитування спектру з Pluto SDR
            pass

        elif action == "stop_rf_stream":
            pass

        elif action == "start_sound_stream":
            # TODO: Запустити процес захоплення аудіо для аналізу
            pass

        elif action == "stop_sound_stream":
            pass

        elif action == "start_alarm":
            relays = data.get("relays", [])
            logger.info(f"Activating relays: {relays}")
            # TODO: Логіка керування GPIO (реле тривоги)

        elif action == "stop_alarm":
            logger.info("Deactivating relays")

        elif action == "false_alarm":
            event_id = data.get("event_id")
            logger.info(f"Marking event {event_id} as false alarm")
            # TODO: Логування хибної тривоги та можливе донавчання моделі

        elif action == "set_rf_range":
            r_range = data.get("range", [])
            logger.info(f"Set follow rf range {r_range}")
            # TODO: Встановлення діапазону сканування для SDR (в МГц)

        else:
            logger.warning(f"Unknown hardware command: {action}")

    def _handle_db_command(self, action: str, data: Dict[str, Any]) -> None:
        """Обробка CRUD операцій та запитів до бази даних."""
        try:
            if action == "db_request_page":
                page = data.get("page", 1)
                size = data.get("size", 15)
                self.db.request_objects_page(page, size)

            elif action == "db_request_add":
                raw_obj = data.get("object")
                if raw_obj:
                    new_object_model = DetectionObject.from_dict(raw_obj)
                    logger.info(f"Adding object: {new_object_model.name}")
                    self.db.add_object(new_object_model)
                else:
                    raise ValueError("Missing 'object' data")

            elif action == "db_request_update":
                raw_obj = data.get("object")
                if raw_obj:
                    updated_object_model = DetectionObject.from_dict(raw_obj)
                    logger.info(f"Updating object ID: {updated_object_model.id}")
                    self.db.update_object(updated_object_model)
                else:
                    raise ValueError("Missing 'object' data")

            elif action == "db_request_delete":
                obj_id = data.get("id")
                if obj_id:
                    logger.info(f"Deleting object ID: {obj_id}")
                    self.db.delete_object(obj_id)
                else:
                    raise ValueError("Missing 'id'")

            elif action == "db_request_classes":
                self.db.request_classes()

            elif action == "db_request_add_class":
                class_dict = data.get("class")
                if class_dict:
                    new_class = ObjectClass.from_dict(class_dict)
                    self.db.add_class(new_class)
                else:
                    raise ValueError("Missing 'class' data")

            elif action == "db_request_rename_class":
                old_cls_dict = data.get("old_class")
                new_cls_dict = data.get("new_class")

                if old_cls_dict and new_cls_dict:
                    cls_id = old_cls_dict.get("id")
                    new_name = new_cls_dict.get("name")
                    if cls_id and new_name:
                        # Створюємо DTO з ID і новим ім'ям для апдейту
                        cls_model = ObjectClass(id=cls_id, name=new_name)
                        self.db.update_class(cls_model)
                    else:
                        logger.error("Rename Class Error: Invalid Data")
                        raise ValueError("Invalid ID or Name")
                else:
                    logger.error("Rename Class Error: Missing old/new class data")
                    raise ValueError("Missing old/new class data")

            elif action == "db_request_delete_class":
                class_id = data.get("id")
                if class_id:
                    self.db.delete_class(class_id)
                else:
                    raise ValueError("Missing 'id'")

            else:
                logger.warning(f"Unknown DB command: {action}")
                self._send_protocol_error(action, "Unknown command")

        except Exception as e:
            logger.error(f"DB Logic Error: {e}")
            self._send_protocol_error(action, str(e))

    def _send_protocol_error(self, operation: str, error_msg: str) -> None:
        """Відправляє повідомлення про помилку протоколу або валідації."""
        response = ServiceResponse(
            operation=operation,
            status=StatusCode.BAD_REQUEST,
            message=f"Protocol/Validation Error: {error_msg}",
        )
        self.send_db_response(response)

    def send_packet(self, action: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Відправляє структурований JSON-пакет клієнту."""
        if (
            self.client_socket
            and self.client_socket.state() == QTcpSocket.SocketState.ConnectedState
        ):
            payload = {
                "action": action,
                "data": data if data else {},
                "timestamp": datetime.now().isoformat(),
            }
            try:
                msg = (json.dumps(payload) + "\n").encode("utf-8")
                self.client_socket.write(msg)
                self.client_socket.flush()
            except Exception as e:
                logger.error(f"Send Error: {e}")

    def send_detection_event(self, event: DetectionEvent) -> None:
        logger.info(f"Sending Detection: {event.name}")
        self.send_packet("detection", event.to_dict())

    def send_detection_background(self, back: DetectionBackground) -> None:
        logger.debug("Sending Detection background")
        self.send_packet("detection_background", back.to_dict())

    def send_gps_data(self, gps_data: GPSData) -> None:
        self.send_packet("gps_position", gps_data.to_dict())

    def send_rf_stream_data(self, spectrum_data: Dict[str, Any]) -> None:
        """Відправляє пакет сирих даних спектру для візуалізації."""
        self.send_packet("rf_stream", spectrum_data)

    def send_sound_stream_data(self, audio_analysis: Dict[str, Any]) -> None:
        """Відправляє результат акустичного аналізу."""
        self.send_packet("sound_stream", audio_analysis)

    @pyqtSlot(object)
    def send_db_response(self, response: ServiceResponse) -> None:
        logger.debug(f"DB Response: {response.operation} -> {response.status}")
        packet_data = response.to_dict()
        self.send_packet("db_operation_result", packet_data)
