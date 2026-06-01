import time
from dataclasses import dataclass

import numpy as np

from app.models.source_type import SourceType


@dataclass
class StreamDataChunk:
    """
    Представляє пакет даних, отриманий від SDR або мікрофона в реальному часі.

    Цей клас використовується для транспортування необроблених даних про потужність
    сигналу разом із метаданими, необхідними для їх візуалізації та подальшої обробки.

    Attributes:
        stream_type (SourceType): Тип джерела даних (SDR або мікрофон).
        data_magnitude (np.ndarray): Масив значень потужності сигналу (uint8).
            Значення переводяться у дБ за формулою: dB = value_uint8 - DB_OFFSET.
        center_freq_hz (float): Центральна частота налаштування SDR у Герцах.
        sample_rate_hz (float): Частота дискретизації у Герцах. Визначає ширину
            смуги огляду (bandwidth).
        timestamp (float): UNIX-час отримання пакету даних.
    """

    stream_type: SourceType
    data_magnitude: np.ndarray
    center_freq_hz: float
    sample_rate_hz: float
    timestamp: float

    @staticmethod
    def from_dict(data: dict, stream_type: SourceType) -> "StreamDataChunk":
        # Перетворюємо список на numpy array з типом uint8 для економії пам'яті
        # та оптимізації подальших математичних операцій.
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
