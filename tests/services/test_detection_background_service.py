"""Юніт-тести для перевірки функціональності DetectionBackgroundService."""

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
    logs_dir = tmp_path / "bg_logs"
    logs_dir.mkdir()
    return str(logs_dir)


@pytest.fixture
def bg_service(temp_logs_dir: str) -> DetectionBackgroundService:
    return DetectionBackgroundService(logs_dir=temp_logs_dir)


def create_mock_background(target_id: str) -> DetectionBackground:
    """Створює тестовий об'єкт DetectionBackground із фіктивними даними."""
    spec = SpectralData(
        center_freq_hz=915e6,
        sample_rate_hz=10e6,
        duration_sec=1.0,
        data_magnitude=np.zeros(10, dtype=np.uint8),
    )
    return DetectionBackground(
        id=target_id, timestamp=datetime.now().isoformat(), spectral_data=spec
    )


def test_add_background_and_retrieve(
    bg_service: DetectionBackgroundService, temp_logs_dir: str
) -> None:
    """Перевіряє успішне додавання фонових даних та їх подальше отримання за ID."""
    bg1 = create_mock_background("target_A")
    bg2 = create_mock_background("target_B")

    # Arrange & Act
    bg_service.add_background(bg1)
    bg_service.add_background(bg2)

    # Assert: Перевіряємо фізичну наявність файлу логів
    files = os.listdir(temp_logs_dir)
    assert len(files) == 1, f"Expected 1 log file, found {len(files)}"
    assert files[0].endswith(".jsonl"), "Log file should have .jsonl extension"

    # Assert: Отримуємо та перевіряємо дані для target_A
    results_a = bg_service.get_backgrounds_by_target_id("target_A")
    assert len(results_a) == 1, f"Expected 1 record for target_A, got {len(results_a)}"
    assert results_a[0].id == "target_A", (
        "ID mismatch for the retrieved background for target_A"
    )

    # Assert: Отримуємо та перевіряємо дані для target_B
    results_b = bg_service.get_backgrounds_by_target_id("target_B")
    assert len(results_b) == 1, f"Expected 1 record for target_B, got {len(results_b)}"
    assert results_b[0].id == "target_B", (
        "ID mismatch for the retrieved background for target_B"
    )


def test_get_backgrounds_non_existent_id(
    bg_service: DetectionBackgroundService,
) -> None:
    """Перевіряє поведінку сервісу при запиті даних для неіснуючого ID."""
    bg_service.add_background(create_mock_background("id1"))

    # Act
    results = bg_service.get_backgrounds_by_target_id("unknown")

    # Assert
    assert len(results) == 0, "Expected an empty list for a non-existent target ID"


def test_multiple_files_handling(
    bg_service: DetectionBackgroundService, temp_logs_dir: str
) -> None:
    """Перевіряє здатність сервісу зчитувати дані з декількох файлів логів."""
    # Arrange: Створюємо файл за "минулу дату" вручну, щоб імітувати ротацію логів
    yesterday = "2020-01-01"
    old_file = os.path.join(temp_logs_dir, f"backgrounds_{yesterday}.jsonl")
    bg_old = create_mock_background("target_1")
    bg_old.timestamp = "2020-01-01T10:00:00"

    with open(old_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(bg_old.to_dict()) + "\n")

    # Act: Додаємо новий запис через сервіс (створить новий файл за сьогодні)
    bg_new = create_mock_background("target_1")
    bg_service.add_background(bg_new)

    # Act: Запитуємо всі дані для цілі
    results = bg_service.get_backgrounds_by_target_id("target_1")

    # Assert: Сервіс має знайти обидва записи, незалежно від файлу
    assert len(results) == 2, (
        f"Expected 2 records from different files, got {len(results)}"
    )

    # Assert: Перевіряємо сортування за часом (від старіших до новіших)
    assert results[0].timestamp < results[1].timestamp, (
        "Background records should be sorted by timestamp"
    )
