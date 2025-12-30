import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from PyQt6.QtCore import QObject, pyqtSlot, QByteArray
from PyQt6.QtNetwork import QTcpServer, QTcpSocket, QHostAddress

# Імпортуємо моделі
from app.models.detection_event import DetectionEvent
from app.models.detection_object import DetectionObject
from app.models.object_class import ObjectClass


class PiServerService(QObject):
    """
    Сервіс-сервер для Raspberry Pi.
    Приймає підключення від Desktop-клієнта, обробляє команди та керує периферією.
    """

    def __init__(self, port: int = 6000, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.port = port
        self.server: Optional[QTcpServer] = None
        self.client_socket: Optional[QTcpSocket] = None

        # Тут можна буде ініціалізувати менеджери для БД та Hardware
        # self.db_manager = ...
        # self.hardware_manager = ...

    def start(self) -> None:
        self.server = QTcpServer(self)
        self.server.newConnection.connect(self._handle_new_connection)

        if self.server.listen(QHostAddress.SpecialAddress.Any, self.port):
            print(f"[PiProxy] Server listening on port {self.port}")
        else:
            print(f"[PiProxy] Error starting server: {self.server.errorString()}")

    def stop(self) -> None:
        if self.client_socket:
            self.client_socket.disconnectFromHost()
            if self.client_socket.state() != QTcpSocket.SocketState.UnconnectedState:
                self.client_socket.waitForDisconnected(1000)

        if self.server:
            self.server.close()

        print("[PiProxy] Server stopped.")

    @pyqtSlot()
    def _handle_new_connection(self) -> None:
        """
        Обробка нового підключення.
        Стратегія: Одночасно лише один клієнт. Новий клієнт 'вибиває' старого.
        """
        if self.client_socket:
            print(
                f"[PiProxy] Closing old connection from {self.client_socket.peerAddress().toString()}"
            )
            self.client_socket.close()
            self.client_socket.deleteLater()  # Важливо для звільнення ресурсів Qt

        self.client_socket = self.server.nextPendingConnection()
        print(
            f"[PiProxy] Client connected: {self.client_socket.peerAddress().toString()}"
        )

        self.client_socket.readyRead.connect(self._read_data)
        self.client_socket.disconnected.connect(self._handle_disconnected)

    @pyqtSlot()
    def _handle_disconnected(self) -> None:
        print("[PiProxy] Client disconnected.")
        # Не обнуляємо self.client_socket одразу тут, якщо плануємо реконнект,
        # але в даній архітектурі це ок, бо чекаємо нового.
        self.client_socket = None

    @pyqtSlot()
    def _read_data(self) -> None:
        if not self.client_socket:
            return

        # Використовуємо canReadLine, тому клієнт МАЄ додавати \n в кінці JSON
        while self.client_socket.canReadLine():
            line = self.client_socket.readLine().trimmed()
            try:
                json_str = bytes(line).decode("utf-8")
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
        """Головний маршрутизатор команд."""

        # Розділяємо логіку на апаратну та серверну (БД) для чистоти коду
        if action.startswith("db_"):
            self._handle_db_command(action, data)
        else:
            self._handle_hardware_command(action, data)

    def _handle_hardware_command(self, action: str, data: Dict[str, Any]) -> None:
        """Обробка команд, пов'язаних з сенсорами та залізом."""

        if action == "get_gps":
            # TODO: Get real GPS data
            # gps_data = self.hardware.get_gps()
            # self.send_gps_data(gps_data)
            pass

        elif action == "start_rf_stream":
            # TODO: Start SDR process
            # self.send_rf_stream_data({...})
            pass

        elif action == "stop_rf_stream":
            pass

        elif action == "start_sound_stream":
            # TODO: Start Audio process
            # self.send_sound_stream_data({...})
            pass

        elif action == "stop_sound_stream":
            pass

        elif action == "start_alarm":
            relays = data.get("relays", [])
            print(f"[PiProxy] Activating relays: {relays}")
            # TODO: GPIO logic
            pass

        elif action == "stop_alarm":
            print("[PiProxy] Deactivating relays")
            pass

        elif action == "false_alarm":
            event_id = data.get("event_id")
            print(f"[PiProxy] Marking event {event_id} as false alarm")
            # TODO: Log false alarm to DB / Retrain model
            pass

        elif action == "set_rf_range":
            min, max = data.get("range")
            print(f"[PiProxy] Set follow rf range {min}-{max}")
            # TODO: Set range for detecting
            pass

        else:
            print(f"[PiProxy] Unknown hardware command: {action}")

    def _handle_db_command(self, action: str, data: Dict[str, Any]) -> None:
        """Обробка CRUD операцій та запитів до бази даних."""

        if action == "db_request_page":
            page = data.get("page", 1)
            size = data.get("size", 15)

            # TODO: Реальна логіка
            # items_dicts, total = self.db.get_objects(page, size)
            # items_models = [DetectionObject.from_dict(d) for d in items_dicts]

            # SIMULATION RESPONSE:
            # self.send_db_objects_page(items_models, page, total)
            pass

        elif action == "db_request_add":
            raw_obj = data.get("object")
            if raw_obj:
                try:
                    new_object_model = DetectionObject.from_dict(raw_obj)
                    print(f"[PiProxy] Adding object: {new_object_model.name}")

                    # created_dict = self.db.add_object(new_object_model.to_dict())
                    # created_model = DetectionObject.from_dict(created_dict)
                    # self.send_db_object_added(created_model)
                except Exception as e:
                    print(f"[PiProxy] Add Error: {e}")
                    # self.send_db_error("add", str(e))
            pass

        elif action == "db_request_update":
            raw_obj = data.get("object")
            if raw_obj:
                try:
                    updated_object_model = DetectionObject.from_dict(raw_obj)
                    print(f"[PiProxy] Updating object ID: {updated_object_model.id}")

                    # updated_dict = self.db.update_object(updated_object_model.to_dict())
                    # updated_model = DetectionObject.from_dict(updated_dict)
                    # self.send_db_object_updated(updated_model)
                except Exception as e:
                    print(f"[PiProxy] Update Error: {e}")
                    # self.send_db_error("update", str(e))
            pass

        elif action == "db_request_delete":
            obj_id = data.get("id")
            print(f"[PiProxy] Deleting object ID: {obj_id}")

            try:
                # success = self.db.delete_object(obj_id)
                # if success:
                #     self.send_db_object_deleted(obj_id)
                # else:
                #     self.send_db_error("delete", "Object not found or could not be deleted")
                pass
            except Exception as e:
                print(f"[PiProxy] Delete Error: {e}")
                # self.send_db_error("delete", str(e))
            pass

        elif action == "db_request_classes":
            # TODO: classes_dicts = self.db.get_classes()
            # classes_models = [ObjectClass.from_dict(c) for c in classes_dicts]

            # SIMULATION RESPONSE:
            # self.send_db_classes(classes_models)
            pass

        elif action == "db_request_add_class":
            name = data.get("name")
            # TODO: success = self.db.add_class(name)
            # SIMULATION RESPONSE:
            # self.send_db_classes(new_classes_models)
            pass

        elif action == "db_request_rename_class":
            old = data.get("old")
            new = data.get("new")
            # TODO: success = self.db.rename_class(old, new)
            # SIMULATION RESPONSE:
            # self.send_db_classes(updated_classes_models)
            pass

        elif action == "db_request_delete_class":
            class_id = data.get("id")
            try:
                # TODO: Логіка в БД має перевірити foreign keys або зробити SELECT count(*) ...
                # is_used = self.db.is_class_used(class_id)

                # if is_used:
                #     self.send_db_error("delete_class", "Class is used")
                # else:
                #     self.db.delete_class(class_id)
                #     new_classes_dicts = self.db.get_classes()
                #     self.send_db_classes(...)
                pass
            except Exception as e:
                print(f"[PiProxy] Delete Class Error: {e}")
                # self.send_db_error("delete_class", f"Помилка сервера: {str(e)}")

        else:
            print(f"[PiProxy] Unknown DB command: {action}")

    # --- SENDER METHODS ---

    def send_packet(self, action: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Відправка відповіді клієнту."""
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
                self.client_socket.write(QByteArray(msg))
                self.client_socket.flush()
            except Exception as e:
                print(f"[PiProxy] Send Error: {e}")

    def send_detection_event(self, event: DetectionEvent) -> None:
        """
        Відправляє подію виявлення.
        Приймає типізований об'єкт DetectionEvent.
        """
        print(f"[PiProxy] Sending Detection: {event.name}")
        self.send_packet("detection", event.to_dict())

    def send_gps_data(self, gps_data: Dict[str, Any]) -> None:
        """Відправляє координати {lat, lon, alt}."""
        self.send_packet("gps_position", gps_data)

    def send_rf_stream_data(self, spectrum_data: Dict[str, Any]) -> None:
        """Відправляє пакет даних спектру."""
        self.send_packet("rf_stream", spectrum_data)

    def send_sound_stream_data(self, audio_analysis: Dict[str, Any]) -> None:
        """Відправляє дані аналізу звуку."""
        self.send_packet("sound_stream", audio_analysis)

    # --- DB RESPONSE SENDERS ---

    def send_db_objects_page(
        self, items: List[DetectionObject], page: int, total_items: int
    ) -> None:
        """
        Відправляє сторінку об'єктів для каталогу.
        Приймає список моделей DetectionObject.
        """
        print(f"[PiProxy] Sending DB Page {page}")

        items_dicts = [obj.to_dict() for obj in items]

        self.send_packet(
            "db_response_page",
            {"items": items_dicts, "page": page, "total": total_items},
        )

    def send_db_operation_status(self, op_type: str, success: bool, msg: str) -> None:
        """Відправляє результат CRUD операції."""
        self.send_packet(
            "db_response_status", {"op": op_type, "success": success, "msg": msg}
        )

    def send_db_error(self, operation: str, error_message: str) -> None:
        """
        Відправляє повідомлення про помилку виконання операції.
        Клієнт повинен показати це повідомлення користувачу.
        """
        print(f"[PiProxy] Sending Error ({operation}): {error_message}")
        self.send_packet(
            "db_response_status",
            {"op": operation, "success": False, "msg": error_message},
        )

    def send_db_object_added(self, obj: DetectionObject) -> None:
        """
        Повідомляє клієнта про успішне створення об'єкта.
        Повертає повний об'єкт (з ID, який присвоїла БД).
        """
        print(f"[PiProxy] Sending Event: Object Added (ID: {obj.id})")
        self.send_packet("db_event_object_added", {"object": obj.to_dict()})

    def send_db_object_updated(self, obj: DetectionObject) -> None:
        """
        Повідомляє клієнта про оновлення об'єкта.
        """
        print(f"[PiProxy] Sending Event: Object Updated (ID: {obj.id})")
        self.send_packet("db_event_object_updated", {"object": obj.to_dict()})

    def send_db_object_deleted(self, obj_id: int) -> None:
        """
        Повідомляє клієнта про видалення об'єкта.
        """
        print(f"[PiProxy] Sending Event: Object Deleted (ID: {obj_id})")
        self.send_packet("db_event_object_deleted", {"id": obj_id})

    def send_db_classes(self, classes: List[ObjectClass]) -> None:
        """
        Відправляє список усіх класів.
        Приймає список моделей ObjectClass.
        """
        print(f"[PiProxy] Sending {len(classes)} classes")
        classes_dicts = [c.to_dict() for c in classes]
        self.send_packet("db_response_classes", {"classes": classes_dicts})
