"""Тести для сервісу очистки даних (CleanerService)."""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.constants import CLEAN_TARGET_NAME
from app.models.settings import CleanRule
from app.services.cleaner_service import CleanerService


@pytest.fixture
def mock_clean_settings() -> MagicMock:
    """Створює макет налаштувань очистки."""
    settings = MagicMock()
    settings.clean_settings = {
        CLEAN_TARGET_NAME.LOGS: CleanRule(enabled=True, days=30),
        CLEAN_TARGET_NAME.SCREENSHOTS: CleanRule(enabled=True, days=7),
    }
    return settings


@pytest.fixture
def temp_dirs(tmp_path: Path) -> dict[str, str]:
    """Створює структуру тимчасових директорій для тестів."""
    logs = tmp_path / "logs"
    bg_logs = tmp_path / "bg_logs"
    media = tmp_path / "media"

    logs.mkdir()
    bg_logs.mkdir()
    media.mkdir()

    return {"logs": str(logs), "bg_logs": str(bg_logs), "media": str(media)}


def test_cleaner_initialization(
    mock_clean_settings: MagicMock, temp_dirs: dict[str, str]
) -> None:
    """Перевірка ініціалізації об'єкта CleanerService та його таргетів."""
    service = CleanerService(mock_clean_settings, paths_override=temp_dirs)

    # Очікується 3 таргети: logs, bg_logs, media (screenshot)
    assert len(service.targets) == 3

    paths = [t.path for t in service.targets]
    assert temp_dirs["logs"] in paths
    assert temp_dirs["bg_logs"] in paths
    assert temp_dirs["media"] in paths


def test_clean_old_files(
    mock_clean_settings: MagicMock, temp_dirs: dict[str, str]
) -> None:
    """Перевірка автоматичного видалення застарілих файлів."""
    service = CleanerService(mock_clean_settings, paths_override=temp_dirs)

    logs_dir = temp_dirs["logs"]

    new_file = os.path.join(logs_dir, "new.jsonl")
    with open(new_file, "w") as f:
        f.write("{}")

    old_file = os.path.join(logs_dir, "old.jsonl")
    with open(old_file, "w") as f:
        f.write("{}")

    # Встановлюємо mtime на 40 днів тому (cutoff = 30)
    old_mtime = time.time() - (40 * 86400)
    os.utime(old_file, (old_mtime, old_mtime))

    service.clean_sdr_data()

    assert os.path.exists(new_file), "New file should not be deleted"
    assert not os.path.exists(old_file), "Old file should be deleted"


def test_clean_wrong_extension(
    mock_clean_settings: MagicMock, temp_dirs: dict[str, str]
) -> None:
    """Перевірка ігнорування файлів з непідтримуваними розширеннями."""
    service = CleanerService(mock_clean_settings, paths_override=temp_dirs)
    logs_dir = temp_dirs["logs"]

    # Файл з непідтримуваним розширенням (.txt)
    txt_file = os.path.join(logs_dir, "old.txt")
    with open(txt_file, "w") as f:
        f.write("test")

    old_mtime = time.time() - (40 * 86400)
    os.utime(txt_file, (old_mtime, old_mtime))

    service.clean_sdr_data()

    assert os.path.exists(txt_file), "File with .txt extension should not be deleted"


def test_clean_disabled_target(temp_dirs: dict[str, str]) -> None:
    """Перевірка поведінки сервісу, коли правило очистки вимкнено."""
    settings = MagicMock()
    settings.clean_settings = {
        CLEAN_TARGET_NAME.LOGS: CleanRule(enabled=False, days=30),
    }

    service = CleanerService(settings, paths_override=temp_dirs)
    assert len(service.targets) == 0, "Targets for disabled rules should not be created"

    logs_dir = temp_dirs["logs"]
    old_file = os.path.join(logs_dir, "old.jsonl")
    with open(old_file, "w") as f:
        f.write("{}")

    old_mtime = time.time() - (40 * 86400)
    os.utime(old_file, (old_mtime, old_mtime))

    service.clean_sdr_data()
    assert os.path.exists(old_file), (
        "Old file should not be deleted if the rule is disabled"
    )
