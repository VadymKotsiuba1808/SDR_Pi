from dataclasses import dataclass
import numpy as np
import time

from app.models.source_type import SourceType


@dataclass
class StreamDataChunk:
    """
    Пакет даних, що приходить від SDR або мікрофона в реальному часі.
    """

    stream_type: str  # з SourceType
    # Тепер тут uint8.
    # Значення 0 = -127 dB (шум), Значення 255 = +128 dB (теоретичний максимум).
    # Тобто: dB = value - 127
    data_magnitude: np.ndarray
    center_freq_hz: float  # Центральна частота (для RF)
    sample_rate_hz: float  # Частота дискретизації. Визначає ширину смуги огляду.
    timestamp: float  # Час отримання пакету

    @staticmethod
    def from_dict(data: dict, type: str) -> "StreamDataChunk":
        """Парсинг вхідного словника JSON у об'єкт."""

        raw_list = data.get("data_magnitude", [])
        magnitude_array = np.array(raw_list, dtype=np.uint8)

        return StreamDataChunk(
            stream_type=data.get("stream_type", type),
            data_magnitude=magnitude_array,
            center_freq_hz=float(data.get("center_freq_hz", 0)),
            sample_rate_hz=float(data.get("sample_rate_hz", 0)),
            timestamp=float(data.get("timestamp", time.time())),
        )

    def to_dict(self) -> dict:
        return {
            "stream_type": self.stream_type,
            "data_magnitude": self.data_magnitude.tolist(),
            "center_freq_hz": self.center_freq_hz,
            "sample_rate_hz": self.sample_rate_hz,
            "timestamp": self.timestamp,
        }
