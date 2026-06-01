import json
import os
import threading
from datetime import datetime
from typing import List

from app.core.constants import BACKGROUND_LOGS_DIR_PATH
from app.models.detection_background import DetectionBackground


class DetectionBackgroundService:
    """Сервіс для збереження та отримання фонового стану детекцій.

    Цей сервіс відповідає за довготривале зберігання "фону" (спектральних даних або
    стану сигналу навколо виявленого об'єкта) у форматі JSON Lines. Ці дані
    необхідні оператору для верифікації спрацювань системи та подальшого аналізу.

    Attributes:
        logs_dir (str): Шлях до директорії, де зберігаються файли логів.
    """

    def __init__(self, logs_dir: str | None = None) -> None:
        """Ініціалізує сервіс збереження фону.

        Створює директорію для логів, якщо вона не існує, та готує механізми
        синхронізації для потокобезпечного запису.

        Args:
            logs_dir: Директорія для логів фону. Якщо None, використовується
                шлях за замовчуванням з констант.
        """
        self.logs_dir = logs_dir or BACKGROUND_LOGS_DIR_PATH
        # Створюємо директорію при ініціалізації, щоб уникнути помилок при записі
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir, exist_ok=True)

        # Використовуємо threading.Lock, оскільки записи можуть надходити з різних
        # потоків обробки мережевих повідомлень.
        self._lock = threading.Lock()

        # Кешуємо назву файлу та дату, щоб не форматувати рядок при кожному виклику add_background
        self._current_date = datetime.now().strftime("%Y-%m-%d")
        self._current_file = os.path.join(
            self.logs_dir, f"backgrounds_{self._current_date}.jsonl"
        )

    def add_background(self, bg: DetectionBackground) -> None:
        """Зберігає новий запис фону у файл поточної дати.

        Реалізує автоматичну ротацію файлів: якщо настала нова доба, створюється
        новий файл логів. Запис виконується у форматі JSONL (один об'єкт на рядок)
        для полегшення потокового читання великих обсягів даних.

        Args:
            bg: Об'єкт даних фону для збереження.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        # Перевіряємо необхідність ротації файлу логів
        if today != self._current_date:
            self._current_date = today
            self._current_file = os.path.join(
                self.logs_dir, f"backgrounds_{self._current_date}.jsonl"
            )

        try:
            with self._lock:
                with open(self._current_file, "a", encoding="utf-8") as f:
                    # ensure_ascii=False зберігає символи Unicode (наприклад, кирилицю) як є,
                    # що робить файл логів зручним для читання людиною.
                    f.write(json.dumps(bg.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            # Використовуємо stderr для критичних помилок запису, щоб не втратити дані
            print(f"[BackgroundService] Write Error: {e}")

    def get_backgrounds_by_target_id(self, target_id: str) -> List[DetectionBackground]:
        """Шукає всі історичні записи фону для конкретного ID детекції.

        Проходить по всіх файлах .jsonl у директорії логів. Це може бути тривалою
        операцією, якщо накопичено багато даних, тому метод зазвичай викликається
        асинхронно або при перегляді історії конкретної цілі.

        Args:
            target_id: Унікальний ідентифікатор цілі (id об'єкта детекції).

        Returns:
            Список знайдених записів, відсортованих за часом (від старіших до новіших).
        """
        results = []

        if not os.path.exists(self.logs_dir):
            return []

        # Збираємо всі файли логів для повного пошуку в історії
        files = [f for f in os.listdir(self.logs_dir) if f.endswith(".jsonl")]

        # Сортуємо назви файлів (вони містять дати), щоб читати їх у хронологічному порядку
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
                            # Перевіряємо, чи належить цей запис фону шуканій цілі
                            if data.get("id") == target_id:
                                results.append(DetectionBackground.from_dict(data))

                        except (json.JSONDecodeError, ValueError):
                            # Пропускаємо пошкоджені рядки, щоб продовжити пошук у решті файлу
                            continue
            except Exception as e:
                print(f"[BackgroundService] Read Error ({filename}): {e}")

        # Додаткове сортування за таймстампом, оскільки всередині файлів
        # або між файлами (при збоях годинника) порядок може бути порушений.
        results.sort(key=lambda x: x.timestamp)
        return results
