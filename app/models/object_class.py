from dataclasses import dataclass
from typing import Optional


@dataclass
class ObjectClass:
    """
    Представляє клас (категорію) об'єкта детекції.

    Цей клас використовується для групування конкретних об'єктів за типами,
    наприклад: "БПЛА", "Вертоліт", "РЛС" тощо.

    Attributes:
        id: Унікальний ідентифікатор класу в базі даних.
        name: Назва класу об'єкта.
    """

    id: Optional[int]
    name: str

    @staticmethod
    def from_dict(data: dict) -> "ObjectClass":
        raw_id = data.get("id")
        class_id = int(raw_id) if raw_id is not None else None

        return ObjectClass(
            id=class_id,
            name=data.get("name", "Unnamed"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
        }
