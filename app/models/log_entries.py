from dataclasses import dataclass, field
from typing import Optional, Union, Dict, Any
import uuid
from datetime import datetime

from app.models.detection_event import DetectionEvent


class LogType:
    DETECTION = "detection"
    FALSE_ALARM = "false_alarm"


@dataclass
class FalseAlarmPayload:
    detection_id: str
    name: str

    @staticmethod
    def from_dict(data: dict) -> "FalseAlarmPayload":
        return FalseAlarmPayload(
            detection_id=data.get("detection_id", ""),
            name=data.get("name", "Unknown"),
        )


@dataclass
class LogEntry:
    """
    Головний клас запису в лог.
    Відповідає структурі JSON: {type: "...", timestamp: "...", payload: {...}}
    """

    type: str
    payload: Union[DetectionEvent, FalseAlarmPayload]
    timestamp: str = datetime.now().isoformat()

    @property
    def is_detection(self):
        return self.type == LogType.DETECTION

    @property
    def is_false_alarm(self):
        return self.type == LogType.FALSE_ALARM

    def to_dict(self) -> dict:
        """Серіалізація у JSON."""

        return {
            "type": self.type,
            "timestamp": self.timestamp,
            "payload": self.payload.__dict__,
        }

    @staticmethod
    def from_dict(data: dict) -> "LogEntry":
        """Фабричний метод: створює правильний об'єкт залежно від type."""
        entry_type = data.get("type", LogType.DETECTION)
        timestamp = data.get("timestamp", datetime.now().isoformat())
        raw_payload = data.get("payload", {})

        if entry_type == LogType.DETECTION:
            payload_obj = DetectionEvent.from_dict(raw_payload)
        elif entry_type == LogType.FALSE_ALARM:
            payload_obj = FalseAlarmPayload.from_dict(raw_payload)
        else:
            payload_obj = DetectionEvent.from_dict(raw_payload)

        return LogEntry(type=entry_type, timestamp=timestamp, payload=payload_obj)
