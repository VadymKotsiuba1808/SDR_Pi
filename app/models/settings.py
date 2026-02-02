from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class CleanRule:
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
