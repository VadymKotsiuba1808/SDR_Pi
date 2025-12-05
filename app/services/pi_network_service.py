"""
Сервіс мережевої взаємодії (Raspberry Pi).
Відповідає за встановлення та підтримку з'єднання між пристроями (через Ethernet), передачу пакетів даних тощо.
"""

import json
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QByteArray, QTimer
from PyQt6.QtNetwork import QTcpServer, QTcpSocket, QHostAddress
from app.services.settings_service import SettingsService
from app.models.detection_event import DetectionEvent


class PiNetworkService(QObject):

    # Сигнали
    data_received = pyqtSignal(dict)  # Сирі дані (якщо не розпізнано)
    gps_received = pyqtSignal(dict)  # GPS координати
    detection_received = pyqtSignal(DetectionEvent)  # Об'єкт детекції

    # Сигнали для потокових даних (поки зарезервовані)
    rf_data_received = pyqtSignal(dict)
    sound_data_received = pyqtSignal(dict)

    connection_status_changed = pyqtSignal(bool)

    def __init__(self, settings: SettingsService, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.socket = None
        self.server = None
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self._try_connect)

    def start(self):
        if self.settings.pi_is_receiver:
            self._start_server()
        else:
            self._start_client()

    def stop(self):
        self.reconnect_timer.stop()
        if self.server:
            self.server.close()
        if self.socket:
            self.socket.close()

    # --- SERVER MODE ---
    def _start_server(self):
        self.server = QTcpServer(self)
        self.server.newConnection.connect(self._handle_new_connection)
        port = self.settings.pi_target_port
        if self.server.listen(QHostAddress.SpecialAddress.Any, port):
            print(f"[PiNet] Сервер слухає на порту {port}")
        else:
            print(f"[PiNet] Помилка запуску сервера: {self.server.errorString()}")

    @pyqtSlot()
    def _handle_new_connection(self):
        if self.socket:
            self.socket.close()
        self.socket = self.server.nextPendingConnection()
        print(f"[PiNet] Клієнт під'єднався: {self.socket.peerAddress().toString()}")
        self.connection_status_changed.emit(True)
        self.socket.readyRead.connect(self._read_data)
        self.socket.disconnected.connect(self._handle_disconnected)
        self.socket.destroyed.connect(lambda: setattr(self, "socket", None))

    # --- CLIENT MODE ---
    def _start_client(self):
        self._try_connect()

    @pyqtSlot()
    def _try_connect(self):
        if self.socket and self.socket.state() == QTcpSocket.SocketState.ConnectedState:
            return
        self.socket = QTcpSocket(self)
        self.socket.connected.connect(self._handle_connected)
        self.socket.disconnected.connect(self._handle_disconnected)
        self.socket.readyRead.connect(self._read_data)

        ip = self.settings.pi_target_ip
        port = self.settings.pi_target_port
        print(f"[PiNet] Спроба підключення до {ip}:{port}...")
        self.socket.connectToHost(ip, port)

        if not self.socket.waitForConnected(3000):
            self._handle_disconnected()

    @pyqtSlot()
    def _handle_connected(self):
        print("[PiNet] Підключено до сервера!")
        self.reconnect_timer.stop()
        self.connection_status_changed.emit(True)

    @pyqtSlot()
    def _handle_disconnected(self):
        print("[PiNet] З'єднання втрачено.")
        self.connection_status_changed.emit(False)
        if not self.settings.pi_is_receiver:
            self.reconnect_timer.start(5000)

    @pyqtSlot()
    def _read_data(self):
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

                elif action == "false_alarm_ack":
                    print(
                        f"[PiNet] Сервер підтвердив скасування тривоги: {data.get('event_id')}"
                    )

                else:
                    # Якщо прийшло щось нестандартне, віддаємо як є
                    self.data_received.emit(packet)

            except json.JSONDecodeError:
                print(f"[PiNet] Помилка JSON: {line}")
            except Exception as e:
                print(f"[PiNet] Помилка читання: {e}")

    def send_packet(self, action: str, data: dict = None):
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
                print(f"[PiNet] Помилка відправки: {e}")
        else:
            print("[PiNet] Немає з'єднання для відправки.")

    def request_remote_gps(self):
        print("[PiNet] Запит GPS...")
        self.send_packet("get_gps")

    def request_rf_data_start(self):
        print("[PiNet] Старт RF потоку...")
        self.send_packet("start_rf_stream")

    def request_rf_data_end(self):
        print("[PiNet] Стоп RF потоку...")
        self.send_packet("stop_rf_stream")

    def request_sound_data_start(self):
        print("[PiNet] Старт Sound потоку...")
        self.send_packet("start_sound_stream")

    def request_sound_data_end(self):
        print("[PiNet] Стоп Sound потоку...")
        self.send_packet("stop_sound_stream")

    def report_false_alarm(self, event_id):
        print(f"[PiNet] Звіт про хибну тривогу: {event_id}")
        self.send_packet("false_alarm", {"event_id": event_id})
