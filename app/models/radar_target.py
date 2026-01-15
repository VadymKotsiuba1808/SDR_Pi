from dataclasses import dataclass, field
from datetime import datetime
from app.models.detection_event import DetectionEvent

MOVE_THRESHOLD_KM = 0.01  # 10 метрів
ANGLE_THRESHOLD_DEG = 1.0


@dataclass
class RadarTarget:
    """
    Клас-обгортка, що представляє одну активну ціль на радарі.
    Зберігає саму подію, її візуальний номер та час останньої активності.
    """

    event: DetectionEvent
    visual_index: int
    # first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    last_moved_time: datetime = field(default_factory=datetime.now)

    anchor_event: DetectionEvent = field(init=False)

    def __post_init__(self):
        """Викликається автоматично після створення об'єкта dataclass."""
        self.anchor_event = self.event

    def update(self, new_event: DetectionEvent):
        dist_diff = abs(self.anchor_event.distance_km - new_event.distance_km)
        angle_diff = abs(self.anchor_event.angle - new_event.angle)

        if dist_diff > MOVE_THRESHOLD_KM or angle_diff > ANGLE_THRESHOLD_DEG:
            self.last_moved_time = datetime.now()
            self.anchor_event = new_event

        self.last_seen = datetime.now()
        self.event = new_event

    def is_stationary_for(self, seconds: float) -> bool:
        """Повертає True, якщо об'єкт не рухався вказану кількість секунд."""
        delta = datetime.now() - self.last_moved_time
        return delta.total_seconds() >= seconds

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
