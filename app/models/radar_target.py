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
    Клас-обгортка, що представляє одну активну ціль на радарі.

    Зберігає саму подію виявлення, її візуальний індекс для відображення
    на інтерфейсі та часові мітки останньої активності. Використовується
    для фільтрації застарілих цілей та визначення статичних об'єктів.

    Attributes:
        event (DetectionEvent): Поточна подія виявлення.
        visual_index (int): Порядковий номер цілі для UI.
        last_seen (datetime): Час останнього оновлення цілі.
        last_moved_time (datetime): Час останньої значущої зміни координат.
        anchor_event (DetectionEvent): "Опорна" подія для порівняння зміщення.
    """

    event: DetectionEvent
    visual_index: int
    last_seen: datetime = field(default_factory=datetime.now)
    last_moved_time: datetime = field(default_factory=datetime.now)

    anchor_event: DetectionEvent = field(init=False)

    def __post_init__(self) -> None:
        self.anchor_event = self.event

    def update(self, new_event: DetectionEvent) -> None:
        """
        Оновлює стан цілі новими даними.

        Перевіряє, чи відбулося значуще переміщення відносно опорної події.
        Якщо зміна дистанції або кута перевищує встановлені пороги,
        оновлюється час останнього руху та опорна подія.

        Args:
            new_event (DetectionEvent): Нові дані виявлення.
        """
        dist_diff = abs(self.anchor_event.distance_km - new_event.distance_km)
        angle_diff = abs(self.anchor_event.angle - new_event.angle)

        # Перевіряємо пороги, щоб відфільтрувати незначні коливання сигналу
        # та визначити, чи дійсно об'єкт перемістився.
        if dist_diff > MOVE_THRESHOLD_KM or angle_diff > ANGLE_THRESHOLD_DEG:
            self.last_moved_time = datetime.now()
            self.anchor_event = new_event

        self.last_seen = datetime.now()
        self.event = new_event

    def is_stationary_for(self, seconds: float) -> bool:
        """
        Перевіряє, чи є об'єкт нерухомим протягом вказаного часу.

        Args:
            seconds (float): Час у секундах.

        Returns:
            bool: True, якщо об'єкт не рухався довше вказаного часу.
        """
        delta = datetime.now() - self.last_moved_time
        return delta.total_seconds() >= seconds

    def is_expired(self, ttl_seconds: float) -> bool:
        """
        Перевіряє, чи застаріла ціль (Time-to-Live).

        Args:
            ttl_seconds (float): Максимальний час життя цілі без оновлень.

        Returns:
            bool: True, якщо ціль не оновлювалася довше ttl_seconds.
        """
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
