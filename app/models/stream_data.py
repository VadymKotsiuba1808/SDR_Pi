import time
from dataclasses import dataclass

import numpy as np

from app.models.source_type import SourceType


@dataclass
class StreamDataChunk:
    """
    Пакет даних SDR або мікрофона для візуалізації та обробки.

    Транспортує масив потужностей сигналу `data_magnitude` (uint8) та параметри
    спектру (частота, дискретизація). Конвертація: `dB = value - DB_OFFSET`.
    """

    stream_type: SourceType
    data_magnitude: np.ndarray
    center_freq_hz: float
    sample_rate_hz: float
    timestamp: float

    @staticmethod
    def from_dict(data: dict, stream_type: SourceType) -> "StreamDataChunk":
        raw_list = data.get("data_magnitude", [])
        magnitude_array = np.array(raw_list, dtype=np.uint8)

        return StreamDataChunk(
            stream_type=data.get("stream_type", stream_type),
            data_magnitude=magnitude_array,
            center_freq_hz=float(data.get("center_freq_hz", 0)),
            sample_rate_hz=float(data.get("sample_rate_hz", 0)),
            timestamp=float(data.get("timestamp", time.time())),
        )

    def to_dict(self) -> dict:
        return {
            "stream_type": self.stream_type.value
            if hasattr(self.stream_type, "value")
            else self.stream_type,
            "data_magnitude": self.data_magnitude.tolist(),
            "center_freq_hz": self.center_freq_hz,
            "sample_rate_hz": self.sample_rate_hz,
            "timestamp": self.timestamp,
        }
