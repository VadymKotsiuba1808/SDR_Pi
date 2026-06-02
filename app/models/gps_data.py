from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class GPSData:
    """Модель даних GPS для зберігання координат та якості сигналу.

    Attributes:
        lat: Географічна широта.
        lon: Географічна довгота.
        strength: Рівень сигналу (0-100).
    """

    lat: float
    lon: float
    strength: int

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GPSData":
        return GPSData(
            lat=float(data.get("lat", 0)),
            lon=float(data.get("lon", 0)),
            strength=data.get("strength", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "strength": self.strength,
        }
