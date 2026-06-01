import uuid
from dataclasses import dataclass
from datetime import datetime

from app.models.source_type import SourceType


@dataclass
class DetectionEvent:
    """
    Представляє подію виявлення об'єкта.

    Атрибути:
        id (str): Унікальний ідентифікатор події.
        type (SourceType): Джерело детекції (радіочастотне або акустичне).
        name (str): Назва об'єкта або сигналу.
        object_class (str): Клас об'єкта (наприклад, "drone", "bird").
        confidence (float): Впевненість системи у виявленні (0.0 - 1.0).
        timestamp (str): ISO-мітка часу події.
        distance_km (float): Відстань до об'єкта в кілометрах.
        angle (float): Кут (азимут) на об'єкт у градусах.
        frequency_hz (float): Частота сигналу в Герцах.
    """

    id: str
    type: SourceType
    name: str
    object_class: str
    confidence: float
    timestamp: str
    distance_km: float
    angle: float
    frequency_hz: float

    @staticmethod
    def from_dict(data: dict) -> "DetectionEvent":
        """Парсинг вхідного словника JSON у об'єкт."""

        raw_type_val = data.get("type", SourceType.RF)
        raw_type = SourceType.RF
        if isinstance(raw_type_val, SourceType):
            raw_type = raw_type_val
        elif isinstance(raw_type_val, str):
            try:
                raw_type = SourceType(raw_type_val)
            except ValueError:
                try:
                    raw_type = SourceType[raw_type_val.upper()]
                except KeyError:
                    raw_type = SourceType.RF
        else:
            raw_type = SourceType.RF
        obj_class = data.get("object_class", data.get("class", "unknown"))

        return DetectionEvent(
            id=data.get("id", str(uuid.uuid4())),
            type=raw_type,
            name=data.get("name", "unknown"),
            object_class=obj_class,
            confidence=float(data.get("confidence", 0.0)),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            distance_km=float(data.get("distance_km", 0)),
            angle=float(data.get("angle", 0)),
            frequency_hz=float(data.get("frequency_hz", 0)),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value if hasattr(self.type, "value") else self.type,
            "name": self.name,
            "object_class": self.object_class,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "distance_km": self.distance_km,
            "angle": self.angle,
            "frequency_hz": self.frequency_hz,
        }
