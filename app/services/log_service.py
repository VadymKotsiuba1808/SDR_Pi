import os
import json
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

from app.models.log_entries import LogEntry


@dataclass
class LogSession:
    """Модель для відображення доступної сесії в списку."""

    filename: str
    label: str


class LogService:
    """Сервіс для роботи з json файлами сесій, у яких містяться логи"""

    def __init__(self, logs_dir: str = "logs") -> None:
        self.logs_dir = logs_dir

        if not os.path.exists(self.logs_dir):
            print(
                f"[LogService] Warning: Logs directory '{self.logs_dir}' does not exist."
            )

    def get_available_sessions(self) -> List[LogSession]:
        sessions: List[LogSession] = []

        if not os.path.exists(self.logs_dir):
            return sessions

        try:
            files = [f for f in os.listdir(self.logs_dir) if f.endswith(".json")]

            files.sort(
                key=lambda x: os.path.getmtime(os.path.join(self.logs_dir, x)),
                reverse=True,
            )

            for f in files:
                label = f
                if f.startswith("session_"):
                    try:
                        timestr = f.replace("session_", "").replace(".json", "")
                        dt = datetime.strptime(timestr, "%Y-%m-%d_%H-%M-%S")
                        label = dt.strftime("%d.%m.%Y %H:%M")
                    except ValueError:
                        pass

                sessions.append(LogSession(filename=f, label=label))

            print(f"[LogService] Found {len(sessions)} sessions in '{self.logs_dir}'.")
            return sessions

        except Exception as e:
            print(f"[LogService] Error scanning logs directory: {e}")
            return []

    def load_session_data(self, filename: str) -> List[LogEntry]:
        full_path = os.path.join(self.logs_dir, filename)

        if not os.path.exists(full_path):
            print(f"[LogService] Error: File not found at {full_path}")
            return []

        try:
            print(f"[LogService] Loading session: {filename}...")

            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                print(
                    f"[LogService] Invalid format in {filename}: expected a JSON list."
                )
                return []

            entries = [LogEntry.from_dict(item) for item in data]

            entries.sort(key=lambda x: x.timestamp)

            print(f"[LogService] Successfully loaded {len(entries)} entries.")
            return entries

        except json.JSONDecodeError as e:
            print(f"[LogService] JSON Decode Error in {filename}: {e}")
            return []
        except Exception as e:
            print(f"[LogService] Unexpected error loading session: {e}")
            return []
