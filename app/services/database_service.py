"""
Сервіс роботи з базою даних.
Відповідає за додавання, видалення та редагування об'єктів.
"""

import math
import uuid
import random
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer


class DatabaseService(QObject):
    # Сигнали
    objects_page_loaded = pyqtSignal(list, int, int)
    operation_status = pyqtSignal(str, bool, str)

    def __init__(self, network_service, parent=None):
        super().__init__(parent)
        self.network = network_service

        # --- ГЕНЕРАЦІЯ ФЕЙКОВИХ ДАНИХ ---
        self.fake_storage = self._generate_mock_data()
        print(f"[DB Mock] Generated {len(self.fake_storage)} fake objects.")

    def _generate_mock_data(self):
        """Створює 55 різноманітних об'єктів з новою структурою даних (min/max для RF)."""
        data = []
        classes = ["drone", "bird", "airplane", "ufo", "interference"]

        for i in range(1, 56):
            obj_class = classes[i % len(classes)]
            is_dangerous = (i % 3 == 0) or (obj_class == "drone")

            # --- RF: Список діапазонів ---
            rf_list = []
            if i % 2 == 0:
                # Генерація діапазону (Bandwidth)
                center = 2400.0 + (i * 10)
                bw = 20.0
                rf_list.append(
                    {"min_mhz": center - (bw / 2), "max_mhz": center + (bw / 2)}
                )

                # У деяких об'єктів додаємо другу, фіксовану частоту
                if i % 4 == 0:
                    freq = 5800.0 + i
                    rf_list.append(
                        {
                            "min_mhz": freq,
                            "max_mhz": freq,  # min == max означає точну частоту
                        }
                    )

            # --- Sound: Список частот (цілі числа) ---
            sound_list = []
            if i % 3 == 0:
                base_freq = 200 + (i * 10)
                # Генеруємо гармоніки
                for h in range(1, 4):
                    if base_freq * h < 20000:
                        sound_list.append(base_freq * h)

            obj = {
                "id": str(uuid.uuid4()),
                "name": f"Test Object #{i:02d}",
                "object_class": obj_class,
                "is_dangerous": is_dangerous,
                "rf_params": rf_list,  # Список словників {min, max}
                "sound_params": sound_list,  # Список int
            }
            data.append(obj)

        return data

    # --- Публічні методи (MOCK IMPLEMENTATION) ---

    def request_objects_page(self, page=1, page_size=10):
        """Імітація запиту сторінки з затримкою."""
        print(f"[DB Mock] Requesting page {page} (limit {page_size})...")
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

        page_data = self.fake_storage[start:end]
        self.objects_page_loaded.emit(page_data, page, total_pages)

    def add_object(self, obj_data):
        print(f"[DB Mock] Adding: {obj_data.get('name')}")
        if not obj_data.get("id"):
            obj_data["id"] = str(uuid.uuid4())
        self.fake_storage.insert(0, obj_data)
        QTimer.singleShot(
            100, lambda: self.operation_status.emit("add", True, "Success")
        )

    def update_object(self, obj_data):
        target_id = obj_data.get("id")
        print(f"[DB Mock] Updating ID: {target_id}")
        found = False
        for i, obj in enumerate(self.fake_storage):
            if obj["id"] == target_id:
                self.fake_storage[i] = obj_data
                found = True
                break
        status = "Success" if found else "Not Found"
        QTimer.singleShot(
            100, lambda: self.operation_status.emit("update", found, status)
        )

    def delete_object(self, object_id):
        print(f"[DB Mock] Deleting ID: {object_id}")
        initial_len = len(self.fake_storage)
        self.fake_storage = [obj for obj in self.fake_storage if obj["id"] != object_id]
        success = len(self.fake_storage) < initial_len
        status = "Success" if success else "Not Found"
        QTimer.singleShot(
            100, lambda: self.operation_status.emit("delete", success, status)
        )
