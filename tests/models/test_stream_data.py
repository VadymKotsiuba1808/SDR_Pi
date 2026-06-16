"""Модуль з юніт-тестами для моделі StreamDataChunk."""

import numpy as np

from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk


def test_stream_data_chunk_serialization() -> None:
    """Тестує повний цикл серіалізації та десеріалізації StreamDataChunk."""
    mag = np.array([100, 150, 200], dtype=np.uint8)
    data = {
        "stream_type": "RF",
        "data_magnitude": mag.tolist(),
        "center_freq_hz": 2400e6,
        "sample_rate_hz": 10e6,
        "timestamp": 123456789.0,
    }

    obj = StreamDataChunk.from_dict(data, SourceType.RF)

    assert obj.stream_type == "RF", "Stream type should match the input data"
    assert np.array_equal(obj.data_magnitude, mag), "Signal magnitude should match"
    assert obj.timestamp == 123456789.0, "Timestamp should be preserved"
    assert obj.to_dict() == data, (
        "Serialized object should be identical to the input dictionary"
    )


def test_stream_data_chunk_from_dict_minimal() -> None:
    """Тестує десеріалізацію StreamDataChunk з порожнім або мінімальним словником."""
    obj = StreamDataChunk.from_dict({}, SourceType.SOUND)

    assert obj.stream_type == SourceType.SOUND, (
        "Type should match the passed SourceType"
    )
    assert isinstance(obj.data_magnitude, np.ndarray), (
        "Magnitude should be a numpy array even if empty"
    )
    assert obj.center_freq_hz == 0.0, "Default frequency should be 0.0"
