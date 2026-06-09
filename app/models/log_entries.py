from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeGuard, TypeVar, Union

from app.models.detection_event import DetectionEvent


class LogType:
    DETECTION = "detection"
    FALSE_ALARM = "false_alarm"


@dataclass
class FalseAlarmPayload:
    detection_id: str
    name: str

    def to_dict(self) -> dict:
        return {
            "detection_id": self.detection_id,
            "name": self.name,
        }

    @staticmethod
    def from_dict(data: dict) -> "FalseAlarmPayload":
        return FalseAlarmPayload(
            detection_id=data.get("detection_id", ""),
            name=data.get("name", "Unknown"),
        )


LogPayload = Union[DetectionEvent, FalseAlarmPayload]
T = TypeVar("T", bound=LogPayload)


@dataclass
class BaseLogEntry(Generic[T]):
    """Базовий клас логу, який вміє підлаштовувати тип payload."""

    type: str
    payload: T
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class LogEntry(BaseLogEntry[Union[DetectionEvent, FalseAlarmPayload]]):
    """
    Головний клас запису в лог.
    Відповідає структурі JSON: {type: "...", timestamp: "...", payload: {...}}
    """

    def to_dict(self) -> dict:
        """Серіалізація у JSON."""

        payload_data = (
            self.payload.to_dict()
            if hasattr(self.payload, "to_dict")
            else self.payload.__dict__
        )

        return {"type": self.type, "timestamp": self.timestamp, "payload": payload_data}

    @staticmethod
    def from_dict(data: dict) -> "LogEntry":
        """Фабричний метод: створює правильний об'єкт залежно від type."""
        entry_type = data.get("type", LogType.DETECTION)
        timestamp = data.get("timestamp", datetime.now().isoformat())
        raw_payload = data.get("payload", {})
        payload_obj: Union[DetectionEvent, FalseAlarmPayload]

        if entry_type == LogType.DETECTION:
            payload_obj = DetectionEvent.from_dict(raw_payload)
        elif entry_type == LogType.FALSE_ALARM:
            payload_obj = FalseAlarmPayload.from_dict(raw_payload)
        else:
            payload_obj = DetectionEvent.from_dict(raw_payload)

        return LogEntry(type=entry_type, timestamp=timestamp, payload=payload_obj)


def is_detection(log: BaseLogEntry[Any]) -> TypeGuard[BaseLogEntry[DetectionEvent]]:
    """Вказує, що у цього логу payload є DetectionEvent."""
    return log.type == "detection"


def is_false_alarm(
    log: BaseLogEntry[Any],
) -> TypeGuard[BaseLogEntry[FalseAlarmPayload]]:
    """Вказує, що у цього логу payload є FalseAlarmPayload."""
    return log.type == "false_alarm"
