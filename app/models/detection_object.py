from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DetectionObject:
    """
    Модель об'єкта виявлення, що зберігається в базі даних.

    Цей клас представляє сутність об'єкта (наприклад, конкретну модель БПЛА або систему зв'язку),
    який система може ідентифікувати за його радіочастотними або звуковими характеристиками.

    Attributes:
        id: Унікальний ідентифікатор об'єкта. `None` для нових об'єктів, що ще не збережені в БД.
        name: Назва об'єкта (наприклад, "Orlan-10").
        class_id: ID категорії об'єкта (посилання на `ObjectClass`).
        object_class: Текстова назва класу об'єкта для зручності відображення в UI.
        is_dangerous: Прапор, що вказує, чи є об'єкт потенційно небезпечним (ворожим).
        rf_params_hz: Список частотних діапазонів у форматі "min-max" (Гц), на яких працює об'єкт.
            Використовується для співставлення з поточним спектром.
        sound_params_hz: Список характерних звукових частот (Гц) об'єкта.
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
