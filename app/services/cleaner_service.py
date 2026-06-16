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
from app.core.logging_config import get_logger
from app.protocols import CleanerServiceSettings

logger = get_logger(__name__)


@dataclass
class CleanTarget:
    """Представляє ціль для очищення (директорію та параметри фільтрації)."""

    path: str
    days: int
    extensions: List[str]


class CleanerService:
    """Сервіс для автоматичного керування дисковим простором.

    Виконує періодичну очистку застарілих логів, скріншотів та відеозаписів
    на основі налаштувань користувача, щоб забезпечити безперебійну роботу системи.

    !!! info "Архітектурний контекст"
        Сервіс працює за принципом реєстрації "цілей" (CleanTarget) під час ініціалізації.
    """

    def __init__(
        self,
        settings_service: CleanerServiceSettings,
        paths_override: dict | None = None,
    ) -> None:
        super().__init__()
        self.settings_service = settings_service
        self.targets: List[CleanTarget] = []

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

    def clean_sdr_data(self) -> None:
        logger.info("Starting cleanup of old data...")
        now = time.time()

        for target in self.targets:
            folder = target.path
            days = target.days
            extensions = target.extensions

            # Часовий поріг: поточний час мінус (дні * секунд у добі)
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
                            logger.info(f"Deleted old file: {filename}")
                    except Exception as e:
                        logger.error(f"Error deleting {filename}: {e}")
