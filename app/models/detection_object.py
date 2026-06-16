from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DetectionObject:
    """Модель об'єкта виявлення для ідентифікації БПЛА та систем зв'язку.

    Attributes:
        id: Унікальний ідентифікатор (None для нових).
        name: Назва об'єкта.
        class_id: ID категорії об'єкта.
        object_class: Текстова назва класу.
        is_dangerous: Чи є об'єкт потенційно небезпечним.
        rf_params_hz: Частотні діапазони "min-max" (Гц).
        sound_params_hz: Характерні звукові частоти (Гц).
    """

    id: Optional[int]
    name: str

    class_id: int
    object_class: str

    is_dangerous: bool = False
    rf_params_hz: List[str] = field(default_factory=list)
    sound_params_hz: List[int] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict) -> "DetectionObject":
        raw_id = data.get("id")
        obj_id = int(raw_id) if raw_id is not None else None

        return DetectionObject(
            id=obj_id,
            name=data.get("name", "Unnamed"),
            class_id=int(data.get("class_id", 0)),
            object_class=data.get("object_class", "Unknown"),
            is_dangerous=bool(data.get("is_dangerous", False)),
            rf_params_hz=data.get("rf_params_hz", []),
            sound_params_hz=data.get("sound_params_hz", []),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "class_id": self.class_id,
            "object_class": self.object_class,
            "is_dangerous": self.is_dangerous,
            "rf_params_hz": self.rf_params_hz,
            "sound_params_hz": self.sound_params_hz,
        }
