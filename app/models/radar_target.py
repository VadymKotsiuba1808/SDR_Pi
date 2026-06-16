from dataclasses import dataclass, field
from datetime import datetime

from app.models.detection_event import DetectionEvent

# Поріг зміщення для визначення факту руху (10 метрів)
MOVE_THRESHOLD_KM = 0.01
# Поріг зміни кута для визначення факту руху (1 градус)
ANGLE_THRESHOLD_DEG = 1.0


@dataclass
class RadarTarget:
    """
    Представлення активної цілі на радарі.

    Зберігає подію виявлення, візуальний індекс та часові мітки активності.
    Використовується для фільтрації застарілих цілей та визначення статики.

    - **event**: Поточна подія виявлення.
    - **visual_index**: Порядковий номер цілі для UI.
    - **last_seen**: Час останнього оновлення цілі.
    - **last_moved_time**: Час останньої значущої зміни координат.
    - **anchor_event**: "Опорна" подія для порівняння зміщення.
    """

    event: DetectionEvent
    visual_index: int
    last_seen: datetime = field(default_factory=datetime.now)
    last_moved_time: datetime = field(default_factory=datetime.now)

    anchor_event: DetectionEvent = field(init=False)

    def __post_init__(self) -> None:
        self.anchor_event = self.event

    def update(self, new_event: DetectionEvent) -> None:
        """Оновлює стан цілі та перевіряє факт руху."""
        dist_diff = abs(self.anchor_event.distance_km - new_event.distance_km)
        angle_diff = abs(self.anchor_event.angle - new_event.angle)

        if dist_diff > MOVE_THRESHOLD_KM or angle_diff > ANGLE_THRESHOLD_DEG:
            self.last_moved_time = datetime.now()
            self.anchor_event = new_event

        self.last_seen = datetime.now()
        self.event = new_event

    def is_stationary_for(self, seconds: float) -> bool:
        """Перевіряє, чи об'єкт нерухомий протягом вказаного часу."""
        delta = datetime.now() - self.last_moved_time
        return delta.total_seconds() >= seconds

    def is_expired(self, ttl_seconds: float) -> bool:
        """Перевіряє, чи застаріла ціль (Time-to-Live)."""
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
