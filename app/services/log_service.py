import json
import os
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import groupby
from typing import List, Optional

from app.core.constants import LOGS_DIR_PATH
from app.models.log_entries import LogEntry


@dataclass
class LogSession:
    """
    Представляє метадані сесії логування.

    Цей клас використовується для відображення списку доступних сесій у GUI
    та забезпечення зв'язку між файлом на диску та його зрозумілою назвою.

    Attributes:
        filename: Назва файлу логу на диску (наприклад, 'session_2024-06-01_12-00-00.jsonl').
        label: Людиночитана мітка сесії, відформатована для відображення користувачеві.
    """

    filename: str
    label: str


class LogService:
    """
    Сервіс для надійного та асинхронного логування подій у форматі JSON Lines (NDJSON).

    Цей сервіс забезпечує потокобезпечне накопичення логів у буфері та їх періодичне
    скидання на диск у фоновому потоці. Це мінімізує вплив дискових операцій на
    продуктивність основного UI-потоку.

    Особливості:
        - Потокобезпечність через `threading.Lock`.
        - Автоматична ротація файлів при зміні календарної дати.
        - Стійкість до помилок запису (повернення даних у буфер).
        - Підтримка формату NDJSON для легкого парсингу та стійкості до пошкоджень.

    Args:
        flush_interval: Інтервал (у секундах) між автоматичними скиданнями буфера на диск.
        logs_dir: Шлях до директорії, де зберігатимуться файли логів. Якщо None,
            використовується шлях за замовчуванням з констант.
    """

    def __init__(
        self, flush_interval: int = 10, logs_dir: Optional[str] = None
    ) -> None:
        self.flush_interval = flush_interval
        self.logs_dir = logs_dir or LOGS_DIR_PATH

        self._buffer: List[dict] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        self._current_log_filename: Optional[str] = None
        self._current_session_date: Optional[str] = None

        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir, exist_ok=True)

        self._rotate_session_to_date(datetime.now().strftime("%Y-%m-%d"))
        self._start_background_worker()

    def _rotate_session_to_date(self, date_str: str) -> None:
        """
        Створює новий файл сесії логування при зміні дати або при ініціалізації.

        Це необхідно для зручного групування логів за днями та уникнення створення
        надто великих файлів.

        Args:
            date_str: Рядок дати у форматі 'YYYY-MM-DD'.
        """
        if self._current_session_date == date_str and self._current_log_filename:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._current_session_date = date_str

        self._current_log_filename = f"session_{timestamp}.jsonl"

        print(f"[LogService] Session rotated: {self._current_log_filename}")

    def add_log(self, entry: LogEntry) -> None:
        """
        Додає новий запис логу до внутрішнього буфера.

        Цей метод є неблокуючим відносно дискових операцій. Запис фактично
        буде здійснено під час наступного циклу фонового воркера.

        Args:
            entry: Об'єкт LogEntry, який потрібно зберегти.
        """
        try:
            if hasattr(entry, "to_dict"):
                data = entry.to_dict()
            else:
                data = asdict(entry)

            with self._lock:
                self._buffer.append(data)

        except Exception as e:
            print(f"[LogService] Error adding log: {e}")

    def _flush_buffer(self) -> None:
        """
        Скидає вміст буфера на диск.

        Метод сортує логі за часом, групує їх за датами (якщо в буфері є логі
        за різні дні) та записує у відповідні файли сесій.

        !!! note
            Якщо запис на диск не вдався, дані повертаються на початок буфера,
            щоб спробувати записати їх знову під час наступного циклу.
        """
        with self._lock:
            if not self._buffer:
                return

            self._buffer.sort(key=lambda x: x.get("timestamp", ""))

            logs_to_write = self._buffer[:]
            self._buffer.clear()

        def get_date_key(log: dict) -> str:
            ts = log.get("timestamp", "")
            return ts[:10] if len(ts) >= 10 else datetime.now().strftime("%Y-%m-%d")

        for log_date, group in groupby(logs_to_write, key=get_date_key):
            batch = list(group)

            if log_date != self._current_session_date:
                self._rotate_session_to_date(log_date)

            if not self._current_log_filename:
                break

            if not self._append_batch_to_disk(self._current_log_filename, batch):
                # Повертаємо невдалий батч назад у буфер
                with self._lock:
                    self._buffer = batch + self._buffer
                break

    def _append_batch_to_disk(self, filename: str, batch: List[dict]) -> bool:
        """
        Безпосередньо дописує батч записів у файл на диску.

        Args:
            filename: Назва файлу в директорії логів.
            batch: Список словників з даними логів.

        Returns:
            bool: True, якщо запис успішний, False у разі помилки введення/виведення.
        """
        if not batch:
            return True

        path = os.path.join(self.logs_dir, filename)
        try:
            with open(path, "a", encoding="utf-8") as f:
                for entry in batch:
                    json_str = json.dumps(entry, ensure_ascii=False)
                    f.write(json_str + "\n")
            return True
        except Exception as e:
            print(f"[LogService] Disk write error: {e}")
            return False

    def load_session_data(self, filename: str) -> List[LogEntry]:
        """
        Завантажує та десеріалізує дані логів з конкретного файлу сесії.

        Використовується для перегляду історії логів у GUI. Пошкоджені рядки
        ігноруються для забезпечення стійкості.

        Args:
            filename: Назва файлу для завантаження.

        Returns:
            Список об'єктів `LogEntry`, відсортованих за часом.
        """
        path = os.path.join(self.logs_dir, filename)
        if not os.path.exists(path):
            return []

        entries = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entries.append(LogEntry.from_dict(data))
                    except json.JSONDecodeError:
                        print(
                            f"[LogService] Warning: Skipping corrupted line in {filename}"
                        )
                        continue

            entries.sort(key=lambda x: x.timestamp)
            return entries

        except Exception as e:
            print(f"[LogService] Read error: {e}")
            return []

    def _start_background_worker(self) -> None:
        """Запускає фоновий потік для періодичного збереження логів."""
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _worker_loop(self) -> None:
        """Головний цикл фонового воркера."""
        while not self._stop_event.is_set():
            # Очікуємо інтервал або подію зупинки
            if self._stop_event.wait(self.flush_interval):
                break
            self._flush_buffer()

    def stop(self) -> None:
        """
        Коректно зупиняє сервіс логування.

        Гарантує, що всі логі, які залишилися в буфері, будуть записані на диск
        перед завершенням роботи.
        """
        print("[LogService] Stopping...")
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        self.force_flush()

    def force_flush(self) -> None:
        """Примусово скидає поточний буфер на диск незалежно від таймера."""
        self._flush_buffer()

    def get_available_sessions(self) -> List[LogSession]:
        """
        Отримує список усіх доступних файлів сесій з диска.

        Файли сортуються за часом останньої зміни (новіші попереду). Назви файлів
        перетворюються у зручні мітки часу.

        Returns:
            Список об'єктів `LogSession` для відображення в інтерфейсі.
        """
        sessions: List[LogSession] = []
        if not os.path.exists(self.logs_dir):
            return sessions

        files = [
            f
            for f in os.listdir(self.logs_dir)
            if f.endswith(".json") or f.endswith(".jsonl")
        ]
        files.sort(
            key=lambda x: os.path.getmtime(os.path.join(self.logs_dir, x)), reverse=True
        )

        for f in files:
            label = f
            if f.startswith("session_"):
                try:
                    name_part = f.replace("session_", "").split(".")[0]
                    dt = datetime.strptime(name_part, "%Y-%m-%d_%H-%M-%S")
                    label = dt.strftime("%d.%m.%Y %H:%M")
                except ValueError:
                    pass
            sessions.append(LogSession(filename=f, label=label))
        return sessions
