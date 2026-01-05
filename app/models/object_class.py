from typing import Optional
from dataclasses import dataclass


@dataclass
class ObjectClass:
    id: Optional[int]
    name: str

    @staticmethod
    def from_dict(data: dict) -> "ObjectClass":
        return ObjectClass(
            id=int(data.get("id", 0)),
            name=data.get("name", "Unnamed"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
        }
