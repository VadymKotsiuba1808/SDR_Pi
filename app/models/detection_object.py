from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class DetectionObject:
    """
    Модель об'єкта для бази даних.
    При створенні нового об'єкта id = None.
    """

    name: str
    object_class: str
    id: Optional[str] = None
    is_dangerous: bool = False

    rf_params: Optional[Dict[str, Any]] = None
    audio_params: Optional[Dict[str, Any]] = None

    @staticmethod
    def from_dict(data: dict) -> "DetectionObject":
        return DetectionObject(
            id=data.get("id"),  # Може бути None
            name=data.get("name", "Unnamed"),
            object_class=data.get("object_class", "unknown"),
            is_dangerous=bool(data.get("is_dangerous", False)),
            rf_params=data.get("rf_params"),
            audio_params=data.get("audio_params"),
        )

    def to_dict(self) -> dict:
        """
        Серіалізація.
        """
        data = {
            "name": self.name,
            "object_class": self.object_class,
            "is_dangerous": self.is_dangerous,
            "rf_params": self.rf_params,
            "audio_params": self.audio_params,
        }
        # Додаємо ID тільки якщо він є (для редагування)
        if self.id:
            data["id"] = self.id
        return data
