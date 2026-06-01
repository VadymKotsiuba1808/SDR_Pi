import os
import time
from dataclasses import dataclass
from typing import List

from app.core.constants import (
    BACKGROUND_LOGS_DIR_PATH,
    CLEAN_TARGET_NAME,
    LOGS_DIR_PATH,
    MEDIA_DIR_PATH,
)
from app.protocols import CleanerServiceSettings


@dataclass
class CleanTarget:
    """Представляє ціль для очищення (директорію та параметри фільтрації).

    Використовується для групування налаштувань очищення для конкретних типів даних.

    Attributes:
        path (str): Абсолютний шлях до папки, яка підлягає очищенню.
        days (int): Кількість днів, після яких файл вважається застарілим.
        extensions (List[str]): Список розширень файлів для видалення (наприклад, `['.json', '.mp4']`).
    """

    path: str
    days: int
    extensions: List[str]


class CleanerService:
    """Сервіс для автоматичного керування дисковим простором.

    Виконує періодичну очистку застарілих логів, скріншотів та відеозаписів
    на основі налаштувань користувача, щоб забезпечити безперебійну роботу системи
    та запобігти переповненню накопичувача.

    !!! info "Архітектурний контекст"
        Сервіс працює за принципом реєстрації "цілей" (CleanTarget) під час ініціалізації,
        що дозволяє легко розширювати типи даних для очищення.
    """

    def __init__(
        self,
        settings_service: CleanerServiceSettings,
        paths_override: dict | None = None,
    ) -> None:
        """Ініціалізує сервіс очистки.

        Налаштовує шляхи до папок та формує список цілей для очищення на основі
        поточних налаштувань системи.

        Args:
            settings_service (CleanerServiceSettings): Сервіс налаштувань для отримання правил очистки.
            paths_override (dict | None, optional): Словник для заміни стандартних шляхів.
                Використовується переважно в тестах для ізоляції файлової системи та запобігання
                випадковому видаленню реальних даних. Очікує ключі 'logs', 'bg_logs', 'media'.
        """
        super().__init__()
        self.settings_service = settings_service

        self.targets: List[CleanTarget] = []

        # Визначаємо шляхи, враховуючи можливі перевизначення для тестів
        logs_path = (
            paths_override.get("logs", LOGS_DIR_PATH)
            if paths_override
            else LOGS_DIR_PATH
        )
        bg_logs_path = (
            paths_override.get("bg_logs", BACKGROUND_LOGS_DIR_PATH)
            if paths_override
            else BACKGROUND_LOGS_DIR_PATH
        )
        media_path = (
            paths_override.get("media", MEDIA_DIR_PATH)
            if paths_override
            else MEDIA_DIR_PATH
        )

        # Формуємо список цілей на основі активних налаштувань у конфігурації
        clean_settings = self.settings_service.clean_settings

        # Очистка логів основної сесії та фонової детекції
        if CLEAN_TARGET_NAME.LOGS in clean_settings:
            target_settings = clean_settings[CLEAN_TARGET_NAME.LOGS]
            if target_settings.enabled:
                days = target_settings.days
                self.targets.append(CleanTarget(logs_path, days, [".json", ".jsonl"]))
                self.targets.append(
                    CleanTarget(bg_logs_path, days, [".json", ".jsonl"])
                )

        # Очистка скріншотів (статичних зображень)
        if CLEAN_TARGET_NAME.SCREENSHOTS in clean_settings:
            target_settings = clean_settings[CLEAN_TARGET_NAME.SCREENSHOTS]
            if target_settings.enabled:
                days = target_settings.days
                self.targets.append(
                    CleanTarget(media_path, days, [".png", ".jpg", ".jpeg"])
                )

        # Очистка відеозаписів екрану
        if CLEAN_TARGET_NAME.SCREEN_RECORDS in clean_settings:
            target_settings = clean_settings[CLEAN_TARGET_NAME.SCREEN_RECORDS]
            if target_settings.enabled:
                days = target_settings.days
                self.targets.append(
                    CleanTarget(media_path, days, [".mp4", ".avi", ".mkv"])
                )

    def clean_sdr_data(self) -> None:
        """Запускає процес сканування та видалення застарілих файлів.

        Перебирає всі зареєстровані цілі (targets) та видаляє ті файли,
        дата останньої зміни яких старіша за розрахований поріг часу (cutoff).

        !!! warning "Важливо"
            Видалення файлів є незворотнім. Помилки при видаленні окремих файлів
            не переривають загальний процес очищення.

        Returns:
            None
        """
        print("[Cleaner] Запуск очистки старих даних...")
        now = time.time()

        for target in self.targets:
            folder = target.path
            days = target.days
            extensions = target.extensions

            # Розраховуємо часовий поріг: поточний час мінус (кількість днів * секунд у добі)
            cutoff = now - (days * 86400)

            if not os.path.exists(folder):
                continue

            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)

                # Перевіряємо, чи є об'єкт файлом та чи відповідає його розширення цільовим
                if os.path.isfile(filepath) and any(
                    filename.lower().endswith(ext) for ext in extensions
                ):
                    try:
                        file_mtime = os.path.getmtime(filepath)
                        if file_mtime < cutoff:
                            os.remove(filepath)
                            print(f"[Cleaner] Видалено старий файл: {filename}")
                    except Exception as e:
                        # Логуємо помилку, але продовжуємо цикл для інших файлів
                        print(f"[Cleaner] Помилка видалення {filename}: {e}")
