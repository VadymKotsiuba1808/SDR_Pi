import sqlite3
import json
import math
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot

# Налаштування шляху до БД
DB_PATH = "./sdr_pi.db"


class DBWorker(QRunnable):
    """
    Окремий потік для виконання SQL запитів,
    щоб не заморожувати інтерфейс.
    """

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        try:
            self.func(*self.args, **self.kwargs)
        except Exception as e:
            print(f"[DB Error] {e}")


class DatabaseService(QObject):
    # Сигнали (ідентичні до твого старого сервісу + сигнал для класів)
    objects_page_loaded = pyqtSignal(list, int, int)  # data, current_page, total_pages
    classes_loaded = pyqtSignal(list)  # список назв класів для ComboBox
    operation_status = pyqtSignal(str, bool, str)  # operation_type, success, message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.threadpool = QThreadPool()

        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            "PRAGMA synchronous=NORMAL;"
        )  # Трохи менше безпеки, але швидше для SD-карти
        conn.close()

        # Перевірка підключення при старті
        print(f"[DB] Service started. Using database: {DB_PATH}")

    # --- ДОПОМІЖНІ МЕТОДИ (SQL) ---

    def _connect(self):
        """Створює з'єднання з БД."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Дозволяє звертатися до колонок по імені
        return conn

    def _get_class_id(self, cursor, class_name):
        """Знаходить ID класу по назві."""
        cursor.execute(
            "SELECT id FROM object_classes WHERE class_name = ?", (class_name,)
        )
        res = cursor.fetchone()
        if res:
            return res["id"]
        raise ValueError(f"Клас '{class_name}' не знайдено в БД")

    # --- ПУБЛІЧНІ МЕТОДИ (API) ---

    def request_classes(self):
        """Запитує список всіх доступних класів для випадаючого списку."""
        worker = DBWorker(self._fetch_classes_task)
        self.threadpool.start(worker)

    def request_objects_page(self, page=1, page_size=10):
        """Запитує сторінку об'єктів."""
        worker = DBWorker(self._fetch_page_task, page, page_size)
        self.threadpool.start(worker)

    def add_object(self, obj_data):
        """Додає новий об'єкт."""
        worker = DBWorker(self._add_object_task, obj_data)
        self.threadpool.start(worker)

    def update_object(self, obj_data):
        """Оновлює існуючий об'єкт."""
        worker = DBWorker(self._update_object_task, obj_data)
        self.threadpool.start(worker)

    def delete_object(self, object_id):
        """Видаляє об'єкт за ID."""
        worker = DBWorker(self._delete_object_task, object_id)
        self.threadpool.start(worker)

    # --- ВНУТРІШНЯ ЛОГІКА (ЗАДАЧІ ДЛЯ ПОТОКІВ) ---

    def _fetch_classes_task(self):
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT class_name FROM object_classes")
            rows = cursor.fetchall()
            classes = [row["class_name"] for row in rows]
            self.classes_loaded.emit(classes)
        finally:
            conn.close()

    def _fetch_page_task(self, page, page_size):
        conn = self._connect()
        try:
            cursor = conn.cursor()

            # 1. Отримуємо загальну кількість для пагінації
            cursor.execute("SELECT COUNT(*) as count FROM signatures")
            total_items = cursor.fetchone()["count"]
            total_pages = math.ceil(total_items / page_size)

            if page < 1:
                page = 1
            if page > total_pages and total_pages > 0:
                page = total_pages

            offset = (page - 1) * page_size

            # 2. Отримуємо дані з JOIN (щоб отримати назву класу, а не його ID)
            query = """
                SELECT s.id, s.name, c.class_name as object_class, 
                       s.is_dangerous, s.rf_params, s.sound_params
                FROM signatures s
                JOIN object_classes c ON s.class_id = c.id
                ORDER BY s.id DESC
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, (page_size, offset))
            rows = cursor.fetchall()

            # 3. Конвертація в Python-об'єкти
            data = []
            for row in rows:
                obj = dict(row)
                obj["is_dangerous"] = bool(obj["is_dangerous"])
                # Десеріалізація JSON (рядок -> список)
                obj["rf_params"] = (
                    json.loads(obj["rf_params"]) if obj["rf_params"] else []
                )
                obj["sound_params"] = (
                    json.loads(obj["sound_params"]) if obj["sound_params"] else []
                )
                data.append(obj)

            self.objects_page_loaded.emit(data, page, total_pages)

        except Exception as e:
            print(f"[DB Error Fetch] {e}")
            self.objects_page_loaded.emit(
                [], 1, 1
            )  # Повертаємо пустий список, щоб не крашити UI
        finally:
            conn.close()

    def _add_object_task(self, obj_data):
        conn = self._connect()
        try:
            cursor = conn.cursor()

            # Отримуємо ID класу
            class_id = self._get_class_id(cursor, obj_data["object_class"])

            # Підготовка даних (JSON серіалізація)
            rf_json = json.dumps(obj_data.get("rf_params", []))
            sound_json = json.dumps(obj_data.get("sound_params", []))
            is_dang = 1 if obj_data.get("is_dangerous") else 0

            query = """
                INSERT INTO signatures (name, class_id, is_dangerous, rf_params, sound_params)
                VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(
                query, (obj_data["name"], class_id, is_dang, rf_json, sound_json)
            )
            conn.commit()

            self.operation_status.emit("add", True, "Об'єкт успішно додано")
            # Автоматично оновлюємо список
            self.request_objects_page(1)

        except Exception as e:
            self.operation_status.emit("add", False, str(e))
        finally:
            conn.close()

    def _update_object_task(self, obj_data):
        conn = self._connect()
        try:
            cursor = conn.cursor()
            class_id = self._get_class_id(cursor, obj_data["object_class"])

            rf_json = json.dumps(obj_data.get("rf_params", []))
            sound_json = json.dumps(obj_data.get("sound_params", []))
            is_dang = 1 if obj_data.get("is_dangerous") else 0
            obj_id = obj_data["id"]

            query = """
                UPDATE signatures 
                SET name=?, class_id=?, is_dangerous=?, rf_params=?, sound_params=?
                WHERE id=?
            """
            cursor.execute(
                query,
                (obj_data["name"], class_id, is_dang, rf_json, sound_json, obj_id),
            )
            conn.commit()

            self.operation_status.emit("update", True, "Об'єкт оновлено")
            self.request_objects_page(1)  # Або перезавантажити поточну сторінку

        except Exception as e:
            self.operation_status.emit("update", False, str(e))
        finally:
            conn.close()

    def _delete_object_task(self, object_id):
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM signatures WHERE id = ?", (object_id,))
            conn.commit()

            self.operation_status.emit("delete", True, "Об'єкт видалено")
            self.request_objects_page(1)

        except Exception as e:
            self.operation_status.emit("delete", False, str(e))
        finally:
            conn.close()
