from dataclasses import dataclass, field
from datetime import datetime
from app.models.detection_event import DetectionEvent


@dataclass
class RadarTarget:
    """
    Клас-обгортка, що представляє одну активну ціль на радарі.
    Зберігає саму подію, її візуальний номер та час останньої активності.
    """

    event: DetectionEvent
    visual_index: int
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    def update(self, new_event: DetectionEvent):
        """Оновлює дані цілі новою подією."""
        self.event = new_event
        self.last_seen = datetime.now()

    def is_expired(self, ttl_seconds: float) -> bool:
        """Перевіряє, чи не застаріла ціль."""
        age = (datetime.now() - self.last_seen).total_seconds()
        return age > ttl_seconds

    @property
    def id(self) -> str:
        return self.event.id

    @property
    def distance_km(self) -> float:
        return self.event.distance_km

    @property
    def angle(self) -> float:
        return self.event.angle
