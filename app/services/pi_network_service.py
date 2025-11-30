"""
Сервіс мережевої взаємодії (Raspberry Pi).
Відповідає за встановлення та підтримку з'єднання між пристроями (через Ethernet), передачу пакетів даних тощо.
"""

import json
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QByteArray, QTimer
from PyQt6.QtNetwork import QTcpServer, QTcpSocket, QHostAddress
from app.services.settings_service import SettingsService


class PiNetworkService(QObject):
    """
    Сервіс для TCP-зв'язку між двома Raspberry Pi.
    Може працювати в режимі Сервера (приймає дані) або Клієнта (надсилає дані).
    """

    data_received = pyqtSignal(dict)  # Сигнал з отриманими даними (розпарсений JSON)
    connection_status_changed = pyqtSignal(bool)  # Сигнал про статус з'єднання

    def __init__(self, settings: SettingsService, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.socket = None
        self.server = None
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self._try_connect)

    def start(self):
        """Запускає сервіс в залежності від ролі в налаштуваннях."""
        if self.settings.pi_is_receiver:
            self._start_server()
        else:
            self._start_client()

    def stop(self):
        """Зупиняє сервіс."""
        self.reconnect_timer.stop()
        if self.server:
            self.server.close()
        if self.socket:
            self.socket.close()

    # --- SERVER MODE (Receiver Pi) ---
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
        if self.socket:  # Якщо вже є з'єднання, закриваємо старе (один клієнт)
            self.socket.close()

        self.socket = self.server.nextPendingConnection()
        print(f"[PiNet] Клієнт під'єднався: {self.socket.peerAddress().toString()}")
        self.connection_status_changed.emit(True)

        self.socket.readyRead.connect(self._read_data)
        self.socket.disconnected.connect(self._handle_disconnected)
        # Важливо: при видаленні сокета чистимо посилання
        self.socket.destroyed.connect(lambda: setattr(self, "socket", None))

    # --- CLIENT MODE (Sender Pi) ---
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

        # Якщо не вдалося підключитися за 3 секунди - спробуємо пізніше
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
            # Клієнт пробує перепідключитися кожні 5 секунд
            self.reconnect_timer.start(5000)

    # --- COMMON I/O ---
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
                data = json.loads(json_str)
                # print(f"[PiNet] Отримано: {data}") # Розкоментуйте для дебагу
                self.data_received.emit(data)
            except json.JSONDecodeError:
                print(f"[PiNet] Помилка JSON: {line}")
            except Exception as e:
                print(f"[PiNet] Помилка читання: {e}")

    def send_data(self, data: dict):
        """Відправляє словник як JSON-рядок з \n в кінці."""
        if self.socket and self.socket.state() == QTcpSocket.SocketState.ConnectedState:
            try:
                msg = (json.dumps(data) + "\n").encode("utf-8")
                self.socket.write(QByteArray(msg))
                self.socket.flush()  # Гарантуємо відправку
            except Exception as e:
                print(f"[PiNet] Помилка відправки: {e}")
        else:
            print("[PiNet] Немає з'єднання для відправки даних.")
