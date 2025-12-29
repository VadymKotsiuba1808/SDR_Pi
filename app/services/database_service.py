import math
import random
from typing import List, Dict, Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from app.models.object_class import ObjectClass
from app.models.detection_object import DetectionObject


class DatabaseService(QObject):
    """
    Сервіс для роботи з базою даних (Mock implementation).
    Імітує роботу з SQL базою даних (Autoincrement, Foreign Keys, Joins).
    """

    # Сигнали
    # Повертає список моделей DetectionObject, поточну сторінку, загальну кількість
    objects_page_loaded = pyqtSignal(list, int, int)

    # Статус операції: тип операції, успіх, повідомлення
    operation_status = pyqtSignal(str, bool, str)

    # Сигнал про оновлення списку класів (повертає список моделей ObjectClass)
    classes_updated = pyqtSignal(list)

    def __init__(self, network_service: Any, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.network = network_service

        # Лічильники для імітації AUTOINCREMENT (INT)
        self._class_id_counter: int = 1
        self._object_id_counter: int = 1

        # 1. Таблиця класів (Mock)
        self.fake_classes_storage: List[Dict[str, Any]] = self._init_mock_classes()

        # 2. Таблиця об'єктів (Mock)
        self.fake_storage: List[Dict[str, Any]] = self._generate_mock_objects()

        print(
            f"[Database] Service initialized. Mock objects: {len(self.fake_storage)}, Classes: {len(self.fake_classes_storage)}"
        )

    def _init_mock_classes(self) -> List[Dict[str, Any]]:
        names = ["Drone", "Bird", "Airplane", "UFO", "Interference"]
        classes = []
        for name in names:
            classes.append({"id": self._class_id_counter, "name": name})
            self._class_id_counter += 1
        return classes

    def _generate_mock_objects(self) -> List[Dict[str, Any]]:
        data = []
        for i in range(1, 120):
            # Вибираємо випадковий клас
            cls_record = random.choice(self.fake_classes_storage)
            is_dangerous = (i % 3 == 0) or (cls_record["name"] == "Drone")

            # RF Params (List[str] -> "min-max")
            rf_list: List[str] = []
            if i % 2 == 0:
                center = 2400.0 + (i * 10)
                bw = 20.0
                f_min = center - (bw / 2)
                f_max = center + (bw / 2)
                rf_list.append(f"{f_min}-{f_max}")
                if i % 4 == 0:
                    freq = 5800.0 + i
                    rf_list.append(f"{freq}-{freq}")

            # Sound Params (List[int])
            sound_list: List[int] = []
            if i % 3 == 0:
                base_freq = 200 + (i * 10)
                for h in range(1, 4):
                    if base_freq * h < 20000:
                        sound_list.append(int(base_freq * h))

            obj = {
                "id": self._object_id_counter,
                "name": f"Test Object #{i:02d}",
                # --- RELATIONS ---
                "class_id": cls_record["id"],  # Foreign Key
                "object_class": cls_record["name"],  # De-normalized name (Mock JOIN)
                # -----------------
                "is_dangerous": is_dangerous,
                "rf_params": rf_list,
                "sound_params": sound_list,
            }
            data.append(obj)
            self._object_id_counter += 1

        # Сортуємо: нові зверху
        data.reverse()
        return data

    # --- ОБ'ЄКТИ (CRUD) ---

    def request_objects_page(self, page: int = 1, page_size: int = 10) -> None:
        print(f"[Database] Requesting objects page {page} (Size: {page_size})...")
        QTimer.singleShot(150, lambda: self._mock_send_page(page, page_size))

    def _mock_send_page(self, page: int, page_size: int) -> None:
        total_items = len(self.fake_storage)
        total_pages = math.ceil(total_items / page_size)

        if page < 1:
            page = 1
        if page > total_pages and total_pages > 0:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size

        page_data = self.fake_storage[start:end]

        # POPULATION: Актуалізуємо назви класів перед відправкою (Mock JOIN)
        # Це гарантує, що якщо клас перейменували, користувач побачить нову назву
        for obj in page_data:
            cls = next(
                (c for c in self.fake_classes_storage if c["id"] == obj["class_id"]),
                None,
            )
            if cls:
                obj["object_class"] = cls["name"]

        # Конвертуємо dict -> Model
        model_list = [DetectionObject.from_dict(d) for d in page_data]

        print(f"[Database] Sending {len(model_list)} objects for page {page}.")
        self.objects_page_loaded.emit(model_list, page, total_items)

    def add_object(self, obj_data: Dict[str, Any]) -> None:
        print(f"[Database] Adding object: {obj_data.get('name')}")

        # AUTOINCREMENT Simulation
        if obj_data.get("id") is None:
            obj_data["id"] = self._object_id_counter
            self._object_id_counter += 1

        # POPULATION: Заповнюємо object_class по class_id
        if "class_id" in obj_data:
            found_cls = next(
                (
                    c
                    for c in self.fake_classes_storage
                    if c["id"] == obj_data["class_id"]
                ),
                None,
            )
            if found_cls:
                obj_data["object_class"] = found_cls["name"]

        self.fake_storage.insert(0, obj_data)
        self.operation_status.emit("add", True, "Success")

    def update_object(self, obj_data: Dict[str, Any]) -> None:
        target_id = obj_data.get("id")
        print(f"[Database] Updating object ID: {target_id}")

        found = False

        # POPULATION Update
        if "class_id" in obj_data:
            found_cls = next(
                (
                    c
                    for c in self.fake_classes_storage
                    if c["id"] == obj_data["class_id"]
                ),
                None,
            )
            if found_cls:
                obj_data["object_class"] = found_cls["name"]

        for i, obj in enumerate(self.fake_storage):
            if obj["id"] == target_id:
                self.fake_storage[i] = obj_data
                found = True
                break

        self.operation_status.emit("update", found, "Success" if found else "Not Found")

    def delete_object(self, object_id: int) -> None:
        print(f"[Database] Deleting object ID: {object_id}")
        initial_len = len(self.fake_storage)
        self.fake_storage = [obj for obj in self.fake_storage if obj["id"] != object_id]

        success = len(self.fake_storage) < initial_len
        self.operation_status.emit(
            "delete", success, "Success" if success else "Not Found"
        )

    # --- КЛАСИ (CRUD) ---

    def get_all_classes(self) -> List[ObjectClass]:
        """Повертає список об'єктів-моделей класів."""
        return [ObjectClass.from_dict(c) for c in self.fake_classes_storage]

    def add_class(self, class_name: str) -> bool:
        print(f"[Database] Adding class: '{class_name}'")

        # Check duplicate names
        if any(c["name"] == class_name for c in self.fake_classes_storage):
            print(f"[Database] Error: Class '{class_name}' already exists.")
            return False

        new_class = {"id": self._class_id_counter, "name": class_name}
        self._class_id_counter += 1

        self.fake_classes_storage.append(new_class)
        self.classes_updated.emit(self.get_all_classes())
        return True

    def rename_class(self, old_name: str, new_name: str) -> bool:
        print(f"[Database] Renaming class '{old_name}' -> '{new_name}'")
        class_id = None

        # 1. Знаходимо клас
        for c in self.fake_classes_storage:
            if c["name"] == old_name:
                c["name"] = new_name
                class_id = c["id"]
                break

        if class_id is not None:
            # 2. CASCADE UPDATE: Оновлюємо денормалізоване поле у всіх об'єктах
            updated_count = 0
            for obj in self.fake_storage:
                if obj.get("class_id") == class_id:
                    obj["object_class"] = new_name
                    updated_count += 1

            print(
                f"[Database] Class renamed. Cascaded update to {updated_count} objects."
            )
            self.classes_updated.emit(self.get_all_classes())
            return True

        return False

    def is_class_used(self, class_id: int) -> bool:
        """Перевіряє Foreign Key Integrity."""
        for obj in self.fake_storage:
            if obj.get("class_id") == class_id:
                return True
        return False

    def delete_class(self, class_id: int) -> bool:
        print(f"[Database] Deleting class ID: {class_id}")
        initial_len = len(self.fake_classes_storage)
        self.fake_classes_storage = [
            c for c in self.fake_classes_storage if c["id"] != class_id
        ]

        if len(self.fake_classes_storage) < initial_len:
            self.classes_updated.emit(self.get_all_classes())
            return True
        return False
