"""
Тести для сервісу очистки даних (CleanerService).
"""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.constants import CLEAN_TARGET_NAME
from app.models.settings import CleanRule
from app.services.cleaner_service import CleanerService


@pytest.fixture
def mock_clean_settings():
    """Фікстура для макета налаштувань очистки."""
    settings = MagicMock()
    # Вмикаємо очистку логів (30 днів) та медіа (7 днів)
    settings.clean_settings = {
        CLEAN_TARGET_NAME.LOGS: CleanRule(enabled=True, days=30),
        CLEAN_TARGET_NAME.SCREENSHOTS: CleanRule(enabled=True, days=7),
    }
    return settings


@pytest.fixture
def temp_dirs(tmp_path: Path):
    """Фікстура для тимчасових директорій."""
    logs = tmp_path / "logs"
    bg_logs = tmp_path / "bg_logs"
    media = tmp_path / "media"

    logs.mkdir()
    bg_logs.mkdir()
    media.mkdir()

    return {"logs": str(logs), "bg_logs": str(bg_logs), "media": str(media)}


def test_cleaner_initialization(mock_clean_settings, temp_dirs):
    """Перевірка правильної ініціалізації таргетів."""
    service = CleanerService(mock_clean_settings, paths_override=temp_dirs)

    # Має бути 3 таргети: logs, bg_logs, media (screenshot)
    assert len(service.targets) == 3

    paths = [t.path for t in service.targets]
    assert temp_dirs["logs"] in paths
    assert temp_dirs["bg_logs"] in paths
    assert temp_dirs["media"] in paths


def test_clean_old_files(mock_clean_settings, temp_dirs):
    """Перевірка видалення старих файлів."""
    service = CleanerService(mock_clean_settings, paths_override=temp_dirs)

    logs_dir = temp_dirs["logs"]

    # Створюємо новий файл
    new_file = os.path.join(logs_dir, "new.jsonl")
    with open(new_file, "w") as f:
        f.write("{}")

    # Створюємо старий файл
    old_file = os.path.join(logs_dir, "old.jsonl")
    with open(old_file, "w") as f:
        f.write("{}")

    # Встановлюємо mtime на 40 днів тому (cutoff = 30)
    old_mtime = time.time() - (40 * 86400)
    os.utime(old_file, (old_mtime, old_mtime))

    service.clean_sdr_data()

    assert os.path.exists(new_file)
    assert not os.path.exists(old_file)


def test_clean_wrong_extension(mock_clean_settings, temp_dirs):
    """Перевірка, що файли з іншими розширеннями не видаляються."""
    service = CleanerService(mock_clean_settings, paths_override=temp_dirs)
    logs_dir = temp_dirs["logs"]

    # Старий файл, але з іншим розширенням (наприклад, .txt)
    txt_file = os.path.join(logs_dir, "old.txt")
    with open(txt_file, "w") as f:
        f.write("test")

    old_mtime = time.time() - (40 * 86400)
    os.utime(txt_file, (old_mtime, old_mtime))

    service.clean_sdr_data()

    assert os.path.exists(txt_file)


def test_clean_disabled_target(temp_dirs):
    """Перевірка, що відключені таргети не очищаються."""
    settings = MagicMock()
    # Вимикаємо очистку
    settings.clean_settings = {
        CLEAN_TARGET_NAME.LOGS: CleanRule(enabled=False, days=30),
    }

    service = CleanerService(settings, paths_override=temp_dirs)
    assert len(service.targets) == 0

    logs_dir = temp_dirs["logs"]
    old_file = os.path.join(logs_dir, "old.jsonl")
    with open(old_file, "w") as f:
        f.write("{}")

    old_mtime = time.time() - (40 * 86400)
    os.utime(old_file, (old_mtime, old_mtime))

    service.clean_sdr_data()
    assert os.path.exists(old_file)
