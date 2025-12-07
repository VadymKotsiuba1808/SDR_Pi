"""
Сервіс роботи з базою даних.
Відповідає за додавання, видалення та редагування об'єктів
"""

import json
import math
import uuid
import random
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer


class DatabaseService(QObject):
    # Сигнали (залишилися без змін для сумісності з UI)
    objects_page_loaded = pyqtSignal(list, int, int)
    operation_status = pyqtSignal(str, bool, str)

    def __init__(self, network_service, parent=None):
        super().__init__(parent)
        self.network = network_service
        # Ми не підписуємось на network, бо працюємо в режимі імітації
        # self.network.data_received.connect(self._handle_db_response)

        # --- ГЕНЕРАЦІЯ ФЕЙКОВИХ ДАНИХ ---
        self.fake_storage = self._generate_mock_data()
        print(f"[DB Mock] Generated {len(self.fake_storage)} fake objects.")

    def _generate_mock_data(self):
        """Створює 55 різноманітних об'єктів."""
        data = []
        classes = ["drone", "bird", "airplane", "ufo", "interference"]

        for i in range(1, 56):
            obj_class = classes[i % len(classes)]
            is_dangerous = (i % 3 == 0) or (obj_class == "drone")

            # Генеруємо RF дані (через один)
            rf = None
            if i % 2 == 0:
                rf = {
                    "freq_mhz": 2400.0 + (i * 5),
                    "bandwidth": 20.0,
                    "protocol": f"Protocol-{i}",
                }

            # Генеруємо Audio дані (кожен третій)
            audio = None
            if i % 3 == 0:
                audio = {"min_freq": 100 * i, "max_freq": 1000 * i}

            obj = {
                "id": str(uuid.uuid4()),
                "name": f"Test Object #{i:02d}",
                "object_class": obj_class,
                "is_dangerous": is_dangerous,
                "rf_params": rf,
                "audio_params": audio,
            }
            data.append(obj)
        return data

    # --- Публічні методи (MOCK IMPLEMENTATION) ---

    def request_objects_page(self, page=1, page_size=10):
        """Імітація запиту сторінки з затримкою."""
        print(f"[DB Mock] Requesting page {page} (limit {page_size})...")

        # Імітуємо затримку мережі 0.2 сек
        QTimer.singleShot(200, lambda: self._mock_send_page(page, page_size))

    def _mock_send_page(self, page, page_size):
        total_items = len(self.fake_storage)
        total_pages = math.ceil(total_items / page_size)

        if page < 1:
            page = 1
        if page > total_pages and total_pages > 0:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size

        # Зріз даних для поточної сторінки
        page_data = self.fake_storage[start:end]

        # Емітимо сигнал, ніби дані прийшли з мережі
        self.objects_page_loaded.emit(page_data, page, total_pages)

    def add_object(self, obj_data):
        """Імітація додавання."""
        print(f"[DB Mock] Adding: {obj_data.get('name')}")

        # Генеруємо ID, якщо його немає (хоча модель зазвичай це робить)
        if not obj_data.get("id"):
            obj_data["id"] = str(uuid.uuid4())

        # Додаємо в початок списку, щоб відразу побачити
        self.fake_storage.insert(0, obj_data)

        QTimer.singleShot(
            100, lambda: self.operation_status.emit("add", True, "Success")
        )

    def update_object(self, obj_data):
        """Імітація редагування."""
        target_id = obj_data.get("id")
        print(f"[DB Mock] Updating ID: {target_id}")

        found = False
        for i, obj in enumerate(self.fake_storage):
            if obj["id"] == target_id:
                self.fake_storage[i] = obj_data
                found = True
                break

        if found:
            QTimer.singleShot(
                100, lambda: self.operation_status.emit("update", True, "Success")
            )
        else:
            QTimer.singleShot(
                100, lambda: self.operation_status.emit("update", False, "Not Found")
            )

    def delete_object(self, object_id):
        """Імітація видалення."""
        print(f"[DB Mock] Deleting ID: {object_id}")

        initial_len = len(self.fake_storage)
        self.fake_storage = [obj for obj in self.fake_storage if obj["id"] != object_id]

        if len(self.fake_storage) < initial_len:
            QTimer.singleShot(
                100, lambda: self.operation_status.emit("delete", True, "Success")
            )
        else:
            QTimer.singleShot(
                100, lambda: self.operation_status.emit("delete", False, "Not Found")
            )

    # --- Заглушка для справжньої обробки (не використовується зараз) ---
    @pyqtSlot(dict)
    def _handle_db_response(self, packet):
        pass
