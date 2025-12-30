"""
Модель події детекції.
type: Джерело детекції -> ТІЛЬКИ "RF" або "Sound".
object_class: Клас об'єкта -> "drone", "bird", "mavic_3" тощо.
"""

from dataclasses import dataclass
import uuid
from datetime import datetime


@dataclass
class DetectionEvent:

    id: str
    type: str  # "RF" або "Sound"
    name: str
    object_class: str
    confidence: float
    timestamp: str
    distance: int
    angle: float
    frequency: float

    @staticmethod
    def from_dict(data: dict) -> "DetectionEvent":
        """Парсинг вхідного словника JSON у об'єкт."""

        raw_type = data.get("type", "RF")
        if raw_type not in ["RF", "Sound"]:
            raw_type = "RF"

        obj_class = data.get("object_class", data.get("class", "unknown"))

        return DetectionEvent(
            id=data.get("id", str(uuid.uuid4())),
            type=raw_type,
            name=data.get("name", "unknown"),
            object_class=obj_class,
            confidence=float(data.get("confidence", 0.0)),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            distance=int(data.get("distance", 0)),
            angle=float(data.get("angle", 0)),
            frequency=float(data.get("frequency", 0)),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "object_class": self.object_class,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "distance": self.distance,
            "angle": self.angle,
            "frequency": self.frequency,
        }
