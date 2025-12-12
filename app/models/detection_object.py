from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class DetectionObject:
    """
    Модель об'єкта для бази даних.
    Оновлено для підтримки списків частот та перейменовано audio -> sound.
    """

    name: str
    object_class: str
    id: Optional[str] = None
    is_dangerous: bool = False

    rf_params: List[Dict[str, Any]] = field(default_factory=list)
    sound_params: List[int] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict) -> "DetectionObject":
        return DetectionObject(
            id=data.get("id"),
            name=data.get("name", "Unnamed"),
            object_class=data.get("object_class", "unknown"),
            is_dangerous=bool(data.get("is_dangerous", False)),
            # Отримуємо списки, якщо їх немає - повертаємо пустий список
            rf_params=data.get("rf_params", []),
            sound_params=data.get("sound_params", []),
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
            "sound_params": self.sound_params,
        }
        if self.id:
            data["id"] = self.id
        return data
