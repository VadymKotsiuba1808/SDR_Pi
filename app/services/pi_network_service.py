import json
from datetime import datetime
from typing import Any, Dict, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtNetwork import QTcpServer, QTcpSocket

from app.models.detection_background import DetectionBackground
from app.models.detection_event import DetectionEvent
from app.models.detection_object import DetectionObject
from app.models.gps_data import GPSData
from app.models.object_class import ObjectClass
from app.models.service_response import ServiceResponse
from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk
from app.protocols import NetworkServiceSettings


class PiNetworkService(QObject):
    """
    Сервіс мережевої взаємодії з Raspberry Pi.

    Відповідає за встановлення та підтримку з'єднання (Ethernet/TCP),
    обмін даними в реальному часі та проксування запитів до бази даних.
    Використовує асинхронні сигнали Qt для передачі отриманих даних іншим сервісам.

    Attributes:
        data_received (pyqtSignal): Сигнал з сирими даними (dict), якщо тип пакета не розпізнано.
        gps_received (pyqtSignal): Сигнал з об'єктом GPSData.
        detection_received (pyqtSignal): Сигнал з об'єктом DetectionEvent.
        background_received (pyqtSignal): Сигнал з об'єктом DetectionBackground (спектральний фон).
        rf_data_received (pyqtSignal): Сигнал з чанком StreamDataChunk для RF-даних.
        sound_data_received (pyqtSignal): Сигнал з чанком StreamDataChunk для звукових даних.
        request_finished (pyqtSignal): Сигнал про завершення запиту до БД з об'єктом ServiceResponse.
        connection_status_changed (pyqtSignal): Сигнал зміни статусу з'єднання (bool).
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
        """
        Ініціалізує мережевий сервіс.

        Args:
            settings (NetworkServiceSettings): Об'єкт налаштувань (IP, порт).
            parent (Optional[QObject], optional): Батьківський об'єкт Qt. Defaults to None.
        """
        super().__init__(parent)
        self.settings = settings
        self.socket: Optional[QTcpSocket] = None
        self.server: Optional[QTcpServer] = None

        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self._try_connect)

    def start(self) -> None:
        """
        Запускає процес підключення до сервера.

        Викликає початкову спробу підключення. Якщо сервер недоступний,
        подальші спроби будуть керуватися таймером реконнекту.
        """
        self._try_connect()

    def stop(self) -> None:
        """
        Зупиняє сервіс та розриває активне з'єднання.

        Зупиняє таймер повторного підключення та закриває сокет, якщо він відкритий.
        """
        self.reconnect_timer.stop()
        if self.socket:
            self.socket.close()

    @pyqtSlot()
    def _try_connect(self) -> None:
        """
        Намагається встановити TCP-з'єднання з сервером.

        !!! info "Чому це важливо"
            Логіка перевіряє поточний стан сокета, щоб уникнути створення декількох
            паралельних спроб з'єднання, що може призвести до витоку ресурсів
            або конфліктів у стані сервісу.
        """
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

        print(f"[PiNet] Connecting to {ip}:{port}...")
        self.socket.connectToHost(ip, port)

    @pyqtSlot()
    def _handle_connected(self) -> None:
        """Обробник успішного встановлення з'єднання."""
        print("[PiNet] Connected to server!")
        self.reconnect_timer.stop()
        self.connection_status_changed.emit(True)

    @pyqtSlot()
    def _handle_disconnected(self) -> None:
        """
        Обробник розриву з'єднання.

        Ініціює процес автоматичного перепідключення через 5 секунд.
        """
        print("[PiNet] Disconnected.")
        self.connection_status_changed.emit(False)
        self.socket = None

        print("[PiNet] Will try to reconnect in 5s...")
        self.reconnect_timer.start(5000)

    @pyqtSlot()
    def _handle_error(self) -> None:
        """Обробник помилок сокета."""
        if self.socket:
            print(f"[PiNet] Socket Error: {self.socket.errorString()}")
        self.connection_status_changed.emit(False)
        self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """
        Планує швидке перепідключення після помилки.

        !!! note "Логіка"
            Використовується коротший інтервал (3с) порівняно зі звичайним розривом,
            оскільки помилка часто свідчить про тимчасову проблему мережі.
        """
        sock = self.socket
        if sock:
            self.socket = None
            sock.abort()
            sock.deleteLater()

        if not self.reconnect_timer.isActive():
            print("[PiNet] Scheduling reconnect in 3s...")
            self.reconnect_timer.setSingleShot(True)
            self.reconnect_timer.start(3000)

    @pyqtSlot()
    def _read_data(self) -> None:
        """
        Читає та десеріалізує дані з сокета.

        Обробляє вхідні JSON-пакети рядок за рядком. Кожен пакет має містити
        поле `action` для визначення типу даних та `data` з корисним навантаженням.

        !!! warning "Обробка помилок"
            Помилки десеріалізації JSON або створення об'єктів моделей перехоплюються,
            щоб запобігти падінню всього сервісу при отриманні некоректних даних.
        """
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

                # --- Hardware / Stream Data ---
                if action == "detection":
                    event_obj = DetectionEvent.from_dict(data)
                    self.detection_received.emit(event_obj)
                elif action == "detection_background":
                    bg_obj = DetectionBackground.from_dict(data)
                    self.background_received.emit(bg_obj)
                elif action == "gps_position":
                    gps_obj = GPSData.from_dict(data)
                    self.gps_received.emit(gps_obj)

                elif action == "rf_stream":
                    rf_stream_obj = StreamDataChunk.from_dict(data, SourceType.RF)
                    self.rf_data_received.emit(rf_stream_obj)

                elif action == "sound_stream":
                    sound_stream_obj = StreamDataChunk.from_dict(data, SourceType.SOUND)
                    self.sound_data_received.emit(sound_stream_obj)

                elif action == "db_operation_result":
                    response_obj = ServiceResponse.from_dict(data)
                    self.request_finished.emit(response_obj)

                    print(
                        f"[PiNet] Operation '{response_obj.operation}' finished with status {response_obj.status.value}"
                    )
                else:
                    self.data_received.emit(packet)

            except json.JSONDecodeError:
                print(f"[PiNet] JSON Error: {line}")
            except Exception as e:
                print(f"[PiNet] Read Error: {e}")

    def send_packet(self, action: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Універсальний метод відправки пакету на сервер.

        Формує JSON з полями `action`, `data` та `timestamp`, додає символ
        нового рядка та записує в сокет.

        Args:
            action (str): Тип дії (команда).
            data (Optional[Dict[str, Any]], optional): Дані команди. Defaults to None.
        """
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
                print(f"[PiNet] Send Error: {e}")
        else:
            print("[PiNet] Cannot send packet: No connection.")

    # --- PUBLIC API METHODS ---

    def request_remote_gps(self) -> None:
        """Надсилає запит на сервер для отримання поточних GPS-координат."""
        print("[PiNet] Requesting GPS...")
        self.send_packet("get_gps")

    def request_rf_data_start(self) -> None:
        """Починає трансляцію RF-спектра з сервера."""
        print("[PiNet] Starting RF stream...")
        self.send_packet("start_rf_stream")

    def request_rf_data_end(self) -> None:
        """Зупиняє трансляцію RF-спектра."""
        print("[PiNet] Stopping RF stream...")
        self.send_packet("stop_rf_stream")

    def request_sound_data_start(self) -> None:
        """Починає трансляцію звукових даних (аудіо)."""
        print("[PiNet] Starting Sound stream...")
        self.send_packet("start_sound_stream")

    def request_sound_data_end(self) -> None:
        """Зупиняє трансляцію звукових даних."""
        print("[PiNet] Stopping Sound stream...")
        self.send_packet("stop_sound_stream")

    def report_false_alarm(self, event_id: str) -> None:
        """
        Повідомляє сервер про помилкове спрацювання детекції.

        Args:
            event_id (str): Унікальний ідентифікатор події.
        """
        print(f"[PiNet] Reporting false alarm: {event_id}")
        self.send_packet("false_alarm", {"event_id": event_id})

    def request_alarm_start(self, relays: list[str]) -> None:
        """
        Запускає роботу апаратних реле (Jammer).

        Args:
            relays (list[str]): Список назв реле для активації.
        """
        print("[PiNet] Starting relays working...")
        self.send_packet("start_alarm", {"relays": relays})

    def request_alarm_stop(self) -> None:
        """Зупиняє роботу всіх апаратних реле."""
        print("[PiNet] Stopping relays working...")
        self.send_packet("stop_alarm")

    def set_rf_range(self, rf_range: list[int]) -> None:
        """
        Встановлює робочий діапазон частот для SDR.

        Args:
            rf_range (list[int]): Масив [min_freq, max_freq] в МГц.
        """
        print(f"[PiNet] Setting RF range: {rf_range}")
        self.send_packet("set_rf_range", {"range": rf_range})

    # --- DATABASE PROXY METHODS ---

    def request_db_objects_page(self, page: int, page_size: int) -> None:
        """
        Запитує сторінку сигнатур об'єктів з бази даних.

        Args:
            page (int): Номер сторінки.
            page_size (int): Кількість записів на одну сторінку.
        """
        print(f"[PiNet] DB Request: Objects Page {page}")
        self.send_packet("db_request_page", {"page": page, "size": page_size})

    def request_db_add_object(self, obj_data: DetectionObject) -> None:
        """
        Запит на додавання нової сигнатури об'єкта.

        Args:
            obj_data (DetectionObject): Об'єкт моделі з даними.
        """
        print(f"[PiNet] DB Request: Add Object '{obj_data.name}'")
        self.send_packet("db_request_add", {"object": obj_data.to_dict()})

    def request_db_update_object(self, obj_data: DetectionObject) -> None:
        """
        Запит на оновлення існуючої сигнатури.

        Args:
            obj_data (DetectionObject): Об'єкт моделі з оновленими даними.
        """
        print(f"[PiNet] DB Request: Update Object ID {obj_data.id}")
        self.send_packet("db_request_update", {"object": obj_data.to_dict()})

    def request_db_delete_object(self, object_id: int) -> None:
        """
        Запит на видалення сигнатури.

        Args:
            object_id (int): Унікальний ID об'єкта.
        """
        print(f"[PiNet] DB Request: Delete Object ID {object_id}")
        self.send_packet("db_request_delete", {"id": object_id})

    def request_db_classes(self) -> None:
        """Запитує список усіх класів (категорій) об'єктів."""
        print("[PiNet] DB Request: Get All Classes")
        self.send_packet("db_request_classes")

    def request_db_add_class(self, class_obj: ObjectClass) -> None:
        """
        Запит на додавання нового класу об'єктів.

        Args:
            class_obj (ObjectClass): Об'єкт моделі класу.
        """
        print(f"[PiNet] DB Request: Add Class '{class_obj.name}'")
        self.send_packet("db_request_add_class", {"class": class_obj.to_dict()})

    def request_db_rename_class(
        self, old_class_obj: ObjectClass, new_class_obj: ObjectClass
    ) -> None:
        """
        Запит на перейменування класу.

        Args:
            old_class_obj (ObjectClass): Поточні дані класу.
            new_class_obj (ObjectClass): Нові дані класу.
        """
        print(
            f"[PiNet] DB Request: Rename Class '{old_class_obj.name}' -> '{new_class_obj.name}'"
        )
        self.send_packet(
            "db_request_rename_class",
            {
                "old_class": old_class_obj.to_dict(),
                "new_class": new_class_obj.to_dict(),
            },
        )

    def request_db_delete_class(self, class_id: int) -> None:
        """
        Запит на видалення класу.

        Args:
            class_id (int): Унікальний ID класу.
        """
        print(f"[PiNet] DB Request: Delete Class ID {class_id}")
        self.send_packet("db_request_delete_class", {"id": class_id})
