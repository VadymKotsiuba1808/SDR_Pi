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
    filename: str
    label: str


class LogService:
    """
    Надійний сервіс логування, що використовує підхід JSON Lines (NDJSON).
    Це вирішує проблему пошкоджених файлів та втрати даних при крашах.
    """

    def __init__(self, flush_interval: int = 10) -> None:

        self.flush_interval = flush_interval

        self._buffer: List[dict] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        self._current_log_filename: Optional[str] = None
        self._current_session_date: Optional[str] = None

        if not os.path.exists(LOGS_DIR_PATH):
            os.makedirs(LOGS_DIR_PATH, exist_ok=True)

        self._rotate_session_to_date(datetime.now().strftime("%Y-%m-%d"))
        self._start_background_worker()

    def _rotate_session_to_date(self, date_str: str) -> None:
        """Створення нового файлу при зміні дати."""
        if self._current_session_date == date_str and self._current_log_filename:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._current_session_date = date_str

        self._current_log_filename = f"session_{timestamp}.jsonl"

        print(f"[LogService] Session rotated: {self._current_log_filename}")

    def add_log(self, entry: LogEntry) -> None:
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

            if not self._append_batch_to_disk(self._current_log_filename, batch):
                with self._lock:
                    self._buffer = batch + self._buffer
                break

    def _append_batch_to_disk(self, filename: str, batch: List[dict]) -> bool:
        if not batch:
            return True

        path = os.path.join(LOGS_DIR_PATH, filename)
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
        path = os.path.join(LOGS_DIR_PATH, filename)
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
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._stop_event.wait(self.flush_interval):
                break
            self._flush_buffer()

    def stop(self) -> None:
        print("[LogService] Stopping...")
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        self.force_flush()

    def force_flush(self) -> None:
        self._flush_buffer()

    def get_available_sessions(self) -> List[LogSession]:
        sessions = []
        if not os.path.exists(LOGS_DIR_PATH):
            return sessions

        files = [
            f
            for f in os.listdir(LOGS_DIR_PATH)
            if f.endswith(".json") or f.endswith(".jsonl")
        ]
        files.sort(
            key=lambda x: os.path.getmtime(os.path.join(LOGS_DIR_PATH, x)), reverse=True
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
