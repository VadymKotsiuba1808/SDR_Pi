from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class CleanRule:
    """
    Модель правила очищення застарілих даних.

    Attributes:
        enabled (bool): Чи увімкнено правило автоматичного очищення.
        days (int): Кількість днів, після яких дані вважаються застарілими.
    """

    enabled: bool
    days: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CleanRule":
        if not data:
            return CleanRule(enabled=False, days=30)
        return CleanRule(
            enabled=data.get("enabled", False), days=int(data.get("days", 30))
        )
