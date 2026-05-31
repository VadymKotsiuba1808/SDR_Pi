"""
Тести для моделей спектральних даних (DetectionBackground, SpectralData).
"""

import numpy as np

from app.models.detection_background import DetectionBackground, SpectralData


def test_spectral_data_serialization():
    """Тест серіалізації та десеріалізації SpectralData."""
    mag = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    data = {
        "center_freq_hz": 2400e6,
        "sample_rate_hz": 20e6,
        "duration_sec": 0.1,
        "data_magnitude": mag.tolist(),
    }

    obj = SpectralData.from_dict(data)
    assert obj.center_freq_hz == 2400e6
    assert np.array_equal(obj.data_magnitude, mag)
    assert obj.to_dict() == data


def test_detection_background_serialization():
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
    assert obj.id == "bg-001"
    assert obj.spectral_data.center_freq_hz == 433e6
    assert obj.to_dict() == data
