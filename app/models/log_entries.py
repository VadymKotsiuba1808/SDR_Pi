from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeGuard, TypeVar, Union

from app.models.detection_event import DetectionEvent


class LogType:
    """Константи типів логів для забезпечення цілісності даних."""

    DETECTION = "detection"
    FALSE_ALARM = "false_alarm"


@dataclass
class FalseAlarmPayload:
    """
    Дані про хибне спрацювання.

    Використовується, коли оператор позначає виявлений об'єкт як помилковий,
    щоб уникнути подальших некоректних спрацювань алгоритму.

    - **detection_id**: Унікальний ідентифікатор вихідної події виявлення.
    - **name**: Назва або опис об'єкта, який спричинив помилку.
    """

    detection_id: str
    name: str

    def to_dict(self) -> dict:
        """Перетворює об'єкт у словник для JSON-серіалізації."""
        return {
            "detection_id": self.detection_id,
            "name": self.name,
        }

    @staticmethod
    def from_dict(data: dict) -> "FalseAlarmPayload":
        """Створює екземпляр FalseAlarmPayload зі словника."""
        return FalseAlarmPayload(
            detection_id=data.get("detection_id", ""),
            name=data.get("name", "Unknown"),
        )


LogPayload = Union[DetectionEvent, FalseAlarmPayload]
T = TypeVar("T", bound=LogPayload)


@dataclass
class BaseLogEntry(Generic[T]):
    """
    Базовий клас логу з підтримкою різних типів payload.

    Забезпечує уніфіковану структуру для всіх типів системних повідомлень.

    - **type**: Строковий ідентифікатор типу логу (див. `LogType`).
    - **payload**: Конкретні дані події, тип яких залежить від `type`.
    - **timestamp**: Час створення запису в форматі ISO 8601.
    """

    type: str
    payload: T
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class LogEntry(BaseLogEntry[Union[DetectionEvent, FalseAlarmPayload]]):
    """
    Головний клас запису в лог.

    Цей клас використовується для обробки всіх вхідних та вихідних повідомлень журналу.
    Відповідає структурі JSON: `{type: "...", timestamp: "...", payload: {...}}`.
    """

    def to_dict(self) -> dict:
        """Серіалізація об'єкта у словник для мережевого обміну або збереження в БД."""
        payload_data = (
            self.payload.to_dict()
            if hasattr(self.payload, "to_dict")
            else self.payload.__dict__
        )

        return {
            "type": self.type,
            "timestamp": self.timestamp,
            "payload": payload_data,
        }

    @staticmethod
    def from_dict(data: dict) -> "LogEntry":
        """Фабричний метод для створення об'єкта залежно від поля `type`."""
        entry_type = data.get("type", LogType.DETECTION)
        timestamp = data.get("timestamp", datetime.now().isoformat())
        raw_payload = data.get("payload", {})
        payload_obj: Union[DetectionEvent, FalseAlarmPayload]

        if entry_type == LogType.DETECTION:
            payload_obj = DetectionEvent.from_dict(raw_payload)
        elif entry_type == LogType.FALSE_ALARM:
            payload_obj = FalseAlarmPayload.from_dict(raw_payload)
        else:
            # Дефолтний випадок для забезпечення стійкості до невідомих типів
            payload_obj = DetectionEvent.from_dict(raw_payload)

        return LogEntry(type=entry_type, timestamp=timestamp, payload=payload_obj)


def is_detection(log: BaseLogEntry[Any]) -> TypeGuard[BaseLogEntry[DetectionEvent]]:
    """Перевірка, чи є payload типом DetectionEvent."""
    return log.type == LogType.DETECTION


def is_false_alarm(
    log: BaseLogEntry[Any],
) -> TypeGuard[BaseLogEntry[FalseAlarmPayload]]:
    """Перевірка, чи є payload типом FalseAlarmPayload."""
    return log.type == LogType.FALSE_ALARM
