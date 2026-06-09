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
    path: str
    days: int
    extensions: List[str]


class CleanerService:
    """
    Клас для автоматичної очистки пам'яті.
    """

    def __init__(
        self,
        settings_service: CleanerServiceSettings,
        paths_override: dict | None = None,
    ):
        super().__init__()
        self.settings_service = settings_service

        self.targets: List[CleanTarget] = []

        # Використовуємо кастомні шляхи, якщо вони передані (для тестів)
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

        clean_settings = self.settings_service.clean_settings
        if CLEAN_TARGET_NAME.LOGS in clean_settings:
            target_settings = clean_settings[CLEAN_TARGET_NAME.LOGS]
            if target_settings.enabled:
                days = target_settings.days
                self.targets.append(CleanTarget(logs_path, days, [".json", ".jsonl"]))
                self.targets.append(
                    CleanTarget(bg_logs_path, days, [".json", ".jsonl"])
                )

        if CLEAN_TARGET_NAME.SCREENSHOTS in clean_settings:
            target_settings = clean_settings[CLEAN_TARGET_NAME.SCREENSHOTS]
            if target_settings.enabled:
                days = target_settings.days
                self.targets.append(
                    CleanTarget(media_path, days, [".png", ".jpg", ".jpeg"])
                )

        if CLEAN_TARGET_NAME.SCREEN_RECORDS in clean_settings:
            target_settings = clean_settings[CLEAN_TARGET_NAME.SCREEN_RECORDS]
            if target_settings.enabled:
                days = target_settings.days
                self.targets.append(
                    CleanTarget(media_path, days, [".mp4", ".avi", ".mkv"])
                )

    def clean_sdr_data(self):
        print("[Cleaner] Запуск очистки старих даних...")
        now = time.time()

        for target in self.targets:
            folder = target.path
            days = target.days
            extensions = target.extensions
            cutoff = now - (days * 86400)

            if not os.path.exists(folder):
                continue

            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)

                if os.path.isfile(filepath) and any(
                    filename.lower().endswith(ext) for ext in extensions
                ):
                    try:
                        file_mtime = os.path.getmtime(filepath)
                        if file_mtime < cutoff:
                            os.remove(filepath)
                            print(f"[Cleaner] Видалено старий файл: {filename}")
                    except Exception as e:
                        print(f"[Cleaner] Помилка видалення {filename}: {e}")
