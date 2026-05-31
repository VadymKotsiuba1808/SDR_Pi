"""
Тести для моделі StreamDataChunk.
"""

import numpy as np

from app.models.source_type import SourceType
from app.models.stream_data import StreamDataChunk


def test_stream_data_chunk_serialization():
    """Тест серіалізації та десеріалізації StreamDataChunk."""
    mag = np.array([100, 150, 200], dtype=np.uint8)
    data = {
        "stream_type": "RF",
        "data_magnitude": mag.tolist(),
        "center_freq_hz": 2400e6,
        "sample_rate_hz": 10e6,
        "timestamp": 123456789.0,
    }

    obj = StreamDataChunk.from_dict(data, SourceType.RF)
    assert obj.stream_type == "RF"
    assert np.array_equal(obj.data_magnitude, mag)
    assert obj.timestamp == 123456789.0
    assert obj.to_dict() == data


def test_stream_data_chunk_from_dict_minimal():
    """Тест десеріалізації StreamDataChunk з мінімальними даними."""
    obj = StreamDataChunk.from_dict({}, SourceType.SOUND)
    assert obj.stream_type == SourceType.SOUND
    assert isinstance(obj.data_magnitude, np.ndarray)
    assert obj.center_freq_hz == 0.0
