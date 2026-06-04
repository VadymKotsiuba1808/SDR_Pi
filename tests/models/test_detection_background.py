"""Модуль для тестування моделей фонового спектру."""

import numpy as np

from app.models.detection_background import DetectionBackground, SpectralData


def test_spectral_data_serialization() -> None:
    """Тест серіалізації та десеріалізації SpectralData."""
    mag = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    data = {
        "center_freq_hz": 2400e6,
        "sample_rate_hz": 20e6,
        "duration_sec": 0.1,
        "data_magnitude": mag.tolist(),
    }

    obj = SpectralData.from_dict(data)

    assert obj.center_freq_hz == 2400e6, "Center frequency should match the input data"
    assert np.array_equal(obj.data_magnitude, mag), (
        "Magnitude matrix should be identical to the original array"
    )
    assert obj.to_dict() == data, "Resulting dictionary should match the input data"


def test_detection_background_serialization() -> None:
    """Тест серіалізації та десеріалізації DetectionBackground."""
    spec_data = {
        "center_freq_hz": 433e6,
        "sample_rate_hz": 2e6,
        "duration_sec": 1.0,
        "data_magnitude": [[10, 20]],
    }
    data = {
        "id": "bg-001",
        "timestamp": "2026-05-30T11:00:00",
        "spectral_data": spec_data,
    }

    obj = DetectionBackground.from_dict(data)

    assert obj.id == "bg-001", "Background record ID should be preserved"
    assert obj.spectral_data.center_freq_hz == 433e6, (
        "Nested spectral data should be correctly initialized"
    )
    assert obj.to_dict() == data, (
        "Full serialization cycle should return an identical dictionary"
    )
