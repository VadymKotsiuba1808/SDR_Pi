"""
Тести для сервісу фонових детекцій (DetectionBackgroundService).
"""

import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from app.models.detection_background import DetectionBackground, SpectralData
from app.services.detection_background_service import DetectionBackgroundService


@pytest.fixture
def temp_logs_dir(tmp_path: Path) -> str:
    """Фікстура для тимчасової директорії логів."""
    logs_dir = tmp_path / "bg_logs"
    logs_dir.mkdir()
    return str(logs_dir)


@pytest.fixture
def bg_service(temp_logs_dir: str):
    """Фікстура для ініціалізації DetectionBackgroundService."""
    return DetectionBackgroundService(logs_dir=temp_logs_dir)


def create_mock_background(target_id: str):
    """Допоміжна функція для створення об'єкта фону."""
    spec = SpectralData(
        center_freq_hz=915e6,
        sample_rate_hz=10e6,
        duration_sec=1.0,
        data_magnitude=np.zeros(10, dtype=np.uint8),
    )
    return DetectionBackground(
        id=target_id, timestamp=datetime.now().isoformat(), spectral_data=spec
    )


def test_add_background_and_retrieve(bg_service, temp_logs_dir):
    """Тест додавання та отримання фонових даних за ID."""
    bg1 = create_mock_background("target_A")
    bg2 = create_mock_background("target_B")

    bg_service.add_background(bg1)
    bg_service.add_background(bg2)

    # Перевіряємо, що файл створився
    files = os.listdir(temp_logs_dir)
    assert len(files) == 1, f"Expected 1 log file, found {len(files)}"
    assert files[0].endswith(".jsonl"), "Log file should have .jsonl extension"

    # Отримуємо дані для конкретного ID
    results_a = bg_service.get_backgrounds_by_target_id("target_A")
    assert len(results_a) == 1, (
        f"Expected 1 background for target_A, got {len(results_a)}"
    )
    assert results_a[0].id == "target_A", (
        "Retrieved background ID mismatch for target_A"
    )

    results_b = bg_service.get_backgrounds_by_target_id("target_B")
    assert len(results_b) == 1, (
        f"Expected 1 background for target_B, got {len(results_b)}"
    )
    assert results_b[0].id == "target_B", (
        "Retrieved background ID mismatch for target_B"
    )


def test_get_backgrounds_non_existent_id(bg_service):
    """Тест отримання даних для неіснуючого ID."""
    bg_service.add_background(create_mock_background("id1"))
    results = bg_service.get_backgrounds_by_target_id("unknown")
    assert len(results) == 0, "Expected 0 results for non-existent target ID"


def test_multiple_files_handling(bg_service, temp_logs_dir):
    """Тест зчитування даних з декількох файлів (імітація різних дат)."""
    # Створюємо файл за "вчора" вручну
    yesterday = "2020-01-01"
    old_file = os.path.join(temp_logs_dir, f"backgrounds_{yesterday}.jsonl")
    bg_old = create_mock_background("target_1")
    bg_old.timestamp = "2020-01-01T10:00:00"

    with open(old_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(bg_old.to_dict()) + "\n")

    # Додаємо сьогоднішній фон через сервіс
    bg_new = create_mock_background("target_1")
    bg_service.add_background(bg_new)

    # Сервіс має знайти обидва записи
    results = bg_service.get_backgrounds_by_target_id("target_1")
    assert len(results) == 2, (
        f"Expected 2 backgrounds across multiple files, got {len(results)}"
    )
    # Сортування за часом
    assert results[0].timestamp < results[1].timestamp, (
        "Backgrounds should be sorted by timestamp"
    )
