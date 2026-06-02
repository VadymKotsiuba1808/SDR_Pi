import uuid
from dataclasses import dataclass
from datetime import datetime

import numpy as np


@dataclass
class SpectralData:
    """Дані для спектрального аналізу.

    Містить параметри прийому та матрицю амплітуд для побудови
    спектрограм та виявлення сигналів.

    Attributes:
        center_freq_hz: Центральна частота прийому (Гц).
        sample_rate_hz: Смуга пропускання (Гц).
        duration_sec: Тривалість запису (сек).
        data_magnitude: Матриця амплітуд (спектрограма) типу uint8.
    """

    center_freq_hz: float
    sample_rate_hz: float
    duration_sec: float
    data_magnitude: np.ndarray

    @staticmethod
    def from_dict(data: dict) -> "SpectralData":
        mag_data = data.get("data_magnitude", [])
        if isinstance(mag_data, list):
            mag_data = np.array(mag_data, dtype=np.uint8)

        return SpectralData(
            center_freq_hz=float(data.get("center_freq_hz", 0)),
            sample_rate_hz=float(data.get("sample_rate_hz", 0)),
            duration_sec=float(data.get("duration_sec", 0)),
            data_magnitude=mag_data,
        )

    def to_dict(self) -> dict:
        return {
            "center_freq_hz": self.center_freq_hz,
            "sample_rate_hz": self.sample_rate_hz,
            "duration_sec": self.duration_sec,
            "data_magnitude": (
                self.data_magnitude.tolist()
                if isinstance(self.data_magnitude, np.ndarray)
                else self.data_magnitude
            ),
        }


@dataclass
class DetectionBackground:
    """Фоновий спектр радіочастотного оточення.

    Представляє зріз фону в певний момент часу для виявлення аномалій.

    Attributes:
        id: Унікальний ідентифікатор фонового запису.
        timestamp: Часова мітка створення запису (ISO).
        spectral_data: Спектральні дані фону.
    """

    id: str
    timestamp: str
    spectral_data: SpectralData

    @staticmethod
    def from_dict(data: dict) -> "DetectionBackground":
        spec_raw = data.get("spectral_data", {})
        spectral_obj = SpectralData.from_dict(spec_raw)

        return DetectionBackground(
            id=data.get("id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            spectral_data=spectral_obj,
        )

    def to_dict(self) -> dict:
        spec_dict = self.spectral_data.to_dict()

        return {"id": self.id, "timestamp": self.timestamp, "spectral_data": spec_dict}
