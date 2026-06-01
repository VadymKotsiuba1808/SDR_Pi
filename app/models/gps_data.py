from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class GPSData:
    """
    Представляє дані GPS, включаючи координати та рівень сигналу.

    Attributes:
        lat (float): Широта.
        lon (float): Довгота.
        strength (int): Рівень сигналу (від 0 до 100).
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
