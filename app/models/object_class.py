from dataclasses import dataclass
from typing import Optional


@dataclass
class ObjectClass:
    """
    Модель класу (категорії) об'єкта детекції.

    Використовується для групування об'єктів за типами (наприклад, "БПЛА", "РЛС").

    Attributes:
        id: Унікальний ідентифікатор у базі даних.
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
