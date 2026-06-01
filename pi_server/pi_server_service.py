import json
from datetime import datetime
from typing import Any, Dict, Optional

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtNetwork import QHostAddress, QTcpServer, QTcpSocket

from app.models.detection_background import DetectionBackground
from app.models.detection_event import DetectionEvent
from app.models.detection_object import DetectionObject
from app.models.gps_data import GPSData
from app.models.object_class import ObjectClass
from app.models.service_response import ServiceResponse, StatusCode
from pi_server.database_service import DatabaseService


class PiServerService(QObject):
    """Сервіс-сервер для Raspberry Pi.

    Цей клас реалізує TCP-сервер, який працює на Raspberry Pi. Він приймає підключення
    від Desktop-клієнта, обробляє вхідні JSON-команди для керування периферією
    (SDR, GPS, GPIO) та взаємодіє з локальною базою даних через DatabaseService.

    Attributes:
        port (int): Порт, на якому сервер очікує підключення.
        server (Optional[QTcpServer]): Об'єкт TCP-сервера Qt.
        client_socket (Optional[QTcpSocket]): Сокет поточного підключеного клієнта.
        db (DatabaseService): Сервіс для роботи з базою даних SQLite.
    """

    def __init__(
        self,
        port: int = 6000,
        db_service: Optional[DatabaseService] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        """Ініціалізує сервіс сервера.

        Args:
            port: Номер порту для прослуховування. За замовчуванням 6000.
            db_service: Екземпляр сервісу БД. Якщо не вказано, створюється новий.
            parent: Батьківський об'єкт QObject.
        """
        super().__init__(parent)
        self.port = port
        self.server: Optional[QTcpServer] = None
        self.client_socket: Optional[QTcpSocket] = None

        self.db = db_service or DatabaseService()
        self.db.request_finished.connect(self.send_db_response)

    def start(self) -> None:
        """Запускає TCP-сервер на вказаному порту.

        Сервер починає прослуховувати всі доступні мережеві інтерфейси.
        """
        self.server = QTcpServer(self)
        self.server.newConnection.connect(self._handle_new_connection)

        if self.server.listen(QHostAddress.SpecialAddress.Any, self.port):
            print(f"[PiProxy] Server listening on port {self.port}")
        else:
            print(f"[PiProxy] Error starting server: {self.server.errorString()}")

    def stop(self) -> None:
        """Зупиняє сервер та розриває активні з'єднання.

        Метод гарантує коректне закриття клієнтського сокета перед зупинкою сервера.
        """
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

        print("[PiProxy] Server stopped.")

    @pyqtSlot()
    def _handle_new_connection(self) -> None:
        """Обробляє нове вхідне підключення.

        !!! info "Стратегія підключення"
            Система підтримує лише одного активного клієнта одночасно (Desktop GUI).
            Якщо підключається новий клієнт, старе з'єднання примусово закривається.
            Це запобігає конфліктам при керуванні апаратними ресурсами.
        """
        if self.server is None:
            return

        if self.client_socket:
            peer_address = self.client_socket.peerAddress()
            addr_str = peer_address.toString() if peer_address else "Unknown"
            print(f"[PiProxy] Closing old connection from {addr_str}")
            self.client_socket.close()
            self.client_socket.deleteLater()

        self.client_socket = self.server.nextPendingConnection()
        if self.client_socket is None:
            return

        peer_address = self.client_socket.peerAddress()
        addr_str = peer_address.toString() if peer_address else "Unknown"
        print(f"[PiProxy] Client connected: {addr_str}")

        self.client_socket.readyRead.connect(self._read_data)
        self.client_socket.disconnected.connect(self._handle_disconnected)

    @pyqtSlot()
    def _handle_disconnected(self) -> None:
        """Слот для обробки відключення клієнта."""
        print("[PiProxy] Client disconnected.")
        self.client_socket = None

    @pyqtSlot()
    def _read_data(self) -> None:
        """Читає та парсить вхідні дані з сокета.

        Використовує лінійний протокол: кожне повідомлення — це JSON-об'єкт,
        що завершується символом нового рядка `\\n`.
        """
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

                print(f"[PiProxy] Received action: {action}")
                self._process_command(action, data)

            except json.JSONDecodeError:
                print(f"[PiProxy] JSON Error: {line}")
            except Exception as e:
                print(f"[PiProxy] Processing Error: {e}")

    def _process_command(self, action: str, data: Dict[str, Any]) -> None:
        """Головний маршрутизатор команд від клієнта.

        Розподіляє команди на дві категорії: операції з базою даних (префікс `db_`)
        та пряме керування апаратним забезпеченням.

        Args:
            action: Назва команди/дії.
            data: Словник з параметрами команди.
        """
        if action.startswith("db_"):
            self._handle_db_command(action, data)
        else:
            self._handle_hardware_command(action, data)

    def _handle_hardware_command(self, action: str, data: Dict[str, Any]) -> None:
        """Обробка команд, пов'язаних з сенсорами та апаратним забезпеченням.

        Args:
            action: Назва апаратної команди.
            data: Параметри (наприклад, номери реле або частотний діапазон).
        """
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
            print(f"[PiProxy] Activating relays: {relays}")
            # TODO: Логіка керування GPIO (реле тривоги)
            pass

        elif action == "stop_alarm":
            print("[PiProxy] Deactivating relays")
            pass

        elif action == "false_alarm":
            event_id = data.get("event_id")
            print(f"[PiProxy] Marking event {event_id} as false alarm")
            # TODO: Логування хибної тривоги та можливе донавчання моделі
            pass

        elif action == "set_rf_range":
            r_range = data.get("range", [])
            print(f"[PiProxy] Set follow rf range {r_range}")
            # TODO: Встановлення діапазону сканування для SDR (в МГц)
            pass

        else:
            print(f"[PiProxy] Unknown hardware command: {action}")

    def _handle_db_command(self, action: str, data: Dict[str, Any]) -> None:
        """Обробка CRUD операцій та запитів до бази даних.

        Цей метод перетворює JSON-дані у моделі SQLAlchemy/Pydantic та передає
        їх до DatabaseService для асинхронного виконання.

        Args:
            action: Тип операції (наприклад, `db_request_add`).
            data: Дані об'єкта або параметри фільтрації.
        """
        try:
            if action == "db_request_page":
                page = data.get("page", 1)
                size = data.get("size", 15)
                self.db.request_objects_page(page, size)

            elif action == "db_request_add":
                raw_obj = data.get("object")
                if raw_obj:
                    new_object_model = DetectionObject.from_dict(raw_obj)
                    print(f"[PiProxy] Adding object: {new_object_model.name}")
                    self.db.add_object(new_object_model)
                else:
                    raise ValueError("Missing 'object' data")

            elif action == "db_request_update":
                raw_obj = data.get("object")
                if raw_obj:
                    updated_object_model = DetectionObject.from_dict(raw_obj)
                    print(f"[PiProxy] Updating object ID: {updated_object_model.id}")
                    self.db.update_object(updated_object_model)
                else:
                    raise ValueError("Missing 'object' data")

            elif action == "db_request_delete":
                obj_id = data.get("id")
                print(f"[PiProxy] Deleting object ID: {obj_id}")
                if obj_id:
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
                        print("[PiProxy] Rename Class Error: Invalid Data")
                        raise ValueError("Invalid ID or Name")
                else:
                    print("[PiProxy] Rename Class Error: Missing old/new class data")
                    raise ValueError("Missing old/new class data")

            elif action == "db_request_delete_class":
                class_id = data.get("id")
                if class_id:
                    self.db.delete_class(class_id)
                else:
                    raise ValueError("Missing 'id'")

            else:
                print(f"[PiProxy] Unknown DB command: {action}")
                self._send_protocol_error(action, "Unknown command")

        except Exception as e:
            print(f"[PiProxy] DB Logic Error: {e}")
            self._send_protocol_error(action, str(e))

    def _send_protocol_error(self, operation: str, error_msg: str) -> None:
        """Відправляє повідомлення про помилку протоколу або валідації.

        Args:
            operation: Назва операції, під час якої виникла помилка.
            error_msg: Текст повідомлення про помилку.
        """
        response = ServiceResponse(
            operation=operation,
            status=StatusCode.BAD_REQUEST,
            message=f"Protocol/Validation Error: {error_msg}",
        )
        self.send_db_response(response)

    def send_packet(self, action: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Відправляє структурований JSON-пакет клієнту.

        Кожен пакет включає дію, корисне навантаження та мітку часу.
        Додає символ `\\n` в кінці повідомлення для лінійної обробки на стороні клієнта.

        Args:
            action: Назва дії (тип повідомлення).
            data: Дані повідомлення. За замовчуванням порожній словник.
        """
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
                print(f"[PiProxy] Send Error: {e}")

    def send_detection_event(self, event: DetectionEvent) -> None:
        """Відправляє подію виявлення об'єкта.

        Args:
            event: Екземпляр моделі DetectionEvent.
        """
        print(f"[PiProxy] Sending Detection: {event.name}")
        self.send_packet("detection", event.to_dict())

    def send_detection_background(self, back: DetectionBackground) -> None:
        """Відправляє статистичну інформацію про фонову обстановку.

        Args:
            back: Екземпляр моделі DetectionBackground.
        """
        print("[PiProxy] Sending Detection background")
        self.send_packet("detection_background", back.to_dict())

    def send_gps_data(self, gps_data: GPSData) -> None:
        """Відправляє поточні GPS-координати сервера.

        Args:
            gps_data: Екземпляр моделі GPSData {lat, lon, alt}.
        """
        self.send_packet("gps_position", gps_data.to_dict())

    def send_rf_stream_data(self, spectrum_data: Dict[str, Any]) -> None:
        """Відправляє пакет сирих даних спектру для візуалізації.

        Args:
            spectrum_data: Словник з амплітудами та частотами.
        """
        self.send_packet("rf_stream", spectrum_data)

    def send_sound_stream_data(self, audio_analysis: Dict[str, Any]) -> None:
        """Відправляє результат акустичного аналізу.

        Args:
            audio_analysis: Дані про виявлені звукові сигнатури.
        """
        self.send_packet("sound_stream", audio_analysis)

    @pyqtSlot(object)
    def send_db_response(self, response: ServiceResponse) -> None:
        """Відправляє результат виконання операції з БД.

        Цей метод є слотом, який підключається до сигналу `request_finished`
        сервісу бази даних.

        Args:
            response: Об'єкт ServiceResponse зі статусом та даними.
        """
        print(f"[PiProxy] DB Response: {response.operation} -> {response.status}")
        packet_data = response.to_dict()
        self.send_packet("db_operation_result", packet_data)
