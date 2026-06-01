import json
import os
import threading
from datetime import datetime
from typing import List

from app.core.constants import BACKGROUND_LOGS_DIR_PATH
from app.models.detection_background import DetectionBackground


class DetectionBackgroundService:
    """
    Сервіс для збереження та отримання фонового стану детекцій.

    Відповідає за логування "фону" (сигналу навколо виявленого об'єкта)
    у форматі JSON Lines для подальшого аналізу оператором.
    """

    def __init__(self, logs_dir: str | None = None):
        """
        Ініціалізує сервіс збереження фону.

        Args:
            logs_dir (str | None): Директорія для логів фону.
        """
        self.logs_dir = logs_dir or BACKGROUND_LOGS_DIR_PATH
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir, exist_ok=True)
        self._lock = threading.Lock()

        self._current_date = datetime.now().strftime("%Y-%m-%d")
        self._current_file = os.path.join(
            self.logs_dir, f"backgrounds_{self._current_date}.jsonl"
        )

    def add_background(self, bg: DetectionBackground) -> None:
        """
        Зберігає новий запис фону у файл поточної дати.

        Args:
            bg (DetectionBackground): Об'єкт даних фону.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._current_date:
            self._current_date = today
            self._current_file = os.path.join(
                self.logs_dir, f"backgrounds_{self._current_date}.jsonl"
            )

        try:
            with self._lock:
                with open(self._current_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(bg.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[BackgroundService] Write Error: {e}")

    def get_backgrounds_by_target_id(self, target_id: str) -> List[DetectionBackground]:
        """
        Шукає всі історичні записи фону для конкретного ID детекції.

        Args:
            target_id (str): Унікальний ідентифікатор цілі.

        Returns:
            List[DetectionBackground]: Список знайдених записів, відсортованих за часом.
        """
        results = []

        if not os.path.exists(self.logs_dir):
            return []

        files = [f for f in os.listdir(self.logs_dir) if f.endswith(".jsonl")]

        files.sort()

        for filename in files:
            path = os.path.join(self.logs_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            data = json.loads(line)

                            if data.get("id") == target_id:
                                results.append(DetectionBackground.from_dict(data))

                        except (json.JSONDecodeError, ValueError):
                            continue
            except Exception as e:
                print(f"[BackgroundService] Read Error ({filename}): {e}")

        results.sort(key=lambda x: x.timestamp)
        return results
