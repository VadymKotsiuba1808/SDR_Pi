from dataclasses import dataclass, field
from typing import Dict, Optional
import uuid
from datetime import datetime


@dataclass
class DetectionEvent:
    """
    Модель події детекції, отриманої від віддаленого пристрою (Raspberry Pi №1).
    """

    id: str  # Унікальний ID події
    type: str  # "RF" або "Audio"
    object_class: str  # Наприклад: "drone"
    confidence: float  # 0.0 до 1.0
    timestamp: str  # Часова мітка ISO
    distance: int
    angle: float

    @property
    def is_critical(self) -> bool:
        """Логіка визначення важливості (наприклад, поріг впевненості > 0.8)"""
        return self.confidence > 0.8

    @staticmethod
    def from_dict(data: dict) -> "DetectionEvent":
        """Парсинг вхідного словника JSON у об'єкт."""
        return DetectionEvent(
            id=data.get("id", str(uuid.uuid4())),  # Якщо ID не прийшов, генеруємо
            type=data.get("type", "Unknown"),
            object_class=data.get("class", "unknown"),
            confidence=float(data.get("confidence", 0.0)),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            distance=data.get("distance", 0),
            angle=data.get("angle", 0),
        )

    def to_dict(self) -> dict:
        """Серіалізація для відправки (якщо потрібно переслати далі)."""
        return {
            "id": self.id,
            "type": self.type,
            "class": self.object_class,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "distance": self.distance,
            "angle": self.angle,
        }
