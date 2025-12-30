import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QByteArray, QTimer
from PyQt6.QtNetwork import QTcpServer, QTcpSocket, QHostAddress

from app.services.settings_service import SettingsService
from app.models.detection_event import DetectionEvent


class PiNetworkService(QObject):
    """
    Сервіс мережевої взаємодії (Raspberry Pi).
    Відповідає за встановлення та підтримку з'єднання між пристроями (через Ethernet),
    передачу пакетів даних та проксування запитів до БД.
    """

    data_received = pyqtSignal(dict)  # Сирі дані (якщо не розпізнано)
    gps_received = pyqtSignal(dict)  # GPS координати {lat, lon, alt}
    detection_received = pyqtSignal(DetectionEvent)  # Об'єкт детекції

    # --- Сигнали для потокових даних ---
    rf_data_received = pyqtSignal(dict)
    sound_data_received = pyqtSignal(dict)

    # --- Сигнали для роботи з БД  ---
    # (objects_list, page, total_items)
    db_objects_page_received = pyqtSignal(list, int, int)

    # (operation_type, success, message)
    db_operation_status = pyqtSignal(str, bool, str)

    # (classes_list)
    db_classes_received = pyqtSignal(list)

    # --- Сигнали стану з'єднання ---
    connection_status_changed = pyqtSignal(bool)

    def __init__(
        self, settings: SettingsService, parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.socket: Optional[QTcpSocket] = None
        self.server: Optional[QTcpServer] = None

        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self._try_connect)

    def start(self) -> None:
        if self.settings.pi_is_receiver:
            self._start_server()
        else:
            self._start_client()

    def stop(self) -> None:
        self.reconnect_timer.stop()
        if self.server:
            self.server.close()
        if self.socket:
            self.socket.close()

    def _start_server(self) -> None:
        self.server = QTcpServer(self)
        self.server.newConnection.connect(self._handle_new_connection)
        port = self.settings.pi_target_port

        if self.server.listen(QHostAddress.SpecialAddress.Any, port):
            print(f"[PiNet] Server listening on port {port}")
        else:
            print(f"[PiNet] Server start error: {self.server.errorString()}")

    @pyqtSlot()
    def _handle_new_connection(self) -> None:
        if self.socket:
            self.socket.close()

        self.socket = self.server.nextPendingConnection()
        print(f"[PiNet] Client connected: {self.socket.peerAddress().toString()}")

        self.connection_status_changed.emit(True)
        self.socket.readyRead.connect(self._read_data)
        self.socket.disconnected.connect(self._handle_disconnected)

    def _start_client(self) -> None:
        self._try_connect()

    @pyqtSlot()
    def _try_connect(self) -> None:
        if self.socket and self.socket.state() == QTcpSocket.SocketState.ConnectedState:
            return

        self.socket = QTcpSocket(self)
        self.socket.connected.connect(self._handle_connected)
        self.socket.disconnected.connect(self._handle_disconnected)
        self.socket.readyRead.connect(self._read_data)

        ip = self.settings.pi_target_ip
        port = self.settings.pi_target_port

        print(f"[PiNet] Connecting to {ip}:{port}...")
        self.socket.connectToHost(ip, port)

        if not self.socket.waitForConnected(3000):
            pass

    @pyqtSlot()
    def _handle_connected(self) -> None:
        print("[PiNet] Connected to server!")
        self.reconnect_timer.stop()
        self.connection_status_changed.emit(True)

    @pyqtSlot()
    def _handle_disconnected(self) -> None:
        print("[PiNet] Disconnected.")
        self.connection_status_changed.emit(False)
        self.socket = None

        if not self.settings.pi_is_receiver:
            print("[PiNet] Will try to reconnect in 5s...")
            self.reconnect_timer.start(5000)

    @pyqtSlot()
    def _read_data(self) -> None:
        if not self.socket:
            return

        while self.socket.canReadLine():
            line = self.socket.readLine().trimmed()
            try:
                json_str = bytes(line).decode("utf-8")
                if not json_str:
                    continue

                packet = json.loads(json_str)
                action = packet.get("action")
                data = packet.get("data", {})

                if action == "detection":
                    event_obj = DetectionEvent.from_dict(data)
                    self.detection_received.emit(event_obj)

                elif action == "gps_position":
                    self.gps_received.emit(data)

                elif action == "rf_stream":
                    self.rf_data_received.emit(data)

                elif action == "sound_stream":
                    self.sound_data_received.emit(data)

                elif action == "db_response_page":
                    items_raw = data.get("items", [])
                    page = data.get("page", 1)
                    total = data.get("total", 0)

                    # models = [DetectionObject.from_dict(d) for d in items_raw]
                    # self.db_objects_page_received.emit(models, page, total)

                elif action == "db_response_status":
                    op_type = data.get("op", "unknown")
                    success = data.get("success", False)
                    msg = data.get("msg", "")
                    self.db_operation_status.emit(op_type, success, msg)

                elif action == "db_response_classes":
                    classes_raw = data.get("classes", [])
                    # models = [ObjectClass.from_dict(c) for c in classes_raw]
                    # self.db_classes_received.emit(models)

                else:
                    # Fallback для невідомих пакетів
                    self.data_received.emit(packet)

            except json.JSONDecodeError:
                print(f"[PiNet] JSON Error: {line}")
            except Exception as e:
                print(f"[PiNet] Read Error: {e}")

    def send_packet(self, action: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Універсальний метод відправки пакету."""
        if self.socket and self.socket.state() == QTcpSocket.SocketState.ConnectedState:
            payload = {
                "action": action,
                "data": data if data else {},
                "timestamp": datetime.now().isoformat(),
            }
            try:
                msg = (json.dumps(payload) + "\n").encode("utf-8")
                self.socket.write(QByteArray(msg))
                self.socket.flush()
            except Exception as e:
                print(f"[PiNet] Send Error: {e}")
        else:
            print("[PiNet] Cannot send packet: No connection.")

    # --- PUBLIC API METHODS ---

    def request_remote_gps(self) -> None:
        print("[PiNet] Requesting GPS...")
        self.send_packet("get_gps")

    def request_rf_data_start(self) -> None:
        print("[PiNet] Starting RF stream...")
        self.send_packet("start_rf_stream")

    def request_rf_data_end(self) -> None:
        print("[PiNet] Stopping RF stream...")
        self.send_packet("stop_rf_stream")

    def request_sound_data_start(self) -> None:
        print("[PiNet] Starting Sound stream...")
        self.send_packet("start_sound_stream")

    def request_sound_data_end(self) -> None:
        print("[PiNet] Stopping Sound stream...")
        self.send_packet("stop_sound_stream")

    def report_false_alarm(self, event_id: str) -> None:
        print(f"[PiNet] Reporting false alarm: {event_id}")
        self.send_packet("false_alarm", {"event_id": event_id})

    def request_alarm_start(self, relays: list[str]) -> None:
        print("[PiNet] Starting relays working...")
        self.send_packet("start_alarm", {"relays": relays})

    def request_alarm_stop(self) -> None:
        print("[PiNet] Stopping relays working...")
        self.send_packet("stop_alarm")

    def set_rf_range(self, rf_range: list[float]):
        print(f"[PiNet] Setting RF range: {rf_range}")
        self.send_packet("set_rf_range", {"range": rf_range})

    # --- DATABASE PROXY METHODS ---

    def request_db_objects_page(self, page: int, page_size: int) -> None:
        """Запит сторінки об'єктів з віддаленої БД."""
        print(f"[PiNet] DB Request: Objects Page {page}")
        self.send_packet("db_request_page", {"page": page, "size": page_size})

    def request_db_add_object(self, obj_data: Dict[str, Any]) -> None:
        print(f"[PiNet] DB Request: Add Object '{obj_data.get('name')}'")
        self.send_packet("db_request_add", {"object": obj_data})

    def request_db_update_object(self, obj_data: Dict[str, Any]) -> None:
        print(f"[PiNet] DB Request: Update Object ID {obj_data.get('id')}")
        self.send_packet("db_request_update", {"object": obj_data})

    def request_db_delete_object(self, object_id: int) -> None:
        print(f"[PiNet] DB Request: Delete Object ID {object_id}")
        self.send_packet("db_request_delete", {"id": object_id})

    def request_db_classes(self) -> None:
        print("[PiNet] DB Request: Get All Classes")
        self.send_packet("db_request_classes")

    def request_db_add_class(self, class_name: str) -> None:
        print(f"[PiNet] DB Request: Add Class '{class_name}'")
        self.send_packet("db_request_add_class", {"name": class_name})

    def request_db_rename_class(self, old_name: str, new_name: str) -> None:
        print(f"[PiNet] DB Request: Rename Class '{old_name}' -> '{new_name}'")
        self.send_packet("db_request_rename_class", {"old": old_name, "new": new_name})

    def request_db_delete_class(self, class_id: int) -> None:
        print(f"[PiNet] DB Request: Delete Class ID {class_id}")
        self.send_packet("db_request_delete_class", {"id": class_id})
