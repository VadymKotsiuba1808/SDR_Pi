import os
import json
from datetime import datetime

from app.models.log_entries import LogEntry


class LogService:
    def __init__(self, logs_dir="logs"):
        self.logs_dir = logs_dir

    def get_available_sessions(self):
        """
        Сканує папку logs_dir і повертає список реальних .json файлів.
        """
        sessions = []
        if not os.path.exists(self.logs_dir):
            return sessions

        files = [f for f in os.listdir(self.logs_dir) if f.endswith(".json")]
        files.sort(
            key=lambda x: os.path.getmtime(os.path.join(self.logs_dir, x)), reverse=True
        )

        for f in files:

            label = f
            try:
                if f.startswith("session_"):
                    timestr = f.replace("session_", "").replace(".json", "")
                    dt = datetime.strptime(timestr, "%Y-%m-%d_%H-%M-%S")
                    label = dt.strftime("%d.%m.%Y %H:%M")
            except:
                pass

            sessions.append({"filename": f, "label": label})

        return sessions

    def load_session_data(self, filename: str) -> list[LogEntry]:
        """
        Читає реальний JSON файл і перетворює його у список об'єктів LogEntry.
        """
        full_path = os.path.join(self.logs_dir, filename)

        if not os.path.exists(full_path):
            print(f"[LogService] File not found: {full_path}")
            return []

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                print("[LogService] Invalid JSON format: expected a list.")
                return []

            entries = [LogEntry.from_dict(item) for item in data]

            entries.sort(key=lambda x: x.timestamp)

            print(f"[LogService] Loaded {len(entries)} entries from {filename}")
            return entries

        except json.JSONDecodeError as e:
            print(f"[LogService] JSON Error: {e}")
            return []
        except Exception as e:
            print(f"[LogService] Error loading session: {e}")
            return []
